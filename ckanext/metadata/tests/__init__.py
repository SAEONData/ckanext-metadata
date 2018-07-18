# encoding: utf-8

import uuid
import re
import json
from paste.deploy.converters import asbool
import pkg_resources

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import FunctionalTestBase, call_action
import ckan.plugins.toolkit as tk
import ckan.model as ckan_model
import ckanext.metadata.model.setup as ckanext_setup
from ckanext.metadata import model as ckanext_model

_model_map = {
    'organization': ckan_model.Group,
    'infrastructure': ckan_model.Group,
    'metadata_collection': ckan_model.Group,
    'metadata_record': ckan_model.Package,
    'metadata_model': ckanext_model.MetadataModel,
    'metadata_schema': ckanext_model.MetadataSchema,
    'workflow_state': ckanext_model.WorkflowState,
    'workflow_transition': ckanext_model.WorkflowTransition,
    'workflow_metric': ckanext_model.WorkflowMetric,
    'workflow_rule': ckanext_model.WorkflowRule,
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
    text = '_'.join(strings)
    return re.sub('[^a-z0-9_\-]+', '-', text.lower())


def assert_object_matches_dict(object_, dict_):
    """
    Check that the object has all the items in the dict.
    """
    for key in dict_.keys():
        # any kind of empty matches any kind of empty
        dict_value = dict_[key] or None
        object_value = getattr(object_, key) or None
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


def assert_error(error_dict, key, pattern):
    """
    Check that the error dictionary contains the given key with the corresponding error message regex.
    """
    errors = error_dict.get(key)
    if type(errors) is list:
        assert next((True for error in errors if re.search(pattern, error) is not None), False)
    elif isinstance(errors, basestring):
        assert re.search(pattern, errors) is not None
    else:
        assert False


class ActionTestBase(FunctionalTestBase):

    _load_plugins = 'metadata',

    @classmethod
    def setup_class(cls):
        print "\n===", cls.__name__, "==="
        super(ActionTestBase, cls).setup_class()
        ckanext_setup.init_tables()

    def setup(self):
        super(ActionTestBase, self).setup()
        # hack because CKAN doesn't clean up the session properly
        if hasattr(ckan_model.Session, 'revision'):
            delattr(ckan_model.Session, 'revision')
        self.normal_user = ckan_factories.User()
        self.sysadmin_user = ckan_factories.Sysadmin()

    def _test_action(self, action_name, should_error=False, exception_class=tk.ValidationError,
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
            assert False, "Unexpected exception %s: %s" % (type(e), e)
        else:
            if should_error:
                assert False, str(exception_class) + " was not raised"
        finally:
            # close the session to ensure that we're not just getting the obj from
            # memory but are reloading it from the DB
            ckan_model.Session.close_all()

        if not should_error:
            model_class = _model_map[model]
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

    def _assert_validate_activity_logged(self, metadata_record_id, *validation_models, **validation_errors):
        """
        :param validation_models: iterable of metadata model dictionaries
        :param validation_errors: dictionary mapping metadata model keys to expected error patterns (regex's)
        """
        activity_dict = call_action('metadata_record_validation_activity_show', id=metadata_record_id)
        assert activity_dict['user_id'] == self.normal_user['id']
        assert activity_dict['object_id'] == metadata_record_id
        assert activity_dict['activity_type'] == 'metadata validation'
        assert activity_dict['data']['action'] == 'metadata_record_validate'
        logged_results = activity_dict['data']['results']
        assert len(logged_results) == len(validation_models)
        logged_errors = {}
        for validation_model in validation_models:
            logged_result = next((result for result in logged_results
                                  if result['metadata_model_id'] == validation_model['id']), None)
            assert logged_result
            assert logged_result['metadata_model_revision_id'] == validation_model['revision_id']
            logged_errors.update(logged_result['errors'])
        assert len(logged_errors) == len(validation_errors)
        for error_key, error_pattern in validation_errors.items():
            assert_error(logged_errors, error_key, error_pattern)

    def _assert_invalidate_activity_logged(self, metadata_record_id, trigger_action, trigger_object):
        activity_dict = call_action('metadata_record_validation_activity_show', id=metadata_record_id)
        assert activity_dict['user_id'] == self.normal_user['id']
        assert activity_dict['object_id'] == metadata_record_id
        assert activity_dict['activity_type'] == 'metadata validation'
        assert activity_dict['data'] == {
            'action': 'metadata_record_invalidate',
            'trigger_action': trigger_action,
            'trigger_object_id': trigger_object.id if trigger_object else None,
            'trigger_revision_id': trigger_object.revision_id if trigger_object else None,
        }

    def _assert_metadata_record_has_validation_models(self, metadata_record_id, *metadata_model_names):
        """
        Check that the given record has the expected set of validation models.
        """
        validation_model_list = call_action('metadata_record_validation_model_list', id=metadata_record_id)
        assert set(validation_model_list) == set(metadata_model_names)

    def _assert_metadata_model_has_dependent_records(self, metadata_model_id, *metadata_record_ids):
        """
        Check that the given model has the expected set of dependent records.
        """
        dependent_record_list = call_action('metadata_model_dependent_record_list', id=metadata_model_id)
        assert set(dependent_record_list) == set(metadata_record_ids)
