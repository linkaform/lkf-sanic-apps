# -*- coding: utf-8 -*-
import sys, simplejson
from datetime import datetime
from copy import deepcopy

from expense_utils import Expenses
#from linkaform_api import utils, network, lkf_models
#from expense_utils import Expenses

from account_settings import *


if __name__ == '__main__':
    print(sys.argv )
    exp_obj = Expenses(settings)
    exp_obj.update_expense_values()
    exp_obj.sync_solicitud()

    sys.stdout.write(simplejson.dumps({
                'status': 101,
                'merge':{
                    'answers': exp_obj.answers,
                    'replace': True
                    }
                # 'replace_ans': current_record['answers']
            }))

