# encoding: utf-8

import factory

import ckan.model as ckan_model
import ckanext.metadata.model as ckanext_model
from ckan.tests import helpers, factories as ckan_factories


class MetadataCollection(factory.Factory):
    FACTORY_FOR = ckan_model.Group

    name = factory.Sequence(lambda n: 'test_collection_{0:02d}'.format(n))
    title = factory.LazyAttribute(ckan_factories._generate_group_title)
    description = 'A test description for this test metadata collection.'
    doi_collection = 'TEST.DOI'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}
        org_kwargs = {}
        if 'user' in kwargs:
            org_kwargs['user'] = kwargs['user']
        organization_id = kwargs.pop('organization_id', None) or ckan_factories.Organization(**org_kwargs)['id']

        return helpers.call_action('metadata_collection_create',
                                   context=context,
                                   organization_id=organization_id,
                                   **kwargs)


class MetadataRecord(factory.Factory):
    FACTORY_FOR = ckan_model.Package

    title = 'Test Metadata Record'
    metadata_json = factory.Sequence(lambda n: '{{ "testkey": "testvalue{0:02d}" }}'.format(n))
    doi = factory.Sequence(lambda n: '10.12345/{:03d}'.format(n))

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}
        organization_id = kwargs.pop('owner_org', None) or ckan_factories.Organization()['id']
        metadata_collection_id = kwargs.pop('metadata_collection_id', None) \
                                 or MetadataCollection(organization_id=organization_id)['id']
        metadata_standard_id = kwargs.pop('metadata_standard_id', None) or MetadataStandard()['id']

        package_dict = helpers.call_action('metadata_record_create',
                                           context=context,
                                           owner_org=organization_id,
                                           metadata_collection_id=metadata_collection_id,
                                           metadata_standard_id=metadata_standard_id,
                                           **kwargs)
        return package_dict


class MetadataStandard(factory.Factory):
    FACTORY_FOR = ckanext_model.MetadataStandard

    standard_name = factory.Sequence(lambda n: 'test_standard_{0:02d}'.format(n))
    standard_version = '1.0'
    parent_standard_id = ''
    metadata_template_json = '{ "testkey": "testvalue" }'
    description = 'A test description for this test metadata standard.'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}

        return helpers.call_action('metadata_standard_create', context=context, **kwargs)


class MetadataSchema(factory.Factory):
    FACTORY_FOR = ckanext_model.MetadataSchema

    description = 'A test description for this test metadata schema.'
    schema_json = '{"type": "object"}'
    organization_id = ''
    infrastructure_id = ''

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}
        metadata_standard_id = kwargs.pop('metadata_standard_id', None) or MetadataStandard()['id']

        return helpers.call_action('metadata_schema_create',
                                   context=context,
                                   metadata_standard_id=metadata_standard_id,
                                   **kwargs)


class Infrastructure(factory.Factory):
    FACTORY_FOR = ckan_model.Group

    name = factory.Sequence(lambda n: 'test_infrastructure_{0:02d}'.format(n))
    title = factory.LazyAttribute(ckan_factories._generate_group_title)
    description = 'A test description for this test infrastructure.'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}

        return helpers.call_action('infrastructure_create', context=context, **kwargs)


class WorkflowState(factory.Factory):
    FACTORY_FOR = ckanext_model.WorkflowState

    name = factory.Sequence(lambda n: 'test_workflow_state_{0:02d}'.format(n))
    title = factory.LazyAttribute(lambda obj: obj.name.replace('_', ' ').title())
    description = 'A test description for this test workflow state.'
    revert_state_id = ''
    metadata_records_private = False
    workflow_rules_json = '{"type": "object"}'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}

        return helpers.call_action('workflow_state_create', context=context, **kwargs)


class WorkflowTransition(factory.Factory):
    FACTORY_FOR = ckanext_model.WorkflowTransition

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}
        # don't do shortcut evaluation for from_state_id because it can be ''
        from_state_id = kwargs.pop('from_state_id', None)
        if from_state_id is None:
            from_state_id = WorkflowState()['id']
        to_state_id = kwargs.pop('to_state_id', None) or WorkflowState()['id']

        return helpers.call_action('workflow_transition_create',
                                   context=context,
                                   from_state_id=from_state_id,
                                   to_state_id=to_state_id,
                                   **kwargs)


class WorkflowAnnotation(factory.Factory):
    FACTORY_FOR = ckanext_model.WorkflowAnnotation

    name = factory.Sequence(lambda n: 'test_workflow_annotation_{0:02d}'.format(n))
    attributes = '{"attr1": "string"}'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}

        return helpers.call_action('workflow_annotation_create', context=context, **kwargs)


class MetadataJSONAttrMap(factory.Factory):
    FACTORY_FOR = ckanext_model.MetadataJSONAttrMap

    json_path = '/a/b'
    record_attr = 'name'
    is_key = True

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}
        metadata_standard_id = kwargs.pop('metadata_standard_id', None) or MetadataStandard(
            metadata_template_json='{"a": {"b": "foo"}, "c": {"d": "bar"}}')['id']

        return helpers.call_action('metadata_json_attr_map_create',
                                   context=context,
                                   metadata_standard_id=metadata_standard_id,
                                   **kwargs)
