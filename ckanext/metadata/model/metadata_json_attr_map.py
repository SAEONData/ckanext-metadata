# encoding: utf-8

from sqlalchemy import types, Table, Column, ForeignKey, UniqueConstraint
import vdm.sqlalchemy

from ckan.model import meta, core, types as _types, domain_object


metadata_json_attr_map_table = Table(
    'metadata_json_attr_map', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('json_path', types.UnicodeText, nullable=False),
    Column('record_attr', types.UnicodeText, nullable=False),
    Column('is_key', types.Boolean, nullable=False),
    Column('metadata_standard_id', types.UnicodeText, ForeignKey('metadata_standard.id'), nullable=False),
    UniqueConstraint('metadata_standard_id', 'record_attr'),
)

vdm.sqlalchemy.make_table_stateful(metadata_json_attr_map_table)
metadata_json_attr_map_revision_table = core.make_revisioned_table(metadata_json_attr_map_table)


class MetadataJSONAttrMap(vdm.sqlalchemy.RevisionedObjectMixin,
                          vdm.sqlalchemy.StatefulObjectMixin,
                          domain_object.DomainObject):

    @classmethod
    def get(cls, reference):
        """
        Returns a MetadataJSONAttrMap object referenced by its id.
        """
        if not reference:
            return None

        return meta.Session.query(cls).get(reference)

    @classmethod
    def lookup_by_json_path(cls, metadata_standard_id, json_path):
        """
        Returns a MetadataJSONAttrMap object for the given standard by json_path.
        """
        return meta.Session.query(cls) \
            .filter(cls.metadata_standard_id == metadata_standard_id) \
            .filter(cls.json_path == json_path) \
            .first()

    @classmethod
    def lookup_by_record_attr(cls, metadata_standard_id, record_attr):
        """
        Returns a MetadataJSONAttrMap object for the given standard by record_attr.
        """
        return meta.Session.query(cls) \
            .filter(cls.metadata_standard_id == metadata_standard_id) \
            .filter(cls.record_attr == record_attr) \
            .first()


meta.mapper(MetadataJSONAttrMap, metadata_json_attr_map_table,
            extension=[vdm.sqlalchemy.Revisioner(metadata_json_attr_map_revision_table)])

vdm.sqlalchemy.modify_base_object_mapper(MetadataJSONAttrMap, core.Revision, core.State)
MetadataJSONAttrMapRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, MetadataJSONAttrMap, metadata_json_attr_map_revision_table)
