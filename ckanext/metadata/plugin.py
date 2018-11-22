# encoding: utf-8

import ckan.plugins as p
import ckan.plugins.toolkit as tk


class MetadataFrameworkPlugin(p.SingletonPlugin, tk.DefaultGroupForm):

    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)
    p.implements(p.IConfigurer)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IRoutes)

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

    def update_config(self, config):
        tk.add_template_directory(config, 'templates')
        tk.add_public_directory(config, 'public')

    def group_controller(self):
        return 'ckanext.metadata.controllers.metadata_collection:MetadataCollectionController'

    def group_types(self):
        return ['metadata_collection']

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

    def before_map(self, map):
        controller = 'ckanext.metadata.controllers.metadata_standard:MetadataStandardController'
        map.connect('metadata_standard_index', '/metadata_standard', controller=controller, action='index')
        map.connect('metadata_standard_new', '/metadata_standard/new', controller=controller, action='new')

        controller = 'ckanext.metadata.controllers.workflow_state:WorkflowStateController'
        map.connect('workflow_state_index', '/workflow_state', controller=controller, action='index')

        return map

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

        # icons are not correctly set for automatically generated plugin routes, so we do it here
        tk.config['routes.named_routes']['metadata_collection_read']['icon'] = 'sitemap'
        tk.config['routes.named_routes']['metadata_collection_index']['icon'] = 'folder-open'

        return map


class InfrastructureUIPlugin(p.SingletonPlugin, tk.DefaultGroupForm):
    """
    Plugin providing user interfaces for infrastructure-type group objects.

    This must be a standalone plugin, since the MetadataFrameworkPlugin already implements
    IGroupForm for metadata collections. This separation also allows for metadata platforms
    which do not need to use infrastructure objects to exclude them from the UI.
    """
    p.implements(p.IConfigurer)
    p.implements(p.IGroupForm, inherit=True)
    p.implements(p.IFacets, inherit=True)
    p.implements(p.IRoutes, inherit=True)

    def update_config(self, config):
        tk.add_template_directory(config, 'templates')

    def group_controller(self):
        return 'ckanext.metadata.controllers.infrastructure:InfrastructureController'

    def group_types(self):
        return ['infrastructure']

    def index_template(self):
        return 'infrastructure/index.html'

    def read_template(self):
        return 'infrastructure/read.html'

    def about_template(self):
        return 'infrastructure/about.html'

    def activity_template(self):
        return 'infrastructure/activity_stream.html'

    def new_template(self):
        return 'infrastructure/new.html'

    def edit_template(self):
        return 'infrastructure/edit.html'

    def group_form(self):
        return 'infrastructure/new_group_form.html'

    def group_facets(self, facets_dict, group_type, package_type):
        if group_type == 'infrastructure':
            facets_dict['groups'] = tk._('Infrastructures')
        return facets_dict

    def after_map(self, map):
        # icons are not correctly set for automatically generated plugin routes, so we do it here
        tk.config['routes.named_routes']['infrastructure_read']['icon'] = 'sitemap'
        return map
