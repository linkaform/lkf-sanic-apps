# -*- coding: utf-8 -*-
import sys, simplejson
from copy import deepcopy
from math import floor

#from account_utils import unlist, get_inventory_flow, get_record_greenhouse_inventory

from lkf_addons.stock_greenhouse.stock_utils import Stock

from account_settings import *


if __name__ == '__main__':
    # print('enra invmove=', sys.argv)
    # print(f"python { sys.argv[0].split('/')[-1]} '{ sys.argv[1]}' '{ sys.argv[2]}'")
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    if not stock_obj.record_id:
        stock_obj.record_id = stock_obj.object_id() 
    current_record = stock_obj.current_record
    folio =current_record.get('folio')
    # print('current_record',current_record)
    #kwargs = current_record.get('kwargs', current_record.get('properties',{}).get('kwargs', {}))

    dest_folio = stock_obj.move_location(current_record)
    current_record['answers'][stock_obj.f['inv_adjust_status']] =  'done'
    current_record['answers'][stock_obj.f['move_dest_folio']] =  dest_folio
    # sys.stdout.write(simplejson.dumps({
    #     'status': 206,
    #     'metadata':{'editable':False},
    #     'replace_ans': current_record['answers'],
    #     }))
    # sys.stdout.write(simplejson.dumps({
    #     'status': 206,
    #     # 'metadata':{'editable':False},
    #     'merge': {
    #         'answers': current_record['answers']},
    #     }))
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': current_record['answers'],
        'metadata':{"id":stock_obj.record_id}
    }))
