from sanic import Blueprint
from sanic.request import Request
from sanic.response import json

from config.account_settings import *

from lkf_addons.base.app import ScriptLogs, UserActivation, UsersAdmin

script_logs_service = ScriptLogs(settings)

user_activation_service = UserActivation(settings)

users_admin_service = UsersAdmin(settings)

base_bp = Blueprint("base", url_prefix="/base")


def _payload(request: Request) -> dict:
    try:
        if request.json:
            return request.json
    except Exception:
        pass
    return {}


@base_bp.post("/list_script_logs")
async def post_list_script_logs(request: Request):
    p = _payload(request)
    response = script_logs_service.list_script_logs(
        limit=p.get('limit', 25),
        skip=p.get('skip', 0),
        status=p.get('status'),
        script_ids=p.get('script_ids'),
        script_name=p.get('script_name', ''),
        user_ids=p.get('user_ids'),
        user_name=p.get('user_name', ''),
        date1=p.get('date1'),
        date2=p.get('date2'),
        min_duration=p.get('min_duration'),
        max_duration=p.get('max_duration'),
        run_success=p.get('run_success'),
    )
    return json({"data": response}, status=200)


@base_bp.get("/get_script_log_filters")
async def get_get_script_log_filters(request: Request):
    return json({"data": script_logs_service.get_script_log_filters()}, status=200)


@base_bp.post("/get_script_log_content")
async def post_get_script_log_content(request: Request):
    response = script_logs_service.get_script_log_content(_payload(request).get("log_url", ""))
    return json({"data": response}, status=200)


from lkf_addons.base.app import WorkflowLogs

workflow_logs_service = WorkflowLogs(settings)


@base_bp.post("/list_workflow_logs")
async def post_list_workflow_logs(request: Request):
    p = _payload(request)
    response = workflow_logs_service.list_workflow_logs(
        limit=p.get('limit', 25),
        skip=p.get('skip', 0),
        status=p.get('status'),
        rules=p.get('rules'),
        events=p.get('events'),
        workflow_names=p.get('workflow_names'),
        form_ids=p.get('form_ids'),
        user_ids=p.get('user_ids'),
        date1=p.get('date1'),
        date2=p.get('date2'),
    )
    return json({"data": response}, status=200)


@base_bp.get("/get_workflow_log_filters")
async def get_get_workflow_log_filters(request: Request):
    return json({"data": workflow_logs_service.get_workflow_log_filters()}, status=200)


@base_bp.post("/get_workflow_log_detail")
async def post_get_workflow_log_detail(request: Request):
    response = workflow_logs_service.get_workflow_log_detail(_payload(request).get("log_id", ""))
    return json({"data": response}, status=200)


# ---- Pantalla Administracion > Usuarios ----

@base_bp.post("/list_users")
async def post_list_users(request: Request):
    p = _payload(request)
    response = users_admin_service.list_users(
        limit=p.get('limit', 25),
        skip=p.get('skip', 0),
        status=p.get('status'),
        name=p.get('name', ''),
        username=p.get('username', ''),
        email=p.get('email', ''),
        search=p.get('search', ''),
    )
    return json({"data": response}, status=200)


@base_bp.post("/get_user_detail")
async def post_get_user_detail(request: Request):
    response = users_admin_service.get_user_detail(_payload(request).get("record_id", ""))
    return json({"data": response}, status=200)


@base_bp.post("/create_user")
async def post_create_user(request: Request):
    p = _payload(request)
    response = users_admin_service.create_user(
        name=p.get('name', ''), username=p.get('username', ''), email=p.get('email', ''),
        phone=p.get('phone', ''), role=p.get('role', ''),
        empleado=p.get('empleado', ''), empleado_nombre=p.get('empleado_nombre', ''),
    )
    return json({"data": response}, status=200)


@base_bp.post("/update_user")
async def post_update_user(request: Request):
    p = _payload(request)
    response = users_admin_service.update_user(
        record_id=p.get('record_id', ''), name=p.get('name'), phone=p.get('phone'),
        role=p.get('role'), email=p.get('email'),
    )
    return json({"data": response}, status=200)


@base_bp.post("/reset_password")
async def post_reset_password(request: Request):
    response = users_admin_service.reset_password(_payload(request).get("record_id", ""))
    return json({"data": response}, status=200)


# ---- Ruta publica (sin JWT): el usuario fija su contraseña con el enlace del correo ----

@base_bp.post("/set_user_password")
async def post_set_user_password(request: Request):
    """POST y no GET: el token y la contraseña no deben quedar en el access_log."""
    p = _payload(request)
    response = user_activation_service.set_user_password(
        record_id=p.get("record_id", ""),
        token=p.get("token", ""),
        password=p.get("password", ""),
        password2=p.get("password2", ""),
    )
    return json({"data": response}, status=200)
