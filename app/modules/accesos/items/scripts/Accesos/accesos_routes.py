#!/usr/local/bin/python
# coding: utf-8


from sanic import Blueprint
from sanic.request import Request
from sanic.response import json


#     return json(res, status=201)


from lkf_addons.accesos.routes import accesos_bp, service, _ocr_payload

accesos_bp = Blueprint("accesos", url_prefix="/accesos")

@accesos_bp.get("/pases_dos")
async def get_pases_dos(request: Request):
    res = {"data": "Hola Mundo"}
    return json(res, status=201)

@accesos_bp.get("/pases_tres")
async def get_pases_tres(request: Request):
    res = {"data": "Hola Mundo 4546546"}
    return json(res, status=201)

# --- Áreas: pruebas de dynamic_filters + filtros de áreas sin rebuild ---
# (equivalente a lo ya agregado en addons/accesos/routes.py -- vive aquí
# también para poder probarlo en caliente antes del build/deploy real)

@accesos_bp.post("/get_catalog_areas_formatted")
async def post_get_catalog_areas_formatted(request: Request):
    payload = _ocr_payload(request)
    response = service.get_catalog_areas_formatted(
        ubicacion=payload.get("ubicacion", ""),
        dynamic_filters=payload.get("dynamic_filters"),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/filters_areas")
async def get_filters_areas(request: Request):
    return json({"data": service.get_filters_areas()}, status=200)

@accesos_bp.get("/get_area_by_id")
async def get_get_area_by_id(request: Request):
    response = service.get_area_by_id(record_id=request.args.get("record_id", ""))
    return json({"data": response}, status=200)

@accesos_bp.post("/update_area_estado")
async def post_update_area_estado(request: Request):
    payload = _ocr_payload(request)
    response = service.update_area_estado(
        record_id=payload.get("record_id", ""),
        estado=payload.get("estado", ""),
    )
    return json({"data": response}, status=200)

@accesos_bp.post("/update_area_disponibilidad")
async def post_update_area_disponibilidad(request: Request):
    payload = _ocr_payload(request)
    response = service.update_area_disponibilidad(
        record_id=payload.get("record_id", ""),
        disponibilidad=payload.get("disponibilidad", ""),
    )
    return json({"data": response}, status=200)

@accesos_bp.get("/get_all_checks")
async def get_get_all_checks(request: Request):
    response = service.get_all_checks(
        ubicacion=request.args.get("ubicacion", ""),
        nombre_rondin=request.args.get("nombre_rondin", ""),
        area=request.args.get("area", ""),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        limit=int(request.args.get("limit", 100)),
    )
    return json({"data": response}, status=200)


# @accesos_bp.get("/pases")
# async def get_pases(request: Request):
#     res = {"data": "Hola Mundo OVERWRITE"}
#     return json(res, status=201)