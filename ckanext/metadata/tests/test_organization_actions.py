# encoding: utf-8

from ckan import model as ckan_model
from ckan.plugins import toolkit as tk
from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import call_action

from ckanext.metadata import model as ckanext_model
from ckanext.metadata.tests import (
    ActionTestBase,
    assert_error,
    factories as ckanext_factories,
)


class TestOrganizationActions(ActionTestBase):

    # TODO: most of these tests will not work, as chaining of action functions is broken in CKAN
    # and therefore we cannot correctly implement our organization_delete override

    def test_delete_valid(self):
        organization = ckan_factories.Organization()
        self._test_action('delete', 'organization',
                          model_class=ckan_model.Group,
                          id=organization['id'])

    def test_delete_valid_cascade_metadata_models(self):
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])

        self._test_action('delete', 'organization',
                          model_class=ckan_model.Group,
                          id=organization['id'])
        assert ckanext_model.MetadataModel.get(metadata_model['id']).state == 'deleted'

    def test_delete_valid_cascade_metadata_collections(self):
        organization = ckan_factories.Organization()
        metadata_collection = ckanext_factories.MetadataCollection(organization_id=organization['id'])

        self._test_action('delete', 'organization',
                          model_class=ckan_model.Group,
                          id=organization['id'])
        assert ckan_model.Group.get(metadata_collection['id']).state == 'deleted'

    def test_delete_with_dependent_metadata_records(self):
        organization = ckan_factories.Organization()
        metadata_collection = ckanext_factories.MetadataCollection(organization_id=organization['id'])
        metadata_record = ckanext_factories.MetadataRecord(owner_org=organization['id'],
                                                           metadata_collection_id=metadata_collection['id'])

        result, obj = self._test_action('delete', 'organization',
                                        exception_class=tk.ValidationError,
                                        id=organization['id'])
        assert_error(result, 'message', 'Organization has dependent metadata records')

        call_action('metadata_record_delete', id=metadata_record['id'])
        self._test_action('delete', 'organization',
                          model_class=ckan_model.Group,
                          id=organization['id'])
        assert ckan_model.Group.get(metadata_collection['id']).state == 'deleted'

    def test_delete_with_dependent_metadata_models(self):
        # TODO: this test will work once we have metadata models being referenced for validation
        organization = ckan_factories.Organization()
        metadata_model = ckanext_factories.MetadataModel(organization_id=organization['id'])

        # add validation objects here
        result, obj = self._test_action('delete', 'organization',
                                        exception_class=tk.ValidationError,
                                        id=organization['id'])
        assert_error(result, 'message', 'Organization has dependent metadata models that are in use')

        # delete validation objects here
        self._test_action('delete', 'organization',
                          model_class=ckan_model.Group,
                          id=organization['id'])
        assert ckanext_model.MetadataModel.get(metadata_model['id']).state == 'deleted'