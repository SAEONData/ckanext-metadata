# encoding: utf-8

import logging
from ckanext.metadata.logic.auth import _authorize_package_action, _authorize_group_action

log = logging.getLogger(__name__)


def package_update(context, data_dict):
    """
    Override CKAN's package_update to prevent extension-specific package types from being
    updated directly via this action.
    """
    return _authorize_package_action('update', context, data_dict)


def group_update(context, data_dict):
    """
    Override CKAN's group_update to prevent extension-specific group types from being
    updated directly via this action.
    """
    return _authorize_group_action('update', context, data_dict)


def metadata_standard_update(context, data_dict):
    return {'success': True}


def metadata_schema_update(context, data_dict):
    return {'success': True}


def infrastructure_update(context, data_dict):
    return {'success': True}


def metadata_collection_update(context, data_dict):
    return {'success': True}


def metadata_record_update(context, data_dict):
    return {'success': True}


def metadata_record_validate(context, data_dict):
    return {'success': True}


def metadata_record_invalidate(context, data_dict):
    return {'success': True}


def metadata_record_workflow_state_transition(context, data_dict):
    return {'success': True}


def metadata_record_workflow_state_override(context, data_dict):
    return {'success': True}


def metadata_record_workflow_state_revert(context, data_dict):
    return {'success': True}


def metadata_record_workflow_annotation_update(context, data_dict):
    return {'success': True}


def metadata_record_index_update(context, data_dict):
    return {'success': True}


def workflow_state_update(context, data_dict):
    return {'success': True}


def workflow_transition_update(context, data_dict):
    return {'success': True}


def workflow_annotation_update(context, data_dict):
    return {'success': True}


def metadata_json_attr_map_update(context, data_dict):
    return {'success': True}


def metadata_collection_validate(context, data_dict):
    return {'success': True}


def metadata_collection_workflow_state_transition(context, data_dict):
    return {'success': True}


def metadata_record_assign_doi(context, data_dict):
    return {'success': True}
