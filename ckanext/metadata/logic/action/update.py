# encoding: utf-8

import logging
import json

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.logic import schema
from ckanext.metadata.lib.dictization import model_save
import ckanext.metadata.model as ckanext_model
from ckanext.metadata import MetadataValidationState, METADATA_VALIDATION_ACTIVITY_TYPE, METADATA_WORKFLOW_ACTIVITY_TYPE
from ckanext.metadata.lib.dictization import model_dictize

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

    :param id: the id or name of the metadata schema to update
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

    data_dict['id'] = obj.id
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

    Changes to the model_json will cause dependent metadata records to be invalidated.
    If any of metadata_schema_id, organization_id or infrastructure_id change, then
    ex-dependent and newly-dependent metadata records will also be invalidated.

    It is recommended to call
    :py:func:`ckan.logic.action.get.metadata_model_show`, make the desired changes to
    the result, and then call ``metadata_model_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.metadata_model_create`.

    :param id: the id or name of the metadata model to update
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

    id_ = obj.id
    old_dict = model_dictize.metadata_model_dictize(obj, context)
    old_model_json = old_dict['model_json']
    if old_model_json:
        old_model_json = json.loads(old_model_json)
    old_dependent_record_list = tk.get_action('metadata_model_dependent_record_list')(context, {'id': id_})

    data_dict['id'] = id_
    context['metadata_model'] = obj
    context['allow_partial_update'] = True

    data, errors = tk.navl_validate(data_dict, schema.metadata_model_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_model = model_save.metadata_model_dict_save(data, context)
    new_dict = model_dictize.metadata_model_dictize(metadata_model, context)
    new_model_json = new_dict['model_json']
    if new_model_json:
        new_model_json = json.loads(new_model_json)
    new_dependent_record_list = tk.get_action('metadata_model_dependent_record_list')(context, {'id': id_})

    if old_model_json != new_model_json:
        affected_record_ids = set(old_dependent_record_list) | set(new_dependent_record_list)
    else:
        affected_record_ids = set(old_dependent_record_list) ^ set(new_dependent_record_list)

    invalidate_context = context
    invalidate_context['defer_commit'] = True
    for metadata_record_id in affected_record_ids:
        tk.get_action('metadata_record_invalidate')(invalidate_context, {'id': metadata_record_id})

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

    data_dict['id'] = obj.id
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

    data_dict['id'] = obj.id
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

    :param id: the id or name of the metadata record to update
    :type id: string
    :param name: the name of the metadata record (optional)
    :type name: string

    :returns: the updated metadata record (unless 'return_id_only' is set to True
              in the context, in which case just the record id will be returned)
    :rtype: dictionary
    """

    def get_extra(dict_, key):
        return next((x['value'] for x in dict_['extras'] if x['key'] == key), None)
    
    log.info("Updating metadata record: %r", data_dict)

    model = context['model']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Package.get(id_)
    if obj is None or obj.type != 'metadata_record':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_update', context, data_dict)

    id_ = obj.id
    context['metadata_record'] = obj
    old_dict = model_dictize.metadata_record_dictize(obj, context)
    old_metadata_json = get_extra(old_dict, 'metadata_json')
    if old_metadata_json:
        old_metadata_json = json.loads(old_metadata_json)
    old_validation_models = set(tk.get_action('metadata_record_validation_model_list')(context, {'id': id_}))

    data_dict['id'] = id_
    data_dict['type'] = 'metadata_record'
    data_dict['validation_state'] = get_extra(old_dict, 'validation_state')
    data_dict['workflow_state_id'] = get_extra(old_dict, 'workflow_state_id')

    context['schema'] = schema.metadata_record_update_schema()
    context['invoked_api'] = 'metadata_record_update'
    context['defer_commit'] = True
    context['return_id_only'] = True
    context['allow_partial_update'] = True

    tk.get_action('package_update')(context, data_dict)
    model_save.metadata_record_infrastructure_list_save(data_dict.get('infrastructures'), context)

    # ensure new validation model list sees infrastructure list changes
    session.flush()

    new_dict = model_dictize.metadata_record_dictize(obj, context)
    new_metadata_json = get_extra(new_dict, 'metadata_json')
    if new_metadata_json:
        new_metadata_json = json.loads(new_metadata_json)
    new_validation_models = set(tk.get_action('metadata_record_validation_model_list')(context, {'id': id_}))

    # if either the metadata record content or the set of validation models for the record has changed,
    # then the record must be invalidated
    if old_metadata_json != new_metadata_json or old_validation_models != new_validation_models:
        new_dict['validation_state'] = obj.extras['validation_state'] = MetadataValidationState.NOT_VALIDATED

    if not defer_commit:
        model.repo.commit()

    output = id_ if return_id_only \
        else tk.get_action('metadata_record_show')(context, {'id': id_})
    return output


def metadata_record_invalidate(context, data_dict):
    """
    Mark a metadata record as not validated.

    You must be authorized to invalidate the metadata record.

    :param id: the id or name of the metadata record to invalidate
    :type id: string
    """
    log.info("Invalidating metadata record: %r", data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Package.get(id_)
    if obj is None or obj.type != 'metadata_record':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_invalidate', context, data_dict)

    obj.extras['validation_state'] = MetadataValidationState.NOT_VALIDATED

    if not defer_commit:
        model.repo.commit()


def metadata_record_validate(context, data_dict):
    """
    Validate a metadata record (if not already validated), and log the result to
    the metadata record's activity stream.

    You must be authorized to validate the metadata record.

    :param id: the id or name of the metadata record to validate
    :type id: string

    :rtype: validation activity dictionary
    """
    log.info("Validating metadata record: %r", data_dict)

    model = context['model']
    session = context['session']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is None or metadata_record.type != 'metadata_record':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_validate', context, data_dict)

    metadata_record_id = metadata_record.id
    context['metadata_record'] = metadata_record

    # already validated -> return the last validation result
    if metadata_record.extras['validation_state'] != MetadataValidationState.NOT_VALIDATED:
        return tk.get_action('metadata_record_validation_activity_show')(context, {'id': metadata_record_id})

    validation_models = tk.get_action('metadata_record_validation_model_list')\
        (context, {'id': metadata_record_id, 'all_fields': True})
    if not validation_models:
        raise tk.ObjectNotFound(_('Could not find any metadata models for validating this metadata record'))

    # log validation results using CKAN's activity stream model; CKAN doesn't provide a way
    # to hook into activity detail creation, so we work directly with the model objects here
    activity = model.Activity(
        user_id=model.User.by_name(user.decode('utf8')).id,
        object_id=metadata_record_id,
        revision_id=metadata_record.revision_id,
        activity_type=METADATA_VALIDATION_ACTIVITY_TYPE
    )

    # delegate the actual validation work to the pluggable action metadata_validity_check
    activity_details = []
    partial_states = set()
    for metadata_model in validation_models:
        validation_result = tk.get_action('metadata_validity_check')(context, {
            'metadata_json': metadata_record['metadata_json'],
            'model_json': metadata_model['model_json'],
        })
        partial_state = validation_result['status']
        partial_states |= {partial_state}
        activity_detail = model.ActivityDetail(
            activity_id=activity.id,
            object_id=metadata_model['id'],
            object_type=ckanext_model.MetadataModel,
            activity_type=partial_state,
            data=validation_result['errors']
        )
        activity_details += [activity_detail]

    # the resultant validation state of the metadata record is the 'worst' of the results from all the models
    metadata_record.extras['validation_state'] = MetadataValidationState.net_state(partial_states)

    session.add(activity)
    for activity_detail in activity_details:
        session.add(activity_detail)

    if not defer_commit:
        model.repo.commit()

    return tk.get_action('metadata_record_validation_activity_show')(context, {'id': metadata_record_id})


def metadata_record_validation_state_override(context, data_dict):
    """
    Override a metadata record's validation state.

    You must be authorized to override the metadata record's validation state.
    This should normally only be allowed for sysadmins.

    :param id: the id or name of the metadata record to update
    :type id: string
    :param validation_state: a permitted value as per MetadataValidationState
    :type validation_state: string
    """
    log.info("Overriding validation state of metadata record: %r", data_dict)

    model = context['model']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Package.get(id_)
    if obj is None or obj.type != 'metadata_record':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_validation_state_override', context, data_dict)

    validation_state = tk.get_or_bust(data_dict, 'validation_state')
    if validation_state not in MetadataValidationState.all:
        raise tk.ValidationError(_('Invalid validation state'))

    obj.extras['validation_state'] = validation_state

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Override validation state of metadata record %s') % obj.id

    if not defer_commit:
        model.repo.commit()


def metadata_record_workflow_state_override(context, data_dict):
    """
    Override a metadata record's workflow state, bypassing workflow rule evaluation.

    You must be authorized to override the metadata record's workflow state.
    This should normally only be allowed for sysadmins.

    :param id: the id or name of the metadata record to update
    :type id: string
    :param workflow_state_id: the id or name of the workflow state to assign to the record
    :type workflow_state_id: string
    """
    log.info("Overriding workflow state of metadata record: %r", data_dict)

    model = context['model']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id, workflow_state_id = tk.get_or_bust(data_dict, ['id', 'workflow_state_id'])

    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is None or metadata_record.type != 'metadata_record':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    workflow_state = ckanext_model.WorkflowState.get(workflow_state_id)
    if workflow_state is None or workflow_state.state != 'active':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('metadata_record_workflow_state_override', context, data_dict)

    metadata_record.extras['workflow_state_id'] = workflow_state.id

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Override workflow state of metadata record %s') % metadata_record.id

    if not defer_commit:
        model.repo.commit()


def workflow_state_update(context, data_dict):
    """
    Update a workflow state.

    You must be authorized to edit the workflow state.

    It is recommended to call
    :py:func:`ckan.logic.action.get.workflow_state_show`, make the desired changes to
    the result, and then call ``workflow_state_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.workflow_state_create`.

    :param id: the id or name of the workflow state to update
    :type id: string

    :returns: the updated workflow state (unless 'return_id_only' is set to True
              in the context, in which case just the workflow state id will be returned)
    :rtype: dictionary
    """
    log.info("Updating workflow state: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.WorkflowState.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('workflow_state_update', context, data_dict)

    data_dict['id'] = obj.id
    context['workflow_state'] = obj
    context['allow_partial_update'] = True

    data, errors = tk.navl_validate(data_dict, schema.workflow_state_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_state = model_save.workflow_state_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update workflow state %s') % workflow_state.id

    if not defer_commit:
        model.repo.commit()

    output = workflow_state.id if return_id_only \
        else tk.get_action('workflow_state_show')(context, {'id': workflow_state.id})
    return output


def workflow_transition_update(context, data_dict):
    """
    Update a workflow transition.

    Note: this action will always fail; workflow_transition is an association table which
    does not define any properties of its own; to "update" a transition, delete it and
    create a new one.
    """
    raise tk.ValidationError("A workflow transition cannot be updated. Delete it and create a new one instead.")


def workflow_metric_update(context, data_dict):
    """
    Update a workflow metric.

    You must be authorized to edit the workflow metric.

    It is recommended to call
    :py:func:`ckan.logic.action.get.workflow_metric_show`, make the desired changes to
    the result, and then call ``workflow_metric_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.workflow_metric_create`.

    :param id: the id or name of the workflow metric to update
    :type id: string

    :returns: the updated workflow metric (unless 'return_id_only' is set to True
              in the context, in which case just the workflow metric id will be returned)
    :rtype: dictionary
    """
    log.info("Updating workflow metric: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.WorkflowMetric.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Metric')))

    tk.check_access('workflow_metric_update', context, data_dict)

    data_dict['id'] = obj.id
    context['workflow_metric'] = obj
    context['allow_partial_update'] = True

    data, errors = tk.navl_validate(data_dict, schema.workflow_metric_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_metric = model_save.workflow_metric_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update workflow metric %s') % workflow_metric.id

    if not defer_commit:
        model.repo.commit()

    output = workflow_metric.id if return_id_only \
        else tk.get_action('workflow_metric_show')(context, {'id': workflow_metric.id})
    return output


def workflow_rule_update(context, data_dict):
    """
    Update a workflow rule. Only the JSON rule definition can be modified.

    You must be authorized to edit the workflow rule.

    :param id: the id or name of the workflow rule to update
    :type id: string
    :param rule_json: JSON object defining acceptable return value/range from metric
        evaluation to pass this rule
    :type rule_json: string

    :returns: the updated workflow rule (unless 'return_id_only' is set to True
              in the context, in which case just the workflow rule id will be returned)
    :rtype: dictionary
    """
    log.info("Updating workflow rule: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.WorkflowRule.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Rule')))

    tk.check_access('workflow_rule_update', context, data_dict)

    data_dict['id'] = obj.id
    context['workflow_rule'] = obj
    context['allow_partial_update'] = True

    data, errors = tk.navl_validate(data_dict, schema.workflow_rule_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_rule = model_save.workflow_rule_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update workflow rule %s') % workflow_rule.id

    if not defer_commit:
        model.repo.commit()

    output = workflow_rule.id if return_id_only \
        else tk.get_action('workflow_rule_show')(context, {'id': workflow_rule.id})
    return output


def metadata_record_workflow_state_transition(context, data_dict):
    """
    Transition a metadata record to a different workflow state, and log the result
    to the metadata record's activity stream.

    You must be authorized to change the metadata record's workflow state.

    :param id: the id or name of the metadata record to transition
    :type id: string
    :param workflow_state_id: the id or name of the target workflow state
    :type workflow_state_id: string

    :rtype: workflow activity dictionary

    TODO: we must log complete details of the transition, metrics and rules involved
    because later on these might be changed and it won't otherwise be clear how a record
    got into the state it's in... alternative would be to revert all records in a particular
    state if the rules for that state change, but this might cause even more problems...
    """
    log.info("Transitioning workflow state of metadata record: %r", data_dict)

    model = context['model']
    session = context['session']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id, target_workflow_state_id = tk.get_or_bust(data_dict, ['id', 'workflow_state_id'])

    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is None or metadata_record.type != 'metadata_record':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    target_workflow_state = ckanext_model.WorkflowState.get(target_workflow_state_id)
    if target_workflow_state is None or target_workflow_state.state != 'active':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('metadata_record_workflow_state_transition', context, data_dict)

    metadata_record_id = metadata_record.id
    target_workflow_state_id = target_workflow_state.id
    context['metadata_record'] = metadata_record
    context['workflow_state'] = target_workflow_state

    current_workflow_state_id = session.query(model.PackageExtra.value) \
        .filter_by(package_id=metadata_record_id, key='workflow_state_id').scalar()

    if current_workflow_state_id == target_workflow_state_id:
        return None

    workflow_transition = ckanext_model.WorkflowTransition.lookup(current_workflow_state_id, target_workflow_state_id)
    if not workflow_transition or workflow_transition.state != 'active':
        raise tk.ValidationError(_("Invalid workflow state transition"))

    workflow_rules = tk.get_action('workflow_state_rule_list')(context, {'id': target_workflow_state_id})

    # log results of rule evaluation using CKAN's activity stream model; CKAN doesn't provide a way
    # to hook into activity detail creation, so we work directly with the model objects here
    activity = model.Activity(
        user_id=model.User.by_name(user.decode('utf8')).id,
        object_id=metadata_record_id,
        revision_id=metadata_record.revision_id,
        activity_type=METADATA_WORKFLOW_ACTIVITY_TYPE,
        data={'workflow_transition_id': workflow_transition.id}
    )

    # delegate the actual evaluation work to the pluggable action metadata_workflow_rule_evaluate
    activity_details = []
    success = True  # if there are no rules associated with a state, the transition is allowed
    for workflow_rule in workflow_rules:
        rule_success = tk.get_action('metadata_workflow_rule_evaluate')(context, {
            'metadata_json': metadata_record.extras['metadata_json'],
            'evaluator_url': workflow_rule['evaluator_url'],
            'rule_json': workflow_rule['rule_json'],
        })
        success = success and rule_success
        activity_detail = model.ActivityDetail(
            activity_id=activity.id,
            object_id=workflow_rule['rule_id'],
            object_type=ckanext_model.WorkflowRule,
            activity_type='pass' if rule_success else 'fail',
        )
        activity_details += [activity_detail]

    if success:
        metadata_record.extras['workflow_state_id'] = target_workflow_state_id

    session.add(activity)
    for activity_detail in activity_details:
        session.add(activity_detail)

    if not defer_commit:
        model.repo.commit()

    return tk.get_action('metadata_record_workflow_activity_show')(context, {'id': metadata_record_id})
