#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def get_data():
    pass


if __name__ == "__main__":
    #acceso_obj = Accesos(settings, sys_argv=sys.argv)
    #acceso_obj.console_run()
    #-FILTROS
    #### TODO ####
    # La idea es poder usar el modulo ya ccaraqgaod ya se aqui aqui haga peticiones de local host con curls
    # o la otra idea q se me ocurre es reescribir el routes para que se haga un reload de toda la app cada que se sube un script
    # lo que necesitamos es la flexiblidad de que cada cuenta por medio de scripts tenga su flexibilidad

    #data = acceso_obj.data.get('data',{})
    all_data = simplejson.loads(sys.argv[2])
    data = all_data.get("data", {})
    option = data.get("option",'')
    
    area = data.get("area")
    comments = data.get('comments',"")
    checkin_id = data.get("checkin_id","")
    employee_list = data.get("employee_list",[])
    equipo = data.get('equipo',"")
    forzar = data.get('forzar')
    marca = data.get('marca',"")
    guards = data.get('guards',[])
    location = data.get("location")
    qr_code = data.get('qr_code')
    record_id = data.get('record_id')
    support_guards = data.get('support_guards')
    tipo = data.get('tipo',"")
    vehiculo = data.get('vehiculo',"")
    visita_a = data.get('visita_a',"")
    gafete_id = data.get('gafete_id',"")
    data_msj=data.get("data_msj", {})
    data_cel_msj=data.get("data_cel_msj", {})
    status_visita=data.get("status_visita", "")
    inActive= data.get("inActive", "")
    turn_areas= data.get("turn_areas", True)
    prioridades = data.get("prioridades",[])
    id_bitacora = data.get("id_bitacora",[])
    data_gafete = data.get("data_gafete",{})
    tipo_movimiento = data.get("tipo_movimiento",{})
    dateFrom = data.get("dateFrom", "")
    dateTo = data.get("dateTo", "")
    filterDate = data.get("filterDate", "")
    limit = data.get("limit", 10)
    offset = data.get("offset", 0)
    fotografia=data.get("fotografia",[])
    #-FUNCTIONS
    # option = 'get_user_menu'
    print('option', option)
    if option == 'load_shift':
        # used
        response = acceso_obj.get_shift_data(booth_location=location, booth_area=area)
    elif option == 'assets_access_pass':
        response = acceso_obj.assets_access_pass(location)
    elif option == 'assing_gafete':
        response = acceso_obj.assing_gafete(data_gafete, id_bitacora, tipo_movimiento)
    elif option == 'list_bitacora':
        response = acceso_obj.get_list_bitacora(location,  area, prioridades=prioridades, dateFrom=dateFrom, dateTo=dateTo, limit=limit, offset=offset,  filterDate=filterDate)
    elif option == 'list_bitacora2':
        response = acceso_obj.get_list_bitacora2(location,  area, prioridades=prioridades, dateFrom=dateFrom, dateTo=dateTo, filterDate=filterDate)
    elif option == 'get_user_booths':
        response = acceso_obj.get_user_booths_availability(turn_areas=turn_areas)
    elif option == 'get_boot_guards' or option == 'guardias_de_apoyo':
        response = acceso_obj.get_booths_guards(location, area, solo_disponibles=True, **{'position':acceso_obj.support_guard})
    elif option == 'catalog_estado':
        response = acceso_obj.catalogo_estados()
    elif option == 'catalog_location':
        response = acceso_obj.get_catalog_locations(location)
    elif option == 'checkin':
        # used
        response = acceso_obj.do_checkin(location, area, employee_list, fotografia=fotografia)
    elif option == 'checkout':
        # used
        response = acceso_obj.do_checkout(checkin_id=checkin_id, \
            location=location, area= area, guards=guards, forzar=forzar, comments=comments, fotografia=fotografia)
    elif option == 'get_user_menu':
        response = dispatch("pases")
        #response = acceso_obj.get_config_accesos()
    elif option == 'search_access_pass':
        # used
        response = acceso_obj.search_access_pass(qr_code=qr_code, location=location)
    elif option == 'lista_pases':
        end_point = "lista_pases"
        response = dispatch(end_point, params={'location':location, 'inActive':inActive})
    elif option == 'do_out':
        # used
        response = acceso_obj.do_out(qr_code, location, area, gafete_id)
    elif option == 'do_access':
        # used
        response = acceso_obj.do_access(qr_code, location, area, data)
    elif option == 'update_bitacora_entrada':
        # used
        response = acceso_obj.update_bitacora_entrada(data, record_id=record_id)
    elif option == 'update_bitacora_entrada_many':
        # used
        response = acceso_obj.update_bitacora_entrada_many(data, record_id=record_id)
    elif option == 'notes_guard':
        response = acceso_obj.get_guard_notes(location, booth)
    elif option == 'vehiculo_tipo':
        if tipo and marca:
            response = acceso_obj.vehiculo_modelo(tipo, marca)
        elif tipo:
            response = acceso_obj.vehiculo_marca(tipo)
        else:
            response = acceso_obj.vehiculo_tipo()
    elif option == 'create_pase' or option == 'crear_pase':
        response = acceso_obj.create_access_pass(data_pase)
    elif option == 'update_guards':
        response = acceso_obj.update_guards_checkin(support_guards, checkin_id, location, area)
    elif option == 'visita_a':
        response = acceso_obj.visita_a(location)
    elif option == 'visita_a_detail':
        response = acceso_obj.visita_a_detail(location, visita_a)
    elif option == 'enviar_msj':
        response = acceso_obj.create_enviar_msj(data_msj=data_msj, data_cel_msj=data_cel_msj)
    elif option == 'send_msj_by_access':
        response = acceso_obj.send_email_and_sms(data=data_msj)

    else :
        response = {"msg": "Empty"}
    # print('================ END RETURN =================')
    # print(simplejson.dumps(response, indent=3))
    #acceso_obj.HttpResponse({"data":response})
    print('>>>response', response)
    sys.stdout.write(simplejson.dumps(response.json()))

