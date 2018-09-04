# encoding: utf-8

import logging
import json

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

    :param id: the id or name of the metadata standard
    :type id: string
    """
    original_action(context, data_dict)

    id_ = tk.get_or_bust(data_dict, 'id')
    metadata_standard = ckanext_model.MetadataStandard.get(id_)
    if metadata_standard is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Standard')))

    log.info("Initializing search index from metadata standard %s: %r",
             metadata_standard.name, metadata_standard.metadata_template_json)

    template_record_json = json.dumps({
        'metadata_json': json.loads(metadata_standard.metadata_template_json),
        'organization': 'Organization Title',
        'collection': 'Collection Title',
        'infrastructures': ['Infrastructure 1 Title', 'Infrastructure 2 Title'],
    })
    client.initialize_index(metadata_standard.name, template_record_json)


@tk.chained_action
def metadata_record_index_update(original_action, context, data_dict):
    """
    Add/update/delete a metadata record in a search index.

    :param id: the id or name of the metadata record
    :type id: string
    """
    original_action(context, data_dict)

    model = context['model']
    session = context['session']

    metadata_record = context.get('metadata_record')
    if not metadata_record:
        id_ = tk.get_or_bust(data_dict, 'id')
        metadata_record = model.Package.get(id_)
        if metadata_record is None or metadata_record.type != 'metadata_record':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    index_name = session.query(ckanext_model.MetadataStandard.name) \
        .filter_by(id=metadata_record.extras['metadata_standard_id']) \
        .scalar()

    if metadata_record.private:
        log.debug("Removing metadata record from search index: %s", metadata_record.name)
        client.delete_record(index_name, metadata_record.name)
    else:
        log.debug("Adding metadata record to search index: %s", metadata_record.name)

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
            .filter(model.Member.table_name == 'package') \
            .filter(model.Member.table_id == metadata_record.id) \
            .filter(model.Member.state == 'active') \
            .all()
        infrastructure_titles = [title for (title,) in infrastructure_titles]

        record_json = json.dumps({
            'metadata_json': json.loads(metadata_record.extras['metadata_json']),
            'organization': organization_title,
            'collection': collection_title,
            'infrastructures': infrastructure_titles,
        })
        client.push_record(index_name, record_json)


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
            .join(model.Member, model.Package.id == model.Member.table_id) \
            .filter(model.Member.group_id == infrastructure_id) \
            .filter(model.Member.table_name == 'package') \
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
    Hook into this action so that we can update the search index if a metadata collection title changes.
    """
    model = context['model']
    session = context['session']
    return_id_only = context.get('return_id_only', False)

    update_search_index = False

    new_title = data_dict.get('title')
    if new_title is not None:
        id_ = tk.get_or_bust(data_dict, 'id')
        metadata_collection = model.Group.get(id_)
        if metadata_collection is None or metadata_collection.type != 'metadata_collection':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))
        
        update_search_index = new_title != metadata_collection.title

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
