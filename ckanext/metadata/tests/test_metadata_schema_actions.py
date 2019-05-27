# encoding: utf-8

from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import call_action

from ckanext.metadata import model as ckanext_model
from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    generate_name,
    assert_object_matches_dict,
    assert_error,
    assert_package_has_extra,
    assert_metadata_record_has_validation_schemas,
    assert_metadata_schema_has_dependent_records,
    factories as ckanext_factories,
    load_example,
)


class TestMetadataSchemaActions(ActionTestBase):

    def _generate_and_validate_metadata_record(self, metadata_standard_id=None,
                                               add_infrastructure_to_record=False,
                                               add_organization_to_schema=False,
                                               add_infrastructure_to_schema=False):
        """
        Generate a metadata record and a metadata schema, and validate the record using the schema.
        :param metadata_standard_id: specify the metadata standard to use
        :param add_infrastructure_to_record: assign an infrastructure to the record
        :param add_organization_to_schema: associate the record's organization with the schema
        :param add_infrastructure_to_schema: associate the record's infrastructure with the schema
        :return: tuple of new record and schema dictionaries
        """
        metadata_record = ckanext_factories.MetadataRecord(
            metadata_standard_id=metadata_standard_id,
            infrastructures=[{'id': ckanext_factories.Infrastructure()['id']}] if add_infrastructure_to_record else [])

        metadata_schema = ckanext_factories.MetadataSchema(
            metadata_standard_id=metadata_record['metadata_standard_id'],
            organization_id=metadata_record['owner_org'] if add_organization_to_schema else '',
            infrastructure_id=metadata_record['infrastructures'][0]['id'] if add_infrastructure_to_schema else '')

        assert_metadata_record_has_validation_schemas(metadata_record['id'], metadata_schema['name'])
        self._validate_metadata_record(metadata_record)
        self.assert_validate_activity_logged(metadata_record['id'], metadata_schema)
        return metadata_record, metadata_schema

    def _generate_and_validate_metadata_record_using_schema(self, metadata_schema):
        """
        Generate a metadata record with the same standard and organization/infrastructure of the given schema,
        and validate it using this schema.
        :return: metadata record dict
        """
        metadata_record = ckanext_factories.MetadataRecord(
            metadata_standard_id=metadata_schema['metadata_standard_id'],
            owner_org=metadata_schema['organization_id'],
            infrastructures=[{'id': metadata_schema['infrastructure_id']}] if metadata_schema['infrastructure_id'] else [])

        assert_metadata_record_has_validation_schemas(metadata_record['id'], metadata_schema['name'])
        self._validate_metadata_record(metadata_record)
        self.assert_validate_activity_logged(metadata_record['id'], metadata_schema)
        return metadata_record

    def _validate_metadata_record(self, metadata_record):
        """
        :param metadata_record: metadata record dict
        """
        call_action('metadata_record_validate', id=metadata_record['id'], context={'user': self.normal_user['name']})
        assert_package_has_extra(metadata_record['id'], 'validated', True)

    def test_create_valid(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'description': 'This is a test metadata schema',
            'metadata_standard_id': metadata_standard['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'schema_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self.test_action('metadata_schema_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == generate_name(metadata_standard['name'], '', '')

    def test_create_valid_datacite(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'metadata_standard_id': metadata_standard['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'schema_json': load_example('datacite_4.2_saeon_schema.json'),
        }
        result, obj = self.test_action('metadata_schema_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_setname(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'name': 'test-metadata-schema',
            'metadata_standard_id': metadata_standard['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'schema_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self.test_action('metadata_schema_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_organization_byname(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        organization = ckan_factories.Organization()
        input_dict = {
            'metadata_standard_id': metadata_standard['name'],
            'organization_id': organization['name'],
            'infrastructure_id': '',
            'schema_json': '{}',
        }
        result, obj = self.test_action('metadata_schema_create', **input_dict)
        assert obj.metadata_standard_id == metadata_standard['id']
        assert obj.organization_id == organization['id']
        assert obj.infrastructure_id is None
        assert obj.name == generate_name(metadata_standard['name'], organization['name'], '')

    def test_create_valid_with_infrastructure_byname(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'metadata_standard_id': metadata_standard['name'],
            'organization_id': '',
            'infrastructure_id': infrastructure['name'],
            'schema_json': '{}',
        }
        result, obj = self.test_action('metadata_schema_create', **input_dict)
        assert obj.metadata_standard_id == metadata_standard['id']
        assert obj.organization_id is None
        assert obj.infrastructure_id == infrastructure['id']
        assert obj.name == generate_name(metadata_standard['name'], '', infrastructure['name'])

    def test_create_valid_same_standard_different_organization(self):
        organization1 = ckan_factories.Organization()
        organization2 = ckan_factories.Organization()
        metadata_schema = ckanext_factories.MetadataSchema(organization_id=organization1['id'])
        input_dict = {
            'metadata_standard_id': metadata_schema['metadata_standard_id'],
            'organization_id': organization2['id'],
            'infrastructure_id': '',
            'schema_json': '{}',
        }
        result, obj = self.test_action('metadata_schema_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_standard_different_infrastructure(self):
        infrastructure1 = ckanext_factories.Infrastructure()
        infrastructure2 = ckanext_factories.Infrastructure()
        metadata_schema = ckanext_factories.MetadataSchema(infrastructure_id=infrastructure1['id'])
        input_dict = {
            'metadata_standard_id': metadata_schema['metadata_standard_id'],
            'organization_id': '',
            'infrastructure_id': infrastructure2['id'],
            'schema_json': '{}',
        }
        result, obj = self.test_action('metadata_schema_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_organization_different_standard(self):
        organization = ckan_factories.Organization()
        metadata_schema = ckanext_factories.MetadataSchema(organization_id=organization['id'])
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'metadata_standard_id': metadata_standard['id'],
            'organization_id': metadata_schema['organization_id'],
            'infrastructure_id': '',
            'schema_json': '{}',
        }
        result, obj = self.test_action('metadata_schema_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_infrastructure_different_standard(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_schema = ckanext_factories.MetadataSchema(infrastructure_id=infrastructure['id'])
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'metadata_standard_id': metadata_standard['id'],
            'organization_id': '',
            'infrastructure_id': metadata_schema['infrastructure_id'],
            'schema_json': '{}',
        }
        result, obj = self.test_action('metadata_schema_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalidate_records_matching_standard(self):
        """
        Create a schema that will be used for validating an existing validated metadata record by virtue
        of matching on the record's metadata standard. This should invalidate the record.
        """
        # add org to schema to avoid unique key violation below
        metadata_record, _ = self._generate_and_validate_metadata_record(add_organization_to_schema=True)
        result, obj = self.test_action('metadata_schema_create',
                                       metadata_standard_id=metadata_record['metadata_standard_id'],
                                       organization_id='',
                                       infrastructure_id='',
                                       schema_json='{}')
        assert_package_has_extra(metadata_record['id'], 'validated', False)
        self.assert_invalidate_activity_logged(metadata_record['id'], 'metadata_schema_create', obj)

    def test_create_invalidate_records_matching_standard_organization(self):
        """
        Create a schema that will be used for validating an existing validated metadata record by virtue
        of matching on standard and organization. This should invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record()
        result, obj = self.test_action('metadata_schema_create',
                                       metadata_standard_id=metadata_record['metadata_standard_id'],
                                       organization_id=metadata_record['owner_org'],
                                       infrastructure_id='',
                                       schema_json='{}')
        assert_package_has_extra(metadata_record['id'], 'validated', False)
        self.assert_invalidate_activity_logged(metadata_record['id'], 'metadata_schema_create', obj)

    def test_create_invalidate_records_matching_standard_infrastructure(self):
        """
        Create a schema that will be used for validating an existing validated metadata record by virtue
        of matching on standard and infrastructure. This should invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True)
        result, obj = self.test_action('metadata_schema_create',
                                       metadata_standard_id=metadata_record['metadata_standard_id'],
                                       organization_id='',
                                       infrastructure_id=metadata_record['infrastructures'][0]['id'],
                                       schema_json='{}')
        assert_package_has_extra(metadata_record['id'], 'validated', False)
        self.assert_invalidate_activity_logged(metadata_record['id'], 'metadata_schema_create', obj)

    def test_create_no_invalidate_records_different_standard(self):
        """
        Create a schema with a different standard to that of an existing validated metadata record.
        This should not invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record()
        call_action('metadata_schema_create',
                    metadata_standard_id=ckanext_factories.MetadataStandard()['id'],
                    organization_id='',
                    infrastructure_id='',
                    schema_json='{}')
        assert_package_has_extra(metadata_record['id'], 'validated', True)

    def test_create_no_invalidate_records_different_organization(self):
        """
        Create a schema with the same standard but a different organization to that of an existing
        validated metadata record. This should not invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record()
        call_action('metadata_schema_create',
                    metadata_standard_id=metadata_record['metadata_standard_id'],
                    organization_id=ckan_factories.Organization()['id'],
                    infrastructure_id='',
                    schema_json='{}')
        assert_package_has_extra(metadata_record['id'], 'validated', True)

    def test_create_no_invalidate_records_different_infrastructure_1(self):
        """
        Create a schema with the same standard but a different infrastructure to that of an existing
        validated metadata record. This should not invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True)
        call_action('metadata_schema_create',
                    metadata_standard_id=metadata_record['metadata_standard_id'],
                    organization_id='',
                    infrastructure_id=ckanext_factories.Infrastructure()['id'],
                    schema_json='{}')
        assert_package_has_extra(metadata_record['id'], 'validated', True)

    def test_create_no_invalidate_records_different_infrastructure_2(self):
        """
        Create a schema with the same standard but a different infrastructure to that of an existing
        validated metadata record. This should not invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record()
        call_action('metadata_schema_create',
                    metadata_standard_id=metadata_record['metadata_standard_id'],
                    organization_id='',
                    infrastructure_id=ckanext_factories.Infrastructure()['id'],
                    schema_json='{}')
        assert_package_has_extra(metadata_record['id'], 'validated', True)

    def test_create_invalid_duplicate_name(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       name=metadata_schema['name'])
        assert_error(result, 'name', 'Duplicate name: Metadata Schema')

    def test_create_invalid_duplicate_standard(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       metadata_standard_id=metadata_schema['metadata_standard_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_duplicate_standard_organization(self):
        organization = ckan_factories.Organization()
        metadata_schema = ckanext_factories.MetadataSchema(organization_id=organization['id'])
        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       metadata_standard_id=metadata_schema['metadata_standard_id'],
                                       organization_id=metadata_schema['organization_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_duplicate_standard_infrastructure(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_schema = ckanext_factories.MetadataSchema(infrastructure_id=infrastructure['id'])
        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       metadata_standard_id=metadata_schema['metadata_standard_id'],
                                       infrastructure_id=metadata_schema['infrastructure_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_with_organization_and_infrastructure(self):
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       organization_id=organization['id'],
                                       infrastructure_id=infrastructure['id'])
        assert_error(result, '__after',
                     'A metadata schema may be associated with either an organization or an infrastructure but not both.')

    def test_create_invalid_not_json(self):
        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       schema_json='not json')
        assert_error(result, 'schema_json', 'JSON decode error')

    def test_create_invalid_not_json_dict(self):
        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       schema_json='[1,2,3]')
        assert_error(result, 'schema_json', 'Invalid JSON schema')

    def test_create_invalid_not_json_schema(self):
        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       schema_json='{"type": "foo"}')
        assert_error(result, 'schema_json', 'Invalid JSON schema')

    def test_create_invalid_missing_params(self):
        result, obj = self.test_action('metadata_schema_create', should_error=True)
        assert_error(result, 'metadata_standard_id', 'Missing parameter')
        assert_error(result, 'organization_id', 'Missing parameter')
        assert_error(result, 'infrastructure_id', 'Missing parameter')
        assert_error(result, 'schema_json', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       metadata_standard_id='',
                                       schema_json='')
        assert_error(result, 'metadata_standard_id', 'Missing value')
        assert_error(result, 'schema_json', 'Missing value')

    def test_create_invalid_bad_references(self):
        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       metadata_standard_id='a',
                                       organization_id='b',
                                       infrastructure_id='c')
        assert_error(result, 'metadata_standard_id', 'Not found: Metadata Standard')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_create_invalid_deleted_references(self):
        metadata_standard = ckanext_factories.MetadataStandard()
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        call_action('metadata_standard_delete', id=metadata_standard['id'])
        call_action('organization_delete', id=organization['id'])
        call_action('infrastructure_delete', id=infrastructure['id'])

        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       metadata_standard_id=metadata_standard['id'],
                                       organization_id=organization['id'],
                                       infrastructure_id=infrastructure['id'])
        assert_error(result, 'metadata_standard_id', 'Not found: Metadata Standard')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_update_valid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        metadata_standard = ckanext_factories.MetadataStandard()
        input_dict = {
            'id': metadata_schema['id'],
            'description': 'Updated test metadata schema description',
            'metadata_standard_id': metadata_standard['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'schema_json': '{ "testkey": "newtestvalue" }',
        }
        result, obj = self.test_action('metadata_schema_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == generate_name(metadata_standard['name'], '', '')

    def test_update_valid_partial(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'name': 'updated-test-metadata-schema',
            'metadata_standard_id': metadata_schema['metadata_standard_id'],
            'organization_id': '',
            'infrastructure_id': '',
            'schema_json': '{ "testkey": "newtestvalue" }',
        }
        result, obj = self.test_action('metadata_schema_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.description == metadata_schema['description']

    def test_update_valid_datacite(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema['id'],
            'metadata_standard_id': metadata_schema['metadata_standard_id'],
            'organization_id': '',
            'infrastructure_id': '',
            'schema_json': load_example('datacite_4.2_saeon_schema.json'),
        }
        result, obj = self.test_action('metadata_schema_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_set_organization(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        organization = ckan_factories.Organization()
        input_dict = {
            'id': metadata_schema['id'],
            'metadata_standard_id': metadata_schema['metadata_standard_id'],
            'organization_id': organization['id'],
            'infrastructure_id': '',
            'schema_json': '{}',
        }
        result, obj = self.test_action('metadata_schema_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        metadata_standard = ckanext_model.MetadataStandard.get(metadata_schema['metadata_standard_id'])
        assert obj.name == generate_name(metadata_standard.name, organization['name'], '')

    def test_update_valid_set_infrastructure(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'id': metadata_schema['id'],
            'metadata_standard_id': metadata_schema['metadata_standard_id'],
            'organization_id': '',
            'infrastructure_id': infrastructure['id'],
            'schema_json': '{}',
        }
        result, obj = self.test_action('metadata_schema_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        metadata_standard = ckanext_model.MetadataStandard.get(metadata_schema['metadata_standard_id'])
        assert obj.name == generate_name(metadata_standard.name, '', infrastructure['name'])

    def test_update_json_invalidate_records_1(self):
        """
        Update the JSON of a schema that was used to validate existing metadata records that are associated with
        different organizations and infrastructures. This should invalidate all those records.
        """
        metadata_record_1, metadata_schema = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True)
        metadata_record_2 = self._generate_and_validate_metadata_record_using_schema(metadata_schema)
        assert_metadata_schema_has_dependent_records(metadata_schema['id'], metadata_record_1['id'], metadata_record_2['id'])

        result, obj = self.test_action('metadata_schema_update',
                                       id=metadata_schema['id'],
                                       metadata_standard_id=metadata_schema['metadata_standard_id'],
                                       organization_id='',
                                       infrastructure_id='',
                                       schema_json='{ "newtestkey": "newtestvalue" }')

        assert_package_has_extra(metadata_record_1['id'], 'validated', False)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        assert_metadata_schema_has_dependent_records(metadata_schema['id'], metadata_record_1['id'], metadata_record_2['id'])
        self.assert_invalidate_activity_logged(metadata_record_1['id'], 'metadata_schema_update', obj)
        self.assert_invalidate_activity_logged(metadata_record_2['id'], 'metadata_schema_update', obj)

    def test_update_json_invalidate_records_2(self):
        """
        Update the JSON of a schema that was used to validate existing metadata records that are associated with
        the same infrastructure and different organizations. This should invalidate all those records.
        """
        metadata_record_1, metadata_schema = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True, add_infrastructure_to_schema=True)
        metadata_record_2 = self._generate_and_validate_metadata_record_using_schema(metadata_schema)
        assert_metadata_schema_has_dependent_records(metadata_schema['id'], metadata_record_1['id'], metadata_record_2['id'])

        result, obj = self.test_action('metadata_schema_update',
                                       id=metadata_schema['id'],
                                       metadata_standard_id=metadata_schema['metadata_standard_id'],
                                       organization_id='',
                                       infrastructure_id=metadata_schema['infrastructure_id'],
                                       schema_json='{ "newtestkey": "newtestvalue" }')

        assert_package_has_extra(metadata_record_1['id'], 'validated', False)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        assert_metadata_schema_has_dependent_records(metadata_schema['id'], metadata_record_1['id'], metadata_record_2['id'])
        self.assert_invalidate_activity_logged(metadata_record_1['id'], 'metadata_schema_update', obj)
        self.assert_invalidate_activity_logged(metadata_record_2['id'], 'metadata_schema_update', obj)

    def test_update_json_invalidate_records_3(self):
        """
        Update the JSON of a schema that was used to validate existing metadata records that are associated with
        the same organization and different infrastructures. This should invalidate all those records.
        """
        metadata_record_1, metadata_schema = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True, add_organization_to_schema=True)
        metadata_record_2 = self._generate_and_validate_metadata_record_using_schema(metadata_schema)
        assert_metadata_schema_has_dependent_records(metadata_schema['id'], metadata_record_1['id'], metadata_record_2['id'])

        result, obj = self.test_action('metadata_schema_update',
                                       id=metadata_schema['id'],
                                       metadata_standard_id=metadata_schema['metadata_standard_id'],
                                       organization_id=metadata_schema['organization_id'],
                                       infrastructure_id='',
                                       schema_json='{ "newtestkey": "newtestvalue" }')

        assert_package_has_extra(metadata_record_1['id'], 'validated', False)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        assert_metadata_schema_has_dependent_records(metadata_schema['id'], metadata_record_1['id'], metadata_record_2['id'])
        self.assert_invalidate_activity_logged(metadata_record_1['id'], 'metadata_schema_update', obj)
        self.assert_invalidate_activity_logged(metadata_record_2['id'], 'metadata_schema_update', obj)

    def test_update_infrastructure_invalidate_records_1(self):
        """
        Assign an infrastructure to a schema that was used to validate existing metadata records. This should invalidate
        those records that are no longer dependent on the schema due to not being associated with that infrastructure.
        """
        metadata_record_1, metadata_schema = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True)
        metadata_record_2 = self._generate_and_validate_metadata_record_using_schema(metadata_schema)
        assert_metadata_schema_has_dependent_records(metadata_schema['id'], metadata_record_1['id'], metadata_record_2['id'])

        result, obj = self.test_action('metadata_schema_update',
                                       id=metadata_schema['id'],
                                       metadata_standard_id=metadata_schema['metadata_standard_id'],
                                       organization_id='',
                                       infrastructure_id=metadata_record_1['infrastructures'][0]['id'],
                                       schema_json=metadata_schema['schema_json'])

        assert_package_has_extra(metadata_record_1['id'], 'validated', True)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        assert_metadata_schema_has_dependent_records(metadata_schema['id'], metadata_record_1['id'])
        self.assert_invalidate_activity_logged(metadata_record_2['id'], 'metadata_schema_update', obj)

    def test_update_infrastructure_invalidate_records_2(self):
        """
        Unassign an infrastructure from a schema. This should invalidate existing validated metadata records that are
        newly dependent on the schema.
        """
        metadata_record_1, metadata_schema_1 = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True, add_infrastructure_to_schema=True)
        metadata_record_2, metadata_schema_2 = self._generate_and_validate_metadata_record(metadata_standard_id=metadata_record_1['metadata_standard_id'], add_organization_to_schema=True)
        assert_metadata_schema_has_dependent_records(metadata_schema_1['id'], metadata_record_1['id'])

        result, obj = self.test_action('metadata_schema_update',
                                       id=metadata_schema_1['id'],
                                       metadata_standard_id=metadata_schema_1['metadata_standard_id'],
                                       organization_id='',
                                       infrastructure_id='',
                                       schema_json=metadata_schema_1['schema_json'])

        assert_package_has_extra(metadata_record_1['id'], 'validated', True)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        assert_metadata_schema_has_dependent_records(metadata_schema_1['id'], metadata_record_1['id'], metadata_record_2['id'])
        self.assert_invalidate_activity_logged(metadata_record_2['id'], 'metadata_schema_update', obj)

    def test_update_organization_invalidate_records_1(self):
        """
        Assign an organization to a schema that was used to validate existing metadata records. This should invalidate
        those records that are no longer dependent on the schema due to not being associated with that organization.
        """
        metadata_record_1, metadata_schema = self._generate_and_validate_metadata_record()
        metadata_record_2 = self._generate_and_validate_metadata_record_using_schema(metadata_schema)
        assert_metadata_schema_has_dependent_records(metadata_schema['id'], metadata_record_1['id'], metadata_record_2['id'])

        result, obj = self.test_action('metadata_schema_update',
                                       id=metadata_schema['id'],
                                       metadata_standard_id=metadata_schema['metadata_standard_id'],
                                       organization_id=metadata_record_1['owner_org'],
                                       infrastructure_id='',
                                       schema_json=metadata_schema['schema_json'])

        assert_package_has_extra(metadata_record_1['id'], 'validated', True)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        assert_metadata_schema_has_dependent_records(metadata_schema['id'], metadata_record_1['id'])
        self.assert_invalidate_activity_logged(metadata_record_2['id'], 'metadata_schema_update', obj)

    def test_update_organization_invalidate_records_2(self):
        """
        Unassign an organization from a schema. This should invalidate existing validated metadata records that are
        newly dependent on the schema.
        """
        metadata_record_1, metadata_schema_1 = self._generate_and_validate_metadata_record(add_organization_to_schema=True)
        metadata_record_2, metadata_schema_2 = self._generate_and_validate_metadata_record(metadata_standard_id=metadata_record_1['metadata_standard_id'], add_organization_to_schema=True)
        assert_metadata_schema_has_dependent_records(metadata_schema_1['id'], metadata_record_1['id'])

        result, obj = self.test_action('metadata_schema_update',
                                       id=metadata_schema_1['id'],
                                       metadata_standard_id=metadata_schema_1['metadata_standard_id'],
                                       organization_id='',
                                       infrastructure_id='',
                                       schema_json=metadata_schema_1['schema_json'])

        assert_package_has_extra(metadata_record_1['id'], 'validated', True)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        assert_metadata_schema_has_dependent_records(metadata_schema_1['id'], metadata_record_1['id'], metadata_record_2['id'])
        self.assert_invalidate_activity_logged(metadata_record_2['id'], 'metadata_schema_update', obj)

    def test_update_invalid_duplicate_name(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_schema1['id'],
            'name': metadata_schema2['name'],
        }
        result, obj = self.test_action('metadata_schema_update', should_error=True, **input_dict)
        assert_error(result, 'name', 'Duplicate name: Metadata Schema')

    def test_update_invalid_missing_params(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema['id'])
        assert_error(result, 'metadata_standard_id', 'Missing parameter')
        assert_error(result, 'organization_id', 'Missing parameter')
        assert_error(result, 'infrastructure_id', 'Missing parameter')
        assert_error(result, 'schema_json', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema['id'],
                                       metadata_standard_id='',
                                       schema_json='')
        assert_error(result, 'metadata_standard_id', 'Missing value')
        assert_error(result, 'schema_json', 'Missing value')

    def test_update_invalid_duplicate_standard(self):
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema()
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema1['id'],
                                       metadata_standard_id=metadata_schema2['metadata_standard_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_duplicate_standard_organization(self):
        organization = ckan_factories.Organization()
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema(organization_id=organization['id'])
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema1['id'],
                                       metadata_standard_id=metadata_schema2['metadata_standard_id'],
                                       organization_id=metadata_schema2['organization_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_duplicate_standard_infrastructure(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_schema1 = ckanext_factories.MetadataSchema()
        metadata_schema2 = ckanext_factories.MetadataSchema(infrastructure_id=infrastructure['id'])
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema1['id'],
                                       metadata_standard_id=metadata_schema2['metadata_standard_id'],
                                       infrastructure_id=metadata_schema2['infrastructure_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_with_organization_set_infrastructure(self):
        organization = ckan_factories.Organization()
        metadata_schema = ckanext_factories.MetadataSchema(organization_id=organization['id'])
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema['id'],
                                       infrastructure_id=infrastructure['id'])
        assert_error(result, '__after',
                     'A metadata schema may be associated with either an organization or an infrastructure but not both.')

    def test_update_invalid_with_infrastructure_set_organization(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_schema = ckanext_factories.MetadataSchema(infrastructure_id=infrastructure['id'])
        organization = ckan_factories.Organization()
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema['id'],
                                       organization_id=organization['id'])
        assert_error(result, '__after',
                     'A metadata schema may be associated with either an organization or an infrastructure but not both.')

    def test_update_invalid_not_json(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema['id'],
                                       schema_json='not json')
        assert_error(result, 'schema_json', 'JSON decode error')

    def test_update_invalid_not_json_dict(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema['id'],
                                       schema_json='[1,2,3]')
        assert_error(result, 'schema_json', 'Invalid JSON schema')

    def test_update_invalid_not_json_schema(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema['id'],
                                       schema_json='{"type": "foo"}')
        assert_error(result, 'schema_json', 'Invalid JSON schema')

    def test_update_invalid_bad_references(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        result, obj = self.test_action('metadata_schema_update', should_error=True,
                                       id=metadata_schema['id'],
                                       metadata_standard_id='a',
                                       organization_id='b',
                                       infrastructure_id='c')
        assert_error(result, 'metadata_standard_id', 'Not found: Metadata Standard')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_update_invalid_deleted_references(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        metadata_standard = ckanext_factories.MetadataStandard()
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        call_action('metadata_standard_delete', id=metadata_standard['id'])
        call_action('organization_delete', id=organization['id'])
        call_action('infrastructure_delete', id=infrastructure['id'])

        result, obj = self.test_action('metadata_schema_create', should_error=True,
                                       id=metadata_schema['id'],
                                       metadata_standard_id=metadata_standard['id'],
                                       organization_id=organization['id'],
                                       infrastructure_id=infrastructure['id'])
        assert_error(result, 'metadata_standard_id', 'Not found: Metadata Standard')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_delete_valid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        self.test_action('metadata_schema_delete',
                         id=metadata_schema['id'])

    def test_delete_invalidate_records(self):
        metadata_record, metadata_schema = self._generate_and_validate_metadata_record()
        result, obj = self.test_action('metadata_schema_delete',
                                       id=metadata_schema['id'])
        assert_package_has_extra(metadata_record['id'], 'validated', False)
        self.assert_invalidate_activity_logged(metadata_record['id'], 'metadata_schema_delete', obj)

        metadata_record, metadata_schema = self._generate_and_validate_metadata_record(add_organization_to_schema=True)
        result, obj = self.test_action('metadata_schema_delete',
                                       id=metadata_schema['id'])
        assert_package_has_extra(metadata_record['id'], 'validated', False)
        self.assert_invalidate_activity_logged(metadata_record['id'], 'metadata_schema_delete', obj)

        metadata_record, metadata_schema = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True,
                                                                                      add_infrastructure_to_schema=True)
        result, obj = self.test_action('metadata_schema_delete',
                                       id=metadata_schema['id'])
        assert_package_has_extra(metadata_record['id'], 'validated', False)
        self.assert_invalidate_activity_logged(metadata_record['id'], 'metadata_schema_delete', obj)
