# encoding: utf-8

import json
import uuid

import ckan.plugins.toolkit as tk
from ckan.common import _
import ckan.lib.navl.dictization_functions as df
import ckanext.metadata.model as ckanext_model


convert_to_extras = tk.get_validator('convert_to_extras')


def _make_uuid():
    return unicode(uuid.uuid4())


def _convert_missing(value, default=None):
    """
    Instead of having to check values for both None and Missing, call this function to
    convert Missing to None (or some other default).
    """
    if value is None or value is tk.missing:
        return default
    return value


# region General validators

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
    if not value:
        return None

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
    if not value:
        return None

    return value

# endregion


# region Framework validators

def organization_exists(group_id_or_name, context):
    """
    Checks that a group of type 'organization' exists with the given name/id,
    and converts name to id if applicable.
    """
    if not group_id_or_name:
        return None

    model = context['model']
    group = model.Group.get(group_id_or_name)
    if not group or group.type != 'organization':
        raise tk.Invalid('%s: %s %s' % (_('Not found'), _('Organization'), group_id_or_name))

    return group.id


def infrastructure_exists(group_id_or_name, context):
    """
    Checks that a group of type 'infrastructure' exists with the given name/id,
    and converts name to id if applicable.
    """
    if not group_id_or_name:
        return None

    model = context['model']
    group = model.Group.get(group_id_or_name)
    if not group or group.type != 'infrastructure':
        raise tk.Invalid('%s: %s %s' % (_('Not found'), _('Infrastructure'), group_id_or_name))

    return group.id


def metadata_collection_exists(group_id_or_name, context):
    """
    Checks that a group of type 'metadata_collection' exists with the given name/id,
    and converts name to id if applicable.
    """
    if not group_id_or_name:
        return None

    model = context['model']
    group = model.Group.get(group_id_or_name)
    if not group or group.type != 'metadata_collection':
        raise tk.Invalid('%s: %s %s' % (_('Not found'), _('Metadata Collection'), group_id_or_name))

    return group.id


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
        extra = session.query(model.PackageExtra).filter_by(package_id=id_, key='metadata_collection_id').first()
        metadata_collection_id = extra.value if extra else None

    extra = session.query(model.GroupExtra).filter_by(group_id=metadata_collection_id, key='organization_id').first()
    metadata_collection_organization_id = extra.value if extra else None

    if organization_id != metadata_collection_organization_id:
        raise tk.Invalid(_("owner_org must be the same organization that owns the metadata collection"))


def metadata_record_schema_selector(key, data, errors, context):
    """
    Sets the metadata_schema_id of a metadata record given the schema name and version
    supplied as input. For use with the '__after' schema key.
    """
    schema_name = _convert_missing(data.get(key[:-1] + ('schema_name',)))
    schema_version = _convert_missing(data.get(key[:-1] + ('schema_version',)))

    if schema_name and schema_version:
        metadata_schema = ckanext_model.MetadataSchema.by_name_and_version(schema_name, schema_version)
        if not metadata_schema:
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
        raise tk.Invalid('%s: %s %s' % (_('Already exists'), _('Group'), group_id_or_name))

    return group_id_or_name


def metadata_model_does_not_exist(metadata_model_id, context):
    if not metadata_model_id:
        return None

    result = ckanext_model.MetadataModel.get(metadata_model_id)
    if result:
        raise tk.Invalid('%s: %s %s' % (_('Already exists'), _('Metadata Model'), metadata_model_id))

    return metadata_model_id


def metadata_schema_exists(metadata_schema_id, context):
    if not metadata_schema_id:
        return None

    result = ckanext_model.MetadataSchema.get(metadata_schema_id)
    if not result:
        raise tk.Invalid('%s: %s %s' % (_('Not found'), _('Metadata Schema'), metadata_schema_id))

    return metadata_schema_id


def metadata_schema_does_not_exist(metadata_schema_id, context):
    if not metadata_schema_id:
        return None

    result = ckanext_model.MetadataSchema.get(metadata_schema_id)
    if result:
        raise tk.Invalid('%s: %s %s' % (_('Already exists'), _('Metadata Schema'), metadata_schema_id))

    return metadata_schema_id


def unique_metadata_schema_name_and_version(key, data, errors, context):
    """
    For use with the '__after' schema key.
    """
    id_ = data.get(key[:-1] + ('id',))
    schema_name = _convert_missing(data.get(key[:-1] + ('schema_name',)))
    schema_version = _convert_missing(data.get(key[:-1] + ('schema_version',)))

    if schema_name and schema_version:
        metadata_schema = ckanext_model.MetadataSchema.by_name_and_version(schema_name, schema_version)
        if metadata_schema and metadata_schema.id != id_:
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
    if metadata_model and metadata_model.id != id_:
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

# endregion
