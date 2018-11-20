# encoding: utf-8

import ckan.plugins.toolkit as tk


class MetadataStandardController(tk.BaseController):

    def index(self):
        return tk.render('metadata_standard/index.html')
