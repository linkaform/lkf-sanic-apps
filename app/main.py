#!/usr/local/bin/python
# coding: utf-8

print('***************************** main...')
import os
from sanic import Sanic
from sanic.response import text
from sanic.response import json
from sanic.response import file, empty

# linkaform_api crea un MongoClient nuevo en cada get_collections y nunca lo cierra
# (7 hilos por cliente con replica de 3 nodos). En addons no importa porque el
# proceso muere; aqui el proceso vive y se acumulan (~450 hilos al arrancar).
# Se reusa un cliente por URI. Va antes de importar las rutas/modulos.
from linkaform_api import network as _lkf_network
_mongo_client_orig = _lkf_network.MongoClient
_mongo_clients = {}
def _shared_mongo_client(*args, **kwargs):
    key = (args, tuple(sorted(kwargs.items())))
    if key not in _mongo_clients:
        _mongo_clients[key] = _mongo_client_orig(*args, **kwargs)
    return _mongo_clients[key]
_lkf_network.MongoClient = _shared_mongo_client

# Las llamadas HTTP (linkaform_api y modulos) no traen timeout: si Linkaform no
# contesta, el handler sincrono congela el worker para siempre. Se pone uno por
# default a toda requests.Session (requests.get/post tambien pasan por ahi).
# Read en segundos sin recibir bytes, no duracion total del script.
import requests as _requests
_HTTP_TIMEOUT = (int(os.getenv('LKF_HTTP_CONNECT_TIMEOUT', 10)),
                 int(os.getenv('LKF_HTTP_READ_TIMEOUT', 120)))

# Header X-Clave10 (nombre_script:opcion) en toda peticion saliente, para que infra
# sepa en HAProxy que script la mando. El valor llega en el header que manda
# dispatch() y se guarda por request (cada request es su propia task de asyncio).
import contextvars as _contextvars
_CLAVE10_HEADER = 'X-Clave10'
_clave10_ctx = _contextvars.ContextVar('clave10_header', default='sanic')
def _with_clave10_header(headers):
    headers = dict(headers or {})
    if not any(k.lower() == _CLAVE10_HEADER.lower() for k in headers):
        headers[_CLAVE10_HEADER] = _clave10_ctx.get()
    return headers

_session_request_orig = _requests.Session.request
def _session_request_with_timeout(self, method, url, **kwargs):
    if kwargs.get('timeout') is None:
        kwargs['timeout'] = _HTTP_TIMEOUT
    kwargs['headers'] = _with_clave10_header(kwargs.get('headers'))
    return _session_request_orig(self, method, url, **kwargs)
_requests.Session.request = _session_request_with_timeout

# CouchDB va por su propio cliente HTTP, no por requests.
import warnings as _warnings
with _warnings.catch_warnings():
    _warnings.simplefilter('ignore')
    import couchdb.http as _couch_http
_couch_request_orig = _couch_http.Session.request
def _couch_request_with_header(self, method, url, body=None, headers=None, *args, **kwargs):
    return _couch_request_orig(self, method, url, body, _with_clave10_header(headers), *args, **kwargs)
_couch_http.Session.request = _couch_request_with_header

# Los hilos de ThreadPoolExecutor (accesos/service.py) no heredan contextvars: se les
# pasa solo el header. No se copia todo el contexto para no cambiar el usuario/JWT
# que hoy ven esos hilos (linkaform_api.request_context).
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor
_executor_submit_orig = _ThreadPoolExecutor.submit
def _executor_submit_with_header(self, fn, /, *args, **kwargs):
    value = _clave10_ctx.get()
    def _run(*a, **kw):
        _clave10_ctx.set(value)
        return fn(*a, **kw)
    return _executor_submit_orig(self, _run, *args, **kwargs)
_ThreadPoolExecutor.submit = _executor_submit_with_header

# ConnectionClient reintenta 9 veces incluyendo POST/PATCH. Con read timeout eso
# reenviaria un POST que Linkaform si recibio (registros duplicados): se dejan
# los reintentos de conexion y se apagan los de lectura.
_connection_client_init_orig = _lkf_network.ConnectionClient.__init__
def _connection_client_init(self, *args, **kwargs):
    _connection_client_init_orig(self, *args, **kwargs)
    for _adapter in self.session.adapters.values():
        _adapter.max_retries = _adapter.max_retries.new(read=0)
_lkf_network.ConnectionClient.__init__ = _connection_client_init

from config.settings import settings
from database import init_db, get_db_pool
from dependencies import init_dependencies

# Middleware
from middleware.error_handlers import setup_error_handlers
from middleware.auth import SANIC_PORT, setup_auth

# Addons Routes

from addons_routes import *
# from addons_routes import blueprints


# Blueprints de módulos
# from lkf_addons.accesos.routes import accesos_bp
# from lkf_addons.employee.routes import employee_bp

# Se enlistan modulos que se van a usar
# Vamos a poner los blueprints de los modulos que son los que van a tener las rutas
# from lkf_addons.accesos.routes import accesos
# from lkf_addons.accesos.app import Accesos
# import lkf_addons
# print('lkf_addons', lkf_addons)
# print('lkf_addons', dir(lkf_addons))
###

# INSTANCIA GLOBAL DE SANIC
app = Sanic("clave10_api")

# ============================================
# CONFIGURACIÓN GLOBAL (CARGADA UNA SOLA VEZ)
# ============================================

# 1. Configurar settings globales
app.ctx.settings = settings
app.config.API_KEY = os.getenv("SANIC_API_KEY", "")
app.config.update_config({
    "MONGODB_URI": settings.config.get('MONGODB_URI'),
    "MONGODB_HOST": settings.config.get('MONGODB_HOST'),
    "MONGODB_PORT": settings.config.get('MONGODB_PORT'),
    "KEEP_ALIVE_TIMEOUT": 30,
    "REQUEST_TIMEOUT": 60,
    "RESPONSE_TIMEOUT": 60
})




# ============================================
# LIFECYCLE EVENTS
# ============================================

@app.before_server_start
async def setup_db(app, loop):
    """Inicializar pool de conexiones MongoDB al arrancar"""
    print(">>> Inicializando pool de conexiones MongoDB...")
    app.ctx.db_pool = init_db(app.ctx.settings)
    print(f">>> Pool de conexiones creado: {app.ctx.db_pool}")

@app.before_server_start
async def setup_dependencies(app, loop):
    """Inicializar dependencias globales (LKF API, etc.)"""
    print(">>> Inicializando dependencias globales...")
    app.ctx.dependencies = await init_dependencies(app.ctx.settings)
    print(">>> Dependencias inicializadas correctamente")

@app.after_server_stop
async def close_db(app, loop):
    """Cerrar conexiones al detener el servidor"""
    print(">>> Cerrando conexiones MongoDB...")
    if hasattr(app.ctx, 'db_pool'):
        app.ctx.db_pool.close()


# ============================================
# REGISTRO DE BLUEPRINTS
# ============================================

# Registrar blueprints de módulos
# print('################# TODO DO.... ESTO DEBE DE SER DINAMICO ##########################################3')
# app.blueprint(accesos_bp)
# app.blueprint(employee_bp)


print(f'Registrando {len(blueprints)} blueprints dinámicamente...')
for bp in blueprints:
    bp_name =  bp.lower() + '_bp'
    print('>>> Registrando blueprint: ', bp_name)
    app.blueprint(eval(bp_name))

# ============================================
# MIDDLEWARE
# ============================================

setup_error_handlers(app)
setup_auth(app)

@app.on_request
async def set_clave10_header(request):
    _clave10_ctx.set(request.headers.get(_CLAVE10_HEADER) or f"sanic:{request.path}")


# ============================================
# RUTAS BASE
# ============================================

@app.get("/")
async def index(request):
    return json({
        "message": "Clave10 API",
        "endpoints": {
            "health": "/health",
            "accesos": "/accesos/*"
        }
    })

@app.get("/favicon.ico")
async def favicon(request):
    return await file("static/favicon.ico")  # cambia ruta si es necesario

@app.get("/health")
async def health(request):
    """Health check endpoint"""
    db_status = "connected" if hasattr(app.ctx, 'db_pool') else "disconnected"
    return json({
        "status": "ok",
        "database": db_status,
        "version": "1.0.0"
    })

# ============================================
# INICIAR APLICACIÓN
# ============================================

if __name__ == "__main__":
    # debug/auto_reload solo en dev: en un contenedor de cuenta real (ENV=='prod', ver
    # config/settings.py) Sanic vigila con el reloader el __file__ de TODO sys.modules,
    # incluidos los scripts de cuenta cargados por importlib en loader.py -- con eso
    # prendido, cada sync de un script (lsyncd) reinicia el proceso solo a mitad de
    # trafico, repitiendo el login real contra la API y la reconexion a Mongo.
    _USE_LOCAL_SETTINGS = os.environ.get('USE_LOCAL_SETTINGS', '').strip().lower() in ('1', 'true', 'yes')
    
    app.run(
        host="0.0.0.0",
        port=SANIC_PORT,
        access_log=True,
        debug=_USE_LOCAL_SETTINGS, 
        auto_reload=_USE_LOCAL_SETTINGS, 
        workers=int(os.getenv("WORKERS", 1))  # Múltiples workers para concurrencia
    )


# def create_app() -> Sanic:
#     app = Sanic("app")

#     # Config básica (puedes reutilizar la de LinkaForm si quieres)
#     app.config.API_KEY = os.getenv("SANIC_API_KEY", "")


#     # Registrar blueprints
#     app.blueprint(accesos_bp)
#     # app.blueprint(stock)
#     # app.blueprint(employee)
#     # app.blueprint(bp_stock)

#     # Middlewares
#     setup_error_handlers(app)
#     setup_auth(app)

#     # Ruta de healthcheck
#     @app.get("/health")
#     async def health(_):
#         return json({"status": "ok"})

#     return app

# if __name__ == "__main__":
#     print('>>>>>>>>>>> LODING MAIN2 <<<<<<<<<<<<')
#     app = create_app()
#     app.run(host="0.0.0.0", port=SANIC_PORT, debug=True)