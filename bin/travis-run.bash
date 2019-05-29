#!/bin/bash
set -e

nosetests --ckan \
          --nologcapture \
          --with-pylons=test.ini \
          --with-coverage \
          --cover-package=ckanext.metadata \
          --cover-inclusive \
          --cover-erase \
          --cover-tests \
          ckanext/metadata/tests
