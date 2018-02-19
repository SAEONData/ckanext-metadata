# encoding: utf-8

import logging

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.lib.dictization import model_save
import ckanext.metadata.model as ckanext_model

log = logging.getLogger(__name__)


def metadata_schema_delete(context, data_dict):
    """
    Delete a metadata schema.

    You must be authorized to delete the metadata schema.

    :param id: the id of the metadata schema to delete
    :type id: string
    """
    log.info("Deleting metadata schema: %r", data_dict)

    model = context['model']
    user = context['user']

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.MetadataSchema.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s %s' % (_('Not found'), _('Metadata Schema'), id_))
    context['metadata_schema'] = obj

    tk.check_access('metadata_schema_delete', context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete metadata schema %s') % obj.id

    obj.delete()
    model.repo.commit()


def metadata_model_delete(context, data_dict):
    """
    Delete a metadata model.

    You must be authorized to delete the metadata model.

    :param id: the id of the metadata model to delete
    :type id: string
    """
    log.info("Deleting metadata model: %r", data_dict)

    model = context['model']
    user = context['user']

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.MetadataModel.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s %s' % (_('Not found'), _('Metadata Model'), id_))
    context['metadata_model'] = obj

    tk.check_access('metadata_model_delete', context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete metadata model %s') % obj.id

    obj.delete()
    model.repo.commit()


def infrastructure_delete(context, data_dict):
    """
    Delete an infrastructure.

    You must be authorized to delete the infrastructure.

    :param id: the id of the infrastructure to delete
    :type id: string
    """
    log.info("Deleting infrastructure: %r", data_dict)
    tk.check_access('infrastructure_delete', context, data_dict)

    data_dict['type'] = 'infrastructure'
    context['invoked_api'] = 'infrastructure_delete'

    tk.get_action('group_delete')(context, data_dict)


def metadata_collection_delete(context, data_dict):
    """
    Delete a metadata collection.

    You must be authorized to delete the metadata collection.

    :param id: the id of the metadata collection to delete
    :type id: string
    """
    log.info("Deleting metadata collection: %r", data_dict)
    tk.check_access('metadata_collection_delete', context, data_dict)

    data_dict['type'] = 'metadata_collection'
    context['invoked_api'] = 'metadata_collection_delete'

    tk.get_action('group_delete')(context, data_dict)


def metadata_record_delete(context, data_dict):
    """
    Delete a metadata record.

    You must be authorized to delete the metadata record.

    :param id: the id of the metadata record to delete
    :type id: string
    """
    log.info("Deleting metadata record: %r", data_dict)
    tk.check_access('metadata_record_delete', context, data_dict)

    data_dict['type'] = 'metadata_record'
    context['invoked_api'] = 'metadata_record_delete'

    tk.get_action('package_delete')(context, data_dict)
