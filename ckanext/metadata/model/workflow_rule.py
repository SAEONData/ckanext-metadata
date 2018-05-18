# encoding: utf-8

from sqlalchemy import types, Table, Column, ForeignKey, UniqueConstraint
import vdm.sqlalchemy

from ckan.model import meta, core, types as _types, domain_object


workflow_rule_table = Table(
    'workflow_rule', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('workflow_state_id', types.UnicodeText, ForeignKey('workflow_state.id'), nullable=False),
    Column('workflow_metric_id', types.UnicodeText, ForeignKey('workflow_metric.id'), nullable=False),
    Column('rule_json', types.UnicodeText, nullable=False),
    UniqueConstraint('workflow_state_id', 'workflow_metric_id'),
)

vdm.sqlalchemy.make_table_stateful(workflow_rule_table)
workflow_rule_revision_table = core.make_revisioned_table(workflow_rule_table)


class WorkflowRule(vdm.sqlalchemy.RevisionedObjectMixin,
                   vdm.sqlalchemy.StatefulObjectMixin,
                   domain_object.DomainObject):

    @classmethod
    def get(cls, reference):
        """
        Returns a workflow_rule object referenced by its id.
        """
        if not reference:
            return None

        return meta.Session.query(cls).get(reference)

    @classmethod
    def lookup(cls, workflow_state_id, workflow_metric_id):
        """
        Returns a workflow_rule object for the given state and metric.
        """
        return meta.Session.query(cls) \
            .filter(cls.workflow_state_id == workflow_state_id) \
            .filter(cls.workflow_metric_id == workflow_metric_id) \
            .first()


meta.mapper(WorkflowRule, workflow_rule_table,
            extension=[vdm.sqlalchemy.Revisioner(workflow_rule_revision_table)])

vdm.sqlalchemy.modify_base_object_mapper(WorkflowRule, core.Revision, core.State)
WorkflowRuleRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, WorkflowRule, workflow_rule_revision_table)
