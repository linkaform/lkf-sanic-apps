# -*- coding: utf-8 -*-
import sys, simplejson, copy

from jit_utils import JIT

from account_settings import *


if __name__ == '__main__':
    jit_obj = JIT(settings, sys_argv=sys.argv, use_api=True)
    jit_obj.console_run()

    response = jit_obj.balance_warehouse()
    print('TODO: revisar si un create no estuvo bien y ponerlo en error o algo')
    jit_obj.answers[jit_obj.f['status']] =  'done'
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': jit_obj.answers,
        }))
