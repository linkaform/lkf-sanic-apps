# -*- coding: utf-8 -*-
import sys, simplejson, math
from datetime import timedelta, datetime

from linkaform_api import settings
from account_settings import *

from gh_stock_report import Reports

    

if __name__ == '__main__':
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    answers = {"61ef32bcdf0ec2ba73dec33c":{"61ef32bcdf0ec2ba73dec33d":"LNAFP"},"620a9ee0a449b98114f61d77":202350}
    report_obj.data = {'data':
        {
        'product_code': answers.get(report_obj.CATALOG_PRODUCT_RECIPE_OBJ_ID,{} ).get(report_obj.f['product_code']),
        'lot_number': answers.get(report_obj.f.get('product_lot'))
        }
    }
    data, actuals = report_obj.get_product_kardex()
    print(">>>>>>")
    res = {'response':data}
    sys.stdout.write(simplejson.dumps(res))

