# encoding: utf-8

from sqlalchemy import types, orm, Table, Column, ForeignKey, UniqueConstraint
import vdm.sqlalchemy

from ckan.model import meta, core, types as _types, domain_object


metadata_schema_table = Table(
    'metadata_schema', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('name', types.UnicodeText, nullable=False, unique=True),
    Column('title', types.UnicodeText),
    Column('description', types.UnicodeText),
    Column('metadata_standard_id', types.UnicodeText, ForeignKey('metadata_standard.id'), nullable=False),
    Column('organization_id', types.UnicodeText, ForeignKey('group.id')),
    Column('infrastructure_id', types.UnicodeText, ForeignKey('group.id')),
    Column('schema_json', types.UnicodeText),
    # null organization & infrastructure implies that the object is the default schema for the given metadata standard
    UniqueConstraint('metadata_standard_id', 'organization_id', 'infrastructure_id')
)

vdm.sqlalchemy.make_table_stateful(metadata_schema_table)
metadata_schema_revision_table = core.make_revisioned_table(metadata_schema_table)


class MetadataSchema(vdm.sqlalchemy.RevisionedObjectMixin,
                    vdm.sqlalchemy.StatefulObjectMixin,
                    domain_object.DomainObject):

    @classmethod
    def get(cls, reference):
        """
        Returns a metadata_schema object referenced by its id or name.
        """
        if not reference:
            return None

        metadata_schema = meta.Session.query(cls).get(reference)
        if metadata_schema is None:
            metadata_schema = cls.by_name(reference)
        return metadata_schema

    @classmethod
    def lookup(cls, metadata_standard_id, organization_id, infrastructure_id):
        """
        Returns a metadata_schema object by metadata_standard, organization, infrastructure.
        """
        return meta.Session.query(cls) \
            .filter(cls.metadata_standard_id == metadata_standard_id) \
            .filter(cls.organization_id == organization_id) \
            .filter(cls.infrastructure_id == infrastructure_id) \
            .first()


meta.mapper(MetadataSchema, metadata_schema_table,
            extension=[vdm.sqlalchemy.Revisioner(metadata_schema_revision_table)])

vdm.sqlalchemy.modify_base_object_mapper(MetadataSchema, core.Revision, core.State)
MetadataSchemaRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, MetadataSchema, metadata_schema_revision_table)
