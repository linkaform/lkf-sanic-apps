#!/usr/local/bin/python
# coding: utf-8
# middlewares/auth.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sanic import Sanic
from sanic.request import Request
from sanic.response import json


class ConnectionClient(object):
    """Mismo patron de retry de conexion que linkaform_api/network.py
    (ConnectionClient) -- reintenta a nivel de conexion (timeouts, connection
    refused) con backoff exponencial, no reintenta por status code de la
    respuesta. Util aqui porque dispatch() llama a las propias rutas de este
    proceso Sanic, y justo despues de que el backend recrea el contenedor la
    primera peticion puede llegar antes de que el server termine de
    levantar."""

    def __init__(self, retries=9, backoff_factor=0.1):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            status_forcelist=None,
            status=0,
            allowed_methods=['GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'PATCH', 'DELETE'],
            backoff_factor=backoff_factor,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def get(self, url, params=None, **kwargs):
        return self.session.get(url, params=params, **kwargs)

    def post(self, url, json=None, **kwargs):
        return self.session.post(url, json=json, **kwargs)

    def put(self, url, json=None, **kwargs):
        return self.session.put(url, json=json, **kwargs)

    def delete(self, url, params=None, **kwargs):
        return self.session.delete(url, params=params, **kwargs)


# Singleton a nivel de modulo: se reusa la misma session (y su pool de
# conexiones) entre llamadas a dispatch(), igual que el resto de la
# arquitectura Sanic mantiene sus dependencias "calientes" entre requests.
_connection_client = ConnectionClient()


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
        response = _connection_client.get(url, params=params, headers=headers)
    elif method == 'post':
        response = _connection_client.post(url, json=params, headers=headers)
    elif method == 'put':
        response = _connection_client.put(url, json=params, headers=headers)
    elif method == 'delete':
        response = _connection_client.delete(url, params=params, headers=headers)
    else:
        response = _connection_client.get(url, params=params, headers=headers)
    return response