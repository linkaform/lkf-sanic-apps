

from sanic import Blueprint
from sanic.request import Request
from sanic.response import json

# from services.accesos_service import AccesosService
from .app import Employee

print('employeeemployee antes de cargar config .settings accesos')
from config.account_settings import *
# from config.settings import get_lkf_settings
print('employeeemployee despues de cargar config .settings accesos')
# settings = get_lkf_settings()
# print('settings accesos', settings)
employee_bp = Blueprint("employee", url_prefix="/employee")


#TODO: Cargar servicios desde la cuenta del cliente.
print('cargar servicios desde la cuenta del cliente')
service = Employee(settings)


print('--------------- RUTAS  Employee--------------------')

@employee_bp.get("/employee_data")
async def get_employee_data(request: Request):
    print('request.args:', request.args)
    empresa = request.args.get("empresa")
    # records = service.get_locations_address()
    records = service.get_employee_data()
    print('records:', records)
    # records = await service.listar_pases_por_empresa(empresa=empresa)
    # records = [{"empresa": empresa, "count": 42}]
    return json({"data": records}, status=201)

# @accesos_bp.post("/incidentes")
# async def post_incidente(request: Request):
#     payload = request.json or {}
#     res = await service.crear_incidente(payload)
#     return json(res, status=201)

# @accesos_bp.get("/acceso")
# async def get_acceso(request: Request):
#     res = {'demo':'true', 'message':'Acceso registrado'}
#     print("Acceso regist22rado", res)
#     return json(res, status=201)

print('fin de rutas... Employee')