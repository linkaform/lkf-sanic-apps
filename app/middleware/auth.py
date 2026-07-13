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



def get_jwt_from_api_key(api_key):
    """
    Intercambia un API key por un JWT valido usando el mecanismo ya existente
    en linkaform_api (utils.Cache.get_jwt -> network.login). Es el equivalente
    a instanciar la clase de un modulo con use_api=True en el sistema legacy:
    en vez de requerir el JWT de un usuario logeado, se autentica con el
    API key de la cuenta (que el cliente puede elegir por llamada).
    """
    from linkaform_api import settings, utils
    lkf_api = utils.Cache(settings)
    return lkf_api.get_jwt(api_key=api_key)


def dispatch_with_api_key(end_point, api_key, module='accesos', params={}, method='get', **kwargs):
    """
    Igual que dispatch(), pero en vez de reusar el jwt del payload original
    (kwargs['jwt']/kwargs['Bearer']), lo reemplaza por uno obtenido a partir
    del API key indicado. Util para scripts que antes se ejecutaban con
    use_api=True.
    """
    jwt = get_jwt_from_api_key(api_key)
    kwargs = {k: v for k, v in kwargs.items() if k not in ('jwt', 'Bearer')}
    kwargs['jwt'] = f"Bearer {jwt}"
    return dispatch(end_point, module=module, params=params, method=method, **kwargs)


def dispatch(end_point, module='accesos', params={}, method='get', **kwargs):
    headers = {
        'Authorization': kwargs.get('jwt',kwargs.get('Bearer')),
        'Content-Type': 'application/json',
    }
    url = f"http://0.0.0.0:8000/{module}/{end_point}"
    print('url', url)
    if method == 'get':
        response = requests.get(url, params, headers=headers)
    elif method == 'post':
        response = requests.post(url, json=params, headers=headers)
    elif method == 'put':
        response = requests.put(url, json=params, headers=headers)
    elif method == 'delete':
        response = requests.delete(url, params=params, headers=headers)
    else:
        response = requests.get(url, params, headers=headers)
    return response