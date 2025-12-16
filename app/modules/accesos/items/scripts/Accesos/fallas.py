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
    data = acceso_obj.data.get('data',{})
    option = data.get("option",'')

    data_failure = data.get("data_failure",{
        'falla_estatus': '',
        'falla_fecha_hora': '',
        'falla_reporta_nombre': '',
        'falla_ubicacion': '',
        'falla_caseta':'',
        'falla':'',
        'falla_objeto_afectado':'',
        'falla_comentarios':'',
        'falla_evidencia':'',
        'falla_documento':'',
        'falla_responsable_solucionar_nombre':'',
    })
    data_failure_update = data.get("data_failure_update",{
        'falla_status':'resuelto',
    })

    location = data.get("location",'')
    area = data.get("area",'')
    folio = data.get("folio",'')
    falla_grupo_seguimiento = data.get("falla_grupo_seguimiento",'')
    status = data.get("status",'')
    tipo = data.get("tipo",'')

    dateFrom = data.get("dateFrom", "")
    dateTo = data.get("dateTo", "")
    filterDate = data.get("filterDate", "")

    print('option', option)
    if option == 'new_failure':
        response = acceso_obj.create_failure(data_failure)
    elif option == 'get_failure_by_folio':
        response = acceso_obj.get_list_fallas(location, area, folio=folio)
    elif option == 'get_failures':
        response = acceso_obj.get_list_fallas(location, area, status=status, dateFrom=dateFrom, dateTo=dateTo, filterDate=filterDate)
    elif option == 'get_fallas':
        response = acceso_obj.get_list_fallas(location, area, status=status, dateFrom=dateFrom, dateTo=dateTo, filterDate=filterDate)
    elif option == 'update_failure':
        response = acceso_obj.update_failure(data_failure_update, folio)
    elif option == 'update_failure_seguimiento':
        response = acceso_obj.update_failure_seguimiento(location, area, status=status, folio=folio, falla_grupo_seguimiento=falla_grupo_seguimiento)
    elif option == 'delete_failure':
        response = acceso_obj.delete_failure(folio)
    elif option =='catalogo_area_empleado_apoyo':
        response = acceso_obj.catalogo_config_area_empleado_apoyo()
    elif option == 'catalogo_fallas':
        if tipo:
            response = acceso_obj.catalogo_falla(tipo)
        else:
            response = acceso_obj.catalogo_falla()
    elif option == 'catalogo_area_empleado_apoyo':
            response = acceso_obj.catalogo_config_area_empleado_apoyo()
    else :
        response = {"msg": "Empty"}
    acceso_obj.HttpResponse({"data":response})