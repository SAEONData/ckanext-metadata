# encoding: utf-8

# Permissible date/time values: http://www.w3.org/TR/NOTE-datetime
# Permissible date/time ranges: http://www.ukoln.ac.uk/metadata/dcmi/collection-RKMS-ISO8601

import logging
import jsonschema
import jsonschema.validators
from datetime import datetime
import re
import urlparse

import ckan.plugins.toolkit as tk
from ckan.common import _

log = logging.getLogger(__name__)

DOI_RE = re.compile(r'^10\.\d+(\.\d+)*/.+$')
TIME_RE = re.compile(r'^(?P<h>\d{2}):(?P<m>\d{2})(:(?P<s>\d{2})(\.\d+)?)?(Z|[+-](?P<tzh>\d{2}):(?P<tzm>\d{2}))$')
GEO_POINT_RE = re.compile(r'^(?P<lat>[+-]?\d+(\.\d+)?)\s+(?P<lon>[+-]?\d+(\.\d+)?)$')
GEO_BOX_RE = re.compile(r'^(?P<lat1>[+-]?\d+(\.\d+)?)\s+(?P<lon1>[+-]?\d+(\.\d+)?)\s+(?P<lat2>[+-]?\d+(\.\d+)?)\s+(?P<lon2>[+-]?\d+(\.\d+)?)$')

checks_format = jsonschema.FormatChecker.cls_checks


class JSONValidator(object):

    # TODO: move some of the stuff in here down to MetadataValidator / WorkflowValidator

    def __init__(self, schema):
        """
        Check the given schema and create a validator for it.
        :param schema: JSON schema dict
        """
        jsonschema_validator_cls = jsonschema.validators.validator_for(schema)
        jsonschema_validator_cls.check_schema(schema)
        jsonschema_validator_cls.VALIDATORS.update({
            'vocabulary': vocabulary_validator,
        })

        try:
            import rfc3987
        except ImportError:
            raise ImportError("Module rfc3987 is required for uri format checking")

        format_checker = jsonschema.FormatChecker(formats=[
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
            'geolocation-point',
            'geolocation-box',
        ])

        self.jsonschema_validator = jsonschema_validator_cls(schema, format_checker=format_checker)

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


def vocabulary_validator(validator, vocabulary_name, instance, schema):
    if validator.is_type(instance, 'string'):
        try:
            vocabulary = tk.get_action('vocabulary_show')(data_dict={'id': vocabulary_name})
            tags = [tag['name'] for tag in vocabulary['tags']]
            if instance not in tags:
                yield jsonschema.ValidationError(_('Tag not found in vocabulary'))
        except tk.ObjectNotFound:
            yield jsonschema.ValidationError("%s: %s '%s'" % (_('Not found'), _('Vocabulary'), vocabulary_name))


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


@checks_format('geolocation-point')
def is_geolocation_point(instance):
    if not isinstance(instance, basestring):
        return True
    match = re.match(GEO_POINT_RE, instance)
    if match:
        lat, lon = match.group('lat', 'lon')
        if (
                 -90 <= float(lat) <= 90 and
                -180 <= float(lon) <= 180
        ):
            return True
    return False


@checks_format('geolocation-box')
def is_geolocation_box(instance):
    if not isinstance(instance, basestring):
        return True
    match = re.match(GEO_BOX_RE, instance)
    if match:
        lat1, lon1, lat2, lon2 = match.group('lat1', 'lon1', 'lat2', 'lon2')
        if (
                 -90 <= float(lat1) <= 90 and
                -180 <= float(lon1) <= 180 and
                 -90 <= float(lat2) <= 90 and
                -180 <= float(lon2) <= 180 and
                float(lat1) <= float(lat2) and
                float(lon1) <= float(lon2)
        ):
            return True
    return False