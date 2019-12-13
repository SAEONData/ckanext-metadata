# encoding: utf-8

from ckan.tests.helpers import call_action
import ckan.plugins.toolkit as tk

from ckanext.metadata import model as ckanext_model
from ckanext.metadata.tests import (
    ActionTestBase,
    assert_object_matches_dict,
    assert_error,
    factories as ckanext_factories,
)


class TestInfrastructureActions(ActionTestBase):

    def _generate_infrastructure(self, **kwargs):
        return ckanext_factories.Infrastructure(user=self.normal_user, **kwargs)

    def test_create_valid(self):
        input_dict = {
            'name': 'test-infrastructure',
            'title': 'Test Infrastructure',
            'description': 'This is a test infrastructure',
        }
        result, obj = self.test_action('infrastructure_create', **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        infrastructure = self._generate_infrastructure()
        result, obj = self.test_action('infrastructure_create', should_error=True,
                                       name=infrastructure['name'])
        assert_error(result, 'name', 'Group name already exists in database')

    def test_update_valid(self):
        infrastructure = self._generate_infrastructure()
        input_dict = {
            'id': infrastructure['id'],
            'name': 'updated-test-infrastructure',
            'title': 'Updated Test Infrastructure',
            'description': 'Updated test infrastructure',
        }
        result, obj = self.test_action('infrastructure_update', **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_partial(self):
        infrastructure = self._generate_infrastructure()
        input_dict = {
            'id': infrastructure['id'],
            'title': 'Updated Test Infrastructure',
        }
        result, obj = self.test_action('infrastructure_update', **input_dict)
        assert obj.type == 'infrastructure'
        assert obj.is_organization == False
        assert obj.title == input_dict['title']
        assert obj.name == infrastructure['name']
        assert obj.description == infrastructure['description']

    def test_update_invalid_duplicate_name(self):
        infrastructure1 = self._generate_infrastructure()
        infrastructure2 = self._generate_infrastructure()
        input_dict = {
            'id': infrastructure1['id'],
            'name': infrastructure2['name'],
        }
        result, obj = self.test_action('infrastructure_update', should_error=True, **input_dict)
        assert_error(result, 'name', 'Group name already exists in database')

    def test_update_invalid_hierarchy_not_allowed(self):
        infrastructure1 = self._generate_infrastructure()
        infrastructure2 = self._generate_infrastructure()
        input_dict = {
            'id': infrastructure1['id'],
            'groups': [{'name': infrastructure2['name']}],
        }
        result, obj = self.test_action('infrastructure_update', should_error=True, **input_dict)
        assert_error(result, '__junk', 'The input field .*groups.* was not expected.')

    def test_delete_valid(self):
        infrastructure = self._generate_infrastructure()
        self.test_action('infrastructure_delete',
                         id=infrastructure['id'])

    def test_delete_with_dependencies(self):
        infrastructure = self._generate_infrastructure()
        metadata_schema = ckanext_factories.MetadataSchema(infrastructure_id=infrastructure['id'])
        metadata_collection = ckanext_factories.MetadataCollection(infrastructures=[{'id': infrastructure['id']}])

        result, obj = self.test_action('infrastructure_delete', should_error=True,
                                       id=infrastructure['id'])
        assert_error(result, 'message', 'Infrastructure has dependent metadata collections')
        assert ckanext_model.MetadataSchema.get(metadata_schema['id']).state == 'active'

        call_action('metadata_collection_delete', id=metadata_collection['id'])
        self.test_action('infrastructure_delete',
                         id=infrastructure['id'])
        assert ckanext_model.MetadataSchema.get(metadata_schema['id']).state == 'deleted'

    def test_member_create_invalid(self):
        metadata_record = ckanext_factories.MetadataRecord()
        infrastructure = self._generate_infrastructure()
        result, obj = self.test_action('member_create', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       id=infrastructure['id'],
                                       object=metadata_record['id'],
                                       object_type='package',
                                       capacity='public')
        assert_error(result, None, "This action may not be used to alter a metadata record's membership of metadata collections or infrastructures.")

    def test_member_delete_invalid(self):
        infrastructure = self._generate_infrastructure()
        metadata_collection = ckanext_factories.MetadataCollection(infrastructures=[{'id': infrastructure['id']}])
        result, obj = self.test_action('member_delete', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       id=infrastructure['id'],
                                       object=metadata_collection['id'],
                                       object_type='group')
        assert_error(result, None, "This action may not be used to alter a metadata collection's membership of infrastructures.")

    def test_group_create_invalid(self):
        result, obj = self.test_action('group_create', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       type='infrastructure')
        assert_error(result, None, "This action may not be used for infrastructure type objects.")

    def test_group_update_invalid(self):
        infrastructure = self._generate_infrastructure()
        result, obj = self.test_action('group_update', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       id=infrastructure['id'])
        assert_error(result, None, "This action may not be used for infrastructure type objects.")

    def test_group_delete_invalid(self):
        infrastructure = self._generate_infrastructure()
        result, obj = self.test_action('group_delete', should_error=True, check_auth=True,
                                       exception_class=tk.NotAuthorized,
                                       id=infrastructure['id'])
        assert_error(result, None, "This action may not be used for infrastructure type objects.")
