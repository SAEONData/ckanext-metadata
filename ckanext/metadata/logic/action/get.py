# encoding: utf-8

import logging
from paste.deploy.converters import asbool
from sqlalchemy import or_
import json

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.logic import schema, METADATA_VALIDATION_ACTIVITY_TYPE, METADATA_WORKFLOW_ACTIVITY_TYPE
from ckanext.metadata.lib.dictization import model_dictize
from ckanext.metadata import jsonschema_validation
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

    metadata_schema_id = tk.get_or_bust(data_dict, 'id')
    metadata_schema = ckanext_model.MetadataSchema.get(metadata_schema_id)
    if metadata_schema is not None:
        metadata_schema_id = metadata_schema.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Schema')))

    tk.check_access('metadata_schema_show', context, data_dict)

    context['metadata_schema'] = metadata_schema
    metadata_schema_dict = model_dictize.metadata_schema_dictize(metadata_schema, context)

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
    
    metadata_schemas = session.query(ckanext_model.MetadataSchema.id, ckanext_model.MetadataSchema.name) \
        .filter_by(state='active') \
        .all()
    result = []
    for (id_, name) in metadata_schemas:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('metadata_schema_show')(context, data_dict)]
        else:
            result += [name]

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

    metadata_model_id = tk.get_or_bust(data_dict, 'id')
    metadata_model = ckanext_model.MetadataModel.get(metadata_model_id)
    if metadata_model is not None:
        metadata_model_id = metadata_model.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Model')))

    tk.check_access('metadata_model_show', context, data_dict)

    context['metadata_model'] = metadata_model
    metadata_model_dict = model_dictize.metadata_model_dictize(metadata_model, context)

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

    metadata_models = session.query(ckanext_model.MetadataModel.id, ckanext_model.MetadataModel.name) \
        .filter_by(state='active') \
        .all()
    result = []
    for (id_, name) in metadata_models:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('metadata_model_show')(context, data_dict)]
        else:
            result += [name]

    return result


@tk.side_effect_free
def metadata_model_dependent_record_list(context, data_dict):
    """
    Return a list of ids of metadata records that are dependent on the given
    metadata model for validation.

    :param id: the id or name of the metadata model
    :type id: string

    :rtype: list of strings
    """
    log.debug("Retrieving list of metadata records dependent on metadata model: %r", data_dict)

    session = context['session']
    model = context['model']

    metadata_model_id = tk.get_or_bust(data_dict, 'id')
    metadata_model = ckanext_model.MetadataModel.get(metadata_model_id)
    if metadata_model is not None:
        metadata_model_id = metadata_model.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Model')))

    tk.check_access('metadata_model_dependent_record_list', context, data_dict)

    q = session.query(model.Package.id) \
        .join(model.PackageExtra) \
        .filter(model.Package.state == 'active') \
        .filter(model.PackageExtra.key == 'metadata_schema_id') \
        .filter(model.PackageExtra.value == metadata_model.metadata_schema_id)

    if metadata_model.organization_id:
        q = q.filter(model.Package.owner_org == metadata_model.organization_id)

    if metadata_model.infrastructure_id:
        q = q.join(model.Member, model.Member.table_id == model.Package.id) \
            .filter(model.Member.table_name == 'package') \
            .filter(model.Member.state == 'active') \
            .join(model.Group, model.Group.id == model.Member.group_id) \
            .filter(model.Group.type == 'infrastructure') \
            .filter(model.Group.state == 'active') \
            .filter(model.Group.id == metadata_model.infrastructure_id)

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
        'include_followers': False,
    })
    context.update({
        'schema': schema.infrastructure_show_schema(),
        'invoked_api': 'infrastructure_show',
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

    data_dict.update({
        'type': 'infrastructure',
        'include_dataset_count': True,
        'include_extras': True,
        'include_tags': False,
        'include_users': False,
        'include_groups': False,
    })
    context.update({
        'invoked_api': 'infrastructure_list',
    })
    
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
        'include_followers': False,
    })
    context.update({
        'schema': schema.metadata_collection_show_schema(),
        'invoked_api': 'metadata_collection_show',
    })

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
    context.update({
        'invoked_api': 'metadata_collection_list',
    })

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

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_show', context, data_dict)

    context['package'] = metadata_record
    metadata_record_dict = model_dictize.metadata_record_dictize(metadata_record, context)

    result_dict, errors = tk.navl_validate(metadata_record_dict, schema.metadata_record_show_schema(), context)
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
def metadata_record_validation_model_list(context, data_dict):
    """
    Return a list of metadata models to be used for validating a metadata record.

    This comprises the following:
    1. The default model defined for the record's metadata schema.
    2. A model for that schema (optionally) defined for the owner organization.
    3. Any models (optionally) defined for that schema for infrastructures linked to the record.

    :param id: the id or name of the metadata record
    :type id: string
    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of names (dictionaries if all_fields) of metadata models
    """
    log.debug("Retrieving metadata models for metadata record validation: %r", data_dict)

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

    tk.check_access('metadata_record_validation_model_list', context, data_dict)

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
    metadata_schema_id = session.query(model.PackageExtra.value) \
        .filter_by(package_id=metadata_record_id, key='metadata_schema_id').scalar()

    MetadataModel = ckanext_model.MetadataModel
    metadata_model_names = session.query(MetadataModel.name) \
        .filter_by(metadata_schema_id=metadata_schema_id, state='active') \
        .filter(or_(MetadataModel.organization_id == organization_id, MetadataModel.organization_id == None)) \
        .filter(or_(MetadataModel.infrastructure_id == infra_id for infra_id in infrastructure_ids)) \
        .all()

    result = []
    all_fields = asbool(data_dict.get('all_fields'))
    for (metadata_model_name,) in metadata_model_names:
        if all_fields:
            result += [tk.get_action('metadata_model_show')(context, {'id': metadata_model_name})]
        else:
            result += [metadata_model_name]

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
    Check the validity of a metadata dictionary against a metadata model.

    :param metadata_json: JSON dictionary of metadata record content
    :type metadata_json: string
    :param model_json: JSON dictionary defining a metadata model
    :type model_json: string

    :rtype: dictionary of metadata errors; empty dict implies that the metadata is 100% valid
        against the given model
    """
    log.debug("Checking metadata validity")
    tk.check_access('metadata_validity_check', context, data_dict)

    session = context['session']
    data, errors = tk.navl_validate(data_dict, schema.metadata_validity_check_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_json = json.loads(data['metadata_json'])
    model_json = json.loads(data['model_json'])

    metadata_errors = {}
    validator = jsonschema_validation.create_validator(model_json)
    for metadata_error in validator.iter_errors(metadata_json):
        metadata_errors[tuple(metadata_error.path)] = metadata_error.message

    return metadata_errors


@tk.side_effect_free
def metadata_workflow_rule_evaluate(context, data_dict):
    """
    Evaluate whether a metadata dictionary passes a workflow rule.

    :param metadata_json: JSON dictionary of metadata record content
    :type metadata_json: string
    :param evaluator_url: URI of the metric evaluation service
    :type evaluator_url: string
    :param rule_json: JSON dictionary defining a workflow rule
    :type rule_json: string

    :rtype: boolean (pass/fail)
    """
    log.debug("Evaluating metadata against workflow rule", data_dict)
    tk.check_access('metadata_workflow_rule_evaluate', context, data_dict)

    model = context['model']
    session = context['session']

    metadata_json, evaluator_url, rule_json = tk.get_or_bust(
        data_dict, ['metadata_json', 'evaluator_url', 'rule_json'])

    raise NotImplementedError


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
def workflow_state_show(context, data_dict):
    """
    Return a workflow state definition.

    :param id: the id or name of the workflow state
    :type id: string

    :rtype: dictionary
    """
    log.debug("Retrieving workflow state: %r", data_dict)

    workflow_state_id = tk.get_or_bust(data_dict, 'id')
    workflow_state = ckanext_model.WorkflowState.get(workflow_state_id)
    if workflow_state is not None:
        workflow_state_id = workflow_state.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('workflow_state_show', context, data_dict)

    context['workflow_state'] = workflow_state
    workflow_state_dict = model_dictize.workflow_state_dictize(workflow_state, context)

    result_dict, errors = tk.navl_validate(workflow_state_dict, schema.workflow_state_show_schema(), context)
    return result_dict


@tk.side_effect_free
def workflow_state_list(context, data_dict):
    """
    Return a list of names of the site's workflow states.

    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean

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
def workflow_state_rule_list(context, data_dict):
    """
    Return a list of rules for a workflow state.

    :param id: the id or name of the workflow state
    :type id: string

    :rtype: list of dictionaries combining rule and metric information {
            rule_id
            metric_name
            metric_title
            metric_description
            evaluator_url
            rule_json
        }
    """
    log.debug("Retrieving list of rules for workflow state: %r", data_dict)

    session = context['session']
    workflow_state = context.get('workflow_state')
    if workflow_state:
        workflow_state_id = workflow_state.id
    else:
        workflow_state_id = tk.get_or_bust(data_dict, 'id')
        workflow_state = ckanext_model.WorkflowState.get(workflow_state_id)
        if workflow_state is not None:
            workflow_state_id = workflow_state.id
        else:
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('workflow_state_rule_list', context, data_dict)

    rules = session.query(ckanext_model.WorkflowRule) \
        .join(ckanext_model.WorkflowMetric) \
        .filter(ckanext_model.WorkflowRule.workflow_state_id == workflow_state_id) \
        .all()

    return [{
        'rule_id': rule.id,
        'metric_name': rule.name,
        'metric_title': rule.title,
        'metric_description': rule.description,
        'evaluator_url': rule.evaluator_url,
        'rule_json': rule.rule_json,
    } for rule in rules]


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
def workflow_metric_show(context, data_dict):
    """
    Return a workflow metric definition.

    :param id: the id or name of the workflow metric
    :type id: string

    :rtype: dictionary
    """
    log.debug("Retrieving workflow metric: %r", data_dict)

    workflow_metric_id = tk.get_or_bust(data_dict, 'id')
    workflow_metric = ckanext_model.WorkflowMetric.get(workflow_metric_id)
    if workflow_metric is not None:
        workflow_metric_id = workflow_metric.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Metric')))

    tk.check_access('workflow_metric_show', context, data_dict)

    context['workflow_metric'] = workflow_metric
    workflow_metric_dict = model_dictize.workflow_metric_dictize(workflow_metric, context)

    result_dict, errors = tk.navl_validate(workflow_metric_dict, schema.workflow_metric_show_schema(), context)
    return result_dict


@tk.side_effect_free
def workflow_metric_list(context, data_dict):
    """
    Return a list of names of the site's workflow metrics.

    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving workflow metric list: %r", data_dict)
    tk.check_access('workflow_metric_list', context, data_dict)

    session = context['session']
    all_fields = asbool(data_dict.get('all_fields'))

    workflow_metrics = session.query(ckanext_model.WorkflowMetric.id, ckanext_model.WorkflowMetric.name) \
        .filter_by(state='active') \
        .all()
    result = []
    for (id_, name) in workflow_metrics:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('workflow_metric_show')(context, data_dict)]
        else:
            result += [name]

    return result


@tk.side_effect_free
def workflow_rule_show(context, data_dict):
    """
    Return a workflow rule definition.

    :param id: the id of the workflow rule
    :type id: string

    :rtype: dictionary
    """
    log.debug("Retrieving workflow rule: %r", data_dict)

    workflow_rule_id = tk.get_or_bust(data_dict, 'id')
    workflow_rule = ckanext_model.WorkflowRule.get(workflow_rule_id)
    if workflow_rule is not None:
        workflow_rule_id = workflow_rule.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Rule')))

    tk.check_access('workflow_rule_show', context, data_dict)

    context['workflow_rule'] = workflow_rule
    workflow_rule_dict = model_dictize.workflow_rule_dictize(workflow_rule, context)

    result_dict, errors = tk.navl_validate(workflow_rule_dict, schema.workflow_rule_show_schema(), context)
    return result_dict


@tk.side_effect_free
def workflow_rule_list(context, data_dict):
    """
    Return a list of ids of the site's workflow rules.

    :param all_fields: return dictionaries instead of just ids (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings
    """
    log.debug("Retrieving workflow rule list: %r", data_dict)
    tk.check_access('workflow_rule_list', context, data_dict)

    session = context['session']
    all_fields = asbool(data_dict.get('all_fields'))

    workflow_rules = session.query(ckanext_model.WorkflowRule.id) \
        .filter_by(state='active') \
        .all()
    result = []
    for (id_,) in workflow_rules:
        if all_fields:
            data_dict['id'] = id_
            result += [tk.get_action('workflow_rule_show')(context, data_dict)]
        else:
            result += [id_]

    return result
