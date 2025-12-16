# -*- coding: utf-8 -*-
import sys, simplejson
from datetime import datetime, timedelta
from bson import errors, ObjectId

from lkf_addons.base.app import Schedule

from account_settings import *

 
if __name__ == "__main__":
    # print(sys.argv)
    schedule_obj = Schedule(settings, sys_argv=sys.argv, use_api=True)
    schedule_obj.console_run()
    lkf_api = schedule_obj.lkf_api
    res = schedule_obj.schedule_task()
    data = res.get('data')
    if res.get('status_code') == 0:
        print('Ningun cambio')
    elif res.get('status_code') == 200:
        if res.get('deleted'):
            schedule_obj.answers['abcde00010000000a0000000'] = 'eliminado'
        else:
            schedule_obj.answers['abcde0001000000000000000'] = data.get('dag_id')
            schedule_obj.answers.update(schedule_obj.get_dag_dates(data))
            if res.get('is_paused') == True:
                schedule_obj.answers['abcde00010000000a0000000'] = 'pausado'
            else:
                schedule_obj.answers['abcde00010000000a0000000'] = 'corriendo'

        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans': schedule_obj.answers,
        }))
    else:
        msg_error_app = "Something went wrong!!!"
        if res.get('json',{}).get('error') or res.get('status_code') == 400:
            if res.get('json',{}).get('error'):
                msg_error_app = res['json']['error']
            else:
                msg_error_app = res['json'].get('message','Something went wrong!!!')
        else:
            msg_error_app = {
                "error":{"msg": [msg_error_app], "label": "Cron Id", "error":[msg_error_app]},
            }
        raise Exception(simplejson.dumps(msg_error_app))