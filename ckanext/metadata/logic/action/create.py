# encoding: utf-8

import logging

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.logic import schema, MetadataValidationState
from ckanext.metadata.lib.dictization import model_save

log = logging.getLogger(__name__)


# optional params may or may not be supplied by the caller
# nullable params must be supplied but may be empty
# all other params must be supplied and must not be empty

def metadata_schema_create(context, data_dict):
    """
    Create a new metadata schema.

    You must be authorized to create metadata schemas.

    :param id: the id of the metadata schema (optional - only sysadmins can set this)
    :type id: string
    :param name: the name of the new metadata schema (optional - auto-generated if not supplied);
        must conform to standard naming rules
    :type name: string
    :param title: the title of the metadata schema (optional)
    :type title: string
    :param description: the description of the metadata schema (optional)
    :type description: string
    :param schema_name: the name of the metadata schema
    :type schema_name: string
    :param schema_version: the version of the metadata schema (nullable)
    :type schema_version: string
    :param schema_xsd: the XSD document defining the schema (nullable)
    :type schema_xsd: string
    :param base_schema_id: the id or name of the metadata schema from which this schema is derived (nullable)
    :type base_schema_id: string

    :returns: the newly created metadata schema (unless 'return_id_only' is set to True
              in the context, in which case just the metadata schema id will be returned)
    :rtype: dictionary
    """
    log.info("Creating metadata schema: %r", data_dict)
    tk.check_access('metadata_schema_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data, errors = tk.navl_validate(data_dict, schema.metadata_schema_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_schema = model_save.metadata_schema_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create metadata schema %s') % metadata_schema.id

    if not defer_commit:
        model.repo.commit()

    output = metadata_schema.id if return_id_only \
        else tk.get_action('metadata_schema_show')(context, {'id': metadata_schema.id})
    return output


def metadata_model_create(context, data_dict):
    """
    Create a new metadata model.

    You must be authorized to create metadata models.

    A model must be one and only one of the following:
    - the default for the given schema (no organization or infrastructure)
    - associated with an organization
    - associated with an infrastructure

    Any metadata records that are now dependent on this model are invalidated.

    :param id: the id of the metadata model (optional - only sysadmins can set this)
    :type id: string
    :param name: the name of the new metadata model (optional - auto-generated if not supplied);
        must conform to standard naming rules
    :type name: string
    :param title: the title of the metadata model (optional)
    :type title: string
    :param description: the description of the metadata model (optional)
    :type description: string
    :param metadata_schema_id: the id or name of the metadata schema from which this model is derived
    :type metadata_schema_id: string
    :param model_json: the JSON dictionary defining the model (nullable)
    :type model_json: string
    :param organization_id: the id or name of the associated organization (nullable)
    :type organization_id: string
    :param infrastructure_id: the id or name of the associated infrastructure (nullable)
    :type infrastructure_id: string

    :returns: the newly created metadata model (unless 'return_id_only' is set to True
              in the context, in which case just the metadata model id will be returned)
    :rtype: dictionary
    """
    log.info("Creating metadata model: %r", data_dict)
    tk.check_access('metadata_model_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data, errors = tk.navl_validate(data_dict, schema.metadata_model_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_model = model_save.metadata_model_dict_save(data, context)

    # creating the revision also flushes the session which gives us the new object id
    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create metadata model %s') % metadata_model.id

    dependent_record_list = tk.get_action('metadata_model_dependent_record_list')(context, {'id': metadata_model.id})
    invalidate_context = context
    invalidate_context['defer_commit'] = True
    for metadata_record_id in dependent_record_list:
        tk.get_action('metadata_record_invalidate')(invalidate_context, {'id': metadata_record_id})

    if not defer_commit:
        model.repo.commit()

    output = metadata_model.id if return_id_only \
        else tk.get_action('metadata_model_show')(context, {'id': metadata_model.id})
    return output


def infrastructure_create(context, data_dict):
    """
    Create a group of type 'infrastructure'.
    
    You must be authorized to create infrastructures.

    :param id: the id of the infrastructure (optional - only sysadmins can set this)
    :type id: string
    :param name: the name of the infrastructure; must conform to group naming rules
    :type name: string
    :param title: the title of the infrastructure (optional)
    :type title: string
    :param description: the description of the infrastructure (optional)
    :type description: string
    :param users: the users associated with the infrastructure (optional); a list of dictionaries
        each with key ``'name'`` (string, the id or name of the user) and optionally ``'capacity'``
        (string, the capacity in which the user is a member of the infrastructure)
    :type users: list of dictionaries

    :returns: the newly created infrastructure (unless 'return_id_only' is set to True
              in the context, in which case just the infrastructure id will be returned)
    :rtype: dictionary
    """
    log.info("Creating infrastructure: %r", data_dict)
    tk.check_access('infrastructure_create', context, data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data_dict['type'] = 'infrastructure'
    data_dict['is_organization'] = False
    context['schema'] = schema.infrastructure_create_schema()
    context['invoked_api'] = 'infrastructure_create'
    context['defer_commit'] = True
    context['return_id_only'] = True

    # defer_commit does not actually work due to a bug in _group_or_org_create (in ckan.logic.action.create)
    # - addition of the creating user as a member is done (committed) without consideration for defer_commit
    # - but it does not make much difference to us here
    infrastructure_id = tk.get_action('group_create')(context, data_dict)

    if not defer_commit:
        model.repo.commit()

    output = infrastructure_id if return_id_only \
        else tk.get_action('infrastructure_show')(context, {'id': infrastructure_id})
    return output


def metadata_collection_create(context, data_dict):
    """
    Create a group of type 'metadata_collection'.

    You must be authorized to create metadata collections.

    :param id: the id of the metadata collection (optional - only sysadmins can set this)
    :type id: string
    :param name: the name of the metadata collection; must conform to group naming rules
    :type name: string
    :param title: the title of the metadata collection (optional)
    :type title: string
    :param description: the description of the metadata collection (optional)
    :type description: string
    :param organization_id: the id or name of the organization to which this collection belongs
    :type organization_id: string
    :param users: the users associated with the collection (optional); a list of dictionaries
        each with key ``'name'`` (string, the id or name of the user) and optionally ``'capacity'``
        (string, the capacity in which the user is a member of the collection)
    :type users: list of dictionaries

    :returns: the newly created metadata collection (unless 'return_id_only' is set to True
              in the context, in which case just the metadata collection id will be returned)
    :rtype: dictionary
    """
    log.info("Creating metadata collection: %r", data_dict)
    tk.check_access('metadata_collection_create', context, data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data_dict['type'] = 'metadata_collection'
    data_dict['is_organization'] = False
    context['schema'] = schema.metadata_collection_create_schema()
    context['invoked_api'] = 'metadata_collection_create'
    context['defer_commit'] = True
    context['return_id_only'] = True

    # defer_commit does not actually work due to a bug in _group_or_org_create (in ckan.logic.action.create)
    # - addition of the creating user as a member is done (committed) without consideration for defer_commit
    # - but it does not make much difference to us here
    metadata_collection_id = tk.get_action('group_create')(context, data_dict)

    if not defer_commit:
        model.repo.commit()

    output = metadata_collection_id if return_id_only \
        else tk.get_action('metadata_collection_show')(context, {'id': metadata_collection_id})
    return output


def metadata_record_create(context, data_dict):
    """
    Create a package of type 'metadata_record'.

    You must be authorized to create metadata records.

    :param id: the id of the metadata record (optional - only sysadmins can set this)
    :type id: string
    :param name: the name of the new metadata record (optional - auto-generated if not supplied);
        must conform to package naming rules
    :type name: string
    :param title: the title of the metadata record (optional)
    :type title: string
    :param owner_org: the id or name of the organization to which this record belongs
    :type owner_org: string
    :param metadata_collection_id: the id or name of the metadata collection to which this record will be added
    :type metadata_collection_id: string
    :param infrastructures: the infrastructures associated with the record (nullable - may be an empty list);
        list of dictionaries each with key ``'id'`` (string, the id or name of the infrastructure)
    :type infrastructures: list of dictionaries
    :param metadata_schema_id: the id or name of the metadata schema that describes the record's structure
    :type metadata_schema_id: string
    :param metadata_json: JSON dictionary of metadata record content (nullable)
    :type metadata_json: string
    :param metadata_raw: original unmodified metadata (nullable)
    :type metadata_raw: string
    :param metadata_url: URL pointing to original unmodified metadata (nullable)
    :type metadata_url: string

    :returns: the newly created metadata record (unless 'return_id_only' is set to True
              in the context, in which case just the metadata record id will be returned)
    :rtype: dictionary
    """
    log.info("Creating metadata record: %r", data_dict)
    tk.check_access('metadata_record_create', context, data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data_dict['type'] = 'metadata_record'
    data_dict['validation_state'] = MetadataValidationState.NOT_VALIDATED
    data_dict['workflow_state_id'] = None

    context['schema'] = schema.metadata_record_create_schema()
    context['invoked_api'] = 'metadata_record_create'
    context['defer_commit'] = True
    context['return_id_only'] = True

    metadata_record_id = tk.get_action('package_create')(context, data_dict)
    model_save.metadata_record_infrastructure_list_save(data_dict.get('infrastructures'), context)

    if not defer_commit:
        model.repo.commit()

    output = metadata_record_id if return_id_only \
        else tk.get_action('metadata_record_show')(context, {'id': metadata_record_id})
    return output


def workflow_state_create(context, data_dict):
    """
    Create a new workflow state.

    You must be authorized to create workflow states.

    :param id: the id of the workflow state (optional - only sysadmins can set this)
    :type id: string
    :param name: the name of the new workflow state; must conform to standard naming rules
    :type name: string
    :param title: the title of the workflow state (optional)
    :type title: string
    :param description: the description of the workflow state (optional)
    :type description: string
    :param revert_state_id: the id or name of the state to which a metadata record is
        reverted in case it no longer fulfils the rules for this state (nullable)
    :type revert_state_id: string

    :returns: the newly created workflow state (unless 'return_id_only' is set to True
              in the context, in which case just the workflow state id will be returned)
    :rtype: dictionary
    """
    log.info("Creating workflow state: %r", data_dict)
    tk.check_access('workflow_state_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data, errors = tk.navl_validate(data_dict, schema.workflow_state_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_state = model_save.workflow_state_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create workflow state %s') % workflow_state.id

    if not defer_commit:
        model.repo.commit()

    output = workflow_state.id if return_id_only \
        else tk.get_action('workflow_state_show')(context, {'id': workflow_state.id})
    return output


def workflow_transition_create(context, data_dict):
    """
    Create a new workflow transition.

    You must be authorized to create workflow transitions.

    :param id: the id of the workflow transition (optional - only sysadmins can set this)
    :type id: string
    :param from_state_id: the id or name of the source workflow state (nullable - null implies
        that the target state is an initial workflow state)
    :type from_state_id: string
    :param to_state_id: the id or name of the target workflow state
    :type to_state_id: string

    :returns: the newly created workflow transition (unless 'return_id_only' is set to True
              in the context, in which case just the workflow transition id will be returned)
    :rtype: dictionary
    """
    log.info("Creating workflow transition: %r", data_dict)
    tk.check_access('workflow_transition_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data, errors = tk.navl_validate(data_dict, schema.workflow_transition_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_transition = model_save.workflow_transition_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create workflow transition %s') % workflow_transition.id

    if not defer_commit:
        model.repo.commit()

    output = workflow_transition.id if return_id_only \
        else tk.get_action('workflow_transition_show')(context, {'id': workflow_transition.id})
    return output


def workflow_metric_create(context, data_dict):
    """
    Create a new workflow metric.

    You must be authorized to create workflow metrics.

    :param id: the id of the workflow metric (optional - only sysadmins can set this)
    :type id: string
    :param name: the name of the new workflow metric; must conform to standard naming rules
    :type name: string
    :param title: the title of the workflow metric (optional)
    :type title: string
    :param description: the description of the workflow metric (optional)
    :type description: string
    :param evaluator_url: URI of the service that will evaluate rules linked to this metric
    :type evaluator_url: string

    :returns: the newly created workflow metric (unless 'return_id_only' is set to True
              in the context, in which case just the workflow metric id will be returned)
    :rtype: dictionary
    """
    log.info("Creating workflow metric: %r", data_dict)
    tk.check_access('workflow_metric_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data, errors = tk.navl_validate(data_dict, schema.workflow_metric_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_metric = model_save.workflow_metric_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create workflow metric %s') % workflow_metric.id

    if not defer_commit:
        model.repo.commit()

    output = workflow_metric.id if return_id_only \
        else tk.get_action('workflow_metric_show')(context, {'id': workflow_metric.id})
    return output


def workflow_rule_create(context, data_dict):
    """
    Create a new workflow rule.

    You must be authorized to create workflow rules.

    :param id: the id of the workflow rule (optional - only sysadmins can set this)
    :type id: string
    :param workflow_state_id: the id or name of the workflow state to which this rule applies
    :type workflow_state_id: string
    :param workflow_metric_id: the id or name of the workflow metric to be evaluated
    :type workflow_metric_id: string
    :param rule_json: JSON object defining acceptable return value/range from metric
        evaluation to pass this rule
    :type rule_json: string

    :returns: the newly created workflow rule (unless 'return_id_only' is set to True
              in the context, in which case just the workflow rule id will be returned)
    :rtype: dictionary
    """
    log.info("Creating workflow rule: %r", data_dict)
    tk.check_access('workflow_rule_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data, errors = tk.navl_validate(data_dict, schema.workflow_rule_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_rule = model_save.workflow_rule_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create workflow rule %s') % workflow_rule.id

    if not defer_commit:
        model.repo.commit()

    output = workflow_rule.id if return_id_only \
        else tk.get_action('workflow_rule_show')(context, {'id': workflow_rule.id})
    return output
