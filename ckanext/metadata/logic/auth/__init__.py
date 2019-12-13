# encoding: utf-8

from ckan.common import _
from ckan.logic import auth


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
