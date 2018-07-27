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


def metadata_model_dict_save(metadata_model_dict, context):
    return _object_dict_save(metadata_model_dict, 'metadata_model', ckanext_model.MetadataModel,
                             ckanext_model.metadata_model_table, context)


def metadata_schema_dict_save(metadata_schema_dict, context):
    return _object_dict_save(metadata_schema_dict, 'metadata_schema', ckanext_model.MetadataSchema,
                             ckanext_model.metadata_schema_table, context)


def workflow_state_dict_save(workflow_state_dict, context):
    return _object_dict_save(workflow_state_dict, 'workflow_state', ckanext_model.WorkflowState,
                             ckanext_model.workflow_state_table, context)


def workflow_transition_dict_save(workflow_transition_dict, context):
    return _object_dict_save(workflow_transition_dict, 'workflow_transition', ckanext_model.WorkflowTransition,
                             ckanext_model.workflow_transition_table, context)


def workflow_annotation_dict_save(workflow_annotation_dict, context):
    return _object_dict_save(workflow_annotation_dict, 'workflow_annotation', ckanext_model.WorkflowAnnotation,
                             ckanext_model.workflow_annotation_table, context)


def _object_dict_save(object_dict, model_name, model_class, table, context):
    session = context['session']
    obj = context.get(model_name)
    if obj:
        object_dict['id'] = obj.id
    else:
        # in case of a unique constraint collision with an existing deleted record,
        # we undelete the record and update it
        unique_constraints = d.get_unique_constraints(table, context)
        for constraint in unique_constraints:
            params = dict((key, object_dict.get(key)) for key in constraint)
            obj = session.query(model_class).filter_by(**params).first()
            if obj:
                if obj.state != 'deleted' or object_dict.get('id', obj.id) != obj.id:
                    raise tk.Invalid(_("Unique constraint violation: %s") % constraint)
                object_dict['id'] = obj.id
                object_dict['state'] = 'active'

    return d.table_dict_save(object_dict, model_class, context)
