#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def console_run(self):
    print(f"python { self.argv[0].split('/')[-1]} '{ self.argv[1]}' '{ self.argv[2]}'")

def _as_list(value):
    if isinstance(value, list):
        return value
    return [value] if value else []


def create_rondin(params):
    data = params.get("data", {})
    return dispatch("create_rondin", params={
        'rondin_data': data.get('rondin_data', {}),
    }, method='post', **params)

def claim_rondin(params):
    data = params.get("data", {})
    return dispatch("claim_rondin", params={
        'record_id': data.get('record_id', ''),
    }, method='post', **params)

def create_incidencia_by_rondin(params):
    data = params.get("data", {})
    return dispatch("create_incidencia_by_rondin", params={
        'rondin_data': data.get('rondin_data', {}),
    }, method='post', **params)

def delete_rondin(params):
    data = params.get("data", {})
    return dispatch("delete_rondin", params={
        'folio': data.get('folio', ''),
    }, method='post', **params)

def edit_areas_rondin(params):
    data = params.get("data", {})
    return dispatch("edit_areas_rondin", params={
        'areas': data.get('areas', []),
        'folio': data.get('folio', ''),
        'record_id': data.get('record_id', ''),
    }, method='post', **params)

def get_recorridos(params):
    data = params.get("data", {})
    return dispatch("get_recorridos", params={
        'date_from': data.get('date_from', ''),
        'date_to': data.get('date_to', ''),
        'area_details': data.get('area_details', False),
        'limit': data.get('limit', 20),
        'offset': data.get('offset', 0),
    }, method='get', **params)

def get_bitacora(params):
    data = params.get("data", {})
    current_record = params.get('current_record', {}) or {}
    return dispatch("get_bitacora", params={
        'date_from': data.get('date_from', ''),
        'date_to': data.get('date_to', ''),
        'area_details': data.get('area_details', False),
        'limit': data.get('limit', 15),
        'offset': data.get('offset', 0),
        'ubicacion': data.get('ubicacion', ''),
        'nombre_rondin': data.get('nombre_rondin', ''),
        'timezone': data.get('timezone') or current_record.get('timezone', 'America/Mexico_City'),
    }, method='get', **params)

def get_catalog_areas(params):
    data = params.get("data", {})
    return dispatch("get_catalog_areas", params={
        'ubicacion': data.get('ubicacion', ''),
    }, method='get', **params)

def get_all_checks(params):
    data = params.get("data", {})
    return dispatch("get_all_checks", params={
        'ubicacion': data.get('ubicacion', ''),
        'nombre_rondin': data.get('nombre_rondin', ''),
    }, method='get', **params)

def get_rondin_by_id(params):
    data = params.get("data", {})
    return dispatch("get_rondin_by_id", params={
        'record_id': data.get('record_id', ''),
    }, method='get', **params)

def get_incidencias_rondines(params):
    data = params.get("data", {})
    return dispatch("get_incidencias_rondines", params={
        'ubicacion': data.get('ubicacion', ''),
        'area': data.get('area', ''),
        'date_from': data.get('date_from', ''),
        'date_to': data.get('date_to', ''),
        'limit': data.get('limit', 20),
        'offset': data.get('offset', 0),
    }, method='get', **params)

def get_rondines_images(params):
    data = params.get("data", {})
    return dispatch("get_rondines_images", params={
        'ubicacion': data.get('ubicacion', ''),
        'areas': _as_list(data.get('areas')),
        'date_from': data.get('date_from', ''),
        'date_to': data.get('date_to', ''),
        'limit': data.get('limit', 20),
        'offset': data.get('offset', 0),
    }, method='get', **params)

def get_bitacora_rondines(params):
    data = params.get("data", {})
    current_record = params.get('current_record', {}) or {}
    return dispatch("get_bitacora_rondines", params={
        'ubicacion': data.get('ubicacion', ''),
        'nombre_rondin': data.get('nombre_rondin', ''),
        'year': data.get('year', ''),
        'month': data.get('month', ''),
        'timezone': data.get('timezone') or current_record.get('timezone', 'America/Mexico_City'),
    }, method='get', **params)

def get_check_by_id(params):
    data = params.get("data", {})
    current_record = params.get('current_record', {}) or {}
    return dispatch("get_check_by_id", params={
        'record_id': data.get('record_id', ''),
        'timezone': data.get('timezone') or current_record.get('timezone', 'America/Mexico_City'),
    }, method='get', **params)

def get_bitacora_by_id(params):
    data = params.get("data", {})
    current_record = params.get('current_record', {}) or {}
    return dispatch("get_bitacora_by_id", params={
        'record_id': data.get('record_id', ''),
        'timezone': data.get('timezone') or current_record.get('timezone', 'America/Mexico_City'),
    }, method='get', **params)

def get_catalog_areas_formatted(params):
    data = params.get("data", {})
    return dispatch("get_catalog_areas_formatted", params={
        'ubicacion': data.get('ubicacion', ''),
    }, method='get', **params)

def catalago_grupos_recorridos(params):
    return dispatch("catalago_grupos_recorridos", params={}, method='get', **params)

def catalogo_inspecciones(params):
    return dispatch("catalogo_inspecciones", params={}, method='get', **params)

def pause_or_play_rondin(params):
    data = params.get("data", {})
    return dispatch("pause_or_play_rondin", params={
        'record_id': data.get('record_id', ''),
        'paused': data.get('paused', True),
    }, method='post', **params)

def update_rondin(params):
    data = params.get("data", {})
    return dispatch("update_rondin", params={
        'folio': data.get('folio', ''),
        'rondin_data': data.get('rondin_data', {}),
    }, method='post', **params)

def update_inspeccion(params):
    data = params.get("data", {})
    return dispatch("update_inspeccion", params={
        'folio': data.get('folio', ''),
        'rondin_data': data.get('rondin_data', {}),
    }, method='post', **params)

def asignar_recorrido(params):
    data = params.get("data", {})
    return dispatch("asignar_recorrido", params={
        'folio': data.get('folio', ''),
        'asignado_a': data.get('asignado_a', []),
    }, method='post', **params)

def run_cron(params):
    data = params.get("data", {})
    return dispatch("run_cron", params={
        'dag_id': data.get('dag_id', []),
    }, method='post', **params)


DISPATCHER = {
    "create_rondin": create_rondin,
    "claim_rondin": claim_rondin,
    "create_incidencia_by_rondin": create_incidencia_by_rondin,
    "delete_rondin": delete_rondin,
    "edit_areas_rondin": edit_areas_rondin,
    "get_recorridos": get_recorridos,
    "get_bitacora": get_bitacora,
    "get_catalog_areas": get_catalog_areas,
    "get_all_checks": get_all_checks,
    "get_rondin_by_id": get_rondin_by_id,
    "get_incidencias_rondines": get_incidencias_rondines,
    "get_rondines_images": get_rondines_images,
    "get_bitacora_rondines": get_bitacora_rondines,
    "get_check_by_id": get_check_by_id,
    "get_bitacora_by_id": get_bitacora_by_id,
    "get_catalog_areas_formatted": get_catalog_areas_formatted,
    "catalago_grupos_recorridos": catalago_grupos_recorridos,
    "catalogo_inspecciones": catalogo_inspecciones,
    "pause_or_play_rondin": pause_or_play_rondin,
    "update_rondin": update_rondin,
    "update_inspeccion": update_inspeccion,
    "asignar_recorrido": asignar_recorrido,
    "run_rondin": run_cron,
    "run_cron": run_cron,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    console_run(sys)
    data = params.get("data", {})
    option = data.get("option")
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
