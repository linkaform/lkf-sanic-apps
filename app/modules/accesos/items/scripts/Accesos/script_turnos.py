#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def get_data():
    pass

def load_shift(params):
    data = params.get("data", {})
    return dispatch(
        "load_shift", 
        params={
            'booth_location': data.get('location', ''), 
            'booth_area': data.get('area', '')
        },
        method='get',
        **params
    )

def assets_access_pass(params):
    data = kwargs.get("data", {})
    return dispatch("assets_access_pass", params={
        'location': data.get('location', '')
    }, **params)

def assing_gafete(params):
    data = kwargs.get("data", {})
    return dispatch("assing_gafete", params={
        'data_gafete': data.get('data_gafete', {}), 
        'id_bitacora': data.get('id_bitacora', ''), 
        'tipo_movimiento': data.get('tipo_movimiento', '')
    }, **params)

def list_bitacora(params):
    data = params.get("data", {})
    return dispatch("list_bitacora", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'prioridades': data.get('prioridades', []),
        'dateFrom': data.get('dateFrom', ''),
        'dateTo': data.get('dateTo', ''),
        'limit': data.get('limit', 10),
        'offset': data.get('offset', 0),
        'filterDate': data.get('filterDate', '')
    }, **params)

def list_bitacora2(params):
    data = params.get("data", {})
    return dispatch("list_bitacora2", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'prioridades': data.get('prioridades', []),
        'dateFrom': data.get('dateFrom', ''),
        'dateTo': data.get('dateTo', ''),
        'filterDate': data.get('filterDate', '')
    }, **params)

def get_user_booths(params):
    data = params.get("data", {})
    return dispatch("get_user_booths", params={
        'turn_areas': data.get('turn_areas', True)
    }, **data)

def get_boot_guards(params):
    data = params.get("data", {})
    return dispatch("get_boot_guards", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
    }, **params)

def get_user_menu(params):
    data = params.get("data", {})
    return dispatch("get_config_accesos", params={}, **params)


DISPATCHER = {
    "load_shift": load_shift,
    "assets_access_pass": assets_access_pass,
    "assing_gafete": assing_gafete,
    "list_bitacora": list_bitacora,
    "list_bitacora2": list_bitacora2,
    "get_user_booths": get_user_booths,
    "get_boot_guards": get_boot_guards,
    "get_user_menu": get_user_menu,
    "guardias_de_apoyo": get_boot_guards,
}

if __name__ == "__main__":
    #acceso_obj = Accesos(settings, sys_argv=sys.argv)
    #acceso_obj.console_run()
    #-FILTROS
    #### TODO ####
    # La idea es poder usar el modulo ya ccaraqgaod ya se aqui aqui haga peticiones de local host con curls
    # o la otra idea q se me ocurre es reescribir el routes para que se haga un reload de toda la app cada que se sube un script
    # lo que necesitamos es la flexiblidad de que cada cuenta por medio de scripts tenga su flexibilidad

    #data = acceso_obj.data.get('data',{})
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option")
    print('..... arranca script turnos')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported"}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))