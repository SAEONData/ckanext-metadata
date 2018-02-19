# encoding: utf-8

from sqlalchemy import types, Table, Column, ForeignKey, UniqueConstraint
import vdm.sqlalchemy

from ckan.model import meta, core, types as _types, domain_object


metadata_schema_table = Table(
    'metadata_schema', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('title', types.UnicodeText),
    Column('description', types.UnicodeText),
    Column('schema_name', types.UnicodeText, nullable=False),
    Column('schema_version', types.UnicodeText, nullable=False),
    Column('schema_xsd', types.UnicodeText),
    # we implement the self-referencing "softly", otherwise revision table
    # auto-generation gets confused about how to join to this table
    Column('base_schema_id', types.UnicodeText),  # ForeignKey('metadata_schema.id')),
    UniqueConstraint('schema_name', 'schema_version')
)

vdm.sqlalchemy.make_table_stateful(metadata_schema_table)
metadata_schema_revision_table = core.make_revisioned_table(metadata_schema_table)


class MetadataSchema(vdm.sqlalchemy.RevisionedObjectMixin,
                     vdm.sqlalchemy.StatefulObjectMixin,
                     domain_object.DomainObject):

    @classmethod
    def get(cls, reference):
        return meta.Session.query(cls).filter(cls.id == reference).first()

    @classmethod
    def by_name_and_version(cls, schema_name, schema_version):
        return meta.Session.query(cls) \
            .filter(cls.schema_name == schema_name) \
            .filter(cls.schema_version == schema_version) \
            .first()


meta.mapper(MetadataSchema, metadata_schema_table,
            extension=[vdm.sqlalchemy.Revisioner(metadata_schema_revision_table)])

vdm.sqlalchemy.modify_base_object_mapper(MetadataSchema, core.Revision, core.State)
MetadataSchemaRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, MetadataSchema, metadata_schema_revision_table)
