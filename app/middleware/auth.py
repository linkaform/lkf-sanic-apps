#!/usr/local/bin/python
# coding: utf-8
# middlewares/auth.py
import requests
from sanic import Sanic
from sanic.request import Request
from sanic.response import json


def setup_auth(app: Sanic):
    @app.middleware("request")
    async def validate_api_key(request: Request):
        # ejemplo ultra-simple
        expected = app.config.get("API_KEY")
        received = request.headers.get("X-API-KEY")
        if expected and expected != received:
            return json({"error": "Unauthorized"}, status=401)


def dispatch(end_point, params={}, method='get'):
    url = "http://127.0.0.1:8000/accesos/"+end_point
    if method == 'get':
        response = requests.get(url, params)
    elif method == 'patch':
        response = requests.patch(url, params)
    elif method == 'post':
        response = requests.post(url, params)
    elif method == 'put':
        response = requests.put(url, params)
    elif method == 'delete':
        response = requests.delete(url, params)
    else:
        response = requests.get(url, params)
    return response