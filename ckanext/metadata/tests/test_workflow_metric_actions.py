# encoding: utf-8

from ckan.plugins import toolkit as tk

from ckanext.metadata import model as ckanext_model
from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_object_matches_dict,
    assert_error,
    factories as ckanext_factories,
)


class TestWorkflowMetricActions(ActionTestBase):

    def test_create_valid(self):
        input_dict = {
            'name': 'test-workflow-metric',
            'title': 'Test Workflow Metric',
            'description': 'This is a test workflow metric',
            'evaluator_uri': 'http://example.net/',
        }
        result, obj = self._test_action('create', 'workflow_metric',
                                        model_class=ckanext_model.WorkflowMetric, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        input_dict = {
            'id': make_uuid(),
            'name': 'test-workflow-metric',
            'evaluator_uri': 'http://example.net/',
        }
        result, obj = self._test_action('create', 'workflow_metric',
                                        model_class=ckanext_model.WorkflowMetric,
                                        sysadmin=True, check_auth=True, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        workflow_metric = ckanext_factories.WorkflowMetric()
        result, obj = self._test_action('create', 'workflow_metric',
                                        exception_class=tk.ValidationError,
                                        name=workflow_metric['name'])
        assert_error(result, 'name', 'Duplicate name: Workflow Metric')

    def test_create_invalid_missing_params(self):
        result, obj = self._test_action('create', 'workflow_metric',
                                        exception_class=tk.ValidationError)
        assert_error(result, 'name', 'Missing parameter')
        assert_error(result, 'evaluator_uri', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self._test_action('create', 'workflow_metric',
                                        exception_class=tk.ValidationError,
                                        name='',
                                        evaluator_uri='')
        assert_error(result, 'name', 'Missing value')
        assert_error(result, 'evaluator_uri', 'Missing value')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._test_action('create', 'workflow_metric',
                                        exception_class=tk.ValidationError, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        workflow_metric = ckanext_factories.WorkflowMetric()
        result, obj = self._test_action('create', 'workflow_metric',
                                        exception_class=tk.ValidationError, sysadmin=True, check_auth=True,
                                        id=workflow_metric['id'])
        assert_error(result, 'id', 'Already exists: Workflow Metric')

    def test_update_valid(self):
        workflow_metric = ckanext_factories.WorkflowMetric()
        input_dict = {
            'id': workflow_metric['id'],
            'name': 'updated-test-workflow-metric',
            'title': 'Updated Test Workflow Metric',
            'description': 'Updated test workflow metric description',
            'evaluator_uri': 'http://updated.example.net/',
        }
        result, obj = self._test_action('update', 'workflow_metric',
                                        model_class=ckanext_model.WorkflowMetric, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_partial(self):
        workflow_metric = ckanext_factories.WorkflowMetric()
        input_dict = {
            'id': workflow_metric['id'],
            'name': 'updated-test-workflow-metric',
            'evaluator_uri': 'http://updated.example.net/',
        }
        result, obj = self._test_action('update', 'workflow_metric',
                                        model_class=ckanext_model.WorkflowMetric, **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.title == workflow_metric['title']
        assert obj.description == workflow_metric['description']

    def test_update_invalid_duplicate_name(self):
        workflow_metric1 = ckanext_factories.WorkflowMetric()
        workflow_metric2 = ckanext_factories.WorkflowMetric()
        input_dict = {
            'id': workflow_metric1['id'],
            'name': workflow_metric2['name'],
        }
        result, obj = self._test_action('update', 'workflow_metric',
                                        exception_class=tk.ValidationError, **input_dict)
        assert_error(result, 'name', 'Duplicate name: Workflow Metric')

    def test_update_invalid_missing_params(self):
        workflow_metric = ckanext_factories.WorkflowMetric()
        result, obj = self._test_action('update', 'workflow_metric',
                                        exception_class=tk.ValidationError,
                                        id=workflow_metric['id'])
        assert_error(result, 'evaluator_uri', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        workflow_metric = ckanext_factories.WorkflowMetric()
        result, obj = self._test_action('update', 'workflow_metric',
                                        exception_class=tk.ValidationError,
                                        id=workflow_metric['id'],
                                        evaluator_uri='')
        assert_error(result, 'evaluator_uri', 'Missing value')

    def test_delete_valid(self):
        workflow_metric = ckanext_factories.WorkflowMetric()
        self._test_action('delete', 'workflow_metric',
                          model_class=ckanext_model.WorkflowMetric,
                          id=workflow_metric['id'])

    def test_delete_with_rule_references(self):
        workflow_metric = ckanext_factories.WorkflowMetric()
        workflow_rule = ckanext_factories.WorkflowRule(workflow_metric_id=workflow_metric['id'])
        self._test_action('delete', 'workflow_metric',
                          model_class=ckanext_model.WorkflowMetric,
                          id=workflow_metric['id'])
        assert ckanext_model.WorkflowRule.get(workflow_rule['id']).state == 'deleted'
