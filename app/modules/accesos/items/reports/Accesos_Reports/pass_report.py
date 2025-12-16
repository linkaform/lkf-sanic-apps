# -*- coding: utf-8 -*-
import sys, simplejson, math
import json
import math
from datetime import timedelta, datetime

from linkaform_api import settings, base
from account_settings import *

print('inicia....')
#Se agrega path para que obtenga el archivo de Stock de este modulo
sys.path.append('/srv/scripts/addons/modules/accesos/items/scripts/Accesos')
from accesos_utils import Accesos

if __name__ == "__main__":
    acc_obj = Accesos(settings, sys_argv=sys.argv, use_api=True)
    acc_obj.console_run()

    data = acc_obj.data
    data = data.get('data',[])
    area = data.get('area','get_report')
    location = data.get('location','Planta Monterrey')
    page = data.get('page','Turnos')
    print("data//////////////////", data)

    response = acc_obj.get_page_stats(booth_area=area, location=location, page=page)
    print('response////////', response)
    # acc_obj.HttpResponse({"data":response})

