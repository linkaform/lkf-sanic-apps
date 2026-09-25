# coding: utf-8
# print('=================== LODING SETTINGS FOR ENVIOIRMENT: {} ==================='.format(ENV))
import os

from linkaform_api import settings


MODULES_PATH = '/srv/lkf-sanic-app/modules'
ADDONS_PATH = '/usr/local/lib/python3.12/site-packages/lkf_addons/'


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

settings.ENV = ENV

def get_lkf_settings():
    print('>>>>>>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<')
    return settings

def get_settings():
    return settings