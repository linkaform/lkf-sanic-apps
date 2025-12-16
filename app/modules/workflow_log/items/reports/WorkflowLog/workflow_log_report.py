# -*- coding: utf-8 -*-

import sys, simplejson
from datetime import datetime, timedelta, date
from copy import deepcopy

print('Arranca Stock - Report en modulo stock....')
# from lkf_addons.stock.report import Reports

#Se agrega path para que obtenga el archivo de Stock de este modulo
sys.path.append('/srv/scripts/addons/modules/workflow_log/items/scripts/WorkflowLog')
from workflow_log_utils import WorkflowLog

today = date.today()
year_week = int(today.strftime('%Y%W'))


class Reports(WorkflowLog):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False):
        #base.LKF_Base.__init__(self, settings, sys_argv=sys_argv, use_api=use_api)
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.INVENTORY_ID = self.lkm.form_id('stock_inventory','id')
