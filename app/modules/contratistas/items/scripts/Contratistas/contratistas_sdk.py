#!/usr/local/bin/python
# coding: utf-8
# Puente entre el script-runner de Django (/api/infosync/scripts/run/) y las
# rutas Sanic del modulo Contratistas. Es lo unico que el front de clave10
# invoca: script_name="contratistas_sdk.py" + option="<nombre de la ruta>".
#
# Calca app/modules/location/items/scripts/Locations/location_sdk.py, con dos
# diferencias deliberadas:
#
#   1. NO lleva prints de debug. location_sdk.py trae print('aca va') /
#      print('aqui....'), y aqui pasan contrasenas por este proceso: todo lo
#      que se imprima va al mismo stdout que el runner de Django captura.
#   2. Reenvia account_id en las rutas publicas.
#
# El Authorization del contratista viaja solo: dispatch() lo arma con
# kwargs['jwt'] / kwargs['Bearer'], que vienen en el payload original, y por
# eso se propaga con **params. Cuando no hay token, requests omite el header
# y la ruta lo recibe como None -> el servicio responde 401.

import sys

import simplejson

from middleware.auth import dispatch


def check_invitacion(params):
    data = params.get("data", {})
    return dispatch("check_invitacion", module='contratistas', params={
        'record_id': data.get('record_id', ''),
        'email': data.get('email', ''),
        'account_id': data.get('account_id', ''),
    }, method='post', **params)


def crear_cuenta_contratista(params):
    data = params.get("data", {})
    payload = {'account_id': data.get('account_id', '')}
    for key in ('record_id', 'email', 'password', 'password2',
                'nombre', 'apellidos', 'telefono', 'razon_social'):
        if key in data:
            payload[key] = data.get(key)
    return dispatch("crear_cuenta_contratista", module='contratistas',
                    params=payload, method='post', **params)


def aceptar_invitacion(params):
    data = params.get("data", {})
    return dispatch("aceptar_invitacion", module='contratistas', params={
        'record_id': data.get('record_id', ''),
    }, method='post', **params)


def get_contratista_by_id(params):
    data = params.get("data", {})
    return dispatch("get_contratista_by_id", module='contratistas', params={
        'record_id': data.get('record_id', ''),
    }, method='get', **params)


def update_contratista(params):
    data = params.get("data", {})
    payload = {'record_id': data.get('record_id', '')}
    for key in ('razon_social', 'rfc', 'telefono', 'servicios',
                'alta_fiscal', 'identificacion', 'comprobante_domicilio'):
        if key in data:
            payload[key] = data.get(key)
    if 'marcar_completada' in data:
        payload['marcar_completada'] = data.get('marcar_completada')
    return dispatch("update_contratista", module='contratistas',
                    params=payload, method='post', **params)


DISPATCHER = {
    "check_invitacion": check_invitacion,
    "crear_cuenta_contratista": crear_cuenta_contratista,
    "aceptar_invitacion": aceptar_invitacion,
    "get_contratista_by_id": get_contratista_by_id,
    "update_contratista": update_contratista,
}


if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option", "")
    handler = DISPATCHER.get(option)
    if not handler:
        sys.stdout.write(simplejson.dumps({
            "error": f"Option '{option}' not supported",
            "valid_options": list(DISPATCHER.keys()),
        }))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
