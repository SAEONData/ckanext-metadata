# encoding: utf-8

from ckan.tests.helpers import call_action

from ckanext.metadata.tests import (
    ActionTestBase,
    make_uuid,
    assert_object_matches_dict,
    assert_error,
    factories as ckanext_factories,
)


class TestWorkflowAnnotationActions(ActionTestBase):

    def test_create_valid(self):
        metadata_record = ckanext_factories.MetadataRecord()
        input_dict = {
            'metadata_record_id': metadata_record['id'],
            'workflow_annotation_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._test_action('workflow_annotation_create', **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_byname(self):
        metadata_record = ckanext_factories.MetadataRecord()
        input_dict = {
            'metadata_record_id': metadata_record['name'],
            'workflow_annotation_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._test_action('workflow_annotation_create', **input_dict)
        input_dict = {
            'metadata_record_id': metadata_record['id'],
            'workflow_annotation_json': '{ "testkey": "testvalue" }',
        }
        assert_object_matches_dict(obj, input_dict)

    def test_create_valid_sysadmin_setid(self):
        metadata_record = ckanext_factories.MetadataRecord()
        input_dict = {
            'id': make_uuid(),
            'metadata_record_id': metadata_record['id'],
            'workflow_annotation_json': '{ "testkey": "testvalue" }',
        }
        result, obj = self._test_action('workflow_annotation_create', sysadmin=True, check_auth=True, **input_dict)
        assert_object_matches_dict(obj, input_dict)

    def test_create_invalid_missing_params(self):
        result, obj = self._test_action('workflow_annotation_create', should_error=True)
        assert_error(result, 'metadata_record_id', 'Missing parameter')
        assert_error(result, 'workflow_annotation_json', 'Missing parameter')

    def test_create_invalid_missing_values(self):
        result, obj = self._test_action('workflow_annotation_create', should_error=True,
                                        metadata_record_id='',
                                        workflow_annotation_json='')
        assert_error(result, 'metadata_record_id', 'Missing value')
        assert_error(result, 'workflow_annotation_json', 'Missing value')

    def test_create_invalid_nonsysadmin_setid(self):
        result, obj = self._test_action('workflow_annotation_create', should_error=True, check_auth=True,
                                        id=make_uuid())
        assert_error(result, 'id', 'The input field id was not expected.')

    def test_create_invalid_sysadmin_duplicate_id(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self._test_action('workflow_annotation_create', should_error=True, sysadmin=True, check_auth=True,
                                        id=workflow_annotation['id'])
        assert_error(result, 'id', 'Already exists: Workflow Annotation')

    def test_create_invalid_bad_references(self):
        result, obj = self._test_action('workflow_annotation_create', should_error=True,
                                        metadata_record_id='foo')
        assert_error(result, 'metadata_record_id', 'Not found: Metadata Record')

    def test_create_invalid_deleted_references(self):
        metadata_record = ckanext_factories.MetadataRecord()
        call_action('metadata_record_delete', id=metadata_record['id'])
        result, obj = self._test_action('workflow_annotation_create', should_error=True,
                                        metadata_record_id=metadata_record['id'])
        assert_error(result, 'metadata_record_id', 'Not found: Metadata Record')

    def test_create_invalid_not_json(self):
        result, obj = self._test_action('workflow_annotation_create', should_error=True,
                                        workflow_annotation_json='not json')
        assert_error(result, 'workflow_annotation_json', 'JSON decode error')

    def test_update_invalid(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        result, obj = self._test_action('workflow_annotation_update', should_error=True,
                                        id=workflow_annotation['id'])
        assert_error(result, 'message', 'A workflow annotation cannot be updated. Delete it and create a new one instead.')

    def test_delete_valid(self):
        workflow_annotation = ckanext_factories.WorkflowAnnotation()
        self._test_action('workflow_annotation_delete',
                          id=workflow_annotation['id'])
