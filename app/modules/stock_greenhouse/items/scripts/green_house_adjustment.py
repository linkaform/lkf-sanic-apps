# -*- coding: utf-8 -*-
import sys, simplejson, math
from datetime import timedelta, datetime

from linkaform_api import settings, network, utils

from account_settings import *
#from account_utils import get_plant_recipe, select_S4_recipe, set_lot_ready_week
#from stock_utils import *
from lkf_addons.stock_greenhouse.stock_utils import Stock

print('usando greeeeeenhouse....')

# lkf = self.lkf.LKFModules()

if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    if not stock_obj.record_id:
        stock_obj.record_id = stock_obj.object_id() 
    folio = stock_obj.current_record.get('folio')
    stock_obj.inventory_adjustment(folio, stock_obj.current_record)
