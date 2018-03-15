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

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}
        organization_id = kwargs.pop('organization_id', None) or ckan_factories.Organization()['id']

        return helpers.call_action('metadata_collection_create',
                                   context=context,
                                   organization_id=organization_id,
                                   **kwargs)


class MetadataRecord(factory.Factory):
    FACTORY_FOR = ckan_model.Package

    name = factory.Sequence(lambda n: 'test_record_{0:02d}'.format(n))
    title = 'Test Metadata Record'
    content_json = '{ "testkey": "testvalue" }'
    content_raw = '<xml/>'
    content_url = 'http://example.net/'
    infrastructures = []

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}

        if {'schema_name', 'schema_version'}.issubset(kwargs):
            metadata_schema = ckanext_model.MetadataSchema.lookup(
                kwargs.pop('schema_name'), kwargs.pop('schema_version'))
        else:
            metadata_schema = ckanext_model.MetadataSchema.get(MetadataSchema()['id'])

        organization_id = kwargs.pop('owner_org', None) or ckan_factories.Organization()['id']
        metadata_collection_id = kwargs.pop('metadata_collection_id', None) \
                                 or MetadataCollection(organization_id=organization_id)['id']

        package_dict = helpers.call_action('metadata_record_create',
                                           context=context,
                                           owner_org=organization_id,
                                           metadata_collection_id=metadata_collection_id,
                                           schema_name=metadata_schema.schema_name,
                                           schema_version=metadata_schema.schema_version,
                                           **kwargs)
        return package_dict


class MetadataSchema(factory.Factory):
    FACTORY_FOR = ckanext_model.MetadataSchema

    schema_name = factory.Sequence(lambda n: 'test_schema_{0:02d}'.format(n))
    schema_version = '1.0'
    schema_xsd = '<xsd/>'
    base_schema_id = ''
    title = factory.LazyAttribute(lambda obj: obj.schema_name.replace('_', ' ').title())
    description = 'A test description for this test metadata schema.'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        context = {'user': ckan_factories._get_action_user_name(kwargs)}

        return helpers.call_action('metadata_schema_create', context=context, **kwargs)


class MetadataModel(factory.Factory):
    FACTORY_FOR = ckanext_model.MetadataModel

    title = factory.Sequence(lambda n: 'Test Metadata Model {0:02d}'.format(n))
    description = 'A test description for this test metadata model.'
    model_json = '{ "testkey": "testvalue" }'
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
        metadata_schema_id = kwargs.pop('metadata_schema_id', None) or MetadataSchema()['id']

        return helpers.call_action('metadata_model_create',
                                   context=context,
                                   metadata_schema_id=metadata_schema_id,
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
