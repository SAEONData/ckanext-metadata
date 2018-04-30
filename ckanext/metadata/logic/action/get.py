# encoding: utf-8

import logging
from paste.deploy.converters import asbool
from sqlalchemy import or_

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.logic import schema
from ckanext.metadata.lib.dictization import model_dictize
import ckanext.metadata.model as ckanext_model
from ckanext.metadata import METADATA_VALIDATION_ACTIVITY_TYPE, METADATA_WORKFLOW_ACTIVITY_TYPE

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
    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.MetadataModel.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Model')))

    tk.check_access('metadata_model_dependent_record_list', context, data_dict)

    q = session.query(model.Package.id) \
        .join(model.PackageExtra) \
        .filter(model.Package.state == 'active') \
        .filter(model.PackageExtra.key == 'metadata_schema_id') \
        .filter(model.PackageExtra.value == obj.metadata_schema_id)

    if obj.organization_id:
        q = q.filter(model.Package.owner_org == obj.organization_id)

    if obj.infrastructure_id:
        q = q.join(model.Member, model.Member.table_id == model.Package.id) \
            .filter(model.Member.table_name == 'package') \
            .filter(model.Member.state == 'active') \
            .join(model.Group, model.Group.id == model.Member.group_id) \
            .filter(model.Group.type == 'infrastructure') \
            .filter(model.Group.state == 'active') \
            .filter(model.Group.id == obj.infrastructure_id)

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
    :param all_fields: return dictionaries instead of just names (optional, default: ``False``)
    :type all_fields: boolean


    :rtype: list of names (dictionaries if all_fields) of metadata models
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
        .filter_by(object_id=id_, activity_type=METADATA_VALIDATION_ACTIVITY_TYPE) \
        .order_by(model.Activity.timestamp.desc()) \
        .first()
    if not activity:
        return None

    return model_dictize.metadata_record_activity_dictize(activity, context)


@tk.side_effect_free
def metadata_validity_check(context, data_dict):
    """
    Check the validity of a metadata dictionary against a metadata model.

    :param content_json: JSON dictionary of metadata record content
    :type content_json: string
    :param model_json: JSON dictionary defining a metadata model
    :type model_json: string

    :rtype: dictionary {
            'status': MetadataValidationState
            'errors': dictionary
        }
    """
    log.debug("Checking metadata validity")
    tk.check_access('metadata_validity_check', context, data_dict)

    model = context['model']
    session = context['session']

    content_json, model_json = tk.get_or_bust(data_dict, ['content_json', 'model_json'])

    raise NotImplementedError


@tk.side_effect_free
def metadata_workflow_rule_evaluate(context, data_dict):
    """
    Evaluate whether a metadata dictionary passes a workflow rule.

    :param content_json: JSON dictionary of metadata record content
    :type content_json: string
    :param evaluator_uri: URI of the metric evaluation service
    :type evaluator_uri: string
    :param min_value: minimum accepted return value from the evaluator
    :type min_value: integer
    :param max_value: maximum accepted return value from the evaluator
    :type max_value: integer

    :rtype: boolean (pass/fail)
    """
    log.debug("Evaluating metadata against workflow rule", data_dict)
    tk.check_access('metadata_workflow_rule_evaluate', context, data_dict)

    model = context['model']
    session = context['session']

    content_json, evaluator_uri, min_value, max_value = tk.get_or_bust(
        data_dict, ['content_json', 'evaluator_uri', 'min_value', 'max_value'])

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
    obj = context.get('metadata_record')
    if not obj:
        id_ = tk.get_or_bust(data_dict, 'id')
        obj = model.Package.get(id_)
        if obj is None or obj.type != 'metadata_record':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_workflow_activity_show', context, data_dict)

    id_ = obj.id
    activity = session.query(model.Activity) \
        .filter_by(object_id=id_, activity_type=METADATA_WORKFLOW_ACTIVITY_TYPE) \
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

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.WorkflowState.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('workflow_state_show', context, data_dict)

    context['workflow_state'] = obj
    workflow_state_dict = model_dictize.workflow_state_dictize(obj, context)

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
            evaluator_uri
            min_value
            max_value
        }
    """
    log.debug("Retrieving list of rules for workflow state: %r", data_dict)

    session = context['session']
    obj = context.get('workflow_state')
    if not obj:
        id_ = tk.get_or_bust(data_dict, 'id')
        obj = ckanext_model.WorkflowState.get(id_)
        if obj is None:
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('workflow_state_rule_list', context, data_dict)

    context['workflow_state'] = obj
    id_ = obj.id

    rules = session.query(ckanext_model.WorkflowRule) \
        .join(ckanext_model.WorkflowMetric) \
        .filter(ckanext_model.WorkflowRule.workflow_state_id == id_) \
        .all()

    return [{
        'rule_id': rule.id,
        'metric_name': rule.name,
        'metric_title': rule.title,
        'metric_description': rule.description,
        'evaluator_uri': rule.evaluator_uri,
        'min_value': rule.min_value,
        'max_value': rule.max_value,
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

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.WorkflowTransition.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Transition')))

    tk.check_access('workflow_transition_show', context, data_dict)

    context['workflow_transition'] = obj
    workflow_transition_dict = model_dictize.workflow_transition_dictize(obj, context)

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

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.WorkflowMetric.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Metric')))

    tk.check_access('workflow_metric_show', context, data_dict)

    context['workflow_metric'] = obj
    workflow_metric_dict = model_dictize.workflow_metric_dictize(obj, context)

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
