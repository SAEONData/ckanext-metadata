# encoding: utf-8

import json

import ckan.plugins as p
import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.lib.helpers as helpers
from ckan.logic import clean_dict, tuplize_dict, parse_params
import ckan.lib.navl.dictization_functions as dict_fns


class MetadataRecordController(tk.BaseController):

    # Note: URLs must be constructed using metadata_record.id rather than metadata_record.name,
    # because name can be mapped from a metadata JSON element which we cannot rely on to be
    # URL safe; e.g. if name gets the DOI it will contain a '/'.

    @staticmethod
    def _set_template_vars(record_id, organization_id, collection_id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}

        try:
            if not tk.c.metadata_record:
                if record_id:
                    try:
                        tk.c.metadata_record = tk.get_action('metadata_record_show')(context, {'id': record_id})
                    except tk.ObjectNotFound:
                        tk.abort(404, tk._('Metadata record not found'))

            if not tk.c.organization:
                if not organization_id:
                    organization_id = tk.c.metadata_record['owner_org'] if tk.c.metadata_record else None
                try:
                    tk.c.organization = tk.get_action('organization_show')(context, {'id': organization_id})
                except tk.ObjectNotFound:
                    tk.abort(404, tk._('Organization not found'))

            if not tk.c.metadata_collection:
                if not collection_id:
                    collection_id = tk.c.metadata_record['metadata_collection_id'] if tk.c.metadata_record else None
                try:
                    tk.c.metadata_collection = tk.get_action('metadata_collection_show')(context, {'id': collection_id})
                except tk.ObjectNotFound:
                    tk.abort(404, tk._('Metadata collection not found'))

                org = tk.c.organization
                if tk.c.metadata_collection['organization_id'] not in (org['id'], org['name']):
                    tk.abort(400, tk._('Metadata collection does not belong to the specified organization'))

            if record_id and not tk.c.metadata_standard:
                tk.c.metadata_standard = tk.get_action('metadata_standard_show')(context, {'id': tk.c.metadata_record['metadata_standard_id']})

            if record_id and not tk.c.workflow_state:
                if tk.c.metadata_record['workflow_state_id']:
                    tk.c.workflow_state = tk.get_action('workflow_state_show')(context, {'id': tk.c.metadata_record['workflow_state_id']})

            tk.c.is_elasticsearch_enabled = p.plugin_loaded('metadata_elasticsearch')

        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))

    def index(self, organization_id=None, metadata_collection_id=None):
        tk.h.redirect_to('metadata_collection_read', organization_id=organization_id, id=metadata_collection_id)

    def new(self, data=None, errors=None, error_summary=None, organization_id=None, metadata_collection_id=None):
        self._set_template_vars(None, organization_id, metadata_collection_id)

        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params}

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_new(context)

        try:
            tk.check_access('metadata_record_create', context, {'owner_org': organization_id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to create a metadata record'))

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        metadata_standard_lookup_list = self._metadata_standard_lookup_list()
        doi_attr_mappings = self._doi_attribute_mappings([ms['value'] for ms in metadata_standard_lookup_list])
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'new',
                'metadata_standard_lookup_list': metadata_standard_lookup_list,
                'doi_attr_mappings': doi_attr_mappings}

        tk.c.form = tk.render('metadata_record/edit_form.html', extra_vars=vars)
        return tk.render('metadata_record/new.html')

    def edit(self, id, data=None, errors=None, error_summary=None, organization_id=None, metadata_collection_id=None):
        self._set_template_vars(id, organization_id, metadata_collection_id)

        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params, 'for_edit': True}

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_edit(id, context)

        try:
            tk.check_access('metadata_record_update', context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('User %r not authorized to edit %s') % (tk.c.user, id))

        data = data or tk.c.metadata_record
        errors = errors or {}
        error_summary = error_summary or {}
        metadata_standard_lookup_list = self._metadata_standard_lookup_list()
        doi_attr_mappings = self._doi_attribute_mappings([ms['value'] for ms in metadata_standard_lookup_list])
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'edit',
                'metadata_standard_lookup_list': metadata_standard_lookup_list,
                'doi_attr_mappings': doi_attr_mappings}

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
        self._set_template_vars(id, organization_id, metadata_collection_id)
        return tk.render('metadata_record/read.html')

    def activity(self, id, organization_id=None, metadata_collection_id=None):
        self._set_template_vars(id, organization_id, metadata_collection_id)
        return tk.render('metadata_record/activity_stream.html')

    def status(self, id, organization_id=None, metadata_collection_id=None):
        self._set_template_vars(id, organization_id, metadata_collection_id)
        return tk.render('metadata_record/status.html')

    def validation(self, id, organization_id=None, metadata_collection_id=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}

        if tk.request.method == 'POST':
            if 'validate' in tk.request.params:
                self._validate(id, organization_id, metadata_collection_id, context)
            else:
                self._invalidate(id, organization_id, metadata_collection_id, context)

        self._set_template_vars(id, organization_id, metadata_collection_id)

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

        last_validation_result = tk.get_action('metadata_record_validation_activity_show')(context, {'id': id})
        last_validation_result = json.dumps(last_validation_result, indent=4)

        return tk.render('metadata_record/validation.html', extra_vars={'last_validation_result': last_validation_result})

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
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}

        if tk.request.method == 'POST':
            if 'transition' in tk.request.params:
                target_state_id = tk.request.params.get('target_state_id')
                if target_state_id:
                    self._transition(id, organization_id, metadata_collection_id, target_state_id, context)
            else:
                self._revert(id, organization_id, metadata_collection_id, context)

        self._set_template_vars(id, organization_id, metadata_collection_id)
        tk.c.annotations = tk.get_action('metadata_record_workflow_annotation_list')(context, {'id': id})

        last_workflow_result = tk.get_action('metadata_record_workflow_activity_show')(context, {'id': id})
        last_workflow_result = json.dumps(last_workflow_result, indent=4)

        return tk.render('metadata_record/workflow.html', extra_vars={
            'workflow_state_lookup_list': self._workflow_state_lookup_list(),
            'last_workflow_result': last_workflow_result})

    def annotation_new(self, id, data=None, errors=None, error_summary=None, organization_id=None, metadata_collection_id=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params}

        self._set_template_vars(id, organization_id, metadata_collection_id)

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_annotation_new(id, context)

        try:
            tk.check_access('metadata_record_workflow_annotation_create', context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to add annotations to the metadata record'))

        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        predefined_annotations = self._predefined_annotation_list()
        data.setdefault('is_predefined', True)

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'new',
                'predefined_annotations': predefined_annotations,
                'annotation_key_lookup_list': self._annotation_key_lookup_list(predefined_annotations),
                'user_lookup_list': self._user_lookup_list(predefined_annotations),
                'email_lookup_list': self._email_lookup_list(predefined_annotations)}

        tk.c.form = tk.render('metadata_record/annotation_form.html', extra_vars=vars)
        return tk.render('metadata_record/annotation_edit.html', extra_vars=vars)

    def annotation_edit(self, id, key, data=None, errors=None, error_summary=None, organization_id=None, metadata_collection_id=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user,
                   'save': 'save' in tk.request.params}

        self._set_template_vars(id, organization_id, metadata_collection_id)

        if context['save'] and not data and tk.request.method == 'POST':
            return self._save_annotation_edit(id, key, context)

        try:
            tk.check_access('metadata_record_workflow_annotation_update', context, {'id': id})
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to update annotations on the metadata record'))

        try:
            old_data = tk.get_action('metadata_record_workflow_annotation_show')(context, {
                'id': id,
                'key': key,
                'deserialize_json': True,
            })
            data = data or old_data
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, tk._('Annotation not found'))

        errors = errors or {}
        predefined_annotations = self._predefined_annotation_list()
        data.setdefault('is_predefined', data['key'] in [a['name'] for a in predefined_annotations])

        vars = {'data': data, 'errors': errors, 'error_summary': error_summary, 'action': 'edit',
                'predefined_annotations': predefined_annotations,
                'annotation_key_lookup_list': self._annotation_key_lookup_list(predefined_annotations),
                'user_lookup_list': self._user_lookup_list(predefined_annotations),
                'email_lookup_list': self._email_lookup_list(predefined_annotations)}

        tk.c.form = tk.render('metadata_record/annotation_form.html', extra_vars=vars)
        return tk.render('metadata_record/annotation_edit.html', extra_vars=vars)

    def annotation_delete(self, id, key, organization_id=None, metadata_collection_id=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        try:
            if tk.request.method == 'POST':
                tk.get_action('metadata_record_workflow_annotation_delete')(context, {'id': id, 'key': key})
                tk.h.flash_notice(tk._('Annotation has been deleted.'))
                tk.h.redirect_to('metadata_record_workflow', id=id, organization_id=organization_id, metadata_collection_id=metadata_collection_id)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to delete annotation'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Annotation not found'))

    def elastic(self, id, organization_id=None, metadata_collection_id=None):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}

        if tk.request.method == 'POST':
            self._elastic_update_index(id, organization_id, metadata_collection_id, context)

        self._set_template_vars(id, organization_id, metadata_collection_id)
        return tk.render('metadata_record/elastic.html', extra_vars={
            'elastic_record_info': self._elastic_record_info(id)})

    @staticmethod
    def _transition(id, organization_id, metadata_collection_id, workflow_state_id, context):
        try:
            workflow_activity_dict = tk.get_action('metadata_record_workflow_state_transition')(context, {'id': id, 'workflow_state_id': workflow_state_id})
            if workflow_activity_dict['data']['errors']:
                tk.h.flash_error(tk._('The workflow transition could not be completed due to workflow validation errors.'))
            else:
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
    def _doi_attribute_mappings(metadata_standard_names):
        """
        Return a dict of {metadata_standard_name: doi_source_path}, where doi_source_path is
        the MetadataJSONAttrMap.json_path for MetadataJSONAttrMap.record_attr == 'doi', or ''
        if a 'doi' mapping has not been defined.

        :param metadata_standard_names: list of names of available metadata standards
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        result = {}
        for metadata_standard in metadata_standard_names:
            if not metadata_standard:
                result[metadata_standard] = ''
                continue
            attr_maps = tk.get_action('metadata_json_attr_map_list')(context, {
                'all_fields': True,
                'metadata_standard_id': metadata_standard,
            })
            doi_source_path = next((attr_map['json_path'] for attr_map in attr_maps
                                    if attr_map['record_attr'] == 'doi'), '')
            result[metadata_standard] = doi_source_path
        return result

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

    @staticmethod
    def _predefined_annotation_list():
        """
        Return a list of predefined workflow annotations.
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        return tk.get_action('workflow_annotation_list')(context, {'all_fields': True, 'deserialize_json': True})

    @staticmethod
    def _annotation_key_lookup_list(predefined_annotations):
        """
        Return a list of {'value': name, 'text': display_name} dicts for populating the
        annotation key select control.
        """
        return [{'value': '', 'text': tk._('(None)')}] + \
               [{'value': annotation['name'], 'text': annotation['name']} for annotation in predefined_annotations]

    @staticmethod
    def _user_lookup_list(predefined_annotations):
        """
        Return a list of {'value': user_id, 'text': user_email} dicts for populating user
        select controls, if there are any 'userid' type attributes in the predefined annotation definitions.
        """
        if any((True for annotation in predefined_annotations if 'userid' in annotation['attributes'].itervalues())):
            context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'keep_email': True}
            users = tk.get_action('user_list')(context, {'all_fields': True})
            return [{'value': '', 'text': tk._('(None)')}] + \
                   [{'value': user['id'], 'text': user['email']}
                    for user in users if user['name'] != 'default']

    @staticmethod
    def _email_lookup_list(predefined_annotations):
        """
        Return a list of {'value': user_email, 'text': user_email} dicts for populating user
        select controls, if there are any 'email' type attributes in the predefined annotation definitions.
        """
        if any((True for annotation in predefined_annotations if 'email' in annotation['attributes'].itervalues())):
            context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'keep_email': True}
            users = tk.get_action('user_list')(context, {'all_fields': True})
            return [{'value': '', 'text': tk._('(None)')}] + \
                   [{'value': user['email'], 'text': user['email']}
                    for user in users if user['name'] != 'default']

    def _save_new(self, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            context['message'] = data_dict.get('log_message', '')
            metadata_record = tk.get_action('metadata_record_create')(context, data_dict)
            tk.h.redirect_to('metadata_record_read', id=metadata_record['id'],
                             organization_id=tk.c.organization['name'],
                             metadata_collection_id=tk.c.metadata_collection['name'])
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata record not found'))
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
            context['message'] = data_dict.get('log_message', '')
            context['allow_partial_update'] = True
            metadata_record = tk.get_action('metadata_record_update')(context, data_dict)
            tk.h.redirect_to('metadata_record_read', id=metadata_record['id'],
                             organization_id=tk.c.organization['name'],
                             metadata_collection_id=tk.c.metadata_collection['name'])
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata record not found'))
        except tk.NotAuthorized, e:
            tk.abort(403, e.message)
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)

    def _save_annotation_new(self, id, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            data_dict['id'] = id
            tk.get_action('metadata_record_workflow_annotation_create')(context, data_dict)
            tk.h.redirect_to('metadata_record_workflow', id=id,
                             organization_id=tk.c.organization['name'],
                             metadata_collection_id=tk.c.metadata_collection['name'])
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to add annotations to the metadata record'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata record not found'))
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.annotation_new(id, data_dict, errors, error_summary)

    def _save_annotation_edit(self, id, key, context):
        try:
            data_dict = clean_dict(dict_fns.unflatten(tuplize_dict(parse_params(tk.request.params))))
            data_dict['id'] = id
            tk.get_action('metadata_record_workflow_annotation_update')(context, data_dict)
            tk.h.redirect_to('metadata_record_workflow', id=id,
                             organization_id=tk.c.organization['name'],
                             metadata_collection_id=tk.c.metadata_collection['name'])
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to update annotations on the metadata record'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata record not found'))
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.annotation_edit(id, key, data_dict, errors, error_summary)

    @staticmethod
    def _elastic_update_index(id, organization_id, metadata_collection_id, context):
        try:
            tk.get_action('metadata_record_index_update')(context, {'id': id, 'async': False})
            tk.h.flash_notice(tk._('The metadata search index has been updated.'))
        except tk.NotAuthorized:
            tk.abort(403, tk._('Unauthorized to update the search index'))
        except tk.ObjectNotFound:
            tk.abort(404, tk._('Metadata record not found'))
        except tk.ValidationError as e:
            if e.error_dict and e.error_dict.get('message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            tk.h.flash_error(msg)
        tk.h.redirect_to('metadata_record_elastic', id=id, organization_id=organization_id, metadata_collection_id=metadata_collection_id)

    @staticmethod
    def _elastic_record_info(id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        try:
            record_dict = tk.get_action('metadata_record_index_show')(context, {'id': id})
            return {
                'exists': record_dict is not None,
                'record': json.dumps(record_dict, indent=2) if record_dict else '',
            }
        except tk.ValidationError, e:
            if e.error_dict and e.error_dict.get('message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            return {'error': msg}
