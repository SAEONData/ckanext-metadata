# encoding: utf-8

import logging
from ckanext.metadata.logic.auth import check_privs, _authorize_package_action, _authorize_group_action

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


# Admin functions

def metadata_standard_update(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def metadata_schema_update(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def infrastructure_update(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def workflow_state_update(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def workflow_transition_update(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def workflow_annotation_update(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def metadata_json_attr_map_update(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


def metadata_record_workflow_state_override(context, data_dict):
    return {'success': check_privs(context, require_admin=True)}


# Curation functions

def metadata_collection_update(context, data_dict):
    if 'id' in (data_dict or {}):
        model = context['model']
        session = context['session']
        metadata_collection_id = model.Group.get(data_dict['id']).id
        organization_id = session.query(model.GroupExtra.value).filter_by(group_id=metadata_collection_id, key='organization_id').scalar()
    else:
        organization_id = None
    return {'success': check_privs(context, require_curator=True, require_organization=organization_id)}


def metadata_record_workflow_state_transition(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_curator=True, require_organization=organization_id)}


def metadata_record_workflow_state_revert(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_curator=True, require_organization=organization_id)}


def metadata_record_index_update(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_curator=True, require_organization=organization_id)}


def metadata_collection_validate(context, data_dict):
    if 'id' in (data_dict or {}):
        model = context['model']
        session = context['session']
        metadata_collection_id = model.Group.get(data_dict['id']).id
        organization_id = session.query(model.GroupExtra.value).filter_by(group_id=metadata_collection_id, key='organization_id').scalar()
    else:
        organization_id = None
    return {'success': check_privs(context, require_curator=True, require_organization=organization_id)}


def metadata_collection_workflow_state_transition(context, data_dict):
    if 'id' in (data_dict or {}):
        model = context['model']
        session = context['session']
        metadata_collection_id = model.Group.get(data_dict['id']).id
        organization_id = session.query(model.GroupExtra.value).filter_by(group_id=metadata_collection_id, key='organization_id').scalar()
    else:
        organization_id = None
    return {'success': check_privs(context, require_curator=True, require_organization=organization_id)}


def metadata_record_assign_doi(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_curator=True, require_organization=organization_id)}


# Contributor functions

def metadata_record_update(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_contributor=True, require_organization=organization_id)}


def metadata_record_workflow_annotation_update(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_contributor=True, require_organization=organization_id)}


def metadata_record_validate(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_contributor=True, require_organization=organization_id)}


def metadata_record_invalidate(context, data_dict):
    organization_id = context['model'].Package.get(data_dict['id']).owner_org if 'id' in (data_dict or {}) else None
    return {'success': check_privs(context, require_contributor=True, require_organization=organization_id)}
