# encoding: utf-8

import logging
import ckan.plugins.toolkit as tk
from ckanext.metadata.logic.auth import _action_auth

log = logging.getLogger(__name__)


# # TODO: chained_auth_function is only in the latest dev CKAN
#
# @tk.chained_auth_function
# def package_show(next_auth, context, data_dict):
#     """
#     Override CKAN's package_show to prevent extension-specific package types from being retrieved
#     directly via this API.
#     """
#     result = _action_auth(context, data_dict, ('metadata_record',), '_show')
#     return result if result else next_auth(context, data_dict)
#
#
# @tk.chained_auth_function
# def package_list(next_auth, context, data_dict):
#     """
#     Override CKAN's package_list to prevent extension-specific package types from being retrieved
#     directly via this API.
#     """
#     result = _action_auth(context, data_dict, ('metadata_record',), '_list')
#     return result if result else next_auth(context, data_dict)
#
#
# @tk.chained_auth_function
# def group_show(next_auth, context, data_dict):
#     """
#     Override CKAN's group_show to prevent extension-specific group types from being retrieved
#     directly via this API.
#     """
#     result = _action_auth(context, data_dict, ('infrastructure', 'metadata_collection',), '_show')
#     return result if result else next_auth(context, data_dict)
#
#
# @tk.chained_auth_function
# def group_list(next_auth, context, data_dict):
#     """
#     Override CKAN's group_list to prevent extension-specific group types from being retrieved
#     directly via this API.
#     """
#     result = _action_auth(context, data_dict, ('infrastructure', 'metadata_collection',), '_list')
#     return result if result else next_auth(context, data_dict)


def metadata_schema_show(context, data_dict):
    return {'success': True}


def metadata_model_show(context, data_dict):
    return {'success': True}


def infrastructure_show(context, data_dict):
    return {'success': True}


def metadata_collection_show(context, data_dict):
    return {'success': True}


def metadata_record_show(context, data_dict):
    return {'success': True}


def metadata_schema_list(context, data_dict):
    return {'success': True}


def metadata_model_list(context, data_dict):
    return {'success': True}


def metadata_model_dependent_record_list(context, data_dict):
    return {'success': True}


def infrastructure_list(context, data_dict):
    return {'success': True}


def metadata_collection_list(context, data_dict):
    return {'success': True}


def metadata_record_list(context, data_dict):
    return {'success': True}


def metadata_record_validation_model_list(context, data_dict):
    return {'success': True}


def metadata_record_validation_activity_show(context, data_dict):
    return {'success': True}


def metadata_validity_check(context, data_dict):
    return {'success': True}


def metadata_record_workflow_rules_check(context, data_dict):
    return {'success': True}


def metadata_record_workflow_activity_show(context, data_dict):
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
