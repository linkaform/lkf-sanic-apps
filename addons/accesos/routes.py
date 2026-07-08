

import os
import sys
import importlib.util
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
    res = service.get_config_accesos()
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

print('fin de rutas...')