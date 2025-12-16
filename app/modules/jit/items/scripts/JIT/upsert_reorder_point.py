# -*- coding: utf-8 -*-
import sys, simplejson, copy

from jit_utils import JIT

from account_settings import *


if __name__ == '__main__':
    jit_obj = JIT(settings, sys_argv=sys.argv, use_api=True)
    jit_obj.console_run()
    if jit_obj.current_record:
        response = jit_obj.upsert_reorder_point()
    else:
        response = jit_obj.upsert_reorder_point()
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': jit_obj.answers,
        }))
