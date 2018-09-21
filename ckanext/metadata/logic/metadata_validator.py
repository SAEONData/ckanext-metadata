# encoding: utf-8

from ckanext.metadata.logic.json_validator import JSONValidator
from ckanext.metadata.logic.json_validator_functions import vocabulary_validator, task_validator, item_cardinality_validator


class MetadataValidator(JSONValidator):
    """
    JSON Schema validator for metadata.

    Format checkers based on the DataCite 3.1 specification.
    For permissible date/time values, see: http://www.w3.org/TR/NOTE-datetime
    For permissible date/time ranges, see: http://www.ukoln.ac.uk/metadata/dcmi/collection-RKMS-ISO8601
    """

    @classmethod
    def _validators(cls):
        return {
            'vocabulary': vocabulary_validator,
            'itemCardinality': item_cardinality_validator,
        }

    @classmethod
    def _formats(cls):
        return [
            'doi',
            'uri',  # implemented in jsonschema._format.py; requires rfc3987
            'url',
            'year',
            'yearmonth',
            'date',
            'datetime',
            'year-range',
            'yearmonth-range',
            'date-range',
            'datetime-range',
            'longitude',
            'latitude',
        ]
