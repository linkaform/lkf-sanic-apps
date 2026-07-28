#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def catalago_vehiculo(params):
    data = params.get("data", {})
    return dispatch("vehiculo_tipo", params={
        'tipo': data.get('tipo', ''),
        'marca': data.get('marca', ''),
    }, method='get', **params)

def catalago_estados(params):
    return dispatch("catalogo_estados", params={}, method='get', **params)


DISPATCHER = {
    "catalago_vehiculo": catalago_vehiculo,
    "catalago_estados": catalago_estados,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option", "")
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
