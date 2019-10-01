# encoding: utf-8

import re

import ckan.plugins.toolkit as tk
from ckan.controllers.group import GroupController
from ckan.lib.render import TemplateNotFound
import ckan.model as model
import ckan.lib.helpers as helpers
from ckan.logic import clean_dict, tuplize_dict, parse_params
import ckan.lib.navl.dictization_functions as dict_fns


class MetadataCollectionController(GroupController):

    group_types = ['metadata_collection']

    def _guess_group_type(self, expecting_name=False):
        return 'metadata_collection'

    @staticmethod
    def _substitute_name(name):
        return re.sub('^group', 'metadata_collection', name)

    def _action(self, action_name):
        """
        Return the corresponding 'metadata_collection_' action if it exists,
        otherwise fall back to the given 'group_' action.
        """
        try:
            return tk.get_action(self._substitute_name(action_name))
        except KeyError:
            return tk.get_action(action_name)

    def _check_access(self, action_name, *args, **kw):
        """
        Check access for the corresponding 'metadata_collection_' action if it exists,
        otherwise fall back to the given 'group_' action.
        """
        try:
            return tk.check_access(self._substitute_name(action_name), *args, **kw)
        except ValueError:
            return tk.check_access(action_name, *args, **kw)

    def _render_template(self, template_name, group_type):
        """
        Render the corresponding 'metadata_collection_' template if it exists,
        otherwise fall back to the given 'group_' template.
        """
        try:
            return tk.render(self._substitute_name(template_name), extra_vars={'group_type': group_type})
        except TemplateNotFound:
            return tk.render(template_name, extra_vars={'group_type': group_type})

    def _redirect_to_this_controller(self, *args, **kw):
        if tk.c.org_dict:
            kw['organization_id'] = tk.c.org_dict['name']
        return super(MetadataCollectionController, self)._redirect_to_this_controller(*args, **kw)

    def _url_for_this_controller(self, *args, **kw):
        if tk.c.org_dict:
            kw['organization_id'] = tk.c.org_dict['name']
        return super(MetadataCollectionController, self)._redirect_to_this_controller(*args, **kw)

    def _set_organization_context(self, organization_id):
        if organization_id and not tk.c.org_dict:
            context = {'model': model, 'session': model.Session, 'user': tk.c.user}
            data_dict = {'id': organization_id}
            try:
                tk.c.org_dict = tk.get_action('organization_show')(context, data_dict)
            except tk.ObjectNotFound:
                tk.abort(404, tk._('Organization not found'))
            except tk.NotAuthorized:
                tk.abort(403, tk._('Not authorized to see this page'))

    def index(self, organization_id=None):
        tk.h.redirect_to('organization_read', id=organization_id)

    def new(self, data=None, errors=None, error_summary=None, organization_id=None):
        self._set_organization_context(organization_id)
        return super(MetadataCollectionController, self).new(data, errors, error_summary)

    def edit(self, id, data=None, errors=None, error_summary=None, organization_id=None):
        self._set_organization_context(organization_id)
        return super(MetadataCollectionController, self).edit(id, data, errors, error_summary)

    def read(self, id, limit=50, organization_id=None):
        context = {'model': model, 'session': model.Session,
                   'user': tk.c.user, 'for_view': True}

        self._set_organization_context(organization_id)
        tk.c.group_dict = tk.get_action('metadata_collection_show')(context, {'id': id})

        page = tk.h.get_page_number(tk.request.params) or 1
        q = tk.c.q = tk.request.params.get('q', '')

        try:
            tk.check_access('site_read', context)
            tk.check_access('metadata_record_list', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))

        if tk.c.userobj:
            context['user_id'] = tk.c.userobj.id
            context['user_is_admin'] = tk.c.userobj.sysadmin

        try:
            data_dict_global_results = {
                'owner_org': organization_id,
                'metadata_collection_id': id,
                'all_fields': False,
                'q': q,
                'type': 'metadata_record',
            }
            global_results = tk.get_action('metadata_record_list')(context, data_dict_global_results)
        except tk.ValidationError as e:
            if e.error_dict and e.error_dict.get('message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            tk.h.flash_error(msg)
            tk.c.page = helpers.Page([], 0)
            return tk.render('metadata_collection/read.html')

        data_dict_page_results = {
            'owner_org': organization_id,
            'metadata_collection_id': id,
            'all_fields': True,
            'q': q,
            'limit': limit,
            'offset': limit * (page - 1),
        }
        page_results = tk.get_action('metadata_record_list')(context, data_dict_page_results)
        workflow_states = {ws['name']: ws['title'] for ws in tk.get_action('workflow_state_list')(context, {'all_fields': True})}
        for record in page_results:
            record['workflow_state'] = workflow_states.get(record['workflow_state_id'], '')

        tk.c.page = helpers.Page(
            collection=global_results,
            page=page,
            url=tk.h.pager_url,
            items_per_page=limit,
        )

        tk.c.page.items = page_results
        return tk.render('metadata_collection/read.html')

    def bulk_action(self, id, organization_id=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}

        if tk.request.method == 'POST':
            if 'bulk_validate' in tk.request.params:
                async = 'bulk_validate_async' in tk.request.params
                self._bulk_validate(id, organization_id, async, context)
            elif 'bulk_transition' in tk.request.params:
                target_state_id = tk.request.params.get('target_state_id')
                if target_state_id:
                    async = 'bulk_transition_async' in tk.request.params
                    self._bulk_transition(id, organization_id, target_state_id, async, context)
                else:
                    tk.h.flash_notice(tk._('Please select a target workflow state'))

        tk.c.group_dict = self._action('metadata_collection_show')(context, {'id': id})
        self._set_organization_context(organization_id)

        return tk.render('metadata_collection/bulk_action.html', extra_vars={
            'workflow_state_lookup_list': self._workflow_state_lookup_list()})

    @staticmethod
    def _bulk_validate(id, organization_id, async, context):
        try:
            result = tk.get_action('metadata_collection_validate')(context, {'id': id, 'async': async})
            total = result['total_count']
            if async:
                tk.h.flash_notice(tk._('%d metadata records have been queued for validation.' % total))
            else:
                tk.h.flash_success(tk._('%d metadata records have been validated.' % total))
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to validate metadata records'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata collection not found'))

        tk.h.redirect_to('metadata_collection_bulk_action', id=id, organization_id=organization_id)

    @staticmethod
    def _bulk_transition(id, organization_id, workflow_state_id, async, context):
        try:
            result = tk.get_action('metadata_collection_workflow_state_transition')(context, {'id': id, 'workflow_state_id': workflow_state_id, 'async': async})
            total = result['total_count']
            errors = result['error_count']
            success = total - errors
            if async:
                tk.h.flash_notice(tk._('%d metadata records have been queued for workflow state transition.' % total))
            else:
                tk.h.flash_success(tk._('%d metadata records have been processed; %d successes, %d failures.') % (total, success, errors))
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to change the workflow state of metadata records'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata collection not found'))

        tk.h.redirect_to('metadata_collection_bulk_action', id=id, organization_id=organization_id)

    @staticmethod
    def _workflow_state_lookup_list():
        """
        Return a list of {'value': name, 'text': display_name} dicts for populating the
        workflow state select control on the bulk action tab.
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        workflow_states = tk.get_action('workflow_state_list')(context, {'all_fields': True})
        return [{'value': '', 'text': tk._('(None)')}] + \
               [{'value': workflow_state['name'], 'text': workflow_state['display_name']}
                for workflow_state in workflow_states]

    def activity(self, id, offset=0, organization_id=None):
        self._set_organization_context(organization_id)
        return super(MetadataCollectionController, self).activity(id, offset)

    def about(self, id, organization_id=None):
        self._set_organization_context(organization_id)
        return super(MetadataCollectionController, self).about(id)

    def members(self, id, organization_id=None):
        self._set_organization_context(organization_id)
        return super(MetadataCollectionController, self).members(id)

    def member_new(self, id, organization_id=None):
        self._set_organization_context(organization_id)
        return super(MetadataCollectionController, self).member_new(id)

    def member_delete(self, id, organization_id=None):
        self._set_organization_context(organization_id)
        return super(MetadataCollectionController, self).member_delete(id)

    def _save_new(self, context, group_type=None):
        """
        Replacing GroupController._save_new because the redirect_to call is not wrapped.
        """
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            data_dict['type'] = 'metadata_collection'
            data_dict.setdefault('auto_assign_doi', False)
            context['message'] = data_dict.get('log_message', '')
            data_dict['users'] = [{'name': tk.c.user, 'capacity': 'admin'}]
            group = tk.get_action('metadata_collection_create')(context, data_dict)
            tk.h.redirect_to('metadata_collection_read', id=group['name'], organization_id=tk.c.org_dict['name'])
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Group not found'))
        except tk.NotAuthorized, e:
            tk.abort(403, e.message)
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

    def _save_edit(self, id, context):
        """
        Replacing GroupController._save_edit because the redirect_to call is not wrapped.
        """
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            data_dict.setdefault('auto_assign_doi', False)
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id
            context['allow_partial_update'] = True
            group = tk.get_action('metadata_collection_update')(context, data_dict)
            if id != group['name']:
                self._force_reindex(group)
            tk.h.redirect_to('metadata_collection_read', id=group['name'], organization_id=tk.c.org_dict['name'])
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Group not found'))
        except tk.NotAuthorized, e:
            tk.abort(403, e.message)
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)
