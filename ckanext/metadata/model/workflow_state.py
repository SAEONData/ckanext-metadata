# encoding: utf-8

from sqlalchemy import types, Table, Column, ForeignKey
import vdm.sqlalchemy

from ckan.model import meta, core, types as _types, domain_object


workflow_state_table = Table(
    'workflow_state', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('name', types.UnicodeText, nullable=False, unique=True),
    Column('title', types.UnicodeText),
    Column('description', types.UnicodeText),
    # we implement the self-relation "softly", otherwise revision table
    # auto-generation gets confused about how to join to this table
    Column('revert_state_id', types.UnicodeText),  # ForeignKey('workflow_state.id')),
)

vdm.sqlalchemy.make_table_stateful(workflow_state_table)
workflow_state_revision_table = core.make_revisioned_table(workflow_state_table)


class WorkflowState(vdm.sqlalchemy.RevisionedObjectMixin,
                    vdm.sqlalchemy.StatefulObjectMixin,
                    domain_object.DomainObject):

    @classmethod
    def get(cls, reference):
        """
        Returns a workflow_state object referenced by its id or name.
        """
        if not reference:
            return None

        workflow_state = meta.Session.query(cls).get(reference)
        if workflow_state is None:
            workflow_state = cls.by_name(reference)
        return workflow_state


meta.mapper(WorkflowState, workflow_state_table,
            extension=[vdm.sqlalchemy.Revisioner(workflow_state_revision_table)])

vdm.sqlalchemy.modify_base_object_mapper(WorkflowState, core.Revision, core.State)
WorkflowStateRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, WorkflowState, workflow_state_revision_table)
