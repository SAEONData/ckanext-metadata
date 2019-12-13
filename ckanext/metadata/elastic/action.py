# encoding: utf-8

import logging
from paste.deploy.converters import asbool

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.elastic import client
import ckanext.metadata.model as ckanext_model
from ckan.logic.action.update import organization_update as ckan_org_update

log = logging.getLogger(__name__)


@tk.chained_action
def metadata_standard_index_create(original_action, context, data_dict):
    """
    Initialize a metadata search index.

    Creates the index and then pushes all published metadata records associated with
    the metadata standard to the index asynchronously.

    :param id: the id or name of the metadata standard
    :type id: string

    :returns: dict{'records_queued': count of records queued for insertion into the index}
    """
    original_action(context, data_dict)

    id_ = tk.get_or_bust(data_dict, 'id')
    metadata_standard = ckanext_model.MetadataStandard.get(id_)
    if metadata_standard is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Standard')))

    log.info("Initializing search index for metadata standard %s", metadata_standard.name)

    result = client.create_index(metadata_standard.name, metadata_standard.metadata_template_json)
    if not result['success']:
        raise tk.ValidationError(result['msg'])

    model = context['model']
    session = context['session']

    metadata_records = session.query(model.Package).join(model.PackageExtra) \
        .filter(model.PackageExtra.key == 'metadata_standard_id') \
        .filter(model.PackageExtra.value == metadata_standard.id) \
        .filter(model.Package.type == 'metadata_record') \
        .filter(model.Package.state == 'active') \
        .filter(model.Package.private == False) \
        .all()

    log.info("Queueing %d records for insertion into index '%s'" % (len(metadata_records), metadata_standard.name))

    for metadata_record in metadata_records:
        index_context = context.copy()
        index_context['metadata_record'] = metadata_record
        tk.get_action('metadata_record_index_update')(index_context, {'id': metadata_record.id, 'async': True})

    return {'records_queued': len(metadata_records)}


@tk.chained_action
def metadata_standard_index_delete(original_action, context, data_dict):
    """
    Delete a metadata search index.

    :param id: the id or name of the metadata standard
    :type id: string
    """
    original_action(context, data_dict)

    id_ = tk.get_or_bust(data_dict, 'id')
    metadata_standard = ckanext_model.MetadataStandard.get(id_)
    if metadata_standard is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Standard')))

    log.info("Deleting search index for metadata standard %s", metadata_standard.name)

    result = client.delete_index(metadata_standard.name)
    if not result['success']:
        raise tk.ValidationError(result['msg'])


@tk.chained_action
def metadata_record_index_update(original_action, context, data_dict):
    """
    Add/update/delete a metadata record in a search index.

    Looks at the current state of the metadata record; if published (= not private)
    AND active (= not deleted), then add the record to the index (update if already
    present); otherwise, remove the record if present in the index.

    :param id: the id or name of the metadata record
    :type id: string
    :param async: update the index asynchronously (optional, default: ``True``)
    :type async: boolean
    """
    original_action(context, data_dict)

    model = context['model']
    session = context['session']
    async = asbool(data_dict.get('async', True))

    metadata_record = context.get('metadata_record')
    if not metadata_record:
        id_ = tk.get_or_bust(data_dict, 'id')
        metadata_record = model.Package.get(id_)
        if metadata_record is None or metadata_record.type != 'metadata_record':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    index_name = session.query(ckanext_model.MetadataStandard.name) \
        .filter_by(id=metadata_record.extras['metadata_standard_id']) \
        .scalar()
    record_id = metadata_record.id

    if not metadata_record.private and metadata_record.state == 'active':
        log.debug("Adding metadata record to search index: %s", record_id)

        organization_title = session.query(model.Group.title) \
            .filter_by(id=metadata_record.owner_org) \
            .scalar()
        collection_title = session.query(model.Group.title) \
            .filter_by(id=metadata_record.extras['metadata_collection_id']) \
            .scalar()
        infrastructure_titles = session.query(model.Group.title) \
            .join(model.Member, model.Group.id == model.Member.group_id) \
            .filter(model.Group.type == 'infrastructure') \
            .filter(model.Group.state == 'active') \
            .filter(model.Member.table_name == 'group') \
            .filter(model.Member.table_id == metadata_record.extras['metadata_collection_id']) \
            .filter(model.Member.state == 'active') \
            .all()
        infrastructure_titles = [title for (title,) in infrastructure_titles]

        result = client.put_record(index_name, record_id, metadata_record.extras['metadata_json'],
                                   organization_title, collection_title, infrastructure_titles, async)
    else:
        log.debug("Removing metadata record from search index: %s", record_id)
        result = client.delete_record(index_name, record_id, async)

    if not async and not result['success']:
        raise tk.ValidationError(result['msg'])


@tk.chained_action
def metadata_standard_index_show(original_action, context, data_dict):
    """
    Get the document structure of a metadata search index.

    :param id: the id or name of the metadata standard
    :type id: string

    :returns: dictionary, or None if the index does not exist
    """
    original_action(context, data_dict)

    id_ = tk.get_or_bust(data_dict, 'id')
    metadata_standard = ckanext_model.MetadataStandard.get(id_)
    if metadata_standard is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Standard')))

    indexes = client.get_indexes()
    if not indexes['success']:
        raise tk.ValidationError(indexes['msg'])

    if metadata_standard.name in indexes['indexes']:
        result = client.get_index_mapping(metadata_standard.name)
        if not result['success']:
            raise tk.ValidationError(result['msg'])
        return result['mapping']


@tk.chained_action
def metadata_record_index_show(original_action, context, data_dict):
    """
    Get the indexed version of a metadata record.

    :param id: the id or name of the metadata record
    :type id: string

    :returns: dictionary, or None if the record does not exist in the search index
    """
    original_action(context, data_dict)

    model = context['model']
    session = context['session']

    id_ = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(id_)
    if metadata_record is None or metadata_record.type != 'metadata_record':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    index_name = session.query(ckanext_model.MetadataStandard.name) \
        .filter_by(id=metadata_record.extras['metadata_standard_id']) \
        .scalar()
    record_id = metadata_record.id

    result = client.get_record(index_name, record_id)
    if not result['success']:
        raise tk.ValidationError(result['msg'])
    return result.get('record')


@tk.chained_action
def infrastructure_update(original_action, context, data_dict):
    """
    Hook into this action so that we can update the search index if an infrastructure title changes.
    """
    model = context['model']
    session = context['session']
    return_id_only = context.get('return_id_only', False)

    update_search_index = False

    new_title = data_dict.get('title')
    if new_title is not None:
        id_ = tk.get_or_bust(data_dict, 'id')
        infrastructure = model.Group.get(id_)
        if infrastructure is None or infrastructure.type != 'infrastructure':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Infrastructure')))
        
        update_search_index = new_title != infrastructure.title

    result = original_action(context, data_dict)
    infrastructure_id = result if return_id_only else result['id']

    if update_search_index:
        metadata_records = session.query(model.Package) \
            .join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id) \
            .filter(model.PackageExtra.key == 'metadata_collection_id') \
            .join(model.Member, model.PackageExtra.value == model.Member.table_id) \
            .filter(model.Member.group_id == infrastructure_id) \
            .filter(model.Member.table_name == 'group') \
            .filter(model.Member.state != 'deleted') \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .all()

        for metadata_record in metadata_records:
            index_context = context.copy()
            index_context['metadata_record'] = metadata_record
            tk.get_action('metadata_record_index_update')(index_context, {'id': metadata_record.id})

    return result


@tk.chained_action
def metadata_collection_update(original_action, context, data_dict):
    """
    Hook into this action so that we can update the search index if a metadata collection title changes
    or if its infrastructure list changes.
    """
    model = context['model']
    session = context['session']
    return_id_only = context.get('return_id_only', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    metadata_collection = model.Group.get(id_)
    if metadata_collection is None or metadata_collection.type != 'metadata_collection':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))

    update_search_index = False

    new_title = data_dict.get('title')
    if new_title is not None:
        update_search_index = new_title != metadata_collection.title

    if not update_search_index:
        # check if infrastructure list has changed
        new_infrastructures = []
        for new_inf_dict in data_dict.get('infrastructures'):
            new_inf = model.Group.get(new_inf_dict['id'])
            if new_inf is not None:  # no need to validate the infrastructure here; it's done in the original_action call
                new_infrastructures += [new_inf.id]

        old_infrastructures = session.query(model.Member.group_id) \
            .join(model.Group, model.Group.id == model.Member.group_id) \
            .filter(model.Group.type == 'infrastructure') \
            .filter(model.Group.state == 'active') \
            .filter(model.Member.table_name == 'group') \
            .filter(model.Member.table_id == metadata_collection.id) \
            .filter(model.Member.state == 'active') \
            .all()
        old_infrastructures = [old_inf_id for (old_inf_id,) in old_infrastructures]
        update_search_index = set(new_infrastructures) != set(old_infrastructures)

    result = original_action(context, data_dict)
    metadata_collection_id = result if return_id_only else result['id']

    if update_search_index:
        metadata_records = session.query(model.Package) \
            .join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id) \
            .filter(model.PackageExtra.key == 'metadata_collection_id') \
            .filter(model.PackageExtra.value == metadata_collection_id) \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .all()

        for metadata_record in metadata_records:
            index_context = context.copy()
            index_context['metadata_record'] = metadata_record
            tk.get_action('metadata_record_index_update')(index_context, {'id': metadata_record.id})

    return result


def organization_update(context, data_dict):
    """
    Hook into this action so that we can update the search index if an organization title changes.
    """
    model = context['model']
    session = context['session']
    return_id_only = context.get('return_id_only', False)

    update_search_index = False

    new_title = data_dict.get('title')
    if new_title is not None:
        id_ = tk.get_or_bust(data_dict, 'id')
        organization = model.Group.get(id_)
        if organization is None or organization.type != 'organization':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Organization')))
        
        update_search_index = new_title != organization.title

    result = ckan_org_update(context, data_dict)
    organization_id = result if return_id_only else result['id']

    if update_search_index:
        metadata_records = session.query(model.Package) \
            .filter(model.Package.owner_org == organization_id) \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .all()

        for metadata_record in metadata_records:
            index_context = context.copy()
            index_context['metadata_record'] = metadata_record
            tk.get_action('metadata_record_index_update')(index_context, {'id': metadata_record.id})

    return result
