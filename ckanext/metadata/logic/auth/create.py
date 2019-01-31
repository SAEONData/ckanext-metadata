# encoding: utf-8

import logging
from ckanext.metadata.logic.auth import _authorize_core_action

log = logging.getLogger(__name__)


def package_create(context, data_dict):
    """
    Override CKAN's package_create to prevent extension-specific package types from being
    created directly via this action.
    """
    return _authorize_core_action('package_create', context, data_dict, 'metadata_record')


def group_create(context, data_dict):
    """
    Override CKAN's group_create to prevent extension-specific group types from being
    created directly via this action.
    """
    return _authorize_core_action('group_create', context, data_dict, 'infrastructure', 'metadata_collection')


def metadata_standard_create(context, data_dict):
    return {'success': True}


def metadata_schema_create(context, data_dict):
    return {'success': True}


def infrastructure_create(context, data_dict):
    return {'success': True}


def metadata_collection_create(context, data_dict):
    return {'success': True}


def metadata_record_create(context, data_dict):
    return {'success': True}


def workflow_state_create(context, data_dict):
    return {'success': True}


def workflow_transition_create(context, data_dict):
    return {'success': True}


def workflow_annotation_create(context, data_dict):
    return {'success': True}


def metadata_record_workflow_annotation_create(context, data_dict):
    return {'success': True}


def metadata_standard_index_create(context, data_dict):
    return {'success': True}


def metadata_json_attr_map_create(context, data_dict):
    return {'success': True}
