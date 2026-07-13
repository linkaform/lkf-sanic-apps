# middlewares/error_handler.py
import simplejson
import traceback

from sanic import Sanic
from sanic.response import json

def setup_error_handlers(app: Sanic):
    @app.exception(Exception)
    async def handle_exception(request, exc):
        traceback.print_exc()

        try:
            payload = simplejson.loads(str(exc))
            exc_data = payload["exception"]
        except (simplejson.JSONDecodeError, TypeError, KeyError):
            return json({"error": str(exc)}, status=500)

        status_code = exc_data.get("status_code") or 400
        return json(exc_data, status=status_code)