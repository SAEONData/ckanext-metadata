# encoding: utf-8

from sqlalchemy import types, Table, Column, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import aliased
import vdm.sqlalchemy

from ckan.model import meta, core, types as _types, domain_object
from ckanext.metadata.model import WorkflowState


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
        # param from_state_id may be an empty string, for initial transitions
        return meta.Session.query(cls) \
            .filter(cls.from_state_id == (from_state_id or None)) \
            .filter(cls.to_state_id == to_state_id) \
            .first()

    @classmethod
    def path_exists(cls, from_state_id, to_state_id):
        """
        Determines whether an active transition path connecting the given workflow states exists.
        Note: all workflow states in the path must be active.
        """
        from_state = aliased(WorkflowState)
        to_state = aliased(WorkflowState)
        transition_q = meta.Session.query(cls) \
            .join(from_state, cls.from_state_id == from_state.id) \
            .join(to_state, cls.to_state_id == to_state.id) \
            .filter(cls.state == 'active') \
            .filter(from_state.state == 'active') \
            .filter(to_state.state == 'active')

        if transition_q \
                .filter(cls.from_state_id == from_state_id) \
                .filter(cls.to_state_id == to_state_id) \
                .count() > 0:
            return True

        transitions = transition_q \
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
