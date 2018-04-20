# encoding: utf-8

import ckan.authz as authz
import ckan.lib.dictization as d
import ckan.plugins.toolkit as tk
import ckanext.metadata.model as ckanext_model
from ckan.common import _


def metadata_record_infrastructure_list_save(infrastructure_dicts, context):
    """
    Modified from ckan.lib.dictization.model_save.package_membership_list_save
    """
    allow_partial_update = context.get("allow_partial_update", False)
    if infrastructure_dicts is None and allow_partial_update:
        return

    model = context['model']
    session = context['session']
    user = context.get('user')
    package = context.get('package')
    capacity = 'public'

    members = session.query(model.Member) \
        .join(model.Group, model.Member.group_id==model.Group.id) \
        .filter(model.Group.type == 'infrastructure') \
        .filter(model.Member.table_id == package.id) \
        .filter(model.Member.capacity != 'organization')

    infrastructure_members = dict((member.group, member) for member in members)

    infrastructures = set()
    for infrastructure_dict in infrastructure_dicts or []:
        infrastructure = model.Group.get(infrastructure_dict['id'])
        if infrastructure:
            infrastructures.add(infrastructure)

    # Remove any infrastructure groups we are no longer in
    for infrastructure in set(infrastructure_members.keys()) - infrastructures:
        member_obj = infrastructure_members[infrastructure]
        if member_obj and member_obj.state == 'deleted':
            continue
        if authz.has_user_permission_for_group_or_org(
                member_obj.group_id, user, 'read'):
            member_obj.capacity = capacity
            member_obj.state = 'deleted'
            session.add(member_obj)

    # Add any new infrastructure groups
    for infrastructure in infrastructures:
        member_obj = infrastructure_members.get(infrastructure)
        if member_obj and member_obj.state == 'active':
            continue
        if authz.has_user_permission_for_group_or_org(
                infrastructure.id, user, 'read'):
            member_obj = infrastructure_members.get(infrastructure)
            if member_obj:
                member_obj.capacity = capacity
                member_obj.state = 'active'
            else:
                member_obj = model.Member(group=infrastructure,
                                          group_id=infrastructure.id,
                                          table_name='package',
                                          table_id=package.id,
                                          capacity=capacity,
                                          state='active')
            session.add(member_obj)

    session.flush()


def metadata_model_dict_save(metadata_model_dict, context):
    session = context['session']
    obj = context.get('metadata_model')
    if obj:
        metadata_model_dict['id'] = obj.id
    else:
        # in case of a unique constraint collision with an existing deleted record,
        # we undelete the record and update it
        unique_constraints = d.get_unique_constraints(ckanext_model.metadata_model_table, context)
        for constraint in unique_constraints:
            params = dict((key, metadata_model_dict.get(key)) for key in constraint)
            obj = session.query(ckanext_model.MetadataModel).filter_by(**params).first()
            if obj:
                if obj.state != 'deleted' or metadata_model_dict.get('id', obj.id) != obj.id:
                    raise tk.Invalid(_("Unique constraint violation: %s") % constraint)
                metadata_model_dict['id'] = obj.id
                metadata_model_dict['state'] = 'active'

    metadata_model = d.table_dict_save(metadata_model_dict, ckanext_model.MetadataModel, context)
    session.flush()
    return metadata_model


def metadata_schema_dict_save(metadata_schema_dict, context):
    session = context['session']
    obj = context.get('metadata_schema')
    if obj:
        metadata_schema_dict['id'] = obj.id
    else:
        # in case of a unique constraint collision with an existing deleted record,
        # we undelete the record and update it
        unique_constraints = d.get_unique_constraints(ckanext_model.metadata_schema_table, context)
        for constraint in unique_constraints:
            params = dict((key, metadata_schema_dict.get(key)) for key in constraint)
            obj = session.query(ckanext_model.MetadataSchema).filter_by(**params).first()
            if obj:
                if obj.state != 'deleted' or metadata_schema_dict.get('id', obj.id) != obj.id:
                    raise tk.Invalid(_("Unique constraint violation: %s") % constraint)
                metadata_schema_dict['id'] = obj.id
                metadata_schema_dict['state'] = 'active'

    metadata_schema = d.table_dict_save(metadata_schema_dict, ckanext_model.MetadataSchema, context)
    session.flush()
    return metadata_schema
