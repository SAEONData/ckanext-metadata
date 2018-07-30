# encoding: utf-8

from ckanext.metadata.logic.json_validator import JSONValidator


class WorkflowValidator(JSONValidator):
    """
    JSON Schema validator for workflow state transitions.
    """

    @classmethod
    def _validators(cls):
        return {}

    @classmethod
    def _formats(cls):
        return [
            'url',
        ]
