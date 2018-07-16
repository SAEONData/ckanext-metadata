# encoding: utf-8

import logging
import json
from paste.deploy.converters import asbool

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.logic import schema, METADATA_VALIDATION_ACTIVITY_TYPE, METADATA_WORKFLOW_ACTIVITY_TYPE
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

    metadata_schema_id = tk.get_or_bust(data_dict, 'id')
    metadata_schema = ckanext_model.MetadataSchema.get(metadata_schema_id)
    if metadata_schema is not None:
        metadata_schema_id = metadata_schema.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Schema')))

    tk.check_access('metadata_schema_update', context, data_dict)

    data_dict.update({
        'id': metadata_schema_id,
    })
    context.update({
        'metadata_schema': metadata_schema,
        'allow_partial_update': True,
    })

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
        rev.message = _(u'REST API: Update metadata schema %s') % metadata_schema_id

    if not defer_commit:
        model.repo.commit()

    output = metadata_schema_id if return_id_only \
        else tk.get_action('metadata_schema_show')(context, {'id': metadata_schema_id})
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

    metadata_model_id = tk.get_or_bust(data_dict, 'id')
    metadata_model = ckanext_model.MetadataModel.get(metadata_model_id)
    if metadata_model is not None:
        metadata_model_id = metadata_model.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Model')))

    tk.check_access('metadata_model_update', context, data_dict)

    old_model_json = metadata_model.model_json
    if old_model_json:
        old_model_json = json.loads(old_model_json)
    old_dependent_record_list = tk.get_action('metadata_model_dependent_record_list')(context, {'id': metadata_model_id})

    data_dict.update({
        'id': metadata_model_id,
    })
    context.update({
        'metadata_model': metadata_model,
        'allow_partial_update': True,
    })

    data, errors = tk.navl_validate(data_dict, schema.metadata_model_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_model = model_save.metadata_model_dict_save(data, context)
    new_model_json = metadata_model.model_json
    if new_model_json:
        new_model_json = json.loads(new_model_json)
    new_dependent_record_list = tk.get_action('metadata_model_dependent_record_list')(context, {'id': metadata_model_id})

    if old_model_json != new_model_json:
        affected_record_ids = set(old_dependent_record_list) | set(new_dependent_record_list)
    else:
        affected_record_ids = set(old_dependent_record_list) ^ set(new_dependent_record_list)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update metadata model %s') % metadata_model_id

    invalidate_context = context.copy()
    invalidate_context.update({
        'defer_commit': True,
        'trigger_action': 'metadata_model_update',
        'trigger_object_id': metadata_model_id,
        'trigger_revision_id': rev.id,
    })
    for metadata_record_id in affected_record_ids:
        tk.get_action('metadata_record_invalidate')(invalidate_context, {'id': metadata_record_id})

    if not defer_commit:
        model.repo.commit()

    output = metadata_model_id if return_id_only \
        else tk.get_action('metadata_model_show')(context, {'id': metadata_model_id})
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

    infrastructure_id = tk.get_or_bust(data_dict, 'id')
    infrastructure = model.Group.get(infrastructure_id)
    if infrastructure is not None and infrastructure.type == 'infrastructure':
        infrastructure_id = infrastructure.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Infrastructure')))

    tk.check_access('infrastructure_update', context, data_dict)

    data_dict.update({
        'id': infrastructure_id,
        'type': 'infrastructure',
        'is_organization': False,
    })
    context.update({
        'schema': schema.infrastructure_update_schema(),
        'invoked_api': 'infrastructure_update',
        'defer_commit': True,
        'allow_partial_update': True,
    })

    infrastructure_dict = tk.get_action('group_update')(context, data_dict)

    if not defer_commit:
        model.repo.commit()

    output = infrastructure_id if return_id_only \
        else tk.get_action('infrastructure_show')(context, {'id': infrastructure_id})
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

    metadata_collection_id = tk.get_or_bust(data_dict, 'id')
    metadata_collection = model.Group.get(metadata_collection_id)
    if metadata_collection is not None and metadata_collection.type == 'metadata_collection':
        metadata_collection_id = metadata_collection.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))

    tk.check_access('metadata_collection_update', context, data_dict)

    data_dict.update({
        'id': metadata_collection_id,
        'type': 'metadata_collection',
        'is_organization': False,
    })
    context.update({
        'schema': schema.metadata_collection_update_schema(),
        'invoked_api': 'metadata_collection_update',
        'defer_commit': True,
        'allow_partial_update': True,
    })

    metadata_collection_dict = tk.get_action('group_update')(context, data_dict)

    if not defer_commit:
        model.repo.commit()

    output = metadata_collection_id if return_id_only \
        else tk.get_action('metadata_collection_show')(context, {'id': metadata_collection_id})
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
    log.info("Updating metadata record: %r", data_dict)

    model = context['model']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_update', context, data_dict)

    context['metadata_record'] = metadata_record

    # if it's a validated record, get some current state info for checking whether we need to invalidate it
    if asbool(metadata_record.extras['validated']):
        old_metadata_json = metadata_record.extras['metadata_json']
        if old_metadata_json:
            old_metadata_json = json.loads(old_metadata_json)
        old_validation_models = set(tk.get_action('metadata_record_validation_model_list')(context, {'id': metadata_record_id}))

    data_dict.update({
        'id': metadata_record_id,
        'type': 'metadata_record',
        'validated': asbool(metadata_record.extras['validated']),
        'errors': metadata_record.extras['errors'],
        'workflow_state_id': metadata_record.extras['workflow_state_id'],
    })
    context.update({
        'schema': schema.metadata_record_update_schema(),
        'invoked_api': 'metadata_record_update',
        'defer_commit': True,
        'return_id_only': True,
        'allow_partial_update': True,
    })

    tk.get_action('package_update')(context, data_dict)
    model_save.metadata_record_infrastructure_list_save(data_dict.get('infrastructures'), context)

    # check if we need to invalidate the record
    if asbool(metadata_record.extras['validated']):
        # ensure new validation model list sees infrastructure list changes
        session.flush()

        new_metadata_json = metadata_record.extras['metadata_json']
        if new_metadata_json:
            new_metadata_json = json.loads(new_metadata_json)
        new_validation_models = set(tk.get_action('metadata_record_validation_model_list')(context, {'id': metadata_record_id}))

        # if either the metadata record content or the set of validation models for the record has changed,
        # then the record must be invalidated
        if old_metadata_json != new_metadata_json or old_validation_models != new_validation_models:
            invalidate_context = context.copy()
            invalidate_context.update({
                'defer_commit': True,
                'trigger_action': 'metadata_record_update',
                'trigger_object_id': metadata_record_id,
                'trigger_revision_id': model.Package.get(metadata_record_id).revision_id,
            })
            tk.get_action('metadata_record_invalidate')(invalidate_context, {'id': metadata_record_id})

    if not defer_commit:
        model.repo.commit()

    output = metadata_record_id if return_id_only \
        else tk.get_action('metadata_record_show')(context, {'id': metadata_record_id})
    return output


def metadata_record_invalidate(context, data_dict):
    """
    Mark a metadata record as not validated, and log the change to
    the metadata record's activity stream.

    You must be authorized to invalidate the metadata record.

    Note: this function is typically called from within another action function
    whose effect triggers invalidation of the given metadata record. In such a
    case, the calling function should pass the following items in the context:
    'trigger_action': the calling function name, e.g. 'metadata_model_update'
    'trigger_object_id': the id of the object (e.g. a MetadataModel) being modified
    'trigger_revision_id': the id of the revision for this modification

    :param id: the id or name of the metadata record to invalidate
    :type id: string
    """
    log.info("Invalidating metadata record: %r", data_dict)

    model = context['model']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_invalidate', context, data_dict)

    # already not validated
    if not asbool(metadata_record.extras['validated']):
        return

    metadata_record.extras['validated'] = False
    metadata_record.extras['errors'] = '{}'

    trigger_action = context.get('trigger_action')
    trigger_object_id = context.get('trigger_object_id')
    trigger_revision_id = context.get('trigger_revision_id')

    activity_context = context.copy()
    activity_context.update({
        'defer_commit': True,
        'schema': {
            'user_id': [unicode, tk.get_validator('convert_user_name_or_id_to_id')],
            'object_id': [],
            'revision_id': [],
            'activity_type': [],
            'data': [],
        },
    })
    activity_dict = {
        'user_id': user,
        'object_id': metadata_record_id,
        'activity_type': METADATA_VALIDATION_ACTIVITY_TYPE,
        'data': {
            'action': 'metadata_record_invalidate',
            'trigger_action': trigger_action,
            'trigger_object_id': trigger_object_id,
            'trigger_revision_id': trigger_revision_id,
        }
    }
    tk.get_action('activity_create')(activity_context, activity_dict)

    if not defer_commit:
        model.repo.commit()


def metadata_record_validate(context, data_dict):
    """
    Validate a metadata record (if not already validated), and log the result to
    the metadata record's activity stream.

    You must be authorized to validate the metadata record.

    :param id: the id or name of the metadata record to validate
    :type id: string
    """
    log.info("Validating metadata record: %r", data_dict)

    model = context['model']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_validate', context, data_dict)

    context['metadata_record'] = metadata_record

    # already validated
    if asbool(metadata_record.extras['validated']):
        return

    validation_models = tk.get_action('metadata_record_validation_model_list')\
        (context, {'id': metadata_record_id, 'all_fields': True})
    if not validation_models:
        raise tk.ObjectNotFound(_('Could not find any metadata models for validating this metadata record'))

    # delegate the actual validation work to the pluggable action metadata_validity_check
    validation_results = []
    accumulated_errors = {}
    for metadata_model in validation_models:
        validation_errors = tk.get_action('metadata_validity_check')(context, {
            'metadata_json': metadata_record.extras['metadata_json'],
            'model_json': json.dumps(metadata_model['model_json']),
        })
        validation_result = {
            'metadata_model_id': metadata_model['id'],
            'metadata_model_revision_id': metadata_model['revision_id'],
            'errors': validation_errors,
        }
        validation_results += [validation_result]
        accumulated_errors.update(validation_errors)

    metadata_record.extras['validated'] = True
    metadata_record.extras['errors'] = json.dumps(accumulated_errors)

    activity_context = context.copy()
    activity_context.update({
        'defer_commit': True,
        'schema': {
            'user_id': [unicode, tk.get_validator('convert_user_name_or_id_to_id')],
            'object_id': [],
            'revision_id': [],
            'activity_type': [],
            'data': [],
        },
    })
    activity_dict = {
        'user_id': model.User.by_name(user.decode('utf8')).id,
        'object_id': metadata_record_id,
        'activity_type': METADATA_VALIDATION_ACTIVITY_TYPE,
        'data': {
            'action': 'metadata_record_validate',
            'results': validation_results,
        }
    }
    tk.get_action('activity_create')(activity_context, activity_dict)

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

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    workflow_state_id = tk.get_or_bust(data_dict, 'workflow_state_id')
    workflow_state = ckanext_model.WorkflowState.get(workflow_state_id)
    if workflow_state is not None:
        workflow_state_id = workflow_state.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('metadata_record_workflow_state_override', context, data_dict)

    metadata_record.extras['workflow_state_id'] = workflow_state_id

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Override workflow state of metadata record %s') % metadata_record_id

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

    workflow_state_id = tk.get_or_bust(data_dict, 'id')
    workflow_state = ckanext_model.WorkflowState.get(workflow_state_id)
    if workflow_state is not None:
        workflow_state_id = workflow_state.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('workflow_state_update', context, data_dict)

    data_dict.update({
        'id': workflow_state_id,
    })
    context.update({
        'workflow_state': workflow_state,
        'allow_partial_update': True,
    })

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
        rev.message = _(u'REST API: Update workflow state %s') % workflow_state_id

    if not defer_commit:
        model.repo.commit()

    output = workflow_state_id if return_id_only \
        else tk.get_action('workflow_state_show')(context, {'id': workflow_state_id})
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

    workflow_metric_id = tk.get_or_bust(data_dict, 'id')
    workflow_metric = ckanext_model.WorkflowMetric.get(workflow_metric_id)
    if workflow_metric is not None:
        workflow_metric_id = workflow_metric.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Metric')))

    tk.check_access('workflow_metric_update', context, data_dict)

    data_dict.update({
        'id': workflow_metric_id,
    })
    context.update({
        'workflow_metric': workflow_metric,
        'allow_partial_update': True,
    })

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
        rev.message = _(u'REST API: Update workflow metric %s') % workflow_metric_id

    if not defer_commit:
        model.repo.commit()

    output = workflow_metric_id if return_id_only \
        else tk.get_action('workflow_metric_show')(context, {'id': workflow_metric_id})
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

    workflow_rule_id = tk.get_or_bust(data_dict, 'id')
    workflow_rule = ckanext_model.WorkflowRule.get(workflow_rule_id)
    if workflow_rule is not None:
        workflow_rule_id = workflow_rule.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Rule')))

    tk.check_access('workflow_rule_update', context, data_dict)

    data_dict.update({
        'id': workflow_rule_id,
    })
    context.update({
        'workflow_rule': workflow_rule,
        'allow_partial_update': True,
    })

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
        rev.message = _(u'REST API: Update workflow rule %s') % workflow_rule_id

    if not defer_commit:
        model.repo.commit()

    output = workflow_rule_id if return_id_only \
        else tk.get_action('workflow_rule_show')(context, {'id': workflow_rule_id})
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
    """
    log.info("Transitioning workflow state of metadata record: %r", data_dict)

    model = context['model']
    session = context['session']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    target_workflow_state_id = tk.get_or_bust(data_dict, 'workflow_state_id')
    target_workflow_state = ckanext_model.WorkflowState.get(target_workflow_state_id)
    if target_workflow_state is not None:
        target_workflow_state_id = target_workflow_state.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('metadata_record_workflow_state_transition', context, data_dict)

    context.update({
        'metadata_record': metadata_record,
        'workflow_state': target_workflow_state,
    })

    current_workflow_state_id = session.query(model.PackageExtra.value) \
        .filter_by(package_id=metadata_record_id, key='workflow_state_id').scalar()

    # already on target state
    if current_workflow_state_id == target_workflow_state_id:
        return

    workflow_transition = ckanext_model.WorkflowTransition.lookup(current_workflow_state_id, target_workflow_state_id)
    if not workflow_transition or workflow_transition.state != 'active':
        raise tk.ValidationError(_("Invalid workflow state transition"))

    workflow_rules = tk.get_action('workflow_state_rule_list')(context, {'id': target_workflow_state_id})

    # delegate the actual evaluation work to the pluggable action metadata_workflow_rule_evaluate
    rule_results = []
    success = True  # if there are no rules associated with a state, the transition is allowed
    for workflow_rule in workflow_rules:
        rule_success = tk.get_action('metadata_workflow_rule_evaluate')(context, {
            'metadata_json': metadata_record.extras['metadata_json'],
            'evaluator_url': workflow_rule['metric_evaluator_url'],
            'rule_json': workflow_rule['rule_json'],
        })
        rule_result = {
            'workflow_rule_id': workflow_rule['rule_id'],
            'workflow_rule_revision_id': workflow_rule['rule_revision_id'],
            'workflow_metric_id': workflow_rule['metric_id'],
            'workflow_metric_revision_id': workflow_rule['metric_revision_id'],
            'success': rule_success,
        }
        rule_results += [rule_result]
        success = success and rule_success

    if success:
        metadata_record.extras['workflow_state_id'] = target_workflow_state_id

    activity_context = context.copy()
    activity_context.update({
        'defer_commit': True,
        'schema': {
            'user_id': [unicode, tk.get_validator('convert_user_name_or_id_to_id')],
            'object_id': [],
            'revision_id': [],
            'activity_type': [],
            'data': [],
        },
    })
    activity_dict = {
        'user_id': model.User.by_name(user.decode('utf8')).id,
        'object_id': metadata_record_id,
        'activity_type': METADATA_WORKFLOW_ACTIVITY_TYPE,
        'data': {
            'workflow_transition_id': workflow_transition.id,
            'workflow_transition_revision_id': workflow_transition.revision_id,
            'results': rule_results,
        }
    }
    tk.get_action('activity_create')(activity_context, activity_dict)

    if not defer_commit:
        model.repo.commit()
