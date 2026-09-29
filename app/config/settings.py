# coding: utf-8
# print('=================== LODING SETTINGS FOR ENVIOIRMENT: {} ==================='.format(ENV))
import os

from linkaform_api import settings


MODULES_PATH = '/srv/lkf-sanic-app/modules'
ADDONS_PATH = '/usr/local/lib/python3.12/site-packages/lkf_addons/'

# Carpeta de scripts sincronizada de la cuenta activa (ACCOUNT_ID). En produccion trae,
# entre otros, el account_settings.py real de esa cuenta. app/loader.py tambien la usa
# (CUSTOM_MODULE_PATHS) para encontrar los *_service.py personalizados -- un solo lugar
# para no repetir este path a mano en los dos archivos.
ACCOUNT_SCRIPTS_DIR = (
    '/srv/backend.linkaform.com/infosync-api/backend/media/uploads/'
    'public-client-{}/scripts/'
)


def _real_account_settings_file():
    """Ruta al account_settings.py real de la cuenta activa (ACCOUNT_ID por env), si
    existe. En produccion cada contenedor es de UNA cuenta y lo trae en la carpeta de
    scripts sincronizada -- es señal mas confiable de "esto es produccion real" que
    LKF_ENV/secrets/current_env, que ahi nunca se setean (son para ./lkf workon en dev).
    """
    account_id = os.environ.get('ACCOUNT_ID', '').strip()
    if not account_id:
        return None
    custom_file = os.path.join(
        ACCOUNT_SCRIPTS_DIR.format(account_id), 'account_settings.py')
    return custom_file if os.path.exists(custom_file) else None


_REAL_ACCOUNT_SETTINGS_FILE = _real_account_settings_file()

# Produccion real no setea LKF_ENV ni secrets/current_env (eso es cosa de ./lkf workon en
# dev), asi que enviorment.py caeria a 'preprod' por default y con eso COUCH_ENV='dev' --
# apuntando rondines/inbox/catalogos de una cuenta real al CouchDB de dev. Si detectamos
# cuenta real y nadie seteo LKF_ENV a mano, forzamos 'prod' antes de que enviorment.py
# resuelva ENV.
if _REAL_ACCOUNT_SETTINGS_FILE and not os.environ.get('LKF_ENV', '').strip():
    print('Cuenta real de produccion detectada, forzando LKF_ENV=prod')
    os.environ['LKF_ENV'] = 'prod'


def _find_secrets():
    """Raiz de secrets/ (accounts.ini, current_domain, current_env).

    No sirve la ruta relativa fija que usa addons (dirname(dirname(__file__))):
    docker-compose monta app/config en dos profundidades distintas
    (/srv/lkf-sanic-app/config y /srv/lkf-sanic-app/app/config), asi que __file__ cae
    en una o en otra segun quien importe -- main.py o bin/download_module.py. Por eso
    se busca hacia arriba hasta encontrar el directorio.

    LKF_SECRETS_PATH lo fuerza, para casos donde secrets/ vive fuera del arbol.
    """
    forzado = os.environ.get('LKF_SECRETS_PATH', '').strip()
    if forzado:
        return forzado
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        candidato = os.path.join(d, 'secrets')
        if os.path.isdir(candidato):
            return candidato
        padre = os.path.dirname(d)
        if padre == d:
            raise ValueError(
                'No se encontro el directorio secrets/ subiendo desde {}.\n'
                'Ponlo en la raiz del repo, o apunta LKF_SECRETS_PATH a el.'.format(
                    os.path.abspath(__file__)))
        d = padre


SECRETS_PATH = _find_secrets()

config = {
    'COLLECTION' : 'form_answer',
    # 'MONGODB_REPLICASET': 'linkaform_replica',
    # 'MONGO_READPREFERENCE': 'secondaryPreferred',
    'MONGODB_MAX_IDLE_TIME': 12000,
    'MONGODB_MAX_POOL_SIZE': 1000,
    'USER_ID' : '',
    'JWT_KEY': False,
    'USE_JWT': True,
}


config.update({
            'USERNAME' : 'your_likaform_username@here.com',
            'APIKEY': 'your_APIKEY_HERE',
})


settings.config.update(config)



from .enviorment import *
from .enviorment import update_settings
print('ENV DE enviorment', ENV)

settings = update_settings(settings)
# local_settings.py resuelve la cuenta activa via secrets/accounts.ini (./lkf workwith).
# Solo existe en dev, asi que el default es NO cargarlo -- en produccion
# account_settings.py ya trae todo y secrets/accounts.ini ni siquiera esta ahi. El
# docker-compose de desarrollo prende USE_LOCAL_SETTINGS=1 explicitamente.
if os.environ.get('USE_LOCAL_SETTINGS', '').strip().lower() in ('1', 'true', 'yes'):
    print("Loading local settings...")
    from .local_settings import *
else:
    print("USE_LOCAL_SETTINGS no esta activo: se omite local_settings.py, se usa account_settings.py")


def _load_account_settings():
    """Cada contenedor de produccion es de UNA cuenta (ACCOUNT_ID por env, ver el
    docker run del deploy real) y trae su propio account_settings.py en la carpeta
    de scripts sincronizada -- las credenciales reales, no los placeholders de
    arriba. Ese archivo solo toca `linkaform_api.settings` (import absoluto, sin
    depender de este paquete `config`), asi que ejecutarlo por su ruta alcanza
    para que pise USERNAME/APIKEY/ACCOUNT_ID/etc. Si no existe (dev, o sin
    ACCOUNT_ID), no hace nada -- se sigue con lo que haya dejado local_settings.py.
    """
    if not _REAL_ACCOUNT_SETTINGS_FILE:
        print('No hay account_settings.py real de cuenta (ACCOUNT_ID sin setear, o no existe el archivo)')
        return
    import importlib.util
    print('Cargando account_settings real de cuenta desde', _REAL_ACCOUNT_SETTINGS_FILE)
    spec = importlib.util.spec_from_file_location(
        'real_account_settings', _REAL_ACCOUNT_SETTINGS_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    print('USERNAME activo tras account_settings real:', settings.config.get('USERNAME'))


_load_account_settings()

settings.ENV = ENV

def get_lkf_settings():
    print('>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<')
    return settings

def get_settings():
    return settings