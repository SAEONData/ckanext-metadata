# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.lib.helpers as helpers
import ckan.authz as authz
from ckan.logic import clean_dict, tuplize_dict, parse_params
import ckan.lib.navl.dictization_functions as dict_fns


class MetadataSchemaController(tk.BaseController):

    def _set_metadata_standard_context(self, metadata_standard_id):
        if metadata_standard_id and not tk.c.metadata_standard:
            context = {'model': model, 'session': model.Session, 'user': tk.c.user}
            data_dict = {'id': metadata_standard_id}
            try:
                tk.c.metadata_standard = tk.get_action('metadata_standard_show')(context, data_dict)
            except tk.ObjectNotFound:
                tk.abort(404, tk._('Metadata standard not found'))
            except tk.NotAuthorized:
                tk.abort(403, tk._('Not authorized to see this page'))

    def index(self, metadata_standard_id=None):
        self._set_metadata_standard_context(metadata_standard_id)

        page = tk.h.get_page_number(tk.request.params) or 1
        items_per_page = 21

        context = {'model': model, 'session': model.Session,
                   'user': tk.c.user, 'for_view': True}

        q = tk.c.q = tk.request.params.get('q', '')
        sort_by = tk.c.sort_by_selected = tk.request.params.get('sort')
        try:
            tk.check_access('site_read', context)
            tk.check_access('metadata_schema_list', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))

        if tk.c.userobj:
            context['user_id'] = tk.c.userobj.id
            context['user_is_admin'] = tk.c.userobj.sysadmin

        try:
            data_dict_global_results = {
                'metadata_standard_id': metadata_standard_id,
                'all_fields': False,
                'q': q,
                'sort': sort_by,
                'type': 'metadata_schema',
            }
            global_results = tk.get_action('metadata_schema_list')(context, data_dict_global_results)
        except tk.ValidationError as e:
            if e.error_dict and e.error_dict.get('message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            tk.h.flash_error(msg)
            tk.c.page = helpers.Page([], 0)
            return tk.render('metadata_schema/index.html')

        data_dict_page_results = {
            'metadata_standard_id': metadata_standard_id,
            'all_fields': True,
            'q': q,
            'sort': sort_by,
            'limit': items_per_page,
            'offset': items_per_page * (page - 1),
        }
        page_results = tk.get_action('metadata_schema_list')(context, data_dict_page_results)

        tk.c.page = helpers.Page(
            collection=global_results,
            page=page,
            url=tk.h.pager_url,
            items_per_page=items_per_page,
        )

        tk.c.page.items = page_results
        return tk.render('metadata_schema/index.html')

    def new(self, data=None, errors=None, error_summary=None, metadata_standard_id=None):
        self._set_metadata_standard_context(metadata_standard_id)

        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params}
        try:
            tk.check_access('metadata_schema_create', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to create a metadata schema'))

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_new(context)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'new',
                'organization_lookup_list': self._organization_lookup_list(),
                'infrastructure_lookup_list': self._infrastructure_lookup_list()}

        tk.c.is_sysadmin = authz.is_sysadmin(tk.c.user)
        tk.c.form = tk.render('metadata_schema/edit_form.html', extra_vars=vars)
        return tk.render('metadata_schema/new.html')

    def edit(self, id, data=None, errors=None, error_summary=None, metadata_standard_id=None):
        self._set_metadata_standard_context(metadata_standard_id)

        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params, 'for_edit': True}
        data_dict = {'id': id}

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_edit(id, context)

        try:
            old_data = tk.get_action('metadata_schema_show')(context, data_dict)
            data = data or old_data
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Metadata schema not found'))

        tk.c.metadata_schema = old_data
        try:
            tk.check_access('metadata_schema_update', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('User %r not authorized to edit %s') % (tk.c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'edit',
                'organization_lookup_list': self._organization_lookup_list(),
                'infrastructure_lookup_list': self._infrastructure_lookup_list()}

        tk.c.form = tk.render('metadata_schema/edit_form.html', extra_vars=vars)
        return tk.render('metadata_schema/edit.html')

    def delete(self, id, metadata_standard_id=None):
        if 'cancel' in tk.request.params:
            tk.h.redirect_to('metadata_schema_edit', id=id, metadata_standard_id=metadata_standard_id)

        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        try:
            tk.check_access('metadata_schema_delete', context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to delete metadata schema'))

        try:
            if tk.request.method == 'POST':
                tk.get_action('metadata_schema_delete')(context, {'id': id})
                tk.h.flash_notice(tk._('Metadata Schema has been deleted.'))
                tk.h.redirect_to('metadata_schema_index', metadata_standard_id=metadata_standard_id)
            tk.c.metadata_schema = tk.get_action('metadata_schema_show')(context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to delete metadata schema'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata_schema not found'))
        return tk.render('metadata_schema/confirm_delete.html')

    def read(self, id, metadata_standard_id=None):
        self._set_metadata_standard_context(metadata_standard_id)
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.metadata_schema = tk.get_action('metadata_schema_show')(context, {'id': id})
        return tk.render('metadata_schema/read.html')

    def about(self, id, metadata_standard_id=None):
        self._set_metadata_standard_context(metadata_standard_id)
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.metadata_schema = tk.get_action('metadata_schema_show')(context, {'id': id})
        return tk.render('metadata_schema/about.html')

    def activity(self, id, metadata_standard_id=None):
        self._set_metadata_standard_context(metadata_standard_id)
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.metadata_schema = tk.get_action('metadata_schema_show')(context, {'id': id})
        return tk.render('metadata_schema/activity_stream.html')

    @staticmethod
    def _organization_lookup_list():
        """
        Return a list of {'value': name, 'text': display_name} dicts for populating the
        organization select control.
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        organizations = tk.get_action('organization_list')(context, {'all_fields': True})
        return [{'value': '', 'text': tk._('(All)')}] + \
               [{'value': organization['name'], 'text': organization['display_name']}
                for organization in organizations]

    @staticmethod
    def _infrastructure_lookup_list():
        """
        Return a list of {'value': name, 'text': display_name} dicts for populating the
        infrastructure select control.
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        infrastructures = tk.get_action('infrastructure_list')(context, {'all_fields': True})
        return [{'value': '', 'text': tk._('(All)')}] + \
               [{'value': infrastructure['name'], 'text': infrastructure['display_name']}
                for infrastructure in infrastructures]

    def _save_new(self, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            context['message'] = data_dict.get('log_message', '')
            metadata_schema = tk.get_action('metadata_schema_create')(context, data_dict)
            tk.h.redirect_to('metadata_schema_read', id=metadata_schema['name'], metadata_standard_id=tk.c.metadata_standard['name'])
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Metadata schema not found'))
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
            context['message'] = data_dict.get('log_message', '')
            context['allow_partial_update'] = True
            metadata_schema = tk.get_action('metadata_schema_update')(context, data_dict)
            tk.h.redirect_to('metadata_schema_read', id=metadata_schema['name'], metadata_standard_id=tk.c.metadata_standard['name'])
        except (tk.ObjectNotFound, tk.NotAuthorized), e:
            tk.abort(404, tk._('Metadata schema not found'))
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)
