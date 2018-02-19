# encoding: utf-8

from sqlalchemy.sql import select

import ckan.plugins.toolkit as tk
import ckan.lib.dictization as d
import ckanext.metadata.model as ckanext_model


def metadata_model_dictize(metadata_model, context):
    is_latest_revision = not(context.get('revision_id') or
                             context.get('revision_date'))
    execute = _execute if is_latest_revision else _execute_with_revision
    if is_latest_revision:
        if isinstance(metadata_model, ckanext_model.MetadataModelRevision):
            metadata_model = ckanext_model.MetadataModel.get(metadata_model.id)
        result = metadata_model
    else:
        metadata_model_rev = ckanext_model.metadata_model_revision_table
        q = select([metadata_model_rev]).where(metadata_model_rev.c.id == metadata_model.id)
        result = execute(q, metadata_model_rev, context).first()
    if not result:
        raise tk.ObjectNotFound

    result_dict = d.table_dictize(result, context)
    return result_dict


def metadata_schema_dictize(metadata_schema, context):
    is_latest_revision = not(context.get('revision_id') or
                             context.get('revision_date'))
    execute = _execute if is_latest_revision else _execute_with_revision
    if is_latest_revision:
        if isinstance(metadata_schema, ckanext_model.MetadataSchemaRevision):
            metadata_schema = ckanext_model.MetadataSchema.get(metadata_schema.id)
        result = metadata_schema
    else:
        metadata_schema_rev = ckanext_model.metadata_schema_revision_table
        q = select([metadata_schema_rev]).where(metadata_schema_rev.c.id == metadata_schema.id)
        result = execute(q, metadata_schema_rev, context).first()
    if not result:
        raise tk.ObjectNotFound

    result_dict = d.table_dictize(result, context)
    return result_dict


def _execute(q, table, context):
    """
    Copied from ckan.lib.dictization.model_dictize

    Takes an SqlAlchemy query (q) that is (at its base) a Select on an
    object table (table), and it returns the object.

    Analogous with _execute_with_revision, so takes the same params, even
    though it doesn't need the table.
    """
    model = context['model']
    session = model.Session
    return session.execute(q)


def _execute_with_revision(q, rev_table, context):
    """
    Copied from ckan.lib.dictization.model_dictize

    Takes an SqlAlchemy query (q) that is (at its base) a Select on an object
    revision table (rev_table), and you provide revision_id or revision_date in
    the context and it will filter the object revision(s) to an earlier time.

    Raises NotFound if context['revision_id'] is provided, but the revision
    ID does not exist.

    Returns [] if there are no results.
    """
    model = context['model']
    session = model.Session
    revision_id = context.get('revision_id')
    revision_date = context.get('revision_date')

    if revision_id:
        revision = session.query(context['model'].Revision).filter_by(
            id=revision_id).first()
        if not revision:
            raise tk.ObjectNotFound
        revision_date = revision.timestamp

    q = q.where(rev_table.c.revision_timestamp <= revision_date)
    q = q.where(rev_table.c.expired_timestamp > revision_date)

    return session.execute(q)
