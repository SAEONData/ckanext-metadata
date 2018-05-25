# ckanext-metadata

A metadata management framework for [CKAN](https://ckan.org).

[![Travis CI](https://travis-ci.org/SAEONData/ckanext-metadata.svg?branch=master)](https://travis-ci.org/SAEONData/ckanext-metadata)
[![Coverage](https://coveralls.io/repos/SAEONData/ckanext-metadata/badge.svg)](https://coveralls.io/r/SAEONData/ckanext-metadata)

## Requirements

This extension has been developed and tested with CKAN version 2.7.4.

## Installation

### Database setup

    . /usr/lib/ckan/default/bin/activate
    cd /usr/lib/ckan/default/src/ckanext-metadata
    paster metadata initdb -c /etc/ckan/default/development.ini
