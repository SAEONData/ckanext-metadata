# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.authz as authz
from ckan.logic import clean_dict, tuplize_dict, parse_params
import ckan.lib.navl.dictization_functions as dict_fns


class WorkflowTransitionController(tk.BaseController):

    def index(self):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        data_dict = {'all_fields': True}
        try:
            workflow_transition_list = tk.get_action('workflow_transition_list')(context, data_dict)
            # todo: topological sort of transition list
            tk.c.workflow_transitions = workflow_transition_list
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))

        return tk.render('workflow_transition/index.html')

    def new(self, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params}

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_new(context)

        try:
            tk.check_access('workflow_transition_create', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to create workflow transitions'))

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary,
                'workflow_state_lookup_list': self._workflow_state_lookup_list()}

        tk.c.is_sysadmin = authz.is_sysadmin(tk.c.user)
        tk.c.form = tk.render('workflow_transition/edit_form.html', extra_vars=vars)
        return tk.render('workflow_transition/new.html')

    def delete(self, id):
        if 'cancel' in tk.request.params:
            tk.h.redirect_to('workflow_transition_index')

        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        try:
            tk.check_access('workflow_transition_delete', context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to delete workflow transitions'))

        if tk.request.method == 'POST':
            try:
                tk.get_action('workflow_transition_delete')(context, {'id': id})
                tk.h.flash_notice(tk._('Workflow transition has been deleted.'))
                tk.h.redirect_to('workflow_transition_index')
            except tk.NotAuthorized:
                tk.abort(403, tk._('Unauthorized to delete workflow transition'))
            except tk.ObjectNotFound:
                tk.abort(404, tk._('Workflow transition not found'))
            except dict_fns.DataError:
                tk.abort(400, tk._(u'Integrity Error'))
        return tk.render('workflow_transition/confirm_delete.html')

    @staticmethod
    def _workflow_state_lookup_list():
        """
        Return a list of {'value': name, 'text': display_name} dicts for populating the
        from- and to-state select controls.
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        workflow_states = tk.get_action('workflow_state_list')(context, {'all_fields': True})
        return [{'value': '', 'text': '(None)'}] + \
               [{'value': workflow_state['name'], 'text': workflow_state['display_name']}
                for workflow_state in workflow_states]

    def _save_new(self, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            context['message'] = data_dict.get('log_message', '')
            tk.get_action('workflow_transition_create')(context, data_dict)
            tk.h.redirect_to('workflow_transition_index')
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Workflow transition not found'))
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)
