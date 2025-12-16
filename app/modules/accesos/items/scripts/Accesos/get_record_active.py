import sys, simplejson
from datetime import datetime

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
    location = data.get("location",'')
    curp = data.get("curp",'')
    data_item = data.get("dataItem",[])
    data_gafete = data.get("dataGafete",[])
    data_vehicule = data.get("dataVehicule",[])
    #-CONFIGURATION
    #-EXECUTION
    if option !='':
        if option == 'query_alerts':
            response = acceso_obj.get_alerts('planta1')
            sys.stdout.write(simplejson.dumps({"json": response}))
        elif option == 'get_users_information':
            #----Query Data record
            response_movement = acceso_obj.get_user_movement(curp)
            response_bitacora = acceso_obj.get_user_bitacora(curp)
            response_user = acceso_obj.get_user_information(curp)
            sys.stdout.write(simplejson.dumps({"json":{'data_user':response_user,'movement':response_movement,'bitacora':response_bitacora}}))
        elif option == 'set_movement_users':
            response_movement = acceso_obj.get_user_movement(curp)
            if response_movement.get('type','') == 'in':
                #----Add  record
                response_user = acceso_obj.get_user_information(curp)
                response_status = acceso_obj.set_add_record(response_user, data_item, data_vehicule,location)
                sys.stdout.write(simplejson.dumps({"json": response_status}))
            elif response_movement.get('type','') == 'out':
                #----Update  record
                response_status = acceso_obj.set_update_record(response_movement)
                sys.stdout.write(simplejson.dumps({"json": response_status}))
        elif option == 'get_list_users':
            #----Update  record
            get_data_list = acceso_obj.get_list_users(location)
            sys.stdout.write(simplejson.dumps({"json": get_data_list}))
        elif option == 'set_gafete_user':
            response_status = acceso_obj.set_add_record_gafete(curp, location, data_gafete)
            sys.stdout.write(simplejson.dumps({"json": ''}))
    else:
        sys.stdout.write(simplejson.dumps({"msg": "Failed"}))
