# encoding: utf-8

import logging

from ckanext.metadata.model import metadata_model
from ckanext.metadata.model import metadata_schema

log = logging.getLogger(__name__)


def init_tables():
    tables = (
        metadata_schema.metadata_schema_table,
        metadata_schema.metadata_schema_revision_table,
        metadata_model.metadata_model_table,
        metadata_model.metadata_model_revision_table,
    )
    for table in tables:
        if not table.exists():
            log.debug("Creating table %s", table.name)
            table.create()
        else:
            log.debug("Table %s already exists", table.name)
