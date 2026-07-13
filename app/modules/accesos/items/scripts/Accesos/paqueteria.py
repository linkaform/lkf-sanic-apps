#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def nuevo_paquete(params):
    data = params.get("data", {})
    return dispatch("nuevo_paquete", params={
        'data_paquete': data.get('data_paquete', {}),
    }, method='post', **params)

def get_paquetes(params):
    data = params.get("data", {})
    return dispatch("get_paquetes", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'status': data.get('status', ''),
        'dateFrom': data.get('dateFrom', ''),
        'dateTo': data.get('dateTo', ''),
        'filterDate': data.get('filterDate', ''),
    }, method='get', **params)

def actualizar_paquete(params):
    data = params.get("data", {})
    return dispatch("actualizar_paquete", params={
        'data_paquete_actualizar': data.get('data_paquete_actualizar', {}),
        'folio': data.get('folio', ''),
    }, method='post', **params)

def eliminar_paquete(params):
    data = params.get("data", {})
    return dispatch("eliminar_paquete", params={
        'folio': data.get('folio', ''),
    }, method='get', **params)

def get_catalogo_paquetes(params):
    return dispatch("get_catalogo_paquetes", params={}, method='get', **params)


DISPATCHER = {
    "nuevo_paquete": nuevo_paquete,
    "get_paquetes": get_paquetes,
    "actualizar_paquete": actualizar_paquete,
    "eliminar_paquete": eliminar_paquete,
    "get_catalogo_paquetes": get_catalogo_paquetes,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option")
    print('..... arranca script paqueteria')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
