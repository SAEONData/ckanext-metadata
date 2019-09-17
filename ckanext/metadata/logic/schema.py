# encoding: utf-8

import ckan.plugins.toolkit as tk

from ckanext.metadata.logic import validators as v

# shortcuts to toolkit validators / converters
empty = tk.get_validator('empty')
ignore = tk.get_validator('ignore')
ignore_missing = tk.get_validator('ignore_missing')
default = tk.get_validator('default')
name_validator = tk.get_validator('name_validator')
package_name_validator = tk.get_validator('package_name_validator')
package_version_validator = tk.get_validator('package_version_validator')
email_validator = tk.get_validator('email_validator')
group_name_validator = tk.get_validator('group_name_validator')
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
        if v.not_empty in schema['name']:
            schema['name'].remove(v.not_empty)
        schema['name'].insert(0, ignore_missing)


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
        # native package fields with special usage
        'id': [ignore],
        'owner_org': [v.not_empty, v.object_exists('organization'), owner_org_validator, unicode],
        'state': [ignore_not_package_admin, ignore_missing],
        'type': [],
        'private': [],

        # extension-specific fields
        'metadata_collection_id': [v.not_empty, unicode, v.object_exists('metadata_collection'), convert_to_extras],
        'infrastructures': {
            'id': [v.not_empty, unicode, v.object_exists('infrastructure')],
        },
        'metadata_standard_id': [v.not_empty, unicode, v.object_exists('metadata_standard'), convert_to_extras],
        'metadata_json': [v.not_empty, unicode, v.json_dict_validator, convert_to_extras],
        'validated': [convert_to_extras],
        'errors': [convert_to_extras],
        'workflow_state_id': [convert_to_extras],

        # post-validation
        '__after': [v.metadata_record_id_name_generator,
                    v.owner_org_owns_metadata_collection,
                    ignore],
    }

    # optional native package fields
    schema.update(metadata_record_attr_mappable_schema())

    _make_create_schema(schema)
    return schema


def metadata_record_attr_mappable_schema():
    """
    Defines the metadata record (package) fields that may be referenced by MetadataJSONAttrMap.record_attr.
    These fields may optionally be provided as input to the metadata_record_create|update actions; but
    if they are defined in a mapping, the mapping will override any input values with the corresponding
    values in the metadata JSON.
    """
    schema = {
        'name': [ignore_missing, unicode, package_name_validator],
        'title': [ignore_missing, unicode],
        'author': [ignore_missing, unicode],
        'author_email': [ignore_missing, unicode, email_validator],
        'maintainer': [ignore_missing, unicode],
        'maintainer_email': [ignore_missing, unicode, email_validator],
        'license_id': [ignore_missing, unicode],
        'notes': [ignore_missing, unicode],
        'url': [ignore_missing, unicode, v.url_validator],
        'version': [ignore_missing, unicode, package_version_validator],
    }
    return schema


def metadata_record_update_schema():
    schema = metadata_record_create_schema()
    _make_update_schema(schema)
    schema['__after'] = [v.owner_org_owns_metadata_collection, ignore]
    return schema


def metadata_record_show_schema(deserialize_json=False):
    schema = metadata_record_create_schema()
    _make_show_schema(schema)
    schema.update({
        'owner_org': [v.convert_id_to_name('organization')],
        'metadata_standard_id': [convert_from_extras, v.convert_id_to_name('metadata_standard')],
        'metadata_json': [convert_from_extras, v.format_json(deserialize_json)],
        'metadata_collection_id': [convert_from_extras, v.convert_id_to_name('metadata_collection')],
        'infrastructures': {
            'id': [v.convert_id_to_name('infrastructure')],
            '__extras': [ignore],
        },
        'validated': [convert_from_extras, boolean_validator],
        'errors': [convert_from_extras, v.format_json(deserialize_json)],
        'workflow_state_id': [convert_from_extras, default(None), v.convert_id_to_name('workflow_state')],
        'private': [],
        'extras': _extras_schema(),
        'display_name': [],
    })
    return schema


def metadata_validity_check_schema():
    schema = {
        'metadata_json': [v.not_empty, unicode, v.json_dict_validator],
        'schema_json': [v.not_empty, unicode, v.json_schema_validator],
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
        'id': [v.not_empty, unicode, v.object_exists('metadata_record')],
        'key': [v.not_empty, unicode, name_validator, v.schema_key_validator(metadata_record_show_schema(), False)],
        'value': [v.not_empty, unicode, v.json_object_validator],
    }
    _make_create_schema(schema)
    return schema


def metadata_record_workflow_annotation_update_schema():
    schema = metadata_record_workflow_annotation_create_schema()
    _make_update_schema(schema)
    return schema


def metadata_record_workflow_annotation_show_schema(deserialize_json=False):
    """
    Translates from the default JSONPatch output schema.
    """
    schema = {
        '__before': [v.copy('id', 'jsonpatch_id'), ignore],
        'id': [v.copy_from('object_id')],
        'key': [v.copy_from('operation'), v.extract_item('path'), v.extract_re_group(r'/(\w+)')],
        'value': [v.copy_from('operation'), v.extract_item('value'), v.format_json(deserialize_json)],
        'object_id': [],
        'operation': [],
    }
    return schema


def metadata_collection_create_schema():
    schema = {
        # from the default group schema
        'id': [ignore],
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
        'doi_collection': [v.not_missing, unicode, v.doi_collection_validator, convert_to_extras],
        'auto_create_doi': [v.not_missing, boolean_validator, convert_to_extras],
    }
    _make_create_schema(schema)
    return schema


def metadata_collection_update_schema():
    schema = metadata_collection_create_schema()
    schema['organization_id'] = [v.not_empty, unicode, v.metadata_collection_org_unchanged, convert_to_extras]
    _make_update_schema(schema)
    return schema


def metadata_collection_show_schema():
    schema = metadata_collection_create_schema()
    _make_show_schema(schema)
    schema.update({
        'organization_id': [convert_from_extras, v.convert_id_to_name('organization')],
        'extras': _extras_schema(),
        'num_followers': [],
        'package_count': [],
        'display_name': [],
    })
    return schema


def infrastructure_create_schema():
    schema = {
        # from the default group schema
        'id': [ignore],
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
    schema.update({
        'num_followers': [],
        'package_count': [],
        'display_name': [],
    })
    return schema


def metadata_standard_create_schema():
    schema = {
        'id': [ignore],
        'name': [ignore_missing, unicode, name_validator, v.object_name_validator('metadata_standard')],
        'description': [ignore_missing, unicode],
        'standard_name': [v.not_empty, unicode],
        'standard_version': [v.not_missing, unicode],
        'parent_standard_id': [v.not_missing, unicode, v.object_exists('metadata_standard')],
        'metadata_template_json': [v.not_missing, unicode, v.json_dict_validator],
        'state': [ignore_not_sysadmin, ignore_missing],

        # post-validation
        '__after': [v.metadata_standard_name_generator,
                    v.unique_metadata_standard_name_and_version,
                    ignore],
    }
    _make_create_schema(schema)
    return schema


def metadata_standard_update_schema():
    schema = metadata_standard_create_schema()
    schema['parent_standard_id'].append(v.no_loops_in_metadata_standard_hierarchy)
    _make_update_schema(schema)
    return schema


def metadata_standard_show_schema(deserialize_json=False):
    schema = metadata_standard_create_schema()
    _make_show_schema(schema)
    schema.update({
        'parent_standard_id': [v.convert_id_to_name('metadata_standard')],
        'metadata_template_json': [v.format_json(deserialize_json)],
        'display_name': [],
    })
    return schema


def metadata_json_attr_map_create_schema():
    schema = {
        'id': [ignore],
        'json_path': [v.not_empty, unicode, v.json_pointer_validator],
        'record_attr': [v.not_empty, unicode, v.schema_key_validator(metadata_record_attr_mappable_schema(), True)],
        'is_key': [v.not_missing, boolean_validator],
        'metadata_standard_id': [v.not_empty, unicode, v.object_exists('metadata_standard')],

        # post-validation
        '__after': [v.metadata_template_json_path_validator,
                    v.metadata_json_attr_map_unique,
                    ignore],
    }
    _make_create_schema(schema)
    return schema


def metadata_json_attr_map_update_schema():
    schema = metadata_json_attr_map_create_schema()
    schema['metadata_standard_id'] = [empty]  # cannot change the metadata standard to which an attribute map applies
    _make_update_schema(schema)
    return schema


def metadata_json_attr_map_show_schema():
    schema = metadata_json_attr_map_create_schema()
    _make_show_schema(schema)
    schema.update({
        'metadata_standard_id': [v.convert_id_to_name('metadata_standard')],
    })
    return schema


def metadata_json_attr_map_apply_schema():
    schema = {
        'metadata_standard_id': [v.not_empty, unicode, v.object_exists('metadata_standard')],
        'metadata_json': [v.not_empty, unicode, v.json_dict_validator],
    }
    return schema


def metadata_schema_create_schema():
    schema = {
        'id': [ignore],
        'name': [ignore_missing, unicode, name_validator, v.object_name_validator('metadata_schema')],
        'description': [ignore_missing, unicode],
        'metadata_standard_id': [v.not_empty, unicode, v.object_exists('metadata_standard')],
        'organization_id': [v.not_missing, unicode, v.object_exists('organization')],
        'infrastructure_id': [v.not_missing, unicode, v.object_exists('infrastructure')],
        'schema_json': [v.not_empty, unicode, v.json_schema_validator],
        'state': [ignore_not_sysadmin, ignore_missing],

        # post-validation
        '__after': [v.metadata_schema_name_generator,
                    v.metadata_schema_check_organization_infrastructure,
                    v.metadata_schema_unique_standard_organization_infrastructure,
                    ignore],
    }
    _make_create_schema(schema)
    return schema


def metadata_schema_update_schema():
    schema = metadata_schema_create_schema()
    _make_update_schema(schema)
    return schema


def metadata_schema_show_schema(deserialize_json=False):
    schema = metadata_schema_create_schema()
    _make_show_schema(schema)
    schema.update({
        'schema_json': [v.format_json(deserialize_json)],
        'metadata_standard_id': [v.convert_id_to_name('metadata_standard')],
        'organization_id': [v.convert_id_to_name('organization')],
        'infrastructure_id': [v.convert_id_to_name('infrastructure')],
        'display_name': [],
    })
    return schema


def workflow_state_create_schema():
    schema = {
        'id': [ignore],
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


def workflow_state_show_schema(deserialize_json=False):
    schema = workflow_state_create_schema()
    _make_show_schema(schema)
    schema.update({
        'workflow_rules_json': [v.format_json(deserialize_json)],
        'revert_state_id': [v.convert_id_to_name('workflow_state')],
        'display_name': [],
    })
    return schema


def workflow_transition_create_schema():
    schema = {
        'id': [ignore],
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
        'from_state_display_name': [],
        'to_state_display_name': [],
    })
    return schema


def workflow_annotation_create_schema():
    schema = {
        'id': [ignore],
        'name': [v.not_empty, unicode, name_validator, v.object_name_validator('workflow_annotation'), v.schema_key_validator(metadata_record_show_schema(), False)],
        'attributes': [v.not_empty, unicode, v.json_dict_validator, v.workflow_annotation_attributes_validator],
    }
    _make_create_schema(schema)
    return schema


def workflow_annotation_update_schema():
    schema = workflow_annotation_create_schema()
    _make_update_schema(schema)
    return schema


def workflow_annotation_show_schema(deserialize_json=False):
    schema = workflow_annotation_create_schema()
    _make_show_schema(schema)
    schema.update({
        'attributes': [v.format_json(deserialize_json)],
    })
    return schema
