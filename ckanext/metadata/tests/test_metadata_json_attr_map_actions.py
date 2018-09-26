# encoding: utf-8

from ckan.tests.helpers import call_action

from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_object_matches_dict,
    assert_group_has_extra,
    assert_error,
    factories as ckanext_factories,
    load_example,
)


class TestMetadataJSONAttrMapActions(ActionTestBase):

    def test_create_valid(self):
        metadata_standard = ckanext_factories.MetadataStandard(
            metadata_template_json=load_example('saeon_datacite_record.json'))
        input_dict = {
            'json_path': '/identifier/identifier',
            'record_attr': 'name',
            'is_key': True,
            'is_extra': False,
            'metadata_standard_id': metadata_standard['id'],
        }
        result, obj = self.test_action('metadata_json_attr_map_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_metadata_standard_byname(self):
        metadata_standard = ckanext_factories.MetadataStandard(
            metadata_template_json=load_example('saeon_datacite_record.json'))
        input_dict = {
            'json_path': '/identifier/identifier',
            'record_attr': 'name',
            'is_key': False,
            'is_extra': True,
            'metadata_standard_id': metadata_standard['name'],
        }
        result, obj = self.test_action('metadata_json_attr_map_create', **input_dict)
        input_dict['metadata_standard_id'] = metadata_standard['id']
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        metadata_standard = ckanext_factories.MetadataStandard(
            metadata_template_json=load_example('saeon_datacite_record.json'))
        input_dict = {
            'id': make_uuid(),
            'json_path': '/identifier/identifier',
            'record_attr': 'name',
            'is_key': True,
            'is_extra': False,
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

    def test_update_valid(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        input_dict = {
            'id': metadata_json_attr_map['id'],
            'json_path': '/c/d',
            'record_attr': 'notes',
            'is_key': False,
            'is_extra': False,
            'metadata_standard_id': metadata_json_attr_map['metadata_standard_id'],
        }
        result, obj = self.test_action('metadata_json_attr_map_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_invalid_duplicate_standard_jsonpath(self):
        metadata_json_attr_map1 = ckanext_factories.MetadataJSONAttrMap()
        metadata_json_attr_map2 = ckanext_factories.MetadataJSONAttrMap()
        input_dict = {
            'id': metadata_json_attr_map1['id'],
            'json_path': metadata_json_attr_map2['json_path'],
            'metadata_standard_id': metadata_json_attr_map2['metadata_standard_id'],
        }
        result, obj = self.test_action('metadata_json_attr_map_update', should_error=True, **input_dict)
        assert_error(result, 'json_path', 'Unique constraint violation')

    def test_update_invalid_duplicate_standard_recordattr(self):
        metadata_json_attr_map1 = ckanext_factories.MetadataJSONAttrMap()
        metadata_json_attr_map2 = ckanext_factories.MetadataJSONAttrMap()
        input_dict = {
            'id': metadata_json_attr_map1['id'],
            'record_attr': metadata_json_attr_map2['record_attr'],
            'metadata_standard_id': metadata_json_attr_map2['metadata_standard_id'],
        }
        result, obj = self.test_action('metadata_json_attr_map_update', should_error=True, **input_dict)
        assert_error(result, 'record_attr', 'Unique constraint violation')

    def test_delete_valid(self):
        metadata_json_attr_map = ckanext_factories.MetadataJSONAttrMap()
        self.test_action('metadata_json_attr_map_delete',
                         id=metadata_json_attr_map['id'])
