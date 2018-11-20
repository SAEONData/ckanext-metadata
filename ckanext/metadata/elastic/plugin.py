# encoding: utf-8

import ckan.plugins as p
import ckanext.metadata.elastic.action as action


class ElasticSearchPlugin(p.SingletonPlugin):
    """
    Provides integration with the Elastic search agent.
    """
    p.implements(p.IActions)
    p.implements(p.IConfigurable)

    def get_actions(self):
        return {
            'metadata_standard_index_create': action.metadata_standard_index_create,
            'metadata_standard_index_delete': action.metadata_standard_index_delete,
            'metadata_record_index_update': action.metadata_record_index_update,
            'organization_update': action.organization_update,
            'infrastructure_update': action.infrastructure_update,
            'metadata_collection_update': action.metadata_collection_update,
        }

    def configure(self, config):
        if not config.get('ckan.metadata.elastic.search_agent_url'):
            raise Exception('Config option ckan.metadata.elastic.search_agent_url has not been set')
