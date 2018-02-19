# encoding: utf-8

import logging

import ckan.plugins.toolkit as tk
from ckan.common import _

log = logging.getLogger(__name__)


# # TODO: chained_auth_function is only in the latest dev CKAN
# @tk.chained_auth_function
# def package_show(next_auth, context, data_dict):
#     """
#     Override CKAN's package_show to prevent extension-specific package types from being retrieved
#     directly via this API.
#     """
#     for package_type in ['metadata_record']:
#         action_func = package_type + '_show'
#         if data_dict.get('type') == package_type and context.get('invoked_api') != action_func:
#             return {
#                 'success': False,
#                 'msg': _("%s of type '%s' may only be retrieved using the '%s' action function") %
#                        ('Package', package_type, action_func)
#             }
#
#     return next_auth(context, data_dict)
#
#
# # TODO: chained_auth_function is only in the latest dev CKAN
# @tk.chained_auth_function
# def group_show(next_auth, context, data_dict):
#     """
#     Override CKAN's group_show to prevent extension-specific group types from being retrieved
#     directly via this API.
#     """
#     for group_type in ['infrastructure', 'metadata_collection']:
#         action_func = group_type + '_show'
#         if data_dict.get('type') == group_type and context.get('invoked_api') != action_func:
#             return {
#                 'success': False,
#                 'msg': _("%s of type '%s' may only be retrieved using the '%s' action function") %
#                        ('Group', group_type, action_func)
#             }
#
#     return next_auth(context, data_dict)


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
