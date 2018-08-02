# encoding: utf-8

import ckan.model as ckan_model
import ckanext.metadata.model as ckanext_model

METADATA_VALIDATION_ACTIVITY_TYPE = u'metadata validation'
METADATA_WORKFLOW_ACTIVITY_TYPE = u'metadata workflow'

model_map = {
    'organization': {'class': ckan_model.Group, 'desc': u'Organization'},
    'infrastructure': {'class': ckan_model.Group, 'desc': u'Infrastructure'},
    'metadata_collection': {'class': ckan_model.Group, 'desc': u'Metadata Collection'},
    'metadata_record': {'class': ckan_model.Package, 'desc': u'Metadata Record'},
    'metadata_model': {'class': ckanext_model.MetadataModel, 'desc': u'Metadata Model'},
    'metadata_schema': {'class': ckanext_model.MetadataSchema, 'desc': u'Metadata Schema'},
    'workflow_state': {'class': ckanext_model.WorkflowState, 'desc': u'Workflow State'},
    'workflow_transition': {'class': ckanext_model.WorkflowTransition, 'desc': u'Workflow Transition'},
    'workflow_annotation': {'class': ckanext_model.WorkflowAnnotation, 'desc': u'Workflow Annotation'},
}
