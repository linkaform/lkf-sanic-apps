import os
import sys
from sanic import Blueprint
from sanic.request import Request
from sanic.response import json

from loader import get_module_class

print('>>> Iniciando carga de módulo Location')
print('>>> LocationLocationLocationLocationLocationLocationLocationLocation carga de módulo Location')

from config.account_settings import *

ModuleClass = get_module_class('Location')

print('>>> Creando instancia del servicio Location')
service = ModuleClass(settings)
print('>>> Servicio Location inicializado correctamente')

location_bp = Blueprint("location", url_prefix="/location")


def _ocr_payload(request: Request) -> dict:
    """Acepta el payload como JSON o form-data, igual que accesos/routes.py."""
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
    return {}

print('--------------- RUTAS  Location--------------------')

@location_bp.get("/get_catalog_ubicaciones_formatted")
async def get_get_catalog_ubicaciones_formatted(request: Request):
    response = service.get_catalog_ubicaciones_formatted(ubicacion=request.args.get("ubicacion", ""))
    return json({"data": response}, status=200)


@location_bp.get("/get_ubicacion_by_id")
async def get_get_ubicacion_by_id(request: Request):
    response = service.get_ubicacion_by_id(record_id=request.args.get("record_id", ""))
    return json({"data": response}, status=200)


@location_bp.post("/create_ubicacion")
async def post_create_ubicacion(request: Request):
    payload = _ocr_payload(request)
    response = service.create_new_ubicacion(
        nombre=payload.get("nombre", ""),
        direccion=payload.get("direccion", ""),
        colonia=payload.get("colonia", ""),
        ciudad=payload.get("ciudad", ""),
        estado=payload.get("estado", ""),
        pais=payload.get("pais", ""),
        codigo_postal=payload.get("codigo_postal", ""),
        telefono=payload.get("telefono", ""),
        email=payload.get("email", ""),
        geolocalizacion=payload.get("geolocalizacion", {}),
    )
    return json({"data": response}, status=200)


@location_bp.post("/update_ubicacion")
async def post_update_ubicacion(request: Request):
    payload = _ocr_payload(request)
    kwargs = {
        "record_id": payload.get("record_id", ""),
        "nombre_actual": payload.get("nombre_actual", ""),
    }
    for key in (
        "nombre", "direccion", "colonia", "ciudad", "estado",
        "pais", "codigo_postal", "telefono", "email", "geolocalizacion",
    ):
        if key in payload:
            kwargs[key] = payload.get(key)
    response = service.update_ubicacion(**kwargs)
    return json({"data": response}, status=200)



print('fin de rutas... Location')