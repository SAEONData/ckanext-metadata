# encoding: utf-8

from ckanext.metadata.tests import (
    ActionTestBase,
    assert_object_matches_dict,
    assert_error,
    factories as ckanext_factories,
)


class TestWorkflowAnnotationActions(ActionTestBase):

    def test_create_valid(self):
        input_dict = {
            'name': 'test-workflow-annotation',
            'attributes': '{ "attr1": "string", "attr2": "number", "attr3": "boolean" }',
            'is_array': False,
        }
        result, obj = self.test_action('workflow_annotation_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_duplicate_name(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self.test_action('workflow_annotation_create', should_error=True,
                                       name=workflow_annotation['name'])
        assert_error(result, 'name', 'Duplicate name: Workflow Annotation')

    def test_create_invalid_missing_params(self):
        result, obj = self.test_action('workflow_annotation_create', should_error=True)
        assert_error(result, 'name', 'Missing parameter')
        assert_error(result, 'attributes', 'Missing parameter')
        assert_error(result, 'is_array', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self.test_action('workflow_annotation_create', should_error=True,
                                       name='',
                                       attributes='')
        assert_error(result, 'name', 'Missing value')
        assert_error(result, 'attributes', 'Missing value')

    def test_create_invalid_empty_attributes(self):
        result, obj = self.test_action('workflow_annotation_create', should_error=True,
                                       attributes='{}')
        assert_error(result, 'attributes', 'A workflow annotation requires at least one attribute')

    def test_create_invalid_attributes_not_json(self):
        result, obj = self.test_action('workflow_annotation_create', should_error=True,
                                       attributes='not json')
        assert_error(result, 'attributes', 'JSON decode error')

    def test_create_invalid_attributes_not_json_dict(self):
        result, obj = self.test_action('workflow_annotation_create', should_error=True,
                                       attributes='[1,2,3]')
        assert_error(result, 'attributes', 'Expecting a JSON dictionary')

    def test_create_invalid_bad_attribute_names(self):
        result, obj = self.test_action('workflow_annotation_create', should_error=True,
                                       attributes='{" bad": "string"}')
        assert_error(result, 'attributes', 'Workflow annotation attribute name may consist only of alphanumeric characters')

    def test_create_invalid_bad_attribute_types(self):
        result, obj = self.test_action('workflow_annotation_create', should_error=True,
                                       attributes='{"foo": {}}')
        assert_error(result, 'attributes', "Workflow annotation attribute type must be one of 'string', 'number', 'boolean'")

        result, obj = self.test_action('workflow_annotation_create', should_error=True,
                                       attributes='{"foo": "bar"}')
        assert_error(result, 'attributes', "Workflow annotation attribute type must be one of 'string', 'number', 'boolean'")

    def test_update_valid(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        input_dict = {
            'id': workflow_annotation['id'],
            'name': 'updated-test-workflow-annotation',
            'attributes': '{ "attr1": "string", "attr2": "number", "attr3": "boolean" }',
            'is_array': False,
        }
        result, obj = self.test_action('workflow_annotation_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_update_valid_partial(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        input_dict = {
            'id': workflow_annotation['id'],
            'attributes': '{ "attr1": "string", "attr2": "number", "attr3": "boolean" }',
            'is_array': False,
        }
        result, obj = self.test_action('workflow_annotation_update', **input_dict)
        assert_object_matches_dict(obj, input_dict)
        assert obj.name == workflow_annotation['name']

    def test_update_invalid_duplicate_name(self):
        workflow_annotation1 = ckanext_factories.WorkflowAnnotation()
        workflow_annotation2 = ckanext_factories.WorkflowAnnotation()
        input_dict = {
            'id': workflow_annotation1['id'],
            'name': workflow_annotation2['name'],
        }
        result, obj = self.test_action('workflow_annotation_update', should_error=True, **input_dict)
        assert_error(result, 'name', 'Duplicate name: Workflow Annotation')

    def test_update_invalid_missing_params(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self.test_action('workflow_annotation_update', should_error=True,
                                       id=workflow_annotation['id'])
        assert_error(result, 'attributes', 'Missing parameter')
        assert_error(result, 'is_array', 'Missing parameter')

    def test_update_invalid_missing_values(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self.test_action('workflow_annotation_update', should_error=True,
                                       id=workflow_annotation['id'],
                                       attributes='')
        assert_error(result, 'attributes', 'Missing value')

    def test_update_invalid_empty_attributes(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self.test_action('workflow_annotation_update', should_error=True,
                                       id=workflow_annotation['id'],
                                       attributes='{}')
        assert_error(result, 'attributes', 'A workflow annotation requires at least one attribute')

    def test_update_invalid_attributes_not_json(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self.test_action('workflow_annotation_update', should_error=True,
                                       id=workflow_annotation['id'],
                                       attributes='not json')
        assert_error(result, 'attributes', 'JSON decode error')

    def test_update_invalid_attributes_not_json_dict(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self.test_action('workflow_annotation_update', should_error=True,
                                       id=workflow_annotation['id'],
                                       attributes='[1,2,3]')
        assert_error(result, 'attributes', 'Expecting a JSON dictionary')

    def test_update_invalid_bad_attribute_names(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self.test_action('workflow_annotation_update', should_error=True,
                                       id=workflow_annotation['id'],
                                       attributes='{" bad": "string"}')
        assert_error(result, 'attributes', 'Workflow annotation attribute name may consist only of alphanumeric characters')

    def test_update_invalid_bad_attribute_types(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self.test_action('workflow_annotation_update', should_error=True,
                                       id=workflow_annotation['id'],
                                       attributes='{"foo": {}}')
        assert_error(result, 'attributes', "Workflow annotation attribute type must be one of 'string', 'number', 'boolean'")

        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self.test_action('workflow_annotation_update', should_error=True,
                                       id=workflow_annotation['id'],
                                       attributes='{"foo": "bar"}')
        assert_error(result, 'attributes', "Workflow annotation attribute type must be one of 'string', 'number', 'boolean'")

    def test_delete_valid(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        self.test_action('workflow_annotation_delete',
                         id=workflow_annotation['id'])
