# -*- coding: utf-8 -*-
import sys, simplejson
from datetime import datetime
from copy import deepcopy

from expense_utils import Expenses

from account_settings import *


if __name__ == '__main__':
    print(sys.argv )
    expense_obj = Expenses(settings, sys_argv=sys.argv)
    expense_obj.create_expense_authorization(folio=expense_obj.folio)
