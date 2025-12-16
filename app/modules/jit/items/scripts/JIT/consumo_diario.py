# -*- coding: utf-8 -*-
import sys, simplejson, copy

from jit_utils import JIT

from account_settings import *


if __name__ == '__main__':
    print('sys=', sys.argv)
    jit_obj = JIT(settings, sys_argv=sys.argv, use_api=True)
    jit_obj.console_run()
    response = jit_obj.ave_daily_demand()
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': jit_obj.answers,
        }))
