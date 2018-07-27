# encoding: utf-8

from sqlalchemy import types, Table, Column, ForeignKey
import vdm.sqlalchemy
import datetime

from ckan.model import meta, core, types as _types, domain_object


workflow_annotation_table = Table(
    'workflow_annotation', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('metadata_record_id', types.UnicodeText, ForeignKey('package.id'), nullable=False),
    Column('workflow_annotation_json', types.UnicodeText),
    Column('timestamp', types.DateTime, nullable=False, default=datetime.datetime.utcnow),
)

vdm.sqlalchemy.make_table_stateful(workflow_annotation_table)
workflow_annotation_revision_table = core.make_revisioned_table(workflow_annotation_table)


class WorkflowAnnotation(vdm.sqlalchemy.RevisionedObjectMixin,
                         vdm.sqlalchemy.StatefulObjectMixin,
                         domain_object.DomainObject):

    @classmethod
    def get(cls, reference):
        """
        Returns a workflow_annotation object referenced by its id.
        """
        if not reference:
            return None

        return meta.Session.query(cls).get(reference)


meta.mapper(WorkflowAnnotation, workflow_annotation_table,
            extension=[vdm.sqlalchemy.Revisioner(workflow_annotation_revision_table)])

vdm.sqlalchemy.modify_base_object_mapper(WorkflowAnnotation, core.Revision, core.State)
WorkflowAnnotationRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, WorkflowAnnotation, workflow_annotation_revision_table)
