

import os
import sys
import asyncio
import importlib.util
import pytz
from datetime import datetime, timedelta
from pathlib import Path
from sanic import Blueprint
from sanic.request import Request
from sanic.response import json

from loader import get_module_class

########
#### version funcionado
#########


print('>>> Iniciando carga de módulo Accesos')

# ============================================
# CONFIGURACIÓN
# ============================================

# Configuración de settings
print('>>> Cargando configuración')
from config.account_settings import *
print('>>> Configuración cargada')


# ============================================
# CARGAR CLASE ACCESOS
# ============================================

# account_id = os.getenv("ACCOUNT_ID", 1256)

# Cargar la clase (esto se hace UNA VEZ al importar el módulo)
ModuleClass = get_module_class('Accesos')

# Crear instancia global del servicio
print('>>> Creando instancia del servicio Accesos')

service = ModuleClass(settings)
print('>>> Servicio Accesos inicializado correctamente')

# Instancia de Schedule para endpoints de programacion de tareas (cron/airflow),
# usada por ejemplo para programar recorridos de rondines (migrado de config_recorridos.py).
from lkf_addons.base.app import Schedule
schedule_service = Schedule(settings)

# ============================================
# BLUEPRINT
# ============================================

accesos_bp = Blueprint("accesos", url_prefix="/accesos")


@accesos_bp.get("/acceso")
async def get_acceso(request: Request):
    res = {'demo':'true', 'message':'Acceso registrado'}
    return json(res, status=201)


@accesos_bp.get("/get_config_accesos")
async def get_config_accesos(request: Request):
    print('route.... /get_config_accesos')
    res = service.get_config_accesos()
    print('route.... /get_config_accesos222',res)
    return json(res, status=201)

@accesos_bp.post("/incidentes")
async def post_incidente(request: Request):
    payload = request.json or {}
    res = await service.crear_incidente(payload)
    return json(res, status=201)


@accesos_bp.get("/lista_pases")
async def get_lista_pases(request: Request):
    allowed_params = ["location", "status", "inActive"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    records = service.get_lista_pase(**filters)
    return json({"data": records}, status=200)


@accesos_bp.get("/pases")
async def get_pases(request: Request):
    print('request.asrgs:', request.args)
    empresa = request.args.get("empresa")
    # records = service.get_locations_address()
    records = service.get_config_accesos()
    print('records:', records)
    # records = await service.listar_pases_por_empresa(empresa=empresa)
    # records = [{"empresa": empresa, "count": 42}]
    return json({"data": records})

@accesos_bp.get("/load_shift")
async def get_shift_data(request: Request):
    allowed_params = ["booth_location", "booth_area"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    print('filters:', filters)
    records = service.get_shift_data(**filters, headers=dict(request.headers))
    return json({"data": records}, status=200)

@accesos_bp.get("/assets_access_pass")
async def assets_access_pass(request: Request):
    allowed_params = ["location"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    records = service.assets_access_pass(**filters)
    return json({"data": records}, status=200)

@accesos_bp.post("/assing_gafete")
async def assing_gafete(request: Request):
    # POST porque data_gafete es un dict — no cabe de forma confiable en query string.
    payload = _ocr_payload(request)
    allowed_params = ["data_gafete", "id_bitacora", "tipo_movimiento"]
    filters = {k: payload.get(k) for k in allowed_params if payload.get(k) is not None}
    records = service.assing_gafete(**filters)
    return json({"data": records}, status=200)

@accesos_bp.get("/list_bitacora")
async def get_list_bitacora(request: Request):
    allowed_params = ["location", "area", "prioridades", "dateFrom", "dateTo", "limit", "offset", "filterDate"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    if filters.get('limit') is not None:
        filters['limit'] = int(filters['limit'])
    if filters.get('offset') is not None:
        filters['offset'] = int(filters['offset'])
    records = service.get_list_bitacora(**filters)
    return json({"data": records}, status=200)

@accesos_bp.get("/get_user_booths")
async def get_user_booths(request: Request):
    allowed_params = ["turn_areas"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    records = service.get_user_booths_availability(**filters)
    return json({"data": records}, status=200)

@accesos_bp.get("/get_boot_guards")
async def get_booths_guards(request: Request):
    allowed_params = ["location", "area", "solo_disponibles", "position"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    filters['solo_disponibles'] = True
    filters['position'] = 'guardia_de_apoyo'
    records = service.get_booths_guards(**filters)
    return json({"data": records}, status=200)

@accesos_bp.post("/checkout")
async def post_checkout(request: Request):
    # POST porque fotografia/guards son listas — no caben de forma confiable en query string.
    payload = _ocr_payload(request)
    allowed_params = ["checkin_id", "location", "area", "guards", "forzar", "comments", "fotografia", "guard_id"]
    filters = {k: payload.get(k) for k in allowed_params if payload.get(k) is not None}
    records = service.do_checkout(**filters)
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogo_estados")
async def get_catalogo_estados(request: Request):
    records = service.catalogo_estados()
    return json({"data": records}, status=200)

@accesos_bp.post("/checkin")
async def post_checkin(request: Request):
    # POST porque employee_list/fotografia/roles son listas.
    payload = _ocr_payload(request)
    allowed_params = ["location", "area", "employee_list", "fotografia", "check_in_manual", "nombre_suplente", "checkin_id", "roles"]
    filters = {k: payload.get(k) for k in allowed_params if payload.get(k) is not None}
    records = service.do_checkin(**filters)
    return json({"data": records}, status=200)

@accesos_bp.get("/search_access_pass")
async def get_search_access_pass(request: Request):
    allowed_params = ["qr_code", "location"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    records = service.search_access_pass(**filters)
    return json({"data": records}, status=200)

@accesos_bp.get("/do_out")
async def get_do_out(request: Request):
    allowed_params = ["location", "area", "gafete_id", "record_id"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    qr = request.args.get("qr_code")
    records = service.do_out(qr=qr, **filters)
    return json({"data": records}, status=200)

@accesos_bp.post("/do_access")
async def post_do_access(request: Request):
    # POST porque "data" es el payload completo con el que do_access arma el registro de bitacora.
    payload = _ocr_payload(request)
    allowed_params = ["qr_code", "location", "area"]
    filters = {k: payload.get(k) for k in allowed_params if payload.get(k) is not None}
    records = service.do_access(data=payload, **filters)
    return json({"data": records}, status=200)

@accesos_bp.post("/update_bitacora_entrada")
async def post_update_bitacora_entrada(request: Request):
    payload = _ocr_payload(request)
    record_id = payload.get("record_id")
    folio = payload.get("folio")
    records = service.update_bitacora_entrada(payload, record_id=record_id, folio=folio)
    return json({"data": records}, status=200)

@accesos_bp.post("/update_bitacora_entrada_many")
async def post_update_bitacora_entrada_many(request: Request):
    payload = _ocr_payload(request)
    record_id = payload.get("record_id")
    folio = payload.get("folio")
    records = service.update_bitacora_entrada_many(payload, record_id=record_id, folio=folio)
    return json({"data": records}, status=200)

@accesos_bp.get("/vehiculo_tipo")
async def get_vehiculo_tipo(request: Request):
    tipo = request.args.get("tipo")
    marca = request.args.get("marca")
    if tipo and marca:
        records = service.vehiculo_modelo(tipo, marca)
    elif tipo:
        records = service.vehiculo_marca(tipo)
    else:
        records = service.vehiculo_tipo()
    return json({"data": records}, status=200)

@accesos_bp.post("/update_guards")
async def post_update_guards(request: Request):
    # POST porque support_guards es una lista de dicts.
    payload = _ocr_payload(request)
    allowed_params = ["location", "area", "checkin_id"]
    filters = {k: payload.get(k) for k in allowed_params if payload.get(k) is not None}
    support_guards = payload.get("support_guards", [])
    records = service.update_guards_checkin(support_guards, filters.pop("checkin_id", None), filters.get("location"), filters.get("area"))
    return json({"data": records}, status=200)

@accesos_bp.get("/visita_a")
async def get_visita_a(request: Request):
    location = request.args.get("location")
    records = service.visita_a(location)
    return json({"data": records}, status=200)

@accesos_bp.get("/visita_a_detail")
async def get_visita_a_detail(request: Request):
    location = request.args.get("location")
    visita_a = request.args.get("visita_a")
    records = service.visita_a_detail(location, visita_a)
    return json({"data": records}, status=200)

@accesos_bp.post("/enviar_msj")
async def post_enviar_msj(request: Request):
    payload = _ocr_payload(request)
    data_msj = payload.get("data_msj", {})
    data_cel_msj = payload.get("data_cel_msj", {})
    records = service.create_enviar_msj(data_msj=data_msj, data_cel_msj=data_cel_msj)
    return json({"data": records}, status=200)

@accesos_bp.post("/send_msj_by_access")
async def post_send_msj_by_access(request: Request):
    payload = _ocr_payload(request)
    data_msj = payload.get("data_msj", {})
    records = service.send_email_and_sms(data=data_msj)
    return json({"data": records}, status=200)

@accesos_bp.get("/update_delete_suplente")
async def get_update_delete_suplente(request: Request):
    nombre_suplente = request.args.get("nombre_suplente", "")
    records = service.update_delete_suplente(nombre_suplente=nombre_suplente)
    return json({"data": records}, status=200)

@accesos_bp.get("/force_quit_all_persons")
async def get_force_quit_all_persons(request: Request):
    location = request.args.get("location")
    records = service.force_quit_all_persons(location=location)
    return json({"data": records}, status=200)

# ============================================
# Pase de Acceso (migrado de pase_de_acceso.py)
# ============================================

@accesos_bp.post("/crear_pase")
async def post_crear_pase(request: Request):
    # POST porque access_pass es el objeto completo con todos los campos del pase.
    payload = _ocr_payload(request)
    records = service.create_access_pass(access_pass=payload)
    return json({"data": records}, status=201)

@accesos_bp.post("/update_pass")
async def post_update_pass(request: Request):
    payload = _ocr_payload(request)
    folio = payload.get("folio")
    records = service.update_pass(access_pass=payload, folio=folio)
    return json({"data": records}, status=200)

@accesos_bp.post("/update_full_pass")
async def post_update_full_pass(request: Request):
    # Body: {"access_pass": {...}, "folio": "...", "qr_code": "...", "location": "..."}
    payload = _ocr_payload(request)
    access_pass = payload.get("access_pass", {})
    records = service.update_full_pass(
        access_pass=access_pass,
        folio=payload.get("folio"),
        qr_code=payload.get("qr_code"),
        location=payload.get("location"),
    )
    return json({"data": records}, status=200)

@accesos_bp.post("/update_active_pass")
async def post_update_active_pass(request: Request):
    # Body: {"folio": "...", "qr_code": "...", "update_obj": {...}}
    payload = _ocr_payload(request)
    records = service.update_active_pass(
        folio=payload.get("folio"),
        qr_code=payload.get("qr_code"),
        update_obj=payload.get("update_obj", {}),
    )
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogos_pase_area")
async def get_catalogos_pase_area(request: Request):
    location_name = request.args.get("location_name")
    records = service.catalogos_pase_area(location_name)
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogos_pase_location")
async def get_catalogos_pase_location(request: Request):
    records = service.catalogos_pase_location()
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogos_pase_no_jwt")
async def get_catalogos_pase_no_jwt(request: Request):
    qr_code = request.args.get("qr_code")
    records = service.catalagos_pase_no_jwt(qr_code)
    return json({"data": records}, status=200)

@accesos_bp.post("/pase_enviar_msj")
async def post_pase_enviar_msj(request: Request):
    payload = _ocr_payload(request)
    records = service.create_enviar_msj_pase(folio=payload.get("folio"))
    return json({"data": records}, status=200)

@accesos_bp.post("/pase_enviar_correo")
async def post_pase_enviar_correo(request: Request):
    # POST porque envio es una lista.
    payload = _ocr_payload(request)
    records = service.create_enviar_correo(folio=payload.get("folio"), envio=payload.get("envio", []))
    return json({"data": records}, status=200)

@accesos_bp.get("/get_pass")
async def get_get_pass(request: Request):
    qr_code = request.args.get("qr_code")
    records = service.get_pass_custom(qr_code)
    return json({"data": records}, status=200)

@accesos_bp.post("/get_my_pases")
async def post_get_my_pases(request: Request):
    # POST porque dynamic_filters/locations son listas.
    payload = _ocr_payload(request)
    allowed_params = ["tab_status", "limit", "skip", "search_name", "location", "dynamic_filters", "dateFrom", "dateTo", "filterDate", "locations"]
    filters = {k: payload.get(k) for k in allowed_params if payload.get(k) is not None}
    if filters.get('limit') is not None:
        filters['limit'] = int(filters['limit'])
    if filters.get('skip') is not None:
        filters['skip'] = int(filters['skip'])
    records = service.get_my_pases(**filters)
    return json({"data": records}, status=200)

@accesos_bp.get("/get_pdf")
async def get_get_pdf(request: Request):
    qr_code = request.args.get("qr_code")
    template_id = request.args.get("template_id")
    name_pdf = request.args.get("name_pdf")
    records = service.get_pdf(qr_code, template_id=template_id, name_pdf=name_pdf)
    return json({"data": records}, status=200)

@accesos_bp.get("/get_pdf_seg")
async def get_get_pdf_seg(request: Request):
    qr_code = request.args.get("qr_code")
    template_id = request.args.get("template_id")
    name_pdf = request.args.get("name_pdf")
    records = service.get_pdf_seg(qr_code, template_id=template_id, name_pdf=name_pdf)
    return json({"data": records}, status=200)

@accesos_bp.get("/get_user_contacts")
async def get_get_user_contacts(request: Request):
    records = service.get_user_contacts()
    return json({"data": records}, status=200)

@accesos_bp.get("/get_config_modulo_seguridad")
async def get_get_config_modulo_seguridad(request: Request):
    # acepta ?locations=a&locations=b (lista) o ?location=a (una sola).
    # legacy pasa 'location' tal cual (string, sin envolver en lista) cuando
    # solo se manda una ubicacion, asi que replicamos ese shape exacto.
    ubicaciones = request.args.getlist("locations")
    if not ubicaciones:
        ubicaciones = request.args.get("location", "")
    records = service.get_config_modulo_seguridad(ubicaciones=ubicaciones)
    return json({"data": records}, status=200)

@accesos_bp.get("/get_areas_by_locations")
async def get_get_areas_by_locations(request: Request):
    locations = request.args.getlist("locations")
    if not locations:
        location = request.args.get("location")
        locations = [location] if location else []
    records = service.get_areas_by_locations(locations)
    return json({"data": records}, status=200)

@accesos_bp.post("/extends_date_of_pass")
async def post_extends_date_of_pass(request: Request):
    # POST porque update_obj es un dict.
    payload = _ocr_payload(request)
    qr_code = payload.get("qr_code")
    update_obj = payload.get("update_obj", {})
    records = service.extends_date_of_pass(qr_code, update_obj)
    return json({"data": records}, status=200)

# ============================================
# Menus (migrado de menus.py)
# ============================================

@accesos_bp.get("/get_menus")
async def get_get_menus(request: Request):
    print('--- rute get_menus---')
    platform = request.args.get("platform", "")
    records = service.get_user_menus(platform=platform)
    return json({"data": records}, status=200)

@accesos_bp.post("/set_permissions")
async def post_set_permissions(request: Request):
    # POST porque answers es el objeto completo del registro de Configuracion de Menus.
    payload = _ocr_payload(request)
    records = service.set_user_permissions(answers=payload.get("answers", {}), user_id=payload.get("user_id"))
    return json({"data": records}, status=200)

# ============================================
# OCR (self.ai / OpenRouter)
# Todos reciben la imagen como file_url (image_source), no como archivo subido.
# La opción de subida directa de archivo se agrega en una fase posterior.
# ============================================

def _ocr_payload(request: Request) -> dict:
    """
    Acepta el payload venga como JSON (pruebas directas con curl/Postman) o
    como form-data (así lo manda middleware.auth.dispatch cuando los scripts
    CLI de app/modules invocan estas rutas con method='post').
    """
    try:
        if request.json:
            return request.json
    except Exception:
        pass
    if request.form:
        return {
            k: (v[0] if isinstance(v, list) and len(v) == 1 else v)
            for k, v in request.form.items()
        }
    return dict(request.args)


@accesos_bp.post("/ocr_identificacion")
async def post_ocr_identificacion(request: Request):
    payload = _ocr_payload(request)
    res = service.ocr_identificacion(
        image_source=payload.get('image_source'),
        form_id=payload.get('form_id'),
        model=payload.get('model', 'google/gemini-2.5-flash-lite'),
        name=payload.get('name'),
        is_employee=payload.get('is_employee', False),
    )
    return json(res, status=res.get('status_code', 200))

@accesos_bp.post("/ocr_documento")
async def post_ocr_documento(request: Request):
    payload = _ocr_payload(request)
    res = service.ocr_documento(
        image_source=payload.get('image_source'),
        fields=payload.get('fields'),
        extra_instructions=payload.get('extra_instructions'),
        form_id=payload.get('form_id'),
        model=payload.get('model'),
        is_employee=payload.get('is_employee', False),
    )
    return json(res, status=res.get('status_code', 200))

@accesos_bp.post("/ocr_batch")
async def post_ocr_batch(request: Request):
    payload = _ocr_payload(request)
    images = payload.get('images') or ([payload['image_source']] if payload.get('image_source') else [])
    res = service.ocr_batch(
        images=images,
        option_type=payload.get('option_type', 'ocr_id'),
        form_id=payload.get('form_id'),
        model=payload.get('model'),
    )
    return json(res, status=res.get('status_code', 200))

@accesos_bp.post("/ocr_articulo_perdido")
async def post_ocr_articulo_perdido(request: Request):
    payload = _ocr_payload(request)
    res = service.ocr_articulo_perdido(
        image_source=payload.get('image_source'),
        model=payload.get('model', 'google/gemini-2.5-flash-lite'),
    )
    return json(res, status=res.get('status_code', 200))

@accesos_bp.post("/ocr_paquete")
async def post_ocr_paquete(request: Request):
    payload = _ocr_payload(request)
    res = service.ocr_paquete(
        image_source=payload.get('image_source'),
        fields=payload.get('fields', {}),
        extra_instructions=payload.get('extra_instructions'),
        model=payload.get('model', 'google/gemini-2.5-flash-lite'),
    )
    return json(res, status=res.get('status_code', 200))

@accesos_bp.post("/ocr_equipo")
async def post_ocr_equipo(request: Request):
    payload = _ocr_payload(request)
    res = service.ocr_equipo(
        image_source=payload.get('image_source'),
        extra_instructions=payload.get('extra_instructions'),
        model=payload.get('model', 'google/gemini-2.5-flash-lite'),
    )
    return json(res, status=res.get('status_code', 200))

@accesos_bp.post("/ocr_persona")
async def post_ocr_persona(request: Request):
    payload = _ocr_payload(request)
    res = service.ocr_persona(
        image_source=payload.get('image_source'),
        extra_instructions=payload.get('extra_instructions'),
        model=payload.get('model', 'google/gemini-2.5-flash-lite'),
    )
    return json(res, status=res.get('status_code', 200))

@accesos_bp.post("/ocr_vehiculo")
async def post_ocr_vehiculo(request: Request):
    payload = _ocr_payload(request)
    res = service.ocr_vehiculo(
        image_source=payload.get('image_source'),
        fields=payload.get('fields', {}),
        extra_instructions=payload.get('extra_instructions'),
        model=payload.get('model', 'google/gemini-2.5-flash-lite'),
    )
    return json(res, status=res.get('status_code', 200))

@accesos_bp.post("/ocr_truck")
async def post_ocr_truck(request: Request):
    payload = _ocr_payload(request)
    res = service.ocr_truck(
        image_source=payload.get('image_source'),
        fields=payload.get('fields', {}),
        extra_instructions=payload.get('extra_instructions'),
        model=payload.get('model', 'google/gemini-2.5-flash-lite'),
    )
    return json(res, status=res.get('status_code', 200))

@accesos_bp.post("/ocr_articulo_concesionado")
async def post_ocr_articulo_concesionado(request: Request):
    payload = _ocr_payload(request)
    res = service.ocr_articulo_concesionado(
        image_source=payload.get('image_source'),
        extra_instructions=payload.get('extra_instructions'),
        model=payload.get('model', 'google/gemini-2.5-flash-lite'),
    )
    return json(res, status=res.get('status_code', 200))

# ============================================
# Hooks de formulario (migrados de scripts que corrian on-save)
# Reciben las respuestas ACTUALES del formulario y regresan
# {"status": 101, "replace_ans": {...}} para que la plataforma
# reemplace las respuestas antes de finalizar el guardado.
# ============================================

@accesos_bp.post("/bitacora_incidencias")
async def post_bitacora_incidencias_hook(request: Request):
    payload = _ocr_payload(request)
    answers = payload.get("answers", {})
    answers[service.incidence_fields['total_deposito_incidencia']] = service.calcula_total_depositos(answers=answers)
    return json({"status": 101, "replace_ans": answers}, status=200)

# ============================================
# Stats (migrado de get_stats.py)
# ============================================

@accesos_bp.get("/get_stats")
async def get_get_stats(request: Request):
    area = request.args.get("area", "")
    location = request.args.get("location", "")
    page = request.args.get("page", "")
    records = service.get_page_stats(booth_area=area, location=location, page=page)
    return json({"data": records}, status=200)

# ============================================
# SMS (migrado de sms_status.py)
# ============================================

@accesos_bp.post("/send_cel_msj")
async def post_send_cel_msj(request: Request):
    # POST porque data_cel_msj es un dict.
    payload = _ocr_payload(request)
    data_cel_msj = payload.get("data_cel_msj", {})
    records = service.send_cel_msj(data_cel_msj)
    return json({"data": records}, status=200)

# ============================================
# Notas (migrado de notes.py)
# ============================================

@accesos_bp.post("/new_notes")
async def post_new_notes(request: Request):
    # POST porque data_notes es un dict.
    payload = _ocr_payload(request)
    records = service.create_note(payload.get("location", ""), payload.get("area", ""), payload.get("data_notes", {}))
    return json({"data": records}, status=200)

@accesos_bp.get("/get_notes")
async def get_get_notes(request: Request):
    location = request.args.get("location", "")
    area = request.args.get("area", "")
    allowed_params = ["status", "dateFrom", "dateTo"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    limit = request.args.get("limit")
    offset = request.args.get("offset")
    if limit is not None:
        filters['limit'] = int(limit)
    if offset is not None:
        filters['offset'] = int(offset)
    records = service.get_list_notes(location, area, **filters)
    return json({"data": records}, status=200)

@accesos_bp.post("/update_note")
async def post_update_note(request: Request):
    # POST porque data_update es un dict.
    payload = _ocr_payload(request)
    records = service.update_notes(payload.get("data_update", {}), payload.get("folio", ""))
    return json({"data": records}, status=200)

# ============================================
# Checkin/Checkout de caseta (migrado de boot_checkin.py)
# ============================================

def _get_from_answers(answers, key):
    """Busca un valor dentro de `answers` por una key con notacion de puntos
    (equivalente a self.get_answer(key) de linkaform_api, sin depender del
    estado compartido de `service.answers`)."""
    d = answers
    for k in (key or '').split('.'):
        if not isinstance(d, dict):
            return None
        d = d.get(k)
        if d is None:
            return None
    return d

@accesos_bp.post("/boot_checkin")
async def post_boot_checkin(request: Request):
    payload = _ocr_payload(request)
    location = payload.get('location')
    area = payload.get('area')
    employee_list = payload.get('support_guards', [])
    checkin_id = payload.get('checkin_id')
    checkin_type = payload.get('checkin_type')
    answers = payload.get('answers', {})

    if checkin_type and checkin_type not in ('in', 'out'):
        return json({"error": "Checking type can ONLY be 'in' or 'out'"}, status=400)
    if not location:
        location = _get_from_answers(answers, service.checkin_fields['cat_location'])
    if not area:
        area = _get_from_answers(answers, service.checkin_fields['cat_area'])
    if not checkin_type:
        checkin_type = _get_from_answers(answers, service.checkin_fields['checkin_type'])
    if not checkin_type:
        return json({
            "exception": {
                service.checkin_fields['checkin_type']: {"msg": ["Es requerido indicar el tipo de checking"], "label": "Estatus", "error": []}
            }
        }, status=400)

    if checkin_type == "in":
        records = service.do_checkin(location, area, employee_list)
    else:
        records = service.do_checkout(checkin_id, location, area, employee_list)
    return json({"data": records}, status=200)

# ============================================
# Articulos concesionados (migrado de articulos_consecionados.py)
# ============================================

@accesos_bp.post("/new_article")
async def post_new_article(request: Request):
    payload = _ocr_payload(request)
    records = service.create_article_concessioned(payload.get("data_article", {}))
    return json({"data": records}, status=201)

@accesos_bp.get("/get_articles")
async def get_get_articles(request: Request):
    allowed_params = ["location", "area", "status", "dateFrom", "dateTo", "filterDate"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    records = service.get_list_articulos_concesionados(**filters)
    return json({"data": records}, status=200)

@accesos_bp.post("/update_article")
async def post_update_article(request: Request):
    payload = _ocr_payload(request)
    folio = payload.get("folio", [])
    if not isinstance(folio, list):
        folio = [folio] if folio else []
    records = service.update_article_concessioned(payload.get("data_article_update", {}), folio)
    return json({"data": records}, status=200)

@accesos_bp.get("/delete_article")
async def get_delete_article(request: Request):
    folio = request.args.getlist("folio")
    records = service.delete_article_concessioned(folio)
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogo_tipo_concesion")
async def get_catalogo_tipo_concesion(request: Request):
    location = request.args.get("location", "")
    tipo = request.args.get("tipo", "")
    records = service.catalogo_tipo_concesion(location, tipo=tipo)
    return json({"data": records}, status=200)

@accesos_bp.post("/assigne_bitacora")
async def post_assigne_bitacora_hook(request: Request):
    payload = _ocr_payload(request)
    answers = payload.get("answers", {})
    record_id = payload.get("record_id")
    records = service.assigne_bitacora(answers, record_id)
    return json({"data": records}, status=200)

# ============================================
# Paqueteria (migrado de paqueteria.py)
# ============================================

@accesos_bp.post("/nuevo_paquete")
async def post_nuevo_paquete(request: Request):
    payload = _ocr_payload(request)
    records = service.create_paquete(payload.get("data_paquete", {}))
    return json({"data": records}, status=201)

@accesos_bp.get("/get_paquetes")
async def get_get_paquetes(request: Request):
    allowed_params = ["location", "area", "status", "dateFrom", "dateTo", "filterDate"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    records = service.get_paquetes(**filters)
    return json({"data": records}, status=200)

@accesos_bp.post("/actualizar_paquete")
async def post_actualizar_paquete(request: Request):
    payload = _ocr_payload(request)
    records = service.update_paquete(payload.get("data_paquete_actualizar", {}), payload.get("folio"))
    return json({"data": records}, status=200)

@accesos_bp.get("/eliminar_paquete")
async def get_eliminar_paquete(request: Request):
    folio = request.args.get("folio")
    records = service.delete_paquete(folio)
    return json({"data": records}, status=200)

@accesos_bp.get("/get_catalogo_paquetes")
async def get_get_catalogo_paquetes(request: Request):
    records = service.get_catalogo_paquetes()
    return json({"data": records}, status=200)

# ============================================
# Gafetes/Lockers (migrado de gafetes_lockers.py)
# ============================================

@accesos_bp.post("/update_gafet_status")
async def post_update_gafet_status_hook(request: Request):
    payload = _ocr_payload(request)
    records = service.update_gafet_status(answers=payload.get("answers", {}))
    return json({"data": records}, status=200)

@accesos_bp.post("/new_badge")
async def post_new_badge(request: Request):
    payload = _ocr_payload(request)
    records = service.create_badge(payload.get("data_gafete", {}))
    return json({"data": records}, status=201)

@accesos_bp.get("/get_gafetes")
async def get_get_gafetes(request: Request):
    allowed_params = ["status", "location", "area", "gafete_id"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    # legacy siempre pasa 'status' explicitamente (aunque sea None), por lo que
    # el default 'Disponible' de get_gafetes nunca se aplica; si el query string
    # no trae 'status' debemos forzar None para igualar ese comportamiento.
    filters.setdefault("status", None)
    limit = request.args.get("limit")
    skip = request.args.get("skip")
    if limit is not None:
        filters['limit'] = int(limit)
    if skip is not None:
        filters['skip'] = int(skip)
    records = service.get_gafetes(**filters)
    return json({"data": records}, status=200)

@accesos_bp.get("/get_lockers")
async def get_get_lockers(request: Request):
    allowed_params = ["status", "location", "area", "tipo_locker", "locker_id"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    # igual que en get_gafetes: legacy siempre pasa 'status' y 'tipo_locker'
    # explicitamente (aunque sean None), por lo que sus defaults ('Disponible'
    # y 'Locker') nunca se aplican en legacy; forzamos None si faltan en el query.
    filters.setdefault("status", None)
    filters.setdefault("tipo_locker", None)
    limit = request.args.get("limit")
    skip = request.args.get("skip")
    if limit is not None:
        filters['limit'] = int(limit)
    if skip is not None:
        filters['skip'] = int(skip)
    records = service.get_lockers(**filters)
    return json({"data": records}, status=200)

@accesos_bp.get("/deliver_badge")
async def get_deliver_badge(request: Request):
    folio = request.args.get("folio")
    records = service.deliver_badge(folio)
    return json({"data": records}, status=200)

# ============================================
# Articulos perdidos (migrado de articulos_perdidos.py)
# ============================================

@accesos_bp.post("/nuevo_articulo")
async def post_nuevo_articulo(request: Request):
    payload = _ocr_payload(request)
    records = service.create_article_lost(payload.get("data_article", {}))
    return json({"data": records}, status=201)

@accesos_bp.get("/get_articles_perdidos")
async def get_get_articles_perdidos(request: Request):
    location = request.args.get("location", "")
    area = request.args.get("area", "")
    status = request.args.get("status", "")
    allowed_params = ["dateFrom", "dateTo", "filterDate"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    records = service.get_list_article_lost(location, area, status, **filters)
    return json({"data": records}, status=200)

@accesos_bp.post("/update_article_perdido")
async def post_update_article_perdido(request: Request):
    payload = _ocr_payload(request)
    records = service.update_article_lost(payload.get("data_article_update", {}), payload.get("folio"))
    return json({"data": records}, status=200)

@accesos_bp.get("/delete_article_perdido")
async def get_delete_article_perdido(request: Request):
    folio = request.args.getlist("folio")
    records = service.delete_article_lost(folio)
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogo_tipo_articulo")
async def get_catalogo_tipo_articulo(request: Request):
    tipo = request.args.get("tipo", "")
    records = service.catalogo_tipo_articulo(tipo)
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogo_area_empleado")
async def get_catalogo_area_empleado(request: Request):
    location = request.args.get("location", "")
    records = service.catalogo_config_area_empleado(bitacora='Objetos Perdidos', location=location)
    return json({"data": records}, status=200)

# ============================================
# Fallas (migrado de fallas.py)
# ============================================

@accesos_bp.post("/new_failure")
async def post_new_failure(request: Request):
    payload = _ocr_payload(request)
    records = service.create_failure(payload.get("data_failure", {}))
    return json({"data": records}, status=201)

@accesos_bp.get("/get_fallas")
async def get_get_fallas(request: Request):
    location = request.args.get("location", "")
    area = request.args.get("area", "")
    allowed_params = ["status", "folio", "dateFrom", "dateTo", "filterDate"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    records = service.get_list_fallas(location, area, **filters)
    return json({"data": records}, status=200)

@accesos_bp.post("/update_failure_seguimiento")
async def post_update_failure_seguimiento(request: Request):
    payload = _ocr_payload(request)
    records = service.update_failure_seguimiento(
        location=payload.get("location"),
        area=payload.get("area"),
        status=payload.get("status"),
        folio=payload.get("folio"),
        falla_grupo_seguimiento=payload.get("falla_grupo_seguimiento"),
    )
    return json({"data": records}, status=200)

@accesos_bp.post("/update_failure")
async def post_update_failure(request: Request):
    payload = _ocr_payload(request)
    records = service.update_failure(payload.get("data_failure_update", {}), payload.get("folio"))
    return json({"data": records}, status=200)

@accesos_bp.get("/delete_failure")
async def get_delete_failure(request: Request):
    folio = request.args.getlist("folio")
    records = service.delete_failure(folio)
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogo_area_empleado_apoyo")
async def get_catalogo_area_empleado_apoyo(request: Request):
    employees = service.Employee.get_employee_data()
    records = [employee.get('worker_name') for employee in employees]
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogo_fallas")
async def get_catalogo_fallas(request: Request):
    tipo = request.args.get("tipo", "")
    records = service.catalogo_falla(tipo)
    return json({"data": records}, status=200)

# ============================================
# Pase de acceso (variantes de pase_de_acceso_use_api.py)
# ============================================

@accesos_bp.get("/catalogo_vehiculos_pase")
async def get_catalogo_vehiculos_pase(request: Request):
    records = service.catalogo_vehiculos()
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogo_tipo_equipo")
async def get_catalogo_tipo_equipo(request: Request):
    records = service.catalogo_tipo_equipo()
    return json({"data": records}, status=200)

@accesos_bp.get("/get_pass_img")
async def get_get_pass_img(request: Request):
    qr_code = request.args.get("qr_code")
    records = service.get_pass_img(qr_code)
    return json({"data": records}, status=200)

# ============================================
# Incidencias (migrado de incidencias.py)
# ============================================

@accesos_bp.post("/nueva_incidencia")
async def post_nueva_incidencia(request: Request):
    payload = _ocr_payload(request)
    records = service.create_incidence(payload.get("data_incidence", {}))
    return json({"data": records}, status=201)

@accesos_bp.get("/get_incidences")
async def get_get_incidences(request: Request):
    location = request.args.get("location", "")
    area = request.args.get("area", "")
    prioridades = request.args.getlist("prioridades")
    allowed_params = ["dateFrom", "dateTo", "filterDate", "folio"]
    filters = {k: request.args.get(k) for k in allowed_params if request.args.get(k) is not None}
    records = service.get_list_incidences(location, area, prioridades=prioridades, **filters)
    return json({"data": records}, status=200)

@accesos_bp.post("/update_incidence")
async def post_update_incidence(request: Request):
    payload = _ocr_payload(request)
    records = service.update_incidence(payload.get("data_incidence_update", {}), payload.get("folio"))
    return json({"data": records}, status=200)

@accesos_bp.post("/update_incidence_seguimiento")
async def post_update_incidence_seguimiento(request: Request):
    payload = _ocr_payload(request)
    records = service.update_incidence_seguimiento(
        folio=payload.get("folio"),
        incidencia_grupo_seguimiento=payload.get("seguimientos_incidencia", []),
        estatus=payload.get("estatus"),
        location=payload.get("location"),
        area=payload.get("area"),
    )
    return json({"data": records}, status=200)

@accesos_bp.get("/delete_incidence")
async def get_delete_incidence(request: Request):
    folio = request.args.getlist("folio")
    records = service.delete_incidence(folio)
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogo_area_empleado_incidencias")
async def get_catalogo_area_empleado_incidencias(request: Request):
    location = request.args.get("location", "")
    records = service.catalogo_config_area_empleado(bitacora='Incidencias', location=location)
    return json({"data": records}, status=200)

@accesos_bp.get("/catalogo_incidencias")
async def get_catalogo_incidencias(request: Request):
    cat = request.args.get("cat")
    sub_cat = request.args.get("sub_cat")
    records = service.catalogo_incidencias(cat=cat, sub_cat=sub_cat)
    return json({"data": records}, status=200)

# ============================================
# Update QR (migrado de update_qr.py, hook de formulario)
# ============================================

@accesos_bp.post("/update_qr")
async def post_update_qr_hook(request: Request):
    payload = _ocr_payload(request)
    answers = payload.get("answers", {})
    data = service.format_data_area(answers)
    response = service.update_area_tag_id(data)
    answers[service.f['status_new_qr']] = response.get('status', 'error')
    answers[service.f['details_new_qr']] = response.get('details', 'No details provided')
    return json({"status": 101, "replace_ans": answers}, status=200)

# ============================================
# Checkout masivo automatico (migrado de check_out_all.py)
# ============================================

@accesos_bp.post("/check_out_all")
async def post_check_out_all(request: Request):
    records = service.do_checkout_all()
    return json({"response": records}, status=200)

@accesos_bp.post("/check_out_all_users")
async def post_check_out_all_users(request: Request):
    # Ya existia en service.py (check_out_all_users/set_checkout_all_users, cierre
    # automatico de VISITANTES tras 2hrs), pero nunca quedo conectado a ninguna ruta.
    records = service.check_out_all_users()
    return json({"response": records}, status=200)

# ============================================
# Cierre automatico de rondines (migrado de close_rondines.py)
# ============================================

@accesos_bp.post("/close_rondines")
async def post_close_rondines(request: Request):
    rondines = service.get_rondines_by_status()
    if rondines:
        records = service.close_rondines(rondines)
    else:
        records = "No hay rondines para evaluar"
    return json({"response": records}, status=200)

# ============================================
# Google Wallet (migrado de create_pass_google_wallet.py)
# ============================================

@accesos_bp.post("/create_pass_google_wallet")
async def post_create_pass_google_wallet(request: Request):
    payload = _ocr_payload(request)
    qr_code = payload.get('qr_code', '')
    if not qr_code:
        return json({"exception": {"title": "Error", "msg": "No se proporciono el codigo QR"}}, status=400)

    data = service.get_pass_custom(qr_code=qr_code)
    visita_a = [i.get('nombre') for i in data.get('visita_a', [])]
    data_to_google_pass = {
        "nombre": data.get("nombre"),
        "visita_a": visita_a,
        "empresa": data.get("empresa"),
        "ubicaciones": data.get("ubicacion"),
        "num_accesos": data.get("limite_de_acceso"),
        "fecha_desde": data.get("fecha_de_expedicion"),
        "fecha_hasta": data.get("fecha_de_caducidad"),
        "geolocations": data.get("ubicaciones_geolocation"),
    }
    google_wallet_pass_url = service.create_class_google_wallet(data=data_to_google_pass, qr_code=qr_code)

    if not google_wallet_pass_url:
        return json({"exception": {"title": "Error al crear el pase de Google Wallet", "msg": "No se pudo crear el pase de Google Wallet"}}, status=400)

    service.assign_google_pass_url(qr_code, google_wallet_pass_url)

    return json({
        "data": {"google_wallet_url": google_wallet_pass_url},
        "json": {"msg": "Pase de Google Wallet creado exitosamente."}
    }, status=200)

# ============================================
# Apple Wallet (migrado de create_pass_apple_wallet.py)
# ============================================

@accesos_bp.post("/create_pass_apple_wallet")
async def post_create_pass_apple_wallet(request: Request):
    payload = _ocr_payload(request)
    record_id = payload.get('record_id', '')
    file_url = service.create_pass_apple_wallet(record_id)
    return json({"status": 101, "file_url": file_url}, status=200)

# ============================================
# SMS nuevo proveedor (migrado de send_sms_new.py, hook de formulario)
# ============================================

@accesos_bp.post("/send_sms_new")
async def post_send_sms_new_hook(request: Request):
    payload = _ocr_payload(request)
    answers = payload.get("answers", {})
    qr_code = payload.get("record_id", "")
    pre_sms_value = payload.get('pre_sms', '')
    cuenta_value = payload.get('cuenta', '')
    pre_sms = pre_sms_value if isinstance(pre_sms_value, bool) else str(pre_sms_value).lower() == 'true'

    telefono_invitado = answers.get(service.mf['telefono_pase'], '')
    telefono_formateado = telefono_invitado[1:] if telefono_invitado else ''
    nombre_invitado = answers.get(service.mf['nombre_pase'], '')
    link_completar_pase = answers.get(service.pase_entrada_fields['link'], '')
    grupo_visitados = answers.get(service.mf['grupo_visitados'], [])
    nombre_visita_a = ''
    for visita_a in grupo_visitados:
        vista_catalog = visita_a.get(service.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID, {})
        nombre = vista_catalog.get(service.mf['nombre_empleado'])
        if nombre:
            if len(nombre_visita_a) > 0:
                nombre_visita_a += ', '
            nombre_visita_a += nombre

    ubicacion = answers.get(service.mf['grupo_ubicaciones_pase'], [])
    fecha_desde = answers.get(service.mf['fecha_desde_visita'], '')
    fecha_hasta = answers.get(service.mf['fecha_desde_hasta'], '')

    data_cel_msj = {
        'numero': telefono_formateado,
        'nombre': nombre_invitado,
        'link': link_completar_pase,
        'visita_a': nombre_visita_a,
        'ubicacion': ubicacion,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'qr_code': qr_code,
        'pre_sms': pre_sms
    }

    seleccion_de_visitante = answers.get(service.pase_entrada_fields['tipo_visita'])
    if seleccion_de_visitante == 'Buscar visitantes registrados':
        visitante_registrado = answers.get(service.pase_entrada_fields['catalogo_visitante_registrado'], {})
        nombre_visitante_registrado = visitante_registrado.get(service.pase_entrada_fields['nombre_visitante_registrado'], '')
        telefono_vistante_registrado = visitante_registrado.get(service.mf['telefono_visita'], [])[0][0]
        data_cel_msj['nombre'] = nombre_visitante_registrado
        data_cel_msj['numero'] = telefono_vistante_registrado

    mensaje, phone_to = service.format_pass_sms(data_cel_msj=data_cel_msj, pre_sms=pre_sms, account=cuenta_value)

    data_cel_msj['numero'] = telefono_invitado
    response = service.send_sms_alprotel(phone_number=phone_to, message=mensaje, data_cel_msj=data_cel_msj, pre_sms=pre_sms, account=cuenta_value)

    return json({"status": 101, "response_sms": response}, status=200)

# ============================================
# SMS masivo/MasivApp (migrado de send_sms_masiv.py, hook de formulario)
# ============================================

@accesos_bp.post("/send_sms_masiv")
async def post_send_sms_masiv_hook(request: Request):
    payload = _ocr_payload(request)
    answers = payload.get("answers", {})
    qr_code = payload.get("record_id", "")
    pre_sms_value = payload.get('pre_sms', '')
    cuenta_value = payload.get('cuenta', '')
    pre_sms = pre_sms_value if isinstance(pre_sms_value, bool) else str(pre_sms_value).lower() == 'true'

    sms_creds = service.lkf_api.get_sms_creds(use_api_key=True, jwt_settings_key=False)
    masiv_user = sms_creds.get('json', {}).get('masiv_user', '')
    masiv_token = sms_creds.get('json', {}).get('masiv_token', '')

    telefono_invitado = answers.get(service.mf['telefono_pase'], '').replace("+", "")
    nombre_invitado = answers.get(service.mf['nombre_pase'], '')
    link_completar_pase = answers.get(service.pase_entrada_fields['link'], '')
    grupo_visitados = answers.get(service.mf['grupo_visitados'], [])
    nombre_visita_a = ''
    for visita_a in grupo_visitados:
        vista_catalog = visita_a.get(service.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID, {})
        nombre = vista_catalog.get(service.mf['nombre_empleado'])
        if nombre:
            if len(nombre_visita_a) > 0:
                nombre_visita_a += ', '
            nombre_visita_a += nombre

    ubicaciones_list = []
    ubicaciones_group = answers.get(service.mf['grupo_ubicaciones_pase'], '')
    for item in ubicaciones_group:
        ubicacion = item.get(service.Location.UBICACIONES_CAT_OBJ_ID, {}).get(service.Location.f['location'], '')
        ubicaciones_list.append(ubicacion)

    if len(ubicaciones_list) == 1:
        ubicaciones_str = ubicaciones_list[0]
    elif len(ubicaciones_list) == 2:
        ubicaciones_str = f"{ubicaciones_list[0]} y {ubicaciones_list[1]}"
    elif len(ubicaciones_list) > 2:
        ubicaciones_str = f"{ubicaciones_list[0]}, {ubicaciones_list[1]} y {len(ubicaciones_list) - 2} más"
    else:
        ubicaciones_str = ''

    fecha_desde = answers.get(service.mf['fecha_desde_visita'], '')
    fecha_hasta = answers.get(service.mf['fecha_desde_hasta'], '')

    data_cel_msj = {
        'numero': telefono_invitado,
        'nombre': nombre_invitado,
        'link': link_completar_pase,
        'visita_a': nombre_visita_a,
        'ubicacion': ubicaciones_str,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'qr_code': qr_code,
        'pre_sms': pre_sms
    }

    seleccion_de_visitante = answers.get(service.pase_entrada_fields['tipo_visita'])
    if seleccion_de_visitante == 'Buscar visitantes registrados':
        visitante_registrado = answers.get(service.pase_entrada_fields['catalogo_visitante_registrado'], {})
        nombre_visitante_registrado = visitante_registrado.get(service.pase_entrada_fields['nombre_visitante_registrado'], '')
        telefono_vistante_registrado = visitante_registrado.get(service.mf['telefono_visita'], [])[0][0]
        data_cel_msj['nombre'] = nombre_visitante_registrado
        data_cel_msj['numero'] = telefono_vistante_registrado

    mensaje, phone_to = service.format_message(data_cel_msj=data_cel_msj, pre_sms=pre_sms, account=cuenta_value)
    response = service.send_sms_masiv(para=phone_to, texto=mensaje, masiv_user=masiv_user, masiv_token=masiv_token)

    return json({"status": 101, "response_sms": response}, status=200)

# ============================================
# Bitacora de rondines (migrado de bitacora_rondines.py, hook de formulario)
# ============================================

@accesos_bp.post("/bitacora_rondines")
async def post_bitacora_rondines_hook(request: Request):
    from bson import ObjectId as _ObjectId
    payload = _ocr_payload(request)
    current_record = payload.get("current_record", {})
    answers = current_record.get('answers', {})
    if not answers:
        answers = payload.get('answers', {})

    record_id = current_record.get('_id')
    if isinstance(record_id, dict):
        record_id = record_id.get('$oid')
    if not record_id:
        record_id = str(_ObjectId())

    answers = service.calcluta_tiempo_traslados(answers)

    is_child_record = answers.get(service.rondin_keys['registro_padre'])
    if not is_child_record:
        if answers.get(service.f['estatus_del_recorrido']) == 'programado':
            if not answers.get(service.f['areas_del_rondin']):
                service.get_and_set_areas_recorrido(answers)
            if not answers.get(service.USUARIOS_OBJ_ID):
                service.get_and_set_user(answers, record_id, current_record)

    return json({
        "status": 101,
        "replace_ans": answers,
        "metadata": {"id": record_id}
    }, status=200)

# ============================================
# Programacion de recorridos/rondines (migrado de config_recorridos.py, hook)
# Usa la clase Schedule (base/app.py), no Accesos.
# ============================================

@accesos_bp.post("/config_recorridos")
async def post_config_recorridos_hook(request: Request):
    payload = _ocr_payload(request)
    answers = payload.get("answers", {})
    current_record = payload.get("current_record", {})

    res = schedule_service.schedule_task_recorrido(answers=answers, current_record=current_record)
    data = res.get('data') if res else None

    if not res or res.get('status_code') == 0:
        return json({"msg": "Ningun cambio"}, status=200)
    elif res.get('status_code') == 200:
        if res.get('deleted'):
            answers[schedule_service.f['status_cron']] = 'eliminado'
        else:
            answers[schedule_service.f['cron_id']] = data.get('dag_id')
            answers.update(schedule_service.get_dag_dates(data))
            if res.get('is_paused') == True:
                answers[schedule_service.f['status_cron']] = 'pausado'
            else:
                answers[schedule_service.f['status_cron']] = 'corriendo'
        return json({"status": 101, "replace_ans": answers}, status=200)
    else:
        msg_error_app = "Something went wrong!!!"
        if res.get('json', {}).get('error') or res.get('status_code') == 400:
            if res.get('json', {}).get('error'):
                msg_error_app = res['json']['error']
            else:
                msg_error_app = res['json'].get('message', 'Something went wrong!!!')
        else:
            msg_error_app = {
                "error": {"msg": [msg_error_app], "label": "Cron Id", "error": [msg_error_app]},
            }
        return json({"exception": msg_error_app}, status=400)

# ============================================
# Check de rondines por tag fisico (migrado de create_record_check.py)
# ============================================

@accesos_bp.post("/add_record_check")
async def post_add_record_check(request: Request):
    payload = _ocr_payload(request)
    form_information = payload.get('formInformation', {})
    folio_update = payload.get('folioUpdate', '')
    records = service.set_add_record_check(form_information, folio_update)
    return json({"data": records}, status=200)

@accesos_bp.post("/add_inspection_check")
async def post_add_inspection_check(request: Request):
    payload = _ocr_payload(request)
    form_information = payload.get('formInformation', {})
    records = service.set_add_inspection_record(form_information)
    return json({"data": records}, status=200)

@accesos_bp.post("/add_record_bitacora_tag")
async def post_add_record_bitacora_tag(request: Request):
    payload = _ocr_payload(request)
    records = service.set_add_record_bitacora_tag(payload.get('tagId', ''), payload.get('config', ''))
    return json({"data": records}, status=200)

@accesos_bp.get("/get_catalog_tag")
async def get_get_catalog_tag(request: Request):
    tag_id = request.args.get('tagId', '')
    records = service.get_information_catalog(tag_id)
    return json({"data": records}, status=200)

@accesos_bp.get("/get_config_rondines_tag")
async def get_get_config_rondines_tag(request: Request):
    tag_id = request.args.get('tagId', '')
    records = service.get_config_rondines(tag_id)
    return json({"data": records}, status=200)

@accesos_bp.get("/update_record_bitacora_tag")
async def get_update_record_bitacora_tag(request: Request):
    folio_update = request.args.get('folioUpdate', '')
    records = service.update_record_rondin_tag(folio_update)
    return json({"data": records}, status=200)

@accesos_bp.get("/get_information_tag")
async def get_get_information_tag(request: Request):
    tag_id = request.args.get('tagId', '')
    records = service.get_data_tag(tag_id)
    return json({"data": records}, status=200)

@accesos_bp.post("/update_information_tag")
async def post_update_information_tag(request: Request):
    payload = _ocr_payload(request)
    records = service.set_update_tag(
        payload.get('tagId', ''),
        payload.get('listImagesDic', []),
        payload.get('idCatalog', ''),
    )
    return json({"data": records}, status=200)

# ============================================
# Actualizacion/creacion de areas (migrado de update_area.py, hook)
# ============================================

@accesos_bp.post("/update_area")
async def post_update_area_hook(request: Request):
    payload = _ocr_payload(request)
    current_record = payload.get("current_record", {})
    answers = current_record.get('answers', {}) or payload.get('answers', {})

    data = service.format_data_area_config(answers)

    geolocation_raw = current_record.get('geolocation', [])
    geolocation_area = None
    if geolocation_raw:
        geolocation_area = {"latitude": geolocation_raw[1], "longitude": geolocation_raw[0]}

    statuss = 'ok'
    status_comment = ''

    if data.get('qr_area') and not data.get('ubicacion') and not data.get('area'):
        qr_data = service.get_area_ubicacion_record(tag_id_area=data.get('qr_area'))
        if qr_data:
            data['ubicacion'] = qr_data.get('ubicacion', '')
            data['area'] = qr_data.get('area', '')

    nueva_area = data.get('nombre_nueva_area') or None

    if nueva_area:
        service.create_new_area(data, geolocation_area=geolocation_area)
        data['area'] = data.get('nombre_nueva_area')
    else:
        search_area = None
        if data.get('area'):
            search_area = service.get_area_ubicacion_record(ubicacion=data.get('ubicacion'), area=data.get('area'))

        if not search_area:
            msg = 'Revisa el catalogo, no se encontró el área seleccionada en la forma Areas de las Ubicaciones.'
            return json({"exception": {"title": "Área no encontrada", "msg": msg}}, status=400)

        searched_ubicacion = service.unlist(search_area.get('ubicacion', ''))
        searched_area = service.unlist(search_area.get('area', ''))
        if not (search_area and searched_ubicacion == data.get('ubicacion') and searched_area == data.get('area')):
            msg = 'No se encontró el área seleccionada en la forma Areas de las Ubicaciones.'
            msg += 'Intenta creandola primero y solicita a soporte borrar el area creada en catalogo.'
            return json({"exception": {"title": "Área no encontrada", "msg": msg}}, status=400)

    exists_qr = False
    is_a_different_area = True
    if data.get('qr_area'):
        qr_data = service.get_area_ubicacion_record(tag_id_area=data.get('qr_area'))
        if qr_data and qr_data.get('tag_id_area') == data.get('qr_area'):
            if qr_data.get('ubicacion') == data.get('ubicacion') and qr_data.get('area') == data.get('area'):
                is_a_different_area = False
            exists_qr = True

    if exists_qr and is_a_different_area:
        return json({"exception": {"title": "QR ya asignado", "msg": "Ya se ha registrado este QR en otra area."}}, status=400)
    elif data.get('area'):
        service.update_area_config(data)

    answers[service.f['status_details']] = statuss
    answers[service.f['status_details_message']] = status_comment

    return json({"status": 101, "replace_ans": answers}, status=200)

# ============================================
# Checkin manual con horarios (migrado de check_in_manual.py, hook)
# ============================================

@accesos_bp.post("/check_in_manual")
async def post_check_in_manual_hook(request: Request):
    payload = _ocr_payload(request)
    current_record = payload.get("current_record", {})
    answers = current_record.get('answers', {}) or payload.get('answers', {})

    user_id = payload.get('user_id') or service.user.get('user_id')
    timezone = payload.get('timezone', 'America/Mexico_City')
    record_id = current_record.get('_id')
    if isinstance(record_id, dict):
        record_id = record_id.get('$oid')

    option = answers.get(service.f['option_checkin'], '')

    if option == 'iniciar_turno':
        answers = service.check_in_manual(answers, user_id, timezone)
    elif option == 'cerrar_turno':
        answers = service.check_out_manual(answers, user_id, timezone, record_id)

    if answers.get(service.f['start_shift']) and answers.get(service.f['end_shift']) \
            and not answers.get(service.f['horas_trabajadas']):
        answers = service.set_work_hours(answers, answers.get(service.f['start_shift']), answers.get(service.f['end_shift']))

    return json({"status": 101, "replace_ans": answers}, status=200)

# ============================================
# Check de ubicacion de rondin (migrado de check_ubicacion_rondin.py, hook)
# ============================================

@accesos_bp.post("/check_ubicacion_rondin")
async def post_check_ubicacion_rondin_hook(request: Request):
    payload = _ocr_payload(request)
    current_record = payload.get("current_record", {})
    answers = current_record.get('answers', {}) or payload.get('answers', {})
    folio = current_record.get('folio', '')

    record_id = current_record.get('_id')
    if isinstance(record_id, dict):
        record_id = record_id.get('$oid')

    cat_area_rondin = answers.get(service.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {})
    nombre_area_rondin = service.unlist(cat_area_rondin.get(service.f['nombre_area'], []))
    nombre_ubicacion_rondin = service.unlist(cat_area_rondin.get(service.Location.f['location'], []))

    nombres_recorrido = service.get_recorridos_by_area(nombre_ubicacion_rondin, nombre_area_rondin)
    rondin = service.search_rondin_by_name(names=nombres_recorrido)

    if not rondin:
        if nombres_recorrido:
            service.create_rondin(answers, nombre_area_rondin, record_id, nombres_recorrido)
    else:
        rondin_areas = service.unlist(rondin).get('areas_del_rondin', [])
        for area in rondin_areas:
            if nombre_area_rondin == area.get('incidente_area', ''):
                fecha_area_registrada = area.get('fecha_hora_inspeccion_area', '')
                if fecha_area_registrada:
                    tz = pytz.timezone('America/Mexico_City')
                    fecha_reg = datetime.strptime(fecha_area_registrada, '%Y-%m-%d %H:%M:%S')
                    fecha_reg = tz.localize(fecha_reg)
                    ahora = datetime.now(tz)
                    ha_pasado_una_hora = (ahora - fecha_reg) >= timedelta(hours=1)
                    if ha_pasado_una_hora:
                        rondines = service.get_rondines_by_status()
                        service.close_rondines(rondines)
                        service.create_rondin(answers, nombre_area_rondin, record_id, nombres_recorrido)
                        nombre_area_rondin = ''
                    else:
                        nombre_area_rondin = ''

        if nombre_area_rondin:
            service.check_area_in_rondin(data_rondin=answers, area_rondin=nombre_area_rondin, rondin=rondin, record_id=record_id)

    grupo_incidencias = answers.get(service.f['grupo_incidencias_check'], [])
    if grupo_incidencias:
        format_grupo_incidencias = service.format_grupo_incidencias(grupo_incidencias, answers, folio)
        for incidencia in format_grupo_incidencias:
            service.create_incidence_record(answers=incidencia)

    # El script legacy no devuelve replace_ans (solo tiene efectos secundarios
    # en otros registros: BITACORA_RONDINES, BITACORA_INCIDENCIAS), asi que
    # aqui solo se confirma que el hook corrio, sin tocar las respuestas.
    return json({"status": 200, "msg": "ok"}, status=200)

# ============================================
# Rondines cache: resolucion de checks concurrentes por rondin
# (migrado de rondines_cache.py, hook, use_api). Implementacion alterna
# a /check_ubicacion_rondin: en vez de actualizar el rondin directo, junta
# los checks de varios guardias en una cache (rondin_caches) y resuelve un
# "ganador" por ubicacion+usuario antes de crear/actualizar la bitacora.
# ============================================

@accesos_bp.post("/rondines_cache")
async def post_rondines_cache_hook(request: Request):
    payload = _ocr_payload(request)
    current_record = payload.get("current_record", {})
    answers = current_record.get('answers', {}) or payload.get('answers', {})

    record_id = current_record.get('_id')
    if isinstance(record_id, dict):
        record_id = record_id.get('$oid')
    record_id = str(record_id) if record_id else record_id

    user_name = current_record.get('created_by_name', '')
    user_id = current_record.get('created_by_id', 0)
    user_email = current_record.get('created_by_email', '')
    timestamp = current_record.get('start_timestamp', '')
    timezone = current_record.get('timezone', 'America/Mexico_City')
    folio = current_record.get('folio', '')
    tz = pytz.timezone(timezone)

    location_data = answers.get(service.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {})
    location = service.unlist(location_data.get(service.Location.f['location'], ''))
    check_area = service.unlist(location_data.get(service.Location.f['area'], ''))

    #! 1. Obtener los recorridos existentes para el area ejecutada
    recorridos = service.search_rondin_by_area(location, check_area)
    if not recorridos:
        service.update_check_ubicacion(record_id)
        text_no_conf = 'Esta area no pertenece a este rondin.'
        comentario_actual = answers.get(service.f['comentario_check_area'], '')
        answers[service.f['comentario_check_area']] = (
            comentario_actual + '\n' + text_no_conf if comentario_actual else text_no_conf
        )

    #! 2. Se crea un cache con la informacion de el check
    service.create_cache(record_id, user_name, location, folio, timestamp, answers)
    await asyncio.sleep(5)
    cache = service.search_cache()

    #! 3. Se obtienen las ubicaciones(sin repetir) del cache
    service.get_locations_cache(cache)

    #! 4. Se verifica si ya hay ganadores y si no se buscan por ubicacion y si ya tiene tiempo el check
    winners = service.select_winner(cache)
    winners_ids = [winner.get('winner_id') for winner in winners]
    service.set_winners(winners_ids)
    cache = service.search_cache()

    #! 5. Verificar si eres un ganador
    if record_id in winners_ids:
        selected_winner = [winner for winner in winners if winner.get('winner_id') == record_id]
        winner = selected_winner[0] if selected_winner else None
        if winner:
            winner_timestamp = winner.get('winner_record', {}).get('timestamp')
            winner_date = winner_timestamp and datetime.fromtimestamp(winner_timestamp, tz).strftime('%Y-%m-%d %H:%M:%S')
            now = datetime.now(tz)
            if winner_date:
                winner_dt = tz.localize(datetime.strptime(winner_date, '%Y-%m-%d %H:%M:%S'))
                diff = now - winner_dt
                winner_hour = winner_dt.strftime('%Y-%m-%d %H:%M:%S')

                #! Verificar si hay rondines que cerrar
                rondines = service.get_rondines_by_status()
                service.close_rondines(rondines)

                #! 7. Verificamos si ha pasado mas de 15 minutos de este check pasado
                if diff.total_seconds() > 900 and winner.get('type') == 'closed_winner':
                    #! 7-1 Se busca una bitacora cerrada para la hora en que se hizo este check
                    bitacora = service.search_closed_bitacora_by_time(winner.get('location'), user_name, winner_hour)
                    await asyncio.sleep(5)
                    winner_checks = service.search_cache(winner_id=winner.get('winner_id'), location=winner.get('location'), user_name=user_name)
                    #! 7-1-1 Se filtran los checks que pertenezcan a la hora del check ganador
                    window_seconds = 30 * 60  # 30 minutos
                    start_dt = winner_dt
                    end_dt = winner_dt + timedelta(seconds=window_seconds)
                    filter_winner_checks = []
                    for check in winner_checks:
                        check_timestamp = check.get('timestamp')
                        if not check_timestamp:
                            continue
                        check_dt = datetime.fromtimestamp(check_timestamp, tz)
                        if start_dt <= check_dt <= end_dt:
                            filter_winner_checks.append(check)
                    winner_checks = filter_winner_checks
                    winner_checks.append(winner.get('winner_record', {}))
                    if bitacora:
                        #! 7-1-2. Actualizar una bitacora ya cerrada con los checks perdidos
                        service.update_bitacora(winner_checks, bitacora, current_record, timezone, user_id, user_email, timestamp)
                    else:
                        #! 7-1-3. Crea una bitacora ya cerrada con los checks perdidos
                        winner_record = winner.get('winner_record', {})
                        winner_record.update({'checks': winner_checks})
                        service.create_bitacora(winner_record, recorridos, location, timezone, user_name, user_id, user_email, check_area, closed=True)
                    clear_ids = [check.get('_id') for check in winner_checks]
                    service.clear_cache(list_ids=clear_ids)
                else:
                    #! 7-2-1 Se busca una bitacora activa para la hora en que se hizo este check
                    bitacora = service.search_active_bitacora_by_rondin(recorridos, location, user_name)
                    await asyncio.sleep(5)
                    winner_checks = service.search_cache(winner_id=winner.get('winner_id'), location=winner.get('location'), user_name=user_name)
                    winner_checks.append(winner.get('winner_record', {}))
                    if bitacora:
                        #! 7-2-2. Actualizar una bitacora con los checks realizados
                        service.update_bitacora(winner_checks, bitacora, current_record, timezone, user_id, user_email, timestamp)
                    else:
                        #! 7-2-3. Crea una bitacora con los checks realizados
                        winner_record = winner.get('winner_record', {})
                        winner_record.update({'checks': winner_checks})
                        service.create_bitacora(winner_record, recorridos, location, timezone, user_name, user_id, user_email, check_area)
                    clear_ids = [check.get('_id') for check in winner_checks]
                    service.clear_cache(list_ids=clear_ids)

    # El script legacy no devuelve replace_ans mas alla del comentario de "area
    # no configurada" (efectos secundarios en BITACORA_RONDINES via cache).
    return json({"status": 101, "replace_ans": answers}, status=200)

# ============================================
# Rondines: API de gestion de recorridos (migrado de rondines.py)
# ============================================

def _bool_param(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() == 'true'

@accesos_bp.post("/create_rondin")
async def post_create_rondin(request: Request):
    payload = _ocr_payload(request)
    response = service.create_recorrido_rondin(payload.get("rondin_data", {}))
    return json({"data": response}, status=200)

@accesos_bp.post("/claim_rondin")
async def post_claim_rondin(request: Request):
    payload = _ocr_payload(request)
    ok, data = service.claim_rondin(payload.get("record_id", ""))
    return json({"success": ok, "data": data}, status=200 if ok else 400)

@accesos_bp.post("/create_incidencia_by_rondin")
async def post_create_incidencia_by_rondin(request: Request):
    payload = _ocr_payload(request)
    response = service.create_incidencia_by_rondin(payload.get("rondin_data", {}))
    return json({"data": response}, status=200)

@accesos_bp.post("/delete_rondin")
async def post_delete_rondin(request: Request):
    payload = _ocr_payload(request)
    response = service.delete_rondin(folio=payload.get("folio", ""))
    return json({"data": response}, status=200)

@accesos_bp.post("/edit_areas_rondin")
async def post_edit_areas_rondin(request: Request):
    payload = _ocr_payload(request)
    response = service.edit_areas_rondin(
        areas=payload.get("areas", []),
        folio=payload.get("folio", ""),
        record_id=payload.get("record_id", "")
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_recorridos")
async def get_get_recorridos(request: Request):
    response = service.get_recorridos(
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        area_details=_bool_param(request.args.get("area_details"), default=False),
        limit=int(request.args.get("limit", 20)),
        offset=int(request.args.get("offset", 0)),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_bitacora")
async def get_get_bitacora(request: Request):
    response = service.get_bitacora(
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        area_details=_bool_param(request.args.get("area_details"), default=False),
        limit=int(request.args.get("limit", 15)),
        offset=int(request.args.get("offset", 0)),
        ubicacion=request.args.get("ubicacion", ""),
        nombre_rondin=request.args.get("nombre_rondin", ""),
        timezone=request.args.get("timezone"),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_catalog_areas")
async def get_get_catalog_areas(request: Request):
    response = service.get_catalog_areas(ubicacion=request.args.get("ubicacion", ""))
    return json({"data": response}, status=200)

@accesos_bp.get("/get_all_checks")
async def get_get_all_checks(request: Request):
    response = service.get_all_checks(
        ubicacion=request.args.get("ubicacion", ""),
        nombre_rondin=request.args.get("nombre_rondin", ""),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_rondin_by_id")
async def get_get_rondin_by_id(request: Request):
    response = service.get_rondin_by_id(record_id=request.args.get("record_id", ""))
    return json({"data": response}, status=200)

@accesos_bp.get("/get_incidencias_rondines")
async def get_get_incidencias_rondines(request: Request):
    response = service.get_incidencias_rondines(
        location=request.args.get("ubicacion"),
        area=request.args.get("area"),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        limit=int(request.args.get("limit", 20)),
        offset=int(request.args.get("offset", 0)),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_rondines_images")
async def get_get_rondines_images(request: Request):
    areas = request.args.getlist("areas") or None
    response = service.get_rondines_images(
        location=request.args.get("ubicacion"),
        areas=areas,
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        limit=int(request.args.get("limit", 20)),
        offset=int(request.args.get("offset", 0)),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_bitacora_rondines")
async def get_get_bitacora_rondines(request: Request):
    response = service.get_bitacora_rondines(
        location=request.args.get("ubicacion"),
        nombre_rondin=request.args.get("nombre_rondin"),
        year=request.args.get("year"),
        month=request.args.get("month"),
        timezone=request.args.get("timezone"),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_check_by_id")
async def get_get_check_by_id(request: Request):
    response = service.get_check_by_id(
        record_id=request.args.get("record_id", ""),
        timezone=request.args.get("timezone"),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_bitacora_by_id")
async def get_get_bitacora_by_id(request: Request):
    response = service.get_bitacora_by_id(
        record_id=request.args.get("record_id", ""),
        timezone=request.args.get("timezone"),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_catalog_areas_formatted")
async def get_get_catalog_areas_formatted(request: Request):
    response = service.get_catalog_areas_formatted(ubicacion=request.args.get("ubicacion", ""))
    return json({"data": response}, status=200)

@accesos_bp.get("/catalago_grupos_recorridos")
async def get_catalago_grupos_recorridos(request: Request):
    response = service.catalago_grupos_recorridos()
    return json({"data": response}, status=200)

@accesos_bp.get("/catalogo_inspecciones")
async def get_catalogo_inspecciones(request: Request):
    response = service.catalogo_inspecciones()
    return json({"data": response}, status=200)

@accesos_bp.post("/pause_or_play_rondin")
async def post_pause_or_play_rondin(request: Request):
    payload = _ocr_payload(request)
    response = service.pause_or_play_rondin(
        record_id=payload.get("record_id", ""),
        paused=_bool_param(payload.get("paused"), default=True),
    )
    return json({"data": response}, status=200)

@accesos_bp.post("/update_rondin")
async def post_update_rondin(request: Request):
    payload = _ocr_payload(request)
    response = service.update_rondin(folio=payload.get("folio", ""), rondin_data=payload.get("rondin_data", {}))
    return json({"data": response}, status=200)

@accesos_bp.post("/update_inspeccion")
async def post_update_inspeccion(request: Request):
    payload = _ocr_payload(request)
    response = service.update_inspeccion(folio=payload.get("folio", ""), rondin_data=payload.get("rondin_data", {}))
    return json({"data": response}, status=200)

@accesos_bp.post("/asignar_recorrido")
async def post_asignar_recorrido(request: Request):
    payload = _ocr_payload(request)
    response = service.asignar_recorrido(folio=payload.get("folio", ""), asignado_a=payload.get("asignado_a", []))
    return json({"data": response}, status=200)

@accesos_bp.post("/run_cron")
async def post_run_cron(request: Request):
    payload = _ocr_payload(request)
    response = service.run_cron(dag_id=payload.get("dag_id", []))
    return json({"data": response}, status=200)

# ============================================
# Actualizacion de status de pases vencidos (migrado de Rutinas/update_status_pass.py, use_api)
# ============================================

@accesos_bp.post("/update_status_pass")
async def post_update_status_pass(request: Request):
    payload = _ocr_payload(request)
    answers = payload.get("answers", {})
    matched_documents = service.update_pass_status()
    return json({"status": 101, "replace_ans": answers, "matched_documents": matched_documents}, status=200)

# ============================================
# Filtros de listados (migrado de filters.py)
# ============================================

@accesos_bp.get("/filters_recorridos")
async def get_filters_recorridos(request: Request):
    return json({"data": service.get_filters_recorridos()}, status=200)

@accesos_bp.get("/filters_rondines")
async def get_filters_rondines(request: Request):
    return json({"data": service.get_filters_rondines()}, status=200)

@accesos_bp.get("/filters_check_areas")
async def get_filters_check_areas(request: Request):
    return json({"data": service.get_filters_check_areas()}, status=200)

@accesos_bp.get("/filters_incidencias_rondines")
async def get_filters_incidencias_rondines(request: Request):
    return json({"data": service.get_filters_incidencias_rondines()}, status=200)

@accesos_bp.get("/filters_incidencias")
async def get_filters_incidencias(request: Request):
    return json({"data": service.get_filters_incidencias()}, status=200)

@accesos_bp.get("/filters_fallas")
async def get_filters_fallas(request: Request):
    return json({"data": service.get_filters_fallas()}, status=200)

@accesos_bp.get("/filters_in_and_out")
async def get_filters_in_and_out(request: Request):
    return json({"data": service.get_filters_in_and_out()}, status=200)

@accesos_bp.get("/filters_pases")
async def get_filters_pases(request: Request):
    return json({"data": service.get_filters_pases()}, status=200)

@accesos_bp.get("/filters_paqueteria")
async def get_filters_paqueteria(request: Request):
    return json({"data": service.get_filters_paqueteria()}, status=200)

@accesos_bp.get("/filters_concesionados")
async def get_filters_concesionados(request: Request):
    return json({"data": service.get_filters_concesionados()}, status=200)

@accesos_bp.get("/filters_perdidos")
async def get_filters_perdidos(request: Request):
    return json({"data": service.get_filters_perdidos()}, status=200)

@accesos_bp.get("/filters_notas")
async def get_filters_notas(request: Request):
    return json({"data": service.get_filters_notas()}, status=200)

# ============================================
# Config de accesos: permisos legacy (migrado de config_access.py, hook)
# ============================================

@accesos_bp.post("/set_config")
async def post_set_config(request: Request):
    payload = _ocr_payload(request)
    answers = payload.get("answers", {})
    response = service.set_config(answers)
    return json({"data": response}, status=200)

# ============================================
# Transportistas: pases, bitacora de recepcion e inspecciones CTPAT
# (migrado de transportistas.py / transportistas_bitacoras.py, use_api)
# ============================================

@accesos_bp.post("/create_pass_transportista")
async def post_create_pass_transportista(request: Request):
    payload = _ocr_payload(request)
    response = service.create_pass_transportista(payload.get("payload", {}))
    return json({"data": response}, status=200)

@accesos_bp.post("/create_visit_transportista")
async def post_create_visit_transportista(request: Request):
    payload = _ocr_payload(request)
    response = service.create_visit_transportista(payload.get("payload", {}))
    return json({"data": response}, status=200)

@accesos_bp.post("/generate_submit_token_transportista")
async def post_generate_submit_token_transportista(request: Request):
    payload = _ocr_payload(request)
    response = service.generate_submit_token_transportista(payload.get("record_id"))
    return json({"data": response}, status=200)

@accesos_bp.get("/get_andenes")
async def get_get_andenes(request: Request):
    return json({"data": service.get_andenes()}, status=200)

@accesos_bp.get("/get_bitac_transportista_record")
async def get_get_bitac_transportista_record(request: Request):
    response = service.get_bitac_transportista_record(request.args.get("record_id"))
    return json({"data": response}, status=200)

@accesos_bp.get("/get_bitac_transportista_records")
async def get_get_bitac_transportista_records(request: Request):
    return json({"data": service.get_bitac_transportista_records()}, status=200)

@accesos_bp.get("/get_horarios_data")
async def get_get_horarios_data(request: Request):
    dia = request.args.get("dia")
    response = service.get_horarios_data(dia=int(dia) if dia is not None else None)
    return json({"data": response}, status=200)

@accesos_bp.get("/get_pass_transportista")
async def get_get_pass_transportista(request: Request):
    response = service.get_pass_transportista(
        record_id=request.args.get("record_id"),
        token=request.args.get("token"),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_users_data_transportista")
async def get_get_users_data_transportista(request: Request):
    locations = request.args.getlist("locations") or None
    response = service.get_users_data(locations=locations)
    return json({"data": response}, status=200)

@accesos_bp.get("/get_location_data")
async def get_get_location_data(request: Request):
    response = service.get_location_data(request.args.get("location"))
    return json({"data": response}, status=200)

@accesos_bp.get("/get_proveedores_transportista")
async def get_get_proveedores_transportista(request: Request):
    return json({"data": service.get_proveedores_transportista()}, status=200)

@accesos_bp.get("/validate_token_transportista")
async def get_validate_token_transportista(request: Request):
    response = service.validate_token(
        record_id=request.args.get("record_id"),
        token=request.args.get("token"),
    )
    return json({"data": response}, status=200)

@accesos_bp.post("/update_information_transportista")
async def post_update_information_transportista(request: Request):
    payload = _ocr_payload(request)
    response = service.update_information_transportista(payload.get("payload", {}))
    return json({"data": response}, status=200)

@accesos_bp.post("/save_bitac_transportista_record")
async def post_save_bitac_transportista_record(request: Request):
    payload = _ocr_payload(request)
    response = service.save_bitac_transportista_record(payload.get("record_id"), payload.get("payload", {}))
    return json({"data": response}, status=200)

@accesos_bp.post("/delete_bitac_transportista_items")
async def post_delete_bitac_transportista_items(request: Request):
    payload = _ocr_payload(request)
    response = service.delete_bitac_transportista_items(payload.get("record_id"), payload.get("payload", {}))
    return json({"data": response}, status=200)

@accesos_bp.post("/save_inspecciones")
async def post_save_inspecciones(request: Request):
    payload = _ocr_payload(request)
    response = service.save_inspecciones(payload.get("record_id"), payload.get("inspecciones", []))
    return json({"data": response}, status=200)

@accesos_bp.post("/save_inspecciones_sello")
async def post_save_inspecciones_sello(request: Request):
    payload = _ocr_payload(request)
    response = service.save_inspecciones_sello(payload.get("record_id"), payload.get("inspecciones", []))
    return json({"data": response}, status=200)

# ============================================
# Offline services: sincronizacion CouchDB <-> LinkaForm
# (migrado de offline_services.py, use_api)
#
# cr_db se resuelve una vez por request (nunca se guarda en el singleton
# `service`) a partir de user_id, igual que hacia el script legacy con
# self.cr_db = self.get_couch_user_db(f'clave_{user_id}').
# ============================================

def _resolve_offline_user_id(payload):
    current_record = payload.get("current_record", {}) or {}
    return current_record.get('created_by_id') or payload.get('user_id') or 0

@accesos_bp.post("/get_user_catalogs")
async def post_get_user_catalogs(request: Request):
    response = service.get_user_catalogs()
    return json({"data": response}, status=200)

@accesos_bp.post("/assign_user_inbox")
async def post_assign_user_inbox(request: Request):
    payload = _ocr_payload(request)
    user_id = _resolve_offline_user_id(payload)
    cr_db = service.get_couch_user_db(f'clave_{user_id}')
    response = service.assign_user_inbox(
        cr_db,
        data=payload.get("answers", {}),
        record_id=payload.get("record_id"),
        geolocation=payload.get("geolocation", []),
        folio=payload.get("folio"),
    )
    return json({"data": response}, status=200)

@accesos_bp.post("/complete_rondines")
async def post_complete_rondines(request: Request):
    payload = _ocr_payload(request)
    user_id = _resolve_offline_user_id(payload)
    cr_db = service.get_couch_user_db(f'clave_{user_id}')
    response = service.complete_rondines(cr_db, payload.get("records", []))
    return json({"data": response}, status=200)

@accesos_bp.post("/delete_rondines")
async def post_delete_rondines_offline(request: Request):
    payload = _ocr_payload(request)
    user_id = _resolve_offline_user_id(payload)
    cr_db = service.get_couch_user_db(f'clave_{user_id}')
    response = service.delete_rondines(cr_db, payload.get("records", []))
    return json({"data": response}, status=200)

@accesos_bp.post("/reasignar_rondines")
async def post_reasignar_rondines(request: Request):
    payload = _ocr_payload(request)
    user_id = _resolve_offline_user_id(payload)
    cr_db = service.get_couch_user_db(f'clave_{user_id}')
    response = service.reasignar_rondines(cr_db, payload.get("records", []), payload.get("user_to_assign", {}))
    return json({"data": response}, status=200)

@accesos_bp.post("/get_active_guards")
async def post_get_active_guards(request: Request):
    response = service.get_active_guards()
    return json({"data": response}, status=200)

@accesos_bp.post("/sync_records")
async def post_sync_records(request: Request):
    payload = _ocr_payload(request)
    user_id = _resolve_offline_user_id(payload)
    cr_db = service.get_couch_user_db(f'clave_{user_id}')
    response = service.sync_records(cr_db, app_records=payload.get("records", []), test=bool(payload.get("test", False)))
    return json({"data": response}, status=200)

@accesos_bp.post("/clean_db")
async def post_clean_db(request: Request):
    payload = _ocr_payload(request)
    user_id = _resolve_offline_user_id(payload)
    cr_db = service.get_couch_user_db(f'clave_{user_id}')
    response = service.clean_db(cr_db, status=payload.get("status", "received"), batch_size=payload.get("batch_size", 300))
    return json({"data": response}, status=200)

@accesos_bp.post("/fix_rondines")
async def post_fix_rondines(request: Request):
    service.fix_rondines()
    return json({"data": {"status_code": 200, "msg": "OK"}}, status=200)

print('fin de rutas...')