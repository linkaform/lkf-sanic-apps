# coding: utf-8
import sys, simplejson
from linkaform_api import settings
from account_settings import *

from accesos_utils import Accesos

class Accesos(Accesos):
    pass
    
if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv, use_api=True)
    acceso_obj.console_run()
    #-FILTROS
    data = acceso_obj.data.get('data',{})
    option = data.get("option",'')
    area = data.get('area','')
    location = data.get('location','')
    page = data.get('page','')
    print("data//////////////////", data)
    
    if option == 'get_stats':
        response = acceso_obj.get_page_stats(booth_area=area, location=location, page=page)
    else :
        response = {"msg": "Empty"}
    acceso_obj.HttpResponse({"data":response})