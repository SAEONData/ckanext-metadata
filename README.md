# ckanext-metadata

[![Travis CI](https://travis-ci.org/SAEONData/ckanext-metadata.svg?branch=master)](https://travis-ci.org/SAEONData/ckanext-metadata)
[![Coverage](https://coveralls.io/repos/SAEONData/ckanext-metadata/badge.svg)](https://coveralls.io/r/SAEONData/ckanext-metadata)

A metadata management framework for [CKAN](https://ckan.org).

## Requirements

This extension has been developed and tested with CKAN version 2.8.2.

Extension [ckanext-jsonpatch](https://github.com/SAEONData/ckanext-jsonpatch) is required
for metadata workflows.

RabbitMQ server is required for [Elastic search agent](https://github.com/SAEONData/elastic-search-agent)
integration:

    sudo apt install rabbitmq-server

## Installation

Activate your CKAN virtual environment:

    . /usr/lib/ckan/default/bin/activate

Install the latest development version of _ckanext-metadata_ and its dependencies:

    cd /usr/lib/ckan/default
    pip install -e 'git+https://github.com/SAEONData/ckanext-metadata.git#egg=ckanext-metadata'
    pip install -r src/ckanext-metadata/requirements.txt

In a production environment, you'll probably want to pin a specific
[release version](https://github.com/SAEONData/ckanext-metadata/releases) instead, e.g.:

    pip install -e 'git+https://github.com/SAEONData/ckanext-metadata.git@v1.0.0#egg=ckanext-metadata'

Create the required database tables:

    cd /usr/lib/ckan/default/src/ckanext-metadata
    paster metadata_framework initdb -c /etc/ckan/default/development.ini

Add `metadata_framework`, `jsonpatch`, `metadata_infrastructure_ui` (optional, for infrastructure-type groups to
be configurable in the UI), and `metadata_elasticsearch` (optional, for Elastic search agent integration) to the
list of plugins in your CKAN configuration file (e.g. `/etc/ckan/default/production.ini`):

    ckan.plugins = ... metadata_framework jsonpatch metadata_infrastructure_ui metadata_elasticsearch

Restart your CKAN instance.

## Configuration

The following configuration options are used by plugins as indicated:

| Plugin | Option | Default | Description |
| ------ | ------ | ------- | ----------- |
| metadata_framework | ckan.metadata.admin_org | | The name of the admin organization; applicable to the administrator and curator roles.
| metadata_framework | ckan.metadata.admin_role | | The name of the administrator role. A user with the admin role - within the admin org - can perform functions like configuring metadata schemas and workflow schemas.
| metadata_framework | ckan.metadata.curator_role | | The name of the curator role. A user with the curator role - either within the admin org or within the org that owns the resources being requested/updated - can perform functions related to metadata collections and metadata workflow.
| metadata_framework | ckan.metadata.harvester_role | | The name of the harvester role. A harvester is like a contributor, but can also set the workflow state of a metadata record.
| metadata_framework | ckan.metadata.contributor_role | | The name of the contributor role. A contributor can create and update metadata records owned by the organization in which they have that role.
| metadata_framework | ckan.metadata.convert_nested_ids_to_names | True | If True, object IDs are converted to object names in API output dictionaries. Note: this option must be set to True for metadata framework UI forms to work correctly.
| metadata_framework | ckan.metadata.doi_prefix | | The DOI prefix for auto-generation of DOIs (dependent on metadata collection settings).
| metadata_elasticsearch | ckan.metadata.elastic.search_agent_url | | The URL of the Elastic Search Agent.

### Environment variables

* RABBITMQ_HOST: The host on which the RabbitMQ server is running.

Restart your CKAN instance after any configuration changes.
