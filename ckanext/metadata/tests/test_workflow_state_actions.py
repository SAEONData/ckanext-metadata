# encoding: utf-8

from ckan.plugins import toolkit as tk
from ckan.tests.helpers import call_action

from ckanext.metadata import model as ckanext_model
from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_object_matches_dict,
    assert_package_has_extra,
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
        }
        result, obj = self._test_action('create', 'workflow_state',
                                        model_class=ckanext_model.WorkflowState, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_revert(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'name': 'test-workflow-state',
            'revert_state_id': workflow_state['id'],
        }
        result, obj = self._test_action('create', 'workflow_state',
                                        model_class=ckanext_model.WorkflowState, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_with_revert_byname(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'name': 'test-workflow-state',
            'revert_state_id': workflow_state['name'],
        }
        result, obj = self._test_action('create', 'workflow_state',
                                        model_class=ckanext_model.WorkflowState, **input_dict)
        input_dict['revert_state_id'] = workflow_state['id']
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        input_dict = {
            'id': make_uuid(),
            'name': 'test-workflow-state',
            'revert_state_id': '',
        }
        result, obj = self._test_action('create', 'workflow_state',
                                        model_class=ckanext_model.WorkflowState,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        workflow_state = ckanext_factories.WorkflowState()
        result, obj = self._test_action('create', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        name=workflow_state['name'])
        assert_error(result, 'name', 'Duplicate name: Workflow State')

    def test_create_invalid_missing_params(self):
        result, obj = self._test_action('create', 'workflow_state',
                                        exception_class=tk.ValidationError)
        assert_error(result, 'name', 'Missing parameter')
        assert_error(result, 'revert_state_id', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self._test_action('create', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        name='')
        assert_error(result, 'name', 'Missing value')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._test_action('create', 'workflow_state',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        workflow_state = ckanext_factories.WorkflowState()
        result, obj = self._test_action('create', 'workflow_state',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=workflow_state['id'])
        assert_error(result, 'id', 'Already exists: Workflow State')

    def test_create_invalid_sysadmin_self_revert(self):
        new_id = make_uuid()
        input_dict = {
            'id': new_id,
            'revert_state_id': new_id,
        }
        result, obj = self._test_action('create', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert_error(result, 'revert_state_id', 'Not found: Workflow State')

    def test_create_invalid_bad_revert(self):
        result, obj = self._test_action('create', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        revert_state_id='foo')
        assert_error(result, 'revert_state_id', 'Not found: Workflow State')

    def test_create_invalid_deleted_revert(self):
        workflow_state = ckanext_factories.WorkflowState()
        call_action('workflow_state_delete', id=workflow_state['id'])
        result, obj = self._test_action('create', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        revert_state_id=workflow_state['id'])
        assert_error(result, 'revert_state_id', 'Not found: Workflow State')

    def test_update_valid(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'id': workflow_state['id'],
            'name': 'test-workflow-state',
            'title': 'Updated Test Workflow State',
            'description': 'Updated test workflow state description',
            'revert_state_id': '',
        }
        result, obj = self._test_action('update', 'workflow_state',
                                        model_class=ckanext_model.WorkflowState, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_partial(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'id': workflow_state['id'],
            'name': 'updated-test-workflow-state',
            'revert_state_id': '',
        }
        result, obj = self._test_action('update', 'workflow_state',
                                        model_class=ckanext_model.WorkflowState, **input_dict)
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
        }
        result, obj = self._test_action('update', 'workflow_state',
                                        model_class=ckanext_model.WorkflowState, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_change_revert_2(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState(revert_state_id=workflow_state1['id'])
        workflow_state3 = ckanext_factories.WorkflowState(revert_state_id=workflow_state2['id'])
        input_dict = {
            'id': workflow_state3['id'],
            'name': workflow_state3['name'],
            'revert_state_id': workflow_state1['id'],
        }
        result, obj = self._test_action('update', 'workflow_state',
                                        model_class=ckanext_model.WorkflowState, **input_dict)
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
        }
        result, obj = self._test_action('update', 'workflow_state',
                                        model_class=ckanext_model.WorkflowState, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_invalid_duplicate_name(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        input_dict = {
            'id': workflow_state1['id'],
            'name': workflow_state2['name'],
        }
        result, obj = self._test_action('update', 'workflow_state',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'name', 'Duplicate name: Workflow State')

    def test_update_invalid_missing_params(self):
        workflow_state = ckanext_factories.WorkflowState()
        result, obj = self._test_action('update', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        id=workflow_state['id'])
        assert_error(result, 'revert_state_id', 'Missing parameter')

    def test_update_invalid_circular_revert(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState(revert_state_id=workflow_state1['id'])
        workflow_state3 = ckanext_factories.WorkflowState(revert_state_id=workflow_state2['id'])

        result, obj = self._test_action('update', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        id=workflow_state1['id'],
                                        revert_state_id=workflow_state2['id'])
        assert_error(result, 'revert_state_id', 'Revert loop in workflow state graph')

        result, obj = self._test_action('update', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        id=workflow_state1['id'],
                                        revert_state_id=workflow_state3['id'])
        assert_error(result, 'revert_state_id', 'Revert loop in workflow state graph')

    def test_update_invalid_forward_revert(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        workflow_state3 = ckanext_factories.WorkflowState()
        ckanext_factories.WorkflowTransition(from_state_id=workflow_state1['id'], to_state_id=workflow_state2['id'])
        ckanext_factories.WorkflowTransition(from_state_id=workflow_state2['id'], to_state_id=workflow_state3['id'])

        result, obj = self._test_action('update', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        id=workflow_state1['id'],
                                        revert_state_id=workflow_state2['id'])
        assert_error(result, 'revert_state_id', 'Forward revert in workflow state graph')

        result, obj = self._test_action('update', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        id=workflow_state1['id'],
                                        revert_state_id=workflow_state3['id'])
        assert_error(result, 'revert_state_id', 'Forward revert in workflow state graph')

    def test_update_invalid_self_revert(self):
        workflow_state = ckanext_factories.WorkflowState()
        input_dict = {
            'id': workflow_state['id'],
            'revert_state_id': workflow_state['id'],
        }
        result, obj = self._test_action('update', 'workflow_state',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'revert_state_id', 'A workflow state cannot revert to itself')

    def test_update_invalid_bad_revert(self):
        workflow_state = ckanext_factories.WorkflowState()
        result, obj = self._test_action('update', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        id=workflow_state['id'],
                                        revert_state_id='foo')
        assert_error(result, 'revert_state_id', 'Not found: Workflow State')

    def test_update_invalid_deleted_revert(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState()
        call_action('workflow_state_delete', id=workflow_state1['id'])
        result, obj = self._test_action('update', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        id=workflow_state2['id'],
                                        revert_state_id=workflow_state1['id'])
        assert_error(result, 'revert_state_id', 'Not found: Workflow State')

    def test_delete_valid(self):
        workflow_state = ckanext_factories.WorkflowState()
        self._test_action('delete', 'workflow_state',
                          model_class=ckanext_model.WorkflowState,
                          id=workflow_state['id'])

    def test_delete_with_dependencies(self):
        metadata_record = ckanext_factories.MetadataRecord()
        workflow_state = ckanext_factories.WorkflowState()
        call_action('metadata_record_workflow_state_override',
                    id=metadata_record['id'],
                    workflow_state_id=workflow_state['id'])
        assert_package_has_extra(metadata_record['id'], 'workflow_state_id', workflow_state['id'])

        result, obj = self._test_action('delete', 'workflow_state',
                                        exception_class=tk.ValidationError,
                                        id=workflow_state['id'])
        assert_error(result, 'message', 'Workflow state has dependent metadata records')

        call_action('metadata_record_delete', id=metadata_record['id'])
        self._test_action('delete', 'workflow_state',
                          model_class=ckanext_model.WorkflowState,
                          id=workflow_state['id'])

    def test_delete_with_revert_references(self):
        workflow_state1 = ckanext_factories.WorkflowState()
        workflow_state2 = ckanext_factories.WorkflowState(revert_state_id=workflow_state1['name'])
        assert workflow_state2['revert_state_id'] == workflow_state1['id']

        self._test_action('delete', 'workflow_state',
                          model_class=ckanext_model.WorkflowState,
                          id=workflow_state1['id'])
        workflow_state2['revert_state_id'] = None
        del workflow_state2['revision_id']
        assert_object_matches_dict(ckanext_model.WorkflowState.get(workflow_state2['id']), workflow_state2)

    def test_delete_with_transition_references(self):
        workflow_state = ckanext_factories.WorkflowState()
        workflow_transition = ckanext_factories.WorkflowTransition(from_state_id=workflow_state['id'])
        self._test_action('delete', 'workflow_state',
                          model_class=ckanext_model.WorkflowState,
                          id=workflow_state['id'])
        assert ckanext_model.WorkflowTransition.get(workflow_transition['id']).state == 'deleted'

        workflow_state = ckanext_factories.WorkflowState()
        workflow_transition = ckanext_factories.WorkflowTransition(to_state_id=workflow_state['id'])
        self._test_action('delete', 'workflow_state',
                          model_class=ckanext_model.WorkflowState,
                          id=workflow_state['id'])
        assert ckanext_model.WorkflowTransition.get(workflow_transition['id']).state == 'deleted'

        workflow_state = ckanext_factories.WorkflowState()
        workflow_transition = ckanext_factories.WorkflowTransition(from_state_id=None, to_state_id=workflow_state['id'])
        self._test_action('delete', 'workflow_state',
                          model_class=ckanext_model.WorkflowState,
                          id=workflow_state['id'])
        assert ckanext_model.WorkflowTransition.get(workflow_transition['id']).state == 'deleted'

    def test_delete_with_rule_references(self):
        workflow_state = ckanext_factories.WorkflowState()
        workflow_rule = ckanext_factories.WorkflowRule(workflow_state_id=workflow_state['id'])
        self._test_action('delete', 'workflow_state',
                          model_class=ckanext_model.WorkflowState,
                          id=workflow_state['id'])
        assert ckanext_model.WorkflowRule.get(workflow_rule['id']).state == 'deleted'
