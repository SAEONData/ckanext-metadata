# encoding: utf-8

import re

import ckan.plugins.toolkit as tk
from ckan.controllers.group import GroupController
from ckan.lib.render import TemplateNotFound
import ckan.model as model
import ckan.lib.helpers as helpers


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

    def _get_org_dict(self, organization_id):
        context = {'model': model, 'session': model.Session, 'user': tk.c.user}
        data_dict = {'id': organization_id}
        try:
            return tk.get_action('organization_show')(context, data_dict)
        except tk.NotFound:
            tk.abort(404, tk._('Group not found'))
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))

    def index(self, organization_id):
        """
        Copied from GroupController.index() with some modifications.
        """
        tk.c.org_dict = self._get_org_dict(organization_id)

        page = tk.h.get_page_number(tk.request.params) or 1
        items_per_page = 21

        context = {'model': model, 'session': model.Session,
                   'user': tk.c.user, 'for_view': True,
                   'with_private': False}

        q = tk.c.q = tk.request.params.get('q', '')
        sort_by = tk.c.sort_by_selected = tk.request.params.get('sort')
        try:
            tk.check_access('site_read', context)
            tk.check_access('metadata_collection_list', context)
        except tk.NotAuthorized:
            tk.abort(403, tk._('Not authorized to see this page'))

        if tk.c.userobj:
            context['user_id'] = tk.c.userobj.id
            context['user_is_admin'] = tk.c.userobj.sysadmin

        try:
            data_dict_global_results = {
                'owner_org': organization_id,
                'all_fields': False,
                'q': q,
                'sort': sort_by,
                'type': 'metadata_collection',
            }
            global_results = tk.get_action('metadata_collection_list')(context, data_dict_global_results)
        except tk.ValidationError as e:
            if e.error_dict and e.error_dict.get('message'):
                msg = e.error_dict['message']
            else:
                msg = str(e)
            tk.h.flash_error(msg)
            tk.c.page = helpers.Page([], 0)
            return tk.render(self._index_template('metadata_collection'),
                             extra_vars={'group_type': 'metadata_collection'})

        data_dict_page_results = {
            'owner_org': organization_id,
            'all_fields': True,
            'q': q,
            'sort': sort_by,
            'type': 'metadata_collection',
            'limit': items_per_page,
            'offset': items_per_page * (page - 1),
            'include_extras': True
        }
        page_results = tk.get_action('metadata_collection_list')(context, data_dict_page_results)

        tk.c.page = helpers.Page(
            collection=global_results,
            page=page,
            url=tk.h.pager_url,
            items_per_page=items_per_page,
        )

        tk.c.page.items = page_results
        return tk.render(self._index_template('metadata_collection'),
                         extra_vars={'group_type': 'metadata_collection'})

    def read(self, organization_id, id, limit=20):
        tk.c.org_dict = self._get_org_dict(organization_id)
        return super(MetadataCollectionController, self).read(id, limit)

    def activity(self, organization_id, id, offset=0):
        tk.c.org_dict = self._get_org_dict(organization_id)
        return super(MetadataCollectionController, self).activity(id, offset)

    def about(self, organization_id, id):
        tk.c.org_dict = self._get_org_dict(organization_id)
        return super(MetadataCollectionController, self).about(id)
