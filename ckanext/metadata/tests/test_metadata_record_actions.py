# encoding: utf-8

import json
import re
from datetime import datetime

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import call_action
import ckan.plugins.toolkit as tk
import ckan.model as ckan_model
from ckan.lib.redis import connect_to_redis
from ckanext.metadata.common import DOI_RE

from ckanext.metadata.tests import (
    ActionTestBase,
    assert_package_has_extra,
    assert_group_has_member,
    assert_error,
    assert_object_matches_dict,
    assert_package_has_attribute,
    assert_metadata_record_has_validation_schemas,
    factories as ckanext_factories,
    load_example,
)


class TestMetadataRecordActions(ActionTestBase):

    def setup(self):
        super(TestMetadataRecordActions, self).setup()
        self.owner_org = self._generate_organization()
        self.metadata_collection = self._generate_metadata_collection(organization_id=self.owner_org['id'])
        self.metadata_standard = ckanext_factories.MetadataStandard(
            metadata_template_json=load_example('saeon_odp_4.2_record.json'))

    def _generate_organization(self, **kwargs):
        return ckan_factories.Organization(user=self.normal_user, **kwargs)

    def _generate_metadata_collection(self, **kwargs):
        return ckanext_factories.MetadataCollection(user=self.normal_user, **kwargs)

    def _generate_infrastructure(self, **kwargs):
        return ckanext_factories.Infrastructure(user=self.normal_user, **kwargs)

    def _generate_metadata_record(self, **kwargs):
        return ckanext_factories.MetadataRecord(
            owner_org=kwargs.pop('owner_org', self.owner_org['id']),
            metadata_collection_id=kwargs.pop('metadata_collection_id', self.metadata_collection['id']),
            metadata_standard_id=kwargs.pop('metadata_standard_id', self.metadata_standard['id']),
            **kwargs
        )

    def _validate_metadata_record(self, metadata_record):
        """
        Create a (trivial) metadata schema and validate the given record against it.
        :param metadata_record: metadata record dict
        :return: the metadata schema (dict) used to validate the record
        """
        metadata_schema = ckanext_factories.MetadataSchema(
            metadata_standard_id=metadata_record['metadata_standard_id'],
        )
        call_action('metadata_record_validate', id=metadata_record['id'], context={'user': self.normal_user['name']})
        assert_package_has_extra(metadata_record['id'], 'validated', True)
        assert_metadata_record_has_validation_schemas(metadata_record['id'], metadata_schema['name'])
        self.assert_validate_activity_logged(metadata_record['id'], metadata_schema)

        return metadata_schema

    def _make_input_dict(self):
        return {
            'title': 'Test Metadata Record',
            'author': 'Someone',
            'owner_org': self.owner_org['id'],
            'metadata_collection_id': self.metadata_collection['id'],
            'metadata_standard_id': self.metadata_standard['id'],
            'metadata_json': '{ "testkey": "testvalue" }',
            'doi': '',
        }

    @staticmethod
    def _make_input_dict_from_output_dict(output_dict):
        input_dict = output_dict.copy()
        # input_dict['metadata_json'] = json.dumps(input_dict['metadata_json'])
        return input_dict

    def _assert_metadata_record_ok(self, obj, input_dict, **kwargs):
        """
        Check the resulting package object against the input dict and referenced objects.
        Override comparison values using kwargs.
        """
        assert obj.type == 'metadata_record'
        assert obj.title == kwargs.pop('title', input_dict.get('title'))
        assert obj.author == kwargs.pop('author', input_dict.get('author'))
        assert obj.name == kwargs.pop('name', obj.id)
        assert obj.owner_org == kwargs.pop('owner_org', self.owner_org['id'])
        assert obj.private == kwargs.pop('private', True)
        assert obj.url == kwargs.pop('url', None)
        metadata_collection_id = kwargs.pop('metadata_collection_id', self.metadata_collection['id'])
        assert_package_has_extra(obj.id, 'metadata_collection_id', metadata_collection_id)
        assert_package_has_extra(obj.id, 'metadata_standard_id', kwargs.pop('metadata_standard_id', self.metadata_standard['id']))
        assert_package_has_extra(obj.id, 'metadata_json', input_dict['metadata_json'], is_json=True)
        assert_package_has_extra(obj.id, 'doi', kwargs.pop('doi', input_dict['doi']))
        assert_package_has_extra(obj.id, 'validated', kwargs.pop('validated', False))
        assert_package_has_extra(obj.id, 'errors', kwargs.pop('errors', {}), is_json=True)
        assert_package_has_extra(obj.id, 'workflow_state_id', kwargs.pop('workflow_state_id', ''))
        assert_group_has_member(metadata_collection_id, obj.id, 'package')

    def _define_attribute_map(self, json_path, record_attr, is_key=False, **kwargs):
        return ckanext_factories.MetadataJSONAttrMap(
            json_path=json_path,
            record_attr=record_attr,
            is_key=is_key,
            metadata_standard_id=kwargs.pop('metadata_standard_id', self.metadata_standard['id'])
        )

    @staticmethod
    def _grant_privilege(user_id, organization_name, role_name):
        token_data = {
            'privileges': [{
                'institution': organization_name,
                'role': role_name,
            }]
        }
        redis = connect_to_redis()
        key = 'oidc_token_data:' + user_id
        redis.setex(key, json.dumps(token_data), 300)

    def test_create_valid(self):
        input_dict = self._make_input_dict()
        input_dict.update({
            # the following fields are set automatically, so any values provided as input should be ignored
            'type': 'ignore',
            'validated': 'ignore',
            'errors': 'ignore',
            'workflow_state_id': 'ignore',
            'private': 'ignore',
        })
        result, obj = self.test_action('metadata_record_create', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_create_valid_with_doi(self):
        input_dict = self._make_input_dict()
        input_dict['doi'] = '10.1234/xyz.123'
        result, obj = self.test_action('metadata_record_create', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        doi=input_dict['doi'].upper())

    def test_create_valid_auto_generate_doi(self):
        metadata_collection = self._generate_metadata_collection(organization_id=self.owner_org['id'],
                                                                 doi_collection='foo')
        input_dict = self._make_input_dict()
        input_dict['metadata_collection_id'] = metadata_collection['id']
        input_dict['auto_assign_doi'] = True
        result, obj = self.test_action('metadata_record_create', **input_dict)
        doi = ckan_model.Session.query(ckan_model.PackageExtra.value) \
            .filter_by(package_id=obj.id, key='doi') \
            .scalar()
        assert re.match(DOI_RE, doi)
        assert '/FOO.' in doi

    def test_create_valid_auto_generate_doi_update_json(self):
        metadata_collection = self._generate_metadata_collection(organization_id=self.owner_org['id'],
                                                                 doi_collection='')
        self._define_attribute_map('/identifier/identifier', 'doi')
        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        del metadata_dict['identifier']['identifier']
        metadata_json = json.dumps(metadata_dict)

        input_dict = self._make_input_dict()
        input_dict['metadata_collection_id'] = metadata_collection['id']
        input_dict['metadata_json'] = metadata_json
        input_dict['auto_assign_doi'] = True

        result, obj = self.test_action('metadata_record_create', **input_dict)
        doi = ckan_model.Session.query(ckan_model.PackageExtra.value) \
            .filter_by(package_id=obj.id, key='doi') \
            .scalar()
        assert re.match(DOI_RE, doi)
        metadata_json = ckan_model.Session.query(ckan_model.PackageExtra.value) \
            .filter_by(package_id=obj.id, key='metadata_json') \
            .scalar()
        metadata_dict = json.loads(metadata_json)
        assert metadata_dict['identifier']['identifier'] == doi

    def test_create_invalid_auto_generate_doi_conflict(self):
        input_dict = self._make_input_dict()
        input_dict['doi'] = '10.1234/XYZ'
        input_dict['auto_assign_doi'] = True
        result, obj = self.test_action('metadata_record_create', should_error=True, **input_dict)
        assert_error(result, 'message', 'The metadata record already has a DOI')

    def test_create_valid_owner_org_byname(self):
        input_dict = self._make_input_dict()
        input_dict['owner_org'] = self.owner_org['name']
        result, obj = self.test_action('metadata_record_create', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_create_valid_map_attributes(self):
        """
        Test copying of metadata element values into package attributes via metadata JSON
        attribute mappings.
        """
        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier = metadata_dict['identifier']['identifier']
        url = metadata_dict['immutableResource']['resourceURL']
        title = metadata_dict['titles'][0]['title']

        self._define_attribute_map('/identifier/identifier', 'name')
        self._define_attribute_map('/immutableResource/resourceURL', 'url')
        self._define_attribute_map('/titles/0/title', 'title')

        input_dict = self._make_input_dict()
        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_create', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict, name=identifier, title=title, url=url)

    def test_create_valid_map_empty_attributes(self):
        """
        Test that when values do not exist in the metadata JSON for the defined mappings,
        the target attributes are cleared.
        """
        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        metadata_dict['titles'][0] = {}
        del metadata_dict['creators']
        metadata_json = json.dumps(metadata_dict)

        self._define_attribute_map('/titles/0/title', 'title')
        self._define_attribute_map('/creators/0/name', 'author')

        input_dict = self._make_input_dict()
        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_create', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict, title='', author='')

    def test_create_valid_map_empty_name(self):
        """
        Test that when record name is the target of an attribute mapping, and the source value
        is empty, the record name defaults to the record id.
        """
        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        del metadata_dict['identifier']
        metadata_json = json.dumps(metadata_dict)

        self._define_attribute_map('/identifier/identifier', 'name')

        input_dict = self._make_input_dict()
        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_create', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_create_valid_map_attributes_update_existing(self):
        """
        Test that we switch to an update when matching on key attributes, while non-key
        attributes play no part in matching.
        """
        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier = metadata_dict['identifier']['identifier']
        url = metadata_dict['immutableResource']['resourceURL']
        title = metadata_dict['titles'][0]['title']

        self._define_attribute_map('/identifier/identifier', 'name', is_key=True)
        self._define_attribute_map('/immutableResource/resourceURL', 'url', is_key=True)
        self._define_attribute_map('/titles/0/title', 'title', is_key=False)

        metadata_record = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record['name'] == identifier
        assert metadata_record['url'] == url
        assert metadata_record['title'] == title

        metadata_dict['titles'][0]['title'] = 'Updated Title'
        metadata_json = json.dumps(metadata_dict)

        input_dict = self._make_input_dict()
        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_create', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict, title='Updated Title', name=identifier, url=url)
        assert result['id'] == obj.id == metadata_record['id']

    def test_create_invalid_map_attributes_mismatched_keys(self):
        """
        Test that we fail an attempt to create (update) a record when incoming key attributes
        match different existing records.
        """
        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier1 = metadata_dict['identifier']['identifier']
        url1 = metadata_dict['immutableResource']['resourceURL']
        identifier2 = 'A.different.identifier'
        url2 = 'http://a.different.url'

        self._define_attribute_map('/identifier/identifier', 'name', is_key=True)
        self._define_attribute_map('/immutableResource/resourceURL', 'url', is_key=True)

        metadata_record1 = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record1['name'] == identifier1
        assert metadata_record1['url'] == url1

        metadata_dict['identifier']['identifier'] = identifier2
        metadata_dict['immutableResource']['resourceURL'] = url2
        metadata_json = json.dumps(metadata_dict)
        metadata_record2 = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record2['name'] == identifier2
        assert metadata_record2['url'] == url2

        metadata_dict['immutableResource']['resourceURL'] = url1
        metadata_json = json.dumps(metadata_dict)
        input_dict = self._make_input_dict()
        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_create', should_error=True, **input_dict)
        assert_error(result, 'message', 'Cannot unambiguously match an existing record for the given key attribute values')

    def test_create_invalid_map_attributes_partial_keys_1(self):
        """
        Test that we fail an attempt to create (update) a record when some of the incoming key
        attributes do not match the existing record.
        """
        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier = metadata_dict['identifier']['identifier']
        url = metadata_dict['immutableResource']['resourceURL']

        self._define_attribute_map('/identifier/identifier', 'name', is_key=True)
        self._define_attribute_map('/immutableResource/resourceURL', 'url', is_key=True)

        metadata_record = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record['name'] == identifier
        assert metadata_record['url'] == url

        metadata_dict['identifier']['identifier'] = 'foo'
        metadata_json = json.dumps(metadata_dict)

        input_dict = self._make_input_dict()
        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_create', should_error=True, **input_dict)
        assert_error(result, 'message', 'Cannot unambiguously match an existing record for the given key attribute values')

    def test_create_invalid_map_attributes_partial_keys_2(self):
        """
        Test that we fail an attempt to create (update) a record when some of the incoming key
        attributes required to match the existing record are not provided.
        """
        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier = metadata_dict['identifier']['identifier']
        url = metadata_dict['immutableResource']['resourceURL']

        self._define_attribute_map('/identifier/identifier', 'name', is_key=True)
        self._define_attribute_map('/immutableResource/resourceURL', 'url', is_key=True)

        metadata_record = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record['name'] == identifier
        assert metadata_record['url'] == url

        del metadata_dict['identifier']
        metadata_json = json.dumps(metadata_dict)

        input_dict = self._make_input_dict()
        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_create', should_error=True, **input_dict)
        assert_error(result, 'message', 'Cannot unambiguously match an existing record for the given key attribute values')

    def test_create_invalid_missing_params(self):
        result, obj = self.test_action('metadata_record_create', should_error=True)
        assert_error(result, 'owner_org', 'Missing parameter')
        assert_error(result, 'metadata_collection_id', 'Missing parameter')
        assert_error(result, 'metadata_standard_id', 'Missing parameter')
        assert_error(result, 'metadata_json', 'Missing parameter')
        assert_error(result, 'doi', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self.test_action('metadata_record_create', should_error=True,
                                       owner_org='',
                                       metadata_collection_id='',
                                       metadata_standard_id='',
                                       metadata_json='')
        assert_error(result, 'owner_org', 'Missing value')
        assert_error(result, 'metadata_collection_id', 'Missing value')
        assert_error(result, 'metadata_standard_id', 'Missing value')
        assert_error(result, 'metadata_json', 'Missing value')

    def test_create_invalid_not_json(self):
        result, obj = self.test_action('metadata_record_create', should_error=True,
                                       metadata_json='not json')
        assert_error(result, 'metadata_json', 'JSON decode error')

    def test_create_invalid_not_json_dict(self):
        result, obj = self.test_action('metadata_record_create', should_error=True,
                                       metadata_json='[1,2,3]')
        assert_error(result, 'metadata_json', 'Expecting a JSON dictionary')

    def test_create_invalid_not_a_doi(self):
        result, obj = self.test_action('metadata_record_create', should_error=True,
                                       doi='foo')
        assert_error(result, 'doi', 'Invalid DOI')

    def test_create_invalid_doi_already_taken(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self.test_action('metadata_record_create', should_error=True,
                                       doi=metadata_record['doi'])
        assert_error(result, 'doi', 'The DOI has already been taken')

    def test_create_invalid_bad_references(self):
        result, obj = self.test_action('metadata_record_create', should_error=True,
                                       owner_org='a',
                                       metadata_collection_id='b',
                                       metadata_standard_id='c')
        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, 'metadata_standard_id', 'Not found: Metadata Standard')

    def test_create_invalid_deleted_references(self):
        call_action('organization_delete', context={'user': self.normal_user['name']}, id=self.owner_org['id'])
        call_action('metadata_collection_delete', id=self.metadata_collection['id'])
        call_action('metadata_standard_delete', id=self.metadata_standard['id'])

        input_dict = self._make_input_dict()
        result, obj = self.test_action('metadata_record_create', should_error=True, **input_dict)

        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, 'metadata_standard_id', 'Not found: Metadata Standard')

    def test_create_invalid_owner_org_collection_mismatch(self):
        result, obj = self.test_action('metadata_record_create', should_error=True,
                                       owner_org=self.owner_org['id'],
                                       metadata_collection_id=self._generate_metadata_collection()['id'])
        assert_error(result, '__after', 'owner_org must be the same organization that owns the metadata collection')

    def test_create_match_existing_no_change(self):
        metadata_record = self._generate_metadata_record()
        input_dict = self._make_input_dict()
        input_dict['metadata_json'] = metadata_record['metadata_json']

        # should return the existing record
        result, obj = self.test_action('metadata_record_create', **input_dict)

        self._assert_metadata_record_ok(obj, metadata_record)
        assert obj.id == metadata_record['id']

    def test_update_valid(self):
        metadata_record = self._generate_metadata_record()
        new_metadata_collection = self._generate_metadata_collection(organization_id=self.owner_org['id'])
        new_metadata_standard = ckanext_factories.MetadataStandard()

        input_dict = {
            'id': metadata_record['id'],
            'title': 'Updated Test Metadata Record',
            'owner_org': self.owner_org['id'],
            'metadata_collection_id': new_metadata_collection['id'],
            'metadata_standard_id': new_metadata_standard['id'],
            'metadata_json': '{ "newtestkey": "newtestvalue" }',
            'doi': '10.12345/foo',
            # the following fields are set automatically, so any values provided as input should be ignored
            'type': 'ignore',
            'validated': 'ignore',
            'errors': 'ignore',
            'workflow_state_id': 'ignore',
            'private': 'ignore',
        }
        result, obj = self.test_action('metadata_record_update', **input_dict)

        self._assert_metadata_record_ok(obj, input_dict,
                                        metadata_collection_id=new_metadata_collection['id'],
                                        metadata_standard_id=new_metadata_standard['id'],
                                        doi=input_dict['doi'].upper())
        assert_group_has_member(self.metadata_collection['id'], obj.id, 'package', state='deleted')

    def test_update_valid_partial(self):
        metadata_record = self._generate_metadata_record()

        input_dict = self._make_input_dict()
        input_dict.update({
            'id': metadata_record['id'],
            'title': 'Updated Test Metadata Record',
            'metadata_json': '{ "newtestkey": "newtestvalue" }',
        })
        result, obj = self.test_action('metadata_record_update', **input_dict)

        self._assert_metadata_record_ok(obj, input_dict)

    def test_update_json_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_schema = self._validate_metadata_record(metadata_record)

        input_dict = self._make_input_dict_from_output_dict(metadata_record)
        input_dict['metadata_json'] = '{ "newtestkey": "newtestvalue" }'

        result, obj = self.test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        validated=False)
        assert_metadata_record_has_validation_schemas(metadata_record['id'], metadata_schema['name'])
        self.assert_invalidate_activity_logged(metadata_record['id'], 'metadata_record_update', obj)

    def test_update_standard_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_schema = self._validate_metadata_record(metadata_record)
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        new_metadata_standard = ckanext_factories.MetadataStandard()
        input_dict['metadata_standard_id'] = new_metadata_standard['id']

        result, obj = self.test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        metadata_standard_id=new_metadata_standard['id'],
                                        validated=False)
        assert_metadata_record_has_validation_schemas(metadata_record['id'])
        self.assert_invalidate_activity_logged(metadata_record['id'], 'metadata_record_update', obj)

    def test_update_owner_org_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_schema = self._validate_metadata_record(metadata_record)
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        new_organization = self._generate_organization()
        new_metadata_collection = self._generate_metadata_collection(organization_id=new_organization['id'])
        new_metadata_schema = ckanext_factories.MetadataSchema(metadata_standard_id=metadata_record['metadata_standard_id'],
                                                             organization_id=new_organization['id'])
        assert_package_has_extra(metadata_record['id'], 'validated', True)

        input_dict.update({
            'owner_org': new_organization['id'],
            'metadata_collection_id': new_metadata_collection['id'],
        })
        result, obj = self.test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        owner_org=new_organization['id'],
                                        metadata_collection_id=new_metadata_collection['id'],
                                        validated=False)
        assert_metadata_record_has_validation_schemas(metadata_record['id'],
                                                     metadata_schema['name'], new_metadata_schema['name'])
        self.assert_invalidate_activity_logged(metadata_record['id'], 'metadata_record_update', obj)

    # TODO: We should do this in metadata collection tests
    # def test_update_infrastructures_invalidate(self):
    #     infrastructure = self._generate_infrastructure()
    #     metadata_record = self._generate_metadata_record(infrastructures=[{'id': infrastructure['id']}])
    #     metadata_schema = self._validate_metadata_record(metadata_record)
    #     input_dict = self._make_input_dict_from_output_dict(metadata_record)
    #
    #     new_infrastructure = self._generate_infrastructure()
    #     new_metadata_schema = ckanext_factories.MetadataSchema(metadata_standard_id=metadata_record['metadata_standard_id'],
    #                                                          infrastructure_id=new_infrastructure['id'])
    #     assert_package_has_extra(metadata_record['id'], 'validated', True)
    #
    #     input_dict['infrastructures'] = [{'id': new_infrastructure['id']}]
    #     result, obj = self.test_action('metadata_record_update', **input_dict)
    #     self._assert_metadata_record_ok(obj, input_dict,
    #                                     validated=False)
    #     assert_metadata_record_has_validation_schemas(metadata_record['id'], new_metadata_schema['name'])
    #     self.assert_invalidate_activity_logged(metadata_record['id'], 'metadata_record_update', obj)

    def test_update_no_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_schema = self._validate_metadata_record(metadata_record)
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        result, obj = self.test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        validated=True)
        assert_metadata_record_has_validation_schemas(metadata_record['id'], metadata_schema['name'])

        new_organization = self._generate_organization()
        new_metadata_collection = self._generate_metadata_collection(organization_id=new_organization['id'])
        input_dict.update({
            'owner_org': new_organization['id'],
            'metadata_collection_id': new_metadata_collection['id'],
        })
        result, obj = self.test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict,
                                        owner_org=new_organization['id'],
                                        metadata_collection_id=new_metadata_collection['id'],
                                        validated=True)
        assert_metadata_record_has_validation_schemas(metadata_record['id'], metadata_schema['name'])

    def test_update_valid_map_attributes(self):
        """
        Test copying of metadata element values into package attributes via metadata JSON
        attribute mappings.
        """
        metadata_record = self._generate_metadata_record()
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier = metadata_dict['identifier']['identifier']
        url = metadata_dict['immutableResource']['resourceURL']
        title = metadata_dict['titles'][0]['title']

        self._define_attribute_map('/identifier/identifier', 'name')
        self._define_attribute_map('/immutableResource/resourceURL', 'url')
        self._define_attribute_map('/titles/0/title', 'title')

        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict, name=identifier, title=title, url=url)

    def test_update_valid_map_empty_attributes(self):
        """
        Test that when values do not exist in the metadata JSON for the defined mappings,
        the target attributes are cleared.
        """
        metadata_record = self._generate_metadata_record()
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        metadata_dict['titles'][0] = {}
        del metadata_dict['creators']
        metadata_json = json.dumps(metadata_dict)

        self._define_attribute_map('/titles/0/title', 'title')
        self._define_attribute_map('/creators/0/name', 'author')

        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict, title='', author='')

    def test_update_valid_map_empty_name(self):
        """
        Test that when record name is the target of an attribute mapping, and the source value
        is empty, the record name defaults to the record id.
        """
        metadata_record = self._generate_metadata_record()
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        del metadata_dict['identifier']
        metadata_json = json.dumps(metadata_dict)

        self._define_attribute_map('/identifier/identifier', 'name')

        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict)

    def test_update_valid_modify_key_attributes(self):
        """
        Test that we are able to update elements in the JSON that are defined in key
        attribute mappings.
        """
        self._define_attribute_map('/identifier/identifier', 'name', is_key=True)
        self._define_attribute_map('/immutableResource/resourceURL', 'url', is_key=True)

        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier1 = metadata_dict['identifier']['identifier']
        url1 = metadata_dict['immutableResource']['resourceURL']
        identifier2 = 'A.different.identifier'
        url2 = 'http://a.different.url'

        metadata_record = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record['name'] == identifier1
        assert metadata_record['url'] == url1

        metadata_dict['identifier']['identifier'] = identifier2
        metadata_dict['immutableResource']['resourceURL'] = url2
        metadata_json = json.dumps(metadata_dict)

        input_dict = self._make_input_dict_from_output_dict(metadata_record)
        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_update', **input_dict)
        self._assert_metadata_record_ok(obj, input_dict, name=identifier2, url=url2)

    def test_update_invalid_map_attributes_mismatched_keys(self):
        """
        Test that we fail an attempt to update a record when incoming key attributes
        match different existing records.
        """
        metadata_record = self._generate_metadata_record()
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier1 = metadata_dict['identifier']['identifier']
        url1 = metadata_dict['immutableResource']['resourceURL']
        identifier2 = 'A.different.identifier'
        url2 = 'http://a.different.url'

        self._define_attribute_map('/identifier/identifier', 'name', is_key=True)
        self._define_attribute_map('/immutableResource/resourceURL', 'url', is_key=True)

        metadata_record1 = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record1['name'] == identifier1
        assert metadata_record1['url'] == url1

        metadata_dict['identifier']['identifier'] = identifier2
        metadata_dict['immutableResource']['resourceURL'] = url2
        metadata_json = json.dumps(metadata_dict)
        metadata_record2 = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record2['name'] == identifier2
        assert metadata_record2['url'] == url2

        metadata_dict['immutableResource']['resourceURL'] = url1
        metadata_json = json.dumps(metadata_dict)
        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_update', should_error=True, **input_dict)
        assert_error(result, 'message', 'Cannot unambiguously match an existing record for the given key attribute values')

    def test_update_invalid_map_attributes_partial_keys_1(self):
        """
        Test that we fail an attempt to update a record when some of the incoming key
        attributes do not match the existing record.
        """
        metadata_record = self._generate_metadata_record()
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier = metadata_dict['identifier']['identifier']
        url = metadata_dict['immutableResource']['resourceURL']

        self._define_attribute_map('/identifier/identifier', 'name', is_key=True)
        self._define_attribute_map('/immutableResource/resourceURL', 'url', is_key=True)

        metadata_record1 = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record1['name'] == identifier
        assert metadata_record1['url'] == url

        metadata_dict['identifier']['identifier'] = 'foo'
        metadata_json = json.dumps(metadata_dict)

        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_update', should_error=True, **input_dict)
        assert_error(result, 'message', 'Cannot unambiguously match an existing record for the given key attribute values')

    def test_update_invalid_map_attributes_partial_keys_2(self):
        """
        Test that we fail an attempt to create (update) a record when some of the incoming key
        attributes required to match the existing record are not provided.
        """
        metadata_record = self._generate_metadata_record()
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier = metadata_dict['identifier']['identifier']
        url = metadata_dict['immutableResource']['resourceURL']

        self._define_attribute_map('/identifier/identifier', 'name', is_key=True)
        self._define_attribute_map('/immutableResource/resourceURL', 'url', is_key=True)

        metadata_record1 = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record1['name'] == identifier
        assert metadata_record1['url'] == url

        del metadata_dict['identifier']
        metadata_json = json.dumps(metadata_dict)

        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_update', should_error=True, **input_dict)
        assert_error(result, 'message', 'Cannot unambiguously match an existing record for the given key attribute values')

    def test_update_invalid_modify_key_attributes_match_another_record(self):
        """
        Test that we fail an attempt to update key elements in the JSON if those keys are
        already in use by another record.
        """
        self._define_attribute_map('/identifier/identifier', 'name', is_key=True)
        self._define_attribute_map('/immutableResource/resourceURL', 'url', is_key=True)

        metadata_json = load_example('saeon_odp_4.2_record.json')
        metadata_dict = json.loads(metadata_json)
        identifier1 = metadata_dict['identifier']['identifier']
        url1 = metadata_dict['immutableResource']['resourceURL']
        identifier2 = 'A.different.identifier'
        url2 = 'http://a.different.url'

        metadata_record_1 = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record_1['name'] == identifier1
        assert metadata_record_1['url'] == url1

        metadata_dict['identifier']['identifier'] = identifier2
        metadata_dict['immutableResource']['resourceURL'] = url2
        metadata_json = json.dumps(metadata_dict)

        metadata_record_2 = self._generate_metadata_record(metadata_json=metadata_json)
        assert metadata_record_2['name'] == identifier2
        assert metadata_record_2['url'] == url2

        input_dict = self._make_input_dict_from_output_dict(metadata_record_1)
        input_dict['metadata_json'] = metadata_json
        result, obj = self.test_action('metadata_record_update', should_error=True, **input_dict)
        assert_error(result, 'message', 'Cannot update record; another record exists with the given key attribute values')

    def test_update_invalid_missing_params(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self.test_action('metadata_record_update', should_error=True,
                                       id=metadata_record['id'])
        assert_error(result, 'owner_org', 'Missing parameter')
        assert_error(result, 'metadata_collection_id', 'Missing parameter')
        assert_error(result, 'metadata_standard_id', 'Missing parameter')
        assert_error(result, 'metadata_json', 'Missing parameter')
        assert_error(result, 'doi', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self.test_action('metadata_record_update', should_error=True,
                                       id=metadata_record['id'],
                                       owner_org='',
                                       metadata_collection_id='',
                                       metadata_standard_id='',
                                       metadata_json='')
        assert_error(result, 'owner_org', 'Missing value')
        assert_error(result, 'metadata_collection_id', 'Missing value')
        assert_error(result, 'metadata_standard_id', 'Missing value')
        assert_error(result, 'metadata_json', 'Missing value')

    def test_update_invalid_not_json(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self.test_action('metadata_record_update', should_error=True,
                                       id=metadata_record['id'],
                                       metadata_json='not json')
        assert_error(result, 'metadata_json', 'JSON decode error')

    def test_update_invalid_not_json_dict(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self.test_action('metadata_record_update', should_error=True,
                                       id=metadata_record['id'],
                                       metadata_json='[1,2,3]')
        assert_error(result, 'metadata_json', 'Expecting a JSON dictionary')

    def test_update_invalid_not_a_doi(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self.test_action('metadata_record_update', should_error=True,
                                       id=metadata_record['id'],
                                       doi='foo')
        assert_error(result, 'doi', 'Invalid DOI')

    def test_update_invalid_doi_already_taken(self):
        metadata_record1 = self._generate_metadata_record()
        metadata_record2 = self._generate_metadata_record()
        result, obj = self.test_action('metadata_record_update', should_error=True,
                                       id=metadata_record1['id'],
                                       doi=metadata_record2['doi'])
        assert_error(result, 'doi', 'The DOI has already been taken')

    def test_update_invalid_bad_references(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self.test_action('metadata_record_update', should_error=True,
                                       id=metadata_record['id'],
                                       owner_org='a',
                                       metadata_collection_id='b',
                                       metadata_standard_id='c')
        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, 'metadata_standard_id', 'Not found: Metadata Standard')

    def test_update_invalid_deleted_references(self):
        metadata_record = self._generate_metadata_record()
        organization = self._generate_organization()
        metadata_collection = self._generate_metadata_collection(organization_id=organization['id'])
        metadata_standard = ckanext_factories.MetadataStandard()
        call_action('organization_delete', context={'user': self.normal_user['name']}, id=organization['id'])
        call_action('metadata_collection_delete', id=metadata_collection['id'])
        call_action('metadata_standard_delete', id=metadata_standard['id'])

        result, obj = self.test_action('metadata_record_update', should_error=True,
                                       id=metadata_record['id'],
                                       owner_org=organization['id'],
                                       metadata_collection_id=metadata_collection['id'],
                                       metadata_standard_id=metadata_standard['id'])

        assert_error(result, 'owner_org', 'Not found: Organization')
        assert_error(result, 'metadata_collection_id', 'Not found: Metadata Collection')
        assert_error(result, 'metadata_standard_id', 'Not found: Metadata Standard')

    def test_update_invalid_owner_org_collection_mismatch(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self.test_action('metadata_record_update', should_error=True,
                                       id=metadata_record['id'],
                                       owner_org=self.owner_org['id'],
                                       metadata_collection_id=self._generate_metadata_collection()['id'])
        assert_error(result, '__after', 'owner_org must be the same organization that owns the metadata collection')

    def test_delete_valid(self):
        metadata_record = self._generate_metadata_record()
        self.test_action('metadata_record_delete',
                         id=metadata_record['id'])

    def test_invalidate(self):
        metadata_record = self._generate_metadata_record()
        metadata_schema = self._validate_metadata_record(metadata_record)
        input_dict = self._make_input_dict_from_output_dict(metadata_record)

        result, obj = self.test_action('metadata_record_invalidate',
                                       id=metadata_record['id'])
        self._assert_metadata_record_ok(obj, input_dict,
                                        validated=False)
        assert_metadata_record_has_validation_schemas(metadata_record['id'], metadata_schema['name'])
        self.assert_invalidate_activity_logged(metadata_record['id'], None, None)

    def test_validate_datacite(self):
        metadata_record = self._generate_metadata_record(
            metadata_json=load_example('saeon_odp_4.2_record.json'))
        metadata_schema = ckanext_factories.MetadataSchema(
            metadata_standard_id=metadata_record['metadata_standard_id'],
            schema_json=load_example('saeon_odp_4.2_schema.json'))
        ckan_factories.Vocabulary(name='language-tags', tags=[{'name': 'en-us'}])

        assert_metadata_record_has_validation_schemas(metadata_record['id'], metadata_schema['name'])
        self.test_action('metadata_record_validate', id=metadata_record['id'])
        assert_package_has_extra(metadata_record['id'], 'validated', True)
        assert_package_has_extra(metadata_record['id'], 'errors', '{}')
        self.assert_validate_activity_logged(metadata_record['id'], metadata_schema)

    def test_workflow_annotations_valid(self):
        metadata_record = self._generate_metadata_record()

        annotation1_value = '{"foo": true, "bar": "http://example.net"}'
        annotation1_dict, _ = self.test_action('metadata_record_workflow_annotation_create',
                                               id=metadata_record['id'],
                                               key='annotation1_key',
                                               value=annotation1_value)

        _, jsonpatch1 = self.test_action('jsonpatch_show', id=annotation1_dict['jsonpatch_id'])
        jsonpatch1_dict = {
            'model_name': 'metadata_record',
            'object_id': metadata_record['id'],
            'scope': 'workflow',
            'operation': {'op': 'add', 'path': '/annotation1_key', 'value': json.loads(annotation1_value)},
            'ordinal': 0,
            'data': None,
        }
        assert_object_matches_dict(jsonpatch1, jsonpatch1_dict)
        assert type(jsonpatch1.timestamp) is datetime

        annotation2_value = '[1, 2, 3]'
        annotation2_dict, _ = self.test_action('metadata_record_workflow_annotation_create',
                                               id=metadata_record['id'],
                                               key='annotation2_key',
                                               value=annotation2_value)

        _, jsonpatch2 = self.test_action('jsonpatch_show', id=annotation2_dict['jsonpatch_id'])
        jsonpatch2_dict = {
            'model_name': 'metadata_record',
            'object_id': metadata_record['id'],
            'scope': 'workflow',
            'operation': {'op': 'add', 'path': '/annotation2_key', 'value': json.loads(annotation2_value)},
            'ordinal': 0,
            'data': None,
        }
        assert_object_matches_dict(jsonpatch2, jsonpatch2_dict)
        assert type(jsonpatch2.timestamp) is datetime

        annotation_list = call_action('metadata_record_workflow_annotation_list', id=metadata_record['id'])
        assert [annotation['jsonpatch_id'] for annotation in annotation_list] == [jsonpatch1.id, jsonpatch2.id]

        metadata_record_dict, obj = self.test_action('metadata_record_show', id=metadata_record['id'])
        metadata_record_augmented_dict, _ = self.test_action('metadata_record_workflow_augmented_show',
                                                             id=metadata_record['id'])
        self._assert_metadata_record_ok(obj, metadata_record)
        assert metadata_record_augmented_dict.pop('annotation1_key') == json.loads(annotation1_value)
        assert metadata_record_augmented_dict.pop('annotation2_key') == json.loads(annotation2_value)
        assert metadata_record_dict == metadata_record_augmented_dict

    def test_workflow_annotation_invalid_missing_params(self):
        metadata_record = self._generate_metadata_record()
        result, _ = self.test_action('metadata_record_workflow_annotation_create', should_error=True,
                                     id=metadata_record['id'])
        assert_error(result, 'key', 'Missing parameter')
        assert_error(result, 'value', 'Missing parameter')

    def test_workflow_annotation_invalid_missing_values(self):
        metadata_record = self._generate_metadata_record()
        result, _ = self.test_action('metadata_record_workflow_annotation_create', should_error=True,
                                     id=metadata_record['id'],
                                     key='',
                                     value='')
        assert_error(result, 'key', 'Missing value')
        assert_error(result, 'value', 'Missing value')

    def test_workflow_annotation_invalid_existing_metadata_record_key(self):
        metadata_record = self._generate_metadata_record()
        result, _ = self.test_action('metadata_record_workflow_annotation_create', should_error=True,
                                     id=metadata_record['id'],
                                     key='owner_org')
        assert_error(result, 'key', 'The specified key cannot be used')

    def test_workflow_annotation_invalid_key_name(self):
        metadata_record = self._generate_metadata_record()
        result, _ = self.test_action('metadata_record_workflow_annotation_create', should_error=True,
                                     id=metadata_record['id'],
                                     key='metadata_json/description')
        assert_error(result, 'key', 'Must be purely lowercase alphanumeric')

    def test_workflow_transition_captured(self):
        metadata_record = self._generate_metadata_record(
            metadata_json=load_example('saeon_odp_4.2_record.json'))
        workflow_state_captured = ckanext_factories.WorkflowState(
            workflow_rules_json=load_example('workflow_state_captured_rules.json'))
        ckanext_factories.WorkflowTransition(
            from_state_id='',
            to_state_id=workflow_state_captured['id'])

        jsonpatch_ids = []

        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_captured['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_captured['id'],
                                             data_agreement='is a required property',
                                             terms_and_conditions='is a required property',
                                             capture_info='is a required property')
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')

        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='data_agreement',
                                      value='{"accepted": false, "href": "http:example.net/"}',
                                      )['jsonpatch_id']]
        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='terms_and_conditions',
                                      value='"foo"',
                                      )['jsonpatch_id']]
        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='capture_info',
                                      value='"bar"',
                                      )['jsonpatch_id']]

        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_captured['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_captured['id'],
                                             *jsonpatch_ids, **{
                                                 'data_agreement/accepted': 'True was expected',
                                                 'data_agreement/href': 'is not a .*url',
                                                 'terms_and_conditions': 'is not of type .*object',
                                                 'capture_info': 'is not of type .*object',
                                             })
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')

        call_action('metadata_record_workflow_annotation_update', id=metadata_record['id'],
                    key='data_agreement',
                    value='{"accepted": true}')
        call_action('metadata_record_workflow_annotation_update', id=metadata_record['id'],
                    key='terms_and_conditions',
                    value='{"accepted": true}')
        call_action('metadata_record_workflow_annotation_update', id=metadata_record['id'],
                    key='capture_info',
                    value='{"capture_method": "xyz"}')

        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_captured['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_captured['id'],
                                             *jsonpatch_ids, **{
                                                 'data_agreement/href': 'is a required property',
                                                 'capture_info/capture_method': 'is not one of ',
                                             })
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')

        call_action('metadata_record_workflow_annotation_update', id=metadata_record['id'],
                    key='data_agreement',
                    value='{"accepted": true, "href": "http://example.net/"}')
        call_action('metadata_record_workflow_annotation_update', id=metadata_record['id'],
                    key='capture_info',
                    value='{"capture_method": "harvester"}')

        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_captured['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_captured['id'],
                                             *jsonpatch_ids)
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state_captured['id'])

        # already in captured state - no change
        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_captured['id'])
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state_captured['id'])

    def test_workflow_transition_accepted(self):
        metadata_record = self._generate_metadata_record(
            metadata_json=load_example('saeon_odp_4.2_record.json'))
        workflow_state_accepted = ckanext_factories.WorkflowState(
            workflow_rules_json=load_example('workflow_state_accepted_rules.json'))
        ckanext_factories.WorkflowTransition(
            from_state_id='',
            to_state_id=workflow_state_accepted['id'])

        jsonpatch_ids = []
        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='data_agreement',
                                      value='{"accepted": true, "href": "http://example.net/"}',
                                      )['jsonpatch_id']]
        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='terms_and_conditions',
                                      value='{"accepted": true}',
                                      )['jsonpatch_id']]
        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='capture_info',
                                      value='{"capture_method": "wizard"}',
                                      )['jsonpatch_id']]
        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='quality_control_1',
                                      value='"foo"',
                                      )['jsonpatch_id']]

        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_accepted['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_accepted['id'],
                                             *jsonpatch_ids,
                                             validated='True was expected',
                                             quality_control_1='is not of type .*object')
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')

        self._validate_metadata_record(metadata_record)
        call_action('metadata_record_workflow_annotation_update', id=metadata_record['id'],
                    key='quality_control_1',
                    value='{"user": "someone", "date": "Friday the 13th"}')

        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_accepted['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_accepted['id'],
                                             *jsonpatch_ids, **{
                                                 'quality_control_1/user': 'is not a .*email',
                                                 'quality_control_1/date': 'is not a .*date',
                                             })
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')

        call_action('metadata_record_workflow_annotation_update', id=metadata_record['id'],
                    key='quality_control_1',
                    value=json.dumps({"user": self.normal_user['email'], "date": "2018-08-14"}))

        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_accepted['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_accepted['id'],
                                             *jsonpatch_ids, **{
                                                 'quality_control_1/user': 'User .* does not have the curator role',
                                             })
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')

        self._grant_privilege(self.normal_user['id'], self.owner_org['name'], 'curator')
        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_accepted['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_accepted['id'],
                                             *jsonpatch_ids)
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state_accepted['id'])

    def test_workflow_transition_published(self):
        metadata_json = json.loads(load_example('saeon_odp_4.2_record.json'))
        metadata_json['identifier']['identifier'] = 'foo'
        metadata_json['immutableResource']['resourceURL'] = 'http://inaccessible.url'
        metadata_json['linkedResources'][0]['resourceURL'] = 'http://inaccessible.url'
        metadata_record = self._generate_metadata_record(
            metadata_json=json.dumps(metadata_json))

        ckanext_factories.MetadataSchema(
            metadata_standard_id=metadata_record['metadata_standard_id'],
            schema_json=load_example('saeon_odp_4.2_schema.json'))
        call_action('metadata_record_validate', id=metadata_record['id'], context={'user': self.normal_user['name']})

        workflow_state_published = ckanext_factories.WorkflowState(
            workflow_rules_json=load_example('workflow_state_published_rules.json'))
        ckanext_factories.WorkflowTransition(
            from_state_id='',
            to_state_id=workflow_state_published['id'])

        self._grant_privilege(self.normal_user['id'], self.owner_org['name'], 'curator')
        jsonpatch_ids = []
        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='data_agreement',
                                      value='{"accepted": true, "href": "http://example.net/"}',
                                      )['jsonpatch_id']]
        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='terms_and_conditions',
                                      value='{"accepted": true}',
                                      )['jsonpatch_id']]
        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='capture_info',
                                      value='{"capture_method": "curator"}',
                                      )['jsonpatch_id']]
        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='quality_control_1',
                                      value=json.dumps({"user": self.normal_user['email'], "date": "2018-08-14"}),
                                      )['jsonpatch_id']]

        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_published['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_published['id'],
                                             *jsonpatch_ids, **{
                                                 'errors/__maxProperties': 'Object must be empty',
                                                 'quality_control_2': 'is a required property',
                                                 'metadata_json/immutableResource/resourceURL': 'URL test failed',
                                                 'metadata_json/linkedResources/0/resourceURL': 'URL test failed',
                                             })
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')

        metadata_record['metadata_json'] = load_example('saeon_odp_4.2_record.json')
        call_action('metadata_record_update', context={'user': self.normal_user['name']}, **metadata_record)
        call_action('metadata_record_validate', id=metadata_record['id'], context={'user': self.normal_user['name']})

        jsonpatch_ids += [call_action('metadata_record_workflow_annotation_create', id=metadata_record['id'],
                                      key='quality_control_2',
                                      value=json.dumps({"user": self.normal_user['email'], "date": "2018-08-15"}),
                                      )['jsonpatch_id']]

        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_published['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_published['id'],
                                             *jsonpatch_ids, **{
                                                 '__uniqueProperties': 'Object has non-unique properties',
                                             })
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')

        qc2_user = ckan_factories.User()
        call_action('metadata_record_workflow_annotation_update', id=metadata_record['id'],
                    key='quality_control_2',
                    value=json.dumps({"user": qc2_user['email'], "date": "2018-08-14"}))

        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_published['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_published['id'],
                                             *jsonpatch_ids, **{
                                                 'quality_control_2/user': 'User .* does not have the curator role',
                                             })
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')

        self._grant_privilege(qc2_user['id'], self.owner_org['name'], 'curator')
        self.test_action('metadata_record_workflow_state_transition', id=metadata_record['id'],
                         workflow_state_id=workflow_state_published['id'])
        self.assert_workflow_activity_logged('transition', metadata_record['id'], workflow_state_published['id'],
                                             *jsonpatch_ids)
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state_published['id'])

    def test_workflow_state_revert(self):
        metadata_record = self._generate_metadata_record()
        workflow_state1 = ckanext_factories.WorkflowState(metadata_records_private=False)
        workflow_state2 = ckanext_factories.WorkflowState(revert_state_id=workflow_state1['id'], metadata_records_private=True)

        call_action('metadata_record_workflow_state_override', context={'user': self.normal_user['name']},
                    id=metadata_record['id'], workflow_state_id=workflow_state2['id'])
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state2['id'])
        assert_package_has_attribute(metadata_record['id'], 'private', True)

        self.test_action('metadata_record_workflow_state_revert', id=metadata_record['id'])
        self.assert_workflow_activity_logged('revert', metadata_record['id'], workflow_state1['id'])
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state1['id'])
        assert_package_has_attribute(metadata_record['id'], 'private', False)

        self.test_action('metadata_record_workflow_state_revert', id=metadata_record['id'])
        self.assert_workflow_activity_logged('revert', metadata_record['id'], '')
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')
        assert_package_has_attribute(metadata_record['id'], 'private', True)

        # already in null state - no change
        self.test_action('metadata_record_workflow_state_revert', id=metadata_record['id'])
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', '')
        assert_package_has_attribute(metadata_record['id'], 'private', True)

    def test_package_create_invalid(self):
        result, obj = self.test_action('package_create', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       type='metadata_record')
        assert_error(result, None, "This action may not be used for metadata records.")

    def test_package_update_invalid(self):
        metadata_record = ckanext_factories.MetadataRecord()
        result, obj = self.test_action('package_update', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       id=metadata_record['id'])
        assert_error(result, None, "This action may not be used for metadata records.")

    def test_package_delete_invalid(self):
        metadata_record = ckanext_factories.MetadataRecord()
        result, obj = self.test_action('package_delete', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       id=metadata_record['id'])
        assert_error(result, None, "This action may not be used for metadata records.")

    def test_assign_doi(self):
        metadata_collection = self._generate_metadata_collection(organization_id=self.owner_org['id'],
                                                                 doi_collection='')
        metadata_record = self._generate_metadata_record(metadata_collection_id=metadata_collection['id'],
                                                         doi='')
        self.test_action('metadata_record_assign_doi', id=metadata_record['id'])
        doi = ckan_model.Session.query(ckan_model.PackageExtra.value) \
            .filter_by(package_id=metadata_record['id'], key='doi') \
            .scalar()
        assert re.match(DOI_RE, doi)

    def test_assign_doi_with_collection(self):
        metadata_collection = self._generate_metadata_collection(organization_id=self.owner_org['id'],
                                                                 doi_collection='foo')
        metadata_record = self._generate_metadata_record(metadata_collection_id=metadata_collection['id'],
                                                         doi='')
        self.test_action('metadata_record_assign_doi', id=metadata_record['id'])
        doi = ckan_model.Session.query(ckan_model.PackageExtra.value) \
            .filter_by(package_id=metadata_record['id'], key='doi') \
            .scalar()
        assert re.match(DOI_RE, doi)
        assert '/FOO.' in doi

    def test_assign_doi_update_json_1(self):
        """
        Test that the DOI is put into the metadata JSON if there's an appropriate attribute mapping.
        """
        metadata_standard = ckanext_factories.MetadataStandard(metadata_template_json='{"a": {"b": {"c": "doi"}}}')
        self._define_attribute_map('/a/b/c', 'doi', metadata_standard_id=metadata_standard['id'])

        metadata_record = self._generate_metadata_record(doi='', metadata_standard_id=metadata_standard['id'])
        self.test_action('metadata_record_assign_doi', id=metadata_record['id'])

        doi = ckan_model.Session.query(ckan_model.PackageExtra.value) \
            .filter_by(package_id=metadata_record['id'], key='doi') \
            .scalar()
        assert re.match(DOI_RE, doi)

        metadata_json = ckan_model.Session.query(ckan_model.PackageExtra.value) \
            .filter_by(package_id=metadata_record['id'], key='metadata_json') \
            .scalar()
        metadata_dict = json.loads(metadata_json)
        assert metadata_dict['a']['b']['c'] == doi

    def test_assign_doi_update_json_2(self):
        """
        Test that the DOI is put into the metadata JSON if there's an appropriate attribute mapping,
        and that doing so does not bork existing metadata content.
        """
        metadata_standard = ckanext_factories.MetadataStandard(metadata_template_json='{"a": {"b": {"c": "doi"}}}')
        self._define_attribute_map('/a/b/c', 'doi', metadata_standard_id=metadata_standard['id'])

        metadata_record = self._generate_metadata_record(
            doi='',
            metadata_standard_id=metadata_standard['id'],
            metadata_json='{"a": {"x": "y"}}',
        )
        self.test_action('metadata_record_assign_doi', id=metadata_record['id'])

        doi = ckan_model.Session.query(ckan_model.PackageExtra.value) \
            .filter_by(package_id=metadata_record['id'], key='doi') \
            .scalar()
        assert re.match(DOI_RE, doi)

        metadata_json = ckan_model.Session.query(ckan_model.PackageExtra.value) \
            .filter_by(package_id=metadata_record['id'], key='metadata_json') \
            .scalar()
        metadata_dict = json.loads(metadata_json)
        assert metadata_dict['a']['b']['c'] == doi
        assert metadata_dict['a']['x'] == 'y'

    def test_assign_doi_invalid_already_exists(self):
        metadata_record = self._generate_metadata_record()
        result, obj = self.test_action('metadata_record_assign_doi', should_error=True,
                                       id=metadata_record['id'])
        assert_error(result, 'message', 'The metadata record already has a DOI')
