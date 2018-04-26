# encoding: utf-8

from sqlalchemy import types, Table, Column, ForeignKey
import vdm.sqlalchemy

from ckan.model import meta, core, types as _types, domain_object


workflow_metric_table = Table(
    'workflow_metric', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('name', types.UnicodeText, nullable=False, unique=True),
    Column('title', types.UnicodeText),
    Column('description', types.UnicodeText),
    Column('evaluator_uri', types.UnicodeText, nullable=False),
)

vdm.sqlalchemy.make_table_stateful(workflow_metric_table)
workflow_metric_revision_table = core.make_revisioned_table(workflow_metric_table)


class WorkflowMetric(vdm.sqlalchemy.RevisionedObjectMixin,
                     vdm.sqlalchemy.StatefulObjectMixin,
                     domain_object.DomainObject):

    @classmethod
    def get(cls, reference):
        """
        Returns a workflow_metric object referenced by its id or name.
        """
        if not reference:
            return None

        workflow_metric = meta.Session.query(cls).get(reference)
        if workflow_metric is None:
            workflow_metric = cls.by_name(reference)
        return workflow_metric


meta.mapper(WorkflowMetric, workflow_metric_table,
            extension=[vdm.sqlalchemy.Revisioner(workflow_metric_revision_table)])

vdm.sqlalchemy.modify_base_object_mapper(WorkflowMetric, core.Revision, core.State)
WorkflowMetricRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, WorkflowMetric, workflow_metric_revision_table)
