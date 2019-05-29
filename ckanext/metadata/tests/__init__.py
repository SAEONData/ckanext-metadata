# encoding: utf-8

import uuid
import re
import json
from paste.deploy.converters import asbool
import pkg_resources
from collections import deque
import traceback
from nose.tools import nottest

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import FunctionalTestBase, call_action, reset_db
import ckan.plugins.toolkit as tk
import ckan.model as ckan_model
import ckanext.metadata.model.setup as ckanext_setup
from ckanext.metadata import model as ckanext_model
from ckanext.jsonpatch.model.jsonpatch import JSONPatch
import ckanext.jsonpatch.model.setup as jsonpatch_setup

_model_map = {
    'organization': ckan_model.Group,
    'infrastructure': ckan_model.Group,
    'metadata_collection': ckan_model.Group,
    'metadata_record': ckan_model.Package,
    'metadata_schema': ckanext_model.MetadataSchema,
    'metadata_standard': ckanext_model.MetadataStandard,
    'workflow_state': ckanext_model.WorkflowState,
    'workflow_transition': ckanext_model.WorkflowTransition,
    'workflow_annotation': ckanext_model.WorkflowAnnotation,
    'jsonpatch': JSONPatch,
    'metadata_json_attr_map': ckanext_model.MetadataJSONAttrMap,
}


def load_example(filename):
    return pkg_resources.resource_string(__name__, '../../../examples/' + filename)


def make_uuid():
    return unicode(uuid.uuid4())


def generate_name(*strings):
    """
    Converts the given string(s) into a form suitable for an object name.
    """
    strings = list(strings)
    while '' in strings:
        strings.remove('')
    text = '-'.join(strings)
    return re.sub(r'[^a-z0-9_-]+', '-', text.lower())


def assert_object_matches_dict(object_, dict_, json_values=()):
    """
    Check that the object has all the items in the dict.
    """
    for key in dict_.keys():
        # any kind of empty matches any kind of empty
        dict_value = dict_[key] or None
        object_value = getattr(object_, key) or None
        if key in json_values:
            if isinstance(dict_value, basestring):
                dict_value = json.loads(dict_value)
            object_value = json.loads(object_value)
        assert dict_value == object_value


def assert_package_has_extra(package_id, key, value, state='active', is_json=False):
    """
    Check that a package has the specified extra key-value pair.
    """
    extra = ckan_model.Session.query(ckan_model.PackageExtra) \
        .filter(ckan_model.PackageExtra.package_id == package_id) \
        .filter(ckan_model.PackageExtra.key == key) \
        .first()

    assert extra
    assert extra.state == state
    if is_json:
        if isinstance(value, basestring):
            value = json.loads(value)
        extra_value = json.loads(extra.value)
    elif type(value) is bool:
        extra_value = asbool(extra.value)
    else:
        extra_value = extra.value
    assert extra_value == value


def assert_package_has_attribute(package_id, attr, value):
    """
    Check that a package has the specified native attribute value.
    """
    obj = ckan_model.Package.get(package_id)
    assert obj
    assert hasattr(obj, attr)
    assert getattr(obj, attr) == value


def assert_group_has_extra(group_id, key, value, state='active'):
    """
    Check that a group has the specified extra key-value pair.
    """
    extra = ckan_model.Session.query(ckan_model.GroupExtra) \
        .filter(ckan_model.GroupExtra.group_id == group_id) \
        .filter(ckan_model.GroupExtra.key == key) \
        .first()

    assert extra
    assert extra.value == value
    assert extra.state == state


def assert_group_has_member(group_id, object_id, object_table, capacity='public', state='active'):
    """
    Check that a group has the specified object as a member.
    """
    member = ckan_model.Session.query(ckan_model.Member) \
        .filter(ckan_model.Member.group_id == group_id) \
        .filter(ckan_model.Member.table_id == object_id) \
        .filter(ckan_model.Member.table_name == object_table) \
        .first()

    assert member
    assert member.capacity == capacity
    assert member.state == state


def assert_metadata_record_has_validation_schemas(metadata_record_id, *metadata_schema_names):
    """
    Check that the given record has the expected set of validation schemas.
    """
    validation_schema_list = call_action('metadata_record_validation_schema_list', id=metadata_record_id)
    assert set(validation_schema_list) == set(metadata_schema_names)


def assert_metadata_schema_has_dependent_records(metadata_schema_id, *metadata_record_ids):
    """
    Check that the given schema has the expected set of dependent records.
    """
    dependent_record_list = call_action('metadata_schema_dependent_record_list', id=metadata_schema_id)
    assert set(dependent_record_list) == set(metadata_record_ids)


def assert_error(error_dict, key, pattern):
    """
    Check that the error dictionary contains the given key with the corresponding error message regex.
    Key may be in JSON pointer format (e.g. 'infrastructures/0/id').
    """
    def has_error(node, path):
        if path:
            index = path.popleft()
            if type(node) is list:
                index = int(index)
            return has_error(node[index], path)
        elif type(node) is list:
            return next((True for msg in node if re.search(pattern, msg) is not None), False)
        elif isinstance(node, basestring):
            return re.search(pattern, node) is not None
        return False

    error_path = deque(key.split('/')) if key else None
    try:
        assert has_error(error_dict, error_path)
    except KeyError:
        assert False, "'{}' not found in error dict".format(key)


class ActionTestBase(FunctionalTestBase):

    # moved to test.ini, so that plugins are also loaded by any spawned background workers
    # _load_plugins = 'metadata_framework', 'jsonpatch'

    @classmethod
    def setup_class(cls):
        print "\n===", cls.__name__, "==="
        super(ActionTestBase, cls).setup_class()
        ckanext_setup.init_tables()
        jsonpatch_setup.init_tables()

    @classmethod
    def teardown_class(cls):
        super(ActionTestBase, cls).teardown_class()
        # we just want to ensure that after the very last class teardown, we don't leave
        # anything in the DB that might cause FK violations when initializing the first
        # set of tests in another extension
        reset_db()

    def setup(self):
        super(ActionTestBase, self).setup()
        # hack because CKAN doesn't clean up the session properly
        if hasattr(ckan_model.Session, 'revision'):
            delattr(ckan_model.Session, 'revision')
        self.normal_user = ckan_factories.User()
        self.sysadmin_user = ckan_factories.Sysadmin()

    @nottest
    def test_action(self, action_name, should_error=False, exception_class=tk.ValidationError,
                    sysadmin=False, check_auth=False, **kwargs):
        """
        Test an API action.
        :param action_name: action function name, e.g. 'metadata_record_create'
        :param should_error: True if this test should raise an exception, False otherwise
        :param exception_class: the type of exception to be expected if should_error is True
        :param sysadmin: True to execute the action as a sysadmin, False to run it as a normal user
        :param check_auth: True to check whether the user is authorized to perform the action,
            False to ignore the auth check
        :param kwargs: additional args to pass to the action function
        :return: tuple(result dict, result obj)
        """
        model, method = action_name.rsplit('_', 1)
        model_class = _model_map.get(model)
        user = self.sysadmin_user if sysadmin else self.normal_user
        context = {
            'user': user['name'],
            'ignore_auth': not check_auth,
        }

        obj = None
        try:
            result = call_action(action_name, context, **kwargs)
        except exception_class, e:
            if exception_class is tk.ValidationError:
                result = e.error_dict
            else:
                result = e.message
        except Exception, e:
            traceback.print_exc()
            assert False, "Unexpected exception %s: %s" % (type(e), e)
        else:
            if should_error:
                assert False, str(exception_class) + " was not raised"
        finally:
            # close the session to ensure that we're not just getting the obj from
            # memory but are reloading it from the DB
            ckan_model.Session.close_all()

        if not should_error and model_class is not None:
            if method in ('create', 'update', 'show'):
                assert 'id' in result
                obj = model_class.get(result['id'])
                assert type(obj) is model_class
                assert obj.state == 'active'
            elif method == 'delete':
                obj = model_class.get(kwargs['id'])
                assert obj.state == 'deleted'
            elif 'id' in kwargs:
                obj = model_class.get(kwargs['id'])

        return result, obj

    def assert_validate_activity_logged(self, metadata_record_id, *validation_schemas, **validation_errors):
        """
        :param validation_schemas: iterable of metadata schema dictionaries
        :param validation_errors: dictionary mapping metadata schema keys to expected error patterns (regex's)
        """
        activity_dict = call_action('metadata_record_validation_activity_show', id=metadata_record_id)
        assert activity_dict['user_id'] == self.normal_user['id']
        assert activity_dict['object_id'] == metadata_record_id
        assert activity_dict['activity_type'] == 'metadata validation'
        assert activity_dict['data']['action'] == 'metadata_record_validate'
        logged_results = activity_dict['data']['results']
        assert len(logged_results) == len(validation_schemas)
        logged_errors = {}
        for validation_schema in validation_schemas:
            logged_result = next((result for result in logged_results
                                  if result['metadata_schema_id'] == validation_schema['id']), None)
            assert logged_result
            logged_errors.update(logged_result['errors'])
        assert len(logged_errors) == len(validation_errors)
        for error_key, error_pattern in validation_errors.items():
            assert_error(logged_errors, error_key, error_pattern)

    def assert_invalidate_activity_logged(self, metadata_record_id, trigger_action, trigger_object):
        activity_dict = call_action('metadata_record_validation_activity_show', id=metadata_record_id)
        assert activity_dict['user_id'] == self.normal_user['id']
        assert activity_dict['object_id'] == metadata_record_id
        assert activity_dict['activity_type'] == 'metadata validation'
        assert activity_dict['data'] == {
            'action': 'metadata_record_invalidate',
            'trigger_action': trigger_action,
            'trigger_object_id': trigger_object.id if trigger_object else None,
        }

    def assert_workflow_activity_logged(self, action_suffix, metadata_record_id, workflow_state_id,
                                        *jsonpatch_ids, **workflow_errors):
        """
        :param action_suffix: 'transition' | 'revert' | 'override'
        :param workflow_errors: dictionary mapping workflow annotation (flattened) keys to expected error patterns
        """
        activity_dict = call_action('metadata_record_workflow_activity_show', id=metadata_record_id)
        assert activity_dict['user_id'] == self.normal_user['id']
        assert activity_dict['object_id'] == metadata_record_id
        assert activity_dict['activity_type'] == 'metadata workflow'
        assert activity_dict['data']['action'] == 'metadata_record_workflow_state_' + action_suffix
        assert activity_dict['data']['workflow_state_id'] == workflow_state_id
        assert activity_dict['data'].get('jsonpatch_ids', []) == list(jsonpatch_ids)
        logged_errors = activity_dict['data'].get('errors', {})
        for error_key, error_pattern in workflow_errors.items():
            assert_error(logged_errors, error_key, error_pattern)
