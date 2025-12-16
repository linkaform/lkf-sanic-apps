# coding: utf-8
import sys, simplejson
from linkaform_api import settings
from account_settings import *

from accesos_utils import Accesos

class Accesos(Accesos):
    pass



if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv)
    acceso_obj.console_run()
    #-FILTROS
    argument_option = acceso_obj.data.get('option')

    data = acceso_obj.data.get('data',{})
    option = data.get("option",'')
    data_gafete = data.get("data_gafete",{
        'status_gafete':'asignar_gafete',
        'ubicacion_gafete':'Planta Durango',
        'caseta_gafete':'Caseta Vigilancia Av 16',
        'visita_gafete':'Leticia Hernández Hernández',
        'gafete_id':'00001',
        'documento_gafete':['INE'],
    })
    location = data.get("location")
    area = data.get("area")
    tipo_locker = data.get("tipo_locker")
    status = data.get("status")
    limit = data.get("limit",1000)
    skip = data.get("skip",0)
    folio = data.get("folio",'512-10')
    gafete_id= data.get("gafete_id" , data.get('id_gafete'))
    locker_id= data.get("locker_id" , data.get('id_locker'))
    tipo_locker= data.get("tipo_locker")
    tipo_movimiento= data.get("tipo_movimiento")
    print('argument_option=', argument_option)
    print('option=', option)
    #-FUNCTIONS
    #option = 'new_badge';
    #option = 'get_badge';
    #option = 'deliver_badge';
    if argument_option == 'update_status':
        response = acceso_obj.update_gafet_status()
    elif option == 'new_badge':
        response = acceso_obj.create_badge(data_gafete)
    elif option == 'get_gafetes':
        response = acceso_obj.get_gafetes(status=status, location=location, area=area, gafete_id=gafete_id,limit=limit, skip=skip)
    elif option == 'get_lockers':
        response = acceso_obj.get_lockers(
            status=status, 
            location=location, 
            area=area, 
            tipo_locker=tipo_locker, 
            locker_id=locker_id, 
            limit=limit, 
            skip=skip)
    elif option == 'deliver_badge':
        response = acceso_obj.deliver_badge(folio)
    else :
        response = {"msg": "Empty"}
    acceso_obj.HttpResponse({"data":response})