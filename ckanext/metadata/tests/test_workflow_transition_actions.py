# encoding: utf-8

from ckan.tests.helpers import call_action

from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_object_matches_dict,
    assert_error,
    factories as ckanext_factories,
)


class TestWorkflowTransitionActions(ActionTestBase):

    def test_create_valid(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        input_dict = {
            'from_state_id': workflow_state1['id'],
            'to_state_id': workflow_state2['id'],
        }
        result, obj = self.test_action('workflow_transition_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_initial_transition(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'from_state_id': '',
            'to_state_id': workflow_state['id'],
        }
        result, obj = self.test_action('workflow_transition_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_byname(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        input_dict = {
            'from_state_id': workflow_state1['name'],
            'to_state_id': workflow_state2['name'],
        }
        result, obj = self.test_action('workflow_transition_create', **input_dict)
        input_dict = {
            'from_state_id': workflow_state1['id'],
            'to_state_id': workflow_state2['id'],
        }
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_missing_params(self):
        result, obj = self.test_action('workflow_transition_create', should_error=True)
        assert_error(result, 'from_state_id', 'Missing parameter')
        assert_error(result, 'to_state_id', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self.test_action('workflow_transition_create', should_error=True,
                                       to_state_id='')
        assert_error(result, 'to_state_id', 'Missing value')

    def test_create_invalid_self_transition(self):
        workflow_state = ckanext_factories.WorkflowState()
        result, obj = self.test_action('workflow_transition_create', should_error=True,
                                       from_state_id=workflow_state['id'],
                                       to_state_id=workflow_state['id'])
        assert_error(result, '__after', 'The from- and to-state of a workflow transition cannot be the same.')

    def test_create_invalid_bad_states(self):
        result, obj = self.test_action('workflow_transition_create', should_error=True,
                                       from_state_id='foo',
                                       to_state_id='bar')
        assert_error(result, 'from_state_id', 'Not found: Workflow State')
        assert_error(result, 'to_state_id', 'Not found: Workflow State')

    def test_create_invalid_deleted_states(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        call_action('workflow_state_delete', id=workflow_state1['id'])
        call_action('workflow_state_delete', id=workflow_state2['id'])
        result, obj = self.test_action('workflow_transition_create', should_error=True,
                                       from_state_id=workflow_state1['id'],
                                       to_state_id=workflow_state2['id'])
        assert_error(result, 'from_state_id', 'Not found: Workflow State')
        assert_error(result, 'to_state_id', 'Not found: Workflow State')

    def test_create_invalid_duplicate(self):
        workflow_transition = ckanext_factories.WorkflowTransition()
        result, obj = self.test_action('workflow_transition_create', should_error=True,
                                       from_state_id=workflow_transition['from_state_id'],
                                       to_state_id=workflow_transition['to_state_id'])
        assert_error(result, '__after', 'Unique constraint violation')

        workflow_transition = ckanext_factories.WorkflowTransition(from_state_id='')
        result, obj = self.test_action('workflow_transition_create', should_error=True,
                                       from_state_id='',
                                       to_state_id=workflow_transition['to_state_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_circular_transition(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        workflow_state3 = ckanext_factories.WorkflowState()
        ckanext_factories.WorkflowTransition(from_state_id=workflow_state1['id'], to_state_id=workflow_state2['id'])
        ckanext_factories.WorkflowTransition(from_state_id=workflow_state2['id'], to_state_id=workflow_state3['id'])

        result, obj = self.test_action('workflow_transition_create', should_error=True,
                                       from_state_id=workflow_state2['id'],
                                       to_state_id=workflow_state1['id'])
        assert_error(result, '__after', 'Transition loop in workflow state graph')

        result, obj = self.test_action('workflow_transition_create', should_error=True,
                                       from_state_id=workflow_state3['id'],
                                       to_state_id=workflow_state1['id'])
        assert_error(result, '__after', 'Transition loop in workflow state graph')

    def test_create_invalid_backward_transition(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState(revert_state_id=workflow_state1['id'])
        workflow_state3 = ckanext_factories.WorkflowState(revert_state_id=workflow_state2['id'])

        result, obj = self.test_action('workflow_transition_create', should_error=True,
                                       from_state_id=workflow_state2['id'],
                                       to_state_id=workflow_state1['id'])
        assert_error(result, '__after', 'Backward transition in workflow state graph')

        result, obj = self.test_action('workflow_transition_create', should_error=True,
                                       from_state_id=workflow_state3['id'],
                                       to_state_id=workflow_state1['id'])
        assert_error(result, '__after', 'Backward transition in workflow state graph')

    def test_update_invalid(self):
        workflow_transition = ckanext_factories.WorkflowTransition()
        result, obj = self.test_action('workflow_transition_update', should_error=True,
                                       id=workflow_transition['id'])
        assert_error(result, 'message', 'A workflow transition cannot be updated. Delete it and create a new one instead.')

    def test_delete_valid(self):
        workflow_transition = ckanext_factories.WorkflowTransition()
        self.test_action('workflow_transition_delete',
                         id=workflow_transition['id'])
