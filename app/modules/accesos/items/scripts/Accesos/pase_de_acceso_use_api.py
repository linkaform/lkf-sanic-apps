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
    location = data.get("location",'')
    locations = data.get("locations",[])
    folio = data.get("folio",'')
    access_pass = data.get("access_pass",{})
    data_msj=data.get("data_msj", {})
    data_cel_msj=data.get("data_cel_msj", {})
    user_id= data.get("user_id")
    marca = data.get('marca',"")
    tipo = data.get('tipo',"")
    option = data.get("option","")
    qr_code=data.get("qr_code")
    tab_status=data.get("tab_status")
    pre_sms = data.get("enviar_pre_sms",{})
    update_obj = data.get("update_obj",{})
    envio = data.get("envio",[])
    account_id = data.get("account_id", "")
    template_id= data.get("template_id")
    
    if option == 'assets_access_pass':
        response = acceso_obj.get_shift_data(booth_location=location, booth_area=area)
    elif option == 'create_access_pass' or option == 'crear_pase':
        response = acceso_obj.create_access_pass(location, access_pass)
        folio_msj = response.get('json', {}).get('id', '')
    elif option == 'update_pass':
        response = acceso_obj.update_pass(access_pass,folio)
    elif option == 'update_full_pass':
        response = acceso_obj.update_full_pass(access_pass,folio, qr_code, location)
    elif option == 'update_active_pass':
        response = acceso_obj.update_active_pass(folio, qr_code, update_obj)
    elif option == 'catalogos_pase_area':
        response = acceso_obj.catalogos_pase_area(location)
    elif option == 'catalogos_pase_location':
        response = acceso_obj.catalogos_pase_location()
    elif option == 'catalogos_pase_no_jwt':
        response = acceso_obj.catalagos_pase_no_jwt(qr_code)
    elif option == 'enviar_msj':
        response = acceso_obj.create_enviar_msj_pase(folio=folio)
    elif option == 'enviar_correo':
        response = acceso_obj.create_enviar_correo(folio=folio, envio=envio)
    elif option == 'catalago_vehiculo':
        if tipo and marca:
            response = acceso_obj.vehiculo_modelo(tipo, marca)
        elif tipo:
            response = acceso_obj.vehiculo_marca(tipo)
        else:
            response = acceso_obj.vehiculo_tipo()
    elif option == 'catalago_estados':
        response = acceso_obj.catalogo_estados()
    elif option == 'get_pass':
        response = acceso_obj.get_pass_custom(qr_code)
    elif option == 'get_my_pases':
        response = acceso_obj.get_my_pases(tab_status=tab_status)
    elif option == 'get_pdf':
        if account_id == 7742:
            response = acceso_obj.get_pdf(qr_code, template_id=553)
        else:
            response = acceso_obj.get_pdf(qr_code)
    elif option == 'get_pdf_incidencias':
            response = acceso_obj.get_pdf(qr_code, template_id=template_id)
    elif option == 'get_user_contacts':
        response = acceso_obj.get_user_contacts()
    elif option == 'get_config_modulo_seguridad':
        response = acceso_obj.get_config_modulo_seguridad(ubicaciones=locations)
    else :
        response = {"msg": "Empty"}
    acceso_obj.HttpResponse({"data":response})