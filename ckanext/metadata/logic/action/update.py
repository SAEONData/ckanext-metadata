# encoding: utf-8

import logging
import json
import random
import re
from paste.deploy.converters import asbool, falsy
from sqlalchemy import func
from sqlalchemy.orm import aliased
import jsonpointer

import ckan.plugins.toolkit as tk
from ckan.common import _, config
from ckanext.metadata.logic import schema
from ckanext.metadata.common import (
    METADATA_VALIDATION_ACTIVITY_TYPE,
    METADATA_WORKFLOW_ACTIVITY_TYPE,
    DOI_PREFIX_RE,
)
from ckanext.metadata.lib.dictization import model_save
import ckanext.metadata.model as ckanext_model
from ckanext.metadata.logic.metadata_validator import MetadataValidator
from ckanext.metadata.logic.workflow_validator import WorkflowValidator
from ckanext.metadata.lib.bulk_process import bulk_action

log = logging.getLogger(__name__)


# NB: We allow partial updates unconditionally because this is consistent with how
# updating of "native" fields is handled in CKAN: fields are left at their current
# values when parameters are missing from the input (where permitted by ignore_missing
# in the schema). On the contrary, not allowing partial updates can result in data
# (extras, members, etc) being deleted if "list" type params are missing from the input,
# and correct use of the 'allow_partial_update' option would require the caller to
# understand the inner workings of the system.

# The extras saving mechanism is flawed. If a schema defines two "extra" fields, say
# field1 and field2, then these would be left unchanged if neither is supplied by the
# caller on update (assuming we're allowing partial updates). However, if only field1
# is supplied, then field2 ends up being deleted because all extras are lumped together
# in the same list. Again, this requires the caller to understand the inner workings
# of the system - in particular, to know that field1 and field2 are "extra" rather
# than "native". The only way to avoid this problem is to ensure that "extra" fields
# are validated as not_missing in the schema.

# Fields indicated as "optional" in the docstrings remain at their current values if
# not supplied by the caller.

def metadata_standard_update(context, data_dict):
    """
    Update a metadata standard.

    You must be authorized to edit the metadata standard.

    It is recommended to call
    :py:func:`ckan.logic.action.get.metadata_standard_show`, make the desired changes to
    the result, and then call ``metadata_standard_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.metadata_standard_create`.

    :param id: the id or name of the metadata standard to update
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :returns: the updated metadata standard (unless 'return_id_only' is set to True
              in the context, in which case just the metadata standard id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata standard: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    metadata_standard_id = tk.get_or_bust(data_dict, 'id')
    metadata_standard = ckanext_model.MetadataStandard.get(metadata_standard_id)
    if metadata_standard is not None:
        metadata_standard_id = metadata_standard.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Standard')))

    tk.check_access('metadata_standard_update', context, data_dict)

    data_dict.update({
        'id': metadata_standard_id,
    })
    context.update({
        'metadata_standard': metadata_standard,
        'allow_partial_update': True,
    })

    data, errors = tk.navl_validate(data_dict, schema.metadata_standard_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_standard = model_save.metadata_standard_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update metadata standard %s') % metadata_standard_id

    if not defer_commit:
        model.repo.commit()

    output = metadata_standard_id if return_id_only \
        else tk.get_action('metadata_standard_show')(context, {'id': metadata_standard_id, 'deserialize_json': deserialize_json})
    return output


def metadata_schema_update(context, data_dict):
    """
    Update a metadata schema.

    You must be authorized to edit the metadata schema.

    Changes to the schema_json will cause dependent metadata records to be invalidated.
    If any of metadata_standard_id, organization_id or infrastructure_id change, then
    ex-dependent and newly-dependent metadata records will also be invalidated.

    It is recommended to call
    :py:func:`ckan.logic.action.get.metadata_schema_show`, make the desired changes to
    the result, and then call ``metadata_schema_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.metadata_schema_create`.

    :param id: the id or name of the metadata schema to update
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :returns: the updated metadata schema (unless 'return_id_only' is set to True
              in the context, in which case just the metadata schema id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata schema: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    metadata_schema_id = tk.get_or_bust(data_dict, 'id')
    metadata_schema = ckanext_model.MetadataSchema.get(metadata_schema_id)
    if metadata_schema is not None:
        metadata_schema_id = metadata_schema.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Schema')))

    tk.check_access('metadata_schema_update', context, data_dict)

    dependent_record_list_context = context.copy()
    dependent_record_list_context['ignore_auth'] = True

    old_schema_json = metadata_schema.schema_json
    if old_schema_json:
        old_schema_json = json.loads(old_schema_json)
    old_dependent_record_list = tk.get_action('metadata_schema_dependent_record_list')(dependent_record_list_context, {'id': metadata_schema_id})

    data_dict.update({
        'id': metadata_schema_id,
    })
    context.update({
        'metadata_schema': metadata_schema,
        'allow_partial_update': True,
    })

    data, errors = tk.navl_validate(data_dict, schema.metadata_schema_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_schema = model_save.metadata_schema_dict_save(data, context)
    new_schema_json = metadata_schema.schema_json
    if new_schema_json:
        new_schema_json = json.loads(new_schema_json)
    new_dependent_record_list = tk.get_action('metadata_schema_dependent_record_list')(dependent_record_list_context, {'id': metadata_schema_id})

    if old_schema_json != new_schema_json:
        affected_record_ids = set(old_dependent_record_list) | set(new_dependent_record_list)
    else:
        affected_record_ids = set(old_dependent_record_list) ^ set(new_dependent_record_list)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update metadata schema %s') % metadata_schema_id

    invalidate_context = context.copy()
    invalidate_context.update({
        'defer_commit': True,
        'ignore_auth': True,
        'trigger_action': 'metadata_schema_update',
        'trigger_object_id': metadata_schema_id,
    })
    for metadata_record_id in affected_record_ids:
        tk.get_action('metadata_record_invalidate')(invalidate_context, {'id': metadata_record_id})

    if not defer_commit:
        model.repo.commit()

    output = metadata_schema_id if return_id_only \
        else tk.get_action('metadata_schema_show')(context, {'id': metadata_schema_id, 'deserialize_json': deserialize_json})
    return output


def infrastructure_update(context, data_dict):
    """
    Update an infrastructure.

    You must be authorized to edit the infrastructure.

    It is recommended to call
    :py:func:`ckan.logic.action.get.infrastructure_show`, make the desired changes to
    the result, and then call ``infrastructure_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.infrastructure_create`.

    :param id: the id or name of the infrastructure to update
    :type id: string
    :param name: the name of the infrastructure (optional)
    :type name: string

    :returns: the updated infrastructure (unless 'return_id_only' is set to True
              in the context, in which case just the infrastructure id will be returned)
    :rtype: dictionary
    """
    log.info("Updating infrastructure: %r", data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    infrastructure_id = tk.get_or_bust(data_dict, 'id')
    infrastructure = model.Group.get(infrastructure_id)
    if infrastructure is not None and infrastructure.type == 'infrastructure':
        infrastructure_id = infrastructure.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Project')))

    tk.check_access('infrastructure_update', context, data_dict)

    data_dict.update({
        'id': infrastructure_id,
        'type': 'infrastructure',
        'is_organization': False,
    })
    internal_context = context.copy()
    internal_context.update({
        'schema': schema.infrastructure_update_schema(),
        'invoked_action': 'infrastructure_update',
        'defer_commit': True,
        'allow_partial_update': True,
        'ignore_auth': True,
    })

    infrastructure_dict = tk.get_action('group_update')(internal_context, data_dict)

    if not defer_commit:
        model.repo.commit()

    output = infrastructure_id if return_id_only \
        else tk.get_action('infrastructure_show')(internal_context, {'id': infrastructure_id})
    return output


def metadata_collection_update(context, data_dict):
    """
    Update a metadata collection.

    You must be authorized to edit the metadata collection.

    It is recommended to call
    :py:func:`ckan.logic.action.get.metadata_collection_show`, make the desired changes to
    the result, and then call ``metadata_collection_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.metadata_collection_create`.

    :param id: the id or name of the metadata collection to update
    :type id: string
    :param name: the name of the metadata collection (optional)
    :type name: string

    :returns: the updated metadata collection (unless 'return_id_only' is set to True
              in the context, in which case just the collection id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata collection: %r", data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    metadata_collection_id = tk.get_or_bust(data_dict, 'id')
    metadata_collection = model.Group.get(metadata_collection_id)
    if metadata_collection is not None and metadata_collection.type == 'metadata_collection':
        metadata_collection_id = metadata_collection.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))

    tk.check_access('metadata_collection_update', context, data_dict)

    data_dict.update({
        'id': metadata_collection_id,
        'type': 'metadata_collection',
        'is_organization': False,
    })
    internal_context = context.copy()
    internal_context.update({
        'schema': schema.metadata_collection_update_schema(),
        'invoked_action': 'metadata_collection_update',
        'defer_commit': True,
        'allow_partial_update': True,
        'ignore_auth': True,
    })

    tk.get_action('group_update')(internal_context, data_dict)
    model_save.metadata_collection_organization_membership_save(metadata_collection.extras['organization_id'], internal_context)
    model_save.metadata_collection_infrastructure_list_save(data_dict.get('infrastructures'), internal_context)

    if not defer_commit:
        model.repo.commit()

    output = metadata_collection_id if return_id_only \
        else tk.get_action('metadata_collection_show')(internal_context, {'id': metadata_collection_id})
    return output


def metadata_record_update(context, data_dict):
    """
    Update a metadata record.

    You must be authorized to edit the metadata record.

    It is recommended to call
    :py:func:`ckan.logic.action.get.metadata_record_show`, make the desired changes to
    the result, and then call ``metadata_record_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.metadata_record_create`.

    :param id: the id or name of the metadata record to update
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :returns: the updated metadata record (unless 'return_id_only' is set to True
              in the context, in which case just the record id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata record: %r", data_dict)
    tk.check_access('metadata_record_update', context, data_dict)

    model = context['model']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    internal_context = context.copy()
    internal_context['ignore_auth'] = True

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    # this is (mostly) duplicating the schema validation that will be done in package_update below,
    # but we want to validate before processing DOI/SID and attribute mappings
    data, errors = tk.navl_validate(data_dict, schema.metadata_record_update_schema(), internal_context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    doi = data_dict.get('doi')
    sid = data_dict.get('sid')
    if not doi and not sid:
        raise tk.ValidationError({"doi,sid": ["DOI and/or SID must be given"]})

    # check that the DOI, if supplied, does not belong to another record
    if doi:
        existing_doi_rec = session.query(model.Package). \
            join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id). \
            filter(model.PackageExtra.key == 'doi'). \
            filter(func.lower(model.PackageExtra.value) == doi.lower()). \
            first()
        if existing_doi_rec and existing_doi_rec.id != metadata_record_id:
            raise tk.ValidationError({"doi": ["The DOI is associated with another metadata record"]})

    # check that the SID, if supplied, does not belong to another record
    if sid:
        existing_sid_rec = session.query(model.Package). \
            join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id). \
            filter(model.PackageExtra.key == 'sid'). \
            filter(func.lower(model.PackageExtra.value) == sid.lower()). \
            first()
        if existing_sid_rec and existing_sid_rec.id != metadata_record_id:
            raise tk.ValidationError({"sid": ["The SID is associated with another metadata record"]})

    # if the record already has a DOI, make sure it is not being changed or un-set
    existing_doi = metadata_record.extras['doi']
    if existing_doi and existing_doi.lower() != doi.lower():
        raise tk.ValidationError({"doi": ["A metadata record's DOI, once set, cannot be changed or removed"]})

    # check for discrepancy between parameterized DOI and metadata DOI
    metadata_dict = json.loads(data_dict['metadata_json'])
    try:
        metadata_doi = metadata_dict['doi']
        if not isinstance(metadata_doi, basestring) or metadata_doi.lower() != doi.lower():
            raise tk.ValidationError({"metadata_json": ["The DOI in the metadata JSON does not match the given DOI"]})
    except KeyError:
        pass

    # inject DOI into the metadata
    if doi:
        metadata_dict['doi'] = doi
        data_dict['metadata_json'] = json.dumps(metadata_dict, ensure_ascii=False)

    # map values from the metadata JSON into the data_dict
    attr_map = tk.get_action('metadata_json_attr_map_apply')(internal_context, {
        'metadata_standard_id': data_dict.get('metadata_standard_id'),
        'metadata_json': data_dict.get('metadata_json'),
    })
    data_dict.update(attr_map['data_dict'])

    data_dict.update({
        'id': metadata_record_id,
        'type': 'metadata_record',
        'validated': asbool(metadata_record.extras['validated']),
        'errors': metadata_record.extras['errors'],
        'workflow_state_id': metadata_record.extras['workflow_state_id'],
        'private': metadata_record.private,
    })
    internal_context.update({
        'metadata_record': metadata_record,
        'schema': schema.metadata_record_update_schema(),
        'invoked_action': 'metadata_record_update',
        'defer_commit': True,
        'return_id_only': True,
        'allow_partial_update': True,
        'message': _(u'REST API: Update metadata record %s') % metadata_record_id
    })

    # if it's a validated record, get some current state info for checking whether we need to invalidate it
    if asbool(metadata_record.extras['validated']):
        old_metadata_json = metadata_record.extras['metadata_json']
        if old_metadata_json:
            old_metadata_json = json.loads(old_metadata_json)
        old_validation_schemas = set(tk.get_action('metadata_record_validation_schema_list')(internal_context, {'id': metadata_record_id}))

    tk.get_action('package_update')(internal_context, data_dict)
    model_save.metadata_record_collection_membership_save(data_dict['metadata_collection_id'], internal_context)

    # check if we need to invalidate the record
    if asbool(metadata_record.extras['validated']):
        # ensure new validation schema list sees infrastructure list changes (infrastructures are now on the collection but there's no harm in leaving this here)
        session.flush()

        new_metadata_json = metadata_record.extras['metadata_json']
        if new_metadata_json:
            new_metadata_json = json.loads(new_metadata_json)
        new_validation_schemas = set(tk.get_action('metadata_record_validation_schema_list')(internal_context, {'id': metadata_record_id}))

        # if either the metadata record content or the set of validation schemas for the record has changed,
        # then the record must be invalidated
        if old_metadata_json != new_metadata_json or old_validation_schemas != new_validation_schemas:
            invalidate_context = context.copy()
            invalidate_context.update({
                'defer_commit': True,
                'ignore_auth': True,
                'trigger_action': 'metadata_record_update',
                'trigger_object_id': metadata_record_id,
            })
            tk.get_action('metadata_record_invalidate')(invalidate_context, {'id': metadata_record_id})

    if not defer_commit:
        model.repo.commit()

    if not metadata_record.private:
        tk.get_action('metadata_record_index_update')(internal_context, {'id': metadata_record_id})

    output = metadata_record_id if return_id_only \
        else tk.get_action('metadata_record_show')(internal_context, {'id': metadata_record_id, 'deserialize_json': deserialize_json})
    return output


def metadata_record_invalidate(context, data_dict):
    """
    Mark a metadata record as not validated, and log the change to
    the metadata record's activity stream.

    You must be authorized to invalidate the metadata record.

    Note: this function is typically called from within another action function
    whose effect triggers invalidation of the given metadata record. In such a
    case, the calling function should pass the following items in the context:
    'trigger_action': the calling function name, e.g. 'metadata_schema_update'
    'trigger_object_id': the id of the object (e.g. a MetadataSchema) being modified

    :param id: the id or name of the metadata record to invalidate
    :type id: string

    :returns: the validation activity record, unless the metadata record is already in a not
        validated state, in which case nothing is changed and None is returned
    :rtype: dictionary
    """
    log.info("Invalidating metadata record: %r", data_dict)

    model = context['model']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    tk.check_access('metadata_record_invalidate', context, data_dict)

    # already not validated
    if not asbool(metadata_record.extras['validated']):
        return

    metadata_record.extras['validated'] = False
    metadata_record.extras['errors'] = '{}'

    trigger_action = context.get('trigger_action')
    trigger_object_id = context.get('trigger_object_id')

    activity_context = context.copy()
    activity_context.update({
        'defer_commit': True,
        'ignore_auth': True,
        'schema': {
            'user_id': [unicode, tk.get_validator('convert_user_name_or_id_to_id')],
            'object_id': [],
            'revision_id': [],
            'activity_type': [],
            'data': [],
        },
    })
    activity_dict = {
        'user_id': user,
        'object_id': metadata_record_id,
        'activity_type': METADATA_VALIDATION_ACTIVITY_TYPE,
        'data': {
            'action': 'metadata_record_invalidate',
            'trigger_action': trigger_action,
            'trigger_object_id': trigger_object_id,
        }
    }

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Invalidate metadata record %s') % metadata_record_id

    activity_dict = tk.get_action('activity_create')(activity_context, activity_dict)

    if not defer_commit:
        model.repo.commit()

    return activity_dict


def metadata_record_validate(context, data_dict):
    """
    Validate a metadata record (if not already validated), and log the result to
    the metadata record's activity stream.

    You must be authorized to validate the metadata record.

    :param id: the id or name of the metadata record to validate
    :type id: string

    :returns: the validation activity record
    :rtype: dictionary
    """
    log.info("Validating metadata record: %r", data_dict)
    tk.check_access('metadata_record_validate', context, data_dict)

    model = context['model']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    internal_context = context.copy()
    internal_context.update({
        'metadata_record': metadata_record,
        'ignore_auth': True,
    })

    # already validated - return the last validation result
    if asbool(metadata_record.extras['validated']):
        return tk.get_action('metadata_record_validation_activity_show')(internal_context, {
            'id': metadata_record_id,
        })

    validation_schemas = tk.get_action('metadata_record_validation_schema_list')(internal_context, {
        'id': metadata_record_id,
        'all_fields': True,
    })
    if not validation_schemas:
        raise tk.ObjectNotFound(_('Could not find any metadata schemas for validating this metadata record'))

    validation_results = []
    accumulated_errors = {}
    metadata_dict = json.loads(metadata_record.extras['metadata_json'])

    for metadata_schema in validation_schemas:
        validate_context = context.copy()
        validate_context.update({
            'allow_side_effects': True,
            'ignore_auth': True,
        })
        schema_dict = json.loads(metadata_schema['schema_json'])
        json_validator = MetadataValidator(schema_dict, metadata_record_id, validate_context)

        # validate the metadata
        validation_errors = json_validator.validate(metadata_dict)

        # if validation modified the metadata, we update the local dict and the stored JSON,
        # regardless of whether or not validation passed
        if metadata_dict != json_validator.jsonschema_validator.root_instance:
            metadata_dict = json_validator.jsonschema_validator.root_instance.copy()
            metadata_record.extras['metadata_json'] = json.dumps(metadata_dict, ensure_ascii=False)

        validation_result = {
            'metadata_schema_id': metadata_schema['id'],
            'errors': validation_errors,
        }
        validation_results += [validation_result]
        accumulated_errors.update(validation_errors)

    metadata_record.extras['validated'] = True
    metadata_record.extras['errors'] = json.dumps(accumulated_errors, ensure_ascii=False)

    activity_context = context.copy()
    activity_context.update({
        'defer_commit': True,
        'ignore_auth': True,
        'schema': {
            'user_id': [unicode, tk.get_validator('convert_user_name_or_id_to_id')],
            'object_id': [],
            'revision_id': [],
            'activity_type': [],
            'data': [],
        },
    })
    activity_dict = {
        'user_id': model.User.by_name(user.decode('utf8')).id,
        'object_id': metadata_record_id,
        'activity_type': METADATA_VALIDATION_ACTIVITY_TYPE,
        'data': {
            'action': 'metadata_record_validate',
            'results': validation_results,
        }
    }

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in internal_context:
        rev.message = internal_context['message']
    else:
        rev.message = _(u'REST API: Validate metadata record %s') % metadata_record_id

    activity_dict = tk.get_action('activity_create')(activity_context, activity_dict)

    if not defer_commit:
        model.repo.commit()

    return activity_dict


def metadata_record_workflow_state_override(context, data_dict):
    """
    Override a metadata record's workflow state, bypassing workflow rule evaluation,
    and log the change to the metadata record's activity stream.

    You must be authorized to override the metadata record's workflow state.
    This should normally only be allowed for sysadmins.

    :param id: the id or name of the metadata record to update
    :type id: string
    :param workflow_state_id: the id or name of the workflow state to assign to the record
    :type workflow_state_id: string

    :returns: the workflow activity record
    :rtype: dictionary
    """
    log.info("Overriding workflow state of metadata record: %r", data_dict)

    model = context['model']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    workflow_state_id = tk.get_or_bust(data_dict, 'workflow_state_id')
    workflow_state = ckanext_model.WorkflowState.get(workflow_state_id)
    if workflow_state is not None:
        workflow_state_id = workflow_state.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('metadata_record_workflow_state_override', context, data_dict)

    update_search_index = metadata_record.private != workflow_state.metadata_records_private
    metadata_record.private = workflow_state.metadata_records_private
    metadata_record.extras['workflow_state_id'] = workflow_state_id

    activity_context = context.copy()
    activity_context.update({
        'defer_commit': True,
        'ignore_auth': True,
        'schema': {
            'user_id': [unicode, tk.get_validator('convert_user_name_or_id_to_id')],
            'object_id': [],
            'revision_id': [],
            'activity_type': [],
            'data': [],
        },
    })
    activity_dict = {
        'user_id': model.User.by_name(user.decode('utf8')).id,
        'object_id': metadata_record_id,
        'activity_type': METADATA_WORKFLOW_ACTIVITY_TYPE,
        'data': {
            'action': 'metadata_record_workflow_state_override',
            'workflow_state_id': workflow_state_id,
        }
    }

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Override workflow state of metadata record %s') % metadata_record_id

    activity_dict = tk.get_action('activity_create')(activity_context, activity_dict)

    if not defer_commit:
        model.repo.commit()

    if update_search_index:
        index_context = context.copy()
        index_context['metadata_record'] = metadata_record
        index_context['ignore_auth'] = True
        tk.get_action('metadata_record_index_update')(index_context, {'id': metadata_record_id})

    return activity_dict


def workflow_state_update(context, data_dict):
    """
    Update a workflow state.

    You must be authorized to edit the workflow state.

    It is recommended to call
    :py:func:`ckan.logic.action.get.workflow_state_show`, make the desired changes to
    the result, and then call ``workflow_state_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.workflow_state_create`.

    :param id: the id or name of the workflow state to update
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :returns: the updated workflow state (unless 'return_id_only' is set to True
              in the context, in which case just the workflow state id will be returned)
    :rtype: dictionary
    """
    log.info("Updating workflow state: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    workflow_state_id = tk.get_or_bust(data_dict, 'id')
    workflow_state = ckanext_model.WorkflowState.get(workflow_state_id)
    if workflow_state is not None:
        workflow_state_id = workflow_state.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    tk.check_access('workflow_state_update', context, data_dict)

    old_metadata_records_private = workflow_state.metadata_records_private

    data_dict.update({
        'id': workflow_state_id,
    })
    context.update({
        'workflow_state': workflow_state,
        'allow_partial_update': True,
    })

    data, errors = tk.navl_validate(data_dict, schema.workflow_state_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_state = model_save.workflow_state_dict_save(data, context)

    if workflow_state.metadata_records_private != old_metadata_records_private:
        # cascade change in 'metadata_records_private' status to metadata records that are in this workflow state
        metadata_records = session.query(model.Package) \
            .join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id) \
            .filter(model.PackageExtra.key == 'workflow_state_id') \
            .filter(model.PackageExtra.value == workflow_state_id) \
            .filter(model.Package.type == 'metadata_record') \
            .filter(model.Package.state != 'deleted') \
            .all()

        for metadata_record in metadata_records:
            metadata_record.private = workflow_state.metadata_records_private
    else:
        metadata_records = []

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update workflow state %s') % workflow_state_id

    if not defer_commit:
        model.repo.commit()

    for metadata_record in metadata_records:
        index_context = context.copy()
        index_context['metadata_record'] = metadata_record
        index_context['ignore_auth'] = True
        tk.get_action('metadata_record_index_update')(index_context, {'id': metadata_record.id})

    output = workflow_state_id if return_id_only \
        else tk.get_action('workflow_state_show')(context, {'id': workflow_state_id, 'deserialize_json': deserialize_json})
    return output


def workflow_transition_update(context, data_dict):
    """
    Update a workflow transition.

    Note: this action will always fail; workflow_transition is an association table which
    does not define any properties of its own; to "update" a transition, delete it and
    create a new one.
    """
    raise tk.ValidationError(_("A workflow transition cannot be updated. Delete it and create a new one instead."))


def workflow_annotation_update(context, data_dict):
    """
    Update a workflow annotation.

    You must be authorized to edit the workflow annotation.

    It is recommended to call
    :py:func:`ckan.logic.action.get.workflow_annotation_show`, make the desired changes to
    the result, and then call ``workflow_annotation_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.workflow_annotation_create`.

    :param id: the id or name of the workflow annotation to update
    :type id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :returns: the updated workflow annotation (unless 'return_id_only' is set to True
              in the context, in which case just the workflow annotation id will be returned)
    :rtype: dictionary
    """
    log.info("Updating workflow annotation: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    workflow_annotation_id = tk.get_or_bust(data_dict, 'id')
    workflow_annotation = ckanext_model.WorkflowAnnotation.get(workflow_annotation_id)
    if workflow_annotation is not None:
        workflow_annotation_id = workflow_annotation.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow Annotation')))

    tk.check_access('workflow_annotation_update', context, data_dict)

    data_dict.update({
        'id': workflow_annotation_id,
    })
    context.update({
        'workflow_annotation': workflow_annotation,
        'allow_partial_update': True,
    })

    data, errors = tk.navl_validate(data_dict, schema.workflow_annotation_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_annotation = model_save.workflow_annotation_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update workflow annotation %s') % workflow_annotation_id

    if not defer_commit:
        model.repo.commit()

    output = workflow_annotation_id if return_id_only \
        else tk.get_action('workflow_annotation_show')(context, {'id': workflow_annotation_id, 'deserialize_json': deserialize_json})
    return output


def metadata_record_workflow_annotation_update(context, data_dict):
    """
    Update a workflow annotation on a metadata record.

    You must be authorized to update annotations on the metadata record.

    This is a wrapper for jsonpatch_update.

    :param id: the id or name of the metadata record
    :type id: string
    :param key: the annotation key to update
    :type key: string
    :param value: the JSON object to set at the specified key
    :type value: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :returns: the updated workflow annotation (which is a facade to the underlying JSONPatch object)
    :rtype: dictionary
    """
    log.info("Updating a workflow annotation on a metadata record: %r", data_dict)
    tk.check_access('metadata_record_workflow_annotation_update', context, data_dict)

    session = context['session']
    data, errors = tk.navl_validate(data_dict, schema.metadata_record_workflow_annotation_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    annotation_list = tk.get_action('metadata_record_workflow_annotation_list')(context, data_dict)
    annotation_list = [annotation for annotation in annotation_list if annotation['key'] == data_dict['key']]

    if not annotation_list:
        raise tk.ObjectNotFound(_('Workflow annotation with the given key not found on metadata record'))
    if len(annotation_list) > 1:
        raise tk.ValidationError(_('Multiple annotations exist with the same key; delete the extras before updating one'))

    deserialize_json = asbool(data_dict.get('deserialize_json'))
    annotation = annotation_list[0]
    jsonpatch_context = context.copy()
    jsonpatch_context.update({
        'schema': schema.metadata_record_workflow_annotation_show_schema(deserialize_json),
        'ignore_auth': True,
    })
    jsonpatch_data = {
        'id': annotation['jsonpatch_id'],
        'scope': 'workflow',
        'operation': {
            'op': 'add',
            'path': '/' + data_dict['key'],
            'value': json.loads(data_dict['value']),
        },
    }
    return tk.get_action('jsonpatch_update')(jsonpatch_context, jsonpatch_data)


def metadata_record_workflow_state_transition(context, data_dict):
    """
    Transition a metadata record to a different workflow state, and log the result
    to the metadata record's activity stream.

    You must be authorized to change the metadata record's workflow state.

    :param id: the id or name of the metadata record to transition
    :type id: string
    :param workflow_state_id: the id or name of the target workflow state
    :type workflow_state_id: string

    :returns: the workflow activity record, unless the metadata record is already on the target
        state, in which case nothing is changed and None is returned
    :rtype: dictionary
    """
    log.info("Transitioning workflow state of metadata record: %r", data_dict)
    tk.check_access('metadata_record_workflow_state_transition', context, data_dict)

    model = context['model']
    session = context['session']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    target_workflow_state_id = tk.get_or_bust(data_dict, 'workflow_state_id')
    target_workflow_state = ckanext_model.WorkflowState.get(target_workflow_state_id)
    if target_workflow_state is not None:
        target_workflow_state_id = target_workflow_state.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    internal_context = context.copy()
    internal_context.update({
        'metadata_record': metadata_record,
        'workflow_state': target_workflow_state,
        'ignore_auth': True,
    })

    current_workflow_state_id = session.query(model.PackageExtra.value) \
        .filter_by(package_id=metadata_record_id, key='workflow_state_id').scalar()

    # already on target state - return the last workflow result
    if current_workflow_state_id == target_workflow_state_id:
        return tk.get_action('metadata_record_workflow_activity_show')(internal_context, {
            'id': metadata_record_id,
        })

    workflow_transition = ckanext_model.WorkflowTransition.lookup(current_workflow_state_id, target_workflow_state_id)
    if not workflow_transition or workflow_transition.state != 'active':
        raise tk.ValidationError(_("Invalid workflow state transition"))

    # get the metadata record dict, augmented with workflow annotations
    metadata_record_dict = tk.get_action('metadata_record_workflow_augmented_show')(
        internal_context, {'id': metadata_record_id, 'deserialize_json': True})
    jsonpatch_ids = [annotation['jsonpatch_id'] for annotation in
                     tk.get_action('metadata_record_workflow_annotation_list')(internal_context, {'id': metadata_record_id})]

    validate_context = context.copy()
    validate_context['ignore_auth'] = True
    validate_context['allow_side_effects'] = True

    # test whether the augmented metadata record passes the rules for the target state
    workflow_rules_dict = json.loads(target_workflow_state.workflow_rules_json)
    json_validator = WorkflowValidator(workflow_rules_dict, metadata_record_id, validate_context)
    workflow_errors = json_validator.validate(metadata_record_dict)

    if not workflow_errors:
        update_search_index = metadata_record.private != target_workflow_state.metadata_records_private
        metadata_record.private = target_workflow_state.metadata_records_private
        metadata_record.extras['workflow_state_id'] = target_workflow_state_id
    else:
        update_search_index = False

    activity_context = context.copy()
    activity_context.update({
        'defer_commit': True,
        'ignore_auth': True,
        'schema': {
            'user_id': [unicode, tk.get_validator('convert_user_name_or_id_to_id')],
            'object_id': [],
            'revision_id': [],
            'activity_type': [],
            'data': [],
        },
    })
    activity_dict = {
        'user_id': model.User.by_name(user.decode('utf8')).id,
        'object_id': metadata_record_id,
        'activity_type': METADATA_WORKFLOW_ACTIVITY_TYPE,
        'data': {
            'action': 'metadata_record_workflow_state_transition',
            'workflow_state_id': target_workflow_state_id,
            'jsonpatch_ids': jsonpatch_ids,
            'errors': workflow_errors,
        }
    }

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in internal_context:
        rev.message = internal_context['message']
    else:
        rev.message = _(u'REST API: Transition workflow state of metadata record %s') % metadata_record_id

    activity_dict = tk.get_action('activity_create')(activity_context, activity_dict)

    if not defer_commit:
        model.repo.commit()

    if update_search_index:
        index_context = context.copy()
        index_context['metadata_record'] = metadata_record
        index_context['ignore_auth'] = True
        tk.get_action('metadata_record_index_update')(index_context, {'id': metadata_record_id})

    return activity_dict


def metadata_record_workflow_state_revert(context, data_dict):
    """
    Revert a metadata record to the predecessor to its current workflow state (or to None
    if the current state has no revert state), and log the change to the metadata record's
    activity stream.

    You must be authorized to revert the metadata record's workflow state.

    :param id: the id or name of the metadata record to revert
    :type id: string

    :returns: the workflow activity record
    :rtype: dictionary
    """
    log.info("Reverting workflow state of metadata record: %r", data_dict)
    tk.check_access('metadata_record_workflow_state_revert', context, data_dict)

    model = context['model']
    session = context['session']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record_id = tk.get_or_bust(data_dict, 'id')
    metadata_record = model.Package.get(metadata_record_id)
    if metadata_record is not None and metadata_record.type == 'metadata_record':
        metadata_record_id = metadata_record.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    current_workflow_state_id = session.query(model.PackageExtra.value) \
        .filter_by(package_id=metadata_record_id, key='workflow_state_id').scalar()

    # already on null state
    if not current_workflow_state_id:
        return

    target_workflow_state = ckanext_model.WorkflowState.get_revert_state(current_workflow_state_id)
    if target_workflow_state:
        target_workflow_state_id = target_workflow_state.id
        metadata_record_private = target_workflow_state.metadata_records_private
    else:
        target_workflow_state_id = ''
        metadata_record_private = True

    update_search_index = metadata_record.private != metadata_record_private
    metadata_record.private = metadata_record_private
    metadata_record.extras['workflow_state_id'] = target_workflow_state_id

    activity_context = context.copy()
    activity_context.update({
        'defer_commit': True,
        'ignore_auth': True,
        'schema': {
            'user_id': [unicode, tk.get_validator('convert_user_name_or_id_to_id')],
            'object_id': [],
            'revision_id': [],
            'activity_type': [],
            'data': [],
        },
    })
    activity_dict = {
        'user_id': model.User.by_name(user.decode('utf8')).id,
        'object_id': metadata_record_id,
        'activity_type': METADATA_WORKFLOW_ACTIVITY_TYPE,
        'data': {
            'action': 'metadata_record_workflow_state_revert',
            'workflow_state_id': target_workflow_state_id,
        }
    }

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Revert workflow state of metadata record %s') % metadata_record_id

    activity_dict = tk.get_action('activity_create')(activity_context, activity_dict)

    if not defer_commit:
        model.repo.commit()

    if update_search_index:
        index_context = context.copy()
        index_context['metadata_record'] = metadata_record
        index_context['ignore_auth'] = True
        tk.get_action('metadata_record_index_update')(index_context, {'id': metadata_record_id})

    return activity_dict


def metadata_record_index_update(context, data_dict):
    """
    Placeholder function for adding/updating/deleting a metadata record in a search index.
    May be implemented as required by another plugin.

    You must be authorized to update the search index.

    :param id: the id or name of the metadata record
    :type id: string
    """
    tk.check_access('metadata_record_index_update', context, data_dict)


def metadata_json_attr_map_update(context, data_dict):
    """
    Update a metadata JSON attribute map.

    You must be authorized to edit the metadata JSON attribute map.

    It is recommended to call
    :py:func:`ckan.logic.action.get.metadata_json_attr_map_show`, make the desired changes to
    the result, and then call ``metadata_json_attr_map_update()`` with it.

    For further parameters see
    :py:func:`~ckanext.metadata.logic.action.create.metadata_json_attr_map_create`.

    :param id: the id of the metadata JSON attribute map to update
    :type id: string

    :returns: the updated metadata JSON attribute map (unless 'return_id_only' is set to True
              in the context, in which case just the id will be returned)
    :rtype: dictionary
    """
    log.info("Updating metadata JSON attribute map: %r", data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    data_dict['is_key'] = False

    metadata_json_attr_map_id = tk.get_or_bust(data_dict, 'id')
    metadata_json_attr_map = ckanext_model.MetadataJSONAttrMap.get(metadata_json_attr_map_id)
    if metadata_json_attr_map is not None:
        metadata_json_attr_map_id = metadata_json_attr_map.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata JSON Attribute Map')))

    tk.check_access('metadata_json_attr_map_update', context, data_dict)

    data_dict.update({
        'id': metadata_json_attr_map_id,
    })
    context.update({
        'metadata_json_attr_map': metadata_json_attr_map,
        'allow_partial_update': True,
    })

    data, errors = tk.navl_validate(data_dict, schema.metadata_json_attr_map_update_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_json_attr_map = model_save.metadata_json_attr_map_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update metadata JSON attribute map %s') % metadata_json_attr_map_id

    if not defer_commit:
        model.repo.commit()

    output = metadata_json_attr_map_id if return_id_only \
        else tk.get_action('metadata_json_attr_map_show')(context, {'id': metadata_json_attr_map_id})
    return output


def metadata_collection_validate(context, data_dict):
    """
    Bulk validate all the non-validated metadata records in a collection.

    :param id: the id or name of the metadata collection
    :type id: string
    :param async: validate the records asynchronously (optional, default: ``False``)
    :type async: boolean

    :returns: { total_count, error_count }
    :rtype: dict
    """
    log.info("Validating metadata collection: %r", data_dict)
    tk.check_access('metadata_collection_validate', context, data_dict)

    model = context['model']
    session = context['session']
    async = data_dict.get('async', False)

    metadata_collection_id = tk.get_or_bust(data_dict, 'id')
    metadata_collection = model.Group.get(metadata_collection_id)
    if metadata_collection is not None and metadata_collection.type == 'metadata_collection':
        metadata_collection_id = metadata_collection.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))

    collection_extra = aliased(model.PackageExtra)
    validated_extra = aliased(model.PackageExtra)

    record_ids = session.query(model.Package.id) \
        .join(collection_extra) \
        .join(validated_extra) \
        .filter(model.Package.type == 'metadata_record') \
        .filter(model.Package.state == 'active') \
        .filter(collection_extra.key == 'metadata_collection_id') \
        .filter(collection_extra.value == metadata_collection_id) \
        .filter(validated_extra.key == 'validated') \
        .filter(validated_extra.value.in_(falsy)) \
        .all()
    data_dicts = [{'id': record_id} for (record_id,) in record_ids]
    return bulk_action('metadata_record_validate', context, data_dicts, async)


def metadata_collection_workflow_state_transition(context, data_dict):
    """
    Bulk transition all metadata records in a collection to the specified workflow state.

    :param id: the id or name of the metadata collection
    :type id: string
    :param workflow_state_id: the id or name of the target workflow state
    :type workflow_state_id: string
    :param async: transition the records asynchronously (optional, default: ``False``)
    :type async: boolean

    :returns: { total_count, error_count }
    :rtype: dict
    """
    log.info("Transitioning workflow state of metadata records in collection: %r", data_dict)
    tk.check_access('metadata_collection_workflow_state_transition', context, data_dict)

    model = context['model']
    session = context['session']
    async = data_dict.get('async', False)

    metadata_collection_id = tk.get_or_bust(data_dict, 'id')
    metadata_collection = model.Group.get(metadata_collection_id)
    if metadata_collection is not None and metadata_collection.type == 'metadata_collection':
        metadata_collection_id = metadata_collection.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Collection')))

    target_workflow_state_id = tk.get_or_bust(data_dict, 'workflow_state_id')
    target_workflow_state = ckanext_model.WorkflowState.get(target_workflow_state_id)
    if target_workflow_state is not None:
        target_workflow_state_id = target_workflow_state.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Workflow State')))

    collection_extra = aliased(model.PackageExtra)
    workflow_state_extra = aliased(model.PackageExtra)

    record_ids = session.query(model.Package.id) \
        .join(collection_extra) \
        .join(workflow_state_extra) \
        .filter(model.Package.type == 'metadata_record') \
        .filter(model.Package.state == 'active') \
        .filter(collection_extra.key == 'metadata_collection_id') \
        .filter(collection_extra.value == metadata_collection_id) \
        .filter(workflow_state_extra.key == 'workflow_state_id') \
        .filter(workflow_state_extra.value != target_workflow_state_id) \
        .all()
    data_dicts = [{'id': record_id, 'workflow_state_id': target_workflow_state_id}
                  for (record_id,) in record_ids]
    return bulk_action('metadata_record_workflow_state_transition', context, data_dicts, async)


def metadata_record_assign_doi(context, data_dict):
    """
    Assign a DOI to a metadata record.

    Prerequisites for this to succeed:
    - the config option 'ckan.metadata.doi_prefix' must be set
    - the record must not already have a DOI assigned to it

    The metadata collection's 'doi_collection' property will be used if it has been set.

    :param id: the id or name of the metadata record
    :type id: string
    :return: the new DOI
    """
    log.info("Assigning a DOI to metadata record: %r", data_dict)
    tk.check_access('metadata_record_assign_doi', context, data_dict)

    model = context['model']
    session = context['session']
    user = context['user']
    defer_commit = context.get('defer_commit', False)

    metadata_record = context.get('metadata_record')
    if not metadata_record:
        metadata_record_id = tk.get_or_bust(data_dict, 'id')
        metadata_record = model.Package.get(metadata_record_id)
        if metadata_record is None or metadata_record.type != 'metadata_record':
            raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Metadata Record')))

    if metadata_record.extras['doi']:
        raise tk.ValidationError(_("Cannot assign DOI: The metadata record already has a DOI"))

    doi_prefix = config.get('ckan.metadata.doi_prefix')
    if not doi_prefix:
        raise tk.ValidationError(_("Cannot assign DOI: Config option ckan.metadata.doi_prefix has not been set"))

    if not re.match(DOI_PREFIX_RE, doi_prefix):
        raise tk.ValidationError(_("Cannot assign DOI: Config option ckan.metadata.doi_prefix specifies an invalid DOI prefix"))

    doi_collection = session.query(model.GroupExtra.value) \
        .filter_by(key='doi_collection', group_id=metadata_record.extras['metadata_collection_id']) \
        .scalar()
    if doi_collection and not doi_collection.endswith('.'):
        doi_collection += '.'

    while True:
        doi = '{doi_prefix}/{doi_collection}{unique_number}'.format(
            doi_prefix=doi_prefix,
            doi_collection=doi_collection,
            unique_number='{:.10f}'.format(random.SystemRandom().random())[2:],
        )
        # collisions are extremely unlikely, but we check anyway
        collision = session.query(model.PackageExtra) \
            .filter_by(key='doi', value=doi) \
            .first()
        if not collision:
            break

    metadata_record.extras['doi'] = doi

    # if there is a JSON attribute mapping for the 'doi' field, then we try to put the new DOI into the metadata JSON
    doi_json_path = session.query(ckanext_model.MetadataJSONAttrMap.json_path) \
        .filter_by(metadata_standard_id=metadata_record.extras['metadata_standard_id'],
                   record_attr='doi', state='active') \
        .scalar()
    if doi_json_path:
        metadata_dict = json.loads(metadata_record.extras['metadata_json'])

        # if the target element for the DOI is nested, we have to make sure the parent element chain exists
        parents = []
        parent_path = doi_json_path
        while True:
            parent_path = parent_path.rpartition('/')[0]
            if parent_path:
                parents.insert(0, parent_path)
            else:
                break

        try:
            for parent in parents:
                try:
                    jsonpointer.resolve_pointer(metadata_dict, parent)
                except jsonpointer.JsonPointerException:
                    jsonpointer.set_pointer(metadata_dict, parent, {})

            jsonpointer.set_pointer(metadata_dict, doi_json_path, doi)
            metadata_record.extras['metadata_json'] = json.dumps(metadata_dict, ensure_ascii=False)

        except jsonpointer.JsonPointerException:
            # it's good enough that we've set the 'doi' field above
            pass

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Assign DOI to metadata record %s') % metadata_record.id

    if not defer_commit:
        model.repo.commit()

    return doi
