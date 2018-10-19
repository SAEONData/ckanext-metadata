# encoding: utf-8

import logging
import requests
from celery import Celery

from ckan.common import config

app = Celery('client',
             broker='pyamqp://localhost',
             include=['ckanext.metadata.elastic.client'])

log = logging.getLogger(__name__)


def _search_agent_url():
    return config.get('ckan.metadata.elastic.search_agent_url')


@app.task
def _call_agent_async(url, **kwargs):
    _call_agent.delay(url, **kwargs)


def _call_agent(url, **kwargs):
    log.debug("POST to elastic search agent %s %r", url, kwargs)
    try:
        response = requests.post(url, data=kwargs)
        response.raise_for_status()
        result = response.json()
        if not result['success']:
            raise ValueError(result['msg'])
    except requests.RequestException, e:
        log.error("Call to elastic search agent failed: %s", e)
        result = {
            'success': False,
            'msg': "Call to elastic search agent failed: %s" % e,
        }
    except (ValueError, KeyError), e:
        log.error("Invalid response from elastic search agent: %s", e)
        result = {
            'success': False,
            'msg': "Invalid response from elastic search agent",
        }
    return result


# synchronous
def initialize_index(index_name, metadata_template_json):
    url = _search_agent_url() + '/create_index'
    return _call_agent(url, index=index_name, metadata_json=metadata_template_json)


# synchronous
def delete_index(index_name):
    url = _search_agent_url() + '/delete_index'
    return _call_agent(url, index=index_name)


# asynchronous
def push_record(index_name, record_id, metadata_json, organization, collection, infrastructures):
    url = _search_agent_url() + '/add'
    _call_agent_async(url, index=index_name, record_id=record_id, metadata_json=metadata_json,
                      organization=organization, collection=collection, infrastructures=infrastructures)


# asynchronous
def delete_record(index_name, record_id):
    url = _search_agent_url() + '/delete'
    _call_agent_async(url, index=index_name, record_id=record_id)
