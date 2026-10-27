# middlewares/error_handler.py
import simplejson
import traceback
import uuid

from sanic import Sanic
from sanic.response import json

TRACE_MAX = 8000


def setup_error_handlers(app: Sanic):
    @app.exception(Exception)
    async def handle_exception(request, exc):
        tb = traceback.format_exc()
        request_id = uuid.uuid4().hex[:8]
        print(f"[request_id={request_id}] {request.method} {request.path}\n{tb}")

        # dispatch() manda este header: el script recibe el traceback para volcarlo en
        # su stdout y que LinkaForm lo muestre en el log. Un cliente externo no lo manda.
        wants_trace = request.headers.get('X-LKF-Trace') == '1'

        try:
            payload = simplejson.loads(str(exc))
            exc_data = payload["exception"]
        except (simplejson.JSONDecodeError, TypeError, KeyError):
            body = {"error": str(exc)}
            if wants_trace:
                body.update(traceback=tb[-TRACE_MAX:], request_id=request_id)
            return json(body, status=500)

        status_code = exc_data.get("status_code") or 400
        if wants_trace:
            exc_data = {**exc_data, "traceback": tb[-TRACE_MAX:], "request_id": request_id}
        return json(exc_data, status=status_code)