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

    def read(self, id, limit=20, organization_id=None):
        self._set_organization_context(organization_id)
        return super(MetadataCollectionController, self).read(id, limit)

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
            context['message'] = data_dict.get('log_message', '')
            data_dict['users'] = [{'name': tk.c.user, 'capacity': 'admin'}]
            group = tk.get_action('metadata_collection_create')(context, data_dict)
            tk.h.redirect_to('metadata_collection_read', id=group['name'], organization_id=tk.c.org_dict['name'])
        except (tk.ObjectNotFound, tk.NotAuthorized), e:
            tk.abort(404, tk._('Group not found'))
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
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id
            context['allow_partial_update'] = True
            group = tk.get_action('metadata_collection_update')(context, data_dict)
            if id != group['name']:
                self._force_reindex(group)
            tk.h.redirect_to('metadata_collection_read', id=group['name'], organization_id=tk.c.org_dict['name'])
        except (tk.ObjectNotFound, tk.NotAuthorized), e:
            tk.abort(404, tk._('Group not found'))
        except dict_fns.DataError:
            tk.abort(400, tk._(u'Integrity Error'))
        except tk.ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)
