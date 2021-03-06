# encoding: utf-8

from ckan.tests.helpers import call_action

from ckanext.metadata import model as ckanext_model
from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_object_matches_dict,
    assert_package_has_extra,
    assert_package_has_attribute,
    assert_error,
    factories as ckanext_factories,
)


class TestWorkflowStateActions(ActionTestBase):

    def test_create_valid(self):
        input_dict = {
            'name': 'test-workflow-state',
            'title': 'Test Workflow State',
            'description': 'This is a test workflow state',
            'revert_state_id': '',
            'metadata_records_private': True,
            'workflow_rules_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self.test_action('workflow_state_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_revert(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'name': 'test-workflow-state',
            'revert_state_id': workflow_state['id'],
            'metadata_records_private': False,
            'workflow_rules_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self.test_action('workflow_state_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_revert_byname(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'name': 'test-workflow-state',
            'revert_state_id': workflow_state['name'],
            'metadata_records_private': False,
            'workflow_rules_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self.test_action('workflow_state_create', **input_dict)
        input_dict['revert_state_id'] = workflow_state['id']
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        workflow_state = ckanext_factories.WorkflowState()
        result, obj = self.test_action('workflow_state_create', should_error=True,
                                       name=workflow_state['name'])
        assert_error(result, 'name', 'Duplicate name: Workflow State')

    def test_create_invalid_missing_params(self):
        result, obj = self.test_action('workflow_state_create', should_error=True)
        assert_error(result, 'name', 'Missing parameter')
        assert_error(result, 'revert_state_id', 'Missing parameter')
        assert_error(result, 'metadata_records_private', 'Missing parameter')
        assert_error(result, 'workflow_rules_json', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self.test_action('workflow_state_create', should_error=True,
                                       name='',
                                       workflow_rules_json='')
        assert_error(result, 'name', 'Missing value')
        assert_error(result, 'workflow_rules_json', 'Missing value')

    def test_create_invalid_bad_revert(self):
        result, obj = self.test_action('workflow_state_create', should_error=True,
                                       revert_state_id='foo')
        assert_error(result, 'revert_state_id', 'Not found: Workflow State')

    def test_create_invalid_deleted_revert(self):
        workflow_state = ckanext_factories.WorkflowState()
        call_action('workflow_state_delete', id=workflow_state['id'])
        result, obj = self.test_action('workflow_state_create', should_error=True,
                                       revert_state_id=workflow_state['id'])
        assert_error(result, 'revert_state_id', 'Not found: Workflow State')

    def test_update_valid(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'id': workflow_state['id'],
            'name': 'updated-test-workflow-state',
            'title': 'Updated Test Workflow State',
            'description': 'Updated test workflow state description',
            'revert_state_id': '',
            'metadata_records_private': False,
            'workflow_rules_json': '{ "testkey": "newtestvalue" }',
        }
        result, obj = self.test_action('workflow_state_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_partial(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'id': workflow_state['id'],
            'name': 'updated-test-workflow-state',
            'revert_state_id': '',
            'metadata_records_private': False,
            'workflow_rules_json': '{ "testkey": "newtestvalue" }',
        }
        result, obj = self.test_action('workflow_state_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.title == workflow_state['title']
        assert obj.description == workflow_state['description']

    def test_update_valid_change_revert_1(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        input_dict = {
            'id': workflow_state1['id'],
            'name': workflow_state1['name'],
            'revert_state_id': workflow_state2['id'],
            'metadata_records_private': True,
            'workflow_rules_json': '{}',
        }
        result, obj = self.test_action('workflow_state_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_change_revert_2(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState(revert_state_id=workflow_state1['id'])
        workflow_state3 = ckanext_factories.WorkflowState(revert_state_id=workflow_state2['id'])
        input_dict = {
            'id': workflow_state3['id'],
            'name': workflow_state3['name'],
            'revert_state_id': workflow_state1['id'],
            'metadata_records_private': True,
            'workflow_rules_json': '{}',
        }
        result, obj = self.test_action('workflow_state_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_change_revert_3(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState(revert_state_id=workflow_state1['id'])
        workflow_state3 = ckanext_factories.WorkflowState(revert_state_id=workflow_state2['id'])
        ckanext_factories.WorkflowTransition(from_state_id=workflow_state1['id'], to_state_id=workflow_state2['id'])
        ckanext_factories.WorkflowTransition(from_state_id=workflow_state2['id'], to_state_id=workflow_state3['id'])
        input_dict = {
            'id': workflow_state3['id'],
            'name': workflow_state3['name'],
            'revert_state_id': workflow_state1['id'],
            'metadata_records_private': True,
            'workflow_rules_json': '{}',
        }
        result, obj = self.test_action('workflow_state_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_metadata_records_private_cascade_1(self):
        """
        Test that the visibility of a metadata record is determined by that of its workflow state.
        """
        metadata_record = ckanext_factories.MetadataRecord()
        workflow_state = ckanext_factories.WorkflowState(metadata_records_private=False)
        call_action('metadata_record_workflow_state_override', context={'user': self.normal_user['name']},
                    id=metadata_record['id'],
                    workflow_state_id=workflow_state['id'])
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state['id'])
        assert_package_has_attribute(metadata_record['id'], 'private', False)

        input_dict = {
            'id': workflow_state['id'],
            'revert_state_id': '',
            'metadata_records_private': True,
            'workflow_rules_json': '{}',
        }
        result, obj = self.test_action('workflow_state_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state['id'])
        assert_package_has_attribute(metadata_record['id'], 'private', True)

    def test_update_metadata_records_private_cascade_2(self):
        """
        Test that the visibility of a metadata record is determined by that of its workflow state.
        """
        metadata_record = ckanext_factories.MetadataRecord()
        workflow_state = ckanext_factories.WorkflowState(metadata_records_private=True)
        call_action('metadata_record_workflow_state_override', context={'user': self.normal_user['name']},
                    id=metadata_record['id'],
                    workflow_state_id=workflow_state['id'])
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state['id'])
        assert_package_has_attribute(metadata_record['id'], 'private', True)

        input_dict = {
            'id': workflow_state['id'],
            'revert_state_id': '',
            'metadata_records_private': False,
            'workflow_rules_json': '{}',
        }
        result, obj = self.test_action('workflow_state_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state['id'])
        assert_package_has_attribute(metadata_record['id'], 'private', False)

    def test_update_invalid_duplicate_name(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        input_dict = {
            'id': workflow_state1['id'],
            'name': workflow_state2['name'],
        }
        result, obj = self.test_action('workflow_state_update', should_error=True, **input_dict)
        assert_error(result, 'name', 'Duplicate name: Workflow State')

    def test_update_invalid_missing_params(self):
        workflow_state = ckanext_factories.WorkflowState()
        result, obj = self.test_action('workflow_state_update', should_error=True,
                                       id=workflow_state['id'])
        assert_error(result, 'revert_state_id', 'Missing parameter')
        assert_error(result, 'metadata_records_private', 'Missing parameter')
        assert_error(result, 'workflow_rules_json', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        workflow_state = ckanext_factories.WorkflowState()
        result, obj = self.test_action('workflow_state_update', should_error=True,
                                       id=workflow_state['id'],
                                       workflow_rules_json='')
        assert_error(result, 'workflow_rules_json', 'Missing value')

    def test_update_invalid_circular_revert(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState(revert_state_id=workflow_state1['id'])
        workflow_state3 = ckanext_factories.WorkflowState(revert_state_id=workflow_state2['id'])

        result, obj = self.test_action('workflow_state_update', should_error=True,
                                       id=workflow_state1['id'],
                                       revert_state_id=workflow_state2['id'])
        assert_error(result, 'revert_state_id', 'Revert loop in workflow state graph')

        result, obj = self.test_action('workflow_state_update', should_error=True,
                                       id=workflow_state1['id'],
                                       revert_state_id=workflow_state3['id'])
        assert_error(result, 'revert_state_id', 'Revert loop in workflow state graph')

    def test_update_invalid_forward_revert(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        workflow_state3 = ckanext_factories.WorkflowState()
        ckanext_factories.WorkflowTransition(from_state_id=workflow_state1['id'], to_state_id=workflow_state2['id'])
        ckanext_factories.WorkflowTransition(from_state_id=workflow_state2['id'], to_state_id=workflow_state3['id'])

        result, obj = self.test_action('workflow_state_update', should_error=True,
                                       id=workflow_state1['id'],
                                       revert_state_id=workflow_state2['id'])
        assert_error(result, 'revert_state_id', 'Forward revert in workflow state graph')

        result, obj = self.test_action('workflow_state_update', should_error=True,
                                       id=workflow_state1['id'],
                                       revert_state_id=workflow_state3['id'])
        assert_error(result, 'revert_state_id', 'Forward revert in workflow state graph')

    def test_update_invalid_self_revert(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'id': workflow_state['id'],
            'revert_state_id': workflow_state['id'],
        }
        result, obj = self.test_action('workflow_state_update', should_error=True, **input_dict)
        assert_error(result, 'revert_state_id', 'A workflow state cannot revert to itself')

    def test_update_invalid_bad_revert(self):
        workflow_state = ckanext_factories.WorkflowState()
        result, obj = self.test_action('workflow_state_update', should_error=True,
                                       id=workflow_state['id'],
                                       revert_state_id='foo')
        assert_error(result, 'revert_state_id', 'Not found: Workflow State')

    def test_update_invalid_deleted_revert(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        call_action('workflow_state_delete', id=workflow_state1['id'])
        result, obj = self.test_action('workflow_state_update', should_error=True,
                                       id=workflow_state2['id'],
                                       revert_state_id=workflow_state1['id'])
        assert_error(result, 'revert_state_id', 'Not found: Workflow State')

    def test_delete_valid(self):
        workflow_state = ckanext_factories.WorkflowState()
        self.test_action('workflow_state_delete',
                         id=workflow_state['id'])

    def test_delete_with_dependencies(self):
        metadata_record = ckanext_factories.MetadataRecord()
        workflow_state = ckanext_factories.WorkflowState()
        call_action('metadata_record_workflow_state_override', context={'user': self.normal_user['name']},
                    id=metadata_record['id'],
                    workflow_state_id=workflow_state['id'])
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state['id'])

        result, obj = self.test_action('workflow_state_delete', should_error=True,
                                       id=workflow_state['id'])
        assert_error(result, 'message', 'Workflow state has dependent metadata records')

        call_action('metadata_record_delete', id=metadata_record['id'])
        self.test_action('workflow_state_delete',
                         id=workflow_state['id'])

    def test_delete_with_revert_references(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState(revert_state_id=workflow_state1['name'])
        assert workflow_state2['revert_state_id'] == workflow_state1['id']

        self.test_action('workflow_state_delete',
                         id=workflow_state1['id'])
        workflow_state2['revert_state_id'] = None
        del workflow_state2['revision_id']
        del workflow_state2['display_name']
        assert_object_matches_dict(ckanext_model.WorkflowState.get(workflow_state2['id']), workflow_state2, json_values=('workflow_rules_json',))

    def test_delete_with_transition_references(self):
        workflow_state = ckanext_factories.WorkflowState()
        workflow_transition = ckanext_factories.WorkflowTransition(from_state_id=workflow_state['id'])
        self.test_action('workflow_state_delete',
                         id=workflow_state['id'])
        assert ckanext_model.WorkflowTransition.get(workflow_transition['id']).state == 'deleted'

        workflow_state = ckanext_factories.WorkflowState()
        workflow_transition = ckanext_factories.WorkflowTransition(to_state_id=workflow_state['id'])
        self.test_action('workflow_state_delete',
                         id=workflow_state['id'])
        assert ckanext_model.WorkflowTransition.get(workflow_transition['id']).state == 'deleted'

        workflow_state = ckanext_factories.WorkflowState()
        workflow_transition = ckanext_factories.WorkflowTransition(from_state_id=None, to_state_id=workflow_state['id'])
        self.test_action('workflow_state_delete',
                         id=workflow_state['id'])
        assert ckanext_model.WorkflowTransition.get(workflow_transition['id']).state == 'deleted'
