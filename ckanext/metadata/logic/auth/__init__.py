# encoding: utf-8

from ckan.common import _


def _action_auth(context, data_dict, object_types, action_suffix):
    """
    Helper function to prevent core CKAN APIs being used for retrieving or modifying
    extension-specific object types.
    :param object_types: iterable of extension-specific group/package types
    :param action_suffix: '_show', '_create', etc
    :return: None if the operation is allowed, else an auth error dict
    """
    for object_type in object_types:
        action_func = object_type + action_suffix
        if data_dict.get('type') == object_type and context.get('invoked_api') != action_func:
            return {
                'success': False,
                'msg': _("The '%s' action function must be used for this type of object.") % action_func
            }
