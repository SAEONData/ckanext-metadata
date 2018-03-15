# encoding: utf-8

import uuid
import re

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import FunctionalTestBase, call_action
import ckan.plugins.toolkit as tk
import ckan.model as ckan_model
import ckanext.metadata.model as ckanext_model
import ckanext.metadata.model.setup as ckanext_setup
import ckanext.metadata.tests.factories as ckanext_factories


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
        assert_error(result, 'name', 'Group name already exists in database')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'infrastructure',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._call_action('create', 'infrastructure',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=infrastructure['id'])
        assert_error(result, 'id', 'Already exists: Group')

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
        assert_error(result, 'name', 'Group name already exists in database')

    def test_update_invalid_hierarchy_not_allowed(self):
        infrastructure1 = ckanext_factories.Infrastructure()
        infrastructure2 = ckanext_factories.Infrastructure()
        input_dict = {
            'id': infrastructure1['id'],
            'groups': [{'name': infrastructure2['name']}],
        }
        result, obj = self._call_action('update', 'infrastructure',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, '__junk', 'The input field .*groups.* was not expected.')

    def test_delete_valid(self):
        infrastructure = ckanext_factories.Infrastructure()
        self._call_action('delete', 'infrastructure',
                          model_class=ckan_model.Group,
                          id=infrastructure['id'])

    def test_delete_valid_cascade_metadata_models(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])

        self._call_action('delete', 'infrastructure',
                          model_class=ckan_model.Group,
                          id=infrastructure['id'])
        assert ckanext_model.MetadataModel.get(metadata_model['id']).state == 'deleted'

    def test_delete_with_dependent_metadata_records(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_record = ckanext_factories.MetadataRecord(infrastructures=[{'id': infrastructure['id']}])

        result, obj = self._call_action('delete', 'infrastructure',
                                        exception_class=tk.ValidationError,
                                        id=infrastructure['id'])
        assert_error(result, 'message', 'Infrastructure has dependent metadata records')

        call_action('metadata_record_delete', id=metadata_record['id'])
        self._call_action('delete', 'infrastructure',
                          model_class=ckan_model.Group,
                          id=infrastructure['id'])

    def test_delete_with_dependent_metadata_models(self):
        # TODO: this test will work once we have metadata models being referenced for validation
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])

        # add validation objects here
        result, obj = self._call_action('delete', 'infrastructure',
                                        exception_class=tk.ValidationError,
                                        id=infrastructure['id'])
        assert_error(result, 'message', 'Infrastructure has dependent metadata models that are in use')

        # delete validation objects here
        self._call_action('delete', 'infrastructure',
                          model_class=ckan_model.Group,
                          id=infrastructure['id'])
        assert ckanext_model.MetadataModel.get(metadata_model['id']).state == 'deleted'


class TestOrganizationActions(ActionTestBase):

    # TODO: most of these tests will not work, as chaining of action functions is broken in CKAN
    # and therefore we cannot correctly implement our organization_delete override

    def test_delete_valid(self):
        organization = ckan_factories.Organization()
        self._call_action('delete', 'organization',
                          model_class=ckan_model.Group,
                          id=organization['id'])

    def test_delete_valid_cascade_metadata_models(self):
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])

        self._call_action('delete', 'organization',
                          model_class=ckan_model.Group,
                          id=organization['id'])
        assert ckanext_model.MetadataModel.get(metadata_model['id']).state == 'deleted'

    def test_delete_valid_cascade_metadata_collections(self):
        organization = ckan_factories.Organization()
        metadata_collection = ckanext_factories.MetadataCollection(organization_id=organization['id'])

        self._call_action('delete', 'organization',
                          model_class=ckan_model.Group,
                          id=organization['id'])
        assert ckan_model.Group.get(metadata_collection['id']).state == 'deleted'

    def test_delete_with_dependent_metadata_records(self):
        organization = ckan_factories.Organization()
        metadata_collection = ckanext_factories.MetadataCollection(organization_id=organization['id'])
        metadata_record = ckanext_factories.MetadataRecord(owner_org=organization['id'],
                                                           metadata_collection_id=metadata_collection['id'])

        result, obj = self._call_action('delete', 'organization',
                                        exception_class=tk.ValidationError,
                                        id=organization['id'])
        assert_error(result, 'message', 'Organization has dependent metadata records')

        call_action('metadata_record_delete', id=metadata_record['id'])
        self._call_action('delete', 'organization',
                          model_class=ckan_model.Group,
                          id=organization['id'])
        assert ckan_model.Group.get(metadata_collection['id']).state == 'deleted'

    def test_delete_with_dependent_metadata_models(self):
        # TODO: this test will work once we have metadata models being referenced for validation
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])

        # add validation objects here
        result, obj = self._call_action('delete', 'organization',
                                        exception_class=tk.ValidationError,
                                        id=organization['id'])
        assert_error(result, 'message', 'Organization has dependent metadata models that are in use')

        # delete validation objects here
        self._call_action('delete', 'organization',
                          model_class=ckan_model.Group,
                          id=organization['id'])
        assert ckanext_model.MetadataModel.get(metadata_model['id']).state == 'deleted'


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
        assert_error(result, 'name', 'Group name already exists in database')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'metadata_collection',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        result, obj = self._call_action('create', 'metadata_collection',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_collection['id'])
        assert_error(result, 'id', 'Already exists: Group')

    def test_create_invalid_bad_organization(self):
        result, obj = self._call_action('create', 'metadata_collection',
                                        exception_class=tk.ValidationError,
                                        organization_id='foo')
        assert_error(result, 'organization_id', 'Not found: Organization')

    def test_create_invalid_deleted_organization(self):
        organization = ckan_factories.Organization()
        call_action('organization_delete', id=organization['id'])
        result, obj = self._call_action('create', 'metadata_collection',
                                        exception_class=tk.ValidationError,
                                        organization_id=organization['id'])
        assert_error(result, 'organization_id', 'Not found: Organization')

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
        assert_error(result, 'name', 'Group name already exists in database')

    def test_update_invalid_hierarchy_not_allowed(self):
        metadata_collection1 = ckanext_factories.MetadataCollection()
        metadata_collection2 = ckanext_factories.MetadataCollection()
        input_dict = {
            'id': metadata_collection1['id'],
            'groups': [{'name': metadata_collection2['name']}],
        }
        result, obj = self._call_action('update', 'metadata_collection',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, '__junk', 'The input field .*groups.* was not expected.')

    def test_update_invalid_cannot_change_organization(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        organization = ckan_factories.Organization()
        input_dict = {
            'id': metadata_collection['id'],
            'organization_id': organization['id'],
        }
        result, obj = self._call_action('update', 'metadata_collection',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'organization_id', 'The input field organization_id was not expected.')

    def test_delete_valid(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        self._call_action('delete', 'metadata_collection',
                          model_class=ckan_model.Group,
                          id=metadata_collection['id'])

    def test_delete_with_dependencies(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        metadata_record = ckanext_factories.MetadataRecord(
            owner_org=metadata_collection['organization_id'],
            metadata_collection_id=metadata_collection['id'])

        result, obj = self._call_action('delete', 'metadata_collection',
                                        exception_class=tk.ValidationError,
                                        id=metadata_collection['id'])
        assert_error(result, 'message', 'Metadata collection has dependent metadata records')

        call_action('metadata_record_delete', id=metadata_record['id'])
        self._call_action('delete', 'metadata_collection',
                          model_class=ckan_model.Group,
                          id=metadata_collection['id'])


class TestMetadataSchemaActions(ActionTestBase):

    def test_create_valid(self):
        input_dict = {
            'title': 'Test Metadata Schema',
            'description': 'This is a test metadata schema',
            'schema_name': 'DataCite',
            'schema_version': '1.0',
            'schema_xsd': '<xsd/>',
            'base_schema_id': '',
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == generate_name(input_dict['schema_name'], input_dict['schema_version'])

    def test_create_valid_setname(self):
        input_dict = {
            'name': 'test-metadata-schema',
            'schema_name': 'DataCite',
            'schema_version': '1.0',
            'schema_xsd': '<xsd/>',
            'base_schema_id': '',
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_parent(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'schema_name': 'DataCite',
            'schema_version': '1.0',
            'schema_xsd': '<xsd/>',
            'base_schema_id': metadata_schema['id'],
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_parent_byname(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'schema_name': 'DataCite',
            'schema_version': '1.0',
            'schema_xsd': '<xsd/>',
            'base_schema_id': metadata_schema['name'],
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        input_dict['base_schema_id'] = metadata_schema['id']
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        input_dict = {
            'id': make_uuid(),
            'schema_name': 'DataCite',
            'schema_version': '1.0',
            'schema_xsd': '<xsd/>',
            'base_schema_id': '',
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
            'schema_xsd': '<xsd/>',
            'base_schema_id': '',
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_version_different_name(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'schema_name': metadata_schema['schema_name'] + '_foo',
            'schema_version': metadata_schema['schema_version'],
            'schema_xsd': '<xsd/>',
            'base_schema_id': '',
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        name=metadata_schema['name'])
        assert_error(result, 'name', 'Duplicate name: Metadata Schema')

    def test_create_invalid_missing_params(self):
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError)
        assert_error(result, 'schema_name', 'Missing parameter')
        assert_error(result, 'schema_version', 'Missing parameter')
        assert_error(result, 'schema_xsd', 'Missing parameter')
        assert_error(result, 'base_schema_id', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        schema_name='',
                                        schema_version='')
        assert_error(result, 'schema_name', 'Missing value')
        assert_error(result, 'schema_version', 'Missing value')

    def test_create_invalid_duplicate(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'schema_name': metadata_schema['schema_name'],
            'schema_version': metadata_schema['schema_version'],
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_schema['id'])
        assert_error(result, 'id', 'Already exists: Metadata Schema')

    def test_create_invalid_sysadmin_self_parent(self):
        new_id = make_uuid()
        input_dict = {
            'id': new_id,
            'base_schema_id': new_id,
        }
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert_error(result, 'base_schema_id', 'Not found: Metadata Schema')

    def test_create_invalid_bad_parent(self):
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        base_schema_id='foo')
        assert_error(result, 'base_schema_id', 'Not found: Metadata Schema')

    def test_create_invalid_deleted_parent(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        call_action('metadata_schema_delete', id=metadata_schema['id'])
        result, obj = self._call_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        base_schema_id=metadata_schema['id'])
        assert_error(result, 'base_schema_id', 'Not found: Metadata Schema')

    def test_update_valid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'title': 'Updated Test Metadata Schema',
            'description': 'Updated test metadata schema description',
            'schema_name': 'Updated Schema Name',
            'schema_version': 'v99',
            'schema_xsd': '<updated_xsd/>',
            'base_schema_id': '',
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == generate_name(input_dict['schema_name'], input_dict['schema_version'])

    def test_update_valid_partial(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'name': 'updated-test-metadata-schema',
            'schema_name': metadata_schema['schema_name'],
            'schema_version': metadata_schema['schema_name'],
            'schema_xsd': '<updated_xsd/>',
            'base_schema_id': '',
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.title == metadata_schema['title']
        assert obj.description == metadata_schema['description']

    def test_update_valid_change_parent_1(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema1['id'],
            'schema_name': metadata_schema1['schema_name'],
            'schema_version': metadata_schema1['schema_version'],
            'schema_xsd': metadata_schema1['schema_xsd'],
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
            'schema_name': metadata_schema3['schema_name'],
            'schema_version': metadata_schema3['schema_version'],
            'schema_xsd': metadata_schema3['schema_xsd'],
            'base_schema_id': metadata_schema1['id'],
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_invalid_duplicate_name(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema1['id'],
            'name': metadata_schema2['name'],
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'name', 'Duplicate name: Metadata Schema')

    def test_update_invalid_missing_params(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        id=metadata_schema['id'])
        assert_error(result, 'schema_name', 'Missing parameter')
        assert_error(result, 'schema_version', 'Missing parameter')
        assert_error(result, 'schema_xsd', 'Missing parameter')
        assert_error(result, 'base_schema_id', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        id=metadata_schema['id'],
                                        schema_name='',
                                        schema_version='')
        assert_error(result, 'schema_name', 'Missing value')
        assert_error(result, 'schema_version', 'Missing value')

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
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_circular_ref_1(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema(base_schema_id=metadata_schema1['id'])
        input_dict = {
            'id': metadata_schema1['id'],
            'base_schema_id': metadata_schema2['id'],
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'base_schema_id', 'Loop in metadata schema hierarchy')

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
        assert_error(result, 'base_schema_id', 'Loop in metadata schema hierarchy')

    def test_update_invalid_self_parent(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'base_schema_id': metadata_schema['id'],
        }
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'base_schema_id', 'Loop in metadata schema hierarchy')

    def test_update_invalid_bad_parent(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        id=metadata_schema['id'],
                                        base_schema_id='foo')
        assert_error(result, 'base_schema_id', 'Not found: Metadata Schema')

    def test_update_invalid_deleted_parent(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema()
        call_action('metadata_schema_delete', id=metadata_schema1['id'])
        result, obj = self._call_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        id=metadata_schema2['id'],
                                        base_schema_id=metadata_schema1['id'])
        assert_error(result, 'base_schema_id', 'Not found: Metadata Schema')

    def test_delete_valid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        self._call_action('delete', 'metadata_schema',
                          model_class=ckanext_model.MetadataSchema,
                          id=metadata_schema['id'])

    def test_delete_with_dependencies(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema(base_schema_id=metadata_schema1['id'])
        metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_schema1['id'])
        metadata_record = ckanext_factories.MetadataRecord(
            schema_name=metadata_schema1['schema_name'],
            schema_version=metadata_schema1['schema_version'])

        result, obj = self._call_action('delete', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        id=metadata_schema1['id'])

        assert_error(result, 'message', 'Metadata schema has dependent metadata schemas')
        assert_error(result, 'message', 'Metadata schema has dependent metadata models')
        assert_error(result, 'message', 'Metadata schema has dependent metadata records')

        call_action('metadata_schema_delete', id=metadata_schema2['id'])
        call_action('metadata_model_delete', id=metadata_model['id'])
        call_action('metadata_record_delete', id=metadata_record['id'])

        self._call_action('delete', 'metadata_schema',
                          model_class=ckanext_model.MetadataSchema,
                          id=metadata_schema1['id'])


class TestMetadataModelActions(ActionTestBase):

    def test_create_valid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'title': 'Test Metadata Model',
            'description': 'This is a test metadata model',
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'model_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == generate_name(metadata_schema['name'], '', '')

    def test_create_valid_setname(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'name': 'test-metadata-model',
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'model_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_organization_byname(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        organization = ckan_factories.Organization()
        input_dict = {
            'metadata_schema_id': metadata_schema['name'],
            'organization_id': organization['name'],
            'infrastructure_id': '',
            'model_json': '',
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert obj.metadata_schema_id == metadata_schema['id']
        assert obj.organization_id == organization['id']
        assert obj.infrastructure_id is None
        assert obj.name == generate_name(metadata_schema['name'], organization['name'], '')

    def test_create_valid_with_infrastructure_byname(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'metadata_schema_id': metadata_schema['name'],
            'organization_id': '',
            'infrastructure_id': infrastructure['name'],
            'model_json': '',
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert obj.metadata_schema_id == metadata_schema['id']
        assert obj.organization_id is None
        assert obj.infrastructure_id == infrastructure['id']
        assert obj.name == generate_name(metadata_schema['name'], '', infrastructure['name'])

    def test_create_valid_sysadmin_setid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': make_uuid(),
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'model_json': '',
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
            'infrastructure_id': '',
            'model_json': '',
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
            'organization_id': '',
            'infrastructure_id': infrastructure2['id'],
            'model_json': '',
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
            'infrastructure_id': '',
            'model_json': '',
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
            'organization_id': '',
            'infrastructure_id': metadata_model['infrastructure_id'],
            'model_json': '',
        }
        result, obj = self._call_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        name=metadata_model['name'])
        assert_error(result, 'name', 'Duplicate name: Metadata Model')

    def test_create_invalid_duplicate_schema(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_model['metadata_schema_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_duplicate_schema_organization(self):
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_model['metadata_schema_id'],
                                        organization_id=metadata_model['organization_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_duplicate_schema_infrastructure(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_model['metadata_schema_id'],
                                        infrastructure_id=metadata_model['infrastructure_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_with_organization_and_infrastructure(self):
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        organization_id=organization['id'],
                                        infrastructure_id=infrastructure['id'])
        assert_error(result, '__after',
                     'A metadata model may be associated with either an organization or an infrastructure but not both.')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_model['id'])
        assert_error(result, 'id', 'Already exists: Metadata Model')

    def test_create_invalid_not_json(self):
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        model_json='not json')
        assert_error(result, 'model_json', 'JSON decode error')

    def test_create_invalid_not_json_dict(self):
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        model_json='[1,2,3]')
        assert_error(result, 'model_json', 'Expecting a JSON dictionary')

    def test_create_invalid_missing_params(self):
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError)
        assert_error(result, 'metadata_schema_id', 'Missing parameter')
        assert_error(result, 'organization_id', 'Missing parameter')
        assert_error(result, 'infrastructure_id', 'Missing parameter')
        assert_error(result, 'model_json', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id='')
        assert_error(result, 'metadata_schema_id', 'Missing value')

    def test_create_invalid_bad_references(self):
        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id='a',
                                        organization_id='b',
                                        infrastructure_id='c')
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_create_invalid_deleted_references(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        call_action('metadata_schema_delete', id=metadata_schema['id'])
        call_action('organization_delete', id=organization['id'])
        call_action('infrastructure_delete', id=infrastructure['id'])

        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_schema['id'],
                                        organization_id=organization['id'],
                                        infrastructure_id=infrastructure['id'])
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_update_valid(self):
        metadata_model = ckanext_factories.MetadataModel()
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_model['id'],
            'title': 'Updated Test Metadata Model',
            'description': 'Updated test metadata model description',
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'model_json': '{ "testkey": "newtestvalue" }',
        }
        result, obj = self._call_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == generate_name(metadata_schema['name'], '', '')

    def test_update_valid_partial(self):
        metadata_model = ckanext_factories.MetadataModel()
        input_dict = {
            'id': metadata_model['id'],
            'name': 'updated-test-metadata-model',
            'metadata_schema_id': metadata_model['metadata_schema_id'],
            'organization_id': '',
            'infrastructure_id': '',
            'model_json': '{ "testkey": "newtestvalue" }',
        }
        result, obj = self._call_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.title == metadata_model['title']
        assert obj.description == metadata_model['description']

    def test_update_valid_set_organization(self):
        metadata_model = ckanext_factories.MetadataModel()
        organization = ckan_factories.Organization()
        input_dict = {
            'id': metadata_model['id'],
            'metadata_schema_id': metadata_model['metadata_schema_id'],
            'organization_id': organization['id'],
            'infrastructure_id': '',
            'model_json': '',
        }
        result, obj = self._call_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        metadata_schema = ckanext_model.MetadataSchema.get(metadata_model['metadata_schema_id'])
        assert obj.name == generate_name(metadata_schema.name, organization['name'], '')

    def test_update_valid_set_infrastructure(self):
        metadata_model = ckanext_factories.MetadataModel()
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'id': metadata_model['id'],
            'metadata_schema_id': metadata_model['metadata_schema_id'],
            'organization_id': '',
            'infrastructure_id': infrastructure['id'],
            'model_json': '',
        }
        result, obj = self._call_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        metadata_schema = ckanext_model.MetadataSchema.get(metadata_model['metadata_schema_id'])
        assert obj.name == generate_name(metadata_schema.name, '', infrastructure['name'])

    def test_update_invalid_duplicate_name(self):
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel()
        input_dict = {
            'id': metadata_model1['id'],
            'name': metadata_model2['name'],
        }
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'name', 'Duplicate name: Metadata Model')

    def test_update_invalid_missing_params(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'])
        assert_error(result, 'metadata_schema_id', 'Missing parameter')
        assert_error(result, 'organization_id', 'Missing parameter')
        assert_error(result, 'infrastructure_id', 'Missing parameter')
        assert_error(result, 'model_json', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        metadata_schema_id='')
        assert_error(result, 'metadata_schema_id', 'Missing value')

    def test_update_invalid_duplicate_schema(self):
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model1['id'],
                                        metadata_schema_id=metadata_model2['metadata_schema_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_duplicate_schema_organization(self):
        organization = ckan_factories.Organization()
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel(organization_id=organization['id'])
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model1['id'],
                                        metadata_schema_id=metadata_model2['metadata_schema_id'],
                                        organization_id=metadata_model2['organization_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_duplicate_schema_infrastructure(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model1['id'],
                                        metadata_schema_id=metadata_model2['metadata_schema_id'],
                                        infrastructure_id=metadata_model2['infrastructure_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_with_organization_set_infrastructure(self):
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        infrastructure_id=infrastructure['id'])
        assert_error(result, '__after',
                     'A metadata model may be associated with either an organization or an infrastructure but not both.')

    def test_update_invalid_with_infrastructure_set_organization(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        organization = ckan_factories.Organization()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        organization_id=organization['id'])
        assert_error(result, '__after',
                     'A metadata model may be associated with either an organization or an infrastructure but not both.')

    def test_update_invalid_not_json(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        model_json='not json')
        assert_error(result, 'model_json', 'JSON decode error')

    def test_update_invalid_not_json_dict(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        model_json='[1,2,3]')
        assert_error(result, 'model_json', 'Expecting a JSON dictionary')

    def test_update_invalid_bad_references(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._call_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        metadata_schema_id='a',
                                        organization_id='b',
                                        infrastructure_id='c')
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_update_invalid_deleted_references(self):
        metadata_model = ckanext_factories.MetadataModel()
        metadata_schema = ckanext_factories.MetadataSchema()
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        call_action('metadata_schema_delete', id=metadata_schema['id'])
        call_action('organization_delete', id=organization['id'])
        call_action('infrastructure_delete', id=infrastructure['id'])

        result, obj = self._call_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        metadata_schema_id=metadata_schema['id'],
                                        organization_id=organization['id'],
                                        infrastructure_id=infrastructure['id'])
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_delete_valid(self):
        metadata_model = ckanext_factories.MetadataModel()
        self._call_action('delete', 'metadata_model',
                          model_class=ckanext_model.MetadataModel,
                          id=metadata_model['id'])

    def test_delete_with_dependencies(self):
        # TODO: this test will work once we have metadata models being referenced for validation
        metadata_model = ckanext_factories.MetadataModel()

        # add validation objects here
        result, obj = self._call_action('delete', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'])
        assert_error(result, 'message', 'Metadata model has dependent validation records')

        # delete validation objects here
        self._call_action('delete', 'metadata_model',
                          model_class=ckanext_model.MetadataModel,
                          id=metadata_model['id'])


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

    def _make_input_dict(self):
        return {
            'title': 'Test Metadata Record',
            'owner_org': self.owner_org['id'],
            'metadata_collection_id': self.metadata_collection['id'],
            'infrastructures': [],
            'schema_name': self.metadata_schema['schema_name'],
            'schema_version': self.metadata_schema['schema_version'],
            'content_json': '{ "testkey": "testvalue" }',
            'content_raw': '<xml/>',
            'content_url': 'http://example.net/',
        }

    def _assert_metadata_record_ok(self, obj, input_dict, **kwargs):
        """
        Checks the resulting package object against the input dict and referenced objects.
        Override comparison values using kwargs.
        """
        assert obj.type == 'metadata_record'
        assert obj.title == kwargs.pop('title', input_dict.get('title'))
        assert obj.name == kwargs.pop('name', 'metadata-' + obj.id)
        assert obj.owner_org == kwargs.pop('owner_org', self.owner_org['id'])
        assert_package_has_extra(obj.id, 'metadata_collection_id', kwargs.pop('metadata_collection_id', self.metadata_collection['id']))
        assert_package_has_extra(obj.id, 'metadata_schema_id', kwargs.pop('metadata_schema_id', self.metadata_schema['id']))
        assert_package_has_extra(obj.id, 'content_json', input_dict['content_json'])
        assert_package_has_extra(obj.id, 'content_raw', input_dict['content_raw'])
        assert_package_has_extra(obj.id, 'content_url', input_dict['content_url'])

    def test_create_valid(self):
        input_dict = self._make_input_dict()
        result, obj = self._call_action('create', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_create_valid_setname(self):
        input_dict = self._make_input_dict()
        input_dict['name'] = 'test-metadata-record'
        result, obj = self._call_action('create', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict, name=input_dict['name'])

    def test_create_valid_owner_org_byname(self):
        input_dict = self._make_input_dict()
        input_dict['owner_org'] = self.owner_org['name']
        result, obj = self._call_action('create', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_create_valid_with_infrastructures(self):
        infrastructure1 = self._generate_infrastructure()
        infrastructure2 = self._generate_infrastructure()
        input_dict = self._make_input_dict()
        input_dict.update({
            'infrastructures': [
                {'id': infrastructure1['id']},
                {'id': infrastructure2['name']},
            ],
        })
        result, obj = self._call_action('create', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)
        assert_group_has_member(infrastructure1['id'], obj.id, 'package')
        assert_group_has_member(infrastructure2['id'], obj.id, 'package')

    def test_create_valid_sysadmin_setid(self):
        input_dict = self._make_input_dict()
        input_dict['id'] = make_uuid()
        result, obj = self._call_action('create', 'metadata_record',
                                        model_class=ckan_model.Package,
                                        sysadmin=True, check_auth=True, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_record = ckanext_factories.MetadataRecord()
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_record['id'])
        assert_error(result, 'id', 'Dataset id already exists')

    def test_create_invalid_missing_params(self):
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError)
        assert_error(result, 'owner_org', 'Missing parameter')
        assert_error(result, 'metadata_collection_id', 'Missing parameter')
        assert_error(result, 'infrastructures', 'Missing parameter')
        assert_error(result, 'schema_name', 'Missing parameter')
        assert_error(result, 'schema_version', 'Missing parameter')
        assert_error(result, 'content_json', 'Missing parameter')
        assert_error(result, 'content_raw', 'Missing parameter')
        assert_error(result, 'content_url', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        owner_org='',
                                        metadata_collection_id='',
                                        schema_name='',
                                        schema_version='')
        assert_error(result, 'owner_org', 'Missing value')
        assert_error(result, 'metadata_collection_id', 'Missing value')
        assert_error(result, 'schema_name', 'Missing value')
        assert_error(result, 'schema_version', 'Missing value')

    def test_create_invalid_duplicate_name(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        name=metadata_record['name'])
        assert_error(result, 'name', 'That URL is already in use.')

    def test_create_invalid_not_json(self):
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        content_json='not json')
        assert_error(result, 'content_json', 'JSON decode error')

    def test_create_invalid_not_json_dict(self):
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        content_json='[1,2,3]')
        assert_error(result, 'content_json', 'Expecting a JSON dictionary')

    def test_create_invalid_bad_references(self):
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        owner_org='a',
                                        metadata_collection_id='b',
                                        schema_name='c',
                                        schema_version='d',
                                        infrastructures=[{'id': 'e'}])
        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, '__after', 'Could not find a metadata schema')
        assert_error(result['infrastructures'][0], 'id', 'Not found: Infrastructure')

    def test_create_invalid_deleted_references(self):
        infrastructure = self._generate_infrastructure()
        call_action('organization_delete', id=self.owner_org['id'])
        call_action('metadata_collection_delete', id=self.metadata_collection['id'])
        call_action('metadata_schema_delete', id=self.metadata_schema['id'])
        call_action('infrastructure_delete', id=infrastructure['id'])

        input_dict = self._make_input_dict()
        input_dict['infrastructures'] = [{'id': infrastructure['id']}]
        result, obj = self._call_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError, **input_dict)

        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, '__after', 'Could not find a metadata schema')
        assert_error(result['infrastructures'][0], 'id', 'Not found: Infrastructure')

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
            'owner_org': self.owner_org['id'],
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

        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        metadata_collection_id=new_metadata_collection['id'],
                                        metadata_schema_id=new_metadata_schema['id'])
        assert_group_has_member(infrastructure1['id'], obj.id, 'package', state='deleted')
        assert_group_has_member(infrastructure2['id'], obj.id, 'package')
        assert_group_has_member(new_infrastructure['id'], obj.id, 'package')

    def test_update_valid_partial(self):
        infrastructure = self._generate_infrastructure()
        metadata_record = self._generate_metadata_record(
            infrastructures=[{'id': infrastructure['id']}])

        input_dict = self._make_input_dict()
        input_dict.update({
            'id': metadata_record['id'],
            'name': 'updated-test-metadata-record',
            'content_json': '{ "newtestkey": "newtestvalue" }',
            'infrastructures': [{'id': infrastructure['id']}],
        })
        del input_dict['title']

        result, obj = self._call_action('update', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)

        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        title=metadata_record['title'])
        assert_group_has_member(infrastructure['id'], obj.id, 'package')

    def test_update_invalid_duplicate_name(self):
        metadata_record1 = self._generate_metadata_record()
        metadata_record2 = self._generate_metadata_record()
        result, obj = self._call_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record1['id'],
                                        name=metadata_record2['name'])
        assert_error(result, 'name', 'That URL is already in use.')

    def test_update_invalid_missing_params(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._call_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record['id'])
        assert_error(result, 'owner_org', 'Missing parameter')
        assert_error(result, 'metadata_collection_id', 'Missing parameter')
        assert_error(result, 'infrastructures', 'Missing parameter')
        assert_error(result, 'schema_name', 'Missing parameter')
        assert_error(result, 'schema_version', 'Missing parameter')
        assert_error(result, 'content_json', 'Missing parameter')
        assert_error(result, 'content_raw', 'Missing parameter')
        assert_error(result, 'content_url', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._call_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record['id'],
                                        owner_org='',
                                        metadata_collection_id='',
                                        schema_name='',
                                        schema_version='')
        assert_error(result, 'owner_org', 'Missing value')
        assert_error(result, 'metadata_collection_id', 'Missing value')
        assert_error(result, 'schema_name', 'Missing value')
        assert_error(result, 'schema_version', 'Missing value')

    def test_update_invalid_not_json(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._call_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record['id'],
                                        content_json='not json')
        assert_error(result, 'content_json', 'JSON decode error')

    def test_update_invalid_not_json_dict(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._call_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record['id'],
                                        content_json='[1,2,3]')
        assert_error(result, 'content_json', 'Expecting a JSON dictionary')

    def test_update_invalid_bad_references(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._call_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record['id'],
                                        owner_org='a',
                                        metadata_collection_id='b',
                                        schema_name='c',
                                        schema_version='d',
                                        infrastructures=[{'id': 'e'}])
        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, '__after', 'Could not find a metadata schema')
        assert_error(result['infrastructures'][0], 'id', 'Not found: Infrastructure')

    def test_update_invalid_deleted_references(self):
        metadata_record = self._generate_metadata_record()
        infrastructure = self._generate_infrastructure()
        call_action('organization_delete', id=self.owner_org['id'])
        call_action('metadata_collection_delete', id=self.metadata_collection['id'])
        call_action('metadata_schema_delete', id=self.metadata_schema['id'])
        call_action('infrastructure_delete', id=infrastructure['id'])

        input_dict = self._make_input_dict()
        input_dict['id'] = metadata_record['id']
        input_dict['infrastructures'] = [{'id': infrastructure['id']}]
        result, obj = self._call_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError, **input_dict)

        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, '__after', 'Could not find a metadata schema')
        assert_error(result['infrastructures'][0], 'id', 'Not found: Infrastructure')

    def test_delete_valid(self):
        metadata_record = self._generate_metadata_record()
        self._call_action('delete', 'metadata_record',
                          model_class=ckan_model.Package,
                          id=metadata_record['id'])
