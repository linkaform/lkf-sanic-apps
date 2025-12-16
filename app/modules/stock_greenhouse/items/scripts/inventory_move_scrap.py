# -*- coding: utf-8 -*-
import sys, simplejson
from linkaform_api import settings, network, utils

#from account_utils import get_plant_recipe, select_S4_recipe, get_record_greenhouse_inventory
from account_settings import *

from lkf_addons.stock_greenhouse.stock_utils import Stock


if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    if not stock_obj.record_id:
        stock_obj.record_id = stock_obj.object_id()   
    status_code = stock_obj.do_scrap()
    stock_obj.answers[stock_obj.f['inv_scrap_status']] = 'done'
    update_ok = False
    print('res=',status_code)
    print('status_code33333',status_code.get('status_code'))
    if status_code.get('status_code') == 202:
        stock_obj.answers[stock_obj.f['inv_scrap_status']] = 'done'
        print('new answers=', stock_obj.answers)
        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans':  stock_obj.answers,
            'metadata':{"id":stock_obj.record_id}
        }))
    else:
        stock_obj.answers[stock_obj.f['inv_scrap_status']] = 'error'
        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans':  stock_obj.answers,
            'metadata':{"id":stock_obj.record_id}
        }))