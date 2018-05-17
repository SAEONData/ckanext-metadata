# encoding: utf-8

import json

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import call_action
import ckan.plugins.toolkit as tk
import ckan.model as ckan_model

from ckanext.metadata import model as ckanext_model
from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_package_has_extra,
    assert_group_has_member,
    assert_error,
    factories as ckanext_factories,
)


class TestMetadataRecordActions(ActionTestBase):

    def setup(self):
        super(TestMetadataRecordActions, self).setup()
        self.owner_org = self._generate_organization()
        self.metadata_collection = ckanext_factories.MetadataCollection(organization_id=self.owner_org['id'])
        self.metadata_schema = ckanext_factories.MetadataSchema()

    def _generate_organization(self):
        return ckan_factories.Organization(
            users=[{'name': self.normal_user['name'], 'capacity': 'editor'}]
        )

    def _generate_infrastructure(self):
        return ckanext_factories.Infrastructure(
            users=[{'name': self.normal_user['name'], 'capacity': 'member'}]
        )

    def _generate_metadata_record(self, **kwargs):
        return ckanext_factories.MetadataRecord(
            owner_org=self.owner_org['id'],
            metadata_collection_id=self.metadata_collection['id'],
            metadata_schema_id=self.metadata_schema['id'],
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

    @staticmethod
    def _make_input_dict_from_output_dict(output_dict):
        input_dict = output_dict.copy()
        metadata_schema_id = input_dict.pop('metadata_schema_id')
        metadata_schema = ckanext_model.MetadataSchema.get(metadata_schema_id)
        input_dict['schema_name'] = metadata_schema.schema_name
        input_dict['schema_version'] = metadata_schema.schema_version
        input_dict['content_json'] = json.dumps(input_dict['content_json'])
        return input_dict

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
        assert_package_has_extra(obj.id, 'content_json', input_dict['content_json'], is_json=True)
        assert_package_has_extra(obj.id, 'content_raw', input_dict['content_raw'])
        assert_package_has_extra(obj.id, 'content_url', input_dict['content_url'])
        assert_package_has_extra(obj.id, 'validation_state', kwargs.pop('validation_state', 'not validated'))

    def test_create_valid(self):
        input_dict = self._make_input_dict()
        input_dict['type'] = 'ignore this'
        input_dict['validation_state'] = 'ignore this too'
        result, obj = self._test_action('create', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_create_valid_setname(self):
        input_dict = self._make_input_dict()
        input_dict['name'] = 'test-metadata-record'
        result, obj = self._test_action('create', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict, name=input_dict['name'])

    def test_create_valid_owner_org_byname(self):
        input_dict = self._make_input_dict()
        input_dict['owner_org'] = self.owner_org['name']
        result, obj = self._test_action('create', 'metadata_record',
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
        result, obj = self._test_action('create', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)
        assert_group_has_member(infrastructure1['id'], obj.id, 'package')
        assert_group_has_member(infrastructure2['id'], obj.id, 'package')

    def test_create_valid_sysadmin_setid(self):
        input_dict = self._make_input_dict()
        input_dict['id'] = make_uuid()
        result, obj = self._test_action('create', 'metadata_record',
                                        model_class=ckan_model.Package,
                                        sysadmin=True, check_auth=True, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._test_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_record = ckanext_factories.MetadataRecord()
        result, obj = self._test_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_record['id'])
        assert_error(result, 'id', 'Dataset id already exists')

    def test_create_invalid_missing_params(self):
        result, obj = self._test_action('create', 'metadata_record',
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
        result, obj = self._test_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        owner_org='',
                                        metadata_collection_id='',
                                        schema_name='')
        assert_error(result, 'owner_org', 'Missing value')
        assert_error(result, 'metadata_collection_id', 'Missing value')
        assert_error(result, 'schema_name', 'Missing value')

    def test_create_invalid_duplicate_name(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        name=metadata_record['name'])
        assert_error(result, 'name', 'That URL is already in use.')

    def test_create_invalid_not_json(self):
        result, obj = self._test_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        content_json='not json')
        assert_error(result, 'content_json', 'JSON decode error')

    def test_create_invalid_not_json_dict(self):
        result, obj = self._test_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        content_json='[1,2,3]')
        assert_error(result, 'content_json', 'Expecting a JSON dictionary')

    def test_create_invalid_bad_references(self):
        result, obj = self._test_action('create', 'metadata_record',
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
        result, obj = self._test_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError, **input_dict)

        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, '__after', 'Could not find a metadata schema')
        assert_error(result['infrastructures'][0], 'id', 'Not found: Infrastructure')

    def test_create_invalid_owner_org_collection_mismatch(self):
        result, obj = self._test_action('create', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        owner_org=self.owner_org['id'],
                                        metadata_collection_id=ckanext_factories.MetadataCollection()['id'])
        assert_error(result, '__after', 'owner_org must be the same organization that owns the metadata collection')

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
            'type': 'ignore this',
            'validation_state': 'ignore this too',
        }
        result, obj = self._test_action('update', 'metadata_record',
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

        result, obj = self._test_action('update', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)

        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        title=metadata_record['title'])
        assert_group_has_member(infrastructure['id'], obj.id, 'package')

    def test_update_valid_set_validation_state(self):
        metadata_record = self._generate_metadata_record()
        assert metadata_record['validation_state'] == 'not validated'

        result, obj = self._test_action('validation_state_update', 'metadata_record',
                                        model_class=ckan_model.Package,
                                        id=metadata_record['id'],
                                        validation_state='valid')
        self._assert_metadata_record_ok(obj, metadata_record,
                                        name=metadata_record['name'],
                                        validation_state='valid')

        result, obj = self._test_action('validation_state_update', 'metadata_record',
                                        model_class=ckan_model.Package,
                                        id=metadata_record['id'],
                                        validation_state='partially valid')
        self._assert_metadata_record_ok(obj, metadata_record,
                                        name=metadata_record['name'],
                                        validation_state='partially valid')

        result, obj = self._test_action('validation_state_update', 'metadata_record',
                                        model_class=ckan_model.Package,
                                        id=metadata_record['id'],
                                        validation_state='invalid')
        self._assert_metadata_record_ok(obj, metadata_record,
                                        name=metadata_record['name'],
                                        validation_state='invalid')

    def test_update_valid_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_record['metadata_schema_id'])
        validation_model_names = call_action('metadata_record_validation_model_list', id=metadata_record['id'])
        assert validation_model_names == [metadata_model['name']]
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        call_action('metadata_record_validation_state_override', id=input_dict['id'], validation_state='valid')
        input_dict['content_json'] = '{ "newtestkey": "newtestvalue" }'
        result, obj = self._test_action('update', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        validation_state='not validated')

        call_action('metadata_record_validation_state_override', id=input_dict['id'], validation_state='invalid')
        new_metadata_schema = ckanext_factories.MetadataSchema()
        input_dict.update({
            'schema_name': new_metadata_schema['schema_name'],
            'schema_version': new_metadata_schema['schema_version'],
        })
        result, obj = self._test_action('update', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        metadata_schema_id=new_metadata_schema['id'],
                                        validation_state='not validated')
        validation_model_names = call_action('metadata_record_validation_model_list', id=input_dict['id'])
        assert validation_model_names == []

    def test_update_valid_owner_org_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_record['metadata_schema_id'],
                                                         organization_id=metadata_record['owner_org'])
        validation_model_names = call_action('metadata_record_validation_model_list', id=metadata_record['id'])
        assert validation_model_names == [metadata_model['name']]
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        new_organization = self._generate_organization()
        new_metadata_collection = ckanext_factories.MetadataCollection(organization_id=new_organization['id'])
        new_metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_record['metadata_schema_id'],
                                                             organization_id=new_organization['id'])

        call_action('metadata_record_validation_state_override', id=input_dict['id'], validation_state='valid')
        input_dict.update({
            'owner_org': new_organization['id'],
            'metadata_collection_id': new_metadata_collection['id'],
        })
        result, obj = self._test_action('update', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        owner_org=new_organization['id'],
                                        metadata_collection_id=new_metadata_collection['id'],
                                        validation_state='not validated')
        validation_model_names = call_action('metadata_record_validation_model_list', id=input_dict['id'])
        assert validation_model_names == [new_metadata_model['name']]

    def test_update_valid_infrastructures_invalidate(self):
        infrastructure = self._generate_infrastructure()
        metadata_record = self._generate_metadata_record(infrastructures=[{'id': infrastructure['id']}])
        metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_record['metadata_schema_id'],
                                                         infrastructure_id=infrastructure['id'])
        validation_model_names = call_action('metadata_record_validation_model_list', id=metadata_record['id'])
        assert validation_model_names == [metadata_model['name']]
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        new_infrastructure = self._generate_infrastructure()
        new_metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_record['metadata_schema_id'],
                                                             infrastructure_id=new_infrastructure['id'])

        call_action('metadata_record_validation_state_override', id=input_dict['id'], validation_state='valid')
        input_dict['infrastructures'] = [{'id': new_infrastructure['id']}]
        result, obj = self._test_action('update', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        validation_state='not validated')
        validation_model_names = call_action('metadata_record_validation_model_list', id=input_dict['id'])
        assert validation_model_names == [new_metadata_model['name']]

    def test_update_valid_no_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_record['metadata_schema_id'])
        validation_model_names = call_action('metadata_record_validation_model_list', id=metadata_record['id'])
        assert validation_model_names == [metadata_model['name']]
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        call_action('metadata_record_validation_state_override', id=input_dict['id'], validation_state='partially valid')
        new_infrastructure = self._generate_infrastructure()
        input_dict['infrastructures'] = [{'id': new_infrastructure['id']}]
        result, obj = self._test_action('update', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        validation_state='partially valid')
        validation_model_names = call_action('metadata_record_validation_model_list', id=input_dict['id'])
        assert validation_model_names == [metadata_model['name']]

        new_organization = self._generate_organization()
        new_metadata_collection = ckanext_factories.MetadataCollection(organization_id=new_organization['id'])
        input_dict.update({
            'owner_org': new_organization['id'],
            'metadata_collection_id': new_metadata_collection['id'],
        })
        result, obj = self._test_action('update', 'metadata_record',
                                        model_class=ckan_model.Package, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        owner_org=new_organization['id'],
                                        metadata_collection_id=new_metadata_collection['id'],
                                        validation_state='partially valid')
        validation_model_names = call_action('metadata_record_validation_model_list', id=input_dict['id'])
        assert validation_model_names == [metadata_model['name']]

    def test_update_invalid_duplicate_name(self):
        metadata_record1 = self._generate_metadata_record()
        metadata_record2 = self._generate_metadata_record()
        result, obj = self._test_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record1['id'],
                                        name=metadata_record2['name'])
        assert_error(result, 'name', 'That URL is already in use.')

    def test_update_invalid_missing_params(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('update', 'metadata_record',
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
        result, obj = self._test_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record['id'],
                                        owner_org='',
                                        metadata_collection_id='',
                                        schema_name='')
        assert_error(result, 'owner_org', 'Missing value')
        assert_error(result, 'metadata_collection_id', 'Missing value')
        assert_error(result, 'schema_name', 'Missing value')

    def test_update_invalid_not_json(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record['id'],
                                        content_json='not json')
        assert_error(result, 'content_json', 'JSON decode error')

    def test_update_invalid_not_json_dict(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record['id'],
                                        content_json='[1,2,3]')
        assert_error(result, 'content_json', 'Expecting a JSON dictionary')

    def test_update_invalid_bad_references(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('update', 'metadata_record',
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
        result, obj = self._test_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError, **input_dict)

        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, '__after', 'Could not find a metadata schema')
        assert_error(result['infrastructures'][0], 'id', 'Not found: Infrastructure')

    def test_update_invalid_bad_validation_state(self):
        metadata_record = self._generate_metadata_record()
        assert metadata_record['validation_state'] == 'not validated'

        result, obj = self._test_action('validation_state_update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record['id'],
                                        validation_state='foo')
        assert_error(result, 'message', 'Invalid validation state')

    def test_update_invalid_owner_org_collection_mismatch(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('update', 'metadata_record',
                                        exception_class=tk.ValidationError,
                                        id=metadata_record['id'],
                                        owner_org=self.owner_org['id'],
                                        metadata_collection_id=ckanext_factories.MetadataCollection()['id'])
        assert_error(result, '__after', 'owner_org must be the same organization that owns the metadata collection')

    def test_delete_valid(self):
        metadata_record = self._generate_metadata_record()
        self._test_action('delete', 'metadata_record',
                          model_class=ckan_model.Package,
                          id=metadata_record['id'])

    def test_invalidate(self):
        metadata_record = self._generate_metadata_record()
        input_dict = self._make_input_dict_from_output_dict(metadata_record)
        call_action('metadata_record_validation_state_override', id=input_dict['id'], validation_state='valid')

        result, obj = self._test_action('invalidate', 'metadata_record',
                                        model_class=ckan_model.Package,
                                        id=metadata_record['id'])
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        validation_state='not validated')
