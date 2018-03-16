# encoding: utf-8

import logging
from paste.deploy.converters import asbool

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.logic import schema
from ckanext.metadata.lib.dictization import model_dictize
import ckanext.metadata.model as ckanext_model

log = logging.getLogger(__name__)


@tk.side_effect_free
def metadata_schema_show(context, data_dict):
    """
    Return the details of a metadata schema.

    You must be authorized to view the metadata schema.

    :param id: the id of the metadata schema
    :type id: string

    :rtype: dictionary
    """
    log.debug("Retrieving metadata schema: %r", data_dict)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.MetadataSchema.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Schema')))

    tk.check_access('metadata_schema_show', context, data_dict)

    context['metadata_schema'] = obj
    metadata_schema_dict = model_dictize.metadata_schema_dictize(obj, context)

    result_dict, errors = tk.navl_validate(metadata_schema_dict, schema.metadata_schema_show_schema(), context)
    return result_dict


@tk.side_effect_free
def metadata_schema_list(context, data_dict):
    """
    Return a list of names of the site's metadata schemas.
    
    You must be authorized to list metadata schemas.
    
    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving metadata schema list: %r", data_dict)
    tk.check_access('metadata_schema_list', context, data_dict)
    
    session = context['session']
    all_fields = asbool(data_dict.get('all_fields'))
    
    metadata_schemas = session.query(ckanext_model.MetadataSchema).filter_by(state='active').all()
    result = []
    for metadata_schema in metadata_schemas:
        if all_fields:
            data_dict['id'] = metadata_schema.id
            result += [tk.get_action('metadata_schema_show')(context, data_dict)]
        else:
            result += [metadata_schema.name]

    return result


@tk.side_effect_free
def metadata_model_show(context, data_dict):
    """
    Return the details of a metadata model.

    You must be authorized to view the metadata model.

    :param id: the id of the metadata model
    :type id: string

    :rtype: dictionary
    """
    log.debug("Retrieving metadata model: %r", data_dict)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.MetadataModel.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Model')))

    tk.check_access('metadata_model_show', context, data_dict)

    context['metadata_model'] = obj
    metadata_model_dict = model_dictize.metadata_model_dictize(obj, context)

    result_dict, errors = tk.navl_validate(metadata_model_dict, schema.metadata_model_show_schema(), context)
    return result_dict


@tk.side_effect_free
def metadata_model_list(context, data_dict):
    """
    Return a list of names of the site's metadata models.

    You must be authorized to list metadata models.

    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving metadata model list: %r", data_dict)
    tk.check_access('metadata_model_list', context, data_dict)

    session = context['session']
    all_fields = asbool(data_dict.get('all_fields'))

    metadata_models = session.query(ckanext_model.MetadataModel).filter_by(state='active').all()
    result = []
    for metadata_model in metadata_models:
        if all_fields:
            data_dict['id'] = metadata_model.id
            result += [tk.get_action('metadata_model_show')(context, data_dict)]
        else:
            result += [metadata_model.name]

    return result


@tk.side_effect_free
def infrastructure_show(context, data_dict):
    """
    Return the details of an infrastructure.

    You must be authorized to view the infrastructure.

    :param id: the id or name of the infrastructure
    :type id: string

    :rtype: dictionary
    """
    log.debug("Retrieving infrastructure: %r", data_dict)

    model = context['model']
    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Group.get(id_)
    if obj is None or obj.type != 'infrastructure':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Infrastructure')))

    tk.check_access('infrastructure_show', context, data_dict)

    data_dict.update({
        'type': 'infrastructure',
        'include_datasets': False,
        'include_dataset_count': True,
        'include_extras': True,
        'include_tags': False,
        'include_users': False,
        'include_groups': False,
        'include_followers': False,
    })
    context['schema'] = schema.infrastructure_show_schema()
    context['invoked_api'] = 'infrastructure_show'

    return tk.get_action('group_show')(context, data_dict)


@tk.side_effect_free
def infrastructure_list(context, data_dict):
    """
    Return a list of the names of the site's infrastructures.

    You must be authorized to list infrastructures.

    :param all_fields: return group dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving infrastructure list: %r", data_dict)
    tk.check_access('infrastructure_list', context, data_dict)

    data_dict.update({
        'type': 'infrastructure',
        'include_dataset_count': True,
        'include_extras': True,
        'include_tags': False,
        'include_users': False,
        'include_groups': False,
    })
    context['invoked_api'] = 'infrastructure_list'
    
    return tk.get_action('group_list')(context, data_dict)


@tk.side_effect_free
def metadata_collection_show(context, data_dict):
    """
    Return the details of a metadata collection.

    You must be authorized to view the metadata collection.

    :param id: the id or name of the metadata collection
    :type id: string

    :rtype: dictionary
    """
    log.debug("Retrieving metadata collection: %r", data_dict)

    model = context['model']
    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Group.get(id_)
    if obj is None or obj.type != 'metadata_collection':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))

    tk.check_access('metadata_collection_show', context, data_dict)

    data_dict.update({
        'type': 'metadata_collection',
        'include_datasets': False,
        'include_dataset_count': True,
        'include_extras': True,
        'include_tags': False,
        'include_users': False,
        'include_groups': False,
        'include_followers': False,
    })
    context['schema'] = schema.metadata_collection_show_schema()
    context['invoked_api'] = 'metadata_collection_show'

    return tk.get_action('group_show')(context, data_dict)


@tk.side_effect_free
def metadata_collection_list(context, data_dict):
    """
    Return a list of the names of the site's metadata collections.

    You must be authorized to list metadata collections.

    :param all_fields: return group dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving metadata collection list: %r", data_dict)
    tk.check_access('metadata_collection_list', context, data_dict)

    data_dict.update({
        'type': 'metadata_collection',
        'include_dataset_count': True,
        'include_extras': True,
        'include_tags': False,
        'include_users': False,
        'include_groups': False,
    })
    context['invoked_api'] = 'metadata_collection_list'

    return tk.get_action('group_list')(context, data_dict)


@tk.side_effect_free
def metadata_record_show(context, data_dict):
    """
    Return the details of a metadata record.

    You must be authorized to view the metadata record.

    :param id: the id of the metadata record
    :type id: string

    :rtype: dictionary
    """
    log.debug("Retrieving metadata record: %r", data_dict)

    model = context['model']
    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Package.get(id_)
    if obj is None or obj.type != 'metadata_record':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_show', context, data_dict)

    data_dict['type'] = 'metadata_record'
    context['schema'] = schema.metadata_record_show_schema()
    context['invoked_api'] = 'metadata_record_show'

    return tk.get_action('package_show')(context, data_dict)
