#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def new_notes(params):
    data = params.get("data", {})
    return dispatch("new_notes", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'data_notes': data.get('data_notes', {}),
    }, method='post', **params)

def get_notes(params):
    data = params.get("data", {})
    return dispatch("get_notes", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'status': data.get('status', 'abierto'),
        'limit': data.get('limit', 10),
        'offset': data.get('offset', 0),
        'dateFrom': data.get('dateFrom', ''),
        'dateTo': data.get('dateTo', ''),
    }, method='get', **params)

def update_note(params):
    data = params.get("data", {})
    return dispatch("update_note", params={
        'data_update': data.get('data_update', {}),
        'folio': data.get('folio', '588-10'),
    }, method='post', **params)

def delete_note(params):
    # Deshabilitado intencionalmente: sin permisos para borrar notas (igual que en el legacy).
    return {"error": "No hay permisos para borrar notas"}


DISPATCHER = {
    "new_notes": new_notes,
    "get_notes": get_notes,
    "update_note": update_note,
    "delete_note": delete_note,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option")
    print('..... arranca script notes')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        if option == "delete_note":
            sys.stdout.write(simplejson.dumps(response))
        else:
            sys.stdout.write(simplejson.dumps(response.json()))
