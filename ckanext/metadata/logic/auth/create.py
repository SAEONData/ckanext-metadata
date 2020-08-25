# encoding: utf-8

import logging

from ckanext.metadata.logic.auth import check_privs, _authorize_package_action, _authorize_group_action, _authorize_member_action

log = logging.getLogger(__name__)


def package_create(context, data_dict):
    """
    Override CKAN's package_create to prevent extension-specific package types from being
    created directly via this action.
    """
    return _authorize_package_action('create', context, data_dict)


def group_create(context, data_dict):
    """
    Override CKAN's group_create to prevent extension-specific group types from being
    created directly via this action.
    """
    return _authorize_group_action('create', context, data_dict)


def member_create(context, data_dict):
    """
    Override CKAN's member_create to prevent it being used to assign a metadata record to
    an extension group type.
    """
    return _authorize_member_action('create', context, data_dict)


# Admin functions

def metadata_standard_create(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def metadata_schema_create(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def infrastructure_create(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def organization_create(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def workflow_state_create(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def workflow_transition_create(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def workflow_annotation_create(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def metadata_standard_index_create(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def metadata_json_attr_map_create(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def infrastructure_member_create(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


# Curation functions

def metadata_collection_create(context, data_dict):
    return {'success': check_privs(context, require_curator=True, require_organization=(data_dict or {}).get('organization_id'))}


# Contributor functions

def metadata_record_create(context, data_dict):
    return {'success': check_privs(context, require_contributor=True, require_organization=(data_dict or {}).get('owner_org'))}


def metadata_record_workflow_annotation_create(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_contributor=True, require_organization=organization_id)}
