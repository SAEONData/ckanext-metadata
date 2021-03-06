# encoding: utf-8

import logging
from ckan.model import meta
from sqlalchemy import text

from ckanext.metadata.model import *

log = logging.getLogger(__name__)


def init_tables():
    tables = (
        metadata_standard_table,
        metadata_standard_revision_table,
        metadata_schema_table,
        metadata_schema_revision_table,
        workflow_state_table,
        workflow_state_revision_table,
        workflow_transition_table,
        workflow_transition_revision_table,
        metadata_json_attr_map_table,
        metadata_json_attr_map_revision_table,
        workflow_annotation_table,
        workflow_annotation_revision_table,
    )
    for table in tables:
        if not table.exists():
            log.debug("Creating table %s", table.name)
            table.create()
        else:
            log.debug("Table %s already exists", table.name)

    conn = meta.engine.connect()
    conn.execute(text('alter table package add column if not exists last_publish_check timestamp with time zone'))
