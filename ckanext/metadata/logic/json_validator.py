# encoding: utf-8

import logging
import jsonschema
import jsonschema.validators

log = logging.getLogger(__name__)


class JSONValidator(object):
    """
    Encapsulates the JSON Schema validation capabilities supported by the jsonschema library.
    """

    def __init__(self, schema):
        """
        Check the given schema and create a validator for it.
        :param schema: JSON schema dict
        """
        jsonschema_validator_cls = jsonschema.validators.validator_for(schema)
        jsonschema_validator_cls.check_schema(schema)
        jsonschema_validator_cls.VALIDATORS.update(self._validators())

        formats = self._formats()
        if 'uri' in formats:
            try:
                import rfc3987
            except ImportError:
                raise ImportError("Module rfc3987 is required for uri format checking")

        self.jsonschema_validator = jsonschema_validator_cls(
            schema, format_checker=jsonschema.FormatChecker(formats))

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
            Recursively remove empty elements from the instance tree.
            """
            if type(node) is dict:
                # iterate over a copy of the dict's keys, as we are deleting keys during iteration
                for element in node.keys():
                    clear_empties(node[element])
                    if not node[element]:
                        del node[element]
            elif type(node) is list:
                # iterate over a copy of the list, as we are deleting elements during iteration
                for element in list(node):
                    clear_empties(element)
                    if not element:
                        node.remove(element)

        def add_error(node, path, message):
            """
            Add an error message to the error tree.
            """
            if path:
                element = path.popleft()
            else:
                element = u'__global'

            if path:
                if element not in node:
                    node[element] = {}
                add_error(node[element], path, message)
            else:
                if element not in node:
                    node[element] = []
                node[element] += [message]

        errors = {}
        clear_empties(instance)
        for error in self.jsonschema_validator.iter_errors(instance):
            add_error(errors, error.path, error.message)

        return errors
