#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from linkaform_api import settings
from account_settings import *
from middleware.auth import dispatch_with_api_key


def _api_key(data):
    # El cliente puede indicar su propio api_key por llamada; si no, se usa
    # el configurado por default para la cuenta (equivalente a use_api=True).
    return data.get('api_key') or config.get('APIKEY')


def crear_pase(params):
    data = params.get("data", {})
    return dispatch_with_api_key("crear_pase", _api_key(data), params=data.get('access_pass', {}), method='post', **params)

def update_pass(params):
    data = params.get("data", {})
    return dispatch_with_api_key("update_pass", _api_key(data), params={
        **data.get('access_pass', {}),
        'folio': data.get('folio', ''),
    }, method='post', **params)

def update_full_pass(params):
    data = params.get("data", {})
    return dispatch_with_api_key("update_full_pass", _api_key(data), params={
        'access_pass': data.get('access_pass', {}),
        'folio': data.get('folio', ''),
        'qr_code': data.get('qr_code', ''),
        'location': data.get('location', ''),
    }, method='post', **params)

def update_active_pass(params):
    data = params.get("data", {})
    return dispatch_with_api_key("update_active_pass", _api_key(data), params={
        'folio': data.get('folio', ''),
        'qr_code': data.get('qr_code', ''),
        'update_obj': data.get('update_obj', {}),
    }, method='post', **params)

def catalogos_pase_area(params):
    data = params.get("data", {})
    return dispatch_with_api_key("catalogos_pase_area", _api_key(data), params={
        'location_name': data.get('location', ''),
    }, method='get', **params)

def catalogos_pase_location(params):
    data = params.get("data", {})
    return dispatch_with_api_key("catalogos_pase_location", _api_key(data), params={}, method='get', **params)

def catalogos_pase_no_jwt(params):
    data = params.get("data", {})
    return dispatch_with_api_key("catalogos_pase_no_jwt", _api_key(data), params={
        'qr_code': data.get('qr_code', ''),
    }, method='get', **params)

def enviar_msj(params):
    data = params.get("data", {})
    return dispatch_with_api_key("pase_enviar_msj", _api_key(data), params={
        'folio': data.get('folio', ''),
    }, method='post', **params)

def enviar_correo(params):
    data = params.get("data", {})
    return dispatch_with_api_key("pase_enviar_correo", _api_key(data), params={
        'folio': data.get('folio', ''),
        'envio': data.get('envio', []),
    }, method='post', **params)

def catalago_vehiculo(params):
    data = params.get("data", {})
    return dispatch_with_api_key("catalogo_vehiculos_pase", _api_key(data), params={}, method='get', **params)

def catalago_tipo_equipo(params):
    data = params.get("data", {})
    return dispatch_with_api_key("catalogo_tipo_equipo", _api_key(data), params={}, method='get', **params)

def catalago_estados(params):
    data = params.get("data", {})
    return dispatch_with_api_key("catalogo_estados", _api_key(data), params={}, method='get', **params)

def get_pass(params):
    data = params.get("data", {})
    return dispatch_with_api_key("get_pass", _api_key(data), params={
        'qr_code': data.get('qr_code', ''),
    }, method='get', **params)

def get_my_pases(params):
    data = params.get("data", {})
    return dispatch_with_api_key("get_my_pases", _api_key(data), params={
        'tab_status': data.get('tab_status', ''),
    }, method='post', **params)

def get_pdf(params):
    data = params.get("data", {})
    account_id = data.get('account_id', '')
    template_id = 553 if account_id == 7742 else None
    call_params = {'qr_code': data.get('qr_code', '')}
    if template_id:
        call_params['template_id'] = template_id
    return dispatch_with_api_key("get_pdf", _api_key(data), params=call_params, method='get', **params)

def get_pdf_incidencias(params):
    data = params.get("data", {})
    return dispatch_with_api_key("get_pdf", _api_key(data), params={
        'qr_code': data.get('qr_code', ''),
        'template_id': data.get('template_id', ''),
    }, method='get', **params)

def get_user_contacts(params):
    data = params.get("data", {})
    return dispatch_with_api_key("get_user_contacts", _api_key(data), params={}, method='get', **params)

def get_config_modulo_seguridad(params):
    data = params.get("data", {})
    return dispatch_with_api_key("get_config_modulo_seguridad", _api_key(data), params={
        'locations': data.get('locations', []),
    }, method='get', **params)

def get_pass_img(params):
    data = params.get("data", {})
    return dispatch_with_api_key("get_pass_img", _api_key(data), params={
        'qr_code': data.get('qr_code', ''),
    }, method='get', **params)


DISPATCHER = {
    "create_access_pass": crear_pase,
    "crear_pase": crear_pase,
    "update_pass": update_pass,
    "update_full_pass": update_full_pass,
    "update_active_pass": update_active_pass,
    "catalogos_pase_area": catalogos_pase_area,
    "catalogos_pase_location": catalogos_pase_location,
    "catalogos_pase_no_jwt": catalogos_pase_no_jwt,
    "enviar_msj": enviar_msj,
    "enviar_correo": enviar_correo,
    "catalago_vehiculo": catalago_vehiculo,
    "catalago_tipo_equipo": catalago_tipo_equipo,
    "catalago_estados": catalago_estados,
    "get_pass": get_pass,
    "get_my_pases": get_my_pases,
    "get_pdf": get_pdf,
    "get_pdf_incidencias": get_pdf_incidencias,
    "get_user_contacts": get_user_contacts,
    "get_config_modulo_seguridad": get_config_modulo_seguridad,
    "get_pass_img": get_pass_img,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option")
    print('..... arranca script pase_de_acceso_use_api')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
