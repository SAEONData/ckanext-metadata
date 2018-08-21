# encoding: utf-8

import logging
from sqlalchemy import or_

import ckan.plugins.toolkit as tk
from ckan.common import _
import ckanext.metadata.model as ckanext_model
from ckanext.metadata.lib.dictization import model_dictize

log = logging.getLogger(__name__)


def metadata_standard_delete(context, data_dict):
    """
    Delete a metadata standard.

    You must be authorized to delete the metadata standard.

    :param id: the id or name of the metadata standard to delete
    :type id: string
    """
    log.info("Deleting metadata standard: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)

    metadata_standard_id = tk.get_or_bust(data_dict, 'id')
    metadata_standard = ckanext_model.MetadataStandard.get(metadata_standard_id)
    if metadata_standard is not None:
        metadata_standard_id = metadata_standard.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Standard')))

    tk.check_access('metadata_standard_delete', context, data_dict)

    if session.query(model.Package) \
            .join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id) \
            .filter(model.PackageExtra.key == 'metadata_standard_id') \
            .filter(model.PackageExtra.value == metadata_standard_id) \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .count() > 0:
        raise tk.ValidationError(_('Metadata standard has dependent metadata records'))

    cascade_context = {
        'model': model,
        'user': user,
        'session': session,
        'defer_commit': True,
    }

    # clear the parent_standard_id on any child metadata standards - implying that
    # such standards are now 'root' standards, no longer derived from this one
    child_standards = session.query(ckanext_model.MetadataStandard) \
        .filter(ckanext_model.MetadataStandard.parent_standard_id == metadata_standard_id) \
        .filter(ckanext_model.MetadataStandard.state != 'deleted') \
        .all()
    for child_standard in child_standards:
        child_standard_dict = model_dictize.metadata_standard_dictize(child_standard, cascade_context)
        child_standard_dict['parent_standard_id'] = ''
        tk.get_action('metadata_standard_update')(cascade_context, child_standard_dict)

    # cascade delete to dependent metadata schemas
    metadata_schema_ids = session.query(ckanext_model.MetadataSchema.id) \
        .filter(ckanext_model.MetadataSchema.metadata_standard_id == metadata_standard_id) \
        .filter(ckanext_model.MetadataSchema.state != 'deleted') \
        .all()
    for (metadata_schema_id,) in metadata_schema_ids:
        tk.get_action('metadata_schema_delete')(cascade_context, {'id': metadata_schema_id})

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete metadata standard %s') % metadata_standard_id

    metadata_standard.delete()
    if not defer_commit:
        model.repo.commit()


def metadata_schema_delete(context, data_dict):
    """
    Delete a metadata schema.

    You must be authorized to delete the metadata schema.

    Any metadata records that were dependent on this schema are invalidated.

    :param id: the id or name of the metadata schema to delete
    :type id: string
    """
    log.info("Deleting metadata schema: %r", data_dict)

    model = context['model']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_schema_id = tk.get_or_bust(data_dict, 'id')
    metadata_schema = ckanext_model.MetadataSchema.get(metadata_schema_id)
    if metadata_schema is not None:
        metadata_schema_id = metadata_schema.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Schema')))

    tk.check_access('metadata_schema_delete', context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete metadata schema %s') % metadata_schema_id

    dependent_record_list = tk.get_action('metadata_schema_dependent_record_list')(context, {'id': metadata_schema_id})
    invalidate_context = context.copy()
    invalidate_context.update({
        'defer_commit': True,
        'trigger_action': 'metadata_schema_delete',
        'trigger_object_id': metadata_schema_id,
    })
    for metadata_record_id in dependent_record_list:
        tk.get_action('metadata_record_invalidate')(invalidate_context, {'id': metadata_record_id})

    metadata_schema.delete()
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

    infrastructure_id = tk.get_or_bust(data_dict, 'id')
    infrastructure = model.Group.get(infrastructure_id)
    if infrastructure is not None and infrastructure.type == 'infrastructure':
        infrastructure_id = infrastructure.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Infrastructure')))

    tk.check_access('infrastructure_delete', context, data_dict)

    if session.query(model.Member) \
            .join(model.Package, model.Package.id == model.Member.table_id) \
            .filter(model.Member.group_id == infrastructure_id) \
            .filter(model.Member.table_name == 'package') \
            .filter(model.Member.state != 'deleted') \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .count() > 0:
        raise tk.ValidationError(_('Infrastructure has dependent metadata records'))

    # cascade delete to dependent metadata schemas
    cascade_context = {
        'model': model,
        'user': user,
        'session': session,
        'defer_commit': True,
    }
    metadata_schema_ids = session.query(ckanext_model.MetadataSchema.id) \
        .filter(ckanext_model.MetadataSchema.infrastructure_id == infrastructure_id) \
        .filter(ckanext_model.MetadataSchema.state != 'deleted') \
        .all()
    for (metadata_schema_id,) in metadata_schema_ids:
        tk.get_action('metadata_schema_delete')(cascade_context, {'id': metadata_schema_id})

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

    metadata_collection_id = tk.get_or_bust(data_dict, 'id')
    metadata_collection = model.Group.get(metadata_collection_id)
    if metadata_collection is not None and metadata_collection.type == 'metadata_collection':
        metadata_collection_id = metadata_collection.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))

    tk.check_access('metadata_collection_delete', context, data_dict)

    if session.query(model.Package) \
            .join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id) \
            .filter(model.PackageExtra.key == 'metadata_collection_id') \
            .filter(model.PackageExtra.value == metadata_collection_id) \
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

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

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

    workflow_state_id = tk.get_or_bust(data_dict, 'id')
    workflow_state = ckanext_model.WorkflowState.get(workflow_state_id)
    if workflow_state is not None:
        workflow_state_id = workflow_state.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('workflow_state_delete', context, data_dict)

    if session.query(model.Package) \
            .join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id) \
            .filter(model.PackageExtra.key == 'workflow_state_id') \
            .filter(model.PackageExtra.value == workflow_state_id) \
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
    referencing_states = session.query(ckanext_model.WorkflowState) \
        .filter(ckanext_model.WorkflowState.revert_state_id == workflow_state_id) \
        .filter(ckanext_model.WorkflowState.state != 'deleted') \
        .all()
    for referencing_state in referencing_states:
        referencing_state_dict = model_dictize.workflow_state_dictize(referencing_state, cascade_context)
        referencing_state_dict['revert_state_id'] = ''
        tk.get_action('workflow_state_update')(cascade_context, referencing_state_dict)

    # cascade delete to dependent workflow transitions
    workflow_transition_ids = session.query(ckanext_model.WorkflowTransition.id) \
        .filter(or_(ckanext_model.WorkflowTransition.from_state_id == workflow_state_id,
                    ckanext_model.WorkflowTransition.to_state_id == workflow_state_id)) \
        .filter(ckanext_model.WorkflowTransition.state != 'deleted') \
        .all()
    for (workflow_transition_id,) in workflow_transition_ids:
        tk.get_action('workflow_transition_delete')(cascade_context, {'id': workflow_transition_id})

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete workflow state %s') % workflow_state_id

    workflow_state.delete()
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

    workflow_transition_id = tk.get_or_bust(data_dict, 'id')
    workflow_transition = ckanext_model.WorkflowTransition.get(workflow_transition_id)
    if workflow_transition is not None:
        workflow_transition_id = workflow_transition.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Transition')))

    tk.check_access('workflow_transition_delete', context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete workflow transition %s') % workflow_transition_id

    workflow_transition.delete()
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

    organization_id = tk.get_or_bust(data_dict, 'id')
    organization = model.Group.get(organization_id)
    if organization is not None and organization.type == 'organization':
        organization_id = organization.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Organization')))

    tk.check_access('organization_delete', context, data_dict)

    if session.query(model.Package) \
            .filter(model.Package.owner_org == organization_id) \
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
        .filter(model.GroupExtra.value == organization_id) \
        .all()
    for (metadata_collection_id,) in metadata_collection_ids:
        tk.get_action('metadata_collection_delete')(cascade_context, {'id': metadata_collection_id})

    # cascade delete to dependent metadata schemas
    metadata_schema_ids = session.query(ckanext_model.MetadataSchema.id) \
        .filter(ckanext_model.MetadataSchema.organization_id == organization_id) \
        .filter(ckanext_model.MetadataSchema.state != 'deleted') \
        .all()
    for (metadata_schema_id,) in metadata_schema_ids:
        tk.get_action('metadata_schema_delete')(cascade_context, {'id': metadata_schema_id})

    # delete membership relations
    for member in session.query(model.Member) \
            .filter(or_(model.Member.table_id == organization_id, model.Member.group_id == organization_id)) \
            .filter(model.Member.state == 'active') \
            .all():
        member.delete()

    # delete non-metadata packages (could potentially leave orphaned packages
    # behind - see comment in ckan.logic.action.delete._group_or_org_delete)
    package_q = organization.packages(with_private=True, return_query=True)
    package_q = package_q.filter(model.Package.type != 'metadata_record')
    for pkg in package_q.all():
        tk.get_action('package_delete')(cascade_context, {'id': pkg.id})

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete organization %s') % organization_id

    organization.delete()
    if not defer_commit:
        model.repo.commit()
