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

    data_article = data.get("data_article",{
        'guard_perdido':'Pedro Cervantes',
        'estatus_perdido':'pendiente',
        'foto_perdido': [{
            'file_url':'https://f001.backblazeb2.com/file/app-linkaform/public-client-126/71202/60b81349bde5588acca320e1/65dd1061092cd19498857933.jpg',
            'file_name':'ejemploidentificacion.jpg'
        }],
        'date_hallazgo_perdido':'2024-07-08 19:43:01',
        'ubicacion_perdido':"Planta Monterrey",
        'area_perdido':'Recursos eléctricos',
        'comentario_perdido':"soy un comentario",
        'tipo_articulo_perdido': 'Recursos eléctricos',
        'articulo_seleccion':"Dron",
        'articulo_perdido':"",
        'color_perdido':"Blanco",
        'descripcion':"dron blanco",
        'quien_entrega':"Interno",
        'quien_entrega_interno':"",
        'quien_entrega_externo':"nombre de persona",
        'locker_perdido':'L2',
    })
    data_article_update = data.get("data_article_update",{
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

    if option == 'nuevo_articulo':
        response = acceso_obj.create_article_lost(data_article)
    elif option == 'get_articles':
        response = acceso_obj.get_list_article_lost(location, area,status, dateFrom=dateFrom, dateTo=dateTo, filterDate=filterDate)
    elif option == 'update_article':
        response = acceso_obj.update_article_lost(data_article_update, folio)
    elif option == 'delete_article':
        response = acceso_obj.delete_article_lost(folio)
    elif option == 'catalogo_tipo_articulo':
        if tipo:
            response = acceso_obj.catalogo_tipo_articulo(tipo)
        else:
            response = acceso_obj.catalogo_tipo_articulo()
    elif option == 'catalogo_area_empleado':
        response = acceso_obj.catalogo_config_area_empleado(bitacora='Objetos Perdidos')
    else :
        response = {"msg": "Empty"}
    acceso_obj.HttpResponse({"data":response})