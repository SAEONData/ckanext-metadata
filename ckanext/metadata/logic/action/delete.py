# encoding: utf-8

import logging

import ckan.plugins.toolkit as tk
from ckan.common import _
import ckanext.metadata.model as ckanext_model

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
    metadata_models = session.query(ckanext_model.MetadataModel) \
        .filter(ckanext_model.MetadataModel.metadata_schema_id == id_) \
        .filter(ckanext_model.MetadataModel.state != 'deleted') \
        .all()
    for metadata_model in metadata_models:
        metadata_model_delete_context = {
            'model': model,
            'user': user,
            'session': session,
            'defer_commit': True,
        }
        tk.get_action('metadata_model_delete')(metadata_model_delete_context, {'id': metadata_model.id})

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
    metadata_models = session.query(ckanext_model.MetadataModel) \
        .filter(ckanext_model.MetadataModel.infrastructure_id == id_) \
        .filter(ckanext_model.MetadataModel.state != 'deleted') \
        .all()
    for metadata_model in metadata_models:
        metadata_model_delete_context = {
            'model': model,
            'user': user,
            'session': session,
            'defer_commit': True,
        }
        tk.get_action('metadata_model_delete')(metadata_model_delete_context, {'id': metadata_model.id})

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


# # TODO: chaining of action functions does not currently work
# @tk.chained_action
# def organization_delete(original_action, context, data_dict):
#     """
#     Delete an organization.
#
#     You must be authorized to delete the organization.
#
#     :param id: the id or name of the organization to delete
#     :type id: string
#     """
#     log.info("Deleting organization: %r", data_dict)
#
#     session = context['session']
#     model = context['model']
#     user = context['user']
#
#     id_ = tk.get_or_bust(data_dict, 'id')
#     obj = model.Group.get(id_)
#     if obj is None or obj.type != 'organization':
#         raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Organization')))
#
#     id_ = obj.id
#     tk.check_access('organization_delete', context, data_dict)
#
#     if session.query(model.Package) \
#             .filter(model.Package.owner_org == id_) \
#             .filter(model.Package.type == 'metadata_record') \
#             .filter(model.Package.state != 'deleted') \
#             .count() > 0:
#         raise tk.ValidationError(_('Organization has dependent metadata records'))
#
#     delete_context = {
#         'model': model,
#         'user': user,
#         'session': session,
#         'defer_commit': True,
#     }
#
#     # cascade delete to dependent metadata collections
#     metadata_collections = session.query(model.Group) \
#         .join(model.GroupExtra, model.Group.id == model.GroupExtra.group_id) \
#         .filter(model.Group.type == 'metadata_collection') \
#         .filter(model.Group.state != 'deleted') \
#         .filter(model.GroupExtra.key == 'organization_id') \
#         .filter(model.GroupExtra.value == id_) \
#         .all()
#     for metadata_collection in metadata_collections:
#         tk.get_action('metadata_collection_delete')(delete_context, {'id': metadata_collection.id})
#
#     # cascade delete to dependent metadata models
#     metadata_models = session.query(ckanext_model.MetadataModel) \
#         .filter(ckanext_model.MetadataModel.organization_id == id_) \
#         .filter(ckanext_model.MetadataModel.state != 'deleted') \
#         .all()
#     for metadata_model in metadata_models:
#         tk.get_action('metadata_model_delete')(delete_context, {'id': metadata_model.id})
#
#     data_dict['type'] = 'organization'
#     original_action(context, data_dict)
