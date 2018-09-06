# encoding: utf-8

import logging
import requests

from ckan.common import config

log = logging.getLogger(__name__)


def _call_agent(func, **kwargs):
    search_agent_url = config.get('ckan.metadata.elastic.search_agent_url')
    url = search_agent_url + '/' + func
    response = requests.post(url, data=kwargs)
    response.raise_for_status()
    result = response.json()
    if not result['success']:
        raise Exception(result['msg'])


def initialize_index(index_name, metadata_template_json):
    _call_agent('create_index', index=index_name, metadata_json=metadata_template_json)


def push_record(index_name, record_id, metadata_json, organization, collection, infrastructures):
    _call_agent('add', index=index_name, record_id=record_id, metadata_json=metadata_json,
                organization=organization, collection=collection, infrastructures=infrastructures)


def delete_record(index_name, record_id):
    _call_agent('delete', index=index_name, record_id=record_id)
