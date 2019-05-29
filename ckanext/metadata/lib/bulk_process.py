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
    """
    for data_dict in data_dicts:
        if async:
            async_context = context.copy()
            del async_context['session'], async_context['model']
            tk.enqueue_job(_call_action, [action, async_context, data_dict])
        else:
            _call_action(action, context.copy(), data_dict)


def _call_action(action, context, data_dict):
    tk.get_action(action)(context, data_dict)
