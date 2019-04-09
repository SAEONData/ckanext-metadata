# encoding: utf-8

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import call_action
import ckan.plugins.toolkit as tk

from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_object_matches_dict,
    assert_group_has_extra,
    assert_group_has_member,
    assert_error,
    factories as ckanext_factories,
)


class TestMetadataCollectionActions(ActionTestBase):

    def test_create_valid(self):
        organization = ckan_factories.Organization(user=self.normal_user)
        input_dict = {
            'name': 'test-metadata-collection',
            'title': 'Test Metadata Collection',
            'description': 'This is a test metadata collection',
            'organization_id': organization['id'],
        }
        result, obj = self.test_action('metadata_collection_create', **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        assert_group_has_extra(obj.id, 'organization_id', input_dict['organization_id'])
        del input_dict['organization_id']
        assert_object_matches_dict(obj, input_dict)
        assert_group_has_member(organization['id'], obj.id, 'group', capacity='parent')

    def test_create_valid_organization_byname(self):
        organization = ckan_factories.Organization(user=self.normal_user)
        input_dict = {
            'name': 'test-metadata-collection',
            'organization_id': organization['name'],
        }
        result, obj = self.test_action('metadata_collection_create', **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        assert obj.name == input_dict['name']
        assert_group_has_extra(obj.id, 'organization_id', organization['id'])
        assert_group_has_member(organization['id'], obj.id, 'group', capacity='parent')

    def test_create_invalid_duplicate_name(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        result, obj = self.test_action('metadata_collection_create', should_error=True,
                                       name=metadata_collection['name'])
        assert_error(result, 'name', 'Group name already exists in database')

    def test_create_invalid_bad_organization(self):
        result, obj = self.test_action('metadata_collection_create', should_error=True,
                                       organization_id='foo')
        assert_error(result, 'organization_id', 'Not found: Organization')

    def test_create_invalid_deleted_organization(self):
        organization = ckan_factories.Organization()
        call_action('organization_delete', id=organization['id'])
        result, obj = self.test_action('metadata_collection_create', should_error=True,
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
        result, obj = self.test_action('metadata_collection_update', **input_dict)
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
        result, obj = self.test_action('metadata_collection_update', **input_dict)
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
        result, obj = self.test_action('metadata_collection_update', should_error=True, **input_dict)
        assert_error(result, 'name', 'Group name already exists in database')

    def test_update_invalid_hierarchy_not_allowed(self):
        metadata_collection1 = ckanext_factories.MetadataCollection()
        metadata_collection2 = ckanext_factories.MetadataCollection()
        input_dict = {
            'id': metadata_collection1['id'],
            'groups': [{'name': metadata_collection2['name']}],
        }
        result, obj = self.test_action('metadata_collection_update', should_error=True, **input_dict)
        assert_error(result, '__junk', 'The input field .*groups.* was not expected.')

    def test_update_invalid_cannot_change_organization(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        organization = ckan_factories.Organization()
        input_dict = {
            'id': metadata_collection['id'],
            'organization_id': organization['id'],
        }
        result, obj = self.test_action('metadata_collection_update', should_error=True, **input_dict)
        assert_error(result, 'organization_id', 'The input field organization_id was not expected.')

    def test_delete_valid(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        self.test_action('metadata_collection_delete',
                         id=metadata_collection['id'])

    def test_delete_with_dependencies(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        metadata_record = ckanext_factories.MetadataRecord(
            owner_org=metadata_collection['organization_id'],
            metadata_collection_id=metadata_collection['id'])

        result, obj = self.test_action('metadata_collection_delete', should_error=True,
                                       id=metadata_collection['id'])
        assert_error(result, 'message', 'Metadata collection has dependent metadata records')

        call_action('metadata_record_delete', id=metadata_record['id'])
        self.test_action('metadata_collection_delete',
                         id=metadata_collection['id'])

    def test_member_create_invalid(self):
        metadata_record = ckanext_factories.MetadataRecord()
        metadata_collection = ckanext_factories.MetadataCollection()
        result, obj = self.test_action('member_create', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       id=metadata_collection['id'],
                                       object=metadata_record['id'],
                                       object_type='package',
                                       capacity='public')
        assert_error(result, None, "This action may not be used to alter a metadata record's membership of metadata collections or infrastructures.")

    def test_member_delete_invalid(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        metadata_record = ckanext_factories.MetadataRecord(
            owner_org=metadata_collection['organization_id'],
            metadata_collection_id=metadata_collection['id'])
        result, obj = self.test_action('member_delete', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       id=metadata_collection['id'],
                                       object=metadata_record['id'],
                                       object_type='package')
        assert_error(result, None, "This action may not be used to alter a metadata record's membership of metadata collections or infrastructures.")

    def test_group_create_invalid(self):
        result, obj = self.test_action('group_create', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       type='metadata_collection')
        assert_error(result, None, "This action may not be used for metadata_collection type objects.")

    def test_group_update_invalid(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        result, obj = self.test_action('group_update', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       id=metadata_collection['id'])
        assert_error(result, None, "This action may not be used for metadata_collection type objects.")

    def test_group_delete_invalid(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        result, obj = self.test_action('group_delete', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       id=metadata_collection['id'])
        assert_error(result, None, "This action may not be used for metadata_collection type objects.")
