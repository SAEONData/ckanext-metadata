# encoding: utf-8

import logging
from paste.deploy.converters import asbool
from sqlalchemy import or_

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

    :param id: the id or name of the metadata schema
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

    :param id: the id or name of the metadata model
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
    Return a list of names of the site's infrastructures.

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
    Return a list of names of the site's metadata collections.

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

    :param id: the id or name of the metadata record
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

    context['package'] = obj
    metadata_record_dict = model_dictize.metadata_record_dictize(obj, context)

    result_dict, errors = tk.navl_validate(metadata_record_dict, schema.metadata_record_show_schema(), context)
    return result_dict


@tk.side_effect_free
def metadata_record_list(context, data_dict):
    """
    Return a list of names of the site's metadata records.

    :rtype: list of strings
    """
    log.debug("Retrieving metadata record list: %r", data_dict)
    tk.check_access('metadata_record_list', context, data_dict)

    data_dict['type'] = 'metadata_record'
    context['invoked_api'] = 'metadata_record_list'

    return tk.get_action('package_list')(context, data_dict)


@tk.side_effect_free
def metadata_record_validation_model_list(context, data_dict):
    """
    Return a list of metadata models to be used for validating a metadata record.

    This comprises the following:
    1. The default model defined for the record's metadata schema.
    2. A model for that schema (optionally) defined for the owner organization.
    3. Any models (optionally) defined for that schema for infrastructures linked to the record.

    :param id: the id or name of the metadata record
    :type id: string

    :rtype: list of dictionaries of metadata models, including the latest revision id of each
    """
    log.debug("Retrieving metadata models for metadata record validation: %r", data_dict)

    model = context['model']
    session = context['session']
    obj = context.get('metadata_record')
    if not obj:
        id_ = tk.get_or_bust(data_dict, 'id')
        obj = model.Package.get(id_)
        if obj is None or obj.type != 'metadata_record':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_validation_model_list', context, data_dict)

    id_ = obj.id
    organization_id = obj.owner_org
    infrastructure_ids = session.query(model.Group.id) \
        .join(model.Member, model.Group.id == model.Member.group_id) \
        .filter(model.Group.type == 'infrastructure') \
        .filter(model.Group.state == 'active') \
        .filter(model.Member.table_name == 'package') \
        .filter(model.Member.table_id == id_) \
        .filter(model.Member.state == 'active') \
        .all()
    infrastructure_ids = [infra_id for (infra_id,) in infrastructure_ids] + [None]
    metadata_schema_id = session.query(model.PackageExtra.value) \
        .filter_by(package_id=id_, key='metadata_schema_id').scalar()

    MetadataModel = ckanext_model.MetadataModel
    MetadataModelRevision = ckanext_model.MetadataModelRevision

    metadata_model_ids = session.query(MetadataModel.id) \
        .filter_by(metadata_schema_id=metadata_schema_id, state='active') \
        .filter(or_(MetadataModel.organization_id == organization_id, MetadataModel.organization_id == None)) \
        .filter(or_(MetadataModel.infrastructure_id == infra_id for infra_id in infrastructure_ids)) \
        .all()

    result = []
    for (metadata_model_id,) in metadata_model_ids:
        metadata_model_dict = tk.get_action('metadata_model_show')(context, {'id': metadata_model_id})
        metadata_model_dict['revision_id'] = session.query(MetadataModelRevision.revision_id) \
            .filter(MetadataModelRevision.id == metadata_model_id) \
            .order_by(MetadataModelRevision.revision_timestamp.desc()) \
            .first().scalar()
        result += [metadata_model_dict]

    return result


@tk.side_effect_free
def metadata_record_validation_activity_show(context, data_dict):
    """
    Return the latest validation activity for a metadata record.

    :param id: the id or name of the metadata record
    :type id: string

    :rtype: dictionary including activity detail list under 'details',
        or None if the record has never been validated
    """
    log.debug("Retrieving metadata record validation activity: %r", data_dict)

    model = context['model']
    session = context['session']
    obj = context.get('metadata_record')
    if not obj:
        id_ = tk.get_or_bust(data_dict, 'id')
        obj = model.Package.get(id_)
        if obj is None or obj.type != 'metadata_record':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_validation_activity_show', context, data_dict)

    id_ = obj.id
    activity = session.query(model.Activity) \
        .filter(model.Activity.object_id == id_) \
        .filter(model.Activity.activity_type == 'validate_metadata') \
        .order_by(model.Activity.timestamp.desc()) \
        .first()
    if not activity:
        return None

    return model_dictize.metadata_record_validation_activity_dictize(activity, context)


@tk.side_effect_free
def metadata_validity_check(context, data_dict):
    """
    Check the validity of a metadata dictionary against a metadata model.

    :param content_json: JSON dictionary of metadata record content
    :type content_json: string
    :param model_json: JSON dictionary defining a metadata model
    :type model_json: string

    :rtype: dictionary {
        'status': 'valid' | 'partially_valid' | 'invalid' | 'config_error'
        'errors': dictionary
    }
    """
    log.debug("Checking metadata validity")
    tk.check_access('metadata_validity_check', context, data_dict)

    model = context['model']
    session = context['session']

    content_json, model_json = tk.get_or_bust(data_dict, ['content_json', 'model_json'])

    raise NotImplementedError
