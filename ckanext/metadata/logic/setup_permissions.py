# encoding: utf-8

import ckan.plugins.toolkit as tk
from ckan import model

_permissions_map = {
    'metadata': {
        'view': [
            'metadata_record_list',
            'metadata_record_show',
            'metadata_collection_show',
            'organization_show',
            'infrastructure_show',
            'metadata_standard_show',
            'workflow_state_show',
        ],
        'submit': [
            'metadata_record_create',
            'metadata_standard_list',
            'metadata_standard_show',
            'infrastructure_list',
            'infrastructure_show',
        ],
        'manage': [
            'metadata_record_create',
            'metadata_record_update',
            'metadata_record_delete',
            'metadata_record_validation_schema_list',
            'metadata_record_validate',
            'metadata_record_invalidate',
            'metadata_record_workflow_annotation_show',
            'metadata_record_workflow_annotation_list',
            'metadata_record_workflow_annotation_create',
            'metadata_record_workflow_annotation_update',
            'metadata_record_workflow_annotation_delete',
            'metadata_record_workflow_state_transition',
            'metadata_record_workflow_state_revert',
            'metadata_record_index_show',
            'metadata_record_index_update',
            'metadata_record_assign_doi',
            'metadata_standard_list',
            'metadata_standard_show',
            'infrastructure_list',
            'infrastructure_show',
        ],
    },

    'collections': {
        'view': [
            'metadata_collection_list',
            'metadata_collection_show',
            'organization_show',
        ],
        'manage': [
            'metadata_collection_create',
            'metadata_collection_update',
            'metadata_collection_delete',
            'metadata_collection_validate',
            'metadata_collection_workflow_state_transition',
        ],
    },

    'organizations': {
        'view': [
            'organization_list',
            'organization_show',
        ],
        'manage': [
            'organization_create',
            'organization_update',
            'organization_delete',
        ],
    },

    'infrastructures': {
        'view': [
            'infrastructure_list',
            'infrastructure_show',
        ],
        'manage': [
            'infrastructure_create',
            'infrastructure_update',
            'infrastructure_delete',
            'infrastructure_member_create',
            'infrastructure_member_delete',
        ],
    },

    'standards': {
        'view': [
            'metadata_standard_list',
            'metadata_standard_show',
            'metadata_schema_list',
            'metadata_schema_show',
            'infrastructure_show',
            'organization_show',
            'metadata_json_attr_map_list',
            'metadata_json_attr_map_show',
        ],
        'configure': [
            'metadata_standard_create',
            'metadata_standard_update',
            'metadata_standard_delete',
            'metadata_schema_create',
            'metadata_schema_update',
            'metadata_schema_delete',
            'metadata_json_attr_map_create',
            'metadata_json_attr_map_update',
            'metadata_json_attr_map_delete',
        ],
    },

    'workflows': {
        'view': [
            'workflow_state_list',
            'workflow_state_show',
            'workflow_transition_list',
            'workflow_transition_show',
            'workflow_annotation_list',
            'workflow_annotation_show',
        ],
        'configure': [
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

    'search_catalogue': {
        'view': [
            'metadata_standard_index_show',
            'metadata_standard_show',
        ],
        'manage': [
            'metadata_standard_index_create',
            'metadata_standard_index_delete',
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
