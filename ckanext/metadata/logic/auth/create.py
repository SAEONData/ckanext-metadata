# encoding: utf-8

import logging
import ckan.plugins.toolkit as tk
from ckanext.metadata.logic.auth import _action_auth

log = logging.getLogger(__name__)


# # TODO: chained_auth_function is only in the latest dev CKAN
#
# @tk.chained_auth_function
# def package_create(next_auth, context, data_dict):
#     """
#     Override CKAN's package_create to prevent extension-specific package types from being created
#     directly via this API.
#     """
#     result = _action_auth(context, data_dict, ('metadata_record',), '_create')
#     return result if result else next_auth(context, data_dict)
#
#
# @tk.chained_auth_function
# def group_create(next_auth, context, data_dict):
#     """
#     Override CKAN's group_create to prevent extension-specific group types from being created
#     directly via this API.
#     """
#     result = _action_auth(context, data_dict, ('infrastructure', 'metadata_collection',), '_create')
#     return result if result else next_auth(context, data_dict)


def metadata_schema_create(context, data_dict):
    return {'success': True}


def metadata_model_create(context, data_dict):
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
