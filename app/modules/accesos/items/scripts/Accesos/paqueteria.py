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

    data_paquete = data.get("data_paquete",{
        'ubicacion_paqueteria':'',
        'area_paqueteria':'',
        'fotografia_paqueteria': [{
            'file_url':'https://f001.backblazeb2.com/file/app-linkaform/public-client-126/71202/60b81349bde5588acca320e1/65dd1061092cd19498857933.jpg',
            'file_name':'ejemploidentificacion.jpg'
        }],
        'descripcion_paqueteria':'',
        'quien_recibe_paqueteria':"",
        'guardado_en_paqueteria':'',
        'fecha_recibido_paqueteria':"",
        'fecha_entregado_paqueteria': '',
        'estatus_paqueteria':"",
        'entregado_a_paqueteria':"",
        'proveedor':"",
    })
    data_paquete_actualizar = data.get("data_paquete_actualizar",{
        'status_perdido':'entregado',
        'date_entrega_perdido':'2024-07-09 19:43:01'
    })
    location = data.get("location")
    status = data.get("status","")
    area = data.get("area")
    folio = data.get("folio")
    tipo = data.get("tipo","")
    
    dateFrom = data.get("dateFrom", "")
    dateTo = data.get("dateTo", "")
    filterDate = data.get("filterDate", "")


    if option == 'nuevo_paquete':
        response = acceso_obj.create_paquete(data_paquete)
    elif option == 'get_paquetes':
        response = acceso_obj.get_paquetes(location, area, status, dateFrom=dateFrom, dateTo=dateTo, filterDate=filterDate)
    elif option == 'actualizar_paquete':
        response = acceso_obj.update_paquete(data_paquete_actualizar, folio)
    elif option == 'eliminar_paquete':
        response = acceso_obj.delete_paquete(folio)
    elif option == 'get_catalogo_paquetes':
        response = acceso_obj.get_catalogo_paquetes()
    else :
        response = {"msg": "Empty"}
    acceso_obj.HttpResponse({"data":response})