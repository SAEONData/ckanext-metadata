# encoding: utf-8

import logging
import requests

from ckan.common import config

log = logging.getLogger(__name__)


def initialize_index(index_name, template_record_json):
    search_agent_url = config.get('ckan.metadata.elastic.search_agent_url')
    url = search_agent_url + '/initialize'
    payload = {
        'index_name': index_name,
        'record': template_record_json,
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    result = response.json()


def push_record(index_name, record_json):
    search_agent_url = config.get('ckan.metadata.elastic.search_agent_url')
    url = search_agent_url + '/add'
    payload = {
        'index_name': index_name,
        'record': record_json,
    }
    response = requests.post(url, data=payload)
    response.raise_for_status()
    result = response.json()


def delete_record(record_id):
    search_agent_url = config.get('ckan.metadata.elastic.search_agent_url')
