# encoding: utf-8

import logging
import sys

import ckan.plugins.toolkit as tk


class MetadataFrameworkCommand(tk.CkanCommand):
    """
    Metadata framework management commands.

    Usage:
        paster metadata_framework initdb
            - Initialize the database tables for the metadata framework
        paster metadata_framework init_permissions
            - Initialize the permissions for the metadata framework action API
        paster metadata_framework reset_permissions
            - Delete all permissions (including any defined by other extensions)

        Note: the *_permissions commands require the roles plugin provided by the
        ckanext-accesscontrol extension.
    """
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        if not self.args or self.args[0] in ['--help', '-h', 'help']:
            print self.usage
            sys.exit(1)

        cmd = self.args[0]
        self._load_config()

        # initialize logger after config is loaded, so that it is not disabled
        self.log = logging.getLogger(__name__)

        if cmd == 'initdb':
            self._initdb()
        elif cmd == 'init_permissions':
            self._init_permissions()
        elif cmd == 'reset_permissions':
            self._reset_permissions()
        else:
            print "Unknown command", cmd
            print self.usage
            sys.exit(1)

    def _initdb(self):
        from ckanext.metadata.model import setup
        setup.init_tables()
        self.log.info("Metadata tables have been initialized")

    def _init_permissions(self):
        from ckanext.metadata.logic import setup_permissions
        setup_permissions.init_permissions()
        self.log.info("Permissions have been initialized")

    def _reset_permissions(self):
        from ckanext.metadata.logic import setup_permissions
        setup_permissions.reset_permissions()
        self.log.info("Permissions have been reset")
