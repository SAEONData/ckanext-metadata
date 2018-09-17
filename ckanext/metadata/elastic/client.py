# encoding: utf-8

import logging
import requests
from celery import Celery

from ckan.common import config

app = Celery('client',
             broker='pyamqp://localhost',
             include=['ckanext.metadata.elastic.client'])

log = logging.getLogger(__name__)


@app.task
def _call_agent(url, **kwargs):
    response = requests.post(url, data=kwargs)
    response.raise_for_status()
    result = response.json()
    # note: exceptions are lost for async calls as we're not currently using a results backend
    # todo: for synchronous calls exception handling needs to be improved; this causes internal server error
    if not result['success']:
        raise Exception(result['msg'])


def _search_agent_url():
    return config.get('ckan.metadata.elastic.search_agent_url')


# synchronous
def initialize_index(index_name, metadata_template_json):
    url = _search_agent_url() + '/create_index'
    _call_agent(url, index=index_name, metadata_json=metadata_template_json)


# synchronous
def delete_index(index_name):
    url = _search_agent_url() + '/delete_index'
    _call_agent(url, index=index_name)


# asynchronous
def push_record(index_name, record_id, metadata_json, organization, collection, infrastructures):
    url = _search_agent_url() + '/add'
    _call_agent.delay(url, index=index_name, record_id=record_id, metadata_json=metadata_json,
                      organization=organization, collection=collection, infrastructures=infrastructures)


# asynchronous
def delete_record(index_name, record_id):
    url = _search_agent_url() + '/delete'
    _call_agent.delay(url, index=index_name, record_id=record_id)
