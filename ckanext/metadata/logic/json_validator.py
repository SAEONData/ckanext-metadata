# encoding: utf-8

import logging
import jsonschema
import jsonschema.validators
import re
import ast
from jsonpointer import resolve_pointer, JsonPointerException
from collections import deque

import ckan.plugins.toolkit as tk

log = logging.getLogger(__name__)


def add_post_validation_task(self, action_func, data_dict, error_path):
    self.tasks += [{
        'action_func': action_func,
        'data_dict': data_dict,
        'error_path': error_path,
    }]


class JSONValidator(object):
    """
    Encapsulates the JSON Schema validation capabilities supported by the jsonschema library.
    """

    def __init__(self, schema, object_id=None, context=None):
        """
        Check the given schema and create a validator for it.
        :param schema: JSON schema dictionary
        :type schema: dict
        :param object_id: the id of the object that this validator relates to (optional)
        :type object_id: string
        :param context: caller's context (optional)
        :type context: dict
        """
        jsonschema_validator_cls = jsonschema.validators.validator_for(schema)
        jsonschema_validator_cls.check_schema(schema)
        jsonschema_validator_cls.VALIDATORS.update(self._validators())
        jsonschema_validator_cls.add_post_validation_task = add_post_validation_task

        formats = self._formats()
        if 'uri' in formats:
            try:
                import rfc3987
            except ImportError:
                raise ImportError("Module rfc3987 is required for uri format checking")

        self.jsonschema_validator = jsonschema_validator_cls(
            schema, format_checker=jsonschema.FormatChecker(formats))

        self.jsonschema_validator.object_id = object_id
        self.jsonschema_validator.context = context or {}
        self.jsonschema_validator.tasks = []

    @classmethod
    def _validators(cls):
        """
        Define keyword-validator mappings for any new schema keywords supported by this class.
        :return: dict of {string: function}
        """
        return {}

    @classmethod
    def _formats(cls):
        """
        Define the format values supported by this class for the "format" keyword.
        :return: list of strings
        """
        return []

    @classmethod
    def check_schema(cls, schema):
        """
        Check that the given dictionary is a valid JSON schema.
        :param schema: dict
        """
        jsonschema_validator_cls = jsonschema.validators.validator_for(schema)
        jsonschema_validator_cls.check_schema(schema)

    def validate(self, instance):
        """
        Validate a JSON metadata instance.
        :param instance: metadata dict
        :return: error dict
        """

        def clear_empties(node):
            """
            Recursively remove empty strings, lists and dicts from the instance tree.
            """
            if type(node) is dict:
                # iterate over a *copy* of the dict's keys, as we are deleting keys during iteration
                for element in node.keys():
                    clear_empties(node[element])
                    if type(node[element]) in (str, unicode, list, dict, type(None)) and not node[element]:
                        del node[element]
            elif type(node) is list:
                # iterate over a *copy* of the list, as we are deleting elements during iteration
                for element in list(node):
                    clear_empties(element)
                    if type(element) in (str, unicode, list, dict, type(None)) and not element:
                        node.remove(element)

        def add_error(node, path, message):
            """
            Add an error message to the error tree.
            """
            index = str(path.popleft()) if path else '__root'

            if index not in node:
                node[index] = [] if not path else {}

            if path:
                add_error(node[index], path, message)
            elif type(node[index]) is dict:
                # we'll arrive here if we previously added an error at a leaf node and subsequently
                # want to add an error at a parent/ancestor of that leaf; we must add a "dummy" key
                # for the error message list
                add_error(node[index], deque(('_',)), message)
            else:
                node[index] += [message]

        self.jsonschema_validator.root_instance = instance.copy()
        errors = {}
        clear_empties(instance)

        for error in self.jsonschema_validator.iter_errors(instance):

            if error.schema_path[-1] == 'required':
                # put required errors under the required keys themselves
                match = re.match(r'(?P<key>.+) is a required property', error.message)
                assert match is not None, "Unexpected message for 'required' property"
                required_key = ast.literal_eval(match.group('key'))
                error.path.append(required_key)

            elif error.schema_path[-1] == 'not' and error.validator_value == {}:
                error.message = 'This key may not be present in the dictionary'

            elif error.schema_path[-1] == 'minItems':
                error.path.append('__minItems')
                error.message = 'Array has too few items'

            elif error.schema_path[-1] == 'uniqueItems':
                error.path.append('__uniqueItems')
                error.message = 'Array has non-unique items'

            elif error.schema_path[-1] == 'uniqueObjects':
                error.path.append('__uniqueObjects')
                error.message = 'Array has non-unique objects'

            elif error.schema_path[-1] == 'contains':
                error.path.append('__contains')
                error.message = 'Array does not contain a required item'

            elif error.schema_path[-1] == 'task':
                error.path.append('__task')

            elif error.schema_path[-1] == 'itemCardinality':
                error.path.append('__itemCardinality')

            elif error.schema_path[-1] == 'maxProperties':
                error.path.append('__maxProperties')
                if error.schema.get('maxProperties') == 0:
                    error.message = 'Object must be empty'
                else:
                    error.message = 'Object has too many properties'

            add_error(errors, error.path, error.message)

        for task in self.jsonschema_validator.tasks:
            error_path = deque(task['error_path'].split('/'))
            error_path.popleft()  # remove the leading empty string
            error_path.append('__task')
            try:
                # if error_path resolves to a location in the errors dict, we don't want to process the task
                resolve_pointer(errors, task['error_path'])
                add_error(errors, error_path, 'Task not executed due to other errors in the instance')
                continue
            except JsonPointerException:
                # error_path does not resolve, therefore we have no error and can process the task
                pass

            try:
                context = self.jsonschema_validator.context.copy()
                context['defer_commit'] = True
                task['action_func'](context, task['data_dict'])
            except tk.ValidationError, e:
                message = e.error_dict.get('message') or e.error_dict
                add_error(errors, error_path, message)
            except Exception, e:
                add_error(errors, error_path, e.message)

        return errors
