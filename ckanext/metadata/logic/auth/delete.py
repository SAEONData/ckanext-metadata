# encoding: utf-8

import logging
from ckanext.metadata.logic.auth import _authorize_core_action

log = logging.getLogger(__name__)


def package_delete(context, data_dict):
    """
    Override CKAN's package_delete to prevent extension-specific package types from being
    deleted directly via this action.
    """
    return _authorize_core_action('package_delete', context, data_dict, 'metadata_record')


def group_delete(context, data_dict):
    """
    Override CKAN's group_delete to prevent extension-specific group types from being
    deleted directly via this action.
    """
    return _authorize_core_action('group_delete', context, data_dict, 'infrastructure', 'metadata_collection')


def metadata_standard_delete(context, data_dict):
    return {'success': True}


def metadata_schema_delete(context, data_dict):
    return {'success': True}


def infrastructure_delete(context, data_dict):
    return {'success': True}


def metadata_collection_delete(context, data_dict):
    return {'success': True}


def metadata_record_delete(context, data_dict):
    return {'success': True}


def workflow_state_delete(context, data_dict):
    return {'success': True}


def workflow_transition_delete(context, data_dict):
    return {'success': True}


def workflow_annotation_delete(context, data_dict):
    return {'success': True}


def metadata_record_workflow_annotation_delete(context, data_dict):
    return {'success': True}


def organization_delete(context, data_dict):
    return {'success': True}


def metadata_standard_index_delete(context, data_dict):
    return {'success': True}


def metadata_json_attr_map_delete(context, data_dict):
    return {'success': True}
