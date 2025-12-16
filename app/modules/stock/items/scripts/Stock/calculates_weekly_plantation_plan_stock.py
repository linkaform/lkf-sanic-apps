# -*- coding: utf-8 -*-
import sys, simplejson, math
from datetime import datetime, timedelta

from linkaform_api import settings, utils
#from account_utils import unlist
from account_settings import *

from stock_utils import Stock


if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    current_record = stock_obj.current_record
    stock_obj.get_plant_prodctivity(stock_obj.answers)
    print('answers el serlf', stock_obj.answers)
    #current_record['answers']['60a45aacaebd732a38f908bd'] = rfc
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': stock_obj.answers
    }))
    #stock_obj.calculations(current_record)
