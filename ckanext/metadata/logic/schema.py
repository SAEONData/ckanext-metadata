# encoding: utf-8

import ckan.plugins.toolkit as tk

from ckanext.metadata.logic import validators as v

# shortcuts to toolkit validators / converters
empty = tk.get_validator('empty')
ignore = tk.get_validator('ignore')
ignore_missing = tk.get_validator('ignore_missing')
default = tk.get_validator('default')
package_id_does_not_exist = tk.get_validator('package_id_does_not_exist')
name_validator = tk.get_validator('name_validator')
package_name_validator = tk.get_validator('package_name_validator')
group_name_validator = tk.get_validator('group_name_validator')
empty_if_not_sysadmin = tk.get_validator('empty_if_not_sysadmin')
ignore_not_sysadmin = tk.get_validator('ignore_not_sysadmin')
ignore_not_package_admin = tk.get_validator('ignore_not_package_admin')
ignore_not_group_admin = tk.get_validator('ignore_not_group_admin')
owner_org_validator = tk.get_validator('owner_org_validator')
convert_to_extras = tk.get_validator('convert_to_extras')
convert_from_extras = tk.get_validator('convert_from_extras')
boolean_validator = tk.get_validator('boolean_validator')


def _make_create_schema(schema):
    """
    Add some defaults to a "create" schema.
    """
    schema.update({
        # native CKAN fields that we're not interested in can end up in __extras; ignore them
        '__extras': [ignore],
        # disallow anything else that's not in our schema
        '__junk': [empty],
    })


def _make_update_schema(schema):
    """
    Modify a "create" schema to be suitable for an "update" action.
    """
    schema['id'] = []

    # allow name to be optional for updates
    if 'name' in schema:
        for i, validator in enumerate(schema['name']):
            if validator is v.not_empty:
                schema['name'][i] = ignore_missing


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
        # pre-validation
        '__before': [v.metadata_record_infrastructures_not_missing,
                     ignore],

        # from the default package schema
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, package_id_does_not_exist],
        'name': [ignore_missing, unicode, name_validator, package_name_validator],
        'title': [ignore_missing, unicode],
        'state': [ignore_not_package_admin, ignore_missing],
        'owner_org': [v.not_empty, v.object_exists('organization'), owner_org_validator, unicode],
        'type': [],
        'private': [],

        # extension-specific fields
        'metadata_collection_id': [v.not_empty, unicode, v.object_exists('metadata_collection'), convert_to_extras],
        'infrastructures': {
            'id': [v.not_empty, unicode, v.object_exists('infrastructure')],
        },
        'metadata_schema_id': [v.not_empty, unicode, v.object_exists('metadata_schema'), convert_to_extras],
        'metadata_json': [v.not_missing, unicode, v.json_dict_validator, convert_to_extras],
        'metadata_raw': [v.not_missing, unicode, convert_to_extras],
        'metadata_url': [v.not_missing, unicode, v.url_validator, convert_to_extras],
        'validated': [convert_to_extras],
        'errors': [convert_to_extras],
        'workflow_state_id': [convert_to_extras],

        # post-validation
        '__after': [v.metadata_record_id_name_generator,
                    v.owner_org_owns_metadata_collection,
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
        'owner_org': [v.convert_id_to_name('organization')],
        'metadata_schema_id': [convert_from_extras, v.convert_id_to_name('metadata_schema')],
        'metadata_json': [convert_from_extras, v.deserialize_json],
        'metadata_raw': [convert_from_extras],
        'metadata_url': [convert_from_extras],
        'metadata_collection_id': [convert_from_extras, v.convert_id_to_name('metadata_collection')],
        'infrastructures': {
            'id': [v.convert_id_to_name('infrastructure')],
            '__extras': [ignore],
        },
        'validated': [convert_from_extras, boolean_validator],
        'errors': [convert_from_extras, v.deserialize_json],
        'workflow_state_id': [convert_from_extras, default(None), v.convert_id_to_name('workflow_state')],
        'private': [],
        'extras': _extras_schema(),
    })
    return schema


def metadata_validity_check_schema():
    schema = {
        'metadata_json': [v.not_empty, unicode, v.json_dict_validator],
        'model_json': [v.not_empty, unicode, v.json_schema_validator],
    }
    return schema


def metadata_record_workflow_rules_check_schema():
    schema = {
        'metadata_record_json': [v.not_empty, unicode, v.json_dict_validator],
        'workflow_rules_json': [v.not_empty, unicode, v.json_schema_validator],
    }
    return schema


def metadata_record_workflow_annotation_create_schema():
    schema = {
        'id': [],
        'path': [v.not_empty, unicode, v.json_pointer_validator, v.augmented_schema_validator(metadata_record_show_schema())],
        'value': [v.not_empty, unicode, v.json_object_validator],
    }
    return schema


def metadata_collection_create_schema():
    schema = {
        # from the default group schema
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.group_does_not_exist],
        'name': [v.not_empty, unicode, name_validator, group_name_validator],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'state': [ignore_not_group_admin, ignore_missing],
        'type': [],
        'is_organization': [],
        'users': {
            "name": [v.not_empty, unicode],
            "capacity": [ignore_missing],
            "__extras": [ignore]
        },

        # extension-specific fields
        'organization_id': [v.not_empty, unicode, v.object_exists('organization'), convert_to_extras],
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
        'organization_id': [convert_from_extras, v.convert_id_to_name('organization')],
        'extras': _extras_schema(),
    })
    return schema


def infrastructure_create_schema():
    schema = {
        # from the default group schema
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.group_does_not_exist],
        'name': [v.not_empty, unicode, name_validator, group_name_validator],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'state': [ignore_not_group_admin, ignore_missing],
        'type': [],
        'is_organization': [],
        'users': {
            "name": [v.not_empty, unicode],
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
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.object_does_not_exist('metadata_schema')],
        'name': [ignore_missing, unicode, name_validator, v.object_name_validator('metadata_schema')],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'schema_name': [v.not_empty, unicode],
        'schema_version': [v.not_missing, unicode],
        'schema_xsd': [v.not_missing, unicode, v.xsd_validator],
        'base_schema_id': [v.not_missing, unicode, v.object_exists('metadata_schema')],
        'state': [ignore_not_sysadmin, ignore_missing],

        # post-validation
        '__after': [v.metadata_schema_name_generator,
                    v.unique_metadata_schema_name_and_version,
                    ignore],
    }
    _make_create_schema(schema)
    return schema


def metadata_schema_update_schema():
    schema = metadata_schema_create_schema()
    schema['base_schema_id'].append(v.no_loops_in_metadata_schema_hierarchy)
    _make_update_schema(schema)
    return schema


def metadata_schema_show_schema():
    schema = metadata_schema_create_schema()
    _make_show_schema(schema)
    schema.update({
        'base_schema_id': [v.convert_id_to_name('metadata_schema')],
    })
    return schema


def metadata_model_create_schema():
    schema = {
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.object_does_not_exist('metadata_model')],
        'name': [ignore_missing, unicode, name_validator, v.object_name_validator('metadata_model')],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'metadata_schema_id': [v.not_empty, unicode, v.object_exists('metadata_schema')],
        'organization_id': [v.not_missing, unicode, v.object_exists('organization')],
        'infrastructure_id': [v.not_missing, unicode, v.object_exists('infrastructure')],
        'model_json': [v.not_empty, unicode, v.json_schema_validator],
        'state': [ignore_not_sysadmin, ignore_missing],

        # post-validation
        '__after': [v.metadata_model_name_generator,
                    v.metadata_model_check_organization_infrastructure,
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
    schema.update({
        'model_json': [v.deserialize_json],
        'metadata_schema_id': [v.convert_id_to_name('metadata_schema')],
        'organization_id': [v.convert_id_to_name('organization')],
        'infrastructure_id': [v.convert_id_to_name('infrastructure')],
    })
    return schema


def workflow_state_create_schema():
    schema = {
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.object_does_not_exist('workflow_state')],
        'name': [v.not_empty, unicode, name_validator, v.object_name_validator('workflow_state')],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'workflow_rules_json': [v.not_empty, unicode, v.json_schema_validator],
        'metadata_records_private': [v.not_missing, boolean_validator],
        'revert_state_id': [v.not_missing, unicode, v.object_exists('workflow_state')],
        'state': [ignore_not_sysadmin, ignore_missing],
    }
    _make_create_schema(schema)
    return schema


def workflow_state_update_schema():
    schema = workflow_state_create_schema()
    schema['revert_state_id'].append(v.workflow_revert_state_validator)
    _make_update_schema(schema)
    return schema


def workflow_state_show_schema():
    schema = workflow_state_create_schema()
    _make_show_schema(schema)
    schema.update({
        'workflow_rules_json': [v.deserialize_json],
        'revert_state_id': [v.convert_id_to_name('workflow_state')],
    })
    return schema


def workflow_transition_create_schema():
    schema = {
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.object_does_not_exist('workflow_transition')],
        'from_state_id': [v.not_missing, unicode, v.object_exists('workflow_state')],
        'to_state_id': [v.not_empty, unicode, v.object_exists('workflow_state')],
        'state': [ignore_not_sysadmin, ignore_missing],

        # post-validation
        '__after': [v.workflow_transition_check,
                    v.workflow_transition_unique,
                    v.workflow_transition_graph_validator,
                    ignore],
    }
    _make_create_schema(schema)
    return schema


def workflow_transition_show_schema():
    schema = workflow_transition_create_schema()
    _make_show_schema(schema)
    schema.update({
        'from_state_id': [v.convert_id_to_name('workflow_state')],
        'to_state_id': [v.convert_id_to_name('workflow_state')],
    })
    return schema
