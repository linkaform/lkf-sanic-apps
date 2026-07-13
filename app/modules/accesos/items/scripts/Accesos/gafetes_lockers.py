#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def update_gafet_status(current_record, params):
    return dispatch("update_gafet_status", params={
        'answers': current_record.get('answers', {}),
    }, method='post', **params)

def new_badge(params):
    data = params.get("data", {})
    return dispatch("new_badge", params={
        'data_gafete': data.get('data_gafete', {}),
    }, method='post', **params)

def get_gafetes(params):
    data = params.get("data", {})
    return dispatch("get_gafetes", params={
        'status': data.get('status', ''),
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'gafete_id': data.get('gafete_id', data.get('id_gafete', '')),
        'limit': data.get('limit', 1000),
        'skip': data.get('skip', 0),
    }, method='get', **params)

def get_lockers(params):
    data = params.get("data", {})
    return dispatch("get_lockers", params={
        'status': data.get('status', ''),
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'tipo_locker': data.get('tipo_locker', ''),
        'locker_id': data.get('locker_id', data.get('id_locker', '')),
        'limit': data.get('limit', 1000),
        'skip': data.get('skip', 0),
    }, method='get', **params)

def deliver_badge(params):
    data = params.get("data", {})
    return dispatch("deliver_badge", params={
        'folio': data.get('folio', '512-10'),
    }, method='get', **params)


DISPATCHER = {
    "new_badge": new_badge,
    "get_gafetes": get_gafetes,
    "get_lockers": get_lockers,
    "deliver_badge": deliver_badge,
}

if __name__ == "__main__":
    current_record = simplejson.loads(sys.argv[1])
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    argument_option = params.get("option")
    option = data.get("option")
    print('..... arranca script gafetes_lockers')
    if argument_option == 'update_status':
        response = update_gafet_status(current_record, params)
    else:
        handler = DISPATCHER.get(option)
        if not handler:
            response = None
            sys.stdout.write(simplejson.dumps({"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}))
        else:
            response = handler(params)
    if response is not None:
        sys.stdout.write(simplejson.dumps(response.json()))
