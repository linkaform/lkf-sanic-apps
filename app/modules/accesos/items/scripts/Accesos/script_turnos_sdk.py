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
    data = params.get("data", {})
    return dispatch("assets_access_pass", params={
        'location': data.get('location', '')
    }, **params)

def assing_gafete(params):
    data = params.get("data", {})
    return dispatch("assing_gafete", params={
        'data_gafete': data.get('data_gafete', {}),
        'id_bitacora': data.get('id_bitacora', ''),
        'tipo_movimiento': data.get('tipo_movimiento', '')
    }, method='post', **params)

def list_bitacora(params):
    data = params.get("data", {})
    # POST porque dynamic_filters es una lista de dicts -- no cabe de forma
    # confiable en query string (a diferencia de prioridades, que sí).
    return dispatch("list_bitacora", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'prioridades': data.get('prioridades', []),
        'dateFrom': data.get('dateFrom', ''),
        'dateTo': data.get('dateTo', ''),
        'limit': data.get('limit', 10),
        'offset': data.get('offset', 0),
        'filterDate': data.get('filterDate', ''),
        'dynamic_filters': data.get('dynamic_filters', []),
    }, method='post', **params)

def get_user_booths(params):
    data = params.get("data", {})
    return dispatch("get_user_booths", params={
        'turn_areas': data.get('turn_areas', True)
    }, **params)

def get_boot_guards(params):
    data = params.get("data", {})
    return dispatch("get_boot_guards", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
    }, **params)

def get_user_menu(params):
    data = params.get("data", {})
    return dispatch("get_config_accesos", params={}, **params)

def checkout(params):
    data = params.get("data", {})
    return dispatch("checkout", params={
        'checkin_id': data.get('checkin_id', ''),
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'guards': data.get('guards', []),
        'forzar': data.get('forzar', False),
        'comments': data.get('comments', ''),
        'fotografia': data.get('fotografia', []),
        'guard_id': data.get('guard_id', ''),
    }, method='post', **params)

def catalog_estado(params):
    return dispatch("catalogo_estados", params={}, method='get', **params)

def checkin(params):
    data = params.get("data", {})
    return dispatch("checkin", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'employee_list': data.get('employee_list', []),
        'fotografia': data.get('fotografia', []),
        'check_in_manual': data.get('check_in_manual', {}),
        'nombre_suplente': data.get('nombre_suplente', ''),
        'checkin_id': data.get('checkin_id', ''),
        'roles': data.get('roles', []),
    }, method='post', **params)

def search_access_pass(params):
    data = params.get("data", {})
    return dispatch("search_access_pass", params={
        'qr_code': data.get('qr_code', ''),
        'location': data.get('location', ''),
    }, method='get', **params)

def lista_pases(params):
    data = params.get("data", {})
    return dispatch("lista_pases", params={
        'location': data.get('location', ''),
        'inActive': data.get('inActive', ''),
    }, method='get', **params)

def do_out(params):
    data = params.get("data", {})
    return dispatch("do_out", params={
        'qr_code': data.get('qr_code', ''),
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'gafete_id': data.get('gafete_id', ''),
        'record_id': data.get('record_id', ''),
    }, method='get', **params)

def do_access(params):
    data = params.get("data", {})
    return dispatch("do_access", params=data, method='post', **params)

def update_bitacora_entrada(params):
    data = params.get("data", {})
    return dispatch("update_bitacora_entrada", params=data, method='post', **params)

def update_bitacora_entrada_many(params):
    data = params.get("data", {})
    return dispatch("update_bitacora_entrada_many", params=data, method='post', **params)

def vehiculo_tipo(params):
    data = params.get("data", {})
    return dispatch("vehiculo_tipo", params={
        'tipo': data.get('tipo', ''),
        'marca': data.get('marca', ''),
    }, method='get', **params)

def update_guards(params):
    data = params.get("data", {})
    return dispatch("update_guards", params={
        'support_guards': data.get('support_guards', []),
        'checkin_id': data.get('checkin_id', ''),
        'location': data.get('location', ''),
        'area': data.get('area', ''),
    }, method='post', **params)

def visita_a(params):
    data = params.get("data", {})
    return dispatch("visita_a", params={
        'location': data.get('location', ''),
    }, method='get', **params)

def visita_a_detail(params):
    data = params.get("data", {})
    return dispatch("visita_a_detail", params={
        'location': data.get('location', ''),
        'visita_a': data.get('visita_a', ''),
    }, method='get', **params)

def enviar_msj(params):
    data = params.get("data", {})
    return dispatch("enviar_msj", params={
        'data_msj': data.get('data_msj', {}),
        'data_cel_msj': data.get('data_cel_msj', {}),
    }, method='post', **params)

def send_msj_by_access(params):
    data = params.get("data", {})
    return dispatch("send_msj_by_access", params={
        'data_msj': data.get('data_msj', {}),
    }, method='post', **params)

def update_delete_suplente(params):
    data = params.get("data", {})
    return dispatch("update_delete_suplente", params={
        'nombre_suplente': data.get('nombre_suplente', ''),
    }, method='get', **params)

def force_quit_all_persons(params):
    data = params.get("data", {})
    return dispatch("force_quit_all_persons", params={
        'location': data.get('location', ''),
    }, method='get', **params)


DISPATCHER = {
    "load_shift": load_shift,
    "assets_access_pass": assets_access_pass,
    "assing_gafete": assing_gafete,
    "list_bitacora": list_bitacora,
    "list_bitacora2": list_bitacora,
    "get_user_booths": get_user_booths,
    "get_boot_guards": get_boot_guards,
    "get_user_menu": get_user_menu,
    "guardias_de_apoyo": get_boot_guards,
    "checkout": checkout,
    "catalog_estado": catalog_estado,
    "checkin": checkin,
    "search_access_pass": search_access_pass,
    "lista_pases": lista_pases,
    "do_out": do_out,
    "do_access": do_access,
    "update_bitacora_entrada": update_bitacora_entrada,
    "update_bitacora_entrada_many": update_bitacora_entrada_many,
    "vehiculo_tipo": vehiculo_tipo,
    "update_guards": update_guards,
    "visita_a": visita_a,
    "visita_a_detail": visita_a_detail,
    "enviar_msj": enviar_msj,
    "send_msj_by_access": send_msj_by_access,
    "update_delete_suplente": update_delete_suplente,
    "force_quit_all_persons": force_quit_all_persons,
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
    option = data.get("option",'get_user_menu')
    print('..... arranca script turnos')
    print('data=', data)
    print('option=', option)
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported"}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))