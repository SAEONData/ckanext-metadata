# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.lib.helpers as helpers
import ckan.authz as authz
from ckan.logic import clean_dict, tuplize_dict, parse_params
import ckan.lib.navl.dictization_functions as dict_fns


class MetadataStandardController(tk.BaseController):

    def index(self):
        page = tk.h.get_page_number(tk.request.params) or 1
        items_per_page = 21

        context = {'model': model, 'session': model.Session,
                   'user': tk.c.user, 'for_view': True}

        q = tk.c.q = tk.request.params.get('q', '')
        sort_by = tk.c.sort_by_selected = tk.request.params.get('sort')
        try:
            tk.check_access('site_read', context)
            tk.check_access('metadata_standard_list', context)
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
                'type': 'metadata_standard',
            }
            global_results = tk.get_action('metadata_standard_list')(context, data_dict_global_results)
        except tk.ValidationError as e:
            if e.error_dict and e.error_dict.get('message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            tk.h.flash_error(msg)
            tk.c.page = helpers.Page([], 0)
            return tk.render('metadata_standard/index.html')

        data_dict_page_results = {
            'all_fields': True,
            'q': q,
            'sort': sort_by,
            'limit': items_per_page,
            'offset': items_per_page * (page - 1),
        }
        page_results = tk.get_action('metadata_standard_list')(context, data_dict_page_results)

        tk.c.page = helpers.Page(
            collection=global_results,
            page=page,
            url=tk.h.pager_url,
            items_per_page=items_per_page,
        )

        tk.c.page.items = page_results
        return tk.render('metadata_standard/index.html')

    def new(self, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params}
        try:
            tk.check_access('metadata_standard_create', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to create a metadata standard'))

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_new(context)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'new',
                'parent_standard_lookup_list': self._parent_standard_lookup_list()}

        tk.c.is_sysadmin = authz.is_sysadmin(tk.c.user)
        tk.c.form = tk.render('metadata_standard/edit_form.html', extra_vars=vars)
        return tk.render('metadata_standard/new.html')

    def edit(self, id, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params, 'for_edit': True}
        data_dict = {'id': id}

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_edit(id, context)

        try:
            old_data = tk.get_action('metadata_standard_show')(context, data_dict)
            data = data or old_data
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Metadata standard not found'))

        tk.c.metadata_standard = old_data
        try:
            tk.check_access('metadata_standard_update', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('User %r not authorized to edit %s') % (tk.c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'edit',
                'parent_standard_lookup_list': self._parent_standard_lookup_list(exclude=id)}

        tk.c.form = tk.render('metadata_standard/edit_form.html', extra_vars=vars)
        return tk.render('metadata_standard/edit.html')

    def delete(self, id):
        if 'cancel' in tk.request.params:
            tk.h.redirect_to('metadata_standard_edit', id=id)

        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        try:
            tk.check_access('metadata_standard_delete', context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to delete metadata standard'))

        try:
            if tk.request.method == 'POST':
                tk.get_action('metadata_standard_delete')(context, {'id': id})
                tk.h.flash_notice(tk._('Metadata Standard has been deleted.'))
                tk.h.redirect_to('metadata_standard_index')
            tk.c.metadata_standard = tk.get_action('metadata_standard_show')(context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to delete metadata standard'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata_standard not found'))
        return tk.render('metadata_standard/confirm_delete.html')

    def read(self, id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        page = tk.h.get_page_number(tk.request.params) or 1
        items_per_page = 21

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

        tk.c.metadata_standard = tk.get_action('metadata_standard_show')(context, {'id': id})
        try:
            data_dict_global_results = {
                'metadata_standard_id': id,
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
            return tk.render('metadata_standard/read.html')

        data_dict_page_results = {
            'metadata_standard_id': id,
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
        return tk.render('metadata_standard/read.html')

    def about(self, id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.metadata_standard = tk.get_action('metadata_standard_show')(context, {'id': id})
        return tk.render('metadata_standard/about.html')

    def activity(self, id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.metadata_standard = tk.get_action('metadata_standard_show')(context, {'id': id})
        return tk.render('metadata_standard/activity_stream.html')

    def attr_maps(self, id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        try:
            data_dict = {'metadata_standard_id': id, 'all_fields': True}
            tk.c.attr_maps = tk.get_action('metadata_json_attr_map_list')(context, data_dict)
            tk.c.metadata_standard = tk.get_action('metadata_standard_show')(context, {'id': id})
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata standard not found'))
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))

        return tk.render('metadata_standard/attr_maps.html')

    def attr_map_new(self, id):
        pass

    def attr_map_edit(self, id, attr_map_id):
        pass

    def attr_map_delete(self, id, attr_map_id):
        pass

    @staticmethod
    def _parent_standard_lookup_list(exclude=None):
        """
        Return a list of {'value': name, 'text': display_name} dicts for populating the
        parent standard select control.
        :param exclude: name of standard to exclude (if it's the one being edited)
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        metadata_standards = tk.get_action('metadata_standard_list')(context, {'all_fields': True})
        return [{'value': '', 'text': '(None)'}] + \
               [{'value': metadata_standard['name'], 'text': metadata_standard['display_name']}
                for metadata_standard in metadata_standards if metadata_standard['name'] != exclude]

    def _save_new(self, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            context['message'] = data_dict.get('log_message', '')
            metadata_standard = tk.get_action('metadata_standard_create')(context, data_dict)
            tk.h.redirect_to('metadata_standard_read', id=metadata_standard['name'])
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Metadata standard not found'))
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
            metadata_standard = tk.get_action('metadata_standard_update')(context, data_dict)
            tk.h.redirect_to('metadata_standard_read', id=metadata_standard['name'])
        except (tk.ObjectNotFound, tk.NotAuthorized), e:
            tk.abort(404, tk._('Metadata standard not found'))
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)
