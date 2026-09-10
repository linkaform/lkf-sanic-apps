# Flujo de una petición en `lkf-sanic-apps`

Documento de referencia: **qué pasa desde que llega un request HTTP hasta que se
devuelve el JSON**, qué jerarquía de capas existe y dónde se engancha cada pieza.

Todo lo descrito aquí está tomado del código actual del repo; cada afirmación
lleva su referencia `archivo:línea`.

---

## 1. Vista general en una imagen

```
                        ┌──────────────────────────────────────────┐
   Cliente HTTP  ─────► │  Sanic  app = Sanic("clave10_api")       │
   (front / curl)       │  main.py:39   puerto 8000                │
                        └───────────────┬──────────────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │ MIDDLEWARE "request"                  │
                    │   validate_api_key   (auth.py:55)     │  ── 401 y corta ──►
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │ ROUTER de Sanic                       │      rutas ya
                    │   busca el Blueprint por url_prefix   │◄──── mergeadas
                    │   /accesos /employee /location        │      al arrancar
                    │   /contratistas  + rutas base (/ ...) │      (§4.2)
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │ HANDLER  (async def en routes.py)     │
                    │   1. extrae params (args/json/form)   │
                    │   2. filtra allowed_params            │
                    │   3. llama al servicio                │
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │ SERVICIO  (singleton global)          │      clase ya
                    │   service = ModuleClass(settings)     │◄──── resuelta
                    │   Accesos(modules) → Accesos(addons)  │      al arrancar
                    │       → Base → LKF_Base               │      (§4.1)
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │ BACKENDS                              │
                    │   MongoDB · CouchDB · API REST · S3   │
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │ json({"data": ...}, status=...)       │
                    │ (si truena → handle_exception)        │
                    └───────────────────────────────────────┘
```

**Las dos cajas marcadas con ◄── no se resuelven por petición: se resuelven una
sola vez al arrancar**, y es ahí donde entra la capa `app/modules/`. El mismo
módulo existe en dos niveles y el de arriba se sobrepone al de abajo:

```
   ┌─── CAPA DE OVERRIDE ────────────────────────────────────────────────┐
   │  app/modules/<mod>/items/scripts/<Clase>/                           │
   │  (en prod: …/public-client-<ACCOUNT_ID>/scripts/)                   │
   │                                                                     │
   │   <mod>_service.py          <mod>_routes.py                         │
   │   class Accesos(Accesos)    accesos_bp = Blueprint(...)  ← NUEVO    │
   │        │ HERENCIA                 │ MERGE POR URI                   │
   └────────┼───────────────────────────┼────────────────────────────────┘
            │  super() disponible       │  la ruta base con el mismo
            │  se pisa método a método  │  uri se DESCARTA
            ▼                           ▼
   ┌─── CÓDIGO BASE (viaja en la imagen) ────────────────────────────────┐
   │  addons/<mod>/service.py     addons/<mod>/routes.py                 │
   │  class Accesos(Base)         accesos_bp = Blueprint("accesos", ...) │
   └─────────────────────────────────────────────────────────────────────┘

   resuelto por:  get_module_class()        extend_routes()
                  loader.py:176             loader.py:53
```

Cambiar el comportamiento de una cuenta **no requiere rebuild de la imagen**:
se deposita el archivo en la ruta de overrides y el siguiente arranque lo toma.
El detalle completo —y sus tres trampas— está en §4.

---

## 2. Jerarquía de directorios

```
lkf-sanic-apps/
│
├── app/                        ← lo que corre dentro del contenedor como /srv/lkf-sanic-app/app
│   ├── main.py                 ← ★ ENTRYPOINT. Crea la instancia Sanic
│   ├── addons_routes.py        ← ★ REGISTRO. Importa blueprints y aplica overrides
│   ├── loader.py               ← ★ CARGADOR DINÁMICO. Resuelve clases y rutas custom
│   ├── dependencies.py         ← DependenciesManager (singletons de LKF API)
│   ├── database.py             ← pool de MongoDB (pymongo + motor)
│   ├── middleware/
│   │   ├── auth.py             ← middleware de API key + dispatch() + JWT por api_key
│   │   └── error_handlers.py   ← @app.exception(Exception) global
│   ├── config/
│   │   ├── settings.py         ← base; hace settings.config.update(...)
│   │   ├── enviorment.py       ← ENV = local|preprod|prod → hosts de Mongo/API
│   │   ├── local_settings.py   ← credenciales locales (NO va al repo)
│   │   └── account_settings.py ← `from config.settings import *` (lo que importan las rutas)
│   ├── modules/                ← ★ CAPA DE CLIENTE: overrides por cuenta + scripts SDK
│   │   └── <modulo>/items/{scripts,forms,catalogs,reports}/
│   └── static/
│
├── addons/                     ← ★ CÓDIGO BASE DE MÓDULOS
│   │                             se monta como site-packages/lkf_addons/
│   ├── base/app.py             ← class Base(LKF_Base), CargaUniversal, Schedule
│   ├── accesos/
│   │   ├── routes.py           ← Blueprint + 195 rutas
│   │   ├── app.py              ← re-export: `from .service import Accesos`
│   │   ├── service.py          ← ★ LÓGICA REAL (class Accesos)
│   │   ├── models.py
│   │   └── items/              ← recursos instalables del módulo
│   ├── employee/  location/  contratistas/   ← mismo patrón
│   └── ... (~25 módulos más, sin routes.py todavía)
│
├── bin/lkfaddons.py            ← CLI instalador/actualizador de módulos
├── docker/                     ← docker-compose.yml + main_entrypoint.sh
└── Dockerfile                  ← base → develop → prod
```

**Regla mental de las tres capas:**

| Capa | Dónde vive | Responsabilidad |
|---|---|---|
| **Transporte** | `app/main.py`, `app/middleware/` | Sanic, middleware, errores, config global |
| **Ruteo** | `addons/<modulo>/routes.py` | Blueprint, parseo de params, `json(...)` |
| **Negocio** | `addons/<modulo>/service.py` | Mongo, Couch, API, PDFs, OCR, reglas |

Un handler **nunca** debe traer lógica de negocio; un `service.py` **nunca** debe
saber que existe un `Request`.

---

## 3. Arranque: qué pasa ANTES de la primera petición

El orden importa mucho porque casi todo se resuelve en tiempo de importación.

### Paso 1 — `main.py` empieza a importarse

```python
app/main.py:11   from config.settings import settings
app/main.py:16   from middleware.error_handlers import setup_error_handlers
app/main.py:17   from middleware.auth import setup_auth
app/main.py:21   from addons_routes import *      # ← aquí se dispara TODO lo pesado
```

### Paso 2 — `addons_routes.py` importa los blueprints

```python
app/addons_routes.py:7-10
from lkf_addons.accesos.routes      import accesos_bp
from lkf_addons.employee.routes     import employee_bp
from lkf_addons.location.routes     import location_bp
from lkf_addons.contratistas.routes import contratistas_bp
```

Al importar `lkf_addons.accesos.routes` ocurre, **una sola vez**:

```python
addons/accesos/routes.py:29   from config.account_settings import *   # settings
addons/accesos/routes.py:40   ModuleClass = get_module_class('Accesos')
addons/accesos/routes.py:45   service     = ModuleClass(settings)     # ← singleton global
addons/accesos/routes.py:57   accesos_bp  = Blueprint("accesos", url_prefix="/accesos")
addons/accesos/routes.py:60+  @accesos_bp.get(...) ...                # 195 rutas
```

> **Clave:** `service` es **una instancia de módulo, global y compartida por
> todas las peticiones**. No se crea una por request. Todo lo que el constructor
> resuelve (IDs de formularios, catálogos, conexiones) se paga una vez al
> arrancar y se reutiliza siempre.

### Paso 3 — `get_module_class()` decide QUÉ clase se usa

`app/loader.py:176-217`. Busca en orden dentro de `CUSTOM_MODULE_PATHS`
(`loader.py:21-25`):

```
1. /srv/backend.linkaform.com/infosync-api/backend/media/uploads/
       public-client-<ACCOUNT_ID>/scripts/accesos_service.py   ← override del cliente
2. /srv/lkf-sanic-app/app/modules/accesos/items/scripts/Accesos/accesos_service.py
3. /usr/local/lib/python3.12/site-packages/lkf_addons/accesos_service.py
4. FALLBACK → importlib.import_module("lkf_addons.accesos.app")  ← el base del repo
```

Se carga con `importlib.util.spec_from_file_location` (`loader.py:149-160`) y se
registra en `sys.modules` con un nombre único `dynamic_accesos_<hash>`.

### Paso 4 — `extend_routes()` parcha las rutas

`app/addons_routes.py:22-24` → `app/loader.py:53-83`.

Para cada módulo busca un archivo `<modulo>_routes.py` en las mismas rutas
custom. Si existe:

1. Lee `custom_bp._future_routes` (`loader.py:61`).
2. Compara `uri` contra las del blueprint base (`loader.py:64-69`).
3. **Descarta la ruta base** si el URI coincide (`loader.py:72-74` → imprime
   `⚠ Ruta Sobrescritas: <uri>`).
4. Agrega las custom (`loader.py:77`).

Esto es el mecanismo de personalización por cliente: **el cliente puede
sobrescribir un endpoint completo sin tocar el repo**.

> Nota: la comparación es solo por `uri`, no por método HTTP. Un
> `POST /accesos/x` custom elimina también el `GET /accesos/x` base.

### Paso 5 — Configuración global

```python
app/main.py:39      app = Sanic("clave10_api")
app/main.py:46      app.ctx.settings = settings
app/main.py:47      app.config.API_KEY = os.getenv("SANIC_API_KEY", "")
app/main.py:48-55   MONGODB_URI/HOST/PORT, KEEP_ALIVE_TIMEOUT=30,
                    REQUEST_TIMEOUT=60, RESPONSE_TIMEOUT=60
```

### Paso 6 — Hooks de ciclo de vida

```python
app/main.py:64-69   @app.before_server_start  setup_db          → app.ctx.db_pool
app/main.py:71-76   @app.before_server_start  setup_dependencies → app.ctx.dependencies
app/main.py:78-83   @app.after_server_stop    close_db
```

### Paso 7 — Registro de blueprints

```python
app/main.py:96-100
for bp in blueprints:                 # ['Accesos','Employee','Location','Contratistas']
    bp_name = bp.lower() + '_bp'
    app.blueprint(eval(bp_name))      # ← resuelto por el `from addons_routes import *`
```

### Paso 8 — Middleware y rutas base

```python
app/main.py:106  setup_error_handlers(app)
app/main.py:107  setup_auth(app)
app/main.py:114  @app.get("/")           → índice
app/main.py:124  @app.get("/favicon.ico")
app/main.py:128  @app.get("/health")     → {"status","database","version"}
```

### Paso 9 — `app.run()`

```python
app/main.py:144-151
host="0.0.0.0", port=PORT|8000, access_log=True, debug=True,
auto_reload=True, workers=int(os.getenv("WORKERS", 1))
```

Arrancado por `docker/main_entrypoint.sh:6` → `python main.py --auto-reload`.

---

## 4. La capa de overrides: `addons/` vs `app/modules/`

Ésta es la pieza que hace que el proyecto sea multi-cuenta. **El mismo módulo
existe en dos lugares a la vez:**

| | Código base | Capa de override |
|---|---|---|
| Dónde | `addons/<modulo>/` → se monta como `lkf_addons/` | `app/modules/<modulo>/items/scripts/<Clase>/` |
| En producción | dentro de la imagen Docker | `…/public-client-<ACCOUNT_ID>/scripts/` |
| Se cambia | requiere rebuild + deploy | **sin rebuild** — se deposita el archivo y listo |
| Alcance | todas las cuentas | una sola cuenta |

Y se sobrepone **en los dos niveles de la jerarquía**: el servicio y las rutas.
Pero con dos mecanismos distintos, y ahí está lo que hay que entender.

| | Servicio | Rutas |
|---|---|---|
| Archivo | `<modulo>_service.py` | `<modulo>_routes.py` |
| Mecanismo | **herencia de clase Python** | **merge de rutas por URI** |
| Lo resuelve | `get_module_class()` `loader.py:176` | `extend_routes()` `loader.py:53` |
| ¿Alcanza al base? | sí, con `super()` | no: la ruta base se descarta |
| Granularidad | por método | por URI completo |
| Cuándo corre | al importar `routes.py` | en `addons_routes.py:22-24` |

### 4.1 · El servicio SÍ hereda

`app/modules/accesos/items/scripts/Accesos/accesos_service.py`:

```python
from lkf_addons.accesos.service import Accesos

class Accesos(Accesos):                    # ← mismo nombre, hereda del base
    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.f.update({                    # ← agrega/pisa IDs de campos
            'duracion_rondin': '6639b47565d8e5c06fe97cf3',
            ...
        })
```

La cadena efectiva de clases queda así:

```
linkaform_api.base.LKF_Base
   └── Base                      addons/base/app.py:31
         └── Accesos             addons/accesos/service.py      ← base, 438 métodos
               └── Accesos       app/modules/.../accesos_service.py
                                                                ← ESTA es la que se instancia
```

Estado real de ese override en el repo: **21 métodos, de los cuales 17
sobrescriben uno del base** (`get_filters_areas`, `get_catalog_areas_formatted`,
`get_area_by_id`, `close_rondines`, `update_area_estado`…) y 4 son nuevos
(`get_cantidades_de_pases`, `get_cantidades_de_pases_x_persona`,
`get_list_bitacora2`, `get_list_rondines`).

> **Solo `__init__` llama a `super()`.** Los otros 16 métodos sobrescritos
> reemplazan la implementación base por completo. Es herencia real —`super()`
> está disponible— pero en la práctica se usa para reemplazar, no para extender.

Como `routes.py` hace `service = ModuleClass(settings)` y `ModuleClass` ya es la
clase override, **todas las rutas del blueprint base ya están llamando al
servicio extendido sin saberlo**. No hace falta tocar las rutas para cambiar el
comportamiento de un endpoint: basta sobrescribir el método.

### 4.2 · Las rutas NO heredan, se mergean

`app/modules/accesos/items/scripts/Accesos/accesos_routes.py`:

```python
from lkf_addons.accesos.routes import accesos_bp, service, _ocr_payload

accesos_bp = Blueprint("accesos", url_prefix="/accesos")   # ← blueprint NUEVO y VACÍO

@accesos_bp.get("/pases_dos")
async def get_pases_dos(request: Request):
    return json({"data": "Hola Mundo"}, status=201)

@accesos_bp.post("/get_catalog_areas_formatted")
async def post_get_catalog_areas_formatted(request: Request):
    payload = _ocr_payload(request)
    response = service.get_catalog_areas_formatted(
        ubicacion=payload.get("ubicacion", ""),
        dynamic_filters=payload.get("dynamic_filters"),
    )
    return json({"data": response}, status=200)
```

Dos detalles del patrón:

1. **Importa `accesos_bp` y acto seguido lo reasigna** a un `Blueprint` nuevo.
   El import sirve para arrastrar `service` y `_ocr_payload`; la variable del
   blueprint se pisa a propósito para empezar con un set de rutas vacío.
2. **Reusa el `service` ya construido** por el blueprint base. No crea otra
   instancia — que sería pagar de nuevo todo el constructor.

Después `extend_routes()` hace el merge (`loader.py:61-79`): compara los `uri` de
`custom_bp._future_routes` contra los del base, descarta del base los que
coinciden (`⚠ Ruta Sobrescritas`) y agrega todos los custom.

El comentario del propio código lo dice: estas rutas viven ahí *"para poder
probarlo en caliente antes del build/deploy real"*.

### 4.3 · Orden de resolución

`CUSTOM_MODULE_PATHS` (`loader.py:21-25`) se recorre en orden y **gana el
primero que exista**:

```
1. /srv/backend…/public-client-<ACCOUNT_ID>/scripts/       ← producción, por cuenta
2. /srv/lkf-sanic-app/app/modules/accesos/items/scripts/CLASS_NAME
3. /usr/local/lib/python3.12/site-packages/lkf_addons
4. (solo para el servicio) fallback → lkf_addons.<modulo>.app
```

Nombres de archivo que busca:

- Servicio → `<clase>_service.py`, luego `service.py` (`loader.py:189`)
- Rutas → `<modulo>_routes.py` (`loader.py:55`)

### 4.4 · Tres trampas del mecanismo actual

**A. La ruta 2 tiene `accesos` hardcodeado.**

```python
f'/srv/lkf-sanic-app/app/modules/accesos/items/scripts/CLASS_NAME'   # loader.py:23
```

Solo se sustituye `CLASS_NAME`, no el segmento del módulo. Para `Location` busca
en `app/modules/accesos/items/scripts/Location/`, que no existe — el archivo real
está en `app/modules/location/items/scripts/Locations/` (además en plural). En el
contenedor de desarrollo, **solo `Accesos` resuelve por esta ruta**; los overrides
de `location` y `contratistas` solo se alcanzan por la ruta 1, ya desplegados en
la cuenta.

**B. Siempre se busca una variable llamada `accesos_bp`.**

```python
def load_blueprint_from_file(file_path, blueprint_name='accesos_bp'):   # loader.py:85
...
custom_bp = load_blueprint_from_file(custom_file)                       # loader.py:57 ← sin 2º arg
```

`extend_routes()` nunca pasa el nombre del blueprint, así que se queda con el
default. Un `location_routes.py` que exponga `location_bp` devuelve `None` y **el
override se ignora en silencio** (solo se imprime `⚠ No se econtraron rutas
personalizadas en módulo Location`).

**C. Reexportar el blueprint real vaciaría las rutas del módulo.**

`location_routes.py` y `contratistas_routes.py` son reexports planos de 12 líneas:

```python
from lkf_addons.location.routes import location_bp, service
```

Hoy son inertes por la trampa B. Pero si se renombrara esa variable a
`accesos_bp` para que el loader sí la viera, `custom_bp` sería **el mismo objeto**
que `module_bp`, y el merge se autodestruiría:

```python
custom_routes = custom_bp._future_routes            # ← el MISMO set que module_bp
for custom_route in custom_routes:
    for base_route in module_bp._future_routes:     # ← itera ese mismo set
        if custom_route.uri == base_route.uri:      # ← cada ruta hace match consigo misma
            routes_to_remove.add(base_route)        # ← entran TODAS
for route in routes_to_remove:
    module_bp._future_routes.discard(route)         # ← el set queda vacío
module_bp._future_routes.update(custom_bp._future_routes)   # ← update(set_vacío) → sigue vacío
```

El módulo se quedaría sin ninguna ruta. `accesos_routes.py` funciona precisamente
porque **crea un `Blueprint` nuevo** en vez de reexportar el existente.

### 4.5 · Qué mecanismo usar

| Necesitas | Toca | Sin rebuild |
|---|---|---|
| Cambiar la lógica de un endpoint que ya existe | sobrescribe el método en `<modulo>_service.py` | ✔ |
| Agregar un endpoint nuevo | agrégalo en `<modulo>_routes.py` (Blueprint nuevo) | ✔ |
| Cambiar la firma/params de un endpoint existente | ambos: método + ruta con el mismo `uri` | ✔ |
| Que aplique a todas las cuentas | `addons/<modulo>/` + rebuild de imagen | ✘ |

## 5. El viaje de UNA petición (paso a paso)

Tomemos `GET /accesos/list_bitacora?location=Planta1&limit=50`.

### 5.1 · Sanic recibe y construye el `Request`

Parsea URL, headers, query string y body. Aplica `REQUEST_TIMEOUT=60`.

### 5.2 · Middleware de request — `validate_api_key`

`app/middleware/auth.py:54-61`

```python
expected = app.config.get("API_KEY")          # env SANIC_API_KEY
received = request.headers.get("X-API-KEY")
if expected and expected != received:
    return json({"error": "Unauthorized"}, status=401)   # ← corta el flujo
auth_header = request.headers.get("Authorization")       # se lee, no se usa aquí
```

Dos cosas importantes:

- Si `SANIC_API_KEY` **no** está seteada, `expected` es `""` (falsy) y **la
  validación se salta por completo**.
- Devolver una respuesta desde un middleware `"request"` es lo que corta la
  cadena en Sanic: el handler ya no se ejecuta.

El `Authorization` (JWT) **no** se valida aquí. Cada módulo decide qué hacer con
él (ver §8).

### 5.3 · Router → Blueprint → handler

Sanic hace match del URI contra las rutas registradas. `/accesos/...` cae en
`accesos_bp` por su `url_prefix="/accesos"` (`addons/accesos/routes.py:57`).

### 5.4 · El handler extrae los parámetros

`addons/accesos/routes.py:121-137`

```python
@accesos_bp.get("/list_bitacora")
async def get_list_bitacora(request: Request):
    allowed_params = ["location","area","dateFrom","dateTo","limit","offset","filterDate"]
    filters = {k: request.args.get(k) for k in allowed_params
               if request.args.get(k) is not None}         # ← whitelist explícita
    prioridades = request.args.getlist("prioridades")       # listas → getlist()
    if prioridades:
        filters['prioridades'] = prioridades
    if filters.get('limit')  is not None: filters['limit']  = int(filters['limit'])
    if filters.get('offset') is not None: filters['offset'] = int(filters['offset'])
    records = service.get_list_bitacora(**filters)
    return json({"data": records}, status=200)
```

Patrón constante en todo el proyecto:

1. **`allowed_params`** — whitelist; nada que no esté ahí llega al servicio.
2. **`getlist()`** para parámetros repetidos. El comentario en
   `routes.py:126-129` explica el porqué: con `.get()` un `$in` de Mongo recibe
   un string suelto y truena con *"$in needs an array"*.
3. **Casts explícitos** de `limit`/`offset` a `int` (todo query param llega como
   string).
4. **`json({"data": ...}, status=...)`** como forma de respuesta.

### 5.5 · Payloads en POST — `_ocr_payload()`

`addons/accesos/routes.py:469-485` (y su gemelo en `location/routes.py:24-36`,
`contratistas/routes.py:30-42`):

```python
def _ocr_payload(request: Request) -> dict:
    try:
        if request.json: return request.json      # curl / Postman / front
    except Exception: pass
    if request.form:                              # ← así llega desde dispatch()
        return {k: (v[0] if isinstance(v,list) and len(v)==1 else v)
                for k,v in request.form.items()}
    return dict(request.args)                     # último recurso
```

Existe porque **la misma ruta se invoca por dos caminos** con content-types
distintos: JSON desde el front, form-data desde los scripts CLI vía `dispatch()`.

**¿Por qué muchos endpoints son POST aunque "lean" datos?** Dos razones
documentadas en el código:

- Estructuras que no caben confiablemente en query string: `dynamic_filters` es
  lista de dicts (`routes.py:140-142`), `data_gafete` es dict
  (`routes.py:113-114`), `fotografia`/`guards` son listas (`routes.py:171`).
- **Privacidad en logs**: `main.py` corre con `access_log=True`, y un GET dejaría
  el correo del contratista en el log de Sanic y de Django
  (`contratistas/routes.py:54-56`).

### 5.6 · La capa de servicio

`service.get_list_bitacora(**filters)` — instancia global creada en el arranque.

Jerarquía de clases:

```
  linkaform_api.base.LKF_Base          ← paquete externo (linkaform_api 3.0)
        └── Base                        addons/base/app.py:31
              │  define self.mf, self.user_id, self.ai (OpenRouter),
              │  IDs de formularios (self.CONTACTO, self.CLIENTE, ...)
              │  IDs de catálogos (self.USUARIOS, self.GROUP, ...)
              │  el diccionario self.f de campos
              │
              ├── Accesos               addons/accesos/service.py
              ├── Employee              addons/employee/...
              ├── Location              addons/location/...
              ├── Contratistas          addons/contratistas/...
              ├── CargaUniversal        addons/base/app.py:434
              └── Schedule              addons/base/app.py:1333
                     └─ instanciado aparte en accesos/routes.py:50-51
                        para endpoints de cron/airflow (rondines)
```

`addons/accesos/app.py` es solo un re-export (`from .service import Accesos`);
existe porque `self.load(module='Accesos')` y `loader.get_module_class()`
importan por convención `lkf_addons.<modulo>.app`.

Composición entre módulos: un servicio llama a otro con
`self.load(module='Employee', **self.kwargs)`.

### 5.7 · Backends

Desde el servicio se alcanza:

- **MongoDB** — `form_answer` es la colección principal
  (`config/settings.py:10`). Hosts según `ENV` (`config/enviorment.py:15-25`).
- **CouchDB** — bases por usuario para el modo offline:
  `service.get_couch_user_db(f'clave_{user_id}')` (`routes.py:2106`).
- **API REST** vía `self.lkf_api` / `linkaform_api`.
- **Externos** — Google Wallet (`service.py:13668+`), OpenRouter para OCR
  (`base/app.py:57-60`), Backblaze, Oracle.

### 5.8 · Respuesta

`return json({"data": records}, status=200)`. Convención del proyecto: el
payload siempre bajo la llave `"data"`.

### 5.9 · Si algo truena — `handle_exception`

`app/middleware/error_handlers.py:9-20`

```python
@app.exception(Exception)
async def handle_exception(request, exc):
    traceback.print_exc()
    try:
        payload  = simplejson.loads(str(exc))     # ¿la excepción es JSON?
        exc_data = payload["exception"]
    except (simplejson.JSONDecodeError, TypeError, KeyError):
        return json({"error": str(exc)}, status=500)   # error genérico
    status_code = exc_data.get("status_code") or 400
    return json(exc_data, status=status_code)          # error estructurado
```

Dos formas de error:

- Un servicio que lanza `Exception(simplejson.dumps({"exception": {"status_code": 404, "msg": "..."}}))`
  produce una respuesta estructurada con ese status.
- Cualquier otra excepción → `{"error": "<str>"}` con **500**.

---

## 6. El camino alterno: scripts CLI → `dispatch()` → las mismas rutas

Además del HTTP directo, hay un segundo camino de entrada que el front de
clave10 usa hoy.

```
Front clave10
   │  script_name="location_sdk.py", option="get_ubicacion_by_id"
   ▼
Django script-runner  (/api/infosync/scripts/run/)
   │  ejecuta:  python location_sdk.py '<ctx>' '<params-json>'
   ▼
app/modules/<modulo>/items/scripts/<Modulo>/<x>_sdk.py     ← proceso nuevo
   │  DISPATCHER[option](params)
   ▼
middleware.auth.dispatch(endpoint, module=..., params=..., method=...)
   │  auth.py:108-125
   │  POST http://0.0.0.0:8000/<module>/<endpoint>
   ▼
♻ ENTRA POR EL MISMO PUERTO 8000 — vuelve al paso 5.2
```

`app/middleware/auth.py:108-125`:

```python
def dispatch(end_point, module='accesos', params={}, method='get', **kwargs):
    headers = {
        'Authorization': kwargs.get('jwt', kwargs.get('Bearer')),
        'Content-Type': 'application/json',
    }
    url = f"http://0.0.0.0:8000/{module}/{end_point}"
    ...
```

Detalles que importan:

- **El JWT viaja solo**: viene en el payload original como `jwt`/`Bearer` y se
  propaga con `**params` desde el SDK
  (`modules/contratistas/items/scripts/Contratistas/contratistas_sdk.py:15-18`).
  Sin token, `requests` omite el header y la ruta lo recibe como `None`.
- **`ConnectionClient`** (`auth.py:12-50`) es un singleton de módulo con
  `Retry(total=9, backoff_factor=0.1)` y `status=0`: reintenta **solo a nivel de
  conexión** (timeout / connection refused), no por status code. Existe porque
  justo después de que el backend recrea el contenedor, la primera petición puede
  llegar antes de que Sanic termine de levantar (`auth.py:13-19`).
- **`dispatch_with_api_key()`** (`auth.py:85-95`): cambia el JWT del payload por
  uno obtenido del API key de la cuenta vía
  `get_jwt_from_api_key()` (`auth.py:65-82`). Es el equivalente al viejo
  `use_api=True`.
- **`stdout` es el canal de retorno.** El runner de Django trata *cualquier*
  escritura a stderr como fallo (`success=False`, HTTP 400) aunque la respuesta
  sea correcta — por eso `get_jwt_from_api_key` silencia el `UserWarning` de
  `couchdb`/`pkg_resources` (`auth.py:74-79`), y por eso `contratistas_sdk.py`
  no lleva prints de debug (comentario en sus líneas 8-11: por ahí pasan
  contraseñas).

---

## 7. Resumen del orden de ejecución

```
ARRANQUE (una vez)
 1. main.py importa config.settings          → ENV, Mongo hosts, credenciales
 2. main.py importa addons_routes
 3.   ├─ import lkf_addons.<mod>.routes
 4.   │    ├─ get_module_class('<Mod>')      → clase base o override de cliente
 5.   │    ├─ service = ModuleClass(settings)→ SINGLETON GLOBAL
 6.   │    └─ Blueprint + decoradores @bp.get/@bp.post
 7.   └─ extend_routes(bp, 'Mod')            → sobrescribe rutas con las custom
 8. app = Sanic("clave10_api") + app.config
 9. @before_server_start → db_pool, dependencies
10. app.blueprint(...) por cada módulo
11. setup_error_handlers(app); setup_auth(app)
12. app.run(0.0.0.0:8000)

POR PETICIÓN (cada vez)
 a. Sanic parsea el Request
 b. middleware "request": validate_api_key      → 401 si no cuadra
 c. router → blueprint (url_prefix) → handler
 d. handler: allowed_params / _ocr_payload / casts
 e. service.<metodo>(**filters)                 → instancia global
 f. Mongo / Couch / API / OCR / Wallet
 g. json({"data": ...}, status=...)
 h. si excepción → handle_exception (500 o status estructurado)
```

---

## 8. Autenticación: los tres esquemas que conviven

| Esquema | Dónde | Cómo |
|---|---|---|
| **`X-API-KEY`** | middleware global, `auth.py:55-60` | Puerta de entrada. Se salta si `SANIC_API_KEY` está vacía. |
| **`Authorization: Bearer <jwt>`** | por ruta, decisión de cada módulo | Se lee en `auth.py:61` pero **no se valida** ahí. |
| **API key → JWT** | `auth.py:65-82`, `85-95` | Para scripts que corrían con `use_api=True`. |

Estado real del manejo del `Authorization` por módulo:

- **`contratistas/routes.py`** — **sí** lo lee y lo pasa al servicio como
  `auth_header` vía `_auth(request)` (`contratistas/routes.py:45-46`). Es el
  único que lo hace; la autorización se construye explícitamente en su
  `service.py`. Está documentado en el encabezado del archivo (líneas 5-9).
- **`accesos/routes.py`** — pasa `headers=dict(request.headers)` en un solo
  endpoint (`get_shift_data`, línea 102) y **el servicio los ignora**
  (`service.py:11442` acepta `headers=None` y no lo usa).
- **`employee` / `location`** — no leen el header en absoluto.
- Hay rutas explícitamente públicas, marcadas por nombre:
  `/accesos/catalogos_pase_no_jwt` (`routes.py:347`).

**Consecuencia práctica:** el servicio es un singleton sin contexto de usuario.
Las consultas se resuelven con las credenciales del `settings` con el que se
construyó al arrancar, no con las del que llama. Si un endpoint nuevo necesita
saber *quién* pregunta, hay que pasar el `Authorization` explícitamente, como
hace `contratistas`.

---

## 9. Consideraciones de concurrencia (leer antes de agregar rutas)

Cuatro hechos del código actual que conviene tener presentes:

**1. Los handlers son `async` pero los servicios son síncronos.**

```python
records = service.get_list_bitacora(**filters)   # ← llamada BLOQUEANTE
```

No hay `await`. Mientras corre esa consulta a Mongo, el event loop está
bloqueado y no atiende ninguna otra petición.

**2. Corre con un solo worker por defecto** — `workers=int(os.getenv("WORKERS", 1))`
(`main.py:151`). Sumado al punto 1: **las peticiones se serializan**. Se sube
con la variable de entorno `WORKERS`.

**3. `service` es estado compartido.** Una instancia por proceso, viva entre
peticiones. Cualquier atributo que un método escriba en `self` es visible para el
siguiente request — y para el de otro usuario. Los métodos deben tratar `self`
como solo-lectura.

**4. `app.ctx.db_pool` y `app.ctx.dependencies` se inicializan pero ninguna ruta
los consume.** Las rutas usan el `service` global. `database.py`,
`dependencies.py` y el helper `get_dependencies(request)` (`dependencies.py:95`)
están listos pero sin uso; el pool efectivo de Mongo es el que `LKF_Base` abre
por dentro.

Otros detalles:

- `debug=True` y `auto_reload=True` están **hardcodeados** (`main.py:148-150`),
  no leen del entorno.
- `main.py:100` usa `eval(bp_name)` para resolver el blueprint — funciona porque
  `from addons_routes import *` los metió al namespace del módulo.

---

## 10. Cómo agregar un módulo nuevo

```
1. addons/<modulo>/service.py      → class <Modulo>(Base):  lógica
2. addons/<modulo>/app.py          → from .service import <Modulo>     (re-export)
3. addons/<modulo>/routes.py:
       from loader import get_module_class
       from config.account_settings import *
       ModuleClass = get_module_class('<Modulo>')
       service     = ModuleClass(settings)
       <modulo>_bp = Blueprint("<modulo>", url_prefix="/<modulo>")
       @<modulo>_bp.get("/x") async def ...: return json({"data": ...}, status=200)
4. app/addons_routes.py:
       from lkf_addons.<modulo>.routes import <modulo>_bp
       blueprints = [..., '<Modulo>']
```

`main.py` no se toca: recorre `blueprints` y registra por nombre.

**Para exponerlo al front de clave10**, además:

```
5. app/modules/<modulo>/items/scripts/<Modulo>/<modulo>_sdk.py
       from middleware.auth import dispatch
       def <accion>(params): return dispatch("<endpoint>", module='<modulo>',
                                             params={...}, method='post', **params)
       DISPATCHER = {"<accion>": <accion>}
       if __name__ == "__main__":
           params  = simplejson.loads(sys.argv[2])
           option  = params.get("data", {}).get("option", "")
           sys.stdout.write(simplejson.dumps(DISPATCHER[option](params)))
```

Referencia limpia: `app/modules/contratistas/items/scripts/Contratistas/contratistas_sdk.py`
(sin prints de debug, propaga `account_id`).

---

## 11. Despliegue

**Imagen** (`Dockerfile`) — tres etapas: `sanic-base` (Python 3.12 + Mongo tools
+ poppler + Oracle instantclient) → `develop` (deps de `docker/requires.txt`,
`lkfaddons`, wallet, backblaze) → `prod`.

En `prod` (`Dockerfile:109-110`):

```
COPY /addons  →  /usr/local/lib/python3.12/site-packages/lkf_addons/
COPY ./       →  /srv/lkf-sanic-app/
CMD ["python", "main.py"]                      # Dockerfile:123
```

**Desarrollo** (`docker/docker-compose.yml:50-62`) — los mismos destinos se
montan como volúmenes, así que editar `addons/` o `app/` recarga en caliente
(`auto_reload=True`):

```
../addons  → site-packages/lkf_addons/
../app     → /srv/lkf-sanic-app/app
../../linkaform_api/linkaform_api → site-packages/linkaform_api/
puerto     8888 (host) → 8000 (contenedor)
```

**Variables de entorno relevantes:**

| Variable | Default | Usada en |
|---|---|---|
| `PORT` | `8000` | `main.py:146` |
| `WORKERS` | `1` | `main.py:151` |
| `SANIC_API_KEY` | `""` | `main.py:47` → `auth.py:56` |
| `ACCOUNT_ID` | `126` | `loader.py:17` → rutas de override |
| `APP_ROOT` | `/srv/lkf-sanic-app/app` | `loader.py:12` |

El entorno lógico (`local` / `preprod` / `prod`) **no** es variable de entorno:
está hardcodeado en `app/config/enviorment.py:5-7` y define hosts de Mongo, API
y Couch.
