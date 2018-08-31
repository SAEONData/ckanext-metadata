# encoding: utf-8

from sqlalchemy import types, Table, Column, ForeignKey, UniqueConstraint
import vdm.sqlalchemy

from ckan.model import meta, core, types as _types, domain_object


metadata_standard_table = Table(
    'metadata_standard', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('name', types.UnicodeText, nullable=False, unique=True),
    Column('title', types.UnicodeText),
    Column('description', types.UnicodeText),
    Column('standard_name', types.UnicodeText, nullable=False),
    Column('standard_version', types.UnicodeText, nullable=False),
    # we implement the self-relation "softly", otherwise revision table
    # auto-generation gets confused about how to join to this table
    Column('parent_standard_id', types.UnicodeText),  # ForeignKey('metadata_standard.id')),
    Column('metadata_template_json', types.UnicodeText),
    UniqueConstraint('standard_name', 'standard_version')
)

vdm.sqlalchemy.make_table_stateful(metadata_standard_table)
metadata_standard_revision_table = core.make_revisioned_table(metadata_standard_table)


class MetadataStandard(vdm.sqlalchemy.RevisionedObjectMixin,
                       vdm.sqlalchemy.StatefulObjectMixin,
                       domain_object.DomainObject):

    @classmethod
    def get(cls, reference):
        """
        Returns a metadata_standard object referenced by its id or name.
        """
        if not reference:
            return None

        metadata_standard = meta.Session.query(cls).get(reference)
        if metadata_standard is None:
            metadata_standard = cls.by_name(reference)
        return metadata_standard

    @classmethod
    def lookup(cls, standard_name, standard_version):
        """
        Returns a metadata_standard object by standard_name and standard_version.
        """
        return meta.Session.query(cls) \
            .filter(cls.standard_name == standard_name) \
            .filter(cls.standard_version == standard_version) \
            .first()


meta.mapper(MetadataStandard, metadata_standard_table,
            extension=[vdm.sqlalchemy.Revisioner(metadata_standard_revision_table)])

vdm.sqlalchemy.modify_base_object_mapper(MetadataStandard, core.Revision, core.State)
MetadataStandardRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, MetadataStandard, metadata_standard_revision_table)
