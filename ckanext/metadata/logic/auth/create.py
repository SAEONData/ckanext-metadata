# encoding: utf-8

import logging

import ckan.plugins.toolkit as tk
from ckan.common import _

log = logging.getLogger(__name__)


# # TODO: chained_auth_function is only in the latest dev CKAN
# @tk.chained_auth_function
# def package_create(next_auth, context, data_dict):
#     """
#     Override CKAN's package_create to prevent extension-specific package types from being created
#     directly via this API.
#     """
#     for package_type in ['metadata_record']:
#         action_func = package_type + '_create'
#         if data_dict.get('type') == package_type and context.get('invoked_api') != action_func:
#             return {
#                 'success': False,
#                 'msg': _("%s of type '%s' may only be created using the '%s' action function") %
#                        ('Package', package_type, action_func)
#             }
#
#     return next_auth(context, data_dict)
#
#
# # TODO: chained_auth_function is only in the latest dev CKAN
# @tk.chained_auth_function
# def group_create(next_auth, context, data_dict):
#     """
#     Override CKAN's group_create to prevent extension-specific group types from being created
#     directly via this API.
#     """
#     for group_type in ['infrastructure', 'metadata_collection']:
#         action_func = group_type + '_create'
#         if data_dict.get('type') == group_type and context.get('invoked_api') != action_func:
#             return {
#                 'success': False,
#                 'msg': _("%s of type '%s' may only be created using the '%s' action function") %
#                        ('Group', group_type, action_func)
#             }
#
#     return next_auth(context, data_dict)


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
