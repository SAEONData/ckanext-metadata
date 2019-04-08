# encoding: utf-8

import ckan.plugins.toolkit as tk
from ckan import model

_permissions_map = {
    'metadata_record': {
        'read': [
            'metadata_record_show',
            'metadata_record_list',
            'metadata_record_validation_schema_list',
            'metadata_record_workflow_annotation_show',
            'metadata_record_workflow_annotation_list',
            'metadata_record_index_show',
        ],
        'write': [
            'metadata_record_create',
            'metadata_record_update',
            'metadata_record_delete',
        ],
        'manage_workflow': [
            'metadata_record_validate',
            'metadata_record_invalidate',
            'metadata_record_workflow_annotation_create',
            'metadata_record_workflow_annotation_update',
            'metadata_record_workflow_annotation_delete',
            'metadata_record_workflow_state_transition',
            'metadata_record_workflow_state_revert',
            'metadata_record_index_update',
        ],
    },

    'metadata_collection': {
        'read': [
            'metadata_collection_show',
            'metadata_collection_list',
        ],
        'write': [
            'metadata_collection_create',
            'metadata_collection_update',
            'metadata_collection_delete',
        ],
    },

    'organization': {
        'read': [
            'organization_show',
            'organization_list',
        ],
        'write': [
            'organization_create',
            'organization_update',
            'organization_delete',
        ],
    },

    'infrastructure': {
        'read': [
            'infrastructure_show',
            'infrastructure_list',
        ],
        'write': [
            'infrastructure_create',
            'infrastructure_update',
            'infrastructure_delete',
        ],
    },

    'metadata_standard': {
        'read': [
            'metadata_standard_show',
            'metadata_standard_list',
            'metadata_standard_index_show',
        ],
        'write': [
            'metadata_standard_create',
            'metadata_standard_update',
            'metadata_standard_delete',
        ],
        'manage_search_index': [
            'metadata_standard_index_create',
            'metadata_standard_index_delete',
        ]
    },

    'metadata_schema': {
        'read': [
            'metadata_schema_show',
            'metadata_schema_list',
        ],
        'write': [
            'metadata_schema_create',
            'metadata_schema_update',
            'metadata_schema_delete',
        ],
    },

    'workflow_config': {
        'read': [
            'workflow_state_show',
            'workflow_state_list',
            'workflow_transition_show',
            'workflow_transition_list',
            'workflow_annotation_show',
            'workflow_annotation_list',
        ],
        'write': [
            'workflow_state_create',
            'workflow_state_update',
            'workflow_state_delete',
            'workflow_transition_create',
            'workflow_transition_delete',
            'workflow_annotation_create',
            'workflow_annotation_update',
            'workflow_annotation_delete',
        ],
    },
}


def init_permissions():
    context = {
        'model': model,
        'session': model.Session,
        'user': tk.c.user,
        'defer_commit': True,
    }

    for content_type, operations_map in _permissions_map.iteritems():
        for operation, actions in operations_map.iteritems():
            data_dict = {
                'content_type': content_type,
                'operation': operation,
                'actions': actions,
            }
            tk.get_action('permission_define')(context, data_dict)

    model.repo.commit()


def reset_permissions():
    context = {
        'model': model,
        'session': model.Session,
        'user': tk.c.user,
    }
    tk.get_action('permission_delete_all')(context, {})
