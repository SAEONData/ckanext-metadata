# encoding: utf-8

import logging
from sqlalchemy import or_

import ckan.plugins.toolkit as tk
from ckan.common import _
import ckanext.metadata.model as ckanext_model
from ckanext.metadata.lib.dictization import model_dictize

log = logging.getLogger(__name__)


def metadata_schema_delete(context, data_dict):
    """
    Delete a metadata schema.

    You must be authorized to delete the metadata schema.

    :param id: the id or name of the metadata schema to delete
    :type id: string
    """
    log.info("Deleting metadata schema: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.MetadataSchema.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Schema')))

    id_ = obj.id
    tk.check_access('metadata_schema_delete', context, data_dict)

    errors = []
    if session.query(ckanext_model.MetadataSchema) \
            .filter(ckanext_model.MetadataSchema.base_schema_id == id_) \
            .filter(ckanext_model.MetadataSchema.state != 'deleted') \
            .count() > 0:
        errors += [_('Metadata schema has dependent metadata schemas.')]

    if session.query(model.Package) \
            .join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id) \
            .filter(model.PackageExtra.key == 'metadata_schema_id') \
            .filter(model.PackageExtra.value == id_) \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .count() > 0:
        errors += [_('Metadata schema has dependent metadata records.')]

    if errors:
        raise tk.ValidationError(' '.join(errors))

    # cascade delete to dependent metadata models
    cascade_context = {
        'model': model,
        'user': user,
        'session': session,
        'defer_commit': True,
    }
    metadata_model_ids = session.query(ckanext_model.MetadataModel.id) \
        .filter(ckanext_model.MetadataModel.metadata_schema_id == id_) \
        .filter(ckanext_model.MetadataModel.state != 'deleted') \
        .all()
    for (metadata_model_id,) in metadata_model_ids:
        tk.get_action('metadata_model_delete')(cascade_context, {'id': metadata_model_id})

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete metadata schema %s') % id_

    obj.delete()
    if not defer_commit:
        model.repo.commit()


def metadata_model_delete(context, data_dict):
    """
    Delete a metadata model.

    You must be authorized to delete the metadata model.

    Any metadata records that were dependent on this model are invalidated.

    :param id: the id or name of the metadata model to delete
    :type id: string
    """
    log.info("Deleting metadata model: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.MetadataModel.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Model')))

    id_ = obj.id
    tk.check_access('metadata_model_delete', context, data_dict)

    dependent_record_list = tk.get_action('metadata_model_dependent_record_list')(context, {'id': id_})
    invalidate_context = context
    invalidate_context['defer_commit'] = True
    for metadata_record_id in dependent_record_list:
        tk.get_action('metadata_record_invalidate')(invalidate_context, {'id': metadata_record_id})

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete metadata model %s') % id_

    obj.delete()
    if not defer_commit:
        model.repo.commit()


def infrastructure_delete(context, data_dict):
    """
    Delete an infrastructure.

    You must be authorized to delete the infrastructure.

    :param id: the id or name of the infrastructure to delete
    :type id: string
    """
    log.info("Deleting infrastructure: %r", data_dict)

    session = context['session']
    model = context['model']
    user = context['user']

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Group.get(id_)
    if obj is None or obj.type != 'infrastructure':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Infrastructure')))

    id_ = obj.id
    tk.check_access('infrastructure_delete', context, data_dict)

    if session.query(model.Member) \
            .join(model.Package, model.Package.id == model.Member.table_id) \
            .filter(model.Member.group_id == id_) \
            .filter(model.Member.table_name == 'package') \
            .filter(model.Member.state != 'deleted') \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .count() > 0:
        raise tk.ValidationError(_('Infrastructure has dependent metadata records'))

    # cascade delete to dependent metadata models
    cascade_context = {
        'model': model,
        'user': user,
        'session': session,
        'defer_commit': True,
    }
    metadata_model_ids = session.query(ckanext_model.MetadataModel.id) \
        .filter(ckanext_model.MetadataModel.infrastructure_id == id_) \
        .filter(ckanext_model.MetadataModel.state != 'deleted') \
        .all()
    for (metadata_model_id,) in metadata_model_ids:
        tk.get_action('metadata_model_delete')(cascade_context, {'id': metadata_model_id})

    data_dict['type'] = 'infrastructure'
    context['invoked_api'] = 'infrastructure_delete'

    tk.get_action('group_delete')(context, data_dict)


def metadata_collection_delete(context, data_dict):
    """
    Delete a metadata collection.

    You must be authorized to delete the metadata collection.

    :param id: the id or name of the metadata collection to delete
    :type id: string
    """
    log.info("Deleting metadata collection: %r", data_dict)

    session = context['session']
    model = context['model']

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Group.get(id_)
    if obj is None or obj.type != 'metadata_collection':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))

    id_ = obj.id
    tk.check_access('metadata_collection_delete', context, data_dict)

    if session.query(model.Package) \
            .join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id) \
            .filter(model.PackageExtra.key == 'metadata_collection_id') \
            .filter(model.PackageExtra.value == id_) \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .count() > 0:
        raise tk.ValidationError(_('Metadata collection has dependent metadata records'))

    data_dict['type'] = 'metadata_collection'
    context['invoked_api'] = 'metadata_collection_delete'

    tk.get_action('group_delete')(context, data_dict)


def metadata_record_delete(context, data_dict):
    """
    Delete a metadata record.

    You must be authorized to delete the metadata record.

    :param id: the id or name of the metadata record to delete
    :type id: string
    """
    log.info("Deleting metadata record: %r", data_dict)

    model = context['model']

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Package.get(id_)
    if obj is None or obj.type != 'metadata_record':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    id_ = obj.id
    tk.check_access('metadata_record_delete', context, data_dict)

    data_dict['type'] = 'metadata_record'
    context['invoked_api'] = 'metadata_record_delete'

    tk.get_action('package_delete')(context, data_dict)


def workflow_state_delete(context, data_dict):
    """
    Delete a workflow state.

    You must be authorized to delete the workflow state.

    :param id: the id or name of the workflow state to delete
    :type id: string
    """
    log.info("Deleting workflow state: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.WorkflowState.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    id_ = obj.id
    tk.check_access('workflow_state_delete', context, data_dict)

    if session.query(model.Package) \
            .join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id) \
            .filter(model.PackageExtra.key == 'workflow_state_id') \
            .filter(model.PackageExtra.value == id_) \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .count() > 0:
        raise tk.ValidationError(_('Workflow state has dependent metadata records.'))

    cascade_context = {
        'model': model,
        'user': user,
        'session': session,
        'defer_commit': True,
    }

    # clear the revert_state_id on any referencing workflow states - this implies that
    # reverting from such states would now take a metadata record to the 'null' state
    # instead of this one
    workflow_states = session.query(ckanext_model.WorkflowState) \
        .filter(ckanext_model.WorkflowState.revert_state_id == id_) \
        .filter(ckanext_model.WorkflowState.state != 'deleted') \
        .all()
    for workflow_state in workflow_states:
        workflow_state_dict = model_dictize.workflow_state_dictize(workflow_state, cascade_context)
        workflow_state_dict['revert_state_id'] = ''
        tk.get_action('workflow_state_update')(cascade_context, workflow_state_dict)

    # cascade delete to dependent workflow transitions
    workflow_transition_ids = session.query(ckanext_model.WorkflowTransition.id) \
        .filter(or_(ckanext_model.WorkflowTransition.from_state_id == id_,
                    ckanext_model.WorkflowTransition.to_state_id == id_)) \
        .filter(ckanext_model.WorkflowTransition.state != 'deleted') \
        .all()
    for (workflow_transition_id,) in workflow_transition_ids:
        tk.get_action('workflow_transition_delete')(cascade_context, {'id': workflow_transition_id})

    # cascade delete to dependent workflow rules
    workflow_rule_ids = session.query(ckanext_model.WorkflowRule.id) \
        .filter(ckanext_model.WorkflowRule.workflow_state_id == id_) \
        .filter(ckanext_model.WorkflowRule.state != 'deleted') \
        .all()
    for (workflow_rule_id,) in workflow_rule_ids:
        tk.get_action('workflow_rule_delete')(cascade_context, {'id': workflow_rule_id})

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete workflow state %s') % id_

    obj.delete()
    if not defer_commit:
        model.repo.commit()


def workflow_transition_delete(context, data_dict):
    """
    Delete a workflow transition.

    You must be authorized to delete the workflow transition.

    :param id: the id or name of the workflow transition to delete
    :type id: string
    """
    log.info("Deleting workflow transition: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.WorkflowTransition.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Transition')))

    id_ = obj.id
    tk.check_access('workflow_transition_delete', context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete workflow transition %s') % id_

    obj.delete()
    if not defer_commit:
        model.repo.commit()


def workflow_metric_delete(context, data_dict):
    """
    Delete a workflow metric.

    You must be authorized to delete the workflow metric.

    :param id: the id or name of the workflow metric to delete
    :type id: string
    """
    log.info("Deleting workflow metric: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.WorkflowMetric.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Metric')))

    id_ = obj.id
    tk.check_access('workflow_metric_delete', context, data_dict)

    # cascade delete to dependent workflow rules
    cascade_context = {
        'model': model,
        'user': user,
        'session': session,
        'defer_commit': True,
    }
    workflow_rule_ids = session.query(ckanext_model.WorkflowRule.id) \
        .filter(ckanext_model.WorkflowRule.workflow_metric_id == id_) \
        .filter(ckanext_model.WorkflowRule.state != 'deleted') \
        .all()
    for (workflow_rule_id,) in workflow_rule_ids:
        tk.get_action('workflow_rule_delete')(cascade_context, {'id': workflow_rule_id})

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete workflow metric %s') % id_

    obj.delete()
    if not defer_commit:
        model.repo.commit()


def workflow_rule_delete(context, data_dict):
    """
    Delete a workflow rule.

    You must be authorized to delete the workflow rule.

    :param id: the id or name of the workflow rule to delete
    :type id: string
    """
    log.info("Deleting workflow rule: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = ckanext_model.WorkflowRule.get(id_)
    if obj is None:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Rule')))

    id_ = obj.id
    tk.check_access('workflow_rule_delete', context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete workflow rule %s') % id_

    obj.delete()
    if not defer_commit:
        model.repo.commit()


def organization_delete(context, data_dict):
    """
    Delete an organization.

    You must be authorized to delete the organization.

    :param id: the id or name of the organization to delete
    :type id: string
    """
    log.info("Deleting organization: %r", data_dict)

    session = context['session']
    model = context['model']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    id_ = tk.get_or_bust(data_dict, 'id')
    obj = model.Group.get(id_)
    if obj is None or obj.type != 'organization':
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Organization')))

    id_ = obj.id
    tk.check_access('organization_delete', context, data_dict)

    if session.query(model.Package) \
            .filter(model.Package.owner_org == id_) \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .count() > 0:
        raise tk.ValidationError(_('Organization has dependent metadata records'))

    cascade_context = {
        'model': model,
        'user': user,
        'session': session,
        'defer_commit': True,
    }

    # cascade delete to dependent metadata collections
    metadata_collection_ids = session.query(model.Group.id) \
        .join(model.GroupExtra, model.Group.id == model.GroupExtra.group_id) \
        .filter(model.Group.type == 'metadata_collection') \
        .filter(model.Group.state != 'deleted') \
        .filter(model.GroupExtra.key == 'organization_id') \
        .filter(model.GroupExtra.value == id_) \
        .all()
    for (metadata_collection_id,) in metadata_collection_ids:
        tk.get_action('metadata_collection_delete')(cascade_context, {'id': metadata_collection_id})

    # cascade delete to dependent metadata models
    metadata_model_ids = session.query(ckanext_model.MetadataModel.id) \
        .filter(ckanext_model.MetadataModel.organization_id == id_) \
        .filter(ckanext_model.MetadataModel.state != 'deleted') \
        .all()
    for (metadata_model_id,) in metadata_model_ids:
        tk.get_action('metadata_model_delete')(cascade_context, {'id': metadata_model_id})

    # delete membership relations
    for member in session.query(model.Member) \
            .filter(or_(model.Member.table_id == id_, model.Member.group_id == id_)) \
            .filter(model.Member.state == 'active') \
            .all():
        member.delete()

    # delete non-metadata packages (could potentially leave orphaned packages
    # behind - see comment in ckan.logic.action.delete._group_or_org_delete)
    package_q = obj.packages(with_private=True, return_query=True)
    package_q = package_q.filter(model.Package.type != 'metadata_record')
    for pkg in package_q.all():
        tk.get_action('package_delete')(cascade_context, {'id': pkg.id})

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete organization %s') % id_

    obj.delete()
    if not defer_commit:
        model.repo.commit()
