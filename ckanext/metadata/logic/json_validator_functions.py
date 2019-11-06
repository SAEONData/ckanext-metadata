# encoding: utf-8

import jsonschema
import jsonschema.validators
import jsonschema._utils
import jsonpointer
import jsonpatch
from datetime import datetime
import re
import urlparse
import sys
import requests
from requests.exceptions import RequestException

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.common import DOI_RE, TIME_RE

checks_format = jsonschema.FormatChecker.cls_checks


def _unique_objects(array, key_properties):
    """
    Test whether objects in an array are unique with respect to the given set of properties.
    """
    key_objects = []
    for obj in array:
        key_object = {k: v for k, v in obj.iteritems() if k in key_properties}
        if key_object in key_objects:
            return False
        key_objects += [key_object]
    return True


def vocabulary_validator(validator, vocabulary_name, instance, schema):
    """
    "vocabulary" keyword validator function: checks that instance is a tag from the named vocabulary.
    The check is case-insensitive.
    """
    if validator.is_type(instance, 'string'):
        try:
            vocabulary = tk.get_action('vocabulary_show')(data_dict={'id': vocabulary_name})
            tags = [tag['name'].lower() for tag in vocabulary['tags']]
            if instance.lower() not in tags:
                yield jsonschema.ValidationError(_('Tag not found in vocabulary'))
        except tk.ObjectNotFound:
            yield jsonschema.ValidationError("%s: %s '%s'" % (_('Not found'), _('Vocabulary'), vocabulary_name))


def objectid_validator(validator, model_name, instance, schema):
    """
    "objectid" keyword validator function: checks that instance is the id of an object of the named model.
    """
    if validator.is_type(instance, 'string'):
        show_func_name = '{}_show'.format(model_name)
        try:
            show_func = tk.get_action(show_func_name)
        except:
            yield jsonschema.ValidationError(_("Invalid model name '{}': action '{}' not found".
                                               format(model_name, show_func_name)))
            return

        try:
            object_dict = show_func({}, {'id': instance})
        except:
            yield jsonschema.ValidationError("%s: %s" % (_("Not found"), _("User")))
            return

        if object_dict['id'] != instance:
            yield jsonschema.ValidationError(_("Must use object id not name"))


def role_validator(validator, role_name, instance, schema):
    """
    "role" keyword validator function: checks that instance is the id of a user with the named role.
    """
    if validator.is_type(instance, 'string'):
        yield jsonschema.ValidationError("Role validation has not been implemented yet")


def unique_objects_validator(validator, key_properties, instance, schema):
    """
    "uniqueObjects" keyword validator: for an array comprising objects, this checks that the objects
    are unique with respect to the named properties.
    """
    if validator.is_type(instance, 'array') and validator.is_type(schema.get('items', {}), 'object'):
        if not _unique_objects(instance, key_properties):
            yield jsonschema.ValidationError(_("%r has non-unique objects") % (instance,))


def unique_properties_validator(validator, params, instance, schema):
    """
    "uniqueProperties" keyword validator: for an object, checks that the child instances for
    properties with names that match a given regex pattern ("namePattern") are unique.

    e.g.    "uniqueProperties": {
                "namePattern": "element[0-9]+",
                "childProperties": ["key1", "key2"]
            }

    For child instances that are not objects, uniqueness is determined as for "uniqueItems".
    For child instances that are objects, uniqueness is determined as for "uniqueObjects",
    with the child instance key properties specified in the "childProperties" array.
    """
    if validator.is_type(instance, 'object') and validator.is_type(params, 'object'):
        name_pattern = params.get('namePattern', '')
        child_properties = params.get('childProperties', [])
        child_objects = []
        child_non_objects = []
        for name, child_instance in instance.iteritems():
            if re.search(name_pattern, name):
                if validator.is_type(child_instance, 'object'):
                    child_objects += [child_instance]
                else:
                    child_non_objects += [child_instance]

        if not _unique_objects(child_objects, child_properties) or not jsonschema._utils.uniq(child_non_objects):
            yield jsonschema.ValidationError(_("%r has non-unique properties") % (instance,))


def task_validator(validator, task_dict, instance, schema):
    """
    "task" keyword validator: adds a task to the validator, which will call the specified action
    (for the object currently being validated) post-validation if this instance is otherwise valid.
    A task looks like::
        {
            'action': API action name,
            'params': array of [{
                'param': a key in the data_dict to be passed to the action,
                'valueRelPath': JSON pointer into this instance where the value is located
            }],
            'errorAbsPath': JSON pointer into the whole document; the task will only be executed if
                the instance at this location contains no errors
        }

    Note: Validation is usually expected to be a side effect-free process. However, because
    a task likely will cause side effects (i.e. updates to DB objects, besides validation logs),
    we require 'allow_side_effects': True to be set in the context; if False (the default),
    the task is not run and an explanatory error is added.
    """
    if validator.is_type(task_dict, 'object'):
        allow_side_effects = validator.context.get('allow_side_effects', False)
        action_name = task_dict.get('action', '')
        params = task_dict.get('params', [])
        error_path = task_dict.get('errorAbsPath', '')
        errors = False

        if not allow_side_effects:
            errors = True
            yield jsonschema.ValidationError(_("Task cannot be run in this context"))

        try:
            action_func = tk.get_action(action_name)
        except:
            errors = True
            yield jsonschema.ValidationError(_("Action '{}' not found".format(action_name)))

        if not validator.object_id:
            errors = True
            yield jsonschema.ValidationError(_("object_id is not available"))

        data_dict = {'id': validator.object_id}
        try:
            for param in params:
                data_dict[param['param']] = jsonpointer.resolve_pointer(instance, param['valueRelPath'])
        except (TypeError, KeyError):
            errors = True
            yield jsonschema.ValidationError(_("Invalid params array"))
        except jsonpointer.JsonPointerException:
            errors = True
            yield jsonschema.ValidationError(_("valueRelPath: invalid JSON pointer"))

        try:
            jsonpointer.resolve_pointer(validator.root_instance, error_path)
        except jsonpointer.JsonPointerException:
            errors = True
            yield jsonschema.ValidationError(_("errorAbsPath: invalid JSON pointer"))

        if not errors:
            validator.add_post_validation_task(action_func, data_dict, error_path)


def item_cardinality_validator(validator, item_cardinality, instance, schema):
    """
    "itemCardinality" keyword validator: checks that items matching the given schema have at
    least "minCount" and at most "maxCount" occurrences in the array.
    """
    if validator.is_type(instance, 'array'):
        matches = [item for item in instance if validator.is_valid(item, item_cardinality)]
        if len(matches) < item_cardinality.get('minCount', 0):
            yield jsonschema.ValidationError(_("Array contains too few items that match the given schema"))
        if len(matches) > item_cardinality.get('maxCount', sys.maxint):
            yield jsonschema.ValidationError(_("Array contains too many items that match the given schema"))


def url_test_validator(validator, url_exists, instance, schema):
    """
    "urlTest" keyword validator: does a HEAD request to the specified url; the value of this keyword
    (url_exists) is a boolean.
    """
    if validator.is_type(instance, 'string'):
        try:
            response = requests.head(instance)
            response.raise_for_status()
            if not url_exists:
                yield jsonschema.ValidationError(_("URL test is intended to fail for the specified value"))
        except RequestException, e:
            if url_exists:
                yield jsonschema.ValidationError(e.message)


def map_init_validator(validator, target_elements, instance, schema):
    """
    "mapInit" keyword validator: initializes the top-level target elements that will be
    written to by "mapTo" operations.

    "mapInit" is a dict containing the target element names and their corresponding types.
    """
    if validator.is_type(target_elements, 'object'):
        for target_name, target_type in target_elements.iteritems():
            if target_type == 'string':
                validator.root_instance[target_name] = ''
            elif target_type == 'array':
                validator.root_instance[target_name] = []
            else:
                yield jsonschema.ValidationError(_("Unsupported top-level target element type"))


def map_to_validator(validator, map_params, instance, schema):
    """
    "mapTo" keyword validator: provides flexible copying of data from the instance being
    validated to a different location in the document, where the target may be differently
    structured and have different semantics.

    "mapTo" is a dict with the following structure:
    ::
        {
            "target": JSON pointer to the target location
            "value": schema for the value to be inserted at the target location
        }

    The "value" schema has the following structure:
    ::
        {
            "type": (mandatory)
                - the JSON type of the target value; only "string", "array" and "object" are supported
            "source": (optional)
                - if this is a string, it specifies the property on the current instance from which the
                  target value is obtained
                - for a target type of string, this may be a list of strings; it specifies the properties
                  on the current instance from which the target value is constructed, by concatenating
                  source values, separated by newlines
                - if this is not specified, then the entire current instance is used as the source of the
                  target value
            "converter": (optional, for a target type of string)
                - if this is a dict, it defines a simple vocabulary converter, with key-value pairs
                  specifying source-target keyword conversions
                - if this is a string, it indicates a conversion function (linked to a Python routine
                  in JSONValidator._converters), which takes the source value as input and returns the
                  target value
            "items": (mandatory, for a target type of array)
                - defines a nested "value" schema to be used for every item in the target array
            "properties": (mandatory, for a target type of object)
                - defines nested "value" schemas to be used for each property in the target object
        }
    """
    def make_value(source_instance, **kwargs):
        target_type = kwargs.get('type')
        source_prop = kwargs.pop('source', None)

        if not target_type:
            raise SyntaxError(_("A 'type' must be specified for the target value"))
        if source_prop and type(source_instance) is not dict:
            raise SyntaxError(_("The 'source' keyword can only be used with object instances"))

        if isinstance(source_prop, basestring):
            if source_prop in source_instance:
                return make_value(source_instance[source_prop], **kwargs)
            return None
        elif type(source_prop) is list:
            if target_type != 'string':
                raise SyntaxError(_("The 'source' keyword can only specify a list of properties if the target type is 'string'"))
            result = []
            for source_prop_i in source_prop:
                if source_prop_i in source_instance:
                    result += [make_value(source_instance[source_prop_i], **kwargs)]
            return '\n'.join(result)

        if target_type == 'string':
            converter = kwargs.pop('converter', None)
            if type(converter) is dict:
                return converter.get(str(source_instance), str(source_instance))
            elif isinstance(converter, basestring):
                if converter not in validator.converters:
                    raise SyntaxError(_("Converter '{}' not found".format(converter)))
                converter_fn = validator.converters[converter]
                try:
                    return str(converter_fn(source_instance))
                except Exception, e:
                    raise ValueError(_("Unable to convert value using '{}' function: {}".format(converter, e)))
            return str(source_instance)

        elif target_type == 'array':
            item_schema = kwargs.pop('items', None)
            if type(item_schema) is not dict:
                raise SyntaxError(_("An 'items' dictionary must be defined for a target type of 'array'"))
            if type(source_instance) is list:
                return [make_value(source_item, **item_schema) for source_item in source_instance]
            return [make_value(source_instance, **item_schema)]

        elif target_type == 'object':
            properties = kwargs.pop('properties', None)
            if type(properties) is not dict:
                raise SyntaxError(_("A 'properties' dictionary must be defined for a target type of 'object'"))
            result = {}
            for prop_name, prop_schema in properties.iteritems():
                if type(prop_schema) is not dict:
                    raise SyntaxError(_("The value for each property, for a target type of 'object', must be a dictionary"))
                result[prop_name] = make_value(source_instance, **prop_schema)
            return result

        else:
            raise SyntaxError(_("Unsupported 'type' for target: '{}'".format(target_type)))

    if validator.is_type(map_params, 'object'):
        target_path = map_params.get('target')
        value_schema = map_params.get('value')
        errors = False

        if not target_path:
            errors = True
            yield jsonschema.ValidationError(_("A 'target' must be defined"))
        elif target_path == '/':
            errors = True
            yield jsonschema.ValidationError(_("'target' cannot be the document root"))
        else:
            try:
                jsonpointer.JsonPointer(target_path)
            except (TypeError, jsonpointer.JsonPointerException):
                errors = True
                yield jsonschema.ValidationError(_("'target': invalid JSON pointer"))

        if type(value_schema) is not dict:
            errors = True
            yield jsonschema.ValidationError(_("A 'value' schema dictionary must be defined"))

        if errors:
            return

        try:
            operation = {
                'op': 'add',
                'path': target_path,
                'value': make_value(instance, **value_schema),
            }
            patch = jsonpatch.JsonPatch([operation])
            patch.apply(validator.root_instance, in_place=True)

        except SyntaxError, e:
            yield jsonschema.ValidationError(_("Schema syntax error: {}".format(e)))
        except ValueError, e:
            yield jsonschema.ValidationError(_(str(e)))
        except (TypeError, jsonpatch.JsonPatchException, jsonpointer.JsonPointerException), e:
            yield jsonschema.ValidationError(_("Error applying mapping: {}".format(e)))


@checks_format('doi')
def is_doi(instance):
    if not isinstance(instance, basestring):
        return True
    return re.match(DOI_RE, instance) is not None


@checks_format('url')
def is_url(instance):
    if not isinstance(instance, basestring):
        return True
    try:
        urlparts = urlparse.urlparse(instance)
        if not urlparts.scheme or not urlparts.netloc:
            return False
        return True
    except ValueError:
        return False


@checks_format('year')
def is_year(instance):
    if not isinstance(instance, basestring):
        return True
    try:
        datetime.strptime(instance, '%Y')
        return True
    except ValueError:
        return False


@checks_format('yearmonth')
def is_yearmonth(instance):
    if not isinstance(instance, basestring):
        return True
    try:
        datetime.strptime(instance, '%Y-%m')
        return True
    except ValueError:
        return False


@checks_format('date')
def is_date(instance):
    if not isinstance(instance, basestring):
        return True
    try:
        datetime.strptime(instance, '%Y-%m-%d')
        return True
    except ValueError:
        return False


@checks_format('datetime')
def is_datetime(instance):
    if not isinstance(instance, basestring):
        return True
    try:
        datestr, timestr = instance.split('T')
        datetime.strptime(datestr, '%Y-%m-%d')
        time_match = re.match(TIME_RE, timestr)
        if time_match:
            h, m, s, tzh, tzm = time_match.group('h', 'm', 's', 'tzh', 'tzm')
            if (
                    0 <= int(h) <= 23 and
                    0 <= int(m) <= 59 and
                    0 <= int(s) <= 59 and
                    0 <= int(tzm) <= 59
            ):
                return True
        return False
    except ValueError:
        return False


def _is_range(instance, func):
    if not isinstance(instance, basestring):
        return True
    try:
        start, end = instance.split('/')
        if not start and not end:
            return False
        valid_start = not start or func(start)
        valid_end = not end or func(end)
        return valid_start and valid_end
    except ValueError:
        return False


@checks_format('year-range')
def is_year_range(instance):
    return _is_range(instance, is_year)


@checks_format('yearmonth-range')
def is_yearmonth_range(instance):
    return _is_range(instance, is_yearmonth)


@checks_format('date-range')
def is_date_range(instance):
    return _is_range(instance, is_date)


@checks_format('datetime-range')
def is_datetime_range(instance):
    return _is_range(instance, is_datetime)


@checks_format('longitude')
def is_longitude(instance):
    if not isinstance(instance, basestring):
        return True
    try:
        return -180 <= float(instance) <= 180
    except ValueError:
        return False


@checks_format('latitude')
def is_latitude(instance):
    if not isinstance(instance, basestring):
        return True
    try:
        return -90 <= float(instance) <= 90
    except ValueError:
        return False


def date_to_year(instance):
    """
    "date-to-year" converter for the "mapTo" keyword validator.
    """
    dt = datetime.strptime(instance, '%Y-%m-%d')
    return str(dt.year)
