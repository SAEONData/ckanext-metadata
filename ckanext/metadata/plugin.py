# encoding: utf-8

import logging
import ckan.plugins as p

log = logging.getLogger(__name__)


class MetadataFrameworkPlugin(p.SingletonPlugin):
    """
    Plugin providing CRUDs and APIs for metadata framework entities.
    """
    p.implements(p.IActions)
    p.implements(p.IAuthFunctions)

    def get_actions(self):
        return self._get_logic_functions('ckanext.metadata.logic.action')

    def get_auth_functions(self):
        return self._get_logic_functions('ckanext.metadata.logic.auth')

    @staticmethod
    def _get_logic_functions(module_root):

        logic_functions = {}

        for module_name in ['get', 'create', 'update', 'delete']:
            module_path = '%s.%s' % (module_root, module_name,)
            module = __import__(module_path)
            for part in module_path.split('.')[1:]:
                module = getattr(module, part)

            for key, value in module.__dict__.items():
                if not key.startswith('_') and hasattr(value, '__call__') and value.__module__ == module_path:
                    logic_functions[key] = value

        return logic_functions
