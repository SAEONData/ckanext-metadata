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

    def new_template(self):
        return  'infrastructure/new.html'

    def edit_template(self):
        return 'infrastructure/edit.html'

    def group_form(self):
        return 'infrastructure/new_group_form.html'

    def group_facets(self, facets_dict, group_type, package_type):
        if group_type == 'infrastructure':
            facets_dict['groups'] = tk._('Infrastructures')
        return facets_dict


class MetadataCollectionUIPlugin(p.SingletonPlugin, tk.DefaultGroupForm):
    """
    Plugin providing user interfaces for metadata_collection objects.
    """
    p.implements(p.IConfigurer)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IRoutes, inherit=True)

    def update_config(self, config):
        tk.add_template_directory(config, 'templates')

    def group_controller(self):
        return 'ckanext.metadata.controllers.metadata_collection:MetadataCollectionController'

    def group_types(self):
        return ['metadata_collection']

    def form_to_db_schema(self):
        return schema.metadata_collection_create_schema()

    def db_to_form_schema(self):
        return schema.metadata_collection_show_schema()

    def index_template(self):
        return 'metadata_collection/index.html'

    def read_template(self):
        return 'metadata_collection/read.html'

    def about_template(self):
        return 'metadata_collection/about.html'

    def activity_template(self):
        return 'metadata_collection/activity_stream.html'

    def new_template(self):
        return  'metadata_collection/new.html'

    def edit_template(self):
        return 'metadata_collection/edit.html'

    def group_form(self):
        return 'metadata_collection/new_group_form.html'

    def group_facets(self, facets_dict, group_type, package_type):
        if group_type == 'metadata_collection':
            facets_dict['groups'] = tk._('Metadata Collections')
        return facets_dict

    def after_map(self, map):
        """
        Replace the routes that are automatically set up for our group type, because we want metadata
        collections to be accessible under their respective organizations rather than at the top level.
        """
        metadata_collection_routes = [route for route in map.matchlist if route.name and route.name.startswith('metadata_collection_')]
        for route in metadata_collection_routes:
            kwargs = {'controller': route.defaults['controller'],
                      'ckan_icon': tk.config['routes.named_routes'][route.name]['icon']}
            if 'action' in route.defaults:
                kwargs['action'] = route.defaults['action']
            if route.reqs:
                kwargs['requirements'] = route.reqs
            map.connect(route.name, '/organization/{organization_id}' + route.routepath, **kwargs)
            map.matchlist.remove(route)
        return map
