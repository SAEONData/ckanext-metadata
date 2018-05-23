# encoding: utf-8

from ckan.plugins import toolkit as tk
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
        result, obj = self._test_action('create', 'metadata_schema',
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
        result, obj = self._test_action('create', 'metadata_schema',
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
        result, obj = self._test_action('create', 'metadata_schema',
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
        result, obj = self._test_action('create', 'metadata_schema',
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
        result, obj = self._test_action('create', 'metadata_schema',
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
        result, obj = self._test_action('create', 'metadata_schema',
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
        result, obj = self._test_action('create', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._test_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        name=metadata_schema['name'])
        assert_error(result, 'name', 'Duplicate name: Metadata Schema')

    def test_create_invalid_missing_params(self):
        result, obj = self._test_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError)
        assert_error(result, 'schema_name', 'Missing parameter')
        assert_error(result, 'schema_version', 'Missing parameter')
        assert_error(result, 'schema_xsd', 'Missing parameter')
        assert_error(result, 'base_schema_id', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self._test_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        schema_name='')
        assert_error(result, 'schema_name', 'Missing value')

    def test_create_invalid_duplicate(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'schema_name': metadata_schema['schema_name'],
            'schema_version': metadata_schema['schema_version'],
        }
        result, obj = self._test_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._test_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._test_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_schema['id'])
        assert_error(result, 'id', 'Already exists: Metadata Schema')

    def test_create_invalid_sysadmin_self_parent(self):
        new_id = make_uuid()
        input_dict = {
            'id': new_id,
            'base_schema_id': new_id,
        }
        result, obj = self._test_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert_error(result, 'base_schema_id', 'Not found: Metadata Schema')

    def test_create_invalid_bad_parent(self):
        result, obj = self._test_action('create', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        base_schema_id='foo')
        assert_error(result, 'base_schema_id', 'Not found: Metadata Schema')

    def test_create_invalid_deleted_parent(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        call_action('metadata_schema_delete', id=metadata_schema['id'])
        result, obj = self._test_action('create', 'metadata_schema',
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
        result, obj = self._test_action('update', 'metadata_schema',
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
        result, obj = self._test_action('update', 'metadata_schema',
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
        result, obj = self._test_action('update', 'metadata_schema',
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
        result, obj = self._test_action('update', 'metadata_schema',
                                        model_class=ckanext_model.MetadataSchema, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_invalid_duplicate_name(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema1['id'],
            'name': metadata_schema2['name'],
        }
        result, obj = self._test_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'name', 'Duplicate name: Metadata Schema')

    def test_update_invalid_missing_params(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._test_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        id=metadata_schema['id'])
        assert_error(result, 'schema_name', 'Missing parameter')
        assert_error(result, 'schema_version', 'Missing parameter')
        assert_error(result, 'schema_xsd', 'Missing parameter')
        assert_error(result, 'base_schema_id', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._test_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        id=metadata_schema['id'],
                                        schema_name='')
        assert_error(result, 'schema_name', 'Missing value')

    def test_update_invalid_duplicate(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema1['id'],
            'schema_name': metadata_schema2['schema_name'],
            'schema_version': metadata_schema2['schema_version'],
        }
        result, obj = self._test_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_circular_ref_1(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema(base_schema_id=metadata_schema1['id'])
        input_dict = {
            'id': metadata_schema1['id'],
            'base_schema_id': metadata_schema2['id'],
        }
        result, obj = self._test_action('update', 'metadata_schema',
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
        result, obj = self._test_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'base_schema_id', 'Loop in metadata schema hierarchy')

    def test_update_invalid_self_parent(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'base_schema_id': metadata_schema['id'],
        }
        result, obj = self._test_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'base_schema_id', 'Loop in metadata schema hierarchy')

    def test_update_invalid_bad_parent(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self._test_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        id=metadata_schema['id'],
                                        base_schema_id='foo')
        assert_error(result, 'base_schema_id', 'Not found: Metadata Schema')

    def test_update_invalid_deleted_parent(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema()
        call_action('metadata_schema_delete', id=metadata_schema1['id'])
        result, obj = self._test_action('update', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        id=metadata_schema2['id'],
                                        base_schema_id=metadata_schema1['id'])
        assert_error(result, 'base_schema_id', 'Not found: Metadata Schema')

    def test_delete_valid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        self._test_action('delete', 'metadata_schema',
                          model_class=ckanext_model.MetadataSchema,
                          id=metadata_schema['id'])

    def test_delete_with_dependencies(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema(base_schema_id=metadata_schema1['id'])
        metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_schema1['id'])
        metadata_record = ckanext_factories.MetadataRecord(metadata_schema_id=metadata_schema1['id'])

        result, obj = self._test_action('delete', 'metadata_schema',
                                        exception_class=tk.ValidationError,
                                        id=metadata_schema1['id'])

        assert_error(result, 'message', 'Metadata schema has dependent metadata schemas')
        assert_error(result, 'message', 'Metadata schema has dependent metadata records')
        assert ckanext_model.MetadataModel.get(metadata_model['id']).state == 'active'

        call_action('metadata_schema_delete', id=metadata_schema2['id'])
        call_action('metadata_record_delete', id=metadata_record['id'])

        self._test_action('delete', 'metadata_schema',
                          model_class=ckanext_model.MetadataSchema,
                          id=metadata_schema1['id'])
        assert ckanext_model.MetadataModel.get(metadata_model['id']).state == 'deleted'
