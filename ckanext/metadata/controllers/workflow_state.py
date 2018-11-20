# encoding: utf-8

import ckan.plugins.toolkit as tk


class WorkflowStateController(tk.BaseController):

    def index(self):
        return tk.render('workflow_state/index.html')
