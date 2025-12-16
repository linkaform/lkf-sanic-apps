# -*- coding: utf-8 -*-
from linkaform_api import network
import lkfpwd

class Contratista:
    def __init__(self, config):
        self.config = config

class CollectionConnection:
    def __init__(self, connection_id, settings_instance):
        self.settings_connection = {
            'COLLECTION': settings_instance.config.get('COLLECTION'),
            'MONGODB_PORT':settings_instance.config.get('MONGODB_PORT'),
            'MONGODB_HOST': settings_instance.config.get('MONGODB_HOST'),
            'PROTOCOL' : settings_instance.config.get('PROTOCOL'),
            'HOST' : settings_instance.config.get('HOST'),
            'PORT' : settings_instance.config.get('PORT'),
            'ACCOUNT_ID' : connection_id,
            'MONGODB_USER': 'account_{}'.format(connection_id),
            'MONGODB_PASSWORD': lkfpwd.get_pwd(connection_id),
            'AIRFLOW_PROTOCOL':'',
            'AIRFLOW_HOST':'',
            'AIRFLOW_PORT':'',
        }
        
        # Creamos una nueva instancia de Contratista con la configuración generada
        self.settings_connection = Contratista(self.settings_connection)
        
        # Creamos una conexión de red con la configuración generada
        self.net_contratista = network.Network(self.settings_connection)

        # Obtenemos las colecciones y las almacenamos en un atributo
        self.collection_contratista = self.net_contratista.get_collections()

    def get_collections_connection(self):
        """ Metodo para obtener las colecciones """
        return self.collection_contratista