# encoding: utf-8

import uuid
import json
import re

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import FunctionalTestBase, call_action, _get_test_app
import ckan.plugins.toolkit as tk
import ckan.model as ckan_model
import ckanext.metadata.model as ckanext_model
import ckanext.metadata.model.setup as ckanext_setup
import ckanext.metadata.tests.factories as ckanext_factories


def call_action_api(action, apikey=None, **kwargs):
    """
    POST an HTTP request to the CKAN API and return the result.

    Any additional keyword arguments that you pass to this function as **kwargs
    are posted as params to the API.

    Usage:
        success, package_dict = call_action_api('package_create', apikey=apikey, name='my_package')
        assert success and package_dict['name'] == 'my_package'

    :param action: the action to post to, e.g. 'package_create'
    :type action: string
    :param apikey: the API key to put in the Authorization header of the post (optional, default: None)
    :type apikey: string
    :param kwargs: any other keyword arguments passed to this function will be posted to the API as params

    :returns: success (True/False), and the 'result' or 'error' dictionary from the CKAN API response
    :rtype: tuple(bool, dict)
    """
    app = _get_test_app()
    params = json.dumps(kwargs)
    response = app.post('/api/action/{0}'.format(action), params=params,
                        extra_environ={'Authorization': str(apikey)}, status='*')

    success = response.json.get('success')
    assert type(success) is bool, "Invalid API response"
    result = response.json.get('result') if success else response.json.get('error')

    return success, result


def make_uuid():
    return unicode(uuid.uuid4())


def assert_object_matches_dict(object_, dict_):
    """
    Check that the object has all the items in the dict.
    """
    for key in dict_.keys():
        assert dict_[key] == getattr(object_, key)


def assert_package_has_extra(package_id, key, value, state='active'):
    """
    Check that a package has the specified extra key-value pair.
    """
    extra = ckan_model.Session.query(ckan_model.PackageExtra) \
        .filter(ckan_model.PackageExtra.package_id == package_id) \
        .filter(ckan_model.PackageExtra.key == key) \
        .first()

    assert extra
    assert extra.value == value
    assert extra.state == state


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


class ActionTestBase(FunctionalTestBase):

    _load_plugins = 'metadata',

    @classmethod
    def setup_class(cls):
        super(ActionTestBase, cls).setup_class()
        ckanext_setup.init_tables()

    def setup(self):
        super(ActionTestBase, self).setup()
        # hack because CKAN doesn't clean up the session properly
        if hasattr(ckan_model.Session, 'revision'):
            delattr(ckan_model.Session, 'revision')
        self.normal_user = ckan_factories.User()
        self.sysadmin_user = ckan_factories.Sysadmin()

    def _call_action(self, method, model_name, model_class=None, exception_class=None, sysadmin=False, check_auth=False, **kwargs):

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
                result = '\n'.join(e.error_summary.values())
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

        return result, obj


class TestInfrastructureActions(ActionTestBase):

    def test_create_valid(self):
        input_dict = {
            'name': 'test-infrastructure',
            'title': 'Test Infrastructure',
            'description': 'This is a test infrastructure',
        }
        result, obj = self._call_action('create', 'infrastructure',
                                        model_class=ckan_model.Group, **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        input_dict = {
            'id': make_uuid(),
            'name': 'test-infrastructure',
        }
        result, obj = self._call_action('create', 'infrastructure',
                                        model_class=ckan_model.Group,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._call_action('create', 'infrastructure',
                                        exception_class=tk.ValidationError,
                                        name=infrastructure['name'])
        assert 'Group name already exists in database' in result

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'infrastructure',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert 'The input field id was not expected.' in result

    def test_create_invalid_sysadmin_duplicate_id(self):
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._call_action('create', 'infrastructure',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=infrastructure['id'])
        assert 'Already exists: Group' in result

    def test_update_valid(self):
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'id': infrastructure['id'],
            'name': 'updated-test-infrastructure',
            'title': 'Updated Test Infrastructure',
            'description': 'Updated test infrastructure',
        }
        result, obj = self._call_action('update', 'infrastructure',
                                        model_class=ckan_model.Group, **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_partial(self):
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'id': infrastructure['id'],
            'title': 'Updated Test Infrastructure',
        }
        result, obj = self._call_action('update', 'infrastructure',
                                        model_class=ckan_model.Group, **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert obj.title == input_dict['title']
        assert obj.name == infrastructure['name']
        assert obj.description == infrastructure['description']

    def test_update_invalid_duplicate_name(self):
        infrastructure1 = ckanext_factories.Infrastructure()
        infrastructure2 = ckanext_factories.Infrastructure()
        input_dict = {
            'id': infrastructure1['id'],
            'name': infrastructure2['name'],
        }
        result, obj = self._call_action('update', 'infrastructure',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Group name already exists in database' in result

    def test_update_invalid_hierarchy_not_allowed(self):
        infrastructure1 = ckanext_factories.Infrastructure()
        infrastructure2 = ckanext_factories.Infrastructure()
        input_dict = {
            'id': infrastructure1['id'],
            'groups': [{'name': infrastructure2['name']}],
        }
        result, obj = self._call_action('update', 'infrastructure',
                                        exception_class=tk.ValidationError, **input_dict)
        assert re.search('The input field .*groups.* was not expected.', result)

    def test_delete_valid(self):
        infrastructure = ckanext_factories.Infrastructure()
        self._call_action('delete', 'infrastructure',
                          model_class=ckan_model.Group,
                          id=infrastructure['id'])

    def test_delete_invalid_dependencies(self):
        #TODO
        pass


class TestMetadataCollectionActions(ActionTestBase):

    def test_create_valid(self):
        organization = ckan_factories.Organization()
        input_dict = {
            'name': 'test-metadata-collection',
            'title': 'Test Metadata Collection',
            'description': 'This is a test metadata collection',
            'organization_id': organization['id'],
        }
        result, obj = self._call_action('create', 'metadata_collection',
                                        model_class=ckan_model.Group, **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        assert_group_has_extra(obj.id, 'organization_id', input_dict['organization_id'])
        del input_dict['organization_id']
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_organization_byname(self):
        organization = ckan_factories.Organization()
        input_dict = {
            'name': 'test-metadata-collection',
            'organization_id': organization['name'],
        }
        result, obj = self._call_action('create', 'metadata_collection',
                                        model_class=ckan_model.Group, **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        assert obj.name == input_dict['name']
        assert_group_has_extra(obj.id, 'organization_id', organization['id'])

    def test_create_valid_sysadmin_setid(self):
        organization = ckan_factories.Organization()
        input_dict = {
            'id': make_uuid(),
            'name': 'test-metadata-collection',
            'organization_id': organization['id'],
        }
        result, obj = self._call_action('create', 'metadata_collection',
                                        model_class=ckan_model.Group,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        assert_group_has_extra(obj.id, 'organization_id', input_dict['organization_id'])
        del input_dict['organization_id']
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        result, obj = self._call_action('create', 'metadata_collection',
                                        exception_class=tk.ValidationError,
                                        name=metadata_collection['name'])
        assert 'Group name already exists in database' in result

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'metadata_collection',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert 'The input field id was not expected.' in result

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        result, obj = self._call_action('create', 'metadata_collection',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_collection['id'])
        assert 'Already exists: Group' in result

    def test_update_valid(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        input_dict = {
            'id': metadata_collection['id'],
            'name': 'updated-test-metadata-collection',
            'title': 'Updated Test Metadata Collection',
            'description': 'Updated test metadata collection',
        }
        result, obj = self._call_action('update', 'metadata_collection',
                                        model_class=ckan_model.Group, **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        assert_object_matches_dict(obj, input_dict)
        assert_group_has_extra(obj.id, 'organization_id', metadata_collection['organization_id'])

    def test_update_valid_partial(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        input_dict = {
            'id': metadata_collection['id'],
            'title': 'Updated Test Metadata Collection',
        }
        result, obj = self._call_action('update', 'metadata_collection',
                                        model_class=ckan_model.Group, **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        assert obj.title == input_dict['title']
        assert obj.name == metadata_collection['name']
        assert obj.description == metadata_collection['description']
        assert_group_has_extra(obj.id, 'organization_id', metadata_collection['organization_id'])

    def test_update_invalid_duplicate_name(self):
        metadata_collection1 = ckanext_factories.MetadataCollection()
        metadata_collection2 = ckanext_factories.MetadataCollection()
        input_dict = {
            'id': metadata_collection1['id'],
            'name': metadata_collection2['name'],
        }
        result, obj = self._call_action('update', 'metadata_collection',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Group name already exists in database' in result

    def test_update_invalid_hierarchy_not_allowed(self):
        metadata_collection1 = ckanext_factories.MetadataCollection()
        metadata_collection2 = ckanext_factories.MetadataCollection()
        input_dict = {
            'id': metadata_collection1['id'],
            'groups': [{'name': metadata_collection2['name']}],
        }
        result, obj = self._call_action('update', 'metadata_collection',
                                        exception_class=tk.ValidationError, **input_dict)
        assert re.search('The input field .*groups.* was not expected.', result)

    def test_update_invalid_cannot_change_owner_org(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        organization = ckan_factories.Organization()
        input_dict = {
            'id': metadata_collection['id'],
            'organization_id': organization['id'],
        }
        result, obj = self._call_action('update', 'metadata_collection',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'The input field organization_id was not expected.' in result

    def test_delete_valid(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        self._call_action('delete', 'metadata_collection',
                          model_class=ckan_model.Group,
                          id=metadata_collection['id'])

    def test_delete_invalid_dependencies(self):
        #TODO
        pass


class TestMetadataSchemaActions(ActionTestBase):

    def test_create_valid(self):
        input_dict = {
            'title': 'Test Metadata Schema',
            'description': 'This is a test metadata schema',
            'schema_name': 'DataCite',
            'schema_version': '1.0',
            'schema_xsd': '<xsd/>',
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_parent(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'schema_name': 'DataCite',
            'schema_version': '1.0',
            'base_schema_id': metadata_schema['id'],
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        input_dict = {
            'id': make_uuid(),
            'schema_name': 'DataCite',
            'schema_version': '1.0',
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_name_new_version(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'schema_name': metadata_schema['schema_name'],
            'schema_version': metadata_schema['schema_version'] + 'a',
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_version_different_name(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'schema_name': metadata_schema['schema_name'] + '_foo',
            'schema_version': metadata_schema['schema_version'],
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_missing_schema_name(self):
        input_dict = {
            'title': 'Test Metadata Schema',
            'description': 'This is a test metadata schema',
            'schema_version': '1.0',
            'schema_xsd': '<xsd/>',
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Missing value' in result

    def test_create_invalid_missing_schema_version(self):
        input_dict = {
            'title': 'Test Metadata Schema',
            'description': 'This is a test metadata schema',
            'schema_name': 'DataCite',
            'schema_xsd': '<xsd/>',
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Missing value' in result

    def test_create_invalid_duplicate(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'schema_name': metadata_schema['schema_name'],
            'schema_version': metadata_schema['schema_version'],
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Unique constraint violation: ' in result

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert 'The input field id was not expected.' in result

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_schema['id'])
        assert 'Already exists: Metadata Schema' in result

    def test_create_invalid_sysadmin_self_parent(self):
        new_id = make_uuid()
        input_dict = {
            'id': new_id,
            'base_schema_id': new_id,
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert 'Not found: Metadata Schema' in result

    def test_update_valid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'title': 'Updated Test Metadata Schema',
            'description': 'Updated test metadata schema description',
            'schema_name': 'Updated Schema Name',
            'schema_version': 'v99',
            'schema_xsd': '<updated_xsd/>',
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_partial(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'schema_name': 'Updated Schema Name',
            'schema_version': '2.0',
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert obj.schema_name == input_dict['schema_name']
        assert obj.schema_version == input_dict['schema_version']
        assert obj.title == metadata_schema['title']
        assert obj.description == metadata_schema['description']

    def test_update_valid_change_parent_1(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema1['id'],
            'base_schema_id': metadata_schema2['id'],
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_change_parent_2(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema(base_schema_id=metadata_schema1['id'])
        metadata_schema3 = ckanext_factories.MetadataSchema(base_schema_id=metadata_schema2['id'])
        input_dict = {
            'id': metadata_schema3['id'],
            'base_schema_id': metadata_schema1['id'],
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_invalid_missing_schema_name(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'title': 'Updated Test Metadata Schema',
            'description': 'Updated test metadata schema description',
            'schema_version': 'v99',
            'schema_xsd': '<updated_xsd/>',
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Either both or neither schema_name and schema_version must be specified.' in result

    def test_update_invalid_missing_schema_version(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'title': 'Updated Test Metadata Schema',
            'description': 'Updated test metadata schema description',
            'schema_name': 'Updated Schema Name',
            'schema_xsd': '<updated_xsd/>',
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Either both or neither schema_name and schema_version must be specified.' in result

    def test_update_invalid_duplicate(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema1['id'],
            'schema_name': metadata_schema2['schema_name'],
            'schema_version': metadata_schema2['schema_version'],
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Unique constraint violation: ' in result

    def test_update_invalid_circular_ref_1(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema(base_schema_id=metadata_schema1['id'])
        input_dict = {
            'id': metadata_schema1['id'],
            'base_schema_id': metadata_schema2['id'],
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Loop in metadata schema hierarchy' in result

    def test_update_invalid_circular_ref_2(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema(base_schema_id=metadata_schema1['id'])
        metadata_schema3 = ckanext_factories.MetadataSchema(base_schema_id=metadata_schema2['id'])
        input_dict = {
            'id': metadata_schema1['id'],
            'base_schema_id': metadata_schema3['id'],
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Loop in metadata schema hierarchy' in result

    def test_update_invalid_self_parent(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'base_schema_id': metadata_schema['id'],
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'Loop in metadata schema hierarchy' in result

    def test_delete_valid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        self._call_action('delete', 'metadata_schema',
                          model_class=ckanext_model.MetadataSchema,
                          id=metadata_schema['id'])

    def test_delete_invalid_dependencies(self):
        #TODO
        pass


class TestMetadataModelActions(ActionTestBase):

    def test_create_valid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'title': 'Test Metadata Model',
            'description': 'This is a test metadata model',
            'metadata_schema_id': metadata_schema['id'],
            'model_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_organization(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        organization = ckan_factories.Organization()
        input_dict = {
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': organization['id'],
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_infrastructure(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'metadata_schema_id': metadata_schema['id'],
            'infrastructure_id': infrastructure['id'],
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': make_uuid(),
            'metadata_schema_id': metadata_schema['id'],
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_schema_different_organization(self):
        organization1 = ckan_factories.Organization()
        organization2 = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization1['id'])
        input_dict = {
            'metadata_schema_id': metadata_model['metadata_schema_id'],
            'organization_id': organization2['id'],
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_schema_different_infrastructure(self):
        infrastructure1 = ckanext_factories.Infrastructure()
        infrastructure2 = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure1['id'])
        input_dict = {
            'metadata_schema_id': metadata_model['metadata_schema_id'],
            'infrastructure_id': infrastructure2['id'],
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_organization_different_schema(self):
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': metadata_model['organization_id'],
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_infrastructure_different_schema(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'metadata_schema_id': metadata_schema['id'],
            'infrastructure_id': metadata_model['infrastructure_id'],
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_schema(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_model['metadata_schema_id'])
        assert 'Unique constraint violation: ' in result

    def test_create_invalid_duplicate_schema_organization(self):
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_model['metadata_schema_id'],
                                        organization_id=metadata_model['organization_id'])
        assert 'Unique constraint violation: ' in result

    def test_create_invalid_duplicate_schema_infrastructure(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_model['metadata_schema_id'],
                                        infrastructure_id=metadata_model['infrastructure_id'])
        assert 'Unique constraint violation: ' in result

    def test_create_invalid_with_organization_and_infrastructure(self):
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        organization_id=organization['id'],
                                        infrastructure_id=infrastructure['id'])
        assert 'A metadata model may be associated with either an organization or an ' \
               'infrastructure but not both.' in result

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert 'The input field id was not expected.' in result

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_model['id'])
        assert 'Already exists: Metadata Model' in result

    def test_create_invalid_not_json(self):
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        model_json="not json")
        assert 'JSON decode error: ' in result

    def test_create_invalid_not_json_dict(self):
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        model_json="[1,2,3]")
        assert 'Expecting a JSON dictionary' in result

    def test_update_valid(self):
        metadata_model = ckanext_factories.MetadataModel()
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_model['id'],
            'title': 'Updated Test Metadata Model',
            'description': 'Updated test metadata model description',
            'metadata_schema_id': metadata_schema['id'],
            'model_json': '{ "testkey": "newtestvalue" }',
        }
        result, obj = self._call_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_partial(self):
        metadata_model = ckanext_factories.MetadataModel()
        input_dict = {
            'id': metadata_model['id'],
            'title': 'Updated Test Metadata Model',
        }
        result, obj = self._call_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert obj.title == input_dict['title']
        assert obj.description == metadata_model['description']
        assert obj.metadata_schema_id == metadata_model['metadata_schema_id']

    def test_update_valid_set_organization(self):
        metadata_model = ckanext_factories.MetadataModel()
        organization = ckan_factories.Organization()
        input_dict = {
            'id': metadata_model['id'],
            'organization_id': organization['id'],
        }
        result, obj = self._call_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_set_infrastructure(self):
        metadata_model = ckanext_factories.MetadataModel()
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'id': metadata_model['id'],
            'infrastructure_id': infrastructure['id'],
        }
        result, obj = self._call_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_invalid_unset_schema(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        metadata_schema_id='')
        assert 'Not found: Metadata Schema' in result

    def test_update_invalid_unset_json(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        model_json='')
        assert 'JSON decode error: ' in result

    def test_update_invalid_duplicate_schema(self):
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model1['id'],
                                        metadata_schema_id=metadata_model2['metadata_schema_id'])
        assert 'Unique constraint violation: ' in result

    def test_update_invalid_duplicate_schema_organization(self):
        organization = ckan_factories.Organization()
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel(organization_id=organization['id'])
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model1['id'],
                                        metadata_schema_id=metadata_model2['metadata_schema_id'],
                                        organization_id=metadata_model2['organization_id'])
        assert 'Unique constraint violation: ' in result

    def test_update_invalid_duplicate_schema_infrastructure(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model1['id'],
                                        metadata_schema_id=metadata_model2['metadata_schema_id'],
                                        infrastructure_id=metadata_model2['infrastructure_id'])
        assert 'Unique constraint violation: ' in result

    def test_update_invalid_with_organization_set_infrastructure(self):
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        infrastructure_id=infrastructure['id'])
        assert 'A metadata model may be associated with either an organization or an ' \
               'infrastructure but not both.' in result

    def test_update_invalid_with_infrastructure_set_organization(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        organization = ckan_factories.Organization()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        organization_id=organization['id'])
        assert 'A metadata model may be associated with either an organization or an ' \
               'infrastructure but not both.' in result

    def test_delete_valid(self):
        metadata_model = ckanext_factories.MetadataModel()
        self._call_action('delete', 'metadata_model',
                          model_class=ckanext_model.MetadataModel,
                          id=metadata_model['id'])

    def test_delete_invalid_dependencies(self):
        #TODO
        pass


class TestMetadataRecordActions(ActionTestBase):

    def setup(self):
        super(TestMetadataRecordActions, self).setup()
        self.owner_org = ckan_factories.Organization(
            users=[{'name': self.normal_user['name'], 'capacity': 'editor'}])
        self.metadata_collection = ckanext_factories.MetadataCollection(organization_id=self.owner_org['id'])
        self.metadata_schema = ckanext_factories.MetadataSchema()

    def _generate_infrastructure(self):
        return ckanext_factories.Infrastructure(
            users=[{'name': self.normal_user['name'], 'capacity': 'member'}]
        )

    def _generate_metadata_record(self, **kwargs):
        return ckanext_factories.MetadataRecord(
            owner_org=self.owner_org['id'],
            metadata_collection_id=self.metadata_collection['id'],
            **kwargs
        )

    def test_create_valid(self):
        input_dict = {
            'title': 'Test Metadata Record',
            'owner_org': self.metadata_collection['organization_id'],
            'metadata_collection_id': self.metadata_collection['id'],
            'schema_name': self.metadata_schema['schema_name'],
            'schema_version': self.metadata_schema['schema_version'],
            'content_json': '{ "testkey": "testvalue" }',
            'content_raw': '<xml/>',
            'content_url': 'http://example.net/',
        }
        result, obj = self._call_action('create', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        assert obj.type == 'metadata_record'
        assert obj.name == 'metadata-' + obj.id
        assert obj.title == input_dict['title']
        assert obj.owner_org == input_dict['owner_org']
        assert_package_has_extra(obj.id, 'metadata_collection_id', self.metadata_collection['id'])
        assert_package_has_extra(obj.id, 'metadata_schema_id', self.metadata_schema['id'])
        assert_package_has_extra(obj.id, 'content_json', input_dict['content_json'])
        assert_package_has_extra(obj.id, 'content_raw', input_dict['content_raw'])
        assert_package_has_extra(obj.id, 'content_url', input_dict['content_url'])

    def test_create_valid_setname(self):
        input_dict = {
            'name': 'test-metadata-record',
            'owner_org': self.metadata_collection['organization_id'],
            'metadata_collection_id': self.metadata_collection['id'],
            'schema_name': self.metadata_schema['schema_name'],
            'schema_version': self.metadata_schema['schema_version'],
        }
        result, obj = self._call_action('create', 'metadata_record',
                                        model_class=ckan_model.Package,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert obj.type == 'metadata_record'
        assert obj.name == input_dict['name']
        assert obj.owner_org == input_dict['owner_org']
        assert_package_has_extra(obj.id, 'metadata_collection_id', self.metadata_collection['id'])
        assert_package_has_extra(obj.id, 'metadata_schema_id', self.metadata_schema['id'])

    def test_create_valid_owner_org_byname(self):
        input_dict = {
            'owner_org': self.owner_org['name'],
            'metadata_collection_id': self.metadata_collection['id'],
            'schema_name': self.metadata_schema['schema_name'],
            'schema_version': self.metadata_schema['schema_version'],
        }
        result, obj = self._call_action('create', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        assert obj.type == 'metadata_record'
        assert obj.name == 'metadata-' + obj.id
        assert obj.owner_org == self.owner_org['id']
        assert_package_has_extra(obj.id, 'metadata_collection_id', self.metadata_collection['id'])
        assert_package_has_extra(obj.id, 'metadata_schema_id', self.metadata_schema['id'])

    def test_create_valid_with_infrastructures(self):
        infrastructure1 = self._generate_infrastructure()
        infrastructure2 = self._generate_infrastructure()
        input_dict = {
            'owner_org': self.owner_org['name'],
            'metadata_collection_id': self.metadata_collection['id'],
            'schema_name': self.metadata_schema['schema_name'],
            'schema_version': self.metadata_schema['schema_version'],
            'infrastructures': [
                {'id': infrastructure1['id']},
                {'id': infrastructure2['name']},
            ],
        }
        result, obj = self._call_action('create', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        assert obj.type == 'metadata_record'
        assert obj.name == 'metadata-' + obj.id
        assert obj.owner_org == self.owner_org['id']
        assert_package_has_extra(obj.id, 'metadata_collection_id', self.metadata_collection['id'])
        assert_package_has_extra(obj.id, 'metadata_schema_id', self.metadata_schema['id'])
        assert_group_has_member(infrastructure1['id'], obj.id, 'package')
        assert_group_has_member(infrastructure2['id'], obj.id, 'package')

    def test_create_valid_sysadmin_setid(self):
        input_dict = {
            'id': make_uuid(),
            'owner_org': self.metadata_collection['organization_id'],
            'metadata_collection_id': self.metadata_collection['id'],
            'schema_name': self.metadata_schema['schema_name'],
            'schema_version': self.metadata_schema['schema_version'],
        }
        result, obj = self._call_action('create', 'metadata_record',
                                        model_class=ckan_model.Package,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert obj.type == 'metadata_record'
        assert obj.name == 'metadata-' + input_dict['id']
        assert obj.owner_org == input_dict['owner_org']
        assert_package_has_extra(obj.id, 'metadata_collection_id', self.metadata_collection['id'])
        assert_package_has_extra(obj.id, 'metadata_schema_id', self.metadata_schema['id'])

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert 'The input field id was not expected.' in result

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_record = ckanext_factories.MetadataRecord()
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_record['id'])
        assert 'Dataset id already exists' in result

    def test_update_valid(self):
        infrastructure1 = self._generate_infrastructure()
        infrastructure2 = self._generate_infrastructure()
        metadata_record = self._generate_metadata_record(infrastructures=[
            {'id': infrastructure1['id']}, {'id': infrastructure2['id']}])

        new_metadata_collection = ckanext_factories.MetadataCollection(organization_id=self.owner_org['id'])
        new_metadata_schema = ckanext_factories.MetadataSchema()
        new_infrastructure = self._generate_infrastructure()

        input_dict = {
            'id': metadata_record['id'],
            'name': 'updated-test-metadata-record',
            'title': 'Updated Test Metadata Record',
            'metadata_collection_id': new_metadata_collection['id'],
            'schema_name': new_metadata_schema['schema_name'],
            'schema_version': new_metadata_schema['schema_version'],
            'content_json': '{ "newtestkey": "newtestvalue" }',
            'content_raw': '<updated_xml/>',
            'content_url': 'http://updated.example.net/',
            'infrastructures': [
                {'id': infrastructure2['name']},
                {'id': new_infrastructure['name']},
            ],
        }
        result, obj = self._call_action('update', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        assert obj.type == 'metadata_record'
        assert obj.name == input_dict['name']
        assert obj.title == input_dict['title']
        assert obj.owner_org == self.owner_org['id']
        assert_package_has_extra(obj.id, 'metadata_collection_id', new_metadata_collection['id'])
        assert_package_has_extra(obj.id, 'metadata_schema_id', new_metadata_schema['id'])
        assert_package_has_extra(obj.id, 'content_json', input_dict['content_json'])
        assert_package_has_extra(obj.id, 'content_raw', input_dict['content_raw'])
        assert_package_has_extra(obj.id, 'content_url', input_dict['content_url'])
        assert_group_has_member(infrastructure1['id'], obj.id, 'package', state='deleted')
        assert_group_has_member(infrastructure2['id'], obj.id, 'package')
        assert_group_has_member(new_infrastructure['id'], obj.id, 'package')

    def test_update_valid_partial(self):
        infrastructure1 = self._generate_infrastructure()
        infrastructure2 = self._generate_infrastructure()
        metadata_record = self._generate_metadata_record(infrastructures=[
            {'id': infrastructure1['id']}, {'id': infrastructure2['id']}])

        input_dict = {
            'id': metadata_record['id'],
            'name': 'updated-test-metadata-record',
            'content_json': '{ "newtestkey": "newtestvalue" }',
        }
        result, obj = self._call_action('update', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        assert obj.type == 'metadata_record'
        assert obj.name == input_dict['name']
        assert obj.title == metadata_record['title']
        assert obj.owner_org == self.owner_org['id']
        assert_package_has_extra(obj.id, 'metadata_collection_id', metadata_record['metadata_collection_id'])
        assert_package_has_extra(obj.id, 'metadata_schema_id', metadata_record['metadata_schema_id'])
        assert_package_has_extra(obj.id, 'content_json', input_dict['content_json'])
        assert_package_has_extra(obj.id, 'content_raw', metadata_record['content_raw'])
        assert_package_has_extra(obj.id, 'content_url', metadata_record['content_url'])
        assert_group_has_member(infrastructure1['id'], obj.id, 'package')
        assert_group_has_member(infrastructure2['id'], obj.id, 'package')

    def test_update_invalid_duplicate_name(self):
        metadata_record1 = self._generate_metadata_record()
        metadata_record2 = self._generate_metadata_record()
        input_dict = {
            'id': metadata_record1['id'],
            'name': metadata_record2['name'],
        }
        result, obj = self._call_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError, **input_dict)
        assert 'That URL is already in use.' in result

    def test_delete_valid(self):
        metadata_record = self._generate_metadata_record()
        self._call_action('delete', 'metadata_record',
                          model_class=ckan_model.Package,
                          id=metadata_record['id'])

    def test_delete_invalid_dependencies(self):
        #TODO
        pass
