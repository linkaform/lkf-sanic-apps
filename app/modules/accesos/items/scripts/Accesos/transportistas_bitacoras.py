#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from linkaform_api import settings
from account_settings import *
from middleware.auth import dispatch_with_api_key

# Subconjunto de transportistas.py — comparte las mismas rutas del servicio,
# sin las opciones de bitacora/inspecciones (ver transportistas.py para esas).


def create_pass_transportista(api_key, params, payload):
    return dispatch_with_api_key("create_pass_transportista", api_key, params={'payload': payload}, method='post', **params)

def generate_submit_token_transportista(api_key, params, record_id):
    return dispatch_with_api_key("generate_submit_token_transportista", api_key, params={'record_id': record_id}, method='post', **params)

def get_andenes(api_key, params):
    return dispatch_with_api_key("get_andenes", api_key, params={}, method='get', **params)

def get_horarios_data(api_key, params, dia):
    return dispatch_with_api_key("get_horarios_data", api_key, params={'dia': dia}, method='get', **params)

def get_pass_transportista(api_key, params, record_id, token):
    return dispatch_with_api_key("get_pass_transportista", api_key, params={'record_id': record_id, 'token': token}, method='get', **params)

def get_users_data(api_key, params, locations):
    return dispatch_with_api_key("get_users_data_transportista", api_key, params={'locations': locations}, method='get', **params)

def get_location_data(api_key, params, location):
    return dispatch_with_api_key("get_location_data", api_key, params={'location': location}, method='get', **params)

def get_proveedores_transportista(api_key, params):
    return dispatch_with_api_key("get_proveedores_transportista", api_key, params={}, method='get', **params)

def validate_token(api_key, params, record_id, token):
    return dispatch_with_api_key("validate_token_transportista", api_key, params={'record_id': record_id, 'token': token}, method='get', **params)

def update_information_transportista(api_key, params, payload):
    return dispatch_with_api_key("update_information_transportista", api_key, params={'payload': payload}, method='post', **params)


if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get('data', {})
    api_key = data.get('api_key') or config.get('APIKEY')
    option = data.get("option", '')
    payload = data.get("payload", {})
    record_id = data.get("record_id", None)
    token = data.get("token", None)
    locations = data.get("locations", None)
    location = data.get("location", None)
    print('..... arranca script transportistas_bitacoras')

    dispatcher = {
        "create_pass_transportista": lambda: create_pass_transportista(api_key, params, payload),
        "generate_submit_token_transportista": lambda: generate_submit_token_transportista(api_key, params, record_id),
        "get_andenes": lambda: get_andenes(api_key, params),
        "get_horarios_data": lambda: get_horarios_data(api_key, params, data.get('dia')),
        "get_pass_transportista": lambda: get_pass_transportista(api_key, params, record_id, token),
        "get_users_data": lambda: get_users_data(api_key, params, locations),
        "get_location_data": lambda: get_location_data(api_key, params, location),
        "get_proveedores_transportista": lambda: get_proveedores_transportista(api_key, params),
        "validate_token": lambda: validate_token(api_key, params, record_id, token),
        "update_information_transportista": lambda: update_information_transportista(api_key, params, payload),
    }

    action = dispatcher.get(option)
    if not action:
        response_json = {"error": "Opción no válida"}
        sys.stdout.write(simplejson.dumps(response_json))
    else:
        response = action()
        sys.stdout.write(simplejson.dumps(response.json()))
