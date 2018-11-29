# encoding: utf-8

import json
import uuid
import re
import urlparse
import jsonschema
import jsonpointer

import ckan.plugins.toolkit as tk
from ckan.common import _, config
import ckan.lib.navl.dictization_functions as df
import ckanext.metadata.model as ckanext_model
from ckanext.metadata.logic.json_validator import JSONValidator
from ckanext.metadata.common import model_info

convert_to_extras = tk.get_validator('convert_to_extras')


# region Utils

def _make_uuid():
    return unicode(uuid.uuid4())


def _convert_missing(value, default=None):
    """
    Convert Missing to None or some other default.
    """
    if value is tk.missing:
        return default
    return value


def _generate_name(*strings):
    """
    Converts the given string(s) into a form suitable for an object name.
    """
    strings = list(strings)
    while '' in strings:
        strings.remove('')
    text = '_'.join(strings)
    return re.sub(r'[^a-z0-9_-]+', '-', text.lower())

# endregion


# region General validators / converters

def not_missing(key, data, errors, context):
    """
    Replaces the built-in CKAN validator not_missing, so that we can distinguish
    between missing and empty values.
    """
    value = data.get(key)
    if value is tk.missing:
        errors.setdefault(key, [])
        errors[key].append(_('Missing parameter'))
        raise tk.StopOnError


def not_empty(key, data, errors, context):
    """
    Replaces the built-in CKAN validator not_empty, so that we can distinguish
    between missing and empty values. This checks not_missing as well.
    """
    not_missing(key, data, errors, context)
    value = data.get(key)
    if not value:
        errors.setdefault(key, [])
        errors[key].append(_('Missing value'))
        raise tk.StopOnError


def json_object_validator(value):
    """
    Checks for well-formed JSON.
    """
    if value:
        try:
            json.loads(value)
        except ValueError, e:
            raise tk.Invalid(_("JSON decode error: %s") % e.message)

    return value


def json_dict_validator(value):
    """
    Checks for well-formed JSON, and that the supplied JSON represents a dictionary.
    """
    if value:
        try:
            obj = json.loads(value)
        except ValueError, e:
            raise tk.Invalid(_("JSON decode error: %s") % e.message)

        if type(obj) is not dict:
            raise tk.Invalid(_("Expecting a JSON dictionary"))

    return value


def json_schema_validator(value):
    """
    Checks that the value represents a valid JSON schema.
    """
    if value:
        try:
            schema = json.loads(value)
            JSONValidator.check_schema(schema)
        except ValueError, e:
            raise tk.Invalid(_("JSON decode error: %s") % e.message)
        except AttributeError, e:
            raise tk.Invalid(_("Expecting a JSON dictionary"))
        except jsonschema.SchemaError, e:
            raise tk.Invalid(_("Invalid JSON schema: %s") % e.message)

    return value


def json_pointer_validator(value):
    """
    Checks that the value is a valid JSON pointer.
    """
    if value:
        try:
            jsonpointer.JsonPointer(value)
        except jsonpointer.JsonPointerException, e:
            raise tk.Invalid(_("Invalid JSON pointer: %s") % e.message)

    return value


def deserialize_json(value):
    """
    Converts a JSON-format string to an object - for use in "show" schemas
    enabling JSON fields to be nicely embedded in output dicts. If it cannot
    be deserialized, just return the value itself.
    """
    try:
        return json.loads(value)
    except:
        return value


def url_validator(value):
    """
    Check for well-formed URL.
    """
    if value:
        try:
            urlparts = urlparse.urlparse(value)
            if not urlparts.scheme:
                raise ValueError("Missing scheme")
            if not urlparts.netloc:
                raise ValueError("Missing netloc")
        except ValueError, e:
            raise tk.Invalid(_("Invalid URL: %s") % e.message)

    return value


def augmented_schema_validator(schema):
    """
    Checks that the first element of the supplied JSON pointer value is a valid key
    for augmenting the given schema; i.e. it won't replace an already existing key
    in the schema.
    """
    def callable_(key, data, errors, context):
        value = data.get(key)
        parts = value.split('/')
        if len(parts) < 2 or not parts[1]:
            raise tk.Invalid(_("Invalid path"))
        element = parts[1]
        if element in schema:
            raise tk.Invalid(_("An existing key name cannot be used"))

    return callable_


def schema_attribute_validator(schema):
    """
    Checks that the supplied value is a key in the given schema.
    """
    def callable_(key, data, errors, context):
        value = data.get(key)
        if value not in schema:
            raise tk.Invalid(_("The specified attribute cannot be used"))

    return callable_

# endregion


# region Framework validators / converters

def object_name_validator(model_name):
    """
    Checks that the supplied object name is not already in use for the given model.
    """
    model_class = model_info[model_name]['model']
    model_desc = model_info[model_name]['desc']

    def callable_(key, data, errors, context):
        session = context['session']
        obj = context.get(model_name)

        query = session.query(model_class.name).filter_by(name=data[key])
        id_ = obj.id if obj else _convert_missing(data.get(key[:-1] + ('id',)))
        if id_:
            query = query.filter(model_class.id != id_)
        result = query.first()
        if result:
            errors[key].append('%s: %s' % (_('Duplicate name'), _(model_desc)))

    return callable_


def object_exists(model_name):
    """
    Checks that an object exists and is not deleted, and converts name to id if applicable.
    """
    model_class = model_info[model_name]['model']
    model_desc = model_info[model_name]['desc']

    def callable_(key, data, errors, context):
        object_id_or_name = data.get(key)
        if not object_id_or_name:
            data[key] = None
            raise tk.StopOnError

        obj = model_class.get(object_id_or_name)
        if not obj or obj.state == 'deleted' or (hasattr(obj, 'type') and obj.type != model_name):
            errors[key].append('%s: %s' % (_('Not found'), _(model_desc)))
            raise tk.StopOnError

        data[key] = obj.id

    return callable_


def object_does_not_exist(model_name):
    """
    Checks that an object id/name is not already in use.
    """
    model_class = model_info[model_name]['model']
    model_desc = model_info[model_name]['desc']

    def callable_(key, data, errors, context):
        object_id_or_name = data.get(key)
        if not object_id_or_name:
            return None

        result = model_class.get(object_id_or_name)
        if result:
            raise tk.Invalid('%s: %s' % (_('Already exists'), _(model_desc)))

    return callable_


def convert_id_to_name(model_name):
    """
    Converts an object's id to its name.

    Behaviour depends on the value of the config option 'ckan.metadata.convert_nested_ids_to_names'.
    If True, the object id is converted to name; if False (the default) the id is left unaltered.
    """
    convert_nested_ids_to_names = tk.asbool(config.get('ckan.metadata.convert_nested_ids_to_names', False))
    model_class = model_info[model_name]['model']

    def callable_(key, data, errors, context):
        if convert_nested_ids_to_names:
            id_ = data.get(key)
            obj = model_class.get(id_)
            if obj:
                data[key] = obj.name

    return callable_


def owner_org_owns_metadata_collection(key, data, errors, context):
    """
    Checks that the owner_org specified for a metadata record is the same organization that
    owns the metadata collection to which the record is being added.
    For use with the '__after' schema key; group names should already have been converted to group ids.
    """
    model = context['model']
    session = context['session']

    organization_id = data.get(key[:-1] + ('owner_org',))
    metadata_collection_id = _convert_missing(data.get(key[:-1] + ('metadata_collection_id',)))

    id_ = _convert_missing(data.get(key[:-1] + ('id',)))
    obj = model.Package.get(id_) if id_ else None

    # if we're updating, missing value(s) in the input data imply a partial update, so get the
    # existing value(s) and check that the updated combination satisfies our condition
    organization_id = _convert_missing(organization_id, obj.owner_org if obj else None)
    if obj and not metadata_collection_id:
        metadata_collection_id = session.query(model.PackageExtra.value) \
            .filter_by(package_id=id_, key='metadata_collection_id').scalar()

    metadata_collection_organization_id = session.query(model.GroupExtra.value) \
        .filter_by(group_id=metadata_collection_id, key='organization_id').scalar()

    if organization_id != metadata_collection_organization_id:
        raise tk.Invalid(_("owner_org must be the same organization that owns the metadata collection"))


def metadata_record_id_name_generator(key, data, errors, context):
    """
    Generates id and name for a new metadata record where these values have not been supplied.
    For use with the '__after' schema key.
    """
    if errors.get(key[:-1] + ('id',)):
        return  # id was supplied but has been popped out of data due to an error

    model = context['model']
    id_ = _convert_missing(data.get(key[:-1] + ('id',)))
    name = _convert_missing(data.get(key[:-1] + ('name',)))

    if id_ and model.Package.get(id_):
        return  # we only need to generate on create

    if not id_:
        id_ = _make_uuid()
        data[key[:-1] + ('id',)] = id_
    if not name:
        data[key[:-1] + ('name',)] = id_


def metadata_record_infrastructures_not_missing(key, data, errors, context):
    """
    Checks that the infrastructures list is not missing.
    For use with the '__before' schema key; CKAN puts empty lists into __extras,
    so we check that and pop as necessary.
    """
    unflattened = df.unflatten(data)
    infrastructures = unflattened.get('infrastructures')
    if infrastructures is not None:
        return

    extras = data.get(key[:-1] + ('__extras',), {})
    infrastructures = extras.get('infrastructures')
    if infrastructures is not None:
        extras.pop('infrastructures')
        return

    errors.setdefault(key[:-1] + ('infrastructures',), [])
    errors[key[:-1] + ('infrastructures',)].append(_('Missing parameter'))


def group_does_not_exist(group_id_or_name, context):
    if not group_id_or_name:
        return None

    model = context['model']
    result = model.Group.get(group_id_or_name)
    if result:
        raise tk.Invalid('%s: %s' % (_('Already exists'), _('Group')))

    return group_id_or_name


def unique_metadata_standard_name_and_version(key, data, errors, context):
    """
    For use with the '__after' schema key.
    """
    id_ = data.get(key[:-1] + ('id',))
    standard_name = _convert_missing(data.get(key[:-1] + ('standard_name',)))
    standard_version = _convert_missing(data.get(key[:-1] + ('standard_version',)))

    metadata_standard = ckanext_model.MetadataStandard.lookup(standard_name, standard_version)
    if metadata_standard and metadata_standard.state != 'deleted' and metadata_standard.id != id_:
        raise tk.Invalid(_("Unique constraint violation: %s") % '(standard_name, standard_version)')


def no_loops_in_metadata_standard_hierarchy(key, data, errors, context):
    """
    Checks that the parent standard specified in the data would not cause
    a loop in the metadata standard hierarchy.
    """
    metadata_standard = context.get('metadata_standard')
    if not metadata_standard:
        return  # it's a new object - no children

    parent_standard_id = data.get(key[:-1] + ('parent_standard_id',))
    parent = ckanext_model.MetadataStandard.get(parent_standard_id) \
        if parent_standard_id is not None else None

    while parent is not None:
        if parent == metadata_standard:
            raise tk.Invalid(_("Loop in metadata standard hierarchy"))
        parent = ckanext_model.MetadataStandard.get(parent.parent_standard_id) \
            if parent.parent_standard_id is not None else None


def metadata_schema_unique_standard_organization_infrastructure(key, data, errors, context):
    """
    Checks the uniqueness of metadata_standard-organization-infrastructure for a metadata schema.
    For use with the '__after' schema key; group names should already have been converted to group ids.
    """
    metadata_standard_id = data.get(key[:-1] + ('metadata_standard_id',))
    organization_id = data.get(key[:-1] + ('organization_id',))
    infrastructure_id = data.get(key[:-1] + ('infrastructure_id',))

    id_ = _convert_missing(data.get(key[:-1] + ('id',)))
    obj = ckanext_model.MetadataSchema.get(id_) if id_ else None

    # if we're updating, missing value(s) in the input data imply a partial update, so get the
    # existing value(s) and check that the updated key does not violate uniqueness
    metadata_standard_id = _convert_missing(metadata_standard_id, obj.metadata_standard_id if obj else None)
    organization_id = _convert_missing(organization_id, obj.organization_id if obj else None)
    infrastructure_id = _convert_missing(infrastructure_id, obj.infrastructure_id if obj else None)

    metadata_schema = ckanext_model.MetadataSchema.lookup(metadata_standard_id, organization_id, infrastructure_id)
    if metadata_schema and metadata_schema.state != 'deleted' and metadata_schema.id != id_:
        raise tk.Invalid(_("Unique constraint violation: %s") % '(metadata_standard_id, organization_id, infrastructure_id)')


def metadata_schema_check_organization_infrastructure(key, data, errors, context):
    """
    Checks that only one of organization and infrastructure have been set for a metadata schema.
    For use with the '__after' schema key; group names should already have been converted to group ids.
    """
    organization_id = data.get(key[:-1] + ('organization_id',))
    infrastructure_id = data.get(key[:-1] + ('infrastructure_id',))

    id_ = _convert_missing(data.get(key[:-1] + ('id',)))
    obj = ckanext_model.MetadataSchema.get(id_) if id_ else None

    # if we're updating, missing value(s) in the input data imply a partial update, so get the
    # existing value(s) and check that the updated combination does not violate the check constraint
    organization_id = _convert_missing(organization_id, obj.organization_id if obj else None)
    infrastructure_id = _convert_missing(infrastructure_id, obj.infrastructure_id if obj else None)

    if organization_id and infrastructure_id:
        raise tk.Invalid(_("A metadata schema may be associated with either an organization or an "
                           "infrastructure but not both."))


def metadata_standard_name_generator(key, data, errors, context):
    """
    Generates the name for a metadata standard if not supplied. For use with the '__after' schema key.
    """
    name = _convert_missing(data.get(key[:-1] + ('name',)))
    if not name:
        id_ = _convert_missing(data.get(key[:-1] + ('id',)))
        if id_:
            metadata_standard = ckanext_model.MetadataStandard.get(id_)
            if metadata_standard:
                # for updates we want to re-generate the name only if it was previously auto-generated
                autoname = _generate_name(metadata_standard.standard_name, metadata_standard.standard_version)
                if metadata_standard.name != autoname:
                    return

        standard_name = _convert_missing(data.get(key[:-1] + ('standard_name',)), '')
        standard_version = _convert_missing(data.get(key[:-1] + ('standard_version',)), '')
        name = _generate_name(standard_name, standard_version)
        data[key[:-1] + ('name',)] = name


def metadata_schema_name_generator(key, data, errors, context):
    """
    Generates the name for a metadata schema if not supplied. For use with the '__after' schema key.
    """
    model = context['model']

    def get_name_components(metadata_standard_id, organization_id, infrastructure_id):
        metadata_standard = ckanext_model.MetadataStandard.get(metadata_standard_id)
        organization = model.Group.get(organization_id) if organization_id else None
        infrastructure = model.Group.get(infrastructure_id) if infrastructure_id else None

        metadata_standard_name = metadata_standard.name if metadata_standard else ''
        organization_name = organization.name if organization else ''
        infrastructure_name = infrastructure.name if infrastructure else ''

        return metadata_standard_name, organization_name, infrastructure_name

    name = _convert_missing(data.get(key[:-1] + ('name',)))
    if not name:
        id_ = _convert_missing(data.get(key[:-1] + ('id',)))
        if id_:
            metadata_schema = ckanext_model.MetadataSchema.get(id_)
            if metadata_schema:
                # for updates we want to re-generate the name only if it was previously auto-generated
                metadata_standard_name, organization_name, infrastructure_name = get_name_components(
                    metadata_schema.metadata_standard_id,
                    metadata_schema.organization_id,
                    metadata_schema.infrastructure_id
                )
                autoname = _generate_name(metadata_standard_name, organization_name, infrastructure_name)
                if metadata_schema.name != autoname:
                    return

        metadata_standard_name, organization_name, infrastructure_name = get_name_components(
            _convert_missing(data.get(key[:-1] + ('metadata_standard_id',))),
            _convert_missing(data.get(key[:-1] + ('organization_id',))),
            _convert_missing(data.get(key[:-1] + ('infrastructure_id',)))
        )
        name = _generate_name(metadata_standard_name, organization_name, infrastructure_name)
        data[key[:-1] + ('name',)] = name


def workflow_revert_state_validator(key, data, errors, context):
    """
    Checks that the revert state specified in the data would not cause
    a loop in the workflow state graph.
    """
    workflow_state = context.get('workflow_state')
    if not workflow_state:
        # it's a new state - no other state reverts to this one, and no transitions
        # involving this state exist, yet
        return

    revert_state_id = _convert_missing(data.get(key[:-1] + ('revert_state_id',)))
    if not revert_state_id:
        return

    if revert_state_id == workflow_state.id:
        raise tk.Invalid(_("A workflow state cannot revert to itself"))

    if ckanext_model.WorkflowState.revert_path_exists(revert_state_id, workflow_state.id):
        raise tk.Invalid(_("Revert loop in workflow state graph"))

    if ckanext_model.WorkflowTransition.path_exists(workflow_state.id, revert_state_id):
        raise tk.Invalid(_("Forward revert in workflow state graph"))


def workflow_transition_check(key, data, errors, context):
    """
    Checks that the from and to states are not the same. For use with the '__after' schema key.
    """
    from_state_id = data.get(key[:-1] + ('from_state_id',))
    to_state_id = data.get(key[:-1] + ('to_state_id',))

    if from_state_id == to_state_id:
        raise tk.Invalid(_("The from- and to-state of a workflow transition cannot be the same."))


def workflow_transition_unique(key, data, errors, context):
    """
    For use with the '__after' schema key.
    """
    id_ = data.get(key[:-1] + ('id',))
    from_state_id = _convert_missing(data.get(key[:-1] + ('from_state_id',)))
    to_state_id = _convert_missing(data.get(key[:-1] + ('to_state_id',)))

    workflow_transition = ckanext_model.WorkflowTransition.lookup(from_state_id, to_state_id)
    if workflow_transition and workflow_transition.state != 'deleted' and workflow_transition.id != id_:
        raise tk.Invalid(_("Unique constraint violation: %s") % '(from_state_id, to_state_id)')


def workflow_transition_graph_validator(key, data, errors, context):
    """
    Checks that the specified workflow transition would not cause
    a loop in the workflow state graph.
    """
    from_state_id = _convert_missing(data.get(key[:-1] + ('from_state_id',)))
    to_state_id = _convert_missing(data.get(key[:-1] + ('to_state_id',)))
    
    if ckanext_model.WorkflowTransition.path_exists(to_state_id, from_state_id):
        raise tk.Invalid(_("Transition loop in workflow state graph"))

    if ckanext_model.WorkflowState.revert_path_exists(from_state_id, to_state_id):
        raise tk.Invalid(_("Backward transition in workflow state graph"))


def metadata_template_json_path_validator(key, data, errors, context):
    """
    Checks that the supplied JSON path is valid for the metadata template JSON of
    the supplied metadata standard. For use with the '__after' schema key in the
    metadata_json_attr_map_* schemas.
    """
    json_path = _convert_missing(data.get(key[:-1] + ('json_path',)), '')
    metadata_standard_id = _convert_missing(data.get(key[:-1] + ('metadata_standard_id',)))
    if not metadata_standard_id:
        id_ = data.get(key[:-1] + ('id',))
        mapping_obj = ckanext_model.MetadataJSONAttrMap.get(id_)
        if mapping_obj:
            metadata_standard_id = mapping_obj.metadata_standard_id

    metadata_standard = ckanext_model.MetadataStandard.get(metadata_standard_id)
    if metadata_standard:
        metadata_template_dict = json.loads(metadata_standard.metadata_template_json)
        try:
            jsonpointer.resolve_pointer(metadata_template_dict, json_path)
        except jsonpointer.JsonPointerException:
            raise tk.Invalid(_("The supplied JSON path is not valid for the metadata template of the supplied metadata standard"))


def metadata_json_attr_map_unique(key, data, errors, context):
    """
    Checks that for the given metadata standard, the JSON path and record attribute values
    are not already present in some other mapping object(s). For use with the '__after' schema key.
    """
    id_ = data.get(key[:-1] + ('id',))
    json_path = _convert_missing(data.get(key[:-1] + ('json_path',)))
    record_attr = _convert_missing(data.get(key[:-1] + ('record_attr',)))
    metadata_standard_id = _convert_missing(data.get(key[:-1] + ('metadata_standard_id',)))
    if not metadata_standard_id:
        mapping_obj = ckanext_model.MetadataJSONAttrMap.get(id_)
        if mapping_obj:
            metadata_standard_id = mapping_obj.metadata_standard_id

    mapping_obj = ckanext_model.MetadataJSONAttrMap.lookup_by_json_path(metadata_standard_id, json_path)
    if mapping_obj and mapping_obj.state != 'deleted' and mapping_obj.id != id_:
        errors.setdefault(key[:-1] + ('json_path',), [])
        errors[key[:-1] + ('json_path',)].append(_("Unique constraint violation: %s") % '(metadata_standard_id, json_path)')

    mapping_obj = ckanext_model.MetadataJSONAttrMap.lookup_by_record_attr(metadata_standard_id, record_attr)
    if mapping_obj and mapping_obj.state != 'deleted' and mapping_obj.id != id_:
        errors.setdefault(key[:-1] + ('record_attr',), [])
        errors[key[:-1] + ('record_attr',)].append(_("Unique constraint violation: %s") % '(metadata_standard_id, record_attr)')

# endregion
