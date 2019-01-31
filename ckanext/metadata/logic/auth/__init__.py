# encoding: utf-8

from ckan.common import _
from ckan.logic import auth


def _authorize_core_action(action_name, context, data_dict, *ext_object_types):
    """
    Authorize access to a core CKAN action, to ensure that core actions are not used
    directly for retrieving or modifying extension object types.

    :param action_name: name of the core CKAN action, e.g. 'package_create', 'group_show', etc
    :param context: should include 'invoked_action' to indicate the extension action that was
        invoked by the user, which in turn called the given core action
    :param ext_object_types: types of objects (e.g. 'metadata_record', 'metadata_collection', etc)
        that must be retrieved/modified via extension actions
    :return: auth dict{'success': .., 'msg': ..}
    """
    method = action_name.rpartition('_')[2]  # gets 'create', 'show', etc out of the action name
    object_type = data_dict.get('type')
    if object_type in ext_object_types:
        ext_action_name = object_type + '_' + method
        if context.get('invoked_action') != ext_action_name:
            return {
                'success': False,
                'msg': _("The '%s' action function must be used for this type of object.") % ext_action_name
            }

    auth_module = getattr(auth, 'get' if method in ('show', 'list') else method)
    auth_function = getattr(auth_module, action_name)
    return auth_function(context, data_dict)
