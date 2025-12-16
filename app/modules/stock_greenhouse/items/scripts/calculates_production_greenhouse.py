# -*- coding: utf-8 -*-
import sys, simplejson, math
from datetime import timedelta, datetime

from linkaform_api import settings, network, utils

#from account_utils import get_plant_recipe, select_S4_recipe, get_record_greenhouse_inventory
from account_settings import *

from lkf_addons.stock_greenhouse.stock_utils import Stock


if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    if not stock_obj.record_id:
        stock_obj.record_id = stock_obj.object_id()
    current_record = stock_obj.current_record
    # ------------------------------------------------------------------------------
    lkf_api = stock_obj.lkf_api
    if not current_record.get('answers'):
        print('TODO, UPDATE PRODUCT INVENTORY....')
    response = stock_obj.calculates_production_warehouse()
    status_code = 0
    res = {}
    for r in response:
        scode = r.get('status_code')
        if scode > 299:
            res['json'] = r.get('json')
        if scode > status_code:
            status_code = scode
    res['status_code'] = status_code

    if status_code > 299:
        msg_error_app = res.get('json', 'Error de Script favor de reportrar con Admin')
        raise Exception( simplejson.dumps(msg_error_app) )
    else:
        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans': current_record['answers'],
            'metadata':{"id":stock_obj.record_id}
        }))