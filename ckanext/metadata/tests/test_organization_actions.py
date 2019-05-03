# encoding: utf-8

from ckan import model as ckan_model
from ckan.tests import factories as ckan_factories
from ckan.tests.helpers import call_action

from ckanext.metadata import model as ckanext_model
from ckanext.metadata.tests import (
    ActionTestBase,
    assert_error,
    factories as ckanext_factories,
    assert_object_matches_dict,
)


class TestOrganizationActions(ActionTestBase):

    def _generate_organization(self, **kwargs):
        return ckan_factories.Organization(user=self.normal_user, **kwargs)

    def _generate_metadata_collection(self, **kwargs):
        return ckanext_factories.MetadataCollection(user=self.normal_user, **kwargs)

    def test_create_valid(self):
        input_dict = {
            'name': 'test-organization',
            'title': 'Test Organization',
            'description': 'This is a test organization',
        }
        result, obj = self.test_action('organization_create', **input_dict)
        assert obj.type == 'organization'
        assert obj.is_organization == True
        assert_object_matches_dict(obj, input_dict)

        default_collection = ckan_model.Session.query(ckan_model.Group) \
            .join(ckan_model.GroupExtra) \
            .filter_by(key='organization_id', value=obj.id) \
            .first()
        assert default_collection
        assert default_collection.name == input_dict['name'] + '-metadata'

    def test_delete_valid(self):
        organization = self._generate_organization()
        self.test_action('organization_delete',
                         id=organization['id'])

    def test_delete_valid_cascade_metadata_schemas(self):
        organization = self._generate_organization()
        metadata_schema = ckanext_factories.MetadataSchema(organization_id=organization['id'])

        self.test_action('organization_delete',
                         id=organization['id'])
        assert ckanext_model.MetadataSchema.get(metadata_schema['id']).state == 'deleted'

    def test_delete_valid_cascade_metadata_collections(self):
        organization = self._generate_organization()
        metadata_collection = self._generate_metadata_collection(organization_id=organization['id'])

        self.test_action('organization_delete',
                         id=organization['id'])
        assert ckan_model.Group.get(metadata_collection['id']).state == 'deleted'

    def test_delete_with_dependencies(self):
        organization = self._generate_organization()
        metadata_collection = self._generate_metadata_collection(organization_id=organization['id'])
        metadata_schema = ckanext_factories.MetadataSchema(organization_id=organization['id'])
        metadata_record = ckanext_factories.MetadataRecord(owner_org=organization['id'],
                                                           metadata_collection_id=metadata_collection['id'])

        result, obj = self.test_action('organization_delete', should_error=True,
                                       id=organization['id'])
        assert_error(result, 'message', 'Organization has dependent metadata records')
        assert ckan_model.Group.get(metadata_collection['id']).state == 'active'
        assert ckanext_model.MetadataSchema.get(metadata_schema['id']).state == 'active'

        call_action('metadata_record_delete', id=metadata_record['id'])
        self.test_action('organization_delete',
                         id=organization['id'])
        assert ckan_model.Group.get(metadata_collection['id']).state == 'deleted'
        assert ckanext_model.MetadataSchema.get(metadata_schema['id']).state == 'deleted'
