# middlewares/error_handler.py
from sanic import Sanic
from sanic.response import json

def setup_error_handlers(app: Sanic):
    @app.exception(Exception)
    async def handle_exception(request, exc):
        # Puedes afinar la lógica según tus excepciones de LinkaForm
        return json({"error": str(exc)}, status=500)