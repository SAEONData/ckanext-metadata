# encoding: utf-8

import json

from ckan.common import _, config
from ckan.logic import auth
from ckan.lib.redis import connect_to_redis


def check_privs(
        context,
        require_admin=False,
        require_curator=False,
        require_harvester=False,
        require_contributor=False,
        require_organization=None,
):
    """
    Check whether the user has the specified privileges.

    This is done by looking up the info directly in Redis, which gets written by
    ckanext/accesscontrol/logic/openidconnect.py (see functions _extract_token_data
    and _save_token_data for details).

    Note: this is not the usual CKAN way of doing things; it effectively makes this extension
    dependent on ckanext-accesscontrol. At this point, however, it's the simplest means of
    implementing role based access control.

    Roles are cumulative, i.e. a given role can do everything that any lower role can do.
    admin > curator > harvester > contributor > member

    :param require_admin: the user must have the administrator role in the admin organization
    :param require_curator: the user must have the curator role either in the admin organization or the specified require_organization
    :param require_harvester: the user must have the harvester role in the specified require_organization
    :param require_contributor: the user must have the contributor role in the specified require_organization
    :param require_organization: the organization (id or name) associated with the resource being requested or updated
    :return: bool
    """
    admin_org = config.get('ckan.metadata.admin_org')
    admin_role = config.get('ckan.metadata.admin_role')
    curator_role = config.get('ckan.metadata.curator_role')
    harvester_role = config.get('ckan.metadata.harvester_role')
    contributor_role = config.get('ckan.metadata.contributor_role')

    model = context['model']
    user = context['user']
    user_id = model.User.by_name(user.decode('utf8')).id

    redis = connect_to_redis()
    key = 'oidc_token_data:' + user_id
    token_json = redis.get(key)
    if not token_json:
        return False
    token_data = json.loads(token_json)

    if token_data['superuser']:
        return True

    is_admin = False
    is_curator = False
    is_harvester = False
    is_contributor = False
    is_member = False

    if require_organization:
        require_organization = model.Group.get(require_organization).name

    for privilege in token_data['privileges']:
        if privilege['institution'] == admin_org and privilege['role'] == admin_role:
            is_admin = True
        if privilege['institution'] in (admin_org, require_organization) and privilege['role'] == curator_role:
            is_curator = True
        if privilege['institution'] == require_organization and privilege['role'] == harvester_role:
            is_harvester = True
        if privilege['institution'] == require_organization and privilege['role'] == contributor_role:
            is_contributor = True
        if privilege['institution'] == require_organization:
            is_member = True

    if require_admin:
        return is_admin
    if require_curator:
        return is_admin or is_curator
    if require_harvester:
        return is_admin or is_curator or is_harvester
    if require_contributor:
        return is_admin or is_curator or is_harvester or is_contributor
    if require_organization:
        return is_admin or is_curator or is_harvester or is_contributor or is_member

    return True


def _authorize_package_action(method, context, data_dict):
    """
    Authorize access to core CKAN package actions, to ensure that these actions are not used
    directly for modifying metadata records.

    :param method: 'create' | 'update' | 'delete'
    :param context: should include 'invoked_action' to indicate the (correct) extension action
        that was invoked by the user, which in turn called the core package action
    :return: auth dict{'success': .., 'msg': ..}
    """
    package_type = context['package'].type if 'package' in context else data_dict.get('type')
    if not package_type:
        package = context['model'].Package.get(data_dict.get('id'))
        package_type = package.type if package else None

    if package_type == 'metadata_record' and context.get('invoked_action') != package_type + '_' + method:
        return {
            'success': False,
            'msg': _("This action may not be used for metadata records.")
        }

    auth_module = getattr(auth, method)
    auth_function = getattr(auth_module, 'package_' + method)
    return auth_function(context, data_dict)


def _authorize_group_action(method, context, data_dict):
    """
    Authorize access to core CKAN group actions, to ensure that these actions are not used
    directly for modifying metadata collections or infrastructures.

    :param method: 'create' | 'update' | 'delete'
    :param context: should include 'invoked_action' to indicate the (correct) extension action
        that was invoked by the user, which in turn called the core group action
    :return: auth dict{'success': .., 'msg': ..}
    """
    group_type = context['group'].type if 'group' in context else data_dict.get('type')
    if not group_type:
        group = context['model'].Group.get(data_dict.get('id'))
        group_type = group.type if group else None

    if group_type in ('metadata_collection', 'infrastructure') and context.get('invoked_action') != group_type + '_' + method:
        return {
            'success': False,
            'msg': _("This action may not be used for %s type objects.") % group_type
        }

    auth_module = getattr(auth, method)
    auth_function = getattr(auth_module, 'group_' + method)
    return auth_function(context, data_dict)


def _authorize_member_action(method, context, data_dict):
    """
    Authorize access to core CKAN member actions, to ensure that these actions are not used
    directly for altering a metadata record's membership of metadata collections or infrastructures.

    :param method: 'create' | 'delete'
    :return: auth dict{'success': .., 'msg': ..}
    """
    model = context['model']
    if data_dict['object_type'] == 'package':
        package = model.Package.get(data_dict['object'])
        group = model.Group.get(data_dict['id'])
        if package.type == 'metadata_record' and group.type in ('infrastructure', 'metadata_collection'):
            return {
                'success': False,
                'msg': _("This action may not be used to alter a metadata record's membership of metadata collections or infrastructures.")
            }
    elif data_dict['object_type'] == 'group':
        member_grp = model.Group.get(data_dict['object'])
        container_grp = model.Group.get(data_dict['id'])
        if member_grp.type == 'metadata_collection' and container_grp.type in ('infrastructure',):
            return {
                'success': False,
                'msg': _("This action may not be used to alter a metadata collection's membership of infrastructures.")
            }

    auth_module = getattr(auth, method)
    auth_function = getattr(auth_module, 'member_' + method)
    return auth_function(context, data_dict)
