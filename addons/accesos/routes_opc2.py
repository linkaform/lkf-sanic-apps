

from sanic import Blueprint
from sanic.request import Request
from sanic.response import json

########
#### version funcionado
#########
#from .app import Accesos
#
#print('antes de cargar config .settings accesos')
#from config.account_settings import *
#print(' despues de cargar config .settings accesos')
#accesos_bp = Blueprint("accesos", url_prefix="/accesos")
#
#MODULE='/srv/backend.linkaform.com/infosync-api/backend/media/uploads/public-client-126/scripts/accesos/items/scripts/Accesos'
#
#
#
##TODO: Cargar servicios desde la cuenta del cliente.
#print('cargar servicios desde la cuenta del cliente')
#service = Accesos(settings)
####
####



from dependencies import get_dependencies
from database import get_collection
# Blueprint de accesos
accesos_bp = Blueprint("accesos", url_prefix="/accesos")

print('--------------- RUTAS --------------------')


# ============================================
# HELPERS
# ============================================

def get_accesos_service(request):
    """
    Obtiene instancia del servicio Accesos
    REUTILIZA la instancia cacheada en dependencies
    """
    deps = get_dependencies(request)
    return deps.get_module_instance('Accesos')

# ============================================
# ROUTES
# ============================================

@accesos_bp.get("/pases")
async def get_pases(request: Request):
    """
    Obtiene lista de pases
    
    Query params:
        - empresa: Filtrar por empresa
        - location: Filtrar por ubicación
    """
    print('aqui...')
    # Obtener parámetros
    empresa = request.args.get("empresa")
    location = request.args.get("location")
    
    # Obtener servicio (REUTILIZA instancia cacheada)
    service = get_accesos_service(request)
    # records = get_config_accesos()
    # Ejecutar lógica de negocio
    # records = await service.get_lista_pase(
    #     location=location,
    #     status='activo'
    # )
    records = service.get_config_accesos()


    return json({
        "status": "success",
        "data": records,
        "count": len(records)
    })




########
####  version funcioando 
########
"""
@accesos_bp.get("/pases")
async def get_pases(request: Request):
    print('request.args:', request.args)
    empresa = request.args.get("empresa")
    # records = service.get_locations_address()
    records = service.get_config_accesos()
    print('records:', records)
    # records = await service.listar_pases_por_empresa(empresa=empresa)
    # records = [{"empresa": empresa, "count": 42}]
    return json({"data": records})

@accesos_bp.post("/incidentes")
async def post_incidente(request: Request):
    payload = request.json or {}
    res = await service.crear_incidente(payload)
    return json(res, status=201)

@accesos_bp.get("/acceso")
async def get_acceso(request: Request):
    res = {'demo':'true', 'message':'Acceso registrado'}
    print("Acceso regist22rado", res)
    return json(res, status=201)

print('fin de rutas...')
"""