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

    def test_create_valid_invalidate_records(self):
        metadata_record = ckanext_factories.MetadataRecord()
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='partially valid')
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'not validated')

        metadata_record = ckanext_factories.MetadataRecord()
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='invalid')
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id=metadata_record['owner_org'],
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'not validated')

        infrastructure = ckanext_factories.Infrastructure()
        metadata_record = ckanext_factories.MetadataRecord(infrastructures=[{'id': infrastructure['id']}])
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='valid')
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id=infrastructure['id'],
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'not validated')

    def test_create_valid_no_invalidate_records(self):
        metadata_record = ckanext_factories.MetadataRecord()
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='partially valid')
        call_action('metadata_model_create',
                    metadata_schema_id=ckanext_factories.MetadataSchema()['id'],
                    organization_id='',
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'partially valid')

        metadata_record = ckanext_factories.MetadataRecord()
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='invalid')
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id=ckan_factories.Organization()['id'],
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'invalid')

        infrastructure = ckanext_factories.Infrastructure()
        metadata_record = ckanext_factories.MetadataRecord(infrastructures=[{'id': infrastructure['id']}])
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='valid')
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id=ckanext_factories.Infrastructure()['id'],
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'valid')

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

    def test_update_with_dependent_records(self):
        metadata_schema = ckanext_factories.MetadataSchema()
        organization = ckan_factories.Organization()
        infrastructure = ckanext_factories.Infrastructure()
        metadata_record_1 = ckanext_factories.MetadataRecord(metadata_schema_id=metadata_schema['id'])
        metadata_record_2 = ckanext_factories.MetadataRecord(metadata_schema_id=metadata_schema['id'], owner_org=organization['id'])
        metadata_record_3 = ckanext_factories.MetadataRecord(metadata_schema_id=metadata_schema['id'], owner_org=organization['id'], infrastructures=[{'id': infrastructure['id']}])

        metadata_model = ckanext_factories.MetadataModel(metadata_schema_id=metadata_schema['id'])
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_1['id'], metadata_record_2['id'], metadata_record_3['id']}

        # change the model_json - invalidate all dependents
        call_action('metadata_record_validation_state_override', id=metadata_record_1['id'], validation_state='valid')
        call_action('metadata_record_validation_state_override', id=metadata_record_2['id'], validation_state='invalid')
        call_action('metadata_record_validation_state_override', id=metadata_record_3['id'], validation_state='partially valid')
        call_action('metadata_model_update',
                    id=metadata_model['id'],
                    metadata_schema_id=metadata_schema['id'],
                    organization_id='',
                    infrastructure_id='',
                    model_json='{ "newtestkey": "newtestvalue" }')
        assert_package_has_extra(metadata_record_1['id'], 'validation_state', 'not validated')
        assert_package_has_extra(metadata_record_2['id'], 'validation_state', 'not validated')
        assert_package_has_extra(metadata_record_3['id'], 'validation_state', 'not validated')

        # set the infrastructure - invalidate the records that are no longer dependent
        call_action('metadata_record_validation_state_override', id=metadata_record_1['id'], validation_state='valid')
        call_action('metadata_record_validation_state_override', id=metadata_record_2['id'], validation_state='invalid')
        call_action('metadata_record_validation_state_override', id=metadata_record_3['id'], validation_state='partially valid')
        call_action('metadata_model_update',
                    id=metadata_model['id'],
                    metadata_schema_id=metadata_schema['id'],
                    organization_id='',
                    infrastructure_id=infrastructure['id'],
                    model_json='{ "newtestkey": "newtestvalue" }')
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_3['id']}
        assert_package_has_extra(metadata_record_1['id'], 'validation_state', 'not validated')
        assert_package_has_extra(metadata_record_2['id'], 'validation_state', 'not validated')
        assert_package_has_extra(metadata_record_3['id'], 'validation_state', 'partially valid')

        # set the organization - invalidate the record that is newly dependent
        call_action('metadata_record_validation_state_override', id=metadata_record_1['id'], validation_state='valid')
        call_action('metadata_record_validation_state_override', id=metadata_record_2['id'], validation_state='invalid')
        call_action('metadata_record_validation_state_override', id=metadata_record_3['id'], validation_state='partially valid')
        call_action('metadata_model_update',
                    id=metadata_model['id'],
                    metadata_schema_id=metadata_schema['id'],
                    organization_id=organization['id'],
                    infrastructure_id='',
                    model_json='{ "newtestkey": "newtestvalue" }')
        dependent_records = call_action('metadata_model_dependent_record_list', id=metadata_model['id'])
        assert set(dependent_records) == {metadata_record_2['id'], metadata_record_3['id']}
        assert_package_has_extra(metadata_record_1['id'], 'validation_state', 'valid')
        assert_package_has_extra(metadata_record_2['id'], 'validation_state', 'not validated')
        assert_package_has_extra(metadata_record_3['id'], 'validation_state', 'partially valid')

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

    def test_delete_valid_invalidate_records(self):
        metadata_record = ckanext_factories.MetadataRecord()
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='partially valid')
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'not validated')

        metadata_record = ckanext_factories.MetadataRecord()
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='invalid')
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id=metadata_record['owner_org'],
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'not validated')

        infrastructure = ckanext_factories.Infrastructure()
        metadata_record = ckanext_factories.MetadataRecord(infrastructures=[{'id': infrastructure['id']}])
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='valid')
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id=infrastructure['id'],
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'not validated')

    def test_delete_valid_no_invalidate_records(self):
        metadata_record = ckanext_factories.MetadataRecord()
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='partially valid')
        call_action('metadata_model_create',
                    metadata_schema_id=ckanext_factories.MetadataSchema()['id'],
                    organization_id='',
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'partially valid')

        metadata_record = ckanext_factories.MetadataRecord()
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='invalid')
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id=ckan_factories.Organization()['id'],
                    infrastructure_id='',
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'invalid')

        infrastructure = ckanext_factories.Infrastructure()
        metadata_record = ckanext_factories.MetadataRecord(infrastructures=[{'id': infrastructure['id']}])
        call_action('metadata_record_validation_state_override', id=metadata_record['id'], validation_state='valid')
        call_action('metadata_model_create',
                    metadata_schema_id=metadata_record['metadata_schema_id'],
                    organization_id='',
                    infrastructure_id=ckanext_factories.Infrastructure()['id'],
                    model_json='')
        assert_package_has_extra(metadata_record['id'], 'validation_state', 'valid')
