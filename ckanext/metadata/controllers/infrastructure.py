# encoding: utf-8

import ckan.plugins.toolkit as tk
from ckan import model
from ckan.common import _


class InfrastructureController(tk.BaseController):

    items_per_page = 20

    def index(self):
        context = {'model': model, 'session': model.Session,
                   'user': tk.c.user, 'auth_user_obj': tk.c.userobj,
                   'for_view': True}
        data_dict = {'all_fields': True}
        tk.c.infrastructures = tk.get_action('infrastructure_list')(context, data_dict)
        return tk.render('infrastructure/index.html')

    def read(self, id):
        tk.c.infrastructure = self._get_infrastructure_dict(id)
        return tk.render('infrastructure/read.html')

    def new(self):
        pass

    def edit(self, id):
        pass

    def delete(self, id):
        pass

    def about(self, id):
        tk.c.infrastructure = self._get_infrastructure_dict(id)
        return tk.render('infrastructure/about.html')

    def activity(self, id, offset=0):
        context = {'model': model, 'session': model.Session,
                   'user': tk.c.user, 'auth_user_obj': tk.c.userobj,
                   'for_view': True}
        tk.c.infrastructure = self._get_infrastructure_dict(id)
        try:
            tk.c.group_activity_stream = tk.get_action('group_activity_list_html')(context, {'id': id, 'offset': offset})
        except tk.ValidationError:
            tk.abort(400)
        return tk.render('infrastructure/activity_stream.html')

    @staticmethod
    def _get_infrastructure_dict(id):
        context = {'model': model, 'session': model.Session,
                   'user': tk.c.user, 'auth_user_obj': tk.c.userobj,
                   'for_view': True}
        try:
            return tk.get_action('infrastructure_show')(context, {'id': id})
        except (tk.ObjectNotFound, tk.NotAuthorized):
            tk.abort(404, '%s: %s' % (_('Not found'), _('Infrastructure')))
