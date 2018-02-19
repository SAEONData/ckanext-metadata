# encoding: utf-8

import logging

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.logic import schema
from ckanext.metadata.lib.dictization import model_save
import ckanext.metadata.model as ckanext_model

log = logging.getLogger(__name__)


# NB: We allow partial updates unconditionally because this is consistent with
# how updating of "native" fields is done in CKAN. On the contrary, not allowing
# partial updates results in inconsistent behaviour between "native" and "extra"
# fields, and requires that the API user understands the inner workings of the system.

def metadata_schema_update(context, data_dict):
    """
    Update a metadata schema.

    You must be authorized to edit the metadata schema.

    It is recommended to call
    :py:func:`ckan.logic.action.get.metadata_schema_show`, make the desired changes to
    the result, and then call ``metadata_schema_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.metadata_schema_create`.

    :param id: the id of the metadata schema to update
    :type id: string

    :returns: the updated metadata schema (unless 'return_id_only' is set to True
              in the context, in which case just the metadata schema id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata schema: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.MetadataSchema.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s %s' % (_('Not found'), _('Metadata Schema'), id_))

    context['metadata_schema'] = obj
    context['allow_partial_update'] = True

    tk.check_access('metadata_schema_update', context, data_dict)

    data, errors = tk.navl_validate(data_dict, schema.metadata_schema_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_schema = model_save.metadata_schema_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update metadata schema %s') % metadata_schema.id

    if not defer_commit:
        model.repo.commit()

    output = metadata_schema.id if return_id_only \
        else tk.get_action('metadata_schema_show')(context, {'id': metadata_schema.id})
    return output


def metadata_model_update(context, data_dict):
    """
    Update a metadata model.

    You must be authorized to edit the metadata model.

    It is recommended to call
    :py:func:`ckan.logic.action.get.metadata_model_show`, make the desired changes to
    the result, and then call ``metadata_model_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.metadata_model_create`.

    :param id: the id of the metadata model to update
    :type id: string

    :returns: the updated metadata model (unless 'return_id_only' is set to True
              in the context, in which case just the metadata model id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata model: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.MetadataModel.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s %s' % (_('Not found'), _('Metadata Model'), id_))

    context['metadata_model'] = obj
    context['allow_partial_update'] = True

    tk.check_access('metadata_model_update', context, data_dict)

    data, errors = tk.navl_validate(data_dict, schema.metadata_model_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_model = model_save.metadata_model_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update metadata model %s') % metadata_model.id

    if not defer_commit:
        model.repo.commit()

    output = metadata_model.id if return_id_only \
        else tk.get_action('metadata_model_show')(context, {'id': metadata_model.id})
    return output


def infrastructure_update(context, data_dict):
    """
    Update an infrastructure.

    You must be authorized to edit the infrastructure.

    It is recommended to call
    :py:func:`ckan.logic.action.get.infrastructure_show`, make the desired changes to
    the result, and then call ``infrastructure_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.infrastructure_create`.

    :param id: the id or name of the infrastructure to update
    :type id: string

    :returns: the updated infrastructure (unless 'return_id_only' is set to True
              in the context, in which case just the infrastructure id will be returned)
    :rtype: dictionary
    """
    log.info("Updating infrastructure: %r", data_dict)
    tk.check_access('infrastructure_update', context, data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data_dict['type'] = 'infrastructure'
    data_dict['is_organization'] = False
    context['schema'] = schema.infrastructure_update_schema()
    context['invoked_api'] = 'infrastructure_update'
    context['defer_commit'] = True
    context['allow_partial_update'] = True

    infrastructure_dict = tk.get_action('group_update')(context, data_dict)

    if not defer_commit:
        model.repo.commit()

    output = infrastructure_dict['id'] if return_id_only \
        else tk.get_action('infrastructure_show')(context, {'id': infrastructure_dict['id']})
    return output


def metadata_collection_update(context, data_dict):
    """
    Update a metadata collection.

    You must be authorized to edit the metadata collection.

    It is recommended to call
    :py:func:`ckan.logic.action.get.metadata_collection_show`, make the desired changes to
    the result, and then call ``metadata_collection_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.metadata_collection_create`.

    :param id: the id or name of the metadata collection to update
    :type id: string

    :returns: the updated metadata collection (unless 'return_id_only' is set to True
              in the context, in which case just the collection id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata collection: %r", data_dict)
    tk.check_access('metadata_collection_update', context, data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data_dict['type'] = 'metadata_collection'
    data_dict['is_organization'] = False
    context['schema'] = schema.metadata_collection_update_schema()
    context['invoked_api'] = 'metadata_collection_update'
    context['defer_commit'] = True
    context['allow_partial_update'] = True

    metadata_collection_dict = tk.get_action('group_update')(context, data_dict)

    if not defer_commit:
        model.repo.commit()

    output = metadata_collection_dict['id'] if return_id_only \
        else tk.get_action('metadata_collection_show')(context, {'id': metadata_collection_dict['id']})
    return output


def metadata_record_update(context, data_dict):
    """
    Update a metadata record.

    You must be authorized to edit the metadata record.

    It is recommended to call
    :py:func:`ckan.logic.action.get.metadata_record_show`, make the desired changes to
    the result, and then call ``metadata_record_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.metadata_record_create`.

    :param id: the id of the metadata record to update
    :type id: string

    :returns: the updated metadata record (unless 'return_id_only' is set to True
              in the context, in which case just the record id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata record: %r", data_dict)
    tk.check_access('metadata_record_update', context, data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data_dict['type'] = 'metadata_record'
    context['schema'] = schema.metadata_record_update_schema()
    context['invoked_api'] = 'metadata_record_update'
    context['defer_commit'] = True
    context['return_id_only'] = True
    context['allow_partial_update'] = True

    metadata_record_id = tk.get_action('package_update')(context, data_dict)
    model_save.metadata_record_infrastructure_list_save(data_dict.get('infrastructures'), context)

    if not defer_commit:
        model.repo.commit()

    output = metadata_record_id if return_id_only \
        else tk.get_action('metadata_record_show')(context, {'id': metadata_record_id})
    return output
