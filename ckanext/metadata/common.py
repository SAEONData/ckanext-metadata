# encoding: utf-8

from ckan import model
from ckanext.metadata import model as model_ext

METADATA_VALIDATION_ACTIVITY_TYPE = u'metadata validation'
METADATA_WORKFLOW_ACTIVITY_TYPE = u'metadata workflow'

model_info = {
    'organization': {
        'desc': u'Organization',
        'model': model.Group,
        'rev_model': model.GroupRevision,
        'table': model.group_table,
        'rev_table': model.group_revision_table,
    },
    'infrastructure': {
        'desc': u'Infrastructure',
        'model': model.Group,
        'rev_model': model.GroupRevision,
        'table': model.group_table,
        'rev_table': model.group_revision_table,
    },
    'metadata_collection': {
        'desc': u'Metadata Collection',
        'model': model.Group,
        'rev_model': model.GroupRevision,
        'table': model.group_table,
        'rev_table': model.group_revision_table,
    },
    'metadata_record': {
        'desc': u'Metadata Record',
        'model': model.Package,
        'rev_model': model.PackageRevision,
        'table': model.package_table,
        'rev_table': model.package_revision_table,
    },
    'metadata_schema': {
        'desc': u'Metadata Schema',
        'model': model_ext.MetadataSchema,
        'rev_model': model_ext.MetadataSchemaRevision,
        'table': model_ext.metadata_schema_table,
        'rev_table': model_ext.metadata_schema_revision_table,
    },
    'metadata_standard': {
        'desc': u'Metadata Standard',
        'model': model_ext.MetadataStandard,
        'rev_model': model_ext.MetadataStandardRevision,
        'table': model_ext.metadata_standard_table,
        'rev_table': model_ext.metadata_standard_revision_table,
    },
    'workflow_state': {
        'desc': u'Workflow State',
        'model': model_ext.WorkflowState,
        'rev_model': model_ext.WorkflowStateRevision,
        'table': model_ext.workflow_state_table,
        'rev_table': model_ext.workflow_state_revision_table,
    },
    'workflow_transition': {
        'desc': u'Workflow Transition',
        'model': model_ext.WorkflowTransition,
        'rev_model': model_ext.WorkflowTransitionRevision,
        'table': model_ext.workflow_transition_table,
        'rev_table': model_ext.workflow_transition_revision_table,
    },
    'workflow_annotation': {
        'desc': u'Workflow Annotation',
        'model': model_ext.WorkflowAnnotation,
        'rev_model': model_ext.WorkflowAnnotationRevision,
        'table': model_ext.workflow_annotation_table,
        'rev_table': model_ext.workflow_annotation_revision_table,
    },
    'metadata_json_attr_map': {
        'desc': u'Metadata JSON Attribute Map',
        'model': model_ext.MetadataJSONAttrMap,
        'rev_model': model_ext.MetadataJSONAttrMapRevision,
        'table': model_ext.metadata_json_attr_map_table,
        'rev_table': model_ext.metadata_json_attr_map_revision_table,
    },
}
