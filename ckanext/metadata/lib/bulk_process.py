# encoding: utf-8

import logging

import ckan.plugins.toolkit as tk

log = logging.getLogger(__name__)


def bulk_action(action, context, data_dicts, async):
    """
    Carry out multiple invocations of an action, optionally asynchronously.

    :param action: name of the action function
    :param context: context to be passed to each action call (each gets its own copy of the context)
    :param data_dicts: list of dicts to be passed to each action call (as the data_dict)
    :param async: True to make the action calls asynchronously
    :returns: { total_count, error_count }
    :rtype: dict
    """
    error_count = 0
    for data_dict in data_dicts:
        if async:
            async_context = context.copy()
            del async_context['session'], async_context['model']
            tk.enqueue_job(_call_action, [action, async_context, data_dict])
        else:
            if not _call_action(action, context.copy(), data_dict):
                error_count += 1

    return {
        'total_count': len(data_dicts),
        'error_count': error_count,
    }


def _call_action(action, context, data_dict):
    """
    :returns: success/failure
    :rtype: bool
    """
    try:
        tk.get_action(action)(context, data_dict)
        return True
    except:
        return False
