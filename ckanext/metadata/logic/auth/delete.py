# encoding: utf-8

import logging
from ckanext.metadata.logic.auth import check_privs, _authorize_package_action, _authorize_group_action, _authorize_member_action

log = logging.getLogger(__name__)


def package_delete(context, data_dict):
    """
    Override CKAN's package_delete to prevent extension-specific package types from being
    deleted directly via this action.
    """
    return _authorize_package_action('delete', context, data_dict)


def group_delete(context, data_dict):
    """
    Override CKAN's group_delete to prevent extension-specific group types from being
    deleted directly via this action.
    """
    return _authorize_group_action('delete', context, data_dict)


def member_delete(context, data_dict):
    """
    Override CKAN's member_delete to prevent it being used to remove a metadata record from
    an extension group type.
    """
    return _authorize_member_action('delete', context, data_dict)


# Admin functions

def metadata_standard_delete(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def metadata_schema_delete(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def infrastructure_delete(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def workflow_state_delete(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def workflow_transition_delete(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def workflow_annotation_delete(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def organization_delete(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def metadata_standard_index_delete(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def metadata_json_attr_map_delete(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def infrastructure_member_delete(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


# Curation functions

def metadata_collection_delete(context, data_dict):
    if 'id' in (data_dict or {}):
        model = context['model']
        session = context['session']
        metadata_collection_id = model.Group.get(data_dict['id']).id
        organization_id = session.query(model.GroupExtra.value).filter_by(group_id=metadata_collection_id, key='organization_id').scalar()
    else:
        organization_id = None
    return {'success': check_privs(context, require_curator=True, require_organization=organization_id)}


def metadata_record_workflow_annotation_delete(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_curator=True, require_organization=organization_id)}


def metadata_record_delete(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_curator=True, require_organization=organization_id)}
