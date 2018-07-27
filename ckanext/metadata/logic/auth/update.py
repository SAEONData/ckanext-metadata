# encoding: utf-8

import logging
import ckan.plugins.toolkit as tk
from ckanext.metadata.logic.auth import _action_auth

log = logging.getLogger(__name__)


# # TODO: chained_auth_function is only in the latest dev CKAN
#
# @tk.chained_auth_function
# def package_update(next_auth, context, data_dict):
#     """
#     Override CKAN's package_update to prevent extension-specific package types from being updated
#     directly via this API.
#     """
#     result = _action_auth(context, data_dict, ('metadata_record',), '_update')
#     return result if result else next_auth(context, data_dict)
#
#
# @tk.chained_auth_function
# def group_update(next_auth, context, data_dict):
#     """
#     Override CKAN's group_update to prevent extension-specific group types from being updated
#     directly via this API.
#     """
#     result = _action_auth(context, data_dict, ('infrastructure', 'metadata_collection',), '_update')
#     return result if result else next_auth(context, data_dict)


def metadata_schema_update(context, data_dict):
    return {'success': True}


def metadata_model_update(context, data_dict):
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


def workflow_state_update(context, data_dict):
    return {'success': True}


def workflow_transition_update(context, data_dict):
    return {'success': True}


def workflow_annotation_update(context, data_dict):
    return {'success': True}
