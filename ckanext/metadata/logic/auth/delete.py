# encoding: utf-8

import logging
import ckan.plugins.toolkit as tk
from ckanext.metadata.logic.auth import _action_auth

log = logging.getLogger(__name__)


# # TODO: chained_auth_function is only in the latest dev CKAN
#
# @tk.chained_auth_function
# def package_delete(next_auth, context, data_dict):
#     """
#     Override CKAN's package_delete to prevent extension-specific package types from being deleted
#     directly via this API.
#     """
#     result = _action_auth(context, data_dict, ('metadata_record',), '_delete')
#     return result if result else next_auth(context, data_dict)
#
#
# @tk.chained_auth_function
# def group_delete(next_auth, context, data_dict):
#     """
#     Override CKAN's group_delete to prevent extension-specific group types from being deleted
#     directly via this API.
#     """
#     result = _action_auth(context, data_dict, ('infrastructure', 'metadata_collection',), '_delete')
#     return result if result else next_auth(context, data_dict)


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


def organization_delete(context, data_dict):
    return {'success': True}
