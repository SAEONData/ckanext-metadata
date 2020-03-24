# encoding: utf-8

import logging
import requests
from celery import Celery

from ckan.common import config

app = Celery('client',
             broker='pyamqp://{}'.format(config.get('ckan.metadata.elastic.rabbitmq_host')),
             include=['ckanext.metadata.elastic.client'])

log = logging.getLogger(__name__)


def _search_agent_url():
    return config.get('ckan.metadata.elastic.search_agent_url')


@app.task
def _call_agent(url, *outputs, **kwargs):
    """
    Post a request to the Elastic search agent.

    :param url: path to search agent API function
    :param outputs: expected members of the result dict in case of success
                    (optional, in addition to 'success' and 'msg')
    :param kwargs: params to API function

    :return: dict{'success', 'msg', 'output1', ...}
    """
    log.debug("POST to Elasticsearch agent %s %r", url, kwargs)
    try:
        response = requests.post(url, data=kwargs)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result.get('success'), bool):
            raise ValueError("Invalid response")
        if result['success'] and not (set(outputs) <= set(result)):
            raise ValueError("Incomplete response")
    except Exception, e:
        msg = "Request to Elasticsearch agent failed"
        log.error(msg + ": " + str(e))
        result = {'success': False, 'msg': msg}

    if not result['success']:
        result.setdefault('msg', "Operation failed: reason unknown")
    return result


def create_index(index_name, metadata_template_json):
    url = _search_agent_url() + '/create_index'
    return _call_agent(url, index=index_name, metadata_json=metadata_template_json)


def delete_index(index_name):
    url = _search_agent_url() + '/delete_index'
    return _call_agent(url, index=index_name)


def get_indexes():
    url = _search_agent_url() + '/get_indexes'
    return _call_agent(url, 'indexes')


def get_index_mapping(index_name):
    url = _search_agent_url() + '/index_mapping'
    return _call_agent(url, 'mapping', index=index_name)


def get_record(index_name, record_id):
    url = _search_agent_url() + '/search'
    result = _call_agent(url, 'result_length', 'results', index=index_name, record_id=record_id)
    count = result.pop('result_length', 0)
    records = result.pop('results', [])
    if result['success']:
        if count == 1:
            result['record'] = records[0]
        elif count > 1:
            result['success'] = False
            result['msg'] = "Multiple records found with the specified id"
    return result


def put_record(index_name, record_id, metadata_json, organization, collection, infrastructures, async):
    url = _search_agent_url() + '/add'
    func = _call_agent.delay if async else _call_agent
    result = func(url, index=index_name, record_id=record_id, metadata_json=metadata_json,
                  organization=organization, collection=collection, infrastructures=infrastructures)
    if not async:
        return result


def delete_record(index_name, record_id, async):
    url = _search_agent_url() + '/delete'
    func = _call_agent.delay if async else _call_agent
    result = func(url, index=index_name, record_id=record_id, force=True)
    if not async:
        return result
