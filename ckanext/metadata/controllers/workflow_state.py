# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.lib.helpers as helpers
import ckan.authz as authz
from ckan.logic import clean_dict, tuplize_dict, parse_params
import ckan.lib.navl.dictization_functions as dict_fns


class WorkflowStateController(tk.BaseController):

    def index(self):
        page = tk.h.get_page_number(tk.request.params) or 1
        items_per_page = 21

        context = {'model': model, 'session': model.Session,
                   'user': tk.c.user, 'for_view': True}

        q = tk.c.q = tk.request.params.get('q', '')
        sort_by = tk.c.sort_by_selected = tk.request.params.get('sort')
        try:
            tk.check_access('site_read', context)
            tk.check_access('workflow_state_list', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))

        if tk.c.userobj:
            context['user_id'] = tk.c.userobj.id
            context['user_is_admin'] = tk.c.userobj.sysadmin

        try:
            data_dict_global_results = {
                'all_fields': False,
                'q': q,
                'sort': sort_by,
                'type': 'workflow_state',
            }
            global_results = tk.get_action('workflow_state_list')(context, data_dict_global_results)
        except tk.ValidationError as e:
            if e.error_dict and e.error_dict.get('message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            tk.h.flash_error(msg)
            tk.c.page = helpers.Page([], 0)
            return tk.render('workflow_state/index.html')

        data_dict_page_results = {
            'all_fields': True,
            'q': q,
            'sort': sort_by,
            'limit': items_per_page,
            'offset': items_per_page * (page - 1),
        }
        page_results = tk.get_action('workflow_state_list')(context, data_dict_page_results)

        tk.c.page = helpers.Page(
            collection=global_results,
            page=page,
            url=tk.h.pager_url,
            items_per_page=items_per_page,
        )

        tk.c.page.items = page_results
        return tk.render('workflow_state/index.html')

    def new(self, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params}
        try:
            tk.check_access('workflow_state_create', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to create a workflow state'))

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_new(context)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'new',
                'revert_state_lookup_list': self._revert_state_lookup_list()}

        tk.c.is_sysadmin = authz.is_sysadmin(tk.c.user)
        tk.c.form = tk.render('workflow_state/edit_form.html', extra_vars=vars)
        return tk.render('workflow_state/new.html')

    def edit(self, id, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params, 'for_edit': True}
        data_dict = {'id': id}

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_edit(id, context)

        try:
            old_data = tk.get_action('workflow_state_show')(context, data_dict)
            old_data['metadata_records_published'] = not old_data['metadata_records_private']
            data = data or old_data
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Workflow state not found'))

        tk.c.workflow_state = old_data
        try:
            tk.check_access('workflow_state_update', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('User %r not authorized to edit %s') % (tk.c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'edit',
                'revert_state_lookup_list': self._revert_state_lookup_list(exclude=id)}

        tk.c.form = tk.render('workflow_state/edit_form.html', extra_vars=vars)
        return tk.render('workflow_state/edit.html')

    def delete(self, id):
        if 'cancel' in tk.request.params:
            tk.h.redirect_to('workflow_state_edit', id=id)

        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        try:
            tk.check_access('workflow_state_delete', context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to delete workflow state'))

        try:
            if tk.request.method == 'POST':
                tk.get_action('workflow_state_delete')(context, {'id': id})
                tk.h.flash_notice(tk._('Workflow state has been deleted.'))
                tk.h.redirect_to('workflow_state_index')
            tk.c.workflow_state = tk.get_action('workflow_state_show')(context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to delete workflow state'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Workflow state not found'))
        return tk.render('workflow_state/confirm_delete.html')

    def read(self, id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.workflow_state = tk.get_action('workflow_state_show')(context, {'id': id})
        return tk.render('workflow_state/read.html')

    def about(self, id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.workflow_state = tk.get_action('workflow_state_show')(context, {'id': id})
        return tk.render('workflow_state/about.html')

    def activity(self, id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.workflow_state = tk.get_action('workflow_state_show')(context, {'id': id})
        return tk.render('workflow_state/activity_stream.html')

    @staticmethod
    def _revert_state_lookup_list(exclude=None):
        """
        Return a list of {'value': name, 'text': display_name} dicts for populating the
        revert state select control.
        :param exclude: name of workflow state to exclude (if it's the one being edited)
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        workflow_states = tk.get_action('workflow_state_list')(context, {'all_fields': True})
        return [{'value': '', 'text': '(None)'}] + \
               [{'value': workflow_state['name'], 'text': workflow_state['display_name']}
                for workflow_state in workflow_states if workflow_state['name'] != exclude]

    def _save_new(self, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            data_dict.setdefault('metadata_records_published', False)
            data_dict['metadata_records_private'] = not data_dict['metadata_records_published']
            context['message'] = data_dict.get('log_message', '')
            workflow_state = tk.get_action('workflow_state_create')(context, data_dict)
            tk.h.redirect_to('workflow_state_read', id=workflow_state['name'])
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Workflow state not found'))
        except tk.NotAuthorized, e:
            tk.abort(403, e.message)
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

    def _save_edit(self, id, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            data_dict['id'] = id
            data_dict.setdefault('metadata_records_published', False)
            data_dict['metadata_records_private'] = not data_dict['metadata_records_published']
            context['message'] = data_dict.get('log_message', '')
            context['allow_partial_update'] = True
            workflow_state = tk.get_action('workflow_state_update')(context, data_dict)
            tk.h.redirect_to('workflow_state_read', id=workflow_state['name'])
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Workflow state not found'))
        except tk.NotAuthorized, e:
            tk.abort(403, e.message)
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)
