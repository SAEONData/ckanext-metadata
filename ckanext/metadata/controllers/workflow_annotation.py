# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.authz as authz
from ckan.logic import clean_dict, tuplize_dict, parse_params
import ckan.lib.navl.dictization_functions as dict_fns
from ckanext.metadata.common import WORKFLOW_ANNOTATION_ATTRIBUTE_TYPES


class WorkflowAnnotationController(tk.BaseController):

    def index(self):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        data_dict = {'all_fields': True, 'deserialize_json': True}
        try:
            workflow_annotation_list = tk.get_action('workflow_annotation_list')(context, data_dict)
            tk.c.workflow_annotations = workflow_annotation_list
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))

        return tk.render('workflow_annotation/index.html')

    def new(self, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params}

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_new(context)

        try:
            tk.check_access('workflow_annotation_create', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to create workflow annotations'))

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'new',
                'attribute_types': WORKFLOW_ANNOTATION_ATTRIBUTE_TYPES}

        tk.c.is_sysadmin = authz.is_sysadmin(tk.c.user)
        tk.c.form = tk.render('workflow_annotation/edit_form.html', extra_vars=vars)
        return tk.render('workflow_annotation/edit.html', extra_vars=vars)

    def edit(self, id, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params, 'for_edit': True}
        data_dict = {'id': id}

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_edit(id, context)

        try:
            old_data = tk.get_action('workflow_annotation_show')(context, data_dict)
            data = data or old_data
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Workflow annotation not found'))

        tk.c.workflow_annotation = old_data
        try:
            tk.check_access('workflow_annotation_update', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('User %r not authorized to edit %s') % (tk.c.user, id))

        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'edit',
                'attribute_types': WORKFLOW_ANNOTATION_ATTRIBUTE_TYPES}

        tk.c.form = tk.render('workflow_annotation/edit_form.html', extra_vars=vars)
        return tk.render('workflow_annotation/edit.html', extra_vars=vars)

    def delete(self, id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        try:
            if tk.request.method == 'POST':
                tk.get_action('workflow_annotation_delete')(context, {'id': id})
                tk.h.flash_notice(tk._('Workflow annotation has been deleted.'))
                tk.h.redirect_to('workflow_annotation_index')
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to delete workflow annotation'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Workflow annotation not found'))

    def _save_new(self, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            data_dict.setdefault('is_array', False)
            context['message'] = data_dict.get('log_message', '')
            tk.get_action('workflow_annotation_create')(context, data_dict)
            tk.h.redirect_to('workflow_annotation_index')
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Workflow annotation not found'))
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
            data_dict.setdefault('is_array', False)
            context['message'] = data_dict.get('log_message', '')
            context['allow_partial_update'] = True
            tk.get_action('workflow_annotation_update')(context, data_dict)
            tk.h.redirect_to('workflow_annotation_index')
        except (tk.ObjectNotFound, tk.NotAuthorized), e:
            tk.abort(404, tk._('Workflow annotation not found'))
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)
