# encoding: utf-8

from sqlalchemy.sql import select

import ckan.plugins.toolkit as tk
import ckan.lib.dictization as d
import ckan.lib.dictization.model_dictize as ckan_model_dictize
from ckanext.metadata.common import model_info


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
        raise tk.NotFound
    result_dict = d.table_dictize(result, context)
    # strip whitespace from title
    if result_dict.get('title'):
        result_dict['title'] = result_dict['title'].strip()

    # extras
    if is_latest_revision:
        extra = model.package_extra_table
    else:
        extra = model.extra_revision_table
    q = select([extra]).where(extra.c.package_id == pkg.id)
    result = execute(q, extra, context)
    result_dict['extras'] = ckan_model_dictize.extras_list_dictize(result, context)

    # infrastructures
    if is_latest_revision:
        member = model.member_table
    else:
        member = model.member_revision_table
    group = model.group_table
    q = select([group, member.c.capacity],
               from_obj=member.join(group, group.c.id == member.c.group_id)
               ).where(member.c.table_id == pkg.id)\
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
    return _object_dictize('metadata_schema', metadata_schema, context)


def metadata_standard_dictize(metadata_standard, context):
    return _object_dictize('metadata_standard', metadata_standard, context)


def workflow_state_dictize(workflow_state, context):
    return _object_dictize('workflow_state', workflow_state, context)


def workflow_transition_dictize(workflow_transition, context):
    return _object_dictize('workflow_transition', workflow_transition, context)


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
