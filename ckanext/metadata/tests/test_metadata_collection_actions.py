# encoding: utf-8

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import call_action
import ckan.plugins.toolkit as tk

from ckanext.metadata.tests import (
    ActionTestBase,
    assert_object_matches_dict,
    assert_group_has_extra,
    assert_group_has_member,
    assert_error,
    factories as ckanext_factories,
    assert_package_has_extra,
    process_queued_tasks,
)


class TestMetadataCollectionActions(ActionTestBase):

    def test_create_valid(self):
        organization = ckan_factories.Organization(user=self.normal_user)
        input_dict = {
            'name': 'test-metadata-collection',
            'title': 'Test Metadata Collection',
            'description': 'This is a test metadata collection',
            'organization_id': organization['id'],
            'doi_collection': 'test.doi',
            'auto_create_doi': True,
        }
        result, obj = self.test_action('metadata_collection_create', **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        assert_group_has_extra(obj.id, 'organization_id', input_dict['organization_id'])
        assert_group_has_extra(obj.id, 'doi_collection', 'TEST.DOI')
        assert_group_has_extra(obj.id, 'auto_create_doi', True)
        del input_dict['organization_id']
        del input_dict['doi_collection']
        del input_dict['auto_create_doi']
        assert_object_matches_dict(obj, input_dict)
        assert_group_has_member(organization['id'], obj.id, 'group', capacity='parent')

    def test_create_valid_organization_byname(self):
        organization = ckan_factories.Organization(user=self.normal_user)
        input_dict = {
            'name': 'test-metadata-collection',
            'organization_id': organization['name'],
            'doi_collection': '',
            'auto_create_doi': False,
        }
        result, obj = self.test_action('metadata_collection_create', **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        assert obj.name == input_dict['name']
        assert_group_has_extra(obj.id, 'organization_id', organization['id'])
        assert_group_has_extra(obj.id, 'doi_collection', '')
        assert_group_has_extra(obj.id, 'auto_create_doi', False)
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

    def test_create_invalid_bad_doi_collection(self):
        result, obj = self.test_action('metadata_collection_create', should_error=True,
                                       doi_collection='has spaces')
        assert_error(result, 'doi_collection', 'Invalid DOI collection identifier')

    def test_update_valid(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        input_dict = {
            'id': metadata_collection['id'],
            'name': 'updated-test-metadata-collection',
            'title': 'Updated Test Metadata Collection',
            'description': 'Updated test metadata collection',
            'organization_id': metadata_collection['organization_id'],
            'doi_collection': 'updated.test.doi',
            'auto_create_doi': True,
        }
        result, obj = self.test_action('metadata_collection_update', **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        del input_dict['organization_id']
        del input_dict['doi_collection']
        del input_dict['auto_create_doi']
        assert_object_matches_dict(obj, input_dict)
        assert_group_has_extra(obj.id, 'organization_id', metadata_collection['organization_id'])
        assert_group_has_extra(obj.id, 'doi_collection', 'UPDATED.TEST.DOI')
        assert_group_has_extra(obj.id, 'auto_create_doi', True)

    def test_update_valid_partial(self):
        metadata_collection = ckanext_factories.MetadataCollection()
        input_dict = {
            'id': metadata_collection['id'],
            'title': 'Updated Test Metadata Collection',
            'organization_id': metadata_collection['organization_id'],
            'doi_collection': 'updated.test.doi',
            'auto_create_doi': True,
        }
        result, obj = self.test_action('metadata_collection_update', **input_dict)
        assert obj.type == 'metadata_collection'
        assert obj.is_organization == False
        assert obj.title == input_dict['title']
        assert obj.name == metadata_collection['name']
        assert obj.description == metadata_collection['description']
        assert_group_has_extra(obj.id, 'organization_id', metadata_collection['organization_id'])
        assert_group_has_extra(obj.id, 'doi_collection', 'UPDATED.TEST.DOI')
        assert_group_has_extra(obj.id, 'auto_create_doi', True)

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
        assert_error(result, 'organization_id', 'Organization cannot be changed')

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

    def _bulk_action_setup(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        self.workflow_transition_1 = ckanext_factories.WorkflowTransition(from_state_id='')
        self.workflow_transition_2 = ckanext_factories.WorkflowTransition(from_state_id=self.workflow_transition_1['to_state_id'])
        self.metadata_collection = ckanext_factories.MetadataCollection()
        self.metadata_records = [
            ckanext_factories.MetadataRecord(
                owner_org=self.metadata_collection['organization_id'],
                metadata_collection_id=self.metadata_collection['id'],
                metadata_standard_id=metadata_schema['metadata_standard_id'])
            for _ in range(3)
        ]

        # modify the middle record; this should not affect processing of the surrounding records
        self.test_action('metadata_record_validate', id=self.metadata_records[1]['id'])
        self.test_action('metadata_record_workflow_state_override', id=self.metadata_records[1]['id'],
                         workflow_state_id=self.workflow_transition_1['to_state_id'])
        assert_package_has_extra(self.metadata_records[1]['id'], 'validated', True)
        assert_package_has_extra(self.metadata_records[1]['id'], 'workflow_state_id', self.workflow_transition_1['to_state_id'])

    def test_bulk_validate(self):
        self._bulk_action_setup()

        self.test_action('metadata_collection_validate', id=self.metadata_collection['id'])
        assert_package_has_extra(self.metadata_records[0]['id'], 'validated', True)
        assert_package_has_extra(self.metadata_records[1]['id'], 'validated', True)
        assert_package_has_extra(self.metadata_records[2]['id'], 'validated', True)

    def test_bulk_validate_async(self):
        self._bulk_action_setup()

        self.test_action('metadata_collection_validate', id=self.metadata_collection['id'], async=True)
        assert_package_has_extra(self.metadata_records[0]['id'], 'validated', False)
        assert_package_has_extra(self.metadata_records[1]['id'], 'validated', True)
        assert_package_has_extra(self.metadata_records[2]['id'], 'validated', False)

        process_queued_tasks()
        assert_package_has_extra(self.metadata_records[0]['id'], 'validated', True)
        assert_package_has_extra(self.metadata_records[1]['id'], 'validated', True)
        assert_package_has_extra(self.metadata_records[2]['id'], 'validated', True)

    def test_bulk_transition(self):
        self._bulk_action_setup()

        self.test_action('metadata_collection_workflow_state_transition',
                         id=self.metadata_collection['id'],
                         workflow_state_id=self.workflow_transition_2['to_state_id'])
        assert_package_has_extra(self.metadata_records[0]['id'], 'workflow_state_id', '')
        assert_package_has_extra(self.metadata_records[1]['id'], 'workflow_state_id', self.workflow_transition_2['to_state_id'])
        assert_package_has_extra(self.metadata_records[2]['id'], 'workflow_state_id', '')

        self.test_action('metadata_collection_workflow_state_transition',
                         id=self.metadata_collection['id'],
                         workflow_state_id=self.workflow_transition_1['to_state_id'])
        assert_package_has_extra(self.metadata_records[0]['id'], 'workflow_state_id', self.workflow_transition_1['to_state_id'])
        assert_package_has_extra(self.metadata_records[1]['id'], 'workflow_state_id', self.workflow_transition_2['to_state_id'])
        assert_package_has_extra(self.metadata_records[2]['id'], 'workflow_state_id', self.workflow_transition_1['to_state_id'])

    def test_bulk_transition_async(self):
        self._bulk_action_setup()

        self.test_action('metadata_collection_workflow_state_transition',
                         id=self.metadata_collection['id'],
                         workflow_state_id=self.workflow_transition_2['to_state_id'],
                         async=True)
        assert_package_has_extra(self.metadata_records[0]['id'], 'workflow_state_id', '')
        assert_package_has_extra(self.metadata_records[1]['id'], 'workflow_state_id', self.workflow_transition_1['to_state_id'])
        assert_package_has_extra(self.metadata_records[2]['id'], 'workflow_state_id', '')

        process_queued_tasks()
        assert_package_has_extra(self.metadata_records[0]['id'], 'workflow_state_id', '')
        assert_package_has_extra(self.metadata_records[1]['id'], 'workflow_state_id', self.workflow_transition_2['to_state_id'])
        assert_package_has_extra(self.metadata_records[2]['id'], 'workflow_state_id', '')

        self.test_action('metadata_collection_workflow_state_transition',
                         id=self.metadata_collection['id'],
                         workflow_state_id=self.workflow_transition_1['to_state_id'],
                         async=True)
        assert_package_has_extra(self.metadata_records[0]['id'], 'workflow_state_id', '')
        assert_package_has_extra(self.metadata_records[1]['id'], 'workflow_state_id', self.workflow_transition_2['to_state_id'])
        assert_package_has_extra(self.metadata_records[2]['id'], 'workflow_state_id', '')

        process_queued_tasks()
        assert_package_has_extra(self.metadata_records[0]['id'], 'workflow_state_id', self.workflow_transition_1['to_state_id'])
        assert_package_has_extra(self.metadata_records[1]['id'], 'workflow_state_id', self.workflow_transition_2['to_state_id'])
        assert_package_has_extra(self.metadata_records[2]['id'], 'workflow_state_id', self.workflow_transition_1['to_state_id'])
