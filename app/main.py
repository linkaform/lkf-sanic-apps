#!/usr/local/bin/python
# coding: utf-8

print('***************************** main...')
import os
from sanic import Sanic
from sanic.response import text
from sanic.response import json
from sanic.response import file, empty

from config.settings import settings
from database import init_db, get_db_pool
from dependencies import init_dependencies

# Middleware
from middleware.error_handlers import setup_error_handlers
from middleware.auth import setup_auth

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
    print('>>>>>>>>>>> INICIANDO SERVIDOR SANIC <<<<<<<<<<<<')
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        access_log=True,
        debug=True,#bool(os.getenv("DEBUG", True)),
        #debug=False,#bool(os.getenv("DEBUG", True)),
        auto_reload=True,
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
#     app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=True)