# encoding: utf-8

import ckan.plugins.toolkit as tk

from ckanext.metadata.logic import validators as v

# shortcuts to toolkit validators / converters
empty = tk.get_validator('empty')
ignore = tk.get_validator('ignore')
ignore_missing = tk.get_validator('ignore_missing')
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
        'owner_org': [v.not_empty, v.group_exists('organization'), owner_org_validator, unicode],
        'type': [],

        # extension-specific fields
        'metadata_collection_id': [v.not_empty, unicode, v.group_exists('metadata_collection'), convert_to_extras],
        'infrastructures': {
            'id': [v.not_empty, unicode, v.group_exists('infrastructure')],
        },
        'schema_name': [v.not_empty, unicode],
        'schema_version': [v.not_missing, unicode],
        'content_json': [v.not_missing, unicode, v.json_dict_validator, convert_to_extras],
        'content_raw': [v.not_missing, unicode, convert_to_extras],
        'content_url': [v.not_missing, unicode, convert_to_extras],
        'validation_state': [convert_to_extras],
        'workflow_state_id': [convert_to_extras],

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
        'content_json': [convert_from_extras, v.deserialize_json],
        'content_raw': [convert_from_extras],
        'content_url': [convert_from_extras],
        'metadata_collection_id': [convert_from_extras],
        'validation_state': [convert_from_extras],
        'workflow_state_id': [convert_from_extras],
        'private': [],
        'extras': _extras_schema(),
    })
    del schema['schema_name'], schema['schema_version']
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

        # extension-specific fields
        'organization_id': [v.not_empty, unicode, v.group_exists('organization'), convert_to_extras],
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
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.metadata_schema_does_not_exist],
        'name': [ignore_missing, unicode, name_validator, v.metadata_schema_name_validator],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'schema_name': [v.not_empty, unicode],
        'schema_version': [v.not_missing, unicode],
        'schema_xsd': [v.not_missing, unicode, v.xsd_validator],
        'base_schema_id': [v.not_missing, unicode, v.metadata_schema_exists],
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
    return schema


def metadata_model_create_schema():
    schema = {
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.metadata_model_does_not_exist],
        'name': [ignore_missing, unicode, name_validator, v.metadata_model_name_validator],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'metadata_schema_id': [v.not_empty, unicode, v.metadata_schema_exists],
        'organization_id': [v.not_missing, unicode, v.group_exists('organization')],
        'infrastructure_id': [v.not_missing, unicode, v.group_exists('infrastructure')],
        'model_json': [v.not_missing, unicode, v.json_dict_validator],
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
    schema['model_json'] = [v.deserialize_json]
    return schema


def workflow_state_create_schema():
    schema = {
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.workflow_state_does_not_exist],
        'name': [v.not_empty, unicode, name_validator, v.workflow_state_name_validator],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'revert_state_id': [v.not_missing, unicode, v.workflow_state_exists],
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
    return schema


def workflow_transition_create_schema():
    schema = {
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.workflow_transition_does_not_exist],
        'from_state_id': [v.not_missing, unicode, v.workflow_state_exists],
        'to_state_id': [v.not_empty, unicode, v.workflow_state_exists],
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
    return schema


def workflow_metric_create_schema():
    schema = {
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.workflow_metric_does_not_exist],
        'name': [v.not_empty, unicode, name_validator, v.workflow_metric_name_validator],
        'title': [ignore_missing, unicode],
        'description': [ignore_missing, unicode],
        'evaluator_uri': [v.not_empty, unicode, v.uri_validator],
        'state': [ignore_not_sysadmin, ignore_missing],
    }
    _make_create_schema(schema)
    return schema


def workflow_metric_update_schema():
    schema = workflow_metric_create_schema()
    _make_update_schema(schema)
    return schema


def workflow_metric_show_schema():
    schema = workflow_metric_create_schema()
    _make_show_schema(schema)
    return schema


def workflow_rule_create_schema():
    schema = {
        'id': [empty_if_not_sysadmin, ignore_missing, unicode, v.workflow_rule_does_not_exist],
        'workflow_state_id': [v.not_empty, unicode, v.workflow_state_exists],
        'workflow_metric_id': [v.not_empty, unicode, v.workflow_metric_exists],
        'rule_json': [v.not_empty, unicode, v.json_dict_validator],
        'state': [ignore_not_sysadmin, ignore_missing],

        # post-validation
        '__after': [v.workflow_rule_unique, ignore],
    }
    _make_create_schema(schema)
    return schema


def workflow_rule_update_schema():
    schema = workflow_rule_create_schema()
    # cannot change the associated state or metric
    del schema['workflow_state_id'], schema['workflow_metric_id']
    _make_update_schema(schema)
    return schema


def workflow_rule_show_schema():
    schema = workflow_rule_create_schema()
    _make_show_schema(schema)
    schema['rule_json'] = [v.deserialize_json]
    return schema
