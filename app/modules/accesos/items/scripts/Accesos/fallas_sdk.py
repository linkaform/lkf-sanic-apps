#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def new_failure(params):
    data = params.get("data", {})
    return dispatch("new_failure", params={
        'data_failure': data.get('data_failure', {}),
    }, method='post', **params)

def get_failure_by_folio(params):
    data = params.get("data", {})
    return dispatch("get_fallas", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'folio': data.get('folio', ''),
    }, method='get', **params)

def get_fallas(params):
    data = params.get("data", {})
    return dispatch("get_fallas", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'status': data.get('status', ''),
        'dateFrom': data.get('dateFrom', ''),
        'dateTo': data.get('dateTo', ''),
        'filterDate': data.get('filterDate', ''),
    }, method='get', **params)

def update_failure(params):
    data = params.get("data", {})
    return dispatch("update_failure", params={
        'data_failure_update': data.get('data_failure_update', {}),
        'folio': data.get('folio', ''),
    }, method='post', **params)

def update_failure_seguimiento(params):
    data = params.get("data", {})
    return dispatch("update_failure_seguimiento", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'status': data.get('status', ''),
        'folio': data.get('folio', ''),
        'falla_grupo_seguimiento': data.get('falla_grupo_seguimiento', ''),
    }, method='post', **params)

def delete_failure(params):
    data = params.get("data", {})
    folio = data.get('folio')
    return dispatch("delete_failure", params={
        'folio': folio if isinstance(folio, list) else ([folio] if folio else []),
    }, method='get', **params)

def catalogo_area_empleado_apoyo(params):
    return dispatch("catalogo_area_empleado_apoyo", params={}, method='get', **params)

def catalogo_fallas(params):
    data = params.get("data", {})
    return dispatch("catalogo_fallas", params={
        'tipo': data.get('tipo', ''),
    }, method='get', **params)


DISPATCHER = {
    "new_failure": new_failure,
    "get_failure_by_folio": get_failure_by_folio,
    "get_failures": get_fallas,
    "get_fallas": get_fallas,
    "update_failure": update_failure,
    "update_failure_seguimiento": update_failure_seguimiento,
    "delete_failure": delete_failure,
    "catalogo_area_empleado_apoyo": catalogo_area_empleado_apoyo,
    "catalogo_fallas": catalogo_fallas,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option")
    print('..... arranca script fallas')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
