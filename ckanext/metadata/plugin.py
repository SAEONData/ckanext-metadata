# encoding: utf-8

import logging
import ckan.plugins as p
import ckan.plugins.toolkit as tk

log = logging.getLogger(__name__)


class MetadataFrameworkPlugin(p.SingletonPlugin):
    """
    Plugin providing CRUDs and APIs for metadata framework entities.
    """
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)
    p.implements(p.IRoutes, inherit=True)

    def get_actions(self):
        return self._get_logic_functions('ckanext.metadata.logic.action')

    def get_auth_functions(self):
        return self._get_logic_functions('ckanext.metadata.logic.auth')

    def update_config(self, config):
        tk.add_template_directory(config, 'templates')

    def get_helpers(self):
        return {}

    def before_map(self, map):
        map.redirect('/infrastructures', '/infrastructure')
        map.redirect('/infrastructures/{url:.*}', '/infrastructure/{url}')

        with map.submapper(controller='ckanext.metadata.controllers.infrastructure:InfrastructureController',
                           path_prefix='/infrastructure') as m:
            m.index()
            m.connect('infrastructure_new', '/new', action='new')
            m.connect('infrastructure_read', '/{id}', action='read', ckan_icon='sitemap')
            m.connect('infrastructure_edit', '/edit/{id}', action='edit')
            m.connect('infrastructure_delete', '/delete/{id}', action='delete')
            m.connect('infrastructure_about', '/about/{id}', action='about', ckan_icon='info-circle'),
            m.connect('infrastructure_activity', '/activity/{id}/{offset}', action='activity', ckan_icon='clock-o'),

        return map

    @staticmethod
    def _get_logic_functions(module_root):

        logic_functions = {}

        for module_name in ['get', 'create', 'update', 'delete']:
            module_path = '%s.%s' % (module_root, module_name,)
            module = __import__(module_path)
            for part in module_path.split('.')[1:]:
                module = getattr(module, part)

            for key, value in module.__dict__.items():
                if not key.startswith('_') and hasattr(value, '__call__') and value.__module__ == module_path:
                    logic_functions[key] = value

        return logic_functions
