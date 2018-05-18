# encoding: utf-8

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


class TestWorkflowRuleActions(ActionTestBase):

    def test_create_valid(self):
        workflow_state = ckanext_factories.WorkflowState()
        workflow_metric = ckanext_factories.WorkflowMetric()
        input_dict = {
            'workflow_state_id': workflow_state['id'],
            'workflow_metric_id': workflow_metric['id'],
            'rule_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._test_action('create', 'workflow_rule',
                                        model_class=ckanext_model.WorkflowRule, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_byname(self):
        workflow_state = ckanext_factories.WorkflowState()
        workflow_metric = ckanext_factories.WorkflowMetric()
        input_dict = {
            'workflow_state_id': workflow_state['name'],
            'workflow_metric_id': workflow_metric['name'],
            'rule_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._test_action('create', 'workflow_rule',
                                        model_class=ckanext_model.WorkflowRule, **input_dict)
        input_dict = {
            'workflow_state_id': workflow_state['id'],
            'workflow_metric_id': workflow_metric['id'],
            'rule_json': '{ "testkey": "testvalue" }',
        }
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        workflow_state = ckanext_factories.WorkflowState()
        workflow_metric = ckanext_factories.WorkflowMetric()
        input_dict = {
            'id': make_uuid(),
            'workflow_state_id': workflow_state['id'],
            'workflow_metric_id': workflow_metric['id'],
            'rule_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._test_action('create', 'workflow_rule',
                                        model_class=ckanext_model.WorkflowRule,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_missing_params(self):
        result, obj = self._test_action('create', 'workflow_rule',
                                        exception_class=tk.ValidationError)
        assert_error(result, 'workflow_state_id', 'Missing parameter')
        assert_error(result, 'workflow_metric_id', 'Missing parameter')
        assert_error(result, 'rule_json', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self._test_action('create', 'workflow_rule',
                                        exception_class=tk.ValidationError,
                                        workflow_state_id='',
                                        workflow_metric_id='',
                                        rule_json='')
        assert_error(result, 'workflow_state_id', 'Missing value')
        assert_error(result, 'workflow_metric_id', 'Missing value')
        assert_error(result, 'rule_json', 'Missing value')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._test_action('create', 'workflow_rule',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        workflow_rule = ckanext_factories.WorkflowRule()
        result, obj = self._test_action('create', 'workflow_rule',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=workflow_rule['id'])
        assert_error(result, 'id', 'Already exists: Workflow Rule')

    def test_create_invalid_bad_references(self):
        result, obj = self._test_action('create', 'workflow_rule',
                                        exception_class=tk.ValidationError,
                                        workflow_state_id='foo',
                                        workflow_metric_id='bar')
        assert_error(result, 'workflow_state_id', 'Not found: Workflow State')
        assert_error(result, 'workflow_metric_id', 'Not found: Workflow Metric')

    def test_create_invalid_deleted_references(self):
        workflow_state = ckanext_factories.WorkflowState()
        workflow_metric = ckanext_factories.WorkflowMetric()
        call_action('workflow_state_delete', id=workflow_state['id'])
        call_action('workflow_metric_delete', id=workflow_metric['id'])
        result, obj = self._test_action('create', 'workflow_rule',
                                        exception_class=tk.ValidationError,
                                        workflow_state_id=workflow_state['id'],
                                        workflow_metric_id=workflow_metric['id'])
        assert_error(result, 'workflow_state_id', 'Not found: Workflow State')
        assert_error(result, 'workflow_metric_id', 'Not found: Workflow Metric')

    def test_create_invalid_duplicate(self):
        workflow_rule = ckanext_factories.WorkflowRule()
        result, obj = self._test_action('create', 'workflow_rule',
                                        exception_class=tk.ValidationError,
                                        workflow_state_id=workflow_rule['workflow_state_id'],
                                        workflow_metric_id=workflow_rule['workflow_metric_id'])
        assert_error(result, '__after', 'Unique constraint violation')

    def test_create_invalid_not_json(self):
        result, obj = self._test_action('create', 'workflow_rule',
                                        exception_class=tk.ValidationError,
                                        rule_json='not json')
        assert_error(result, 'rule_json', 'JSON decode error')

    def test_update_valid(self):
        workflow_rule = ckanext_factories.WorkflowRule()
        input_dict = {
            'id': workflow_rule['id'],
            'rule_json': '{ "newtestkey": "newtestvalue" }',
        }
        result, obj = self._test_action('update', 'workflow_rule',
                                        model_class=ckanext_model.WorkflowRule, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_invalid_cannot_change_association(self):
        workflow_rule = ckanext_factories.WorkflowRule()
        result, obj = self._test_action('update', 'workflow_rule',
                                        exception_class=tk.ValidationError,
                                        id=workflow_rule['id'],
                                        workflow_state_id=ckanext_factories.WorkflowState(),
                                        workflow_metric_id=ckanext_factories.WorkflowMetric())
        assert_error(result, 'workflow_state_id', 'The input field workflow_state_id was not expected.')
        assert_error(result, 'workflow_metric_id', 'The input field workflow_metric_id was not expected.')

    def test_update_invalid_missing_params(self):
        workflow_rule = ckanext_factories.WorkflowRule()
        result, obj = self._test_action('update', 'workflow_rule',
                                        exception_class=tk.ValidationError,
                                        id=workflow_rule['id'])
        assert_error(result, 'rule_json', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        workflow_rule = ckanext_factories.WorkflowRule()
        result, obj = self._test_action('update', 'workflow_rule',
                                        exception_class=tk.ValidationError,
                                        id=workflow_rule['id'],
                                        rule_json='')
        assert_error(result, 'rule_json', 'Missing value')

    def test_update_invalid_not_json(self):
        workflow_rule = ckanext_factories.WorkflowRule()
        result, obj = self._test_action('update', 'workflow_rule',
                                        exception_class=tk.ValidationError,
                                        id=workflow_rule['id'],
                                        rule_json='not json')
        assert_error(result, 'rule_json', 'JSON decode error')

    def test_delete_valid(self):
        workflow_rule = ckanext_factories.WorkflowRule()
        self._test_action('delete', 'workflow_rule',
                          model_class=ckanext_model.WorkflowRule,
                          id=workflow_rule['id'])
