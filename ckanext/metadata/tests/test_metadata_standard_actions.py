# encoding: utf-8

from ckan.tests.helpers import call_action

from ckanext.metadata import model as ckanext_model
from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    generate_name,
    assert_object_matches_dict,
    assert_error,
    factories as ckanext_factories,
)


class TestMetadataStandardActions(ActionTestBase):

    def test_create_valid(self):
        input_dict = {
            'description': 'This is a test metadata standard',
            'standard_name': 'DataCite',
            'standard_version': '1.0',
            'parent_standard_id': '',
            'metadata_template_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self.test_action('metadata_standard_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == generate_name(input_dict['standard_name'], input_dict['standard_version'])

    def test_create_valid_setname(self):
        input_dict = {
            'name': 'test-metadata-standard',
            'standard_name': 'DataCite',
            'standard_version': '1.0',
            'parent_standard_id': '',
            'metadata_template_json': '{}',
        }
        result, obj = self.test_action('metadata_standard_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_parent(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'standard_name': 'DataCite',
            'standard_version': '1.0',
            'parent_standard_id': metadata_standard['id'],
            'metadata_template_json': '{}',
        }
        result, obj = self.test_action('metadata_standard_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_parent_byname(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'standard_name': 'DataCite',
            'standard_version': '1.0',
            'parent_standard_id': metadata_standard['name'],
            'metadata_template_json': '{}',
        }
        result, obj = self.test_action('metadata_standard_create', **input_dict)
        input_dict['parent_standard_id'] = metadata_standard['id']
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        input_dict = {
            'id': make_uuid(),
            'standard_name': 'DataCite',
            'standard_version': '1.0',
            'parent_standard_id': '',
            'metadata_template_json': '{}',
        }
        result, obj = self.test_action('metadata_standard_create', sysadmin=True, check_auth=True, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_name_new_version(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'standard_name': metadata_standard['standard_name'],
            'standard_version': metadata_standard['standard_version'] + 'a',
            'parent_standard_id': '',
            'metadata_template_json': '{}',
        }
        result, obj = self.test_action('metadata_standard_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_version_different_name(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'standard_name': metadata_standard['standard_name'] + '_foo',
            'standard_version': metadata_standard['standard_version'],
            'parent_standard_id': '',
            'metadata_template_json': '{}',
        }
        result, obj = self.test_action('metadata_standard_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        result, obj = self.test_action('metadata_standard_create', should_error=True,
                                       name=metadata_standard['name'])
        assert_error(result, 'name', 'Duplicate name: Metadata Standard')

    def test_create_invalid_missing_params(self):
        result, obj = self.test_action('metadata_standard_create', should_error=True)
        assert_error(result, 'standard_name', 'Missing parameter')
        assert_error(result, 'standard_version', 'Missing parameter')
        assert_error(result, 'parent_standard_id', 'Missing parameter')
        assert_error(result, 'metadata_template_json', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self.test_action('metadata_standard_create', should_error=True,
                                       standard_name='',
                                       metadata_template_json='')
        assert_error(result, 'standard_name', 'Missing value')
        assert_error(result, 'metadata_template_json', 'Missing value')

    def test_create_invalid_duplicate(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'standard_name': metadata_standard['standard_name'],
            'standard_version': metadata_standard['standard_version'],
        }
        result, obj = self.test_action('metadata_standard_create', should_error=True, **input_dict)
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self.test_action('metadata_standard_create', should_error=True, check_auth=True,
                                       id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        result, obj = self.test_action('metadata_standard_create', should_error=True, sysadmin=True, check_auth=True,
                                       id=metadata_standard['id'])
        assert_error(result, 'id', 'Already exists: Metadata Standard')

    def test_create_invalid_sysadmin_self_parent(self):
        new_id = make_uuid()
        input_dict = {
            'id': new_id,
            'parent_standard_id': new_id,
        }
        result, obj = self.test_action('metadata_standard_create', should_error=True,
                                       sysadmin=True, check_auth=True, **input_dict)
        assert_error(result, 'parent_standard_id', 'Not found: Metadata Standard')

    def test_create_invalid_bad_parent(self):
        result, obj = self.test_action('metadata_standard_create', should_error=True,
                                       parent_standard_id='foo')
        assert_error(result, 'parent_standard_id', 'Not found: Metadata Standard')

    def test_create_invalid_deleted_parent(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        call_action('metadata_standard_delete', id=metadata_standard['id'])
        result, obj = self.test_action('metadata_standard_create', should_error=True,
                                       parent_standard_id=metadata_standard['id'])
        assert_error(result, 'parent_standard_id', 'Not found: Metadata Standard')

    def test_update_valid(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'id': metadata_standard['id'],
            'description': 'Updated test metadata standard description',
            'standard_name': 'Updated Standard Name',
            'standard_version': 'v99',
            'parent_standard_id': '',
            'metadata_template_json': '{ "newtestkey": "newtestvalue" }',
        }
        result, obj = self.test_action('metadata_standard_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == generate_name(input_dict['standard_name'], input_dict['standard_version'])

    def test_update_valid_partial(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'id': metadata_standard['id'],
            'name': 'updated-test-metadata-standard',
            'standard_name': metadata_standard['standard_name'],
            'standard_version': metadata_standard['standard_name'],
            'parent_standard_id': '',
            'metadata_template_json': '{}',
        }
        result, obj = self.test_action('metadata_standard_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.description == metadata_standard['description']

    def test_update_valid_change_parent_1(self):
        metadata_standard1 = ckanext_factories.MetadataStandard()
        metadata_standard2 = ckanext_factories.MetadataStandard()
        input_dict = {
            'id': metadata_standard1['id'],
            'standard_name': metadata_standard1['standard_name'],
            'standard_version': metadata_standard1['standard_version'],
            'parent_standard_id': metadata_standard2['id'],
            'metadata_template_json': '{}',
        }
        result, obj = self.test_action('metadata_standard_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_change_parent_2(self):
        metadata_standard1 = ckanext_factories.MetadataStandard()
        metadata_standard2 = ckanext_factories.MetadataStandard(parent_standard_id=metadata_standard1['id'])
        metadata_standard3 = ckanext_factories.MetadataStandard(parent_standard_id=metadata_standard2['id'])
        input_dict = {
            'id': metadata_standard3['id'],
            'standard_name': metadata_standard3['standard_name'],
            'standard_version': metadata_standard3['standard_version'],
            'parent_standard_id': metadata_standard1['id'],
            'metadata_template_json': '{}',
        }
        result, obj = self.test_action('metadata_standard_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_invalid_duplicate_name(self):
        metadata_standard1 = ckanext_factories.MetadataStandard()
        metadata_standard2 = ckanext_factories.MetadataStandard()
        input_dict = {
            'id': metadata_standard1['id'],
            'name': metadata_standard2['name'],
        }
        result, obj = self.test_action('metadata_standard_update', should_error=True, **input_dict)
        assert_error(result, 'name', 'Duplicate name: Metadata Standard')

    def test_update_invalid_missing_params(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        result, obj = self.test_action('metadata_standard_update', should_error=True,
                                       id=metadata_standard['id'])
        assert_error(result, 'standard_name', 'Missing parameter')
        assert_error(result, 'standard_version', 'Missing parameter')
        assert_error(result, 'parent_standard_id', 'Missing parameter')
        assert_error(result, 'metadata_template_json', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        result, obj = self.test_action('metadata_standard_update', should_error=True,
                                       id=metadata_standard['id'],
                                       standard_name='',
                                       metadata_template_json='')
        assert_error(result, 'standard_name', 'Missing value')
        assert_error(result, 'metadata_template_json', 'Missing value')

    def test_update_invalid_duplicate(self):
        metadata_standard1 = ckanext_factories.MetadataStandard()
        metadata_standard2 = ckanext_factories.MetadataStandard()
        input_dict = {
            'id': metadata_standard1['id'],
            'standard_name': metadata_standard2['standard_name'],
            'standard_version': metadata_standard2['standard_version'],
        }
        result, obj = self.test_action('metadata_standard_update', should_error=True, **input_dict)
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_circular_ref_1(self):
        metadata_standard1 = ckanext_factories.MetadataStandard()
        metadata_standard2 = ckanext_factories.MetadataStandard(parent_standard_id=metadata_standard1['id'])
        input_dict = {
            'id': metadata_standard1['id'],
            'parent_standard_id': metadata_standard2['id'],
        }
        result, obj = self.test_action('metadata_standard_update', should_error=True, **input_dict)
        assert_error(result, 'parent_standard_id', 'Loop in metadata standard hierarchy')

    def test_update_invalid_circular_ref_2(self):
        metadata_standard1 = ckanext_factories.MetadataStandard()
        metadata_standard2 = ckanext_factories.MetadataStandard(parent_standard_id=metadata_standard1['id'])
        metadata_standard3 = ckanext_factories.MetadataStandard(parent_standard_id=metadata_standard2['id'])
        input_dict = {
            'id': metadata_standard1['id'],
            'parent_standard_id': metadata_standard3['id'],
        }
        result, obj = self.test_action('metadata_standard_update', should_error=True, **input_dict)
        assert_error(result, 'parent_standard_id', 'Loop in metadata standard hierarchy')

    def test_update_invalid_self_parent(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'id': metadata_standard['id'],
            'parent_standard_id': metadata_standard['id'],
        }
        result, obj = self.test_action('metadata_standard_update', should_error=True, **input_dict)
        assert_error(result, 'parent_standard_id', 'Loop in metadata standard hierarchy')

    def test_update_invalid_bad_parent(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        result, obj = self.test_action('metadata_standard_update', should_error=True,
                                       id=metadata_standard['id'],
                                       parent_standard_id='foo')
        assert_error(result, 'parent_standard_id', 'Not found: Metadata Standard')

    def test_update_invalid_deleted_parent(self):
        metadata_standard1 = ckanext_factories.MetadataStandard()
        metadata_standard2 = ckanext_factories.MetadataStandard()
        call_action('metadata_standard_delete', id=metadata_standard1['id'])
        result, obj = self.test_action('metadata_standard_update', should_error=True,
                                       id=metadata_standard2['id'],
                                       parent_standard_id=metadata_standard1['id'])
        assert_error(result, 'parent_standard_id', 'Not found: Metadata Standard')

    def test_delete_valid(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        self.test_action('metadata_standard_delete',
                         id=metadata_standard['id'])

    def test_delete_with_child_standards(self):
        metadata_standard1 = ckanext_factories.MetadataStandard()
        metadata_standard2 = ckanext_factories.MetadataStandard(parent_standard_id=metadata_standard1['id'])
        assert metadata_standard2['parent_standard_id'] == metadata_standard1['id']

        self.test_action('metadata_standard_delete',
                         id=metadata_standard1['id'])
        metadata_standard2['parent_standard_id'] = None
        del metadata_standard2['revision_id']
        del metadata_standard2['display_name']
        assert_object_matches_dict(ckanext_model.MetadataStandard.get(metadata_standard2['id']), metadata_standard2, json_values=('metadata_template_json',))

    def test_delete_with_dependencies(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        metadata_schema = ckanext_factories.MetadataSchema(metadata_standard_id=metadata_standard['id'])
        metadata_record = ckanext_factories.MetadataRecord(metadata_standard_id=metadata_standard['id'])

        result, obj = self.test_action('metadata_standard_delete', should_error=True,
                                       id=metadata_standard['id'])

        assert_error(result, 'message', 'Metadata standard has dependent metadata records')
        assert ckanext_model.MetadataSchema.get(metadata_schema['id']).state == 'active'

        call_action('metadata_record_delete', id=metadata_record['id'])
        self.test_action('metadata_standard_delete',
                         id=metadata_standard['id'])
        assert ckanext_model.MetadataSchema.get(metadata_schema['id']).state == 'deleted'
