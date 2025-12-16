import sys, simplejson
from linkaform_api import settings, network, utils
from account_settings import *

from accesos_utils import Accesos

if __name__ == "__main__":
    #acceso_obj = Accesos(settings, sys_argv=sys.argv, use_api=True) 
    acceso_obj = Accesos(settings, sys_argv=sys.argv)
    acceso_obj.console_run()
    #-FILTROS
    all_data = simplejson.loads(sys.argv[2])
    data = all_data.get("data", {})
    option = data.get("option",'')
    #-CONFIGURATION
    if option == 'catalog_brands':
        response = acceso_obj.get_catalog_brands()
        sys.stdout.write(simplejson.dumps({"data": response}))
    else :
        sys.stdout.write(simplejson.dumps({"msg": "Empty"}))
