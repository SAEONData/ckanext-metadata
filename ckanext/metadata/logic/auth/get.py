# encoding: utf-8

import logging
from ckanext.metadata.logic.auth import _authorize_core_action

log = logging.getLogger(__name__)


def package_show(context, data_dict):
    """
    Override CKAN's package_show to prevent extension-specific package types from being
    retrieved directly via this action.
    """
    return _authorize_core_action('package_show', context, data_dict, 'metadata_record')


def package_list(context, data_dict):
    """
    Override CKAN's package_list to prevent extension-specific package types from being
    retrieved directly via this action.
    """
    return _authorize_core_action('package_list', context, data_dict, 'metadata_record')


def group_show(context, data_dict):
    """
    Override CKAN's group_show to prevent extension-specific group types from being
    retrieved directly via this action.
    """
    return _authorize_core_action('group_show', context, data_dict, 'infrastructure', 'metadata_collection')


def group_list(context, data_dict):
    """
    Override CKAN's group_list to prevent extension-specific group types from being
    retrieved directly via this action.
    """
    return _authorize_core_action('group_list', context, data_dict, 'infrastructure', 'metadata_collection')


def metadata_standard_show(context, data_dict):
    return {'success': True}


def metadata_schema_show(context, data_dict):
    return {'success': True}


def infrastructure_show(context, data_dict):
    return {'success': True}


def metadata_collection_show(context, data_dict):
    return {'success': True}


def metadata_record_show(context, data_dict):
    return {'success': True}


def metadata_standard_list(context, data_dict):
    return {'success': True}


def metadata_schema_list(context, data_dict):
    return {'success': True}


def metadata_schema_dependent_record_list(context, data_dict):
    return {'success': True}


def infrastructure_list(context, data_dict):
    return {'success': True}


def metadata_collection_list(context, data_dict):
    return {'success': True}


def metadata_record_list(context, data_dict):
    return {'success': True}


def metadata_record_validation_schema_list(context, data_dict):
    return {'success': True}


def metadata_record_validation_activity_show(context, data_dict):
    return {'success': True}


def metadata_validity_check(context, data_dict):
    return {'success': True}


def metadata_record_workflow_rules_check(context, data_dict):
    return {'success': True}


def metadata_record_workflow_activity_show(context, data_dict):
    return {'success': True}


def metadata_record_workflow_annotation_show(context, data_dict):
    return {'success': True}


def metadata_record_workflow_annotation_list(context, data_dict):
    return {'success': True}


def metadata_record_workflow_augmented_show(context, data_dict):
    return {'success': True}


def workflow_state_show(context, data_dict):
    return {'success': True}


def workflow_state_list(context, data_dict):
    return {'success': True}


def workflow_transition_show(context, data_dict):
    return {'success': True}


def workflow_transition_list(context, data_dict):
    return {'success': True}


def workflow_annotation_show(context, data_dict):
    return {'success': True}


def workflow_annotation_list(context, data_dict):
    return {'success': True}


def metadata_json_attr_map_show(context, data_dict):
    return {'success': True}


def metadata_json_attr_map_list(context, data_dict):
    return {'success': True}


def metadata_json_attr_map_apply(context, data_dict):
    return {'success': True}


def metadata_record_attr_match(context, data_dict):
    return {'success': True}


def metadata_standard_index_show(context, data_dict):
    return {'success': True}


def metadata_record_index_show(context, data_dict):
    return {'success': True}
