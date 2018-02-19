# encoding: utf-8

import ckan.plugins.toolkit as tk

from ckanext.metadata.logic import validators as v

# shortcuts to toolkit validators / converters
empty = tk.get_validator('empty')
not_empty = tk.get_validator('not_empty')
ignore = tk.get_validator('ignore')
ignore_missing = tk.get_validator('ignore_missing')
package_id_does_not_exist = tk.get_validator('package_id_does_not_exist')
name_validator = tk.get_validator('name_validator')
package_name_validator = tk.get_validator('package_name_validator')
group_name_validator = tk.get_validator('group_name_validator')
empty_if_not_sysadmin = tk.get_validator('empty_if_not_sysadmin')
ignore_not_package_admin = tk.get_validator('ignore_not_package_admin')
ignore_not_group_admin = tk.get_validator('ignore_not_group_admin')
owner_org_validator = tk.get_validator('owner_org_validator')
convert_to_extras = tk.get_validator('convert_to_extras')
convert_from_extras = tk.get_validator('convert_from_extras')
keep_extras = tk.get_validator('keep_extras')


def _make_create_schema(schema):
    """
    Add some defaults to a "create" schema.
    """
    schema.update({
        # disallow anything not in the schema
        '__extras': [empty],
        '__junk': [empty],
    })


def _make_update_schema(schema):
    """
    Modify a "create" schema to be suitable for an "update" action.
    """
    schema['id'] = []

    # set top-level fields to be non-required
    # (nested lists are inherently non-required)
    for key, value in schema.iteritems():
        if type(value) is list:
            for i, validator in enumerate(value):
                if validator is not_empty:
                    schema[key][i] = ignore_missing


def _make_show_schema(schema):
    """
    Modify a "create" schema to be suitable for a "show" action.
    """
    # recursively clear all validator lists
    for key, value in schema.iteritems():
        if type(value) is list:
            schema[key] = []
        elif type(value) is dict:
            _make_show_schema(schema[key])

    schema.update({
        'revision_id': [],
        '__extras': [ignore],
        '__junk': [ignore],
    })


def _extras_schema():
    return {
        'key': [],
        'value': [],
    }


def metadata_record_create_schema():
    schema = {
        # from the default package schema
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, package_id_does_not_exist],
        'name': [ignore_missing, unicode, name_validator, package_name_validator],
        'title': [ignore_missing, unicode],
        'state': [ignore_not_package_admin, ignore_missing],
        'owner_org': [not_empty, owner_org_validator, unicode],
        'type': [],

        # extension-specific fields
        'metadata_collection_id': [not_empty, unicode, v.metadata_collection_exists, convert_to_extras],
        'infrastructures': {
            'id': [not_empty, unicode, v.infrastructure_exists],
        },
        'schema_name': [not_empty, unicode],
        'schema_version': [not_empty, unicode],
        'content_json': [ignore_missing, unicode, v.json_dict_validator, convert_to_extras],
        'content_raw': [ignore_missing, unicode, convert_to_extras],
        'content_url': [ignore_missing, unicode, convert_to_extras],

        # post-validation
        '__after': [v.metadata_record_id_name_generator,
                    v.owner_org_owns_metadata_collection,
                    v.metadata_record_schema_selector,
                    ignore],
    }
    _make_create_schema(schema)
    return schema


def metadata_record_update_schema():
    schema = metadata_record_create_schema()
    _make_update_schema(schema)
    return schema


def metadata_record_show_schema():
    schema = metadata_record_create_schema()
    _make_show_schema(schema)
    schema.update({
        'metadata_schema_id': [convert_from_extras],
        'content_json': [convert_from_extras, ignore_missing],
        'content_raw': [convert_from_extras, ignore_missing],
        'content_url': [convert_from_extras, ignore_missing],
        'metadata_collection_id': [convert_from_extras],
        'private': [],
        'extras': _extras_schema(),
    })
    del schema['schema_name'], schema['schema_version']
    return schema


def metadata_collection_create_schema():
    schema = {
        # from the default group schema
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.group_does_not_exist],
        'name': [not_empty, unicode, name_validator, group_name_validator],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'state': [ignore_not_group_admin, ignore_missing],
        'type': [],
        'is_organization': [],

        # extension-specific fields
        'organization_id': [not_empty, unicode, v.organization_exists, convert_to_extras],
    }
    _make_create_schema(schema)
    return schema


def metadata_collection_update_schema():
    schema = metadata_collection_create_schema()
    schema['organization_id'] = [empty]  # cannot change the organization to which a collection belongs
    _make_update_schema(schema)
    return schema


def metadata_collection_show_schema():
    schema = metadata_collection_create_schema()
    _make_show_schema(schema)
    schema.update({
        'organization_id': [convert_from_extras],
        'extras': _extras_schema(),
    })
    return schema


def infrastructure_create_schema():
    schema = {
        # from the default group schema
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.group_does_not_exist],
        'name': [not_empty, unicode, name_validator, group_name_validator],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'state': [ignore_not_group_admin, ignore_missing],
        'type': [],
        'is_organization': [],
        'users': {
            "name": [not_empty, unicode],
            "capacity": [ignore_missing],
            "__extras": [ignore]
        },
    }
    _make_create_schema(schema)
    return schema


def infrastructure_update_schema():
    schema = infrastructure_create_schema()
    _make_update_schema(schema)
    return schema


def infrastructure_show_schema():
    schema = infrastructure_create_schema()
    _make_show_schema(schema)
    return schema


def metadata_schema_create_schema():
    schema = {
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.metadata_schema_does_not_exist],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'schema_name': [not_empty, unicode],
        'schema_version': [not_empty, unicode],
        'schema_xsd': [ignore_missing, unicode, v.xsd_validator],
        'base_schema_id': [ignore_missing, unicode, v.metadata_schema_exists],
        'state': [ignore_missing],

        # post-validation
        '__after': [v.unique_metadata_schema_name_and_version, ignore],
    }
    _make_create_schema(schema)
    return schema


def metadata_schema_update_schema():
    schema = metadata_schema_create_schema()
    schema['base_schema_id'].append(v.no_loops_in_metadata_schema_hierarchy)
    schema['__after'].insert(0, v.both_metadata_schema_name_and_version)
    _make_update_schema(schema)
    return schema


def metadata_schema_show_schema():
    schema = metadata_schema_create_schema()
    _make_show_schema(schema)
    return schema


def metadata_model_create_schema():
    schema = {
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.metadata_model_does_not_exist],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'metadata_schema_id': [not_empty, unicode, v.metadata_schema_exists],
        'organization_id': [ignore_missing, unicode, v.organization_exists],
        'infrastructure_id': [ignore_missing, unicode, v.infrastructure_exists],
        'model_json': [ignore_missing, unicode, v.json_dict_validator],
        'state': [ignore_missing],

        # post-validation
        '__after': [v.metadata_model_check_organization_infrastructure,
                    v.metadata_model_unique_schema_organization_infrastructure,
                    ignore],
    }
    _make_create_schema(schema)
    return schema


def metadata_model_update_schema():
    schema = metadata_model_create_schema()
    _make_update_schema(schema)
    return schema


def metadata_model_show_schema():
    schema = metadata_model_create_schema()
    _make_show_schema(schema)
    return schema
