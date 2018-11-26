# encoding: utf-8

import ckan.plugins.toolkit as tk
import ckan.model as model
import ckan.lib.helpers as helpers
from ckan.controllers.organization import OrganizationController as CKANOrganizationController


class OrganizationController(CKANOrganizationController):

    def read(self, id):
        """
        Change the default read page for organizations to be a metadata collection listing
        instead of a dataset listing.
        """
        context = {'model': model, 'session': model.Session, 'user': tk.c.user, 'for_view': True}
        page = tk.h.get_page_number(tk.request.params) or 1
        items_per_page = 21

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

        tk.c.group_dict = tk.c.org_dict = tk.get_action('organization_show')(context, {'id': id})
        try:
            data_dict_global_results = {
                'owner_org': id,
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
            return tk.render('organization/metadata_collections.html')

        data_dict_page_results = {
            'owner_org': id,
            'all_fields': True,
            'q': q,
            'sort': sort_by,
            'limit': items_per_page,
            'offset': items_per_page * (page - 1),
        }
        page_results = tk.get_action('metadata_collection_list')(context, data_dict_page_results)

        tk.c.page = helpers.Page(
            collection=global_results,
            page=page,
            url=tk.h.pager_url,
            items_per_page=items_per_page,
        )

        tk.c.page.items = page_results
        return tk.render('organization/metadata_collections.html')

    def datasets(self, id):
        return super(OrganizationController, self).read(id)
