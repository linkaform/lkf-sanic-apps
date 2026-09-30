# coding: utf-8
import os

from linkaform_api.settings import config

# SECRETS_PATH lo define settings.py justo antes de importar este modulo. El import es
# circular pero valido: cuando esta linea corre, settings.py ya lo tiene definido.
from .settings import SECRETS_PATH


def _env_activo():
    """El environment activo: lo dice secrets/current_env.

    El default es preprod a proposito: arrancar sin haber corrido `./lkf workon` no debe
    pegarle a la base de datos real de los clientes.
    """
    env = ''
    current_env_file = os.path.join(SECRETS_PATH, 'current_env')
    if os.path.exists(current_env_file):
        env = open(current_env_file, encoding='utf-8').read().strip()
    return env if env in ('preprod', 'prod') else 'preprod'


ENV = _env_activo()

print('=================== LODING SETTINGS FOR ENVIOIRMENT: {} ==================='.format(ENV))
PROTOCOL = config.get('PROTOCOL')
HOST = config.get('HOST')
mongo_hosts = config.get('mongo_hosts')
COUCH_ENV = config.get('COUCH_ENV')

if ENV == 'prod':
    PROTOCOL = 'https'
    HOST = 'app.linkaform.com'
    mongo_hosts = 'db2.linkaform.com:27017,db3.linkaform.com:27017,db4.linkaform.com:27017'
    COUCH_ENV = 'prod'

elif ENV == 'preprod':
    PROTOCOL = 'https'
    HOST = 'preprod.linkaform.com'
    mongo_hosts = 'dbs2.lkf.cloud:27918'
    COUCH_ENV = 'dev'

MAX_POOL_SIZE = 1000
WAIT_QUEUE_TIMEOUT = 1000
MONGODB_URI = 'mongodb://%s/'%(mongo_hosts)

config.update({
        'PROTOCOL' : PROTOCOL,
        'HOST' : HOST,
        'MONGODB_PORT':27017,
        'MONGODB_HOST': mongo_hosts,
        'COUCH_ENV':COUCH_ENV,
        'AIRFLOW_PROTOCOL' : 'http', #http or https
        'AIRFLOW_HOST' : 'airflow.linkaform.com',
        'AIRFLOW_PORT' : 5000,
        'ENV':ENV,
    })

def update_settings(settings):
    global config
    settings.config.update(config)
    return settings
