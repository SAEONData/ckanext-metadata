# encoding: utf-8

import logging

from ckanext.metadata.model import *

log = logging.getLogger(__name__)


def init_tables():
    tables = (
        metadata_standard_table,
        metadata_standard_revision_table,
        metadata_model_table,
        metadata_model_revision_table,
        workflow_state_table,
        workflow_state_revision_table,
        workflow_transition_table,
        workflow_transition_revision_table,
    )
    for table in tables:
        if not table.exists():
            log.debug("Creating table %s", table.name)
            table.create()
        else:
            log.debug("Table %s already exists", table.name)
