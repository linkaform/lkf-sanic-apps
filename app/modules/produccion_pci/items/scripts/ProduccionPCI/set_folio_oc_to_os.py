# -*- coding: utf-8 -*-
"""
Script para pegar el folio de Orden de Compra en los registros de Orden de Servicio
"""

import sys, simplejson
from datetime import datetime
from produccion_pci_utils import Produccion_PCI
from account_settings import *

class SetFolioOCtoOS( Produccion_PCI ):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

    def get_base_query(self, os_forma, os_folios):
        return {
            'form_id': os_forma,
            'folio': {'$in': os_folios},
            'deleted_at': {'$exists': False}
        }

    def update_os_and_libs( self, f_id, folios, folio_oc, cr_contratista, f_id_lib, folios_libs, is_pagada, status_set ):
        """
        Actualiza en Mongo los registros de Orden de Servicio y Liberaciones
        En Orden de Servicio se pega el folio de la Orden de Compra 
        y el Liberaciones se cambia el estatus a orden de compra en caso de que algunos se hayan quedado abiertos

        Args:
            f_id (int): Id de la forma de orden de servicio
            folios (list): Lista de folios de Orden de Servicio
            folio_oc (str): Folio de la Orden de Compra
            cr_contratista (conexion mongo): Conexion a la BD del Contratista
            f_id_lib (int): Id de la forma de Liberacion
            folios_libs (list): Lista de folios de Liberaciones
            is_pagada (bool): True si la Orden de Compra ya esta marcada como Pagada
            status_set (str): Estatus a pegar en los registros de Liberacion
        """
        
        # Se prepara query y datos que se van a pegar
        query_update = self.get_base_query(f_id, folios) 
        query_update['answers.5f40131c9bca6a32f518d9a9'] = {'$exists': False}
        datas_to_set = { "$set":{ 'answers.5f40131c9bca6a32f518d9a9': folio_oc } }
        if is_pagada:
            print('OC pagada')
            datas_to_set['$set'].update({'answers.f1054000a030000000000013': 'pagada'})
        
        # Se actualiza la informacion en la BD de la conexion (Contratista)
        response_update_contratista = cr_contratista.update_many(query_update, datas_to_set)
        print('= response_update_contratista:',response_update_contratista.raw_result)

        # result_update = set_record( f_id, folios, value=datas_to_set )
        
        # Se actualiza la informacion en la BD de Admin
        response_update_pci = lkf_obj.cr.update_many(query_update, datas_to_set)
        print('= response_update_pci:',response_update_pci.raw_result)
        
        # Actualizacion de estatus de las liberaciones
        query_update_libs = self.get_base_query(f_id_lib, folios_libs)
        query_update_libs['answers.f2361400a010000000000005'] = 'liberado'
        response_update_libs = lkf_obj.cr.update_many(query_update_libs, {
            '$set': {
                'answers.f2361400a010000000000005': status_set
            }
        })
        print('... ... response_update_libs=',response_update_libs.raw_result)

    def procesa_conexiones_falla_server( self, dict_connections ):
        """
        Se procesan las conexiones y las OCs que tienen para actualizar sus ordenes de servicio y liberaciones

        Args:
            dict_connections (dict): Diccionario de conexiones y ordenes de compra que tienen
        """
        dict_formas_os = {
            self.FORMA_ORDEN_COMPRA_FIBRA: {'os': self.ORDEN_SERVICIO_FIBRA, 'lib': self.FORMA_LIBERACION_FIBRA, 'status_lib': 'orden_de_compra'},
            self.FORMA_ORDEN_COMPRA_FIBRA_SURESTE: {'os': self.ORDEN_SERVICIO_FIBRA_SURESTE, 'lib': self.FORMA_LIBERACION_FIBRA_SURESTE, 'status_lib': 'orden_de_compra'},
            self.FORMA_ORDEN_COMPRA_FIBRA_NORTE: {'os': self.ORDEN_SERVICIO_FIBRA_NORTE, 'lib': self.FORMA_LIBERACION_FIBRA_NORTE, 'status_lib': 'orden_de_compra'},
            self.FORMA_ORDEN_COMPRA_FIBRA_OCCIDENTE: {'os': self.ORDEN_SERVICIO_FIBRA_OCCIDENTE, 'lib': self.FORMA_LIBERACION_FIBRA_OCCIDENTE, 'status_lib': 'orden_de_compra'},
            self.FORMA_ORDEN_COMPRA_COBRE: {'os': self.ORDEN_SERVICIO_COBRE, 'lib': self.FORMA_LIBERACION_COBRE, 'status_lib': 'liberadoscon'}, 
            self.FORMA_ORDEN_COMPRA_COBRE_SURESTE: {'os': self.ORDEN_SERVICIO_COBRE_SURESTE, 'lib': self.FORMA_LIBERACION_COBRE_SURESTE, 'status_lib': 'liberadoscon'}, 
            self.FORMA_ORDEN_COMPRA_COBRE_NORTE: {'os': self.ORDEN_SERVICIO_COBRE_NORTE, 'lib': self.FORMA_LIBERACION_COBRE_NORTE, 'status_lib': 'liberadoscon'}, 
            self.FORMA_ORDEN_COMPRA_COBRE_OCCIDENTE: {'os': self.ORDEN_SERVICIO_COBRE_OCCIDENTE, 'lib': self.FORMA_LIBERACION_COBRE_OCCIDENTE, 'status_lib': 'liberadoscon'},
        }

        from pci_get_connection_db import CollectionConnection

        for conexion, dict_forms in dict_connections.items():
            print("**********************************************************")
            print('** Procesando conexion =',conexion)
            print("**********************************************************")

            if not conexion:
                continue
            
            # Abro la conexión para empezar con las actualizaciones en el contratista
            colection_connection = CollectionConnection(conexion, settings)
            cr_contratista = colection_connection.get_collections_connection()
            
            for f_id_oc, list_ocs in dict_forms.items():
                print("===== Procesando forma:",f_id_oc)
                formas = dict_formas_os.get(f_id_oc, {})

                try:
                    for info_oc in list_ocs:
                        folio_oc = info_oc.get('OC')
                        print("== Procesando OC:",folio_oc)
                        self.update_os_and_libs( 
                            formas.get('os'), 
                            info_oc.get('folios', []), 
                            folio_oc, 
                            cr_contratista, 
                            formas.get('lib'), 
                            info_oc.get('foliosTelefonos', []), 
                            info_oc.get('pagada', False), 
                            formas.get('status_lib')
                        )
                except Exception as e:
                    print('ERRORRRRRR con el contratista {} msg: {}'.format(conexion, str(e)))
                    continue

    def ocs_falla_en_servidor(self):
        """
        Consulta los registros de Orden de Compra creados durante un periodo de fechas y las agrupa por conexion
        """
        # Si no hay fechas de inicio y fin no se procesa la actualización
        if not str_desde or not str_hasta:
            print('-------- Falta configurar fechas')
            return False
        
        # Se prepara la query para consulta de Ordenes de Compra creadas en el periodo indicado
        forms_oc = [
            self.FORMA_ORDEN_COMPRA_FIBRA, self.FORMA_ORDEN_COMPRA_FIBRA_SURESTE, self.FORMA_ORDEN_COMPRA_FIBRA_NORTE, self.FORMA_ORDEN_COMPRA_FIBRA_OCCIDENTE, 
            self.FORMA_ORDEN_COMPRA_COBRE, self.FORMA_ORDEN_COMPRA_COBRE_SURESTE, self.FORMA_ORDEN_COMPRA_COBRE_NORTE, self.FORMA_ORDEN_COMPRA_COBRE_OCCIDENTE, 
        ]

        query = {
            'created_at': {
                '$gte': datetime.strptime(f'{str_desde} 00:00:00', "%Y-%m-%d %H:%M:%S"),
                '$lte': datetime.strptime(f'{str_hasta} 23:59:59', "%Y-%m-%d %H:%M:%S")
            }
        }
        
        select_columns = [
            'answers.f1962000000000000000fc10.f19620000000000000001fc1', # Folios de OS
            'answers.f1962000000000000000fc10.f19620000000000000001fc2', # Telefono de OS
            'answers.f19620000000000000000fc5', # Estatus de Orden
            'connection_id', 'folio', 'form_id'
        ]
        
        records_ocs = self.get_records(form_id=forms_oc, query_answers=query, select_columns=select_columns)

        # Se prepara un diccionario de conexiones y las OCs que se encontraron
        dict_connections = {}
        for rec in records_ocs:
            answers_oc = rec['answers']
            info_rec = {
                'OC': rec.get('folio'), 
                'pagada': answers_oc.get('f19620000000000000000fc5') == 'pagada', 
                'folios': [], 
                'telefonos': [], 
                'foliosTelefonos': []
            }

            # Se recorre el grupo repetitito de folios para completar el diccionario
            for fol_os in answers_oc.get('f1962000000000000000fc10', []):
                f_os = fol_os.get('f19620000000000000001fc1', '')
                tel_os = fol_os.get('f19620000000000000001fc2', '')
                if not ' ' in f_os:
                    info_rec['folios'].append( f_os )
                    info_rec['foliosTelefonos'].append( f'{f_os}{tel_os}' )
                    info_rec['telefonos'].append( int( tel_os ) )
            
            # Se agrupa por Conexion
            conn = rec.get('connection_id', 0)
            form_id_oc = rec['form_id']
            dict_connections.setdefault(conn, {}).setdefault(form_id_oc, []).append( info_rec )
        
        self.procesa_conexiones_falla_server(dict_connections)

if __name__ == "__main__":
    lkf_obj = SetFolioOCtoOS(settings, sys_argv=sys.argv)

    filters = lkf_obj.data.get('data', {})

    # current_record = lkf_obj.current_record
    # record_id = lkf_obj.record_id
    # current_record['answers']['60465dc1e774d5ef3f7ee685'] = 'procesando'
    # lkf_obj.lkf_api.patch_record(current_record, record_id)

    # str_desde = current_record['answers'].get('62a328850c1647d997be2465')
    # str_hasta = current_record['answers'].get('62a328850c1647d997be2466')

    str_desde = filters.get('desde')
    str_hasta = filters.get('hasta')

    print(f"--- --- Ejecutando Desde= {str_desde} Hasta= {str_hasta} --- ---")

    lkf_obj.ocs_falla_en_servidor()