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
    option = data.get("option","")

    data_incidence = data.get("data_incidence",{
        'reporta_incidencia': "",
        'fecha_hora_incidencia':"",
        'ubicacion_incidencia':"",
        'area_incidencia': "",
        'incidencia':"",
        'comentario_incidencia': "",
        'tipo_dano_incidencia': "",
        'dano_incidencia':"",
        'evidencia_incidencia': [],
        'documento_incidencia':[],
        'prioridad_incidencia':"",
        'notificacion_incidencia':"",
        'datos_deposito_incidencia': [],
        'tags':[],
        'categoria':"",
        'sub_categoria':"",
        'incidente':"",

        'nombre_completo_persona_extraviada':"",
        'edad':"",
        'color_piel':"",
        'color_cabello':"",
        'estatura_aproximada':"",
        'descripcion_fisica_vestimenta':"",
        'nombre_completo_responsable':"",
        'parentesco':"",
        'num_doc_identidad':"",
        'telefono':"",
        'info_coincide_con_videos':"",
        'responsable_que_entrega':"",
        'responsable_que_recibe':"",
    
        'afectacion_patrimonial_incidencia':[],
        'personas_involucradas_incidencia': [],
        'acciones_tomadas_incidencia':[],
        'seguimientos_incidencia':[],

        'valor_estimado':"",
        'pertenencias_sustraidas':"",
        'placas':"",
        'tipo':"",
        'marca':"",
        'modelo':"",
        'color':"",
    })
    data_incidence_update = data.get("data_incidence_update",{
        'incidence':'Se detuvierón las escaleras'
    })
    location = data.get("location","")
    area = data.get("area","")
    prioridades = data.get("prioridades",[])
    folio = data.get("folio")
    sub_cat = data.get("sub_cat")
    cat = data.get("cat")
    dateFrom = data.get("dateFrom", "")
    dateTo = data.get("dateTo", "")
    filterDate = data.get("filterDate", "")
    seguimientos = data.get("seguimientos_incidencia", [])
    qr_code = data.get('qr_code')
    template_id = data.get('template_id')
    name_pdf = data.get('name_pdf')
    estatus = data.get('estatus')

    print('option', option)
    if option == 'nueva_incidencia':
        response = acceso_obj.create_incidence(data_incidence)
    elif option == 'get_incidences':
        response = acceso_obj.get_list_incidences(location, area, prioridades= prioridades, dateFrom=dateFrom, dateTo=dateTo, filterDate=filterDate)
    elif option == 'update_incidence':
        response = acceso_obj.update_incidence(data_incidence_update, folio)
    elif option == 'update_incidence_seguimiento':
        response = acceso_obj.update_incidence_seguimiento(folio=folio, incidencia_grupo_seguimiento=seguimientos, estatus=estatus)
    elif option == 'delete_incidence':
        response = acceso_obj.delete_incidence(folio)
    elif option == 'catalogo_area_empleado':
        response = acceso_obj.catalogo_config_area_empleado(bitacora='Incidencias', location=location)
    elif option == 'catalogo_incidencias':
        response = acceso_obj.catalogo_incidencias(cat=cat,sub_cat=sub_cat)
    elif option == 'get_pdf':
        response = acceso_obj.get_pdf(qr_code=qr_code, template_id=template_id)
    else :
        response = {"msg": "Empty"}
    acceso_obj.HttpResponse({"data":response})
