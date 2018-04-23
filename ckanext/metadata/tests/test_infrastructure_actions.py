# encoding: utf-8

from ckan import model as ckan_model
from ckan.plugins import toolkit as tk
from ckan.tests.helpers import call_action

from ckanext.metadata import model as ckanext_model
from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_object_matches_dict,
    assert_error,
    factories as ckanext_factories,
)


class TestInfrastructureActions(ActionTestBase):

    def test_create_valid(self):
        input_dict = {
            'name': 'test-infrastructure',
            'title': 'Test Infrastructure',
            'description': 'This is a test infrastructure',
        }
        result, obj = self._call_action('create', 'infrastructure',
                                        model_class=ckan_model.Group, **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        input_dict = {
            'id': make_uuid(),
            'name': 'test-infrastructure',
        }
        result, obj = self._call_action('create', 'infrastructure',
                                        model_class=ckan_model.Group,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._call_action('create', 'infrastructure',
                                        exception_class=tk.ValidationError,
                                        name=infrastructure['name'])
        assert_error(result, 'name', 'Group name already exists in database')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._call_action('create', 'infrastructure',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        infrastructure = ckanext_factories.Infrastructure()
        result, obj = self._call_action('create', 'infrastructure',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=infrastructure['id'])
        assert_error(result, 'id', 'Already exists: Group')

    def test_update_valid(self):
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'id': infrastructure['id'],
            'name': 'updated-test-infrastructure',
            'title': 'Updated Test Infrastructure',
            'description': 'Updated test infrastructure',
        }
        result, obj = self._call_action('update', 'infrastructure',
                                        model_class=ckan_model.Group, **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_partial(self):
        infrastructure = ckanext_factories.Infrastructure()
        input_dict = {
            'id': infrastructure['id'],
            'title': 'Updated Test Infrastructure',
        }
        result, obj = self._call_action('update', 'infrastructure',
                                        model_class=ckan_model.Group, **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert obj.title == input_dict['title']
        assert obj.name == infrastructure['name']
        assert obj.description == infrastructure['description']

    def test_update_invalid_duplicate_name(self):
        infrastructure1 = ckanext_factories.Infrastructure()
        infrastructure2 = ckanext_factories.Infrastructure()
        input_dict = {
            'id': infrastructure1['id'],
            'name': infrastructure2['name'],
        }
        result, obj = self._call_action('update', 'infrastructure',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'name', 'Group name already exists in database')

    def test_update_invalid_hierarchy_not_allowed(self):
        infrastructure1 = ckanext_factories.Infrastructure()
        infrastructure2 = ckanext_factories.Infrastructure()
        input_dict = {
            'id': infrastructure1['id'],
            'groups': [{'name': infrastructure2['name']}],
        }
        result, obj = self._call_action('update', 'infrastructure',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, '__junk', 'The input field .*groups.* was not expected.')

    def test_delete_valid(self):
        infrastructure = ckanext_factories.Infrastructure()
        self._call_action('delete', 'infrastructure',
                          model_class=ckan_model.Group,
                          id=infrastructure['id'])

    def test_delete_with_dependencies(self):
        infrastructure = ckanext_factories.Infrastructure()
        metadata_model = ckanext_factories.MetadataModel(infrastructure_id=infrastructure['id'])
        metadata_record = ckanext_factories.MetadataRecord(infrastructures=[{'id': infrastructure['id']}])

        result, obj = self._call_action('delete', 'infrastructure',
                                        exception_class=tk.ValidationError,
                                        id=infrastructure['id'])
        assert_error(result, 'message', 'Infrastructure has dependent metadata records')
        assert ckanext_model.MetadataModel.get(metadata_model['id']).state == 'active'

        call_action('metadata_record_delete', id=metadata_record['id'])
        self._call_action('delete', 'infrastructure',
                          model_class=ckan_model.Group,
                          id=infrastructure['id'])
        assert ckanext_model.MetadataModel.get(metadata_model['id']).state == 'deleted'
