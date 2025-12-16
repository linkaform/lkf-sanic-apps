# -*- coding: utf-8 -*-
import sys, simplejson
from bson import ObjectId

from linkaform_api import settings, utils

from account_settings import *

from lkf_addons.stock_greenhouse.stock_utils import Stock


if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    print(stock_obj.console_run())
    current_record = stock_obj.current_record
    record_id = current_record.get('_id').get('$oid')
    update_res = stock_obj.cr.update_one({'_id':ObjectId(record_id)}, {'$set': {'editable':False}})
