# encoding: utf-8

import logging
import json
from paste.deploy.converters import asbool
from sqlalchemy import func

import ckan.plugins.toolkit as tk
from ckan.common import _
from ckanext.metadata.logic import schema
from ckanext.metadata.lib.dictization import model_save
from ckan.logic.action.create import organization_create as ckan_org_create

log = logging.getLogger(__name__)


# optional params may or may not be supplied by the caller
# nullable params must be supplied but may be empty
# all other params must be supplied and must not be empty

def metadata_standard_create(context, data_dict):
    """
    Create a new metadata standard.

    You must be authorized to create metadata standards.

    :param name: the name of the new metadata standard (optional - auto-generated if not supplied);
        must conform to standard naming rules
    :type name: string
    :param description: the description of the metadata standard (optional)
    :type description: string
    :param standard_name: the name of the metadata standard
    :type standard_name: string
    :param standard_version: the version of the metadata standard (nullable)
    :type standard_version: string
    :param parent_standard_id: the id or name of the metadata standard from which this standard is derived (nullable)
    :type parent_standard_id: string
    :param metadata_template_json: a complete example of a JSON metadata dictionary that conforms to this standard;
        may be used for initializing a search index
    :type metadata_template_json: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :returns: the newly created metadata standard (unless 'return_id_only' is set to True
              in the context, in which case just the metadata standard id will be returned)
    :rtype: dictionary
    """
    log.info("Creating metadata standard: %r", data_dict)
    tk.check_access('metadata_standard_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    data, errors = tk.navl_validate(data_dict, schema.metadata_standard_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_standard = model_save.metadata_standard_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create metadata standard %s') % metadata_standard.id

    if not defer_commit:
        model.repo.commit()

    output = metadata_standard.id if return_id_only \
        else tk.get_action('metadata_standard_show')(context, {'id': metadata_standard.id, 'deserialize_json': deserialize_json})
    return output


def metadata_schema_create(context, data_dict):
    """
    Create a new metadata schema.

    You must be authorized to create metadata schemas.

    A metadata schema must be one and only one of the following:
    - the default for the given metadata standard (no organization or infrastructure)
    - associated with an organization
    - associated with an infrastructure

    Any metadata records that are now dependent on this schema are invalidated.

    :param name: the name of the new metadata schema (optional - auto-generated if not supplied);
        must conform to standard naming rules
    :type name: string
    :param description: the description of the metadata schema (optional)
    :type description: string
    :param metadata_standard_id: the id or name of the metadata standard for which this schema is defined
    :type metadata_standard_id: string
    :param schema_json: the JSON dictionary defining the schema
    :type schema_json: string
    :param organization_id: the id or name of the associated organization (nullable)
    :type organization_id: string
    :param infrastructure_id: the id or name of the associated infrastructure (nullable)
    :type infrastructure_id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :returns: the newly created metadata schema (unless 'return_id_only' is set to True
              in the context, in which case just the metadata schema id will be returned)
    :rtype: dictionary
    """
    log.info("Creating metadata schema: %r", data_dict)
    tk.check_access('metadata_schema_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    data, errors = tk.navl_validate(data_dict, schema.metadata_schema_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_schema = model_save.metadata_schema_dict_save(data, context)

    # creating the revision also flushes the session which gives us the new object id
    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create metadata schema %s') % metadata_schema.id

    dependent_record_list_context = context.copy()
    dependent_record_list_context['ignore_auth'] = True
    dependent_record_list = tk.get_action('metadata_schema_dependent_record_list')(dependent_record_list_context, {'id': metadata_schema.id})
    invalidate_context = context.copy()
    invalidate_context.update({
        'defer_commit': True,
        'ignore_auth': True,
        'trigger_action': 'metadata_schema_create',
        'trigger_object_id': metadata_schema.id,
    })
    for metadata_record_id in dependent_record_list:
        tk.get_action('metadata_record_invalidate')(invalidate_context, {'id': metadata_record_id})

    if not defer_commit:
        model.repo.commit()

    output = metadata_schema.id if return_id_only \
        else tk.get_action('metadata_schema_show')(context, {'id': metadata_schema.id, 'deserialize_json': deserialize_json})
    return output


def infrastructure_create(context, data_dict):
    """
    Create a group of type 'infrastructure'.
    
    You must be authorized to create infrastructures.

    :param name: the name of the infrastructure; must conform to group naming rules
    :type name: string
    :param title: the title of the infrastructure (optional)
    :type title: string
    :param description: the description of the infrastructure (optional)
    :type description: string
    :param users: the users associated with the infrastructure (optional); a list of dictionaries
        each with key ``'name'`` (string, the id or name of the user) and optionally ``'capacity'``
        (string, the capacity in which the user is a member of the infrastructure)
    :type users: list of dictionaries

    :returns: the newly created infrastructure (unless 'return_id_only' is set to True
              in the context, in which case just the infrastructure id will be returned)
    :rtype: dictionary
    """
    log.info("Creating infrastructure: %r", data_dict)
    tk.check_access('infrastructure_create', context, data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data_dict.update({
        'type': 'infrastructure',
        'is_organization': False,
    })
    internal_context = context.copy()
    internal_context.update({
        'schema': schema.infrastructure_create_schema(),
        'invoked_action': 'infrastructure_create',
        'defer_commit': True,
        'return_id_only': True,
        'ignore_auth': True,
    })

    # defer_commit does not actually work due to a bug in _group_or_org_create (in ckan.logic.action.create)
    # - addition of the creating user as a member is done (committed) without consideration for defer_commit
    # - but it does not make much difference to us here
    infrastructure_id = tk.get_action('group_create')(internal_context, data_dict)

    if not defer_commit:
        model.repo.commit()

    output = infrastructure_id if return_id_only \
        else tk.get_action('infrastructure_show')(internal_context, {'id': infrastructure_id})
    return output


def organization_create(context, data_dict):
    """
    Create an organization. Wraps CKAN's organization_create, so that we can
    create a default metadata collection.

    You must be authorized to create organizations.

    For available parameters see
    :py:func:`~ckan.logic.action.create.organization_create`.

    :returns: the newly created organization (unless 'return_id_only' is set
              to True in the context, in which case just the organization id
              will be returned)
    :rtype: dictionary
    """
    log.info("Creating organization: %r", data_dict)
    tk.check_access('organization_create', context, data_dict)

    return_id_only = context.get('return_id_only', False)
    internal_context = context.copy()
    internal_context['defer_commit'] = False

    organization_dict = ckan_org_create(internal_context, data_dict)

    internal_context = context.copy()
    internal_context['defer_commit'] = False

    output = organization_dict['id'] if return_id_only \
        else tk.get_action('organization_show')(internal_context, {'id': organization_dict['id']})
    return output


def metadata_collection_create(context, data_dict):
    """
    Create a group of type 'metadata_collection'.

    You must be authorized to create metadata collections.

    :param name: the name of the metadata collection; must conform to group naming rules
    :type name: string
    :param title: the title of the metadata collection (optional)
    :type title: string
    :param description: the description of the metadata collection (optional)
    :type description: string
    :param organization_id: the id or name of the organization to which this collection belongs
    :type organization_id: string
    :param doi_collection: a qualifier to be inserted into new DOIs after the DOI prefix (nullable);
        e.g. 'DOI.COLLECTION' in '10.12345/DOI.COLLECTION.67890'
    :type doi_collection: string
    :param users: the users associated with the collection (optional); a list of dictionaries
        each with key ``'name'`` (string, the id or name of the user) and optionally ``'capacity'``
        (string, the capacity in which the user is a member of the collection)
    :type users: list of dictionaries
    :param infrastructures: the infrastructures associated with the collection (optional);
        list of dictionaries each with key ``'id'`` (string, the id or name of the infrastructure)
    :type infrastructures: list of dictionaries

    :returns: the newly created metadata collection (unless 'return_id_only' is set to True
              in the context, in which case just the metadata collection id will be returned)
    :rtype: dictionary
    """
    log.info("Creating metadata collection: %r", data_dict)
    tk.check_access('metadata_collection_create', context, data_dict)

    model = context['model']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data_dict.update({
        'type': 'metadata_collection',
        'is_organization': False,
    })
    internal_context = context.copy()
    internal_context.update({
        'schema': schema.metadata_collection_create_schema(),
        'invoked_action': 'metadata_collection_create',
        'defer_commit': True,
        'return_id_only': True,
        'ignore_auth': True,
    })

    # defer_commit does not actually work due to a bug in _group_or_org_create (in ckan.logic.action.create)
    # - addition of the creating user as a member is done (committed) without consideration for defer_commit
    # - this will be a problem if saving of organization membership or infrastructure list fails
    metadata_collection_id = tk.get_action('group_create')(internal_context, data_dict)
    model_save.metadata_collection_organization_membership_save(data_dict['organization_id'], internal_context)
    model_save.metadata_collection_infrastructure_list_save(data_dict.get('infrastructures'), internal_context)

    if not defer_commit:
        model.repo.commit()

    output = metadata_collection_id if return_id_only \
        else tk.get_action('metadata_collection_show')(internal_context, {'id': metadata_collection_id})
    return output


def metadata_record_create(context, data_dict):
    """
    Create a package of type 'metadata_record'.

    You must be authorized to create metadata records.

    If an incoming request matches an existing record on DOI and/or SID,
    then we switch to an update. Comparisons are case-insensitive.
    Once set, a DOI is pinned permanently to a record ID.
    An SID, on the other hand, may be changed or un-set.

    :param doi: digital object identifier (nullable)
    :type doi: string
    :param sid: secondary identifier (nullable, but mandatory if doi is not supplied)
    :type sid: string
    :param owner_org: the id or name of the organization to which this record belongs
    :type owner_org: string
    :param metadata_collection_id: the id or name of the metadata collection to which this record will be added
    :type metadata_collection_id: string
    :param metadata_standard_id: the id or name of the metadata standard that describes the record's structure
    :type metadata_standard_id: string
    :param metadata_json: JSON dictionary of metadata record content
    :type metadata_json: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    The following native package fields may also optionally be supplied:
        title, author, author_email, maintainer, maintainer_email, license_id, notes, url, version
    See :py:func:`ckan.logic.action.create.package_create` for more information.

    Note that these fields (as well as 'name') may be used in metadata JSON attribute mappings, in which
    case the input value(s) are ignored and overridden by the mapped element(s) from the metadata JSON.

    :returns: the newly created metadata record (unless 'return_id_only' is set to True
              in the context, in which case just the metadata record id will be returned)
    :rtype: dictionary
    """
    log.info("Creating metadata record: %r", data_dict)
    tk.check_access('metadata_record_create', context, data_dict)

    model = context['model']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    internal_context = context.copy()
    internal_context['ignore_auth'] = True

    # this is (mostly) duplicating the schema validation that will be done in package_create below,
    # but we want to validate before processing DOI/SID and attribute mappings
    data, errors = tk.navl_validate(data_dict, schema.metadata_record_create_schema(), internal_context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    doi = data_dict.get('doi')
    sid = data_dict.get('sid')
    if not doi and not sid:
        raise tk.ValidationError({"doi,sid": ["DOI and/or SID must be given"]})

    # find a matching record by DOI
    if doi:
        existing_doi_rec = session.query(model.Package). \
            join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id). \
            filter(model.PackageExtra.key == 'doi'). \
            filter(func.lower(model.PackageExtra.value) == doi.lower()). \
            first()
    else:
        existing_doi_rec = None

    # find a matching record by SID
    if sid:
        existing_sid_rec = session.query(model.Package). \
            join(model.PackageExtra, model.Package.id == model.PackageExtra.package_id). \
            filter(model.PackageExtra.key == 'sid'). \
            filter(func.lower(model.PackageExtra.value) == sid.lower()). \
            first()
    else:
        existing_sid_rec = None

    # DOI ownership cannot change
    if existing_doi_rec and existing_doi_rec.owner_org != data['owner_org']:
        raise tk.ValidationError({"doi": ["The DOI is in use by another organization"]})

    # SID ownership cannot change
    if existing_sid_rec and existing_sid_rec.owner_org != data['owner_org']:
        raise tk.ValidationError({"sid": ["The SID is in use by another organization"]})

    # ambiguous match
    if existing_doi_rec and existing_sid_rec and existing_doi_rec.id != existing_sid_rec.id:
        raise tk.ValidationError({"doi,sid": ["The DOI and SID are associated with two different metadata records"]})

    # matched on DOI; switch to an update
    if existing_doi_rec:
        log.info('Matched existing record on DOI; switching to metadata_record_update')
        data_dict['id'] = existing_doi_rec.id
        return tk.get_action('metadata_record_update')(internal_context, data_dict)

    # matched on SID; switch to an update
    # metadata_record_update ensures that an existing DOI is not changed or un-set
    if existing_sid_rec:
        log.info('Matched existing record on SID; switching to metadata_record_update')
        data_dict['id'] = existing_sid_rec.id
        return tk.get_action('metadata_record_update')(internal_context, data_dict)

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
        data_dict['metadata_json'] = json.dumps(metadata_dict)

    # map values from the metadata JSON into the data_dict
    attr_map = tk.get_action('metadata_json_attr_map_apply')(internal_context, {
        'metadata_standard_id': data_dict.get('metadata_standard_id'),
        'metadata_json': data_dict.get('metadata_json'),
    })
    data_dict.update(attr_map['data_dict'])

    # it's new metadata; create the package object
    data_dict.update({
        'type': 'metadata_record',
        'validated': False,
        'errors': '{}',
        'workflow_state_id': '',
        'private': True,
    })
    internal_context.update({
        'schema': schema.metadata_record_create_schema(),
        'invoked_action': 'metadata_record_create',
        'defer_commit': True,
        'return_id_only': True,
    })
    metadata_record_id = tk.get_action('package_create')(internal_context, data_dict)
    model_save.metadata_record_collection_membership_save(data_dict['metadata_collection_id'], internal_context)

    if not defer_commit:
        model.repo.commit()

    output = metadata_record_id if return_id_only \
        else tk.get_action('metadata_record_show')(internal_context, {'id': metadata_record_id, 'deserialize_json': deserialize_json})
    return output


def workflow_state_create(context, data_dict):
    """
    Create a new workflow state.

    You must be authorized to create workflow states.

    :param name: the name of the new workflow state; must conform to standard naming rules
    :type name: string
    :param title: the title of the workflow state (optional)
    :type title: string
    :param description: the description of the workflow state (optional)
    :type description: string
    :param workflow_rules_json: JSON schema against which an augmented metadata record must
        be validated in order to be assigned this workflow state
    :type workflow_rules_json: string
    :param metadata_records_private: determines the private/public status of metadata records
        that are in this workflow state
    :type metadata_records_private: boolean
    :param revert_state_id: the id or name of the state to which a metadata record is
        reverted in case it no longer fulfils the rules for this state (nullable)
    :type revert_state_id: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :returns: the newly created workflow state (unless 'return_id_only' is set to True
              in the context, in which case just the workflow state id will be returned)
    :rtype: dictionary
    """
    log.info("Creating workflow state: %r", data_dict)
    tk.check_access('workflow_state_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    deserialize_json = asbool(data_dict.get('deserialize_json'))

    data, errors = tk.navl_validate(data_dict, schema.workflow_state_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_state = model_save.workflow_state_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create workflow state %s') % workflow_state.id

    if not defer_commit:
        model.repo.commit()

    output = workflow_state.id if return_id_only \
        else tk.get_action('workflow_state_show')(context, {'id': workflow_state.id, 'deserialize_json': deserialize_json})
    return output


def workflow_transition_create(context, data_dict):
    """
    Create a new workflow transition.

    You must be authorized to create workflow transitions.

    :param from_state_id: the id or name of the source workflow state (nullable - null implies
        that the target state is an initial workflow state)
    :type from_state_id: string
    :param to_state_id: the id or name of the target workflow state
    :type to_state_id: string

    :returns: the newly created workflow transition (unless 'return_id_only' is set to True
              in the context, in which case just the workflow transition id will be returned)
    :rtype: dictionary
    """
    log.info("Creating workflow transition: %r", data_dict)
    tk.check_access('workflow_transition_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data, errors = tk.navl_validate(data_dict, schema.workflow_transition_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_transition = model_save.workflow_transition_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create workflow transition %s') % workflow_transition.id

    if not defer_commit:
        model.repo.commit()

    output = workflow_transition.id if return_id_only \
        else tk.get_action('workflow_transition_show')(context, {'id': workflow_transition.id})
    return output


def workflow_annotation_create(context, data_dict):
    """
    Create a new workflow annotation definition, which simply makes it easier for annotations
    to be added to metadata records via the UI.

    You must be authorized to create workflow annotations.

    :param name: the (augmented metadata record) dictionary key under which an annotation will be added
    :type name: string
    :param attributes: a dict of names and JSON types of the annotation attributes
    :type attributes: dictionary

    :returns: the newly created workflow annotation (unless 'return_id_only' is set to True
              in the context, in which case just the workflow annotation id will be returned)
    :rtype: dictionary
    """
    log.info("Creating workflow annotation: %r", data_dict)
    tk.check_access('workflow_annotation_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)

    data, errors = tk.navl_validate(data_dict, schema.workflow_annotation_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    workflow_annotation = model_save.workflow_annotation_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create workflow annotation %s') % workflow_annotation.id

    if not defer_commit:
        model.repo.commit()

    output = workflow_annotation.id if return_id_only \
        else tk.get_action('workflow_annotation_show')(context, {'id': workflow_annotation.id})
    return output


def metadata_record_workflow_annotation_create(context, data_dict):
    """
    Add a workflow annotation to a metadata record.

    You must be authorized to add annotations to the metadata record.

    This is a wrapper for jsonpatch_create, creating an 'add' patch operation with scope 'workflow'.

    :param id: the id or name of the metadata record to annotate
    :type id: string
    :param key: the key in the augmented metadata record dict at which the annotation value will be set;
        this cannot be an existing key in the metadata record show schema
    :type key: string
    :param value: the JSON object to set at the specified key
    :type value: string
    :param deserialize_json: convert JSON string fields to objects in the output dict (optional, default: ``False``)
    :type deserialize_json: boolean

    :returns: the newly created workflow annotation (which is a facade to the underlying JSONPatch object)
    :rtype: dictionary
    """
    log.info("Adding a workflow annotation to a metadata record: %r", data_dict)
    tk.check_access('metadata_record_workflow_annotation_create', context, data_dict)

    session = context['session']
    data, errors = tk.navl_validate(data_dict, schema.metadata_record_workflow_annotation_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    annotation = tk.get_action('metadata_record_workflow_annotation_show')(context, data_dict)
    if annotation:
        raise tk.ValidationError({'key': [_('Duplicate: workflow annotation with the given key already exists on metadata record')]})

    deserialize_json = asbool(data_dict.get('deserialize_json'))
    jsonpatch_context = context.copy()
    jsonpatch_context.update({
        'schema': schema.metadata_record_workflow_annotation_show_schema(deserialize_json),
        'ignore_auth': True,
    })
    jsonpatch_data = {
        'model_name': 'metadata_record',
        'object_id': data_dict['id'],
        'scope': 'workflow',
        'operation': {
            'op': 'add',
            'path': '/' + data_dict['key'],
            'value': json.loads(data_dict['value']),
        },
    }
    return tk.get_action('jsonpatch_create')(jsonpatch_context, jsonpatch_data)


def metadata_standard_index_create(context, data_dict):
    """
    Placeholder function for initializing a metadata search index.
    May be implemented as required by another plugin.

    You must be authorized to create a search index.

    :param id: the id or name of the metadata standard
    :type id: string
    """
    tk.check_access('metadata_standard_index_create', context, data_dict)


def metadata_json_attr_map_create(context, data_dict):
    """
    Create a one-to-one mapping from a metadata JSON element to a metadata record attribute.

    When a metadata record is created or updated, metadata JSON values are copied into
    metadata record attributes for each such defined mapping.

    :param json_path: JSON pointer to a location in a metadata record dictionary
    :type json_path: string
    :param record_attr: the name of an attribute in the metadata record schema
    :type record_attr: string
    :param is_key: no longer used
    :type is_key: boolean
    :param metadata_standard_id: the id or name of the metadata standard for which this mapping is defined
    :type metadata_standard_id: string

    :returns: the newly created MetadataJSONAttrMap object
    :rtype: dictionary
    """
    log.info("Creating metadata JSON attribute mapping: %r", data_dict)
    tk.check_access('metadata_json_attr_map_create', context, data_dict)

    model = context['model']
    user = context['user']
    session = context['session']
    defer_commit = context.get('defer_commit', False)
    return_id_only = context.get('return_id_only', False)
    data_dict['is_key'] = False

    data, errors = tk.navl_validate(data_dict, schema.metadata_json_attr_map_create_schema(), context)
    if errors:
        session.rollback()
        raise tk.ValidationError(errors)

    metadata_json_attr_map = model_save.metadata_json_attr_map_dict_save(data, context)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create metadata JSON attribute mapping %s') % metadata_json_attr_map.id

    if not defer_commit:
        model.repo.commit()

    output = metadata_json_attr_map.id if return_id_only \
        else tk.get_action('metadata_json_attr_map_show')(context, {'id': metadata_json_attr_map.id})
    return output


def infrastructure_member_create(context, data_dict):
    """
    Make a user a member of an infrastructure.

    You must be authorized to edit the infrastructure.

    :param id: the id or name of the infrastructure
    :type id: string
    :param username: name or id of the user
    :type username: string
    :param role: role of the user in the infrastructure. One of ``member``, ``editor``, ``admin``
    :type role: string

    :returns: the newly created (or updated) membership
    :rtype: dictionary
    """
    log.info("Adding a user as a member of an infrastructure: %r", data_dict)
    tk.check_access('infrastructure_member_create', context, data_dict)

    model = context['model']

    infrastructure_id, username, role = tk.get_or_bust(data_dict, ['id', 'username', 'role'])
    infrastructure = model.Group.get(infrastructure_id)
    if infrastructure is not None and infrastructure.type == 'infrastructure':
        infrastructure_id = infrastructure.id
    else:
        raise tk.ObjectNotFound('%s: %s' % (_('Not found'), _('Project')))

    member_dict = {
        'id': infrastructure_id,
        'object': username,
        'object_type': 'user',
        'capacity': role,
    }
    member_context = context.copy()
    member_context['ignore_auth'] = True
    return tk.get_action('member_create')(member_context, member_dict)
