# encoding: utf-8

import logging

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.logic import schema
from ckanext.metadata.lib.dictization import model_save
import ckanext.metadata.model as ckanext_model

log = logging.getLogger(__name__)


# NB: We allow partial updates unconditionally because this is consistent with how
# updating of "native" fields is handled in CKAN: fields are left at their current
# values when parameters are missing from the input (where permitted by ignore_missing
# in the schema). On the contrary, not allowing partial updates can result in data
# (extras, members, etc) being deleted if "list" type params are missing from the input,
# and correct use of the 'allow_partial_update' option would require the caller to
# understand the inner workings of the system.

# The extras saving mechanism is flawed. If a schema defines two "extra" fields, say
# field1 and field2, then these would be left unchanged if neither is supplied by the
# caller on update (assuming we're allowing partial updates). However, if only field1
# is supplied, then field2 ends up being deleted because all extras are lumped together
# in the same list. Again, this requires the caller to understand the inner workings
# of the system - in particular, to know that field1 and field2 are "extra" rather
# than "native". The only way to avoid this problem is to ensure that "extra" fields
# are validated as not_missing in the schema.

# Fields indicated as "optional" in the docstrings remain at their current values if
# not supplied by the caller.

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
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Schema')))

    tk.check_access('metadata_schema_update', context, data_dict)

    context['metadata_schema'] = obj
    context['allow_partial_update'] = True

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
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Model')))

    tk.check_access('metadata_model_update', context, data_dict)

    context['metadata_model'] = obj
    context['allow_partial_update'] = True

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
    :param name: the name of the infrastructure (optional)
    :type name: string

    :returns: the updated infrastructure (unless 'return_id_only' is set to True
              in the context, in which case just the infrastructure id will be returned)
    :rtype: dictionary
    """
    log.info("Updating infrastructure: %r", data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Group.get(id_)
    if obj is None or obj.type != 'infrastructure':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Infrastructure')))

    tk.check_access('infrastructure_update', context, data_dict)

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
    :param name: the name of the metadata collection (optional)
    :type name: string

    :returns: the updated metadata collection (unless 'return_id_only' is set to True
              in the context, in which case just the collection id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata collection: %r", data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Group.get(id_)
    if obj is None or obj.type != 'metadata_collection':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))

    tk.check_access('metadata_collection_update', context, data_dict)

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
    :param name: the name of the metadata record (optional)
    :type name: string

    :returns: the updated metadata record (unless 'return_id_only' is set to True
              in the context, in which case just the record id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata record: %r", data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Package.get(id_)
    if obj is None or obj.type != 'metadata_record':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_update', context, data_dict)

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
