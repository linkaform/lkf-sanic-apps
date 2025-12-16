# -*- coding: utf-8 -*-
import sys, simplejson
from datetime import datetime, timedelta

#from account_utils import get_inventory_flow
from linkaform_api import network, utils
from lkf_addons.stock_greenhouse.stock_utils import Stock

from account_settings import *


if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    current_record = stock_obj.current_record
    if not stock_obj.record_id:
        stock_obj.record_id = stock_obj.object_id()   
    answers = stock_obj.gradings_validations()

    current_record['answers'].update(answers)
    stock_obj.update_log_grading()
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': current_record['answers'],
        'metadata':{"id":stock_obj.record_id}
    }))



