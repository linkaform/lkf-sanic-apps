# -*- coding: utf-8 -*-
import sys, simplejson
from bson import ObjectId

from lab_stock_utils import Stock

from account_settings import *

if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    print('stock_obj record_id', stock_obj.record_id)
    if not stock_obj.record_id:
        stock_obj.record_id = stock_obj.object_id()
        print('NOOOOT ,....stock_obj record_id', stock_obj.record_id)
    stock_obj.move_out_multi_location()
    stock_obj.answers[stock_obj.f['move_status']] =  'done'
    stock_obj.answers[stock_obj.f['inv_adjust_status']] =  'done'
    print('el new id...', stock_obj.record_id)
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': stock_obj.answers,
        'metadata':{"id":stock_obj.record_id}
        }))
