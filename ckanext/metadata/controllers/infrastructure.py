# encoding: utf-8

import re

import ckan.plugins.toolkit as tk
from ckan.controllers.group import GroupController
from ckan.lib.render import TemplateNotFound


class InfrastructureController(GroupController):

    group_types = ['infrastructure']

    def _guess_group_type(self, expecting_name=False):
        return 'infrastructure'

    @staticmethod
    def _substitute_name(name):
        return re.sub('^group', 'infrastructure', name)

    def _action(self, action_name):
        """
        Return the corresponding 'infrastructure_' action if it exists,
        otherwise fall back to the given 'group_' action.
        """
        try:
            return tk.get_action(self._substitute_name(action_name))
        except KeyError:
            return tk.get_action(action_name)

    def _check_access(self, action_name, *args, **kw):
        """
        Check access for the corresponding 'infrastructure_' action if it exists,
        otherwise fall back to the given 'group_' action.
        """
        try:
            return tk.check_access(self._substitute_name(action_name), *args, **kw)
        except ValueError:
            return tk.check_access(action_name, *args, **kw)

    def _render_template(self, template_name, group_type):
        """
        Render the corresponding 'infrastructure_' template if it exists,
        otherwise fall back to the given 'group_' template.
        """
        try:
            return tk.render(self._substitute_name(template_name), extra_vars={'group_type': group_type})
        except TemplateNotFound:
            return tk.render(template_name, extra_vars={'group_type': group_type})
