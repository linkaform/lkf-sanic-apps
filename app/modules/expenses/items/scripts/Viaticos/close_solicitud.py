# -*- coding: utf-8 -*-
import sys, simplejson
#from lkf_addons.expenses.expense_utils import Expenses
from expense_utils import Expenses
from account_settings import *

if __name__ == '__main__':
    expense_obj = Expenses(settings, sys_argv=sys.argv, use_api=True)
    current_record = expense_obj.current_record
    print('.... .... form_id= {} folio= {}'.format( current_record['form_id'], current_record['folio'] ))
    expense_obj.do_solicitud_close( current_record['form_id'], current_record['folio'], force_close=True )