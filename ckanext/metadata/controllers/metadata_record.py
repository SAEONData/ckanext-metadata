# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.lib.helpers as helpers
import ckan.authz as authz
from ckan.logic import clean_dict, tuplize_dict, parse_params
import ckan.lib.navl.dictization_functions as dict_fns


class MetadataRecordController(tk.BaseController):

    # Note: URLs must be constructed using metadata_record.id rather than metadata_record.name,
    # because name can be mapped from a metadata JSON element which we cannot rely on to be
    # URL safe; e.g. if name gets the DOI it will contain a '/'.

    @staticmethod
    def _set_containers_on_context(organization_id, metadata_collection_id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}

        if organization_id and not tk.c.organization:
            data_dict = {'id': organization_id}
            try:
                tk.c.organization = tk.get_action('organization_show')(context, data_dict)
            except tk.ObjectNotFound:
                tk.abort(404, tk._('Organization not found'))
            except tk.NotAuthorized:
                tk.abort(403, tk._('Not authorized to see this page'))

        if metadata_collection_id and not tk.c.metadata_collection:
            data_dict = {'id': metadata_collection_id}
            try:
                tk.c.metadata_collection = tk.get_action('metadata_collection_show')(context, data_dict)
            except tk.ObjectNotFound:
                tk.abort(404, tk._('Metadata collection not found'))
            except tk.NotAuthorized:
                tk.abort(403, tk._('Not authorized to see this page'))

            if not organization_id:
                tk.abort(400, tk._('Organization not specified'))
            org = tk.c.organization
            if tk.c.metadata_collection['organization_id'] not in (org['id'], org['name']):
                tk.abort(400, tk._('Metadata collection does not belong to the specified organization'))

    @staticmethod
    def _set_additionalinfo_on_context(metadata_record):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        tk.c.metadata_standard = tk.get_action('metadata_standard_show')(context, {'id': metadata_record['metadata_standard_id']})
        if metadata_record['workflow_state_id']:
            tk.c.workflow_state = tk.get_action('workflow_state_show')(context, {'id': metadata_record['workflow_state_id']})

    def index(self, organization_id=None, metadata_collection_id=None):
        self._set_containers_on_context(organization_id, metadata_collection_id)

        page = tk.h.get_page_number(tk.request.params) or 1
        items_per_page = 21

        context = {'model': model, 'session': model.Session,
                   'user': tk.c.user, 'for_view': True}

        q = tk.c.q = tk.request.params.get('q', '')
        sort_by = tk.c.sort_by_selected = tk.request.params.get('sort')
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
                'metadata_collection_id': metadata_collection_id,
                'all_fields': False,
                'q': q,
                'sort': sort_by,
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
            return tk.render('metadata_record/index.html')

        data_dict_page_results = {
            'owner_org': organization_id,
            'metadata_collection_id': metadata_collection_id,
            'all_fields': True,
            'q': q,
            'sort': sort_by,
            'limit': items_per_page,
            'offset': items_per_page * (page - 1),
        }
        page_results = tk.get_action('metadata_record_list')(context, data_dict_page_results)

        tk.c.page = helpers.Page(
            collection=global_results,
            page=page,
            url=tk.h.pager_url,
            items_per_page=items_per_page,
        )

        tk.c.page.items = page_results
        return tk.render('metadata_record/index.html')

    def new(self, data=None, errors=None, error_summary=None, organization_id=None, metadata_collection_id=None):
        self._set_containers_on_context(organization_id, metadata_collection_id)

        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params}
        try:
            tk.check_access('metadata_record_create', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to create a metadata record'))

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_new(context)

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'new',
                'metadata_standard_lookup_list': self._metadata_standard_lookup_list(),
                'infrastructure_lookup_list': self._infrastructure_lookup_list()}

        tk.c.is_sysadmin = authz.is_sysadmin(tk.c.user)
        tk.c.form = tk.render('metadata_record/edit_form.html', extra_vars=vars)
        return tk.render('metadata_record/new.html')

    def edit(self, id, data=None, errors=None, error_summary=None, organization_id=None, metadata_collection_id=None):
        self._set_containers_on_context(organization_id, metadata_collection_id)

        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params, 'for_edit': True}
        data_dict = {'id': id}

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_edit(id, context)

        try:
            old_data = tk.get_action('metadata_record_show')(context, data_dict)
            data = data or old_data
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Metadata record not found'))

        tk.c.metadata_record = old_data
        try:
            tk.check_access('metadata_record_update', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('User %r not authorized to edit %s') % (tk.c.user, id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'edit',
                'metadata_standard_lookup_list': self._metadata_standard_lookup_list(),
                'infrastructure_lookup_list': self._infrastructure_lookup_list(),
                'selected_infrastructure_ids': [i['id'] for i in data['infrastructures']]}

        self._set_additionalinfo_on_context(tk.c.metadata_record)
        tk.c.form = tk.render('metadata_record/edit_form.html', extra_vars=vars)
        return tk.render('metadata_record/edit.html')

    def delete(self, id, organization_id=None, metadata_collection_id=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        try:
            if tk.request.method == 'POST':
                tk.get_action('metadata_record_delete')(context, {'id': id})
                tk.h.flash_notice(tk._('Metadata record has been deleted.'))
                tk.h.redirect_to('metadata_record_index', organization_id=organization_id, metadata_collection_id=metadata_collection_id)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to delete metadata record'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata record not found'))

    def read(self, id, organization_id=None, metadata_collection_id=None):
        self._set_containers_on_context(organization_id, metadata_collection_id)
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.metadata_record = tk.get_action('metadata_record_show')(context, {'id': id})
        self._set_additionalinfo_on_context(tk.c.metadata_record)
        return tk.render('metadata_record/read.html')

    def activity(self, id, organization_id=None, metadata_collection_id=None):
        self._set_containers_on_context(organization_id, metadata_collection_id)
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.metadata_record = tk.get_action('metadata_record_show')(context, {'id': id})
        self._set_additionalinfo_on_context(tk.c.metadata_record)
        return tk.render('metadata_record/activity_stream.html')

    def status(self, id, organization_id=None, metadata_collection_id=None):
        self._set_containers_on_context(organization_id, metadata_collection_id)
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        tk.c.metadata_record = tk.get_action('metadata_record_show')(context, {'id': id})
        self._set_additionalinfo_on_context(tk.c.metadata_record)
        return tk.render('metadata_record/status.html')

    def validation(self, id, organization_id=None, metadata_collection_id=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}

        if tk.request.method == 'POST':
            if 'validate' in tk.request.params:
                self._validate(id, organization_id, metadata_collection_id, context)
            else:
                self._invalidate(id, organization_id, metadata_collection_id, context)

        tk.c.metadata_record = tk.get_action('metadata_record_show')(context, {'id': id})
        self._set_containers_on_context(organization_id, metadata_collection_id)
        self._set_additionalinfo_on_context(tk.c.metadata_record)

        page = tk.h.get_page_number(tk.request.params) or 1
        items_per_page = 21

        q = tk.c.q = tk.request.params.get('q', '')
        try:
            tk.check_access('site_read', context)
            tk.check_access('metadata_record_validation_schema_list', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))

        try:
            data_dict_page_results = {
                'id': id,
                'all_fields': True,
                'q': q,
            }
            page_results = tk.get_action('metadata_record_validation_schema_list')(context, data_dict_page_results)
            tk.c.page = helpers.Page(
                collection=page_results,
                page=page,
                url=tk.h.pager_url,
                items_per_page=items_per_page,
            )
            tk.c.page.items = page_results
        except tk.ValidationError as e:
            if e.error_dict and e.error_dict.get('message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            tk.h.flash_error(msg)
            tk.c.page = helpers.Page([], 0)

        return tk.render('metadata_record/validation.html')

    @staticmethod
    def _validate(id, organization_id, metadata_collection_id, context):
        try:
            tk.get_action('metadata_record_validate')(context, {'id': id})
            tk.h.flash_notice(tk._('Metadata record has been validated.'))
            tk.h.redirect_to('metadata_record_validation', id=id, organization_id=organization_id, metadata_collection_id=metadata_collection_id)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to validate metadata record'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata record not found'))

    @staticmethod
    def _invalidate(id, organization_id, metadata_collection_id, context):
        try:
            tk.get_action('metadata_record_invalidate')(context, {'id': id})
            tk.h.flash_notice(tk._('Metadata record has been invalidated.'))
            tk.h.redirect_to('metadata_record_validation', id=id, organization_id=organization_id, metadata_collection_id=metadata_collection_id)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to invalidate metadata record'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata record not found'))

    def workflow(self, id, organization_id=None, metadata_collection_id=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}

        if tk.request.method == 'POST':
            if 'transition' in tk.request.params:
                target_state_id = tk.request.params.get('target_state_id')
                if target_state_id:
                    self._transition(id, organization_id, metadata_collection_id, target_state_id, context)
            else:
                self._revert(id, organization_id, metadata_collection_id, context)

        tk.c.metadata_record = tk.get_action('metadata_record_show')(context, {'id': id})
        self._set_containers_on_context(organization_id, metadata_collection_id)
        self._set_additionalinfo_on_context(tk.c.metadata_record)
        return tk.render('metadata_record/workflow.html', extra_vars={
            'workflow_state_lookup_list': self._workflow_state_lookup_list()})

    @staticmethod
    def _transition(id, organization_id, metadata_collection_id, workflow_state_id, context):
        try:
            tk.get_action('metadata_record_workflow_state_transition')(context, {'id': id, 'workflow_state_id': workflow_state_id})
            tk.h.flash_notice(tk._('The metadata record has been transitioned to a new workflow state.'))
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to change the workflow state of the metadata record'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata record not found'))
        except tk.ValidationError as e:
            if e.error_dict and e.error_dict.get('message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            tk.h.flash_error(msg)
        tk.h.redirect_to('metadata_record_workflow', id=id, organization_id=organization_id, metadata_collection_id=metadata_collection_id)

    @staticmethod
    def _revert(id, organization_id, metadata_collection_id, context):
        try:
            tk.get_action('metadata_record_workflow_state_revert')(context, {'id': id})
            tk.h.flash_notice(tk._('The workflow state of the metadata record has been reverted.'))
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to revert the workflow state of the metadata record'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata record not found'))
        except tk.ValidationError as e:
            if e.error_dict and e.error_dict.get('message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            tk.h.flash_error(msg)
        tk.h.redirect_to('metadata_record_workflow', id=id, organization_id=organization_id, metadata_collection_id=metadata_collection_id)

    @staticmethod
    def _metadata_standard_lookup_list():
        """
        Return a list of {'value': name, 'text': display_name} dicts for populating the
        metadata standard select control.
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        metadata_standards = tk.get_action('metadata_standard_list')(context, {'all_fields': True})
        return [{'value': '', 'text': tk._('(None)')}] + \
               [{'value': metadata_standard['name'], 'text': metadata_standard['display_name']}
                for metadata_standard in metadata_standards]

    @staticmethod
    def _infrastructure_lookup_list():
        """
        Return a list of {'value': name, 'text': display_name} dicts for populating the
        infrastructure select control.
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        infrastructures = tk.get_action('infrastructure_list')(context, {'all_fields': True})
        return [{'value': infrastructure['name'], 'text': infrastructure['display_name']}
                for infrastructure in infrastructures]

    @staticmethod
    def _workflow_state_lookup_list():
        """
        Return a list of {'value': name, 'text': display_name} dicts for populating the
        workflow state select control on the workflows tab.
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        workflow_states = tk.get_action('workflow_state_list')(context, {'all_fields': True})
        return [{'value': '', 'text': tk._('(None)')}] + \
               [{'value': workflow_state['name'], 'text': workflow_state['display_name']}
                for workflow_state in workflow_states]

    def _save_new(self, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            data_dict['infrastructures'] = self._parse_infrastructure_ids(data_dict.get('infrastructure_ids'))
            context['message'] = data_dict.get('log_message', '')
            metadata_record = tk.get_action('metadata_record_create')(context, data_dict)
            tk.h.redirect_to('metadata_record_read', id=metadata_record['id'],
                             organization_id=tk.c.organization['name'],
                             metadata_collection_id=tk.c.metadata_collection['name'])
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Metadata record not found'))
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
            data_dict['infrastructures'] = self._parse_infrastructure_ids(data_dict.get('infrastructure_ids'))
            context['message'] = data_dict.get('log_message', '')
            context['allow_partial_update'] = True
            metadata_record = tk.get_action('metadata_record_update')(context, data_dict)
            tk.h.redirect_to('metadata_record_read', id=metadata_record['id'],
                             organization_id=tk.c.organization['name'],
                             metadata_collection_id=tk.c.metadata_collection['name'])
        except (tk.ObjectNotFound, tk.NotAuthorized), e:
            tk.abort(404, tk._('Metadata record not found'))
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)

    @staticmethod
    def _parse_infrastructure_ids(infrastructure_ids):
        if not infrastructure_ids:
            return []
        if isinstance(infrastructure_ids, basestring):
            return [{'id': infrastructure_ids}]
        return [{'id': infrastructure_id} for infrastructure_id in infrastructure_ids]
