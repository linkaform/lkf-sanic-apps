#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def get_catalog_ubicaciones_formatted(params):
    data = params.get("data", {})
    print('aca va')
    return dispatch("get_catalog_ubicaciones_formatted", module='location', params={
        'ubicacion': data.get('ubicacion', ''),
    }, method='get', **params)


def get_ubicacion_by_id(params):
    data = params.get("data", {})
    return dispatch("get_ubicacion_by_id", module='location', params={
        'record_id': data.get('record_id', ''),
    }, method='get', **params)


def create_ubicacion(params):
    data = params.get("data", {})
    return dispatch("create_new_ubicacion", module='location', params={
        'nombre': data.get('nombre', ''),
        'direccion': data.get('direccion', ''),
        'colonia': data.get('colonia', ''),
        'ciudad': data.get('ciudad', ''),
        'estado': data.get('estado', ''),
        'pais': data.get('pais', ''),
        'codigo_postal': data.get('codigo_postal', ''),
        'telefono': data.get('telefono', ''),
        'email': data.get('email', ''),
        'geolocalizacion': data.get('geolocalizacion', {}),
    }, method='post', **params)


def update_ubicacion(params):
    data = params.get("data", {})
    payload = {
        'record_id': data.get('record_id', ''),
        'nombre_actual': data.get('nombre_actual', ''),
    }
    for key in (
        'nombre', 'direccion', 'colonia', 'ciudad', 'estado',
        'pais', 'codigo_postal', 'telefono', 'email', 'geolocalizacion',
    ):
        if key in data:
            payload[key] = data.get(key)
    return dispatch("update_ubicacion", module='location', params=payload, method='post', **params)


DISPATCHER = {
    "get_catalog_ubicaciones_formatted": get_catalog_ubicaciones_formatted,
    "get_ubicacion_by_id": get_ubicacion_by_id,
    "create_ubicacion": create_ubicacion,
    "update_ubicacion": update_ubicacion,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option", "")
    handler = DISPATCHER.get(option)
    print('aqui....')
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
