#-*- coding: utf-8 -*-
import simplejson, sys
from linkaform_api import settings

from gh_stock_report import Reports

from account_settings import *

if __name__ == "__main__":
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    data = report_obj.data.get('data')
    filters = data.get('filters',[])
    report_obj.get_report_filters(filters)
    sys.stdout.write(simplejson.dumps(report_obj.json))
