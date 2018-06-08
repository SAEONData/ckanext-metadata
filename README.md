# ckanext-metadata

[![Travis CI](https://travis-ci.org/SAEONData/ckanext-metadata.svg?branch=master)](https://travis-ci.org/SAEONData/ckanext-metadata)
[![Coverage](https://coveralls.io/repos/SAEONData/ckanext-metadata/badge.svg)](https://coveralls.io/r/SAEONData/ckanext-metadata)

A metadata management framework for [CKAN](https://ckan.org).

## Requirements

This extension has been developed and tested with CKAN version 2.7.4.

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
    paster metadata initdb -c /etc/ckan/default/development.ini

Open your CKAN configuration file (e.g. `/etc/ckan/default/production.ini`) and
add `metadata` to the list of plugins :

    ckan.plugins = ... metadata

Restart your CKAN instance.
