# encoding: utf-8


METADATA_VALIDATION_ACTIVITY_TYPE = u'metadata validation'
METADATA_WORKFLOW_ACTIVITY_TYPE = u'metadata workflow'


class MetadataValidationState(object):

    NOT_VALIDATED = u'not validated'
    INVALID = u'invalid'
    PARTIALLY_VALID = u'partially valid'
    VALID = u'valid'

    @staticmethod
    def net_state(partial_states):
        """
        Given a bunch of partial validation results, determine the net result.
        This is the 'least valid' of the given partial states.
        :param partial_states: iterable of MetadataValidationState
        :return: MetadataValidationState
        """
        # order of increasing validity
        validity_order = {
            MetadataValidationState.NOT_VALIDATED: 0,
            MetadataValidationState.INVALID: 1,
            MetadataValidationState.PARTIALLY_VALID: 2,
            MetadataValidationState.VALID: 3,
        }

        if not partial_states:
            return MetadataValidationState.NOT_VALIDATED

        result_state = MetadataValidationState.VALID
        for partial_state in partial_states:
            if validity_order[partial_state] < validity_order[result_state]:
                result_state = partial_state

        return result_state
