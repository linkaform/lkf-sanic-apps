# -*- coding: utf-8 -*-
import sys, simplejson

from lab_stock_utils import Stock

from account_settings import *

if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    if not stock_obj.record_id:
        stock_obj.record_id = stock_obj.object_id()
    stock_obj.console_run()
    res = stock_obj.do_scrap()
    print('res',res)

    if res.get('status_code') == 202:
        stock_obj.answers[stock_obj.f['inv_scrap_status']] = 'done'

        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans':  stock_obj.answers,
            'metadata':{"id":stock_obj.record_id}
        }))

