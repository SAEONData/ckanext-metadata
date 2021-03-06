# encoding: utf-8

import ckan.authz as authz
import ckan.lib.dictization as d
import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.common import model_info


def metadata_record_collection_membership_save(metadata_collection_id, context):
    """
    Save the member record representing the metadata record's membership of its metadata
    collection. Modified from ckan.lib.dictization.model_save.package_membership_list_save.
    """
    model = context['model']
    session = context['session']
    user = context.get('user')
    package = context.get('package')
    capacity = 'public'

    members = session.query(model.Member) \
        .join(model.Group, model.Member.group_id==model.Group.id) \
        .filter(model.Group.type == 'metadata_collection') \
        .filter(model.Member.table_id == package.id) \
        .filter(model.Member.table_name == 'package')

    collection_members = dict((member.group, member) for member in members)

    new_collection = model.Group.get(metadata_collection_id)

    # Remove any metadata collection groups we are no longer in (there should be max 1 of these)
    for old_collection in set(collection_members.keys()) - {new_collection}:
        member_obj = collection_members[old_collection]
        if member_obj and member_obj.state == 'deleted':
            continue
        member_obj.capacity = capacity
        member_obj.state = 'deleted'
        session.add(member_obj)

    # Add the record to the new metadata collection group
    member_obj = collection_members.get(new_collection)
    if member_obj and member_obj.state == 'active':
        return
    if member_obj:
        member_obj.capacity = capacity
        member_obj.state = 'active'
    else:
        member_obj = model.Member(group=new_collection,
                                  group_id=new_collection.id,
                                  table_name='package',
                                  table_id=package.id,
                                  capacity=capacity,
                                  state='active')
    session.add(member_obj)


def metadata_collection_organization_membership_save(organization_id, context):
    """
    Save the member record representing the metadata collections's membership of its organization.
    Modified from ckan.lib.dictization.model_save.package_membership_list_save.
    """
    model = context['model']
    session = context['session']
    user = context.get('user')
    collection = context.get('group')
    capacity = 'parent'

    members = session.query(model.Member) \
        .join(model.Group, model.Member.group_id==model.Group.id) \
        .filter(model.Group.type == 'organization') \
        .filter(model.Member.table_id == collection.id) \
        .filter(model.Member.table_name == 'group')

    organization_members = dict((member.group, member) for member in members)

    new_organization = model.Group.get(organization_id)

    # Remove any organizations we are no longer in (there should be max 1 of these)
    for old_organization in set(organization_members.keys()) - {new_organization}:
        member_obj = organization_members[old_organization]
        if member_obj and member_obj.state == 'deleted':
            continue
        member_obj.capacity = capacity
        member_obj.state = 'deleted'
        session.add(member_obj)

    # Add the collection to the new organization
    member_obj = organization_members.get(new_organization)
    if member_obj and member_obj.state == 'active':
        return
    if member_obj:
        member_obj.capacity = capacity
        member_obj.state = 'active'
    else:
        member_obj = model.Member(group=new_organization,
                                  group_id=new_organization.id,
                                  table_name='group',
                                  table_id=collection.id,
                                  capacity=capacity,
                                  state='active')
    session.add(member_obj)


def metadata_record_infrastructure_list_save(infrastructure_dicts, context):
    """
    Save the member records representing the metadata record's membership of its infrastructure
    groups. Modified from ckan.lib.dictization.model_save.package_membership_list_save
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
        .filter(model.Member.table_name == 'package')

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
        member_obj.capacity = capacity
        member_obj.state = 'deleted'
        session.add(member_obj)

    # Add any new infrastructure groups
    for infrastructure in infrastructures:
        member_obj = infrastructure_members.get(infrastructure)
        if member_obj and member_obj.state == 'active':
            continue
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


def metadata_collection_infrastructure_list_save(infrastructure_dicts, context):
    """
    Save the member records representing the metadata collection's membership of its infrastructure
    groups. Modified from ckan.lib.dictization.model_save.package_membership_list_save
    """
    allow_partial_update = context.get("allow_partial_update", False)
    if infrastructure_dicts is None and allow_partial_update:
        return

    model = context['model']
    session = context['session']
    user = context.get('user')
    group = context.get('group')
    capacity = 'public'

    members = session.query(model.Member) \
        .join(model.Group, model.Member.group_id==model.Group.id) \
        .filter(model.Group.type == 'infrastructure') \
        .filter(model.Member.table_id == group.id) \
        .filter(model.Member.table_name == 'group')

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
        member_obj.capacity = capacity
        member_obj.state = 'deleted'
        session.add(member_obj)

    # Add any new infrastructure groups
    for infrastructure in infrastructures:
        member_obj = infrastructure_members.get(infrastructure)
        if member_obj and member_obj.state == 'active':
            continue
        if member_obj:
            member_obj.capacity = capacity
            member_obj.state = 'active'
        else:
            member_obj = model.Member(group=infrastructure,
                                      group_id=infrastructure.id,
                                      table_name='group',
                                      table_id=group.id,
                                      capacity=capacity,
                                      state='active')
        session.add(member_obj)


def metadata_schema_dict_save(metadata_schema_dict, context):
    return _object_dict_save('metadata_schema', metadata_schema_dict, context)


def metadata_standard_dict_save(metadata_standard_dict, context):
    return _object_dict_save('metadata_standard', metadata_standard_dict, context)


def workflow_state_dict_save(workflow_state_dict, context):
    return _object_dict_save('workflow_state', workflow_state_dict, context)


def workflow_transition_dict_save(workflow_transition_dict, context):
    return _object_dict_save('workflow_transition', workflow_transition_dict, context)


def workflow_annotation_dict_save(workflow_annotation_dict, context):
    return _object_dict_save('workflow_annotation', workflow_annotation_dict, context)


def metadata_json_attr_map_dict_save(metadata_json_attr_map_dict, context):
    return _object_dict_save('metadata_json_attr_map', metadata_json_attr_map_dict, context)


def _object_dict_save(model_name, object_dict, context):
    model_class = model_info[model_name]['model']
    table = model_info[model_name]['table']

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
