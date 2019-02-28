# encoding: utf-8

import logging
from paste.deploy.converters import asbool
from sqlalchemy import or_
import json
import jsonpointer

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.logic import schema
from ckanext.metadata.common import METADATA_VALIDATION_ACTIVITY_TYPE, METADATA_WORKFLOW_ACTIVITY_TYPE
from ckanext.metadata.logic.metadata_validator import MetadataValidator
from ckanext.metadata.logic.workflow_validator import WorkflowValidator
from ckanext.metadata.lib.dictization import model_dictize
import ckanext.metadata.model as ckanext_model

log = logging.getLogger(__name__)


@tk.side_effect_free
def metadata_standard_show(context, data_dict):
    """
    Return the details of a metadata standard.

    :param id: the id or name of the metadata standard
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: dictionary
    """
    log.debug("Retrieving metadata standard: %r", data_dict)

    deserialize_json = asbool(data_dict.get('deserialize_json'))

    metadata_standard_id = tk.get_or_bust(data_dict, 'id')
    metadata_standard = ckanext_model.MetadataStandard.get(metadata_standard_id)
    if metadata_standard is not None:
        metadata_standard_id = metadata_standard.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Standard')))

    tk.check_access('metadata_standard_show', context, data_dict)

    context['metadata_standard'] = metadata_standard
    metadata_standard_dict = model_dictize.metadata_standard_dictize(metadata_standard, context)

    result_dict, errors = tk.navl_validate(metadata_standard_dict, schema.metadata_standard_show_schema(deserialize_json), context)
    return result_dict


@tk.side_effect_free
def metadata_standard_list(context, data_dict):
    """
    Return a list of names of the site's metadata standards.
    
    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving metadata standard list: %r", data_dict)
    tk.check_access('metadata_standard_list', context, data_dict)
    
    session = context['session']
    all_fields = asbool(data_dict.get('all_fields'))
    
    metadata_standards = session.query(ckanext_model.MetadataStandard.id, ckanext_model.MetadataStandard.name) \
        .filter_by(state='active') \
        .all()
    result = []
    for (id_, name) in metadata_standards:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('metadata_standard_show')(context, data_dict)]
        else:
            result += [name]

    return result


@tk.side_effect_free
def metadata_schema_show(context, data_dict):
    """
    Return the details of a metadata schema.

    :param id: the id or name of the metadata schema
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: dictionary
    """
    log.debug("Retrieving metadata schema: %r", data_dict)

    deserialize_json = asbool(data_dict.get('deserialize_json'))

    metadata_schema_id = tk.get_or_bust(data_dict, 'id')
    metadata_schema = ckanext_model.MetadataSchema.get(metadata_schema_id)
    if metadata_schema is not None:
        metadata_schema_id = metadata_schema.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Schema')))

    tk.check_access('metadata_schema_show', context, data_dict)

    context['metadata_schema'] = metadata_schema
    metadata_schema_dict = model_dictize.metadata_schema_dictize(metadata_schema, context)

    result_dict, errors = tk.navl_validate(metadata_schema_dict, schema.metadata_schema_show_schema(deserialize_json), context)
    return result_dict


@tk.side_effect_free
def metadata_schema_list(context, data_dict):
    """
    Return a list of names of the site's metadata schemas.

    :param metadata_standard_id: the id or name of the associated metadata standard (optional filter)
    :type metadata_standard_id: string
    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving metadata schema list: %r", data_dict)
    tk.check_access('metadata_schema_list', context, data_dict)

    session = context['session']
    metadata_standard_id = data_dict.get('metadata_standard_id')
    all_fields = asbool(data_dict.get('all_fields'))

    metadata_schemas_q = session.query(ckanext_model.MetadataSchema.id, ckanext_model.MetadataSchema.name) \
        .filter_by(state='active')

    if metadata_standard_id:
        metadata_standard = ckanext_model.MetadataStandard.get(metadata_standard_id)
        if metadata_standard is None or metadata_standard.state != 'active':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Standard')))
        metadata_standard_id = metadata_standard.id
        metadata_schemas_q = metadata_schemas_q.filter_by(metadata_standard_id=metadata_standard_id)

    metadata_schemas = metadata_schemas_q.all()
    result = []
    for (id_, name) in metadata_schemas:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('metadata_schema_show')(context, data_dict)]
        else:
            result += [name]

    return result


@tk.side_effect_free
def metadata_schema_dependent_record_list(context, data_dict):
    """
    Return a list of ids of metadata records that are dependent on the given
    metadata schema for validation.

    :param id: the id or name of the metadata schema
    :type id: string

    :rtype: list of strings
    """
    log.debug("Retrieving list of metadata records dependent on metadata schema: %r", data_dict)

    session = context['session']
    model = context['model']

    metadata_schema_id = tk.get_or_bust(data_dict, 'id')
    metadata_schema = ckanext_model.MetadataSchema.get(metadata_schema_id)
    if metadata_schema is not None:
        metadata_schema_id = metadata_schema.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Schema')))

    tk.check_access('metadata_schema_dependent_record_list', context, data_dict)

    q = session.query(model.Package.id) \
        .join(model.PackageExtra) \
        .filter(model.Package.state == 'active') \
        .filter(model.PackageExtra.key == 'metadata_standard_id') \
        .filter(model.PackageExtra.value == metadata_schema.metadata_standard_id)

    if metadata_schema.organization_id:
        q = q.filter(model.Package.owner_org == metadata_schema.organization_id)

    if metadata_schema.infrastructure_id:
        q = q.join(model.Member, model.Member.table_id == model.Package.id) \
            .filter(model.Member.table_name == 'package') \
            .filter(model.Member.state == 'active') \
            .join(model.Group, model.Group.id == model.Member.group_id) \
            .filter(model.Group.type == 'infrastructure') \
            .filter(model.Group.state == 'active') \
            .filter(model.Group.id == metadata_schema.infrastructure_id)

    return [metadata_record_id for (metadata_record_id,) in q.all()]


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

    infrastructure_id = tk.get_or_bust(data_dict, 'id')
    infrastructure = model.Group.get(infrastructure_id)
    if infrastructure is not None and infrastructure.type == 'infrastructure':
        infrastructure_id = infrastructure.id
    else:
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
        'include_followers': True,
    })
    context.update({
        'schema': schema.infrastructure_show_schema(),
        'invoked_action': 'infrastructure_show',
    })

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

    model = context['model']
    session = context['session']
    all_fields = asbool(data_dict.get('all_fields'))

    infrastructures = session.query(model.Group.id, model.Group.name) \
        .filter_by(type='infrastructure', state='active') \
        .all()
    result = []
    for (id_, name) in infrastructures:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('infrastructure_show')(context, data_dict)]
        else:
            result += [name]

    return result


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

    metadata_collection_id = tk.get_or_bust(data_dict, 'id')
    metadata_collection = model.Group.get(metadata_collection_id)
    if metadata_collection is not None and metadata_collection.type == 'metadata_collection':
        metadata_collection_id = metadata_collection.id
    else:
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
        'include_followers': True,
    })
    context.update({
        'schema': schema.metadata_collection_show_schema(),
        'invoked_action': 'metadata_collection_show',
    })

    return tk.get_action('group_show')(context, data_dict)


@tk.side_effect_free
def metadata_collection_list(context, data_dict):
    """
    Return a list of names of the site's metadata collections.

    :param owner_org: the id or name of the organization that owns the collections (optional filter)
    :type owner_org: string
    :param all_fields: return group dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving metadata collection list: %r", data_dict)
    tk.check_access('metadata_collection_list', context, data_dict)

    model = context['model']
    session = context['session']

    owner_org = data_dict.get('owner_org')
    all_fields = asbool(data_dict.get('all_fields'))

    metadata_collections_q = session.query(model.Group.id, model.Group.name) \
        .filter_by(type='metadata_collection', state='active')

    if owner_org:
        organization = model.Group.get(owner_org)
        if organization is None or \
                organization.type != 'organization' or \
                organization.state != 'active':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Organization')))
        owner_org = organization.id
        metadata_collections_q = metadata_collections_q.join(model.GroupExtra) \
            .filter(model.GroupExtra.key == 'organization_id') \
            .filter(model.GroupExtra.value == owner_org)

    metadata_collections = metadata_collections_q.all()
    result = []
    for (id_, name) in metadata_collections:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('metadata_collection_show')(context, data_dict)]
        else:
            result += [name]

    return result


@tk.side_effect_free
def metadata_record_show(context, data_dict):
    """
    Return the details of a metadata record.

    :param id: the id or name of the metadata record
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: dictionary
    """
    log.debug("Retrieving metadata record: %r", data_dict)

    model = context['model']
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_show', context, data_dict)

    context['package'] = metadata_record
    metadata_record_dict = model_dictize.metadata_record_dictize(metadata_record, context)

    result_dict, errors = tk.navl_validate(metadata_record_dict, schema.metadata_record_show_schema(deserialize_json), context)
    return result_dict


@tk.side_effect_free
def metadata_record_list(context, data_dict):
    """
    Return a list of names of the site's metadata records.

    :param ids: a list of ids and/or names of metadata records to return (optional filter)
    :type ids: list of strings
    :param owner_org: the id or name of the organization that owns the records (optional filter)
    :type owner_org: string
    :param metadata_collection_id: the id or name of the metadata collection to which the records
        belong (optional filter; if specified, owner_org must also be supplied)
    :type metadata_collection_id: string
    :param infrastructure_id: the id or name of an associated infrastructure (optional filter)
    :type infrastructure_id: string
    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving metadata record list: %r", data_dict)
    tk.check_access('metadata_record_list', context, data_dict)

    model = context['model']
    session = context['session']

    # if this is a GET request and exactly one id has been provided, then ids arrives
    # as a string instead of a single-element list containing the id string
    ids = data_dict.get('ids')
    if ids and isinstance(ids, basestring):
        ids = [ids]

    owner_org = data_dict.get('owner_org')
    metadata_collection_id = data_dict.get('metadata_collection_id')
    infrastructure_id = data_dict.get('infrastructure_id')
    all_fields = asbool(data_dict.get('all_fields'))

    metadata_records_q = session.query(model.Package.id, model.Package.name) \
        .filter_by(type='metadata_record', state='active')

    if ids:
        metadata_records_q = metadata_records_q.filter(or_(
            model.Package.id.in_(ids), model.Package.name.in_(ids)))

    if owner_org:
        organization = model.Group.get(owner_org)
        if organization is None or \
                organization.type != 'organization' or \
                organization.state != 'active':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Organization')))
        owner_org = organization.id
        metadata_records_q = metadata_records_q.filter_by(owner_org=owner_org)

    if metadata_collection_id:
        metadata_collection = model.Group.get(metadata_collection_id)
        if metadata_collection is None or \
                metadata_collection.type != 'metadata_collection' or \
                metadata_collection.state != 'active':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))
        metadata_collection_id = metadata_collection.id

        metadata_collection_organization_id = session.query(model.GroupExtra.value) \
            .filter_by(group_id=metadata_collection_id, key='organization_id').scalar()
        if owner_org != metadata_collection_organization_id:
            raise tk.ValidationError(_("owner_org must be the same organization that owns the metadata collection"))

        metadata_records_q = metadata_records_q.join(model.PackageExtra) \
            .filter(model.PackageExtra.key == 'metadata_collection_id') \
            .filter(model.PackageExtra.value == metadata_collection_id)

    if infrastructure_id:
        infrastructure = model.Group.get(infrastructure_id)
        if infrastructure is None or \
                infrastructure.type != 'infrastructure' or \
                infrastructure.state != 'active':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Infrastructure')))
        infrastructure_id = infrastructure.id

        metadata_records_q = metadata_records_q.join(model.Member, model.Package.id==model.Member.table_id) \
            .filter(model.Member.group_id == infrastructure_id) \
            .filter(model.Member.table_name == 'package') \
            .filter(model.Member.state == 'active')

    metadata_records = metadata_records_q.all()
    result = []
    for (id_, name) in metadata_records:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('metadata_record_show')(context, data_dict)]
        else:
            result += [name]

    return result


@tk.side_effect_free
def metadata_record_attr_match(context, data_dict):
    """
    Return the id of a metadata record that unambiguously matches all the supplied attribute
    name-value pairs, or None if not found. If there is any ambiguity, a validation error is
    raised.

    :rtype: string
    """
    log.debug("Retrieving metadata record that matches on key attributes: %r", data_dict)
    tk.check_access('metadata_record_attr_match', context, data_dict)

    model = context['model']
    session = context['session']

    matching_record_id = None
    is_valid = True
    for i, (attr_name, attr_value) in enumerate(data_dict.iteritems()):
        record_list = session.query(model.Package.id) \
            .filter_by(type='metadata_record', state='active') \
            .filter_by(**{attr_name: attr_value}) \
            .all()
        record_list = [id_ for (id_,) in record_list]

        if len(record_list) > 1:
            # this situation might arise if, for example, records were created before setting up
            # JSON attribute mappings for the specified key attributes
            raise tk.ValidationError(_("Multiple records already exist with the value '%s' for the key attribute '%s'")
                                     % (attr_value, attr_name))
        if i == 0:
            # first iteration decides whether or not we have a match;
            # the remaining iterations must match (or not) in exactly the same way
            if len(record_list) == 1:
                matching_record_id = record_list[0]
        elif matching_record_id is not None:
            is_valid = is_valid and len(record_list) == 1 and record_list[0] == matching_record_id
        else:
            is_valid = is_valid and len(record_list) == 0

        if not is_valid:
            raise tk.ValidationError(_("Cannot unambiguously match an existing record for the given key attribute values"))

    return matching_record_id


@tk.side_effect_free
def metadata_record_validation_schema_list(context, data_dict):
    """
    Return a list of metadata schemas to be used for validating a metadata record.

    This comprises the following:
    1. The default schema defined for the record's metadata standard.
    2. A schema for that standard (optionally) defined for the owner organization.
    3. Any schemas (optionally) defined for that standard for infrastructures linked to the record.

    :param id: the id or name of the metadata record
    :type id: string
    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: list of names (dictionaries if all_fields) of metadata schemas
    """
    log.debug("Retrieving metadata schemas for metadata record validation: %r", data_dict)

    model = context['model']
    session = context['session']
    metadata_record = context.get('metadata_record')
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    if metadata_record:
        metadata_record_id = metadata_record.id
    else:
        metadata_record_id = tk.get_or_bust(data_dict, 'id')
        metadata_record = model.Package.get(metadata_record_id)
        if metadata_record is not None and metadata_record.type == 'metadata_record':
            metadata_record_id = metadata_record.id
        else:
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_validation_schema_list', context, data_dict)

    organization_id = metadata_record.owner_org
    infrastructure_ids = session.query(model.Group.id) \
        .join(model.Member, model.Group.id == model.Member.group_id) \
        .filter(model.Group.type == 'infrastructure') \
        .filter(model.Group.state == 'active') \
        .filter(model.Member.table_name == 'package') \
        .filter(model.Member.table_id == metadata_record_id) \
        .filter(model.Member.state == 'active') \
        .all()
    infrastructure_ids = [infra_id for (infra_id,) in infrastructure_ids] + [None]
    metadata_standard_id = session.query(model.PackageExtra.value) \
        .filter_by(package_id=metadata_record_id, key='metadata_standard_id').scalar()

    MetadataSchema = ckanext_model.MetadataSchema
    metadata_schema_names = session.query(MetadataSchema.name) \
        .filter_by(metadata_standard_id=metadata_standard_id, state='active') \
        .filter(or_(MetadataSchema.organization_id == organization_id, MetadataSchema.organization_id == None)) \
        .filter(or_(MetadataSchema.infrastructure_id == infra_id for infra_id in infrastructure_ids)) \
        .all()

    result = []
    all_fields = asbool(data_dict.get('all_fields'))
    for (metadata_schema_name,) in metadata_schema_names:
        if all_fields:
            result += [tk.get_action('metadata_schema_show')(context, {'id': metadata_schema_name, 'deserialize_json': deserialize_json})]
        else:
            result += [metadata_schema_name]

    return result


@tk.side_effect_free
def metadata_record_validation_activity_show(context, data_dict):
    """
    Return the latest validation activity for a metadata record.

    :param id: the id or name of the metadata record
    :type id: string

    :rtype: dictionary, or None if the record has never been validated
    """
    log.debug("Retrieving metadata record validation activity: %r", data_dict)

    model = context['model']
    session = context['session']
    metadata_record = context.get('metadata_record')

    if metadata_record:
        metadata_record_id = metadata_record.id
    else:
        metadata_record_id = tk.get_or_bust(data_dict, 'id')
        metadata_record = model.Package.get(metadata_record_id)
        if metadata_record is not None and metadata_record.type == 'metadata_record':
            metadata_record_id = metadata_record.id
        else:
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_validation_activity_show', context, data_dict)

    activity = session.query(model.Activity) \
        .filter_by(object_id=metadata_record_id, activity_type=METADATA_VALIDATION_ACTIVITY_TYPE) \
        .order_by(model.Activity.timestamp.desc()) \
        .first()
    if not activity:
        return None

    return model_dictize.metadata_record_activity_dictize(activity, context)


@tk.side_effect_free
def metadata_validity_check(context, data_dict):
    """
    Check the validity of a metadata dictionary against a metadata schema.

    :param metadata_json: JSON dictionary of metadata record content
    :type metadata_json: string
    :param schema_json: JSON dictionary defining a metadata schema
    :type schema_json: string

    :rtype: dictionary of metadata errors; empty dict implies that the metadata is 100% valid
        against the given schema
    """
    log.debug("Checking metadata validity")
    tk.check_access('metadata_validity_check', context, data_dict)

    session = context['session']
    data, errors = tk.navl_validate(data_dict, schema.metadata_validity_check_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_dict = json.loads(data['metadata_json'])
    schema_dict = json.loads(data['schema_json'])

    metadata_errors = MetadataValidator(schema_dict).validate(metadata_dict)
    return metadata_errors


@tk.side_effect_free
def metadata_record_workflow_rules_check(context, data_dict):
    """
    Evaluate whether a metadata record passes the rules for a workflow state.

    :param metadata_record_json: JSON dictionary representation of a metadata record object,
        optionally augmented with workflow annotations
    :type metadata_record_json: string
    :param workflow_rules_json: JSON schema defining the workflow rules
    :type workflow_rules_json: string

    :rtype: dictionary of errors; empty dict implies that the metadata record is 100% valid
        against the given rules
    """
    log.debug("Checking metadata record against workflow rules", data_dict)
    tk.check_access('metadata_record_workflow_rules_check', context, data_dict)

    session = context['session']
    data, errors = tk.navl_validate(data_dict, schema.metadata_record_workflow_rules_check_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_record_dict = json.loads(data['metadata_record_json'])
    workflow_rules_dict = json.loads(data['workflow_rules_json'])

    workflow_errors = WorkflowValidator(workflow_rules_dict).validate(metadata_record_dict)
    return workflow_errors


@tk.side_effect_free
def metadata_record_workflow_activity_show(context, data_dict):
    """
    Return the latest workflow activity for a metadata record.

    :param id: the id or name of the metadata record
    :type id: string

    :rtype: dictionary including activity detail list under 'details',
        or None if the record has not yet been assigned a workflow state
    """
    log.debug("Retrieving metadata record workflow activity: %r", data_dict)

    model = context['model']
    session = context['session']
    metadata_record = context.get('metadata_record')

    if metadata_record:
        metadata_record_id = metadata_record.id
    else:
        metadata_record_id = tk.get_or_bust(data_dict, 'id')
        metadata_record = model.Package.get(metadata_record_id)
        if metadata_record is not None and metadata_record.type == 'metadata_record':
            metadata_record_id = metadata_record.id
        else:
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_workflow_activity_show', context, data_dict)

    activity = session.query(model.Activity) \
        .filter_by(object_id=metadata_record_id, activity_type=METADATA_WORKFLOW_ACTIVITY_TYPE) \
        .order_by(model.Activity.timestamp.desc()) \
        .first()
    if not activity:
        return None

    return model_dictize.metadata_record_activity_dictize(activity, context)


@tk.side_effect_free
def metadata_record_workflow_annotation_show(context, data_dict):
    """
    Return the details of a workflow annotation associated with a metadata record.

    :param id: the id or name of the metadata record
    :type id: string
    :param key: the annotation key
    :type key: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: dictionary, which is a facade to the underlying JSONPatch object
    """
    log.debug("Retrieving workflow annotation for metadata record: %r", data_dict)
    tk.check_access('metadata_record_workflow_annotation_show', context, data_dict)

    key = tk.get_or_bust(data_dict, 'key')
    annotation_list = metadata_record_workflow_annotation_list(context, data_dict)

    # ordinarily there should only be one annotation with the given key; we pick it with `next`;
    # it's possible for multiple annotations with the same key to exist if applicable jsonpatches
    # were created directly using the ckanext-jsonpatch API
    return next((annotation for annotation in annotation_list if annotation['key'] == key), None)


@tk.side_effect_free
def metadata_record_workflow_annotation_list(context, data_dict):
    """
    Return a list of workflow annotations associated with a metadata record.

    :param id: the id or name of the metadata record
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: list of dicts
    """
    log.debug("Retrieving workflow annotations for metadata record: %r", data_dict)

    model = context['model']
    metadata_record = context.get('metadata_record')

    if metadata_record:
        metadata_record_id = metadata_record.id
    else:
        metadata_record_id = tk.get_or_bust(data_dict, 'id')
        metadata_record = model.Package.get(metadata_record_id)
        if metadata_record is not None and metadata_record.type == 'metadata_record':
            metadata_record_id = metadata_record.id
        else:
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_workflow_annotation_list', context, data_dict)

    deserialize_json = asbool(data_dict.get('deserialize_json'))
    jsonpatch_context = context.copy()
    jsonpatch_context['schema'] = schema.metadata_record_workflow_annotation_show_schema(deserialize_json)
    jsonpatch_data = {
        'model_name': 'metadata_record',
        'object_id': metadata_record_id,
        'scope': 'workflow',
        'all_fields': True,
    }
    return tk.get_action('jsonpatch_list')(jsonpatch_context, jsonpatch_data)


@tk.side_effect_free
def metadata_record_workflow_augmented_show(context, data_dict):
    """
    Return a metadata record dictionary augmented with workflow annotations.

    This is a convenience function which wraps jsonpatch_apply.

    :param id: the id or name of the metadata record
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: dictionary
    """
    log.debug("Retrieving workflow-augmented metadata record: %r", data_dict)

    model = context['model']
    metadata_record = context.get('metadata_record')
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    if metadata_record:
        metadata_record_id = metadata_record.id
    else:
        metadata_record_id = tk.get_or_bust(data_dict, 'id')
        metadata_record = model.Package.get(metadata_record_id)
        if metadata_record is not None and metadata_record.type == 'metadata_record':
            metadata_record_id = metadata_record.id
        else:
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_workflow_augmented_show', context, data_dict)

    jsonpatch_params = {
        'model_name': 'metadata_record',
        'object_id': metadata_record_id,
        'scope': 'workflow',
        'kwargs': {'deserialize_json': deserialize_json}
    }
    return tk.get_action('jsonpatch_apply')(context, jsonpatch_params)


@tk.side_effect_free
def workflow_state_show(context, data_dict):
    """
    Return a workflow state definition.

    :param id: the id or name of the workflow state
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: dictionary
    """
    log.debug("Retrieving workflow state: %r", data_dict)

    deserialize_json = asbool(data_dict.get('deserialize_json'))

    workflow_state_id = tk.get_or_bust(data_dict, 'id')
    workflow_state = ckanext_model.WorkflowState.get(workflow_state_id)
    if workflow_state is not None:
        workflow_state_id = workflow_state.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('workflow_state_show', context, data_dict)

    context['workflow_state'] = workflow_state
    workflow_state_dict = model_dictize.workflow_state_dictize(workflow_state, context)

    result_dict, errors = tk.navl_validate(workflow_state_dict, schema.workflow_state_show_schema(deserialize_json), context)
    return result_dict


@tk.side_effect_free
def workflow_state_list(context, data_dict):
    """
    Return a list of names of the site's workflow states.

    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving workflow state list: %r", data_dict)
    tk.check_access('workflow_state_list', context, data_dict)

    session = context['session']
    all_fields = asbool(data_dict.get('all_fields'))

    workflow_states = session.query(ckanext_model.WorkflowState.id, ckanext_model.WorkflowState.name) \
        .filter_by(state='active') \
        .all()
    result = []
    for (id_, name) in workflow_states:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('workflow_state_show')(context, data_dict)]
        else:
            result += [name]

    return result


@tk.side_effect_free
def workflow_transition_show(context, data_dict):
    """
    Return a workflow transition definition.

    :param id: the id of the workflow transition
    :type id: string

    :rtype: dictionary
    """
    log.debug("Retrieving workflow transition: %r", data_dict)

    workflow_transition_id = tk.get_or_bust(data_dict, 'id')
    workflow_transition = ckanext_model.WorkflowTransition.get(workflow_transition_id)
    if workflow_transition is not None:
        workflow_transition_id = workflow_transition.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Transition')))

    tk.check_access('workflow_transition_show', context, data_dict)

    context['workflow_transition'] = workflow_transition
    workflow_transition_dict = model_dictize.workflow_transition_dictize(workflow_transition, context)

    result_dict, errors = tk.navl_validate(workflow_transition_dict, schema.workflow_transition_show_schema(), context)
    return result_dict


@tk.side_effect_free
def workflow_transition_list(context, data_dict):
    """
    Return a list of ids of the site's workflow transitions.

    :param all_fields: return dictionaries instead of just ids (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving workflow transition list: %r", data_dict)
    tk.check_access('workflow_transition_list', context, data_dict)

    session = context['session']
    all_fields = asbool(data_dict.get('all_fields'))

    workflow_transitions = session.query(ckanext_model.WorkflowTransition.id) \
        .filter_by(state='active') \
        .all()
    result = []
    for (id_,) in workflow_transitions:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('workflow_transition_show')(context, data_dict)]
        else:
            result += [id_]

    return result


@tk.side_effect_free
def workflow_annotation_show(context, data_dict):
    """
    Return a workflow annotation definition.

    :param id: the id of the workflow annotation
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: dictionary
    """
    log.debug("Retrieving workflow annotation: %r", data_dict)

    deserialize_json = asbool(data_dict.get('deserialize_json'))

    workflow_annotation_id = tk.get_or_bust(data_dict, 'id')
    workflow_annotation = ckanext_model.WorkflowAnnotation.get(workflow_annotation_id)
    if workflow_annotation is not None:
        workflow_annotation_id = workflow_annotation.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Annotation')))

    tk.check_access('workflow_annotation_show', context, data_dict)

    context['workflow_annotation'] = workflow_annotation
    workflow_annotation_dict = model_dictize.workflow_annotation_dictize(workflow_annotation, context)

    result_dict, errors = tk.navl_validate(workflow_annotation_dict, schema.workflow_annotation_show_schema(deserialize_json), context)
    return result_dict


@tk.side_effect_free
def workflow_annotation_list(context, data_dict):
    """
    Return a list of ids of the site's workflow annotations.

    :param all_fields: return dictionaries instead of just ids (optional, default: ``False``)
    :type all_fields: boolean
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving workflow annotation list: %r", data_dict)
    tk.check_access('workflow_annotation_list', context, data_dict)

    session = context['session']
    all_fields = asbool(data_dict.get('all_fields'))

    workflow_annotations = session.query(ckanext_model.WorkflowAnnotation.id) \
        .filter_by(state='active') \
        .all()
    result = []
    for (id_,) in workflow_annotations:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('workflow_annotation_show')(context, data_dict)]
        else:
            result += [id_]

    return result


@tk.side_effect_free
def metadata_json_attr_map_show(context, data_dict):
    """
    Return a metadata JSON attribute map definition.

    :param id: the id of the metadata JSON attribute map
    :type id: string

    :rtype: dictionary
    """
    log.debug("Retrieving metadata JSON attribute map: %r", data_dict)

    metadata_json_attr_map_id = tk.get_or_bust(data_dict, 'id')
    metadata_json_attr_map = ckanext_model.MetadataJSONAttrMap.get(metadata_json_attr_map_id)
    if metadata_json_attr_map is not None:
        metadata_json_attr_map_id = metadata_json_attr_map.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata JSON Attribute Map')))

    tk.check_access('metadata_json_attr_map_show', context, data_dict)

    context['metadata_json_attr_map'] = metadata_json_attr_map
    metadata_json_attr_map_dict = model_dictize.metadata_json_attr_map_dictize(metadata_json_attr_map, context)

    result_dict, errors = tk.navl_validate(metadata_json_attr_map_dict, schema.metadata_json_attr_map_show_schema(), context)
    return result_dict


@tk.side_effect_free
def metadata_json_attr_map_list(context, data_dict):
    """
    Return a list of ids of the metadata JSON attribute maps for a metadata standard.

    :param metadata_standard_id: the id or name of the metadata standard
    :type metadata_standard_id: string
    :param all_fields: return dictionaries instead of just ids (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving metadata JSON attribute map list: %r", data_dict)

    session = context['session']
    all_fields = asbool(data_dict.get('all_fields'))

    metadata_standard_id = tk.get_or_bust(data_dict, 'metadata_standard_id')
    metadata_standard = ckanext_model.MetadataStandard.get(metadata_standard_id)
    if metadata_standard is not None:
        metadata_standard_id = metadata_standard.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Standard')))

    tk.check_access('metadata_json_attr_map_list', context, data_dict)

    metadata_json_attr_maps = session.query(ckanext_model.MetadataJSONAttrMap.id) \
        .filter_by(metadata_standard_id=metadata_standard_id) \
        .filter_by(state='active') \
        .all()
    result = []
    for (id_,) in metadata_json_attr_maps:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('metadata_json_attr_map_show')(context, data_dict)]
        else:
            result += [id_]

    return result


@tk.side_effect_free
def metadata_json_attr_map_apply(context, data_dict):
    """
    Construct a (partial) data dictionary for creating/updating a metadata record by
    mapping values from the given metadata JSON document, using the metadata JSON
    attribute maps that have been defined for the given metadata standard.

    Note that missing or empty elements in the JSON are not copied into the resultant
    data_dict. However, the resultant key_dict includes every key attribute mapping,
    regardless of whether the source element is present or not.

    :param metadata_standard_id: the id or name of the metadata standard
    :type metadata_standard_id: string
    :param metadata_json: JSON dictionary of metadata content
    :type metadata_json: string

    :rtype: dictionary {
                'data_dict': dict of mapped attribute-value pairs, excluding empties
                'key_dict': dict of key mapped attribute-value pairs, including empties
            }
    """
    log.debug("Applying metadata JSON attribute mappings to metadata dict: %r", data_dict)
    tk.check_access('metadata_json_attr_map_apply', context, data_dict)

    session = context['session']
    data, errors = tk.navl_validate(data_dict, schema.metadata_json_attr_map_apply_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_standard_id = data['metadata_standard_id']
    metadata_dict = json.loads(data['metadata_json'])

    metadata_json_attr_maps = session.query(ckanext_model.MetadataJSONAttrMap) \
        .filter_by(metadata_standard_id=metadata_standard_id) \
        .filter_by(state='active') \
        .all()

    result = {
        'data_dict': {},
        'key_dict': {},
    }
    for metadata_json_attr_map in metadata_json_attr_maps:
        attr = metadata_json_attr_map.record_attr
        path = metadata_json_attr_map.json_path
        is_key = metadata_json_attr_map.is_key

        # empty or non-existent elements are mapped to empty strings
        try:
            value = jsonpointer.resolve_pointer(metadata_dict, path) or ''
        except jsonpointer.JsonPointerException:
            value = ''

        if value:
            result['data_dict'][attr] = value
        if is_key:
            result['key_dict'][attr] = value

    return result


@tk.side_effect_free
def metadata_standard_index_show(context, data_dict):
    """
    Placeholder function for retrieving the document structure of a metadata search index.
    May be implemented as required by another plugin.

    :param id: the id or name of the metadata standard
    :type id: string
    """
    tk.check_access('metadata_standard_index_show', context, data_dict)


@tk.side_effect_free
def metadata_record_index_show(context, data_dict):
    """
    Placeholder function for retrieving the indexed version of a metadata record.
    May be implemented as required by another plugin.

    :param id: the id or name of the metadata record
    :type id: string
    """
    tk.check_access('metadata_record_index_show', context, data_dict)
