# encoding: utf-8

from sqlalchemy.sql import select

import ckan.plugins.toolkit as tk
import ckan.lib.dictization as d
import ckan.lib.dictization.model_dictize as ckan_model_dictize
from ckanext.metadata.common import model_info
import ckanext.metadata.model as model_ext


def metadata_record_dictize(pkg, context):
    """
    Based on ckan.lib.dictization.model_dictize.package_dictize
    """
    model = context['model']
    is_latest_revision = not(context.get('revision_id') or
                             context.get('revision_date'))
    execute = _execute if is_latest_revision else _execute_with_revision

    # package
    if is_latest_revision:
        if isinstance(pkg, model.PackageRevision):
            pkg = model.Package.get(pkg.id)
        result = pkg
    else:
        package_rev = model.package_revision_table
        q = select([package_rev]).where(package_rev.c.id == pkg.id)
        result = execute(q, package_rev, context).first()
    if not result:
        raise tk.ObjectNotFound

    result_dict = d.table_dictize(result, context)
    if result_dict.get('title'):
        result_dict['title'] = result_dict['title'].strip()
    result_dict['display_name'] = result_dict['title'] or result_dict['name'] or result_dict['id']

    # extras
    if is_latest_revision:
        extra = model.package_extra_table
    else:
        extra = model.extra_revision_table
    q = select([extra]).where(extra.c.package_id == pkg.id)
    result = execute(q, extra, context)
    result_dict['extras'] = ckan_model_dictize.extras_list_dictize(result, context)

    return result_dict


def metadata_collection_dictize(metadata_collection, context):
    model = context['model']
    is_latest_revision = not(context.get('revision_id') or
                             context.get('revision_date'))
    execute = _execute if is_latest_revision else _execute_with_revision

    result_dict = ckan_model_dictize.group_dictize(metadata_collection, context,
                                                   include_groups=False,
                                                   include_tags=False,
                                                   include_users=False,
                                                   include_extras=True,
                                                   packages_field='dataset_count')

    # infrastructures
    if is_latest_revision:
        member = model.member_table
    else:
        member = model.member_revision_table
    group = model.group_table
    q = select([group, member.c.capacity],
               from_obj=member.join(group, group.c.id == member.c.group_id)
               ).where(member.c.table_id == metadata_collection.id)\
                .where(member.c.state == 'active') \
                .where(group.c.is_organization == False) \
                .where(group.c.type == 'infrastructure')
    result = execute(q, member, context)
    context['with_capacity'] = False
    result_dict['infrastructures'] = ckan_model_dictize.group_list_dictize(
        result, context, with_package_counts=False)

    return result_dict


def metadata_record_activity_dictize(activity, context):
    model = context['model']
    session = context['session']
    activity_dict = ckan_model_dictize.activity_dictize(activity, context)
    activity_details = session.query(model.ActivityDetail) \
        .filter(model.ActivityDetail.activity_id == activity.id) \
        .all()
    activity_dict['details'] = ckan_model_dictize.activity_detail_list_dictize(activity_details, context)
    return activity_dict


def metadata_schema_dictize(metadata_schema, context):

    def group_display_name(group_id):
        if not group_id:
            return
        group = model.Group.get(group_id)
        group_dict = ckan_model_dictize.group_dictize(
            group, context, include_groups=False, include_tags=False, include_users=False, include_extras=False)
        return group_dict['display_name']

    model = context['model']
    metadata_schema_dict = _object_dictize('metadata_schema', metadata_schema, context)
    metadata_standard = model_ext.MetadataStandard.get(metadata_schema.metadata_standard_id)
    metadata_standard_dict = metadata_standard_dictize(metadata_standard, context)
    metadata_schema_dict['display_name'] = metadata_standard_dict['display_name']

    linked_display_name = group_display_name(metadata_schema.organization_id or metadata_schema.infrastructure_id)
    if linked_display_name:
        metadata_schema_dict['display_name'] += ' - {}'.format(linked_display_name)

    return metadata_schema_dict


def metadata_standard_dictize(metadata_standard, context):
    metadata_standard_dict = _object_dictize('metadata_standard', metadata_standard, context)
    metadata_standard_dict['display_name'] = metadata_standard.standard_name
    if metadata_standard.standard_version:
        metadata_standard_dict['display_name'] += ' ' + metadata_standard.standard_version
    return metadata_standard_dict


def workflow_state_dictize(workflow_state, context):
    workflow_state_dict = _object_dictize('workflow_state', workflow_state, context)
    workflow_state_dict['display_name'] = workflow_state_dict['title'] or workflow_state_dict['name']
    return workflow_state_dict


def workflow_transition_dictize(workflow_transition, context):

    def workflow_state_display_name(workflow_state_id):
        if not workflow_state_id:
            return tk._('(None)')
        workflow_state = model_ext.WorkflowState.get(workflow_state_id)
        workflow_state_dict = workflow_state_dictize(workflow_state, context)
        return workflow_state_dict['display_name']

    workflow_transition_dict = _object_dictize('workflow_transition', workflow_transition, context)
    workflow_transition_dict['from_state_display_name'] = workflow_state_display_name(workflow_transition.from_state_id)
    workflow_transition_dict['to_state_display_name'] = workflow_state_display_name(workflow_transition.to_state_id)
    return workflow_transition_dict


def workflow_annotation_dictize(workflow_annotation, context):
    return _object_dictize('workflow_annotation', workflow_annotation, context)


def metadata_json_attr_map_dictize(metadata_json_attr_map, context):
    return _object_dictize('metadata_json_attr_map', metadata_json_attr_map, context)


def _object_dictize(model_name, obj, context):
    model_class = model_info[model_name]['model']
    rev_model_class = model_info[model_name]['rev_model']
    rev_table = model_info[model_name]['rev_table']

    is_latest_revision = not(context.get('revision_id') or context.get('revision_date'))
    execute = _execute if is_latest_revision else _execute_with_revision
    if is_latest_revision:
        if isinstance(obj, rev_model_class):
            obj = model_class.get(obj.id)
        result = obj
    else:
        q = select([(rev_table)]).where(rev_table.c.id == obj.id)
        result = execute(q, rev_table, context).first()
    if not result:
        raise tk.ObjectNotFound

    return d.table_dictize(result, context)


def _execute(q, table, context):
    """
    Copied from ckan.lib.dictization.model_dictize

    Takes an SqlAlchemy query (q) that is (at its base) a Select on an
    object table (table), and it returns the object.

    Analogous with _execute_with_revision, so takes the same params, even
    though it doesn't need the table.
    """
    model = context['model']
    session = model.Session
    return session.execute(q)


def _execute_with_revision(q, rev_table, context):
    """
    Copied from ckan.lib.dictization.model_dictize

    Takes an SqlAlchemy query (q) that is (at its base) a Select on an object
    revision table (rev_table), and you provide revision_id or revision_date in
    the context and it will filter the object revision(s) to an earlier time.

    Raises NotFound if context['revision_id'] is provided, but the revision
    ID does not exist.

    Returns [] if there are no results.
    """
    model = context['model']
    session = model.Session
    revision_id = context.get('revision_id')
    revision_date = context.get('revision_date')

    if revision_id:
        revision = session.query(context['model'].Revision).filter_by(
            id=revision_id).first()
        if not revision:
            raise tk.ObjectNotFound
        revision_date = revision.timestamp

    q = q.where(rev_table.c.revision_timestamp <= revision_date)
    q = q.where(rev_table.c.expired_timestamp > revision_date)

    return session.execute(q)
