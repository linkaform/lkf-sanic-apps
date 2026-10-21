

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

from .checkin import Presencia
from .reporte import ReporteAsistencia

# Asistencia y Check In comparten servicio: pasar a Ausente hace Check Out de lo abierto.
presencia_service = Presencia(settings)
reporte_service = ReporteAsistencia(settings)


@employee_bp.get("/asistencia")
async def get_asistencia(request: Request):
    return json({"data": presencia_service.get_estado()}, status=200)


@employee_bp.post("/asistencia")
async def post_asistencia(request: Request):
    payload = request.json or {}
    return json({"data": presencia_service.set_estatus(payload.get("estatus"))}, status=200)


@employee_bp.post("/asistencia/extra")
async def post_asistencia_extra(request: Request):
    return json({"data": presencia_service.confirmar_extra()}, status=200)


@employee_bp.post("/asistencia/cierre_automatico")
async def post_asistencia_cierre_automatico(request: Request):
    # Lo llama el cierre programado: cierra las jornadas de todos que ya cumplieron su regla.
    return json({"data": presencia_service.cerrar_olvidadas()}, status=200)


@employee_bp.get("/checkin")
async def get_checkin(request: Request):
    return json({"data": presencia_service.get_estado_checkin()}, status=200)


@employee_bp.get("/checkin/lugares")
async def get_checkin_lugares(request: Request):
    return json({"data": presencia_service.get_lugares()}, status=200)


@employee_bp.get("/checkin/roles")
async def get_checkin_roles(request: Request):
    return json({"data": presencia_service.get_roles()}, status=200)


@employee_bp.post("/checkin")
async def post_checkin(request: Request):
    payload = request.json or {}
    allowed = ["ubicacion", "caseta", "rol", "suplente", "motivo", "foto"]
    data = presencia_service.do_checkin(**{k: payload.get(k) for k in allowed if payload.get(k) is not None})
    return json({"data": data}, status=200)


@employee_bp.post("/checkout")
async def post_checkout(request: Request):
    payload = request.json or {}
    allowed = ["comentario", "foto"]
    data = presencia_service.do_checkout(**{k: payload.get(k) for k in allowed if payload.get(k) is not None})
    return json({"data": data}, status=200)


def _reporte_args(request, allowed):
    payload = request.json or {}
    return {k: payload.get(k) for k in allowed if payload.get(k) is not None}


@employee_bp.post("/reporte/hoy")
async def post_reporte_hoy(request: Request):
    args = _reporte_args(request, ["locations"])
    return json({"data": reporte_service.get_hoy(**args)}, status=200)


@employee_bp.post("/reporte/periodo")
async def post_reporte_periodo(request: Request):
    args = _reporte_args(request, ["desde", "hasta", "locations"])
    return json({"data": reporte_service.get_periodo(**args)}, status=200)


@employee_bp.post("/reporte/dia")
async def post_reporte_dia(request: Request):
    args = _reporte_args(request, ["user_id", "fecha"])
    return json({"data": reporte_service.get_dia(**args)}, status=200)


@employee_bp.post("/reporte/ubicaciones")
async def post_reporte_ubicaciones(request: Request):
    return json({"data": reporte_service.get_locations()}, status=200)

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