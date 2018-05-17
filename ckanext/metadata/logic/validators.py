# encoding: utf-8

import json
import uuid
import re

import ckan.plugins.toolkit as tk
from ckan.common import _
import ckan.lib.navl.dictization_functions as df
import ckanext.metadata.model as ckanext_model


convert_to_extras = tk.get_validator('convert_to_extras')


def _make_uuid():
    return unicode(uuid.uuid4())


def _convert_missing(value, default=None):
    """
    Convert Missing to None or some other default.
    """
    if value is tk.missing:
        return default
    return value


def _group_desc(group_type):
    """
    Returns the descriptive form of a group type (for e.g. error/log messages).
    """
    return group_type.replace('_', ' ').title()


def _generate_name(*strings):
    """
    Converts the given string(s) into a form suitable for an object name.
    """
    strings = list(strings)
    while '' in strings:
        strings.remove('')
    text = '_'.join(strings)
    return re.sub('[^a-z0-9_\-]+', '-', text.lower())


def _object_does_not_exist(object_id_or_name, model_class, model_desc):
    """
    Checks that an object id/name is not already in use.
    """
    if not object_id_or_name:
        return None

    result = model_class.get(object_id_or_name)
    if result:
        raise tk.Invalid('%s: %s' % (_('Already exists'), _(model_desc)))

    return object_id_or_name


def _object_exists(key, data, errors, model_class, model_desc):
    """
    Checks that an object exists and is not deleted,
    and converts name to id if applicable.
    """
    object_id_or_name = data.get(key)
    if not object_id_or_name:
        data[key] = None
        raise tk.StopOnError

    obj = model_class.get(object_id_or_name)
    if not obj or obj.state == 'deleted':
        errors[key].append('%s: %s' % (_('Not found'), _(model_desc)))
        raise tk.StopOnError

    data[key] = obj.id


def _name_validator(key, data, errors, context, model_name, model_class, model_desc):
    session = context['session']
    obj = context.get(model_name)

    query = session.query(model_class.name).filter_by(name=data[key])
    id_ = obj.id if obj else _convert_missing(data.get(key[:-1] + ('id',)))
    if id_:
        query = query.filter(model_class.id != id_)
    result = query.first()
    if result:
        errors[key].append('%s: %s' % (_('Duplicate name'), _(model_desc)))


# region General validators / converters

def not_missing(key, data, errors, context):
    """
    Replaces the built-in CKAN validator not_missing, so that we can distinguish
    between missing and empty values.
    """
    value = data.get(key)
    if value is tk.missing:
        errors.setdefault(key, [])
        errors[key].append(_('Missing parameter'))
        raise tk.StopOnError


def not_empty(key, data, errors, context):
    """
    Replaces the built-in CKAN validator not_empty, so that we can distinguish
    between missing and empty values. This checks not_missing as well.
    """
    not_missing(key, data, errors, context)
    value = data.get(key)
    if not value:
        errors.setdefault(key, [])
        errors[key].append(_('Missing value'))
        raise tk.StopOnError


def json_dict_validator(value):
    """
    Checks for well-formed JSON, and that the supplied JSON represents a dictionary.
    """
    if value:
        try:
            obj = json.loads(value)
        except ValueError, e:
            raise tk.Invalid(_("JSON decode error: %s") % e.message)

        if type(obj) is not dict:
            raise tk.Invalid(_("Expecting a JSON dictionary"))

    return value


def xsd_validator(value):
    """
    TODO
    Check for well-formed XSD.
    """
    return value


def deserialize_json(value):
    """
    Converts a JSON-format string to an object - for use in "show" schemas
    enabling JSON fields to be nicely embedded in output dicts. If it cannot
    be deserialized, just return the value itself.
    """
    try:
        return json.loads(value)
    except:
        return value


def uri_validator(value):
    """
    TODO
    Check for a well-formed URI.
    """
    return value

# endregion


# region Framework validators / converters

def group_exists(group_type):
    """
    Checks that a group exists, is of the specified type and is not deleted,
    and converts name to id if applicable.
    """
    def callable_(key, data, errors, context):
        group_id_or_name = data.get(key)
        if not group_id_or_name:
            data[key] = None
            raise tk.StopOnError

        model = context['model']
        group = model.Group.get(group_id_or_name)
        if not group or group.type != group_type or group.state == 'deleted':
            errors[key].append('%s: %s' % (_('Not found'), _(_group_desc(group_type))))
            raise tk.StopOnError

        data[key] = group.id

    return callable_


def owner_org_owns_metadata_collection(key, data, errors, context):
    """
    Checks that the owner_org specified for a metadata record is the same organization that
    owns the metadata collection to which the record is being added.
    For use with the '__after' schema key; group names should already have been converted to group ids.
    """
    model = context['model']
    session = context['session']

    organization_id = data.get(key[:-1] + ('owner_org',))
    metadata_collection_id = _convert_missing(data.get(key[:-1] + ('metadata_collection_id',)))

    id_ = _convert_missing(data.get(key[:-1] + ('id',)))
    obj = model.Package.get(id_) if id_ else None

    # if we're updating, missing value(s) in the input data imply a partial update, so get the
    # existing value(s) and check that the updated combination satisfies our condition
    organization_id = _convert_missing(organization_id, obj.owner_org if obj else None)
    if obj and not metadata_collection_id:
        metadata_collection_id = session.query(model.PackageExtra.value) \
            .filter_by(package_id=id_, key='metadata_collection_id').scalar()

    metadata_collection_organization_id = session.query(model.GroupExtra.value) \
        .filter_by(group_id=metadata_collection_id, key='organization_id').scalar()

    if organization_id != metadata_collection_organization_id:
        raise tk.Invalid(_("owner_org must be the same organization that owns the metadata collection"))


def metadata_record_schema_selector(key, data, errors, context):
    """
    Sets the metadata_schema_id of a metadata record given the schema name and version
    supplied as input. For use with the '__after' schema key.
    """
    schema_name = _convert_missing(data.get(key[:-1] + ('schema_name',)))
    schema_version = _convert_missing(data.get(key[:-1] + ('schema_version',)))

    metadata_schema = ckanext_model.MetadataSchema.lookup(schema_name, schema_version)
    if not metadata_schema or metadata_schema.state == 'deleted':
        raise tk.Invalid(_("Could not find a metadata schema with schema_name='%s'"
                           " and schema_version='%s'") % (schema_name, schema_version))

    data[key[:-1] + ('metadata_schema_id',)] = metadata_schema.id
    convert_to_extras(key[:-1] + ('metadata_schema_id',), data, errors, context)


def metadata_record_id_name_generator(key, data, errors, context):
    """
    Generates id and name for a new metadata record where these values have not been supplied.
    For use with the '__after' schema key.
    """
    if errors.get(key[:-1] + ('id',)):
        return  # id was supplied but has been popped out of data due to an error

    model = context['model']
    id_ = _convert_missing(data.get(key[:-1] + ('id',)))
    name = _convert_missing(data.get(key[:-1] + ('name',)))

    if id_ and model.Package.get(id_):
        return  # we only need to generate on create

    if not id_:
        id_ = _make_uuid()
        data[key[:-1] + ('id',)] = id_
    if not name:
        name = 'metadata-' + id_
        data[key[:-1] + ('name',)] = name


def metadata_record_infrastructures_not_missing(key, data, errors, context):
    """
    Checks that the infrastructures list is not missing.
    For use with the '__before' schema key; CKAN puts empty lists into __extras,
    so we check that and pop as necessary.
    """
    unflattened = df.unflatten(data)
    infrastructures = unflattened.get('infrastructures')
    if infrastructures is not None:
        return

    extras = data.get(key[:-1] + ('__extras',), {})
    infrastructures = extras.get('infrastructures')
    if infrastructures is not None:
        extras.pop('infrastructures')
        return

    errors.setdefault(key[:-1] + ('infrastructures',), [])
    errors[key[:-1] + ('infrastructures',)].append(_('Missing parameter'))


def group_does_not_exist(group_id_or_name, context):
    if not group_id_or_name:
        return None

    model = context['model']
    result = model.Group.get(group_id_or_name)
    if result:
        raise tk.Invalid('%s: %s' % (_('Already exists'), _('Group')))

    return group_id_or_name


def metadata_model_does_not_exist(metadata_model_id_or_name, context):
    return _object_does_not_exist(metadata_model_id_or_name, ckanext_model.MetadataModel, 'Metadata Model')


def metadata_schema_exists(key, data, errors, context):
    _object_exists(key, data, errors, ckanext_model.MetadataSchema, 'Metadata Schema')


def metadata_schema_does_not_exist(metadata_schema_id_or_name, context):
    return _object_does_not_exist(metadata_schema_id_or_name, ckanext_model.MetadataSchema, 'Metadata Schema')


def unique_metadata_schema_name_and_version(key, data, errors, context):
    """
    For use with the '__after' schema key.
    """
    id_ = data.get(key[:-1] + ('id',))
    schema_name = _convert_missing(data.get(key[:-1] + ('schema_name',)))
    schema_version = _convert_missing(data.get(key[:-1] + ('schema_version',)))

    metadata_schema = ckanext_model.MetadataSchema.lookup(schema_name, schema_version)
    if metadata_schema and metadata_schema.state != 'deleted' and metadata_schema.id != id_:
        raise tk.Invalid(_("Unique constraint violation: %s") % '(schema_name, schema_version)')


def no_loops_in_metadata_schema_hierarchy(key, data, errors, context):
    """
    Checks that the base schema specified in the data would not cause
    a loop in the metadata schema hierarchy.
    """
    metadata_schema = context.get('metadata_schema')
    if not metadata_schema:
        return  # it's a new schema - no children

    base_schema_id = data.get(key[:-1] + ('base_schema_id',))
    parent = ckanext_model.MetadataSchema.get(base_schema_id) \
        if base_schema_id is not None else None

    while parent is not None:
        if parent == metadata_schema:
            raise tk.Invalid(_("Loop in metadata schema hierarchy"))
        parent = ckanext_model.MetadataSchema.get(parent.base_schema_id) \
            if parent.base_schema_id is not None else None


def metadata_model_unique_schema_organization_infrastructure(key, data, errors, context):
    """
    Checks the uniqueness of metadata_schema-organization-infrastructure for a metadata model.
    For use with the '__after' schema key; group names should already have been converted to group ids.
    """
    metadata_schema_id = data.get(key[:-1] + ('metadata_schema_id',))
    organization_id = data.get(key[:-1] + ('organization_id',))
    infrastructure_id = data.get(key[:-1] + ('infrastructure_id',))

    id_ = _convert_missing(data.get(key[:-1] + ('id',)))
    obj = ckanext_model.MetadataModel.get(id_) if id_ else None

    # if we're updating, missing value(s) in the input data imply a partial update, so get the
    # existing value(s) and check that the updated key does not violate uniqueness
    metadata_schema_id = _convert_missing(metadata_schema_id, obj.metadata_schema_id if obj else None)
    organization_id = _convert_missing(organization_id, obj.organization_id if obj else None)
    infrastructure_id = _convert_missing(infrastructure_id, obj.infrastructure_id if obj else None)

    metadata_model = ckanext_model.MetadataModel.lookup(metadata_schema_id, organization_id, infrastructure_id)
    if metadata_model and metadata_model.state != 'deleted' and metadata_model.id != id_:
        raise tk.Invalid(_("Unique constraint violation: %s") % '(metadata_schema_id, organization_id, infrastructure_id)')


def metadata_model_check_organization_infrastructure(key, data, errors, context):
    """
    Checks that only one of organization and infrastructure have been set for a metadata model.
    For use with the '__after' schema key; group names should already have been converted to group ids.
    """
    organization_id = data.get(key[:-1] + ('organization_id',))
    infrastructure_id = data.get(key[:-1] + ('infrastructure_id',))

    id_ = _convert_missing(data.get(key[:-1] + ('id',)))
    obj = ckanext_model.MetadataModel.get(id_) if id_ else None

    # if we're updating, missing value(s) in the input data imply a partial update, so get the
    # existing value(s) and check that the updated combination does not violate the check constraint
    organization_id = _convert_missing(organization_id, obj.organization_id if obj else None)
    infrastructure_id = _convert_missing(infrastructure_id, obj.infrastructure_id if obj else None)

    if organization_id and infrastructure_id:
        raise tk.Invalid(_("A metadata model may be associated with either an organization or an "
                           "infrastructure but not both."))


def metadata_schema_name_validator(key, data, errors, context):
    _name_validator(key, data, errors, context, 'metadata_schema', ckanext_model.MetadataSchema, 'Metadata Schema')


def metadata_model_name_validator(key, data, errors, context):
    _name_validator(key, data, errors, context, 'metadata_model', ckanext_model.MetadataModel, 'Metadata Model')


def metadata_schema_name_generator(key, data, errors, context):
    """
    Generates the name for a metadata schema if not supplied. For use with the '__after' schema key.
    """
    name = _convert_missing(data.get(key[:-1] + ('name',)))
    if not name:
        id_ = _convert_missing(data.get(key[:-1] + ('id',)))
        if id_:
            metadata_schema = ckanext_model.MetadataSchema.get(id_)
            if metadata_schema:
                # for updates we want to re-generate the name only if it was previously auto-generated
                autoname = _generate_name(metadata_schema.schema_name, metadata_schema.schema_version)
                if metadata_schema.name != autoname:
                    return

        schema_name = _convert_missing(data.get(key[:-1] + ('schema_name',)), '')
        schema_version = _convert_missing(data.get(key[:-1] + ('schema_version',)), '')
        name = _generate_name(schema_name, schema_version)
        data[key[:-1] + ('name',)] = name


def metadata_model_name_generator(key, data, errors, context):
    """
    Generates the name for a metadata model if not supplied. For use with the '__after' schema key.
    """
    model = context['model']

    def get_name_components(metadata_schema_id, organization_id, infrastructure_id):
        metadata_schema = ckanext_model.MetadataSchema.get(metadata_schema_id)
        organization = model.Group.get(organization_id) if organization_id else None
        infrastructure = model.Group.get(infrastructure_id) if infrastructure_id else None

        metadata_schema_name = metadata_schema.name if metadata_schema else ''
        organization_name = organization.name if organization else ''
        infrastructure_name = infrastructure.name if infrastructure else ''

        return metadata_schema_name, organization_name, infrastructure_name

    name = _convert_missing(data.get(key[:-1] + ('name',)))
    if not name:
        id_ = _convert_missing(data.get(key[:-1] + ('id',)))
        if id_:
            metadata_model = ckanext_model.MetadataModel.get(id_)
            if metadata_model:
                # for updates we want to re-generate the name only if it was previously auto-generated
                metadata_schema_name, organization_name, infrastructure_name = get_name_components(
                    metadata_model.metadata_schema_id,
                    metadata_model.organization_id,
                    metadata_model.infrastructure_id
                )
                autoname = _generate_name(metadata_schema_name, organization_name, infrastructure_name)
                if metadata_model.name != autoname:
                    return

        metadata_schema_name, organization_name, infrastructure_name = get_name_components(
            _convert_missing(data.get(key[:-1] + ('metadata_schema_id',))),
            _convert_missing(data.get(key[:-1] + ('organization_id',))),
            _convert_missing(data.get(key[:-1] + ('infrastructure_id',)))
        )
        name = _generate_name(metadata_schema_name, organization_name, infrastructure_name)
        data[key[:-1] + ('name',)] = name


def workflow_state_does_not_exist(workflow_state_id_or_name, context):
    return _object_does_not_exist(workflow_state_id_or_name, ckanext_model.WorkflowState, 'Workflow State')


def workflow_transition_does_not_exist(workflow_transition_id, context):
    return _object_does_not_exist(workflow_transition_id, ckanext_model.WorkflowTransition, 'Workflow Transition')


def workflow_metric_does_not_exist(workflow_metric_id_or_name, context):
    return _object_does_not_exist(workflow_metric_id_or_name, ckanext_model.WorkflowMetric, 'Workflow Metric')


def workflow_rule_does_not_exist(workflow_rule_id, context):
    return _object_does_not_exist(workflow_rule_id, ckanext_model.WorkflowRule, 'Workflow Rule')


def workflow_state_exists(key, data, errors, context):
    _object_exists(key, data, errors, ckanext_model.WorkflowState, 'Workflow State')


def workflow_metric_exists(key, data, errors, context):
    _object_exists(key, data, errors, ckanext_model.WorkflowMetric, 'Workflow Metric')


def workflow_state_name_validator(key, data, errors, context):
    _name_validator(key, data, errors, context, 'workflow_state', ckanext_model.WorkflowState, 'Workflow State')


def workflow_metric_name_validator(key, data, errors, context):
    _name_validator(key, data, errors, context, 'workflow_metric', ckanext_model.WorkflowMetric, 'Workflow Metric')


def workflow_revert_state_validator(key, data, errors, context):
    """
    Checks that the revert state specified in the data would not cause
    a loop in the workflow state graph.
    """
    workflow_state = context.get('workflow_state')
    if not workflow_state:
        # it's a new state - no other state reverts to this one, and no transitions
        # involving this state exist, yet
        return

    revert_state_id = data.get(key[:-1] + ('revert_state_id',))
    target_state = ckanext_model.WorkflowState.get(revert_state_id) \
        if revert_state_id is not None else None

    if target_state is None:
        return

    if ckanext_model.WorkflowTransition.path_exists(workflow_state.id, target_state.id):
        raise tk.Invalid(_("Loop in workflow state graph"))

    while target_state is not None:
        if target_state == workflow_state:
            raise tk.Invalid(_("Loop in workflow state graph"))
        target_state = ckanext_model.WorkflowState.get(target_state.revert_state_id) \
            if target_state.revert_state_id is not None else None


def workflow_transition_check(key, data, errors, context):
    """
    Checks that the from and to states are not the same. For use with the '__after' schema key.
    """
    from_state_id = data.get(key[:-1] + ('from_state_id',))
    to_state_id = data.get(key[:-1] + ('to_state_id',))

    if from_state_id == to_state_id:
        raise tk.Invalid(_("The from- and to-state of a workflow transition cannot be the same."))


def workflow_transition_unique(key, data, errors, context):
    """
    For use with the '__after' schema key.
    """
    id_ = data.get(key[:-1] + ('id',))
    from_state_id = _convert_missing(data.get(key[:-1] + ('from_state_id',)))
    to_state_id = _convert_missing(data.get(key[:-1] + ('to_state_id',)))

    workflow_transition = ckanext_model.WorkflowTransition.lookup(from_state_id, to_state_id)
    if workflow_transition and workflow_transition.state != 'deleted' and workflow_transition.id != id_:
        raise tk.Invalid(_("Unique constraint violation: %s") % '(from_state_id, to_state_id)')


def workflow_state_graph_validator(key, data, errors, context):
    """
    Checks that the specified workflow transition would not cause
    a loop in the workflow state graph.
    """
    from_state_id = _convert_missing(data.get(key[:-1] + ('from_state_id',)))
    to_state_id = _convert_missing(data.get(key[:-1] + ('to_state_id',)))
    
    if ckanext_model.WorkflowTransition.path_exists(to_state_id, from_state_id):
        raise tk.Invalid(_("Loop in workflow state graph"))


def workflow_rule_unique(key, data, errors, context):
    """
    For use with the '__after' schema key.
    """
    id_ = data.get(key[:-1] + ('id',))
    workflow_state_id = _convert_missing(data.get(key[:-1] + ('workflow_state_id',)))
    workflow_metric_id = _convert_missing(data.get(key[:-1] + ('workflow_metric_id',)))

    workflow_rule = ckanext_model.WorkflowRule.lookup(workflow_state_id, workflow_metric_id)
    if workflow_rule and workflow_rule.state != 'deleted' and workflow_rule.id != id_:
        raise tk.Invalid(_("Unique constraint violation: %s") % '(workflow_state_id, workflow_metric_id)')

# endregion
