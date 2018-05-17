# encoding: utf-8

import uuid
import re
import json

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import FunctionalTestBase, call_action
import ckan.plugins.toolkit as tk
import ckan.model as ckan_model
import ckanext.metadata.model.setup as ckanext_setup


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
    else:
        extra_value = extra.value
    assert extra_value == value


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
    elif type(errors) is unicode:
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

    def _test_action(self, method, model_name, model_class=None, exception_class=None, sysadmin=False, check_auth=False, **kwargs):

        method_name = model_name + '_' + method
        user = self.sysadmin_user if sysadmin else self.normal_user
        context = {
            'user': user['name'],
            'ignore_auth': not check_auth,
        }

        obj = None
        try:
            result = call_action(method_name, context, **kwargs)
        except exception_class, e:
            if exception_class is tk.ValidationError:
                result = e.error_dict
            else:
                result = e.message
        except Exception, e:
            assert False, "Unexpected exception %s: %s" % (type(e), e)
        else:
            if exception_class:
                assert False, str(exception_class) + " was not raised"
        finally:
            # close the session to ensure that we're not just getting the obj from
            # memory but are reloading it from the DB
            ckan_model.Session.close_all()

        if not exception_class:
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
