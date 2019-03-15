# encoding: utf-8

from ckan.tests.helpers import call_action

from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_object_matches_dict,
    assert_error,
    factories as ckanext_factories,
    load_example,
)


class TestMetadataJSONAttrMapActions(ActionTestBase):

    def test_create_valid(self):
        metadata_standard = ckanext_factories.MetadataStandard(
            metadata_template_json=load_example('datacite_4.2_saeon_record.json'))
        input_dict = {
            'json_path': '/identifier/identifier',
            'record_attr': 'name',
            'is_key': True,
            'metadata_standard_id': metadata_standard['id'],
        }
        result, obj = self.test_action('metadata_json_attr_map_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_metadata_standard_byname(self):
        metadata_standard = ckanext_factories.MetadataStandard(
            metadata_template_json=load_example('datacite_4.2_saeon_record.json'))
        input_dict = {
            'json_path': '/identifier/identifier',
            'record_attr': 'name',
            'is_key': False,
            'metadata_standard_id': metadata_standard['name'],
        }
        result, obj = self.test_action('metadata_json_attr_map_create', **input_dict)
        input_dict['metadata_standard_id'] = metadata_standard['id']
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        metadata_standard = ckanext_factories.MetadataStandard(
            metadata_template_json=load_example('datacite_4.2_saeon_record.json'))
        input_dict = {
            'id': make_uuid(),
            'json_path': '/identifier/identifier',
            'record_attr': 'name',
            'is_key': True,
            'metadata_standard_id': metadata_standard['id'],
        }
        result, obj = self.test_action('metadata_json_attr_map_create', sysadmin=True, check_auth=True, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True, check_auth=True,
                                       id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True, sysadmin=True, check_auth=True,
                                       id=metadata_json_attr_map['id'])
        assert_error(result, 'id', 'Already exists: Metadata JSON Attribute Map')

    def test_create_invalid_bad_metadata_standard(self):
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True,
                                       metadata_standard_id='foo')
        assert_error(result, 'metadata_standard_id', 'Not found: Metadata Standard')

    def test_create_invalid_deleted_metadata_standard(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        call_action('metadata_standard_delete', id=metadata_standard['id'])
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True,
                                       metadata_standard_id=metadata_standard['id'])
        assert_error(result, 'metadata_standard_id', 'Not found: Metadata Standard')

    def test_create_invalid_duplicate_standard_jsonpath(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        input_dict = {
            'json_path': metadata_json_attr_map['json_path'],
            'metadata_standard_id': metadata_json_attr_map['metadata_standard_id'],
        }
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True, **input_dict)
        assert_error(result, 'json_path', 'Unique constraint violation')

    def test_create_invalid_duplicate_standard_recordattr(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        input_dict = {
            'record_attr': metadata_json_attr_map['record_attr'],
            'metadata_standard_id': metadata_json_attr_map['metadata_standard_id'],
        }
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True, **input_dict)
        assert_error(result, 'record_attr', 'Unique constraint violation')

    def test_create_invalid_bad_json_path(self):
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True,
                                       json_path='foo')
        assert_error(result, 'json_path', 'Invalid JSON pointer')

    def test_create_invalid_json_path(self):
        metadata_standard = ckanext_factories.MetadataStandard(
            metadata_template_json=load_example('datacite_4.2_saeon_record.json'))
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True,
                                       metadata_standard_id=metadata_standard['id'],
                                       json_path='/identifier/foo')
        assert_error(result, '__after', 'The supplied JSON path is not valid for the metadata template of the supplied metadata standard')

    def test_create_invalid_record_attr(self):
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True,
                                       record_attr='owner_org')
        assert_error(result, 'record_attr', 'The specified key cannot be used')

    def test_create_invalid_missing_params(self):
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True)
        assert_error(result, 'json_path', 'Missing parameter')
        assert_error(result, 'record_attr', 'Missing parameter')
        assert_error(result, 'is_key', 'Missing parameter')
        assert_error(result, 'metadata_standard_id', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self.test_action('metadata_json_attr_map_create', should_error=True,
                                       json_path='',
                                       record_attr='',
                                       metadata_standard_id='')
        assert_error(result, 'json_path', 'Missing value')
        assert_error(result, 'record_attr', 'Missing value')
        assert_error(result, 'metadata_standard_id', 'Missing value')

    def test_update_valid(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        input_dict = {
            'id': metadata_json_attr_map['id'],
            'json_path': '/c/d',
            'record_attr': 'notes',
            'is_key': False,
        }
        result, obj = self.test_action('metadata_json_attr_map_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_invalid_duplicate_standard_jsonpath(self):
        metadata_json_attr_map1 = ckanext_factories.MetadataJSONAttrMap(json_path='/c/d', record_attr='url')
        metadata_json_attr_map2 = ckanext_factories.MetadataJSONAttrMap(metadata_standard_id=metadata_json_attr_map1['metadata_standard_id'])
        input_dict = {
            'id': metadata_json_attr_map1['id'],
            'json_path': metadata_json_attr_map2['json_path'],
        }
        result, obj = self.test_action('metadata_json_attr_map_update', should_error=True, **input_dict)
        assert_error(result, 'json_path', 'Unique constraint violation')

    def test_update_invalid_duplicate_standard_recordattr(self):
        metadata_json_attr_map1 = ckanext_factories.MetadataJSONAttrMap(json_path='/c/d', record_attr='url')
        metadata_json_attr_map2 = ckanext_factories.MetadataJSONAttrMap(metadata_standard_id=metadata_json_attr_map1['metadata_standard_id'])
        input_dict = {
            'id': metadata_json_attr_map1['id'],
            'record_attr': metadata_json_attr_map2['record_attr'],
        }
        result, obj = self.test_action('metadata_json_attr_map_update', should_error=True, **input_dict)
        assert_error(result, 'record_attr', 'Unique constraint violation')

    def test_update_invalid_bad_json_path(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        result, obj = self.test_action('metadata_json_attr_map_update', should_error=True,
                                       id=metadata_json_attr_map['id'],
                                       json_path='foo')
        assert_error(result, 'json_path', 'Invalid JSON pointer')

    def test_update_invalid_json_path(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        metadata_standard = ckanext_factories.MetadataStandard(
            metadata_template_json=load_example('datacite_4.2_saeon_record.json'))
        result, obj = self.test_action('metadata_json_attr_map_update', should_error=True,
                                       id=metadata_json_attr_map['id'],
                                       metadata_standard_id=metadata_standard['id'],
                                       json_path='/identifier/foo')
        assert_error(result, '__after', 'The supplied JSON path is not valid for the metadata template of the supplied metadata standard')

    def test_update_invalid_record_attr(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        result, obj = self.test_action('metadata_json_attr_map_update', should_error=True,
                                       id=metadata_json_attr_map['id'],
                                       record_attr='owner_org')
        assert_error(result, 'record_attr', 'The specified key cannot be used')

    def test_update_invalid_missing_params(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        result, obj = self.test_action('metadata_json_attr_map_update', should_error=True,
                                       id=metadata_json_attr_map['id'])
        assert_error(result, 'json_path', 'Missing parameter')
        assert_error(result, 'record_attr', 'Missing parameter')
        assert_error(result, 'is_key', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        result, obj = self.test_action('metadata_json_attr_map_update', should_error=True,
                                       id=metadata_json_attr_map['id'],
                                       json_path='',
                                       record_attr='')
        assert_error(result, 'json_path', 'Missing value')
        assert_error(result, 'record_attr', 'Missing value')

    def test_delete_valid(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        self.test_action('metadata_json_attr_map_delete',
                         id=metadata_json_attr_map['id'])
