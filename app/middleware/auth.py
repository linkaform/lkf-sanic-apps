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
        print('request... URL',request.headers)
        if expected and expected != received:
            return json({"error": "Unauthorized"}, status=401)
        auth_header = request.headers.get("Authorization")
        print('atuh_header',auth_header)
        print('TODO: Validar JWT....')



def dispatch(end_point, params={}, method='get', **kwargs):
    print('en dispatcher....', kwargs)
    headers = {
        'Authorization': kwargs.get('jwt',kwargs.get('Bearer')),
        'Content-Type': 'application/json',
    }
    url = "http://127.0.0.1:8000/accesos/"+end_point
    print('url', url)
    print('params', params)
    if method == 'get':
        response = requests.get(url, params, headers=headers)
    elif method == 'post':
        response = requests.post(url, params, headers=headers)
    elif method == 'put':
        response = requests.put(url, params, headers=headers)
    elif method == 'delete':
        response = requests.delete(url, params, headers=headers)
    else:
        response = requests.get(url, params, headers=headers)
    return response