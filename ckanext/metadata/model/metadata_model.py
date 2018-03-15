# encoding: utf-8

from sqlalchemy import types, orm, Table, Column, ForeignKey, UniqueConstraint
import vdm.sqlalchemy

from ckan.model import meta, core, types as _types, domain_object
from ckanext.metadata.model.metadata_schema import MetadataSchema


metadata_model_table = Table(
    'metadata_model', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('name', types.UnicodeText, nullable=False, unique=True),
    Column('title', types.UnicodeText),
    Column('description', types.UnicodeText),
    Column('metadata_schema_id', types.UnicodeText, ForeignKey('metadata_schema.id'), nullable=False),
    Column('organization_id', types.UnicodeText, ForeignKey('group.id')),
    Column('infrastructure_id', types.UnicodeText, ForeignKey('group.id')),
    Column('model_json', types.UnicodeText),
    # null organization & infrastructure indicates the default model for the given schema
    UniqueConstraint('metadata_schema_id', 'organization_id', 'infrastructure_id')
)

vdm.sqlalchemy.make_table_stateful(metadata_model_table)
metadata_model_revision_table = core.make_revisioned_table(metadata_model_table)


class MetadataModel(vdm.sqlalchemy.RevisionedObjectMixin,
                    vdm.sqlalchemy.StatefulObjectMixin,
                    domain_object.DomainObject):

    @classmethod
    def get(cls, reference):
        """
        Returns a metadata_model object referenced by its id or name.
        """
        if not reference:
            return None

        metadata_model = meta.Session.query(cls).get(reference)
        if metadata_model is None:
            metadata_model = cls.by_name(reference)
        return metadata_model

    @classmethod
    def lookup(cls, metadata_schema_id, organization_id, infrastructure_id):
        """
        Returns a metadata_model object by metadata_schema, organization, infrastructure.
        """
        return meta.Session.query(cls) \
            .filter(cls.metadata_schema_id == metadata_schema_id) \
            .filter(cls.organization_id == organization_id) \
            .filter(cls.infrastructure_id == infrastructure_id) \
            .first()


meta.mapper(MetadataModel, metadata_model_table,
            properties={'schema': orm.relation(MetadataSchema, backref='models')},
            extension=[vdm.sqlalchemy.Revisioner(metadata_model_revision_table)])

vdm.sqlalchemy.modify_base_object_mapper(MetadataModel, core.Revision, core.State)
MetadataModelRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, MetadataModel, metadata_model_revision_table)
