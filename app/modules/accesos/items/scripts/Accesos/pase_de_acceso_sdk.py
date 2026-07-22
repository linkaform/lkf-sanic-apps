#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def crear_pase(params):
    data = params.get("data", {})
    return dispatch("crear_pase", params=data.get('access_pass', {}), method='post', **params)

def update_pass(params):
    data = params.get("data", {})
    return dispatch("update_pass", params={
        **data.get('access_pass', {}),
        'folio': data.get('folio', ''),
    }, method='post', **params)

def update_full_pass(params):
    data = params.get("data", {})
    return dispatch("update_full_pass", params={
        'access_pass': data.get('access_pass', {}),
        'folio': data.get('folio', ''),
        'qr_code': data.get('qr_code', ''),
        'location': data.get('location', ''),
    }, method='post', **params)

def update_active_pass(params):
    data = params.get("data", {})
    return dispatch("update_active_pass", params={
        'folio': data.get('folio', ''),
        'qr_code': data.get('qr_code', ''),
        'update_obj': data.get('update_obj', {}),
    }, method='post', **params)

def catalogos_pase_area(params):
    data = params.get("data", {})
    return dispatch("catalogos_pase_area", params={
        'location_name': data.get('location', ''),
    }, method='get', **params)

def catalogos_pase_location(params):
    return dispatch("catalogos_pase_location", params={}, method='get', **params)

def catalogos_pase_no_jwt(params):
    data = params.get("data", {})
    return dispatch("catalogos_pase_no_jwt", params={
        'qr_code': data.get('qr_code', ''),
    }, method='get', **params)

def enviar_msj(params):
    data = params.get("data", {})
    return dispatch("pase_enviar_msj", params={
        'folio': data.get('folio', ''),
    }, method='post', **params)

def enviar_correo(params):
    data = params.get("data", {})
    return dispatch("pase_enviar_correo", params={
        'folio': data.get('folio', ''),
        'envio': data.get('envio', []),
    }, method='post', **params)

def catalago_vehiculo(params):
    data = params.get("data", {})
    return dispatch("vehiculo_tipo", params={
        'tipo': data.get('tipo', ''),
        'marca': data.get('marca', ''),
    }, method='get', **params)

def catalago_estados(params):
    return dispatch("catalogo_estados", params={}, method='get', **params)

def get_pass(params):
    data = params.get("data", {})
    return dispatch("get_pass", params={
        'qr_code': data.get('qr_code', ''),
    }, method='get', **params)

def get_my_pases(params):
    data = params.get("data", {})
    return dispatch("get_my_pases", params={
        'tab_status': data.get('tab_status', ''),
        'limit': data.get('limit', 25),
        'skip': data.get('skip', 0),
        'search_name': data.get('search_name'),
        'location': data.get('location', ''),
        'dynamic_filters': data.get('dynamic_filters', {}),
        'dateFrom': data.get('dateFrom', ''),
        'dateTo': data.get('dateTo', ''),
        'filterDate': data.get('filterDate', ''),
        'locations': data.get('locations', []),
    }, method='post', **params)

def get_pdf(params):
    data = params.get("data", {})
    return dispatch("get_pdf", params={
        'qr_code': data.get('qr_code', ''),
    }, method='get', **params)

def get_user_contacts(params):
    return dispatch("get_user_contacts", params={}, method='get', **params)

def get_config_modulo_seguridad(params):
    data = params.get("data", {})
    return dispatch("get_config_modulo_seguridad", params={
        'location': data.get('location', ''),
    }, method='get', **params)

def get_areas_by_locations(params):
    data = params.get("data", {})
    # legacy solo lee 'locations' (lista) para esta opcion, ignora 'location'
    # (singular); si el caller no manda 'locations' explicitamente, legacy
    # regresa {} (sin la key 'areas_by_location'). Replicamos ese shape.
    return dispatch("get_areas_by_locations", params={
        'locations': data.get('locations', []),
    }, method='get', **params)

def extends_date_of_pass(params):
    data = params.get("data", {})
    return dispatch("extends_date_of_pass", params={
        'qr_code': data.get('qr_code', ''),
        'update_obj': data.get('update_obj', {}),
    }, method='post', **params)


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
    "catalago_estados": catalago_estados,
    "get_pass": get_pass,
    "get_my_pases": get_my_pases,
    "get_pdf": get_pdf,
    "get_user_contacts": get_user_contacts,
    "get_config_modulo_seguridad": get_config_modulo_seguridad,
    "get_areas_by_locations": get_areas_by_locations,
    "extends_date_of_pass": extends_date_of_pass,
}
print('aaaaaaa')
if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option")
    print('..... arranca script pase_de_acceso')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
