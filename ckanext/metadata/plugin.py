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
        controller = 'ckanext.metadata.controllers.organization:OrganizationController'
        map.connect('organization_datasets', '/organization/datasets/{id}', controller=controller, action='datasets', ckan_icon='site-map')

        controller = 'ckanext.metadata.controllers.metadata_record:MetadataRecordController'
        map.connect('metadata_record_index', '/organization/{organization_id}/metadata_collection/{metadata_collection_id}/metadata_record', controller=controller, action='index')
        map.connect('metadata_record_new', '/organization/{organization_id}/metadata_collection/{metadata_collection_id}/metadata_record/new', controller=controller, action='new')
        map.connect('metadata_record_edit', '/organization/{organization_id}/metadata_collection/{metadata_collection_id}/metadata_record/edit/{id}', controller=controller, action='edit', ckan_icon='pencil-square-o')
        map.connect('metadata_record_delete', '/organization/{organization_id}/metadata_collection/{metadata_collection_id}/metadata_record/delete/{id}', controller=controller, action='delete')
        map.connect('metadata_record_read', '/organization/{organization_id}/metadata_collection/{metadata_collection_id}/metadata_record/{id}', controller=controller, action='read', ckan_icon='file-text-o')
        map.connect('metadata_record_activity', '/organization/{organization_id}/metadata_collection/{metadata_collection_id}/metadata_record/activity/{id}', controller=controller, action='activity', ckan_icon='clock-o')
        map.connect('metadata_record_status', '/organization/{organization_id}/metadata_collection/{metadata_collection_id}/metadata_record/status/{id}', controller=controller, action='status', ckan_icon='info-circle')
        map.connect('metadata_record_validation', '/organization/{organization_id}/metadata_collection/{metadata_collection_id}/metadata_record/validation/{id}', controller=controller, action='validation', ckan_icon='check-square-o')
        map.connect('metadata_record_workflow', '/organization/{organization_id}/metadata_collection/{metadata_collection_id}/metadata_record/workflow/{id}', controller=controller, action='workflow', ckan_icon='caret-square-o-right')

        controller = 'ckanext.metadata.controllers.metadata_standard:MetadataStandardController'
        map.connect('metadata_standard_index', '/metadata_standard', controller=controller, action='index')
        map.connect('metadata_standard_new', '/metadata_standard/new', controller=controller, action='new')
        map.connect('metadata_standard_edit', '/metadata_standard/edit/{id}', controller=controller, action='edit', ckan_icon='pencil-square-o')
        map.connect('metadata_standard_delete', '/metadata_standard/delete/{id}', controller=controller, action='delete')
        map.connect('metadata_standard_read', '/metadata_standard/{id}', controller=controller, action='read', ckan_icon='file-text-o')
        map.connect('metadata_standard_about', '/metadata_standard/about/{id}', controller=controller, action='about', ckan_icon='info-circle')
        map.connect('metadata_standard_activity', '/metadata_standard/activity/{id}', controller=controller, action='activity', ckan_icon='clock-o')
        map.connect('metadata_standard_attr_maps', '/metadata_standard/attr_maps/{id}', controller=controller, action='attr_maps', ckan_icon='random')
        map.connect('/metadata_standard/attr_map_new/{id}', controller=controller, action='attr_map_new')
        map.connect('/metadata_standard/attr_map_edit/{id}/{attr_map_id}', controller=controller, action='attr_map_edit')
        map.connect('/metadata_standard/attr_map_delete/{id}/{attr_map_id}', controller=controller, action='attr_map_delete')

        controller = 'ckanext.metadata.controllers.metadata_schema:MetadataSchemaController'
        map.connect('metadata_schema_index', '/metadata_standard/{metadata_standard_id}/metadata_schema', controller=controller, action='index')
        map.connect('metadata_schema_new', '/metadata_standard/{metadata_standard_id}/metadata_schema/new', controller=controller, action='new')
        map.connect('metadata_schema_edit', '/metadata_standard/{metadata_standard_id}/metadata_schema/edit/{id}', controller=controller, action='edit', ckan_icon='pencil-square-o')
        map.connect('metadata_schema_delete', '/metadata_standard/{metadata_standard_id}/metadata_schema/delete/{id}', controller=controller, action='delete')
        map.connect('metadata_schema_read', '/metadata_standard/{metadata_standard_id}/metadata_schema/{id}', controller=controller, action='read', ckan_icon='file-text-o')
        map.connect('metadata_schema_about', '/metadata_standard/{metadata_standard_id}/metadata_schema/about/{id}', controller=controller, action='about', ckan_icon='info-circle')
        map.connect('metadata_schema_activity', '/metadata_standard/{metadata_standard_id}/metadata_schema/activity/{id}', controller=controller, action='activity', ckan_icon='clock-o')

        controller = 'ckanext.metadata.controllers.workflow_state:WorkflowStateController'
        map.connect('workflow_state_index', '/workflow_state', controller=controller, action='index')
        map.connect('workflow_state_new', '/workflow_state/new', controller=controller, action='new')
        map.connect('workflow_state_edit', '/workflow_state/edit/{id}', controller=controller, action='edit', ckan_icon='pencil-square-o')
        map.connect('workflow_state_delete', '/workflow_state/delete/{id}', controller=controller, action='delete')
        map.connect('workflow_state_read', '/workflow_state/{id}', controller=controller, action='read', ckan_icon='file-text-o')
        map.connect('workflow_state_about', '/workflow_state/about/{id}', controller=controller, action='about', ckan_icon='info-circle')
        map.connect('workflow_state_activity', '/workflow_state/activity/{id}', controller=controller, action='activity', ckan_icon='clock-o')

        controller = 'ckanext.metadata.controllers.workflow_transition:WorkflowTransitionController'
        map.connect('workflow_transition_index', '/workflow_transition', controller=controller, action='index')
        map.connect('workflow_transition_new', '/workflow_transition/new', controller=controller, action='new')
        map.connect('workflow_transition_delete', '/workflow_transition/delete/{id}', controller=controller, action='delete')

        controller = 'ckanext.metadata.controllers.workflow_annotation:WorkflowAnnotationController'
        map.connect('workflow_annotation_index', '/workflow_annotation', controller=controller, action='index')
        map.connect('workflow_annotation_new', '/workflow_annotation/new', controller=controller, action='new')
        map.connect('workflow_annotation_edit', '/workflow_annotation/edit/{id}', controller=controller, action='edit')
        map.connect('workflow_annotation_delete', '/workflow_annotation/delete/{id}', controller=controller, action='delete')

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
        tk.config['routes.named_routes']['organization_datasets']['icon'] = 'sitemap'

        # re-route organization_read to our controller
        org_read_routes = [route for route in map.matchlist if route.name and route.name == 'organization_read']
        for route in org_read_routes:
            map.matchlist.remove(route)
        controller = 'ckanext.metadata.controllers.organization:OrganizationController'
        map.connect('organization_read', '/organization/{id}', controller=controller, action='read', ckan_icon='folder-open')

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
