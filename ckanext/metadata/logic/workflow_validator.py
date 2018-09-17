# encoding: utf-8

from ckanext.metadata.logic.json_validator import JSONValidator
from ckanext.metadata.logic.json_validator_functions import (
    objectid_validator,
    role_validator,
    unique_objects_validator,
    url_test_validator,
)


class WorkflowValidator(JSONValidator):
    """
    JSON Schema validator for workflow state transitions.
    """

    @classmethod
    def _validators(cls):
        return {
            'objectid': objectid_validator,
            'role': role_validator,
            'uniqueObjects': unique_objects_validator,
            'urlTest': url_test_validator,
        }

    @classmethod
    def _formats(cls):
        return [
            'url',
            'date',
        ]
