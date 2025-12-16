

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
    print("Acceso regist22rado", res)
    return json(res, status=201)


@accesos_bp.post("/incidentes")
async def post_incidente(request: Request):
    payload = request.json or {}
    res = await service.crear_incidente(payload)
    return json(res, status=201)


@accesos_bp.get("/lista_pases")
async def get_lista_pases(request: Request):
    print('request.asrgs:', request.args)
    # records = service.get_locations_address()
    location = request.args.get('location')
    status = request.args.get('status')
    inActive = request.args.get('inActive')
    records = service.get_lista_pase(location, status, inActive)
    print('records:', records)
    # records = await service.listar_pases_por_empresa(empresa=empresa)
    # records = [{"empresa": empresa, "count": 42}]
    return json({"data": records}, status=201)


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


print('fin de rutas...')