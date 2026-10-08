from sanic import Blueprint
from sanic.request import Request
from sanic.response import json

from config.account_settings import *

from lkf_addons.base.app import ScriptLogs

script_logs_service = ScriptLogs(settings)

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
