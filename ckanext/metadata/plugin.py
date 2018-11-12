# encoding: utf-8

import logging

import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckanext.metadata.logic import schema

log = logging.getLogger(__name__)


class MetadataFrameworkPlugin(p.SingletonPlugin):
    """
    Plugin providing CRUDs and APIs for metadata framework entities.
    """
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    def get_actions(self):
        return self._get_logic_functions('ckanext.metadata.logic.action')

    def get_auth_functions(self):
        return self._get_logic_functions('ckanext.metadata.logic.auth')

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


class InfrastructureUIPlugin(p.SingletonPlugin, tk.DefaultGroupForm):
    """
    Plugin providing user interfaces for infrastructure objects.
    """
    p.implements(p.IConfigurer)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IFacets, inherit=True)

    def update_config(self, config):
        tk.add_template_directory(config, 'templates')

    def group_controller(self):
        return 'ckanext.metadata.controllers.infrastructure:InfrastructureController'

    def group_types(self):
        return ['infrastructure']

    def form_to_db_schema(self):
        return schema.infrastructure_create_schema()

    def db_to_form_schema(self):
        return schema.infrastructure_show_schema()

    def index_template(self):
        return 'infrastructure/index.html'

    def read_template(self):
        return 'infrastructure/read.html'

    def about_template(self):
        return 'infrastructure/about.html'

    def activity_template(self):
        return 'infrastructure/activity_stream.html'

    def group_facets(self, facets_dict, group_type, package_type):
        if group_type == 'infrastructure':
            facets_dict['groups'] = tk._('Infrastructures')
        return facets_dict
