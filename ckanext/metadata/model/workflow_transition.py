# encoding: utf-8

from sqlalchemy import types, Table, Column, ForeignKey, CheckConstraint, UniqueConstraint
import vdm.sqlalchemy

from ckan.model import meta, core, types as _types, domain_object


workflow_transition_table = Table(
    'workflow_transition', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('from_state_id', types.UnicodeText, ForeignKey('workflow_state.id')),
    Column('to_state_id', types.UnicodeText, ForeignKey('workflow_state.id'), nullable=False),
    UniqueConstraint('from_state_id', 'to_state_id'),
    CheckConstraint('from_state_id is null or from_state_id != to_state_id'),
)

vdm.sqlalchemy.make_table_stateful(workflow_transition_table)
workflow_transition_revision_table = core.make_revisioned_table(workflow_transition_table)


class WorkflowTransition(vdm.sqlalchemy.RevisionedObjectMixin,
                         vdm.sqlalchemy.StatefulObjectMixin,
                         domain_object.DomainObject):

    @classmethod
    def get(cls, reference):
        """
        Returns a workflow_transition object referenced by its id.
        """
        if not reference:
            return None

        return meta.Session.query(cls).get(reference)

    @classmethod
    def lookup(cls, from_state_id, to_state_id):
        """
        Returns a workflow_transition object that connects the given states.
        """
        return meta.Session.query(cls) \
            .filter(cls.from_state_id == from_state_id) \
            .filter(cls.to_state_id == to_state_id) \
            .first()

    @classmethod
    def path_exists(cls, from_state_id, to_state_id):
        """
        Determines whether a transition path connecting the given states exists.
        """
        if cls.lookup(from_state_id, to_state_id) is not None:
            return True

        transitions = meta.Session.query(cls) \
            .filter(cls.from_state_id == from_state_id) \
            .all()
        for transition in transitions:
            if cls.path_exists(transition.to_state_id, to_state_id):
                return True

        return False


meta.mapper(WorkflowTransition, workflow_transition_table,
            extension=[vdm.sqlalchemy.Revisioner(workflow_transition_revision_table)])

vdm.sqlalchemy.modify_base_object_mapper(WorkflowTransition, core.Revision, core.State)
WorkflowTransitionRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, WorkflowTransition, workflow_transition_revision_table)
