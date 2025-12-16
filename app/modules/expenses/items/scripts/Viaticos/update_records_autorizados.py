# -*- coding: utf-8 -*-
import sys, simplejson

from lkf_addons.expenses.expense_utils import Expenses

from account_settings import *

class LocalExpenses(Expenses):


    def update_autorization_records(self, answers):
        answers['test'] = 'update....'
        result = super().update_autorization_records(answers)
        return result
        # result = expense_obj.update_autorization_records(answers)


if __name__ == '__main__':
    # expense_obj = Expenses(settings)
    local_exp  = LocalExpenses(settings, sys_argv=sys.argv)
    local_exp.console_run()
    answers = local_exp.current_record['answers']
    local_exp.current_record['answers'] = local_exp.update_autorization_records(answers)
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': local_exp.current_record['answers']
    }))