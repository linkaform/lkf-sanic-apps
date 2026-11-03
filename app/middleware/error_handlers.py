# middlewares/error_handler.py
import simplejson
import traceback
import uuid

import requests
from sanic import Sanic
from sanic.response import json
from urllib3.exceptions import MaxRetryError, TimeoutError as Urllib3TimeoutError

TRACE_MAX = 8000


def _is_upstream_timeout(exc):
    # Con read=0 (ver main.py) el read timeout no llega como requests.Timeout sino como
    # ConnectionError(MaxRetryError(reason=ReadTimeoutError)): hay que ver la causa.
    if isinstance(exc, requests.exceptions.Timeout):
        return True
    if isinstance(exc, requests.exceptions.ConnectionError) and exc.args:
        cause = exc.args[0]
        return isinstance(cause, MaxRetryError) and isinstance(cause.reason, Urllib3TimeoutError)
    return False


def setup_error_handlers(app: Sanic):
    @app.exception(Exception)
    async def handle_exception(request, exc):
        tb = traceback.format_exc()
        request_id = uuid.uuid4().hex[:8]
        print(f"[request_id={request_id}] {request.method} {request.path}\n{tb}")

        # dispatch() manda este header: el script recibe el traceback para volcarlo en
        # su stdout y que LinkaForm lo muestre en el log. Un cliente externo no lo manda.
        wants_trace = request.headers.get('X-LKF-Trace') == '1'

        # Linkaform no contesto a tiempo: es el upstream, no un fallo del script.
        if _is_upstream_timeout(exc):
            body = {"error": "Linkaform no respondio a tiempo", "detail": str(exc)}
            if wants_trace:
                body.update(traceback=tb[-TRACE_MAX:], request_id=request_id)
            return json(body, status=504)

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