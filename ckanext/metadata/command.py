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
        paster metadata_framework initperms
            - Initialize the permissions for the metadata framework action API
              (requires the roles plugin provided by the ckanext-accesscontrol extension)
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
        elif cmd == 'initperms':
            self._initperms()

    def _initdb(self):
        from ckanext.metadata.model import setup
        setup.init_tables()
        self.log.info("Metadata tables have been initialized")

    def _initperms(self):
        from ckanext.metadata.logic import setup_permissions
        setup_permissions.init_permissions()
        self.log.info("Permissions have been initialized")
