# -*- coding: utf-8 -*-
# Rutas del modulo Contratistas -- backend de la pantalla publica
# "Invitacion de contratista" del front clave10.
#
# Calca addons/location/routes.py. La diferencia importante: aqui SI se lee el
# header Authorization y se pasa al servicio como kwarg (auth_header), porque
# estas rutas necesitan saber QUIEN llama. Ninguna otra ruta del proyecto lo
# hace hoy (accesos/routes.py pasa headers= y el servicio los ignora), asi que
# la autorizacion se construye explicitamente en service.py.

from sanic import Blueprint
from sanic.request import Request
from sanic.response import json

from loader import get_module_class

print('>>> Iniciando carga de módulo Contratistas')

from config.account_settings import *

ModuleClass = get_module_class('Contratistas')

print('>>> Creando instancia del servicio Contratistas')
service = ModuleClass(settings)
print('>>> Servicio Contratistas inicializado correctamente')

contratistas_bp = Blueprint("contratistas", url_prefix="/contratistas")


def _payload(request: Request) -> dict:
    """Acepta el payload como JSON o form-data, igual que location/routes.py."""
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


def _auth(request: Request):
    return request.headers.get("Authorization")


print('--------------- RUTAS Contratistas --------------------')


# ---- Compuerta de identidad (sin JWT del contratista) ----

@contratistas_bp.post("/check_invitacion")
async def post_check_invitacion(request: Request):
    """POST y no GET a proposito: main.py corre con access_log=True, y un GET
    dejaria el correo del contratista en el log de Sanic y de Django. Tampoco
    debe cachearse."""
    payload = _payload(request)
    response = service.check_invitacion(
        record_id=payload.get("record_id", ""),
        email=payload.get("email", ""),
    )
    return json({"data": response}, status=200)


# NO hay ruta /check_username, y es a proposito: un endpoint publico que
# responde "ese usuario existe" es un oraculo de enumeracion (y, pasando por el
# script-runner de Django, un proceso nuevo por cada tecla). La disponibilidad
# la resuelve el alta: si rebota, crear_cuenta_contratista devuelve
# username_ocupado + sugerencias y el front reintenta.

@contratistas_bp.post("/crear_cuenta_contratista")
async def post_crear_cuenta_contratista(request: Request):
    """Alta del contratista. Los kwargs se listan uno por uno a proposito:
    con **payload, una llave inesperada en el body reventaria en TypeError
    (un 500 con traceback) en vez de ignorarse."""
    payload = _payload(request)
    response = service.crear_cuenta_contratista(
        record_id=payload.get("record_id", ""),
        email=payload.get("email", ""),
        username=payload.get("username", ""),
        password=payload.get("password", ""),
        password2=payload.get("password2", ""),
        nombre=payload.get("nombre", ""),
        apellidos=payload.get("apellidos", ""),
        telefono=payload.get("telefono", ""),
        puesto=payload.get("puesto", ""),
    )
    return json({"data": response}, status=200)


# ---- Rutas que exigen el JWT del contratista ----

@contratistas_bp.post("/aceptar_invitacion")
async def post_aceptar_invitacion(request: Request):
    payload = _payload(request)
    response = service.aceptar_invitacion(
        record_id=payload.get("record_id", ""),
        auth_header=_auth(request),
    )
    return json({"data": response}, status=200)


@contratistas_bp.get("/get_contratista_by_id")
async def get_get_contratista_by_id(request: Request):
    response = service.get_contratista_by_id(
        record_id=request.args.get("record_id", ""),
        auth_header=_auth(request),
    )
    return json({"data": response}, status=200)


@contratistas_bp.post("/update_contratista")
async def post_update_contratista(request: Request):
    """POST: `servicios` es una lista y los tres campos de documentos son
    listas de dicts -- no caben confiablemente en un query string."""
    payload = _payload(request)
    kwargs = {"record_id": payload.get("record_id", "")}
    for key in ("razon_social", "rfc", "telefono", "servicios",
                "alta_fiscal", "identificacion", "comprobante_domicilio"):
        if key in payload:
            kwargs[key] = payload.get(key)
    kwargs["marcar_completada"] = bool(payload.get("marcar_completada", False))
    kwargs["auth_header"] = _auth(request)
    response = service.update_contratista(**kwargs)
    return json({"data": response}, status=200)


print('fin de rutas... Contratistas')
