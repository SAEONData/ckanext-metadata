# ckanext-metadata

A metadata management framework for CKAN.

[![Travis CI](https://travis-ci.org/SAEONData/ckanext-metadata.svg?branch=master)](https://travis-ci.org/SAEONData/ckanext-metadata)
[![Coverage](https://coveralls.io/repos/SAEONData/ckanext-metadata/badge.svg)](https://coveralls.io/r/SAEONData/ckanext-metadata)

## Installation

This extension requires CKAN v2.7 or later.

### Database setup

    . /usr/lib/ckan/default/bin/activate
    cd /usr/lib/ckan/default/src/ckanext-metadata
    paster metadata initdb -c /etc/ckan/default/development.ini
