# encoding: utf-8

from ckan.plugins import toolkit as tk
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
    factories as ckanext_factories,
)


class TestMetadataModelActions(ActionTestBase):

    def _generate_and_validate_metadata_record(self, metadata_schema_id=None,
                                               add_infrastructure_to_record=False,
                                               add_organization_to_model=False,
                                               add_infrastructure_to_model=False):
        """
        Generate a metadata record and a metadata model, and validate the record using the model.
        :param metadata_schema_id: specify the metadata schema to use
        :param add_infrastructure_to_record: assign an infrastructure to the record
        :param add_organization_to_model: associate the record's organization with the model
        :param add_infrastructure_to_model: associate the record's infrastructure with the model
        :return: tuple of new record and model dictionaries
        """
        metadata_record = ckanext_factories.MetadataRecord(
            metadata_schema_id=metadata_schema_id,
            infrastructures=[{'id': ckanext_factories.Infrastructure()['id']}] if add_infrastructure_to_record else [])

        metadata_model = ckanext_factories.MetadataModel(
            metadata_schema_id=metadata_record['metadata_schema_id'],
            organization_id=metadata_record['owner_org'] if add_organization_to_model else '',
            infrastructure_id=metadata_record['infrastructures'][0]['id'] if add_infrastructure_to_model else '')

        self._validate_metadata_record(metadata_record)
        return metadata_record, metadata_model

    def _generate_and_validate_metadata_record_using_model(self, metadata_model):
        """
        Generate a metadata record with the same schema and organization/infrastructure of the given model,
        and validate it using this model.
        :return: metadata record dict
        """
        metadata_record = ckanext_factories.MetadataRecord(
            metadata_schema_id=metadata_model['metadata_schema_id'],
            owner_org=metadata_model['organization_id'],
            infrastructures=[{'id': metadata_model['infrastructure_id']}] if metadata_model['infrastructure_id'] else [])

        self._validate_metadata_record(metadata_record)
        return metadata_record

    def _validate_metadata_record(self, metadata_record):
        """
        :param metadata_record: metadata record dict
        """
        call_action('metadata_record_validate', id=metadata_record['id'], context={'user': self.normal_user['name']})
        assert_package_has_extra(metadata_record['id'], 'validated', True)

    def test_create_valid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'title': 'Test Metadata Model',
            'description': 'This is a test metadata model',
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'model_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._test_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == generate_name(metadata_schema['name'], '', '')

    def test_create_valid_setname(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'name': 'test-metadata-model',
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'model_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._test_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_organization_byname(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        organization = ckan_factories.Organization()
        input_dict = {
            'metadata_schema_id': metadata_schema['name'],
            'organization_id': organization['name'],
            'infrastructure_id': '',
            'model_json': '',
        }
        result, obj = self._test_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert obj.metadata_schema_id == metadata_schema['id']
        assert obj.organization_id == organization['id']
        assert obj.infrastructure_id is None
        assert obj.name == generate_name(metadata_schema['name'], organization['name'], '')

    def test_create_valid_with_infrastructure_byname(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'metadata_schema_id': metadata_schema['name'],
            'organization_id': '',
            'infrastructure_id': infrastructure['name'],
            'model_json': '',
        }
        result, obj = self._test_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert obj.metadata_schema_id == metadata_schema['id']
        assert obj.organization_id is None
        assert obj.infrastructure_id == infrastructure['id']
        assert obj.name == generate_name(metadata_schema['name'], '', infrastructure['name'])

    def test_create_valid_sysadmin_setid(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': make_uuid(),
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'model_json': '',
        }
        result, obj = self._test_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_schema_different_organization(self):
        organization1 = ckan_factories.Organization()
        organization2 = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization1['id'])
        input_dict = {
            'metadata_schema_id': metadata_model['metadata_schema_id'],
            'organization_id': organization2['id'],
            'infrastructure_id': '',
            'model_json': '',
        }
        result, obj = self._test_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_schema_different_infrastructure(self):
        infrastructure1 = ckanext_factories.Infrastructure()
        infrastructure2 = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure1['id'])
        input_dict = {
            'metadata_schema_id': metadata_model['metadata_schema_id'],
            'organization_id': '',
            'infrastructure_id': infrastructure2['id'],
            'model_json': '',
        }
        result, obj = self._test_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_organization_different_schema(self):
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': metadata_model['organization_id'],
            'infrastructure_id': '',
            'model_json': '',
        }
        result, obj = self._test_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_same_infrastructure_different_schema(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': '',
            'infrastructure_id': metadata_model['infrastructure_id'],
            'model_json': '',
        }
        result, obj = self._test_action('create', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalidate_records_matching_schema(self):
        """
        Create a model that will be used for validating an existing validated metadata record by virtue
        of matching on the record's schema. This should invalidate the record.
        """
        # add org to model to avoid unique key violation below
        metadata_record, _ = self._generate_and_validate_metadata_record(add_organization_to_model=True)
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validated', False)

    def test_create_invalidate_records_matching_schema_organization(self):
        """
        Create a model that will be used for validating an existing validated metadata record by virtue
        of matching on schema and organization. This should invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record()
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id=metadata_record['owner_org'],
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validated', False)

    def test_create_invalidate_records_matching_schema_infrastructure(self):
        """
        Create a model that will be used for validating an existing validated metadata record by virtue
        of matching on schema and infrastructure. This should invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True)
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id=metadata_record['infrastructures'][0]['id'],
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validated', False)

    def test_create_no_invalidate_records_different_schema(self):
        """
        Create a model with a different schema to that of an existing validated metadata record.
        This should not invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record()
        call_action('metadata_model_create',
                    metadata_schema_id=ckanext_factories.MetadataSchema()['id'],
                    organization_id='',
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validated', True)

    def test_create_no_invalidate_records_different_organization(self):
        """
        Create a model with the same schema but a different organization to that of an existing
        validated metadata record. This should not invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record()
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id=ckan_factories.Organization()['id'],
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validated', True)

    def test_create_no_invalidate_records_different_infrastructure_1(self):
        """
        Create a model with the same schema but a different infrastructure to that of an existing
        validated metadata record. This should not invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True)
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id=ckanext_factories.Infrastructure()['id'],
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validated', True)

    def test_create_no_invalidate_records_different_infrastructure_2(self):
        """
        Create a model with the same schema but a different infrastructure to that of an existing
        validated metadata record. This should not invalidate the record.
        """
        metadata_record, _ = self._generate_and_validate_metadata_record()
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id=ckanext_factories.Infrastructure()['id'],
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validated', True)

    def test_create_invalid_duplicate_name(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        name=metadata_model['name'])
        assert_error(result, 'name', 'Duplicate name: Metadata Model')

    def test_create_invalid_duplicate_schema(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_model['metadata_schema_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_duplicate_schema_organization(self):
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_model['metadata_schema_id'],
                                        organization_id=metadata_model['organization_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_duplicate_schema_infrastructure(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_model['metadata_schema_id'],
                                        infrastructure_id=metadata_model['infrastructure_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_with_organization_and_infrastructure(self):
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        organization_id=organization['id'],
                                        infrastructure_id=infrastructure['id'])
        assert_error(result, '__after',
                     'A metadata model may be associated with either an organization or an infrastructure but not both.')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=metadata_model['id'])
        assert_error(result, 'id', 'Already exists: Metadata Model')

    def test_create_invalid_not_json(self):
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        model_json='not json')
        assert_error(result, 'model_json', 'JSON decode error')

    def test_create_invalid_not_json_dict(self):
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        model_json='[1,2,3]')
        assert_error(result, 'model_json', 'Expecting a JSON dictionary')

    def test_create_invalid_not_json_schema(self):
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        model_json='{"type": "foo"}')
        assert_error(result, 'model_json', 'Invalid JSON schema')

    def test_create_invalid_missing_params(self):
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError)
        assert_error(result, 'metadata_schema_id', 'Missing parameter')
        assert_error(result, 'organization_id', 'Missing parameter')
        assert_error(result, 'infrastructure_id', 'Missing parameter')
        assert_error(result, 'model_json', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id='')
        assert_error(result, 'metadata_schema_id', 'Missing value')

    def test_create_invalid_bad_references(self):
        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id='a',
                                        organization_id='b',
                                        infrastructure_id='c')
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_create_invalid_deleted_references(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        call_action('metadata_schema_delete', id=metadata_schema['id'])
        call_action('organization_delete', id=organization['id'])
        call_action('infrastructure_delete', id=infrastructure['id'])

        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        metadata_schema_id=metadata_schema['id'],
                                        organization_id=organization['id'],
                                        infrastructure_id=infrastructure['id'])
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_update_valid(self):
        metadata_model = ckanext_factories.MetadataModel()
        metadata_schema = ckanext_factories.MetadataSchema()
        input_dict = {
            'id': metadata_model['id'],
            'title': 'Updated Test Metadata Model',
            'description': 'Updated test metadata model description',
            'metadata_schema_id': metadata_schema['id'],
            'organization_id': '',
            'infrastructure_id': '',
            'model_json': '{ "testkey": "newtestvalue" }',
        }
        result, obj = self._test_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == generate_name(metadata_schema['name'], '', '')

    def test_update_valid_partial(self):
        metadata_model = ckanext_factories.MetadataModel()
        input_dict = {
            'id': metadata_model['id'],
            'name': 'updated-test-metadata-model',
            'metadata_schema_id': metadata_model['metadata_schema_id'],
            'organization_id': '',
            'infrastructure_id': '',
            'model_json': '{ "testkey": "newtestvalue" }',
        }
        result, obj = self._test_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.title == metadata_model['title']
        assert obj.description == metadata_model['description']

    def test_update_valid_set_organization(self):
        metadata_model = ckanext_factories.MetadataModel()
        organization = ckan_factories.Organization()
        input_dict = {
            'id': metadata_model['id'],
            'metadata_schema_id': metadata_model['metadata_schema_id'],
            'organization_id': organization['id'],
            'infrastructure_id': '',
            'model_json': '',
        }
        result, obj = self._test_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        metadata_schema = ckanext_model.MetadataSchema.get(metadata_model['metadata_schema_id'])
        assert obj.name == generate_name(metadata_schema.name, organization['name'], '')

    def test_update_valid_set_infrastructure(self):
        metadata_model = ckanext_factories.MetadataModel()
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'id': metadata_model['id'],
            'metadata_schema_id': metadata_model['metadata_schema_id'],
            'organization_id': '',
            'infrastructure_id': infrastructure['id'],
            'model_json': '',
        }
        result, obj = self._test_action('update', 'metadata_model',
                                        model_class=ckanext_model.MetadataModel, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        metadata_schema = ckanext_model.MetadataSchema.get(metadata_model['metadata_schema_id'])
        assert obj.name == generate_name(metadata_schema.name, '', infrastructure['name'])

    def test_update_json_invalidate_records_1(self):
        """
        Update the JSON of a model that was used to validate existing metadata records that are associated with
        different organizations and infrastructures. This should invalidate all those records.
        """
        metadata_record_1, metadata_model = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True)
        metadata_record_2 = self._generate_and_validate_metadata_record_using_model(metadata_model)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id']}

        call_action('metadata_model_update',
                    id=metadata_model['id'],
                    metadata_schema_id=metadata_model['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id='',
                    model_json='{ "newtestkey": "newtestvalue" }')

        assert_package_has_extra(metadata_record_1['id'], 'validated', False)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id']}

    def test_update_json_invalidate_records_2(self):
        """
        Update the JSON of a model that was used to validate existing metadata records that are associated with
        the same infrastructure and different organizations. This should invalidate all those records.
        """
        metadata_record_1, metadata_model = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True, add_infrastructure_to_model=True)
        metadata_record_2 = self._generate_and_validate_metadata_record_using_model(metadata_model)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id']}

        call_action('metadata_model_update',
                    id=metadata_model['id'],
                    metadata_schema_id=metadata_model['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id=metadata_model['infrastructure_id'],
                    model_json='{ "newtestkey": "newtestvalue" }')

        assert_package_has_extra(metadata_record_1['id'], 'validated', False)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id']}

    def test_update_json_invalidate_records_3(self):
        """
        Update the JSON of a model that was used to validate existing metadata records that are associated with
        the same organization and different infrastructures. This should invalidate all those records.
        """
        metadata_record_1, metadata_model = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True, add_organization_to_model=True)
        metadata_record_2 = self._generate_and_validate_metadata_record_using_model(metadata_model)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id']}

        call_action('metadata_model_update',
                    id=metadata_model['id'],
                    metadata_schema_id=metadata_model['metadata_schema_id'],
                    organization_id=metadata_model['organization_id'],
                    infrastructure_id='',
                    model_json='{ "newtestkey": "newtestvalue" }')

        assert_package_has_extra(metadata_record_1['id'], 'validated', False)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id']}

    def test_update_infrastructure_invalidate_records_1(self):
        """
        Assign an infrastructure to a model that was used to validate existing metadata records. This should invalidate
        those records that are no longer dependent on the model due to not being associated with that infrastructure.
        """
        metadata_record_1, metadata_model = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True)
        metadata_record_2 = self._generate_and_validate_metadata_record_using_model(metadata_model)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id']}

        call_action('metadata_model_update',
                    id=metadata_model['id'],
                    metadata_schema_id=metadata_model['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id=metadata_record_1['infrastructures'][0]['id'],
                    model_json='{}')

        assert_package_has_extra(metadata_record_1['id'], 'validated', True)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id']}

    def test_update_infrastructure_invalidate_records_2(self):
        """
        Unassign an infrastructure from a model. This should invalidate existing validated metadata records that are
        newly dependent on the model.
        """
        metadata_record_1, metadata_model_1 = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True, add_infrastructure_to_model=True)
        metadata_record_2, metadata_model_2 = self._generate_and_validate_metadata_record(metadata_schema_id=metadata_record_1['metadata_schema_id'], add_organization_to_model=True)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model_1['id'])
        assert set(dependent_records) == {metadata_record_1['id']}

        call_action('metadata_model_update',
                    id=metadata_model_1['id'],
                    metadata_schema_id=metadata_model_1['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id='',
                    model_json='{}')

        assert_package_has_extra(metadata_record_1['id'], 'validated', True)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model_1['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id']}

    def test_update_organization_invalidate_records_1(self):
        """
        Assign an organization to a model that was used to validate existing metadata records. This should invalidate
        those records that are no longer dependent on the model due to not being associated with that organization.
        """
        metadata_record_1, metadata_model = self._generate_and_validate_metadata_record()
        metadata_record_2 = self._generate_and_validate_metadata_record_using_model(metadata_model)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id']}

        call_action('metadata_model_update',
                    id=metadata_model['id'],
                    metadata_schema_id=metadata_model['metadata_schema_id'],
                    organization_id=metadata_record_1['owner_org'],
                    infrastructure_id='',
                    model_json='{}')

        assert_package_has_extra(metadata_record_1['id'], 'validated', True)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id']}

    def test_update_organization_invalidate_records_2(self):
        """
        Unassign an organization from a model. This should invalidate existing validated metadata records that are
        newly dependent on the model.
        """
        metadata_record_1, metadata_model_1 = self._generate_and_validate_metadata_record(add_organization_to_model=True)
        metadata_record_2, metadata_model_2 = self._generate_and_validate_metadata_record(metadata_schema_id=metadata_record_1['metadata_schema_id'], add_organization_to_model=True)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model_1['id'])
        assert set(dependent_records) == {metadata_record_1['id']}

        call_action('metadata_model_update',
                    id=metadata_model_1['id'],
                    metadata_schema_id=metadata_model_1['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id='',
                    model_json='{}')

        assert_package_has_extra(metadata_record_1['id'], 'validated', True)
        assert_package_has_extra(metadata_record_2['id'], 'validated', False)
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model_1['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id']}

    def test_update_invalid_duplicate_name(self):
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel()
        input_dict = {
            'id': metadata_model1['id'],
            'name': metadata_model2['name'],
        }
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'name', 'Duplicate name: Metadata Model')

    def test_update_invalid_missing_params(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'])
        assert_error(result, 'metadata_schema_id', 'Missing parameter')
        assert_error(result, 'organization_id', 'Missing parameter')
        assert_error(result, 'infrastructure_id', 'Missing parameter')
        assert_error(result, 'model_json', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        metadata_schema_id='')
        assert_error(result, 'metadata_schema_id', 'Missing value')

    def test_update_invalid_duplicate_schema(self):
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel()
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model1['id'],
                                        metadata_schema_id=metadata_model2['metadata_schema_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_duplicate_schema_organization(self):
        organization = ckan_factories.Organization()
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel(organization_id=organization['id'])
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model1['id'],
                                        metadata_schema_id=metadata_model2['metadata_schema_id'],
                                        organization_id=metadata_model2['organization_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_duplicate_schema_infrastructure(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model1 = ckanext_factories.MetadataModel()
        metadata_model2 = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model1['id'],
                                        metadata_schema_id=metadata_model2['metadata_schema_id'],
                                        infrastructure_id=metadata_model2['infrastructure_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_update_invalid_with_organization_set_infrastructure(self):
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        infrastructure_id=infrastructure['id'])
        assert_error(result, '__after',
                     'A metadata model may be associated with either an organization or an infrastructure but not both.')

    def test_update_invalid_with_infrastructure_set_organization(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        organization = ckan_factories.Organization()
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        organization_id=organization['id'])
        assert_error(result, '__after',
                     'A metadata model may be associated with either an organization or an infrastructure but not both.')

    def test_update_invalid_not_json(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        model_json='not json')
        assert_error(result, 'model_json', 'JSON decode error')

    def test_update_invalid_not_json_dict(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        model_json='[1,2,3]')
        assert_error(result, 'model_json', 'Expecting a JSON dictionary')

    def test_update_invalid_not_json_schema(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        model_json='{"type": "foo"}')
        assert_error(result, 'model_json', 'Invalid JSON schema')

    def test_update_invalid_bad_references(self):
        metadata_model = ckanext_factories.MetadataModel()
        result, obj = self._test_action('update', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        metadata_schema_id='a',
                                        organization_id='b',
                                        infrastructure_id='c')
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_update_invalid_deleted_references(self):
        metadata_model = ckanext_factories.MetadataModel()
        metadata_schema = ckanext_factories.MetadataSchema()
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        call_action('metadata_schema_delete', id=metadata_schema['id'])
        call_action('organization_delete', id=organization['id'])
        call_action('infrastructure_delete', id=infrastructure['id'])

        result, obj = self._test_action('create', 'metadata_model',
                                        exception_class=tk.ValidationError,
                                        id=metadata_model['id'],
                                        metadata_schema_id=metadata_schema['id'],
                                        organization_id=organization['id'],
                                        infrastructure_id=infrastructure['id'])
        assert_error(result, 'metadata_schema_id', 'Not found: Metadata Schema')
        assert_error(result, 'organization_id', 'Not found: Organization')
        assert_error(result, 'infrastructure_id', 'Not found: Infrastructure')

    def test_delete_valid(self):
        metadata_model = ckanext_factories.MetadataModel()
        self._test_action('delete', 'metadata_model',
                          model_class=ckanext_model.MetadataModel,
                          id=metadata_model['id'])

    def test_delete_invalidate_records(self):
        metadata_record, metadata_model = self._generate_and_validate_metadata_record()
        self._test_action('delete', 'metadata_model',
                          model_class=ckanext_model.MetadataModel,
                          id=metadata_model['id'])
        assert_package_has_extra(metadata_record['id'], 'validated', False)

        metadata_record, metadata_model = self._generate_and_validate_metadata_record(add_organization_to_model=True)
        self._test_action('delete', 'metadata_model',
                          model_class=ckanext_model.MetadataModel,
                          id=metadata_model['id'])
        assert_package_has_extra(metadata_record['id'], 'validated', False)

        metadata_record, metadata_model = self._generate_and_validate_metadata_record(add_infrastructure_to_record=True, add_infrastructure_to_model=True)
        self._test_action('delete', 'metadata_model',
                          model_class=ckanext_model.MetadataModel,
                          id=metadata_model['id'])
        assert_package_has_extra(metadata_record['id'], 'validated', False)
