# encoding: utf-8

import json

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import call_action

from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_package_has_extra,
    assert_group_has_member,
    assert_error,
    factories as ckanext_factories,
    load_example,
)


class TestMetadataRecordActions(ActionTestBase):

    def setup(self):
        super(TestMetadataRecordActions, self).setup()
        self.owner_org = self._generate_organization()
        self.metadata_collection = self._generate_metadata_collection(organization_id=self.owner_org['id'])
        self.metadata_schema = ckanext_factories.MetadataSchema()

    def _generate_organization(self, **kwargs):
        return ckan_factories.Organization(user=self.normal_user, **kwargs)

    def _generate_metadata_collection(self, **kwargs):
        return ckanext_factories.MetadataCollection(user=self.normal_user, **kwargs)

    def _generate_infrastructure(self, **kwargs):
        return ckanext_factories.Infrastructure(user=self.normal_user, **kwargs)

    def _generate_metadata_record(self, **kwargs):
        return ckanext_factories.MetadataRecord(
            owner_org=self.owner_org['id'],
            metadata_collection_id=self.metadata_collection['id'],
            metadata_schema_id=self.metadata_schema['id'],
            **kwargs
        )

    def _validate_metadata_record(self, metadata_record):
        """
        Create a (trivial) metadata model and validate the given record against it.
        :param metadata_record: metadata record dict
        :return: the metadata model (dict) used to validate the record
        """
        metadata_model = ckanext_factories.MetadataModel(
            metadata_schema_id=metadata_record['metadata_schema_id'],
            infrastructure_id=metadata_record['infrastructures'][0]['id'] if metadata_record['infrastructures'] else ''
        )
        call_action('metadata_record_validate', id=metadata_record['id'], context={'user': self.normal_user['name']})
        assert_package_has_extra(metadata_record['id'], 'validated', True)
        self._assert_metadata_record_has_validation_models(metadata_record['id'], metadata_model['name'])
        self._assert_validate_activity_logged(metadata_record['id'], metadata_model)

        return metadata_model

    def _make_input_dict(self):
        return {
            'title': 'Test Metadata Record',
            'owner_org': self.owner_org['id'],
            'metadata_collection_id': self.metadata_collection['id'],
            'infrastructures': [],
            'metadata_schema_id': self.metadata_schema['id'],
            'metadata_json': '{ "testkey": "testvalue" }',
            'metadata_raw': '<xml/>',
            'metadata_url': 'http://example.net/',
        }

    @staticmethod
    def _make_input_dict_from_output_dict(output_dict):
        input_dict = output_dict.copy()
        input_dict['metadata_json'] = json.dumps(input_dict['metadata_json'])
        return input_dict

    def _assert_metadata_record_ok(self, obj, input_dict, **kwargs):
        """
        Check the resulting package object against the input dict and referenced objects.
        Override comparison values using kwargs.
        """
        assert obj.type == 'metadata_record'
        assert obj.title == kwargs.pop('title', input_dict.get('title'))
        assert obj.name == kwargs.pop('name', 'metadata-' + obj.id)
        assert obj.owner_org == kwargs.pop('owner_org', self.owner_org['id'])
        assert_package_has_extra(obj.id, 'metadata_collection_id', kwargs.pop('metadata_collection_id', self.metadata_collection['id']))
        assert_package_has_extra(obj.id, 'metadata_schema_id', kwargs.pop('metadata_schema_id', self.metadata_schema['id']))
        assert_package_has_extra(obj.id, 'metadata_json', input_dict['metadata_json'], is_json=True)
        assert_package_has_extra(obj.id, 'metadata_raw', input_dict['metadata_raw'])
        assert_package_has_extra(obj.id, 'metadata_url', input_dict['metadata_url'])
        assert_package_has_extra(obj.id, 'validated', kwargs.pop('validated', False))
        assert_package_has_extra(obj.id, 'errors', kwargs.pop('errors', {}), is_json=True)
        assert_package_has_extra(obj.id, 'workflow_state_id', kwargs.pop('workflow_state_id', ''))

    def test_create_valid(self):
        input_dict = self._make_input_dict()
        input_dict['type'] = 'ignore'
        input_dict['validated'] = 'ignore'
        input_dict['errors'] = 'ignore'
        input_dict['workflow_state_id'] = 'ignore'
        result, obj = self._test_action('metadata_record_create', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_create_valid_setname(self):
        input_dict = self._make_input_dict()
        input_dict['name'] = 'test-metadata-record'
        result, obj = self._test_action('metadata_record_create', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict, name=input_dict['name'])

    def test_create_valid_owner_org_byname(self):
        input_dict = self._make_input_dict()
        input_dict['owner_org'] = self.owner_org['name']
        result, obj = self._test_action('metadata_record_create', **input_dict)
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
        result, obj = self._test_action('metadata_record_create', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)
        assert_group_has_member(infrastructure1['id'], obj.id, 'package')
        assert_group_has_member(infrastructure2['id'], obj.id, 'package')

    def test_create_valid_sysadmin_setid(self):
        input_dict = self._make_input_dict()
        input_dict['id'] = make_uuid()
        result, obj = self._test_action('metadata_record_create', sysadmin=True, check_auth=True, **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._test_action('metadata_record_create', should_error=True, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_record = ckanext_factories.MetadataRecord()
        result, obj = self._test_action('metadata_record_create', should_error=True, sysadmin=True, check_auth=True,
                                        id=metadata_record['id'])
        assert_error(result, 'id', 'Dataset id already exists')

    def test_create_invalid_missing_params(self):
        result, obj = self._test_action('metadata_record_create', should_error=True)
        assert_error(result, 'owner_org', 'Missing parameter')
        assert_error(result, 'metadata_collection_id', 'Missing parameter')
        assert_error(result, 'infrastructures', 'Missing parameter')
        assert_error(result, 'metadata_schema_id', 'Missing parameter')
        assert_error(result, 'metadata_json', 'Missing parameter')
        assert_error(result, 'metadata_raw', 'Missing parameter')
        assert_error(result, 'metadata_url', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self._test_action('metadata_record_create', should_error=True,
                                        owner_org='',
                                        metadata_collection_id='',
                                        metadata_schema_id='')
        assert_error(result, 'owner_org', 'Missing value')
        assert_error(result, 'metadata_collection_id', 'Missing value')
        assert_error(result, 'metadata_schema_id', 'Missing value')

    def test_create_invalid_duplicate_name(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('metadata_record_create', should_error=True,
                                        name=metadata_record['name'])
        assert_error(result, 'name', 'That URL is already in use.')

    def test_create_invalid_not_json(self):
        result, obj = self._test_action('metadata_record_create', should_error=True,
                                        metadata_json='not json')
        assert_error(result, 'metadata_json', 'JSON decode error')

    def test_create_invalid_not_json_dict(self):
        result, obj = self._test_action('metadata_record_create', should_error=True,
                                        metadata_json='[1,2,3]')
        assert_error(result, 'metadata_json', 'Expecting a JSON dictionary')

    def test_create_invalid_bad_references(self):
        result, obj = self._test_action('metadata_record_create', should_error=True,
                                        owner_org='a',
                                        metadata_collection_id='b',
                                        metadata_schema_id='c',
                                        infrastructures=[{'id': 'd'}])
        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result['infrastructures'][0], 'id', 'Not found: Infrastructure')

    def test_create_invalid_deleted_references(self):
        infrastructure = self._generate_infrastructure()
        call_action('organization_delete', context={'user': self.normal_user['name']}, id=self.owner_org['id'])
        call_action('metadata_collection_delete', id=self.metadata_collection['id'])
        call_action('metadata_schema_delete', id=self.metadata_schema['id'])
        call_action('infrastructure_delete', id=infrastructure['id'])

        input_dict = self._make_input_dict()
        input_dict['infrastructures'] = [{'id': infrastructure['id']}]
        result, obj = self._test_action('metadata_record_create', should_error=True, **input_dict)

        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result['infrastructures'][0], 'id', 'Not found: Infrastructure')

    def test_create_invalid_owner_org_collection_mismatch(self):
        result, obj = self._test_action('metadata_record_create', should_error=True,
                                        owner_org=self.owner_org['id'],
                                        metadata_collection_id=self._generate_metadata_collection()['id'])
        assert_error(result, '__after', 'owner_org must be the same organization that owns the metadata collection')

    def test_update_valid(self):
        infrastructure1 = self._generate_infrastructure()
        infrastructure2 = self._generate_infrastructure()
        metadata_record = self._generate_metadata_record(infrastructures=[
            {'id': infrastructure1['id']}, {'id': infrastructure2['id']}])

        new_metadata_collection = self._generate_metadata_collection(organization_id=self.owner_org['id'])
        new_metadata_schema = ckanext_factories.MetadataSchema()
        new_infrastructure = self._generate_infrastructure()

        input_dict = {
            'id': metadata_record['id'],
            'name': 'updated-test-metadata-record',
            'title': 'Updated Test Metadata Record',
            'owner_org': self.owner_org['id'],
            'metadata_collection_id': new_metadata_collection['id'],
            'metadata_schema_id': new_metadata_schema['id'],
            'metadata_json': '{ "newtestkey": "newtestvalue" }',
            'metadata_raw': '<updated_xml/>',
            'metadata_url': 'http://updated.example.net/',
            'infrastructures': [
                {'id': infrastructure2['name']},
                {'id': new_infrastructure['name']},
            ],
            'type': 'ignore',
            'validated': 'ignore',
            'errors': 'ignore',
            'workflow_state_id': 'ignore',
        }
        result, obj = self._test_action('metadata_record_update', **input_dict)

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
            'metadata_json': '{ "newtestkey": "newtestvalue" }',
            'infrastructures': [{'id': infrastructure['id']}],
        })
        del input_dict['title']

        result, obj = self._test_action('metadata_record_update', **input_dict)

        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        title=metadata_record['title'])
        assert_group_has_member(infrastructure['id'], obj.id, 'package')

    def test_update_json_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_model = self._validate_metadata_record(metadata_record)

        input_dict = self._make_input_dict_from_output_dict(metadata_record)
        input_dict['metadata_json'] = '{ "newtestkey": "newtestvalue" }'

        result, obj = self._test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        validated=False)
        self._assert_metadata_record_has_validation_models(metadata_record['id'], metadata_model['name'])
        self._assert_invalidate_activity_logged(metadata_record['id'], 'metadata_record_update', obj)

    def test_update_schema_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_model = self._validate_metadata_record(metadata_record)
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        new_metadata_schema = ckanext_factories.MetadataSchema()
        input_dict['metadata_schema_id'] = new_metadata_schema['id']

        result, obj = self._test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        metadata_schema_id=new_metadata_schema['id'],
                                        validated=False)
        self._assert_metadata_record_has_validation_models(metadata_record['id'])
        self._assert_invalidate_activity_logged(metadata_record['id'], 'metadata_record_update', obj)

    def test_update_owner_org_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_model = self._validate_metadata_record(metadata_record)
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        new_organization = self._generate_organization()
        new_metadata_collection = self._generate_metadata_collection(organization_id=new_organization['id'])
        new_metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_record['metadata_schema_id'],
                                                             organization_id=new_organization['id'])
        assert_package_has_extra(metadata_record['id'], 'validated', True)

        input_dict.update({
            'owner_org': new_organization['id'],
            'metadata_collection_id': new_metadata_collection['id'],
        })
        result, obj = self._test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        owner_org=new_organization['id'],
                                        metadata_collection_id=new_metadata_collection['id'],
                                        validated=False)
        self._assert_metadata_record_has_validation_models(metadata_record['id'],
                                                           metadata_model['name'], new_metadata_model['name'])
        self._assert_invalidate_activity_logged(metadata_record['id'], 'metadata_record_update', obj)

    def test_update_infrastructures_invalidate(self):
        infrastructure = self._generate_infrastructure()
        metadata_record = self._generate_metadata_record(infrastructures=[{'id': infrastructure['id']}])
        metadata_model = self._validate_metadata_record(metadata_record)
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        new_infrastructure = self._generate_infrastructure()
        new_metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_record['metadata_schema_id'],
                                                             infrastructure_id=new_infrastructure['id'])
        assert_package_has_extra(metadata_record['id'], 'validated', True)

        input_dict['infrastructures'] = [{'id': new_infrastructure['id']}]
        result, obj = self._test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        validated=False)
        self._assert_metadata_record_has_validation_models(metadata_record['id'], new_metadata_model['name'])
        self._assert_invalidate_activity_logged(metadata_record['id'], 'metadata_record_update', obj)

    def test_update_no_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_model = self._validate_metadata_record(metadata_record)
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        new_infrastructure = self._generate_infrastructure()
        input_dict['infrastructures'] = [{'id': new_infrastructure['id']}]
        result, obj = self._test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        validated=True)
        self._assert_metadata_record_has_validation_models(metadata_record['id'], metadata_model['name'])

        new_organization = self._generate_organization()
        new_metadata_collection = self._generate_metadata_collection(organization_id=new_organization['id'])
        input_dict.update({
            'owner_org': new_organization['id'],
            'metadata_collection_id': new_metadata_collection['id'],
        })
        result, obj = self._test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        owner_org=new_organization['id'],
                                        metadata_collection_id=new_metadata_collection['id'],
                                        validated=True)
        self._assert_metadata_record_has_validation_models(metadata_record['id'], metadata_model['name'])

    def test_update_invalid_duplicate_name(self):
        metadata_record1 = self._generate_metadata_record()
        metadata_record2 = self._generate_metadata_record()
        result, obj = self._test_action('metadata_record_update', should_error=True,
                                        id=metadata_record1['id'],
                                        name=metadata_record2['name'])
        assert_error(result, 'name', 'That URL is already in use.')

    def test_update_invalid_missing_params(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('metadata_record_update', should_error=True,
                                        id=metadata_record['id'])
        assert_error(result, 'owner_org', 'Missing parameter')
        assert_error(result, 'metadata_collection_id', 'Missing parameter')
        assert_error(result, 'infrastructures', 'Missing parameter')
        assert_error(result, 'metadata_schema_id', 'Missing parameter')
        assert_error(result, 'metadata_json', 'Missing parameter')
        assert_error(result, 'metadata_raw', 'Missing parameter')
        assert_error(result, 'metadata_url', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('metadata_record_update', should_error=True,
                                        id=metadata_record['id'],
                                        owner_org='',
                                        metadata_collection_id='',
                                        metadata_schema_id='')
        assert_error(result, 'owner_org', 'Missing value')
        assert_error(result, 'metadata_collection_id', 'Missing value')
        assert_error(result, 'metadata_schema_id', 'Missing value')

    def test_update_invalid_not_json(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('metadata_record_update', should_error=True,
                                        id=metadata_record['id'],
                                        metadata_json='not json')
        assert_error(result, 'metadata_json', 'JSON decode error')

    def test_update_invalid_not_json_dict(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('metadata_record_update', should_error=True,
                                        id=metadata_record['id'],
                                        metadata_json='[1,2,3]')
        assert_error(result, 'metadata_json', 'Expecting a JSON dictionary')

    def test_update_invalid_bad_references(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('metadata_record_update', should_error=True,
                                        id=metadata_record['id'],
                                        owner_org='a',
                                        metadata_collection_id='b',
                                        metadata_schema_id='c',
                                        infrastructures=[{'id': 'd'}])
        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result['infrastructures'][0], 'id', 'Not found: Infrastructure')

    def test_update_invalid_deleted_references(self):
        metadata_record = self._generate_metadata_record()
        infrastructure = self._generate_infrastructure()
        organization = self._generate_organization()
        metadata_collection = self._generate_metadata_collection(organization_id=organization['id'])
        metadata_schema = ckanext_factories.MetadataSchema()
        call_action('organization_delete', context={'user': self.normal_user['name']}, id=organization['id'])
        call_action('metadata_collection_delete', id=metadata_collection['id'])
        call_action('metadata_schema_delete', id=metadata_schema['id'])
        call_action('infrastructure_delete', id=infrastructure['id'])

        result, obj = self._test_action('metadata_record_update', should_error=True,
                                        id=metadata_record['id'],
                                        owner_org=organization['id'],
                                        metadata_collection_id=metadata_collection['id'],
                                        metadata_schema_id=metadata_schema['id'],
                                        infrastructures=[{'id': infrastructure['id']}])

        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result['infrastructures'][0], 'id', 'Not found: Infrastructure')

    def test_update_invalid_owner_org_collection_mismatch(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self._test_action('metadata_record_update', should_error=True,
                                        id=metadata_record['id'],
                                        owner_org=self.owner_org['id'],
                                        metadata_collection_id=self._generate_metadata_collection()['id'])
        assert_error(result, '__after', 'owner_org must be the same organization that owns the metadata collection')

    def test_delete_valid(self):
        metadata_record = self._generate_metadata_record()
        self._test_action('metadata_record_delete',
                          id=metadata_record['id'])

    def test_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_model = self._validate_metadata_record(metadata_record)
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        result, obj = self._test_action('metadata_record_invalidate',
                                        id=metadata_record['id'])
        self._assert_metadata_record_ok(obj, input_dict,
                                        name=input_dict['name'],
                                        validated=False)
        self._assert_metadata_record_has_validation_models(metadata_record['id'], metadata_model['name'])
        self._assert_invalidate_activity_logged(metadata_record['id'], None, None)

    # def test_validate_datacite(self):
    #     metadata_record = self._generate_metadata_record(
    #         metadata_json=load_example('saeon_datacite_record.json'))
    #     metadata_model = ckanext_factories.MetadataModel(
    #         metadata_schema_id=metadata_record['metadata_schema_id'],
    #         model_json=load_example('saeon_datacite_model.json'))
