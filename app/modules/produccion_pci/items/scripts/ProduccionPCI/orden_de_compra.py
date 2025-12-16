# -*- coding: utf-8 -*-

"""
Descripción: Este script obtiene las liberaciones generadas de las Órdenes de servicio
            y crea registros de Orden de Compra y los asigna a los contratistas

Uso: Se ejecuta en la forma Generar Liberaciones Fibra Cobre cuando estatus == "Generar Orden de Compra"
"""

import sys, simplejson
from datetime import datetime, timedelta
from produccion_pci_utils import Produccion_PCI

from account_settings import *

class GenerarOrdenDeCompra( Produccion_PCI ):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

    def get_descuentos_en_xls(self):
        """
        Se obtienen los descuentos que cargarn en formato excel para cada contratista

        Return: Diccionario con el email del contratista y el descuento que se aplicará
        """
        if not current_record['answers'].get('f2362800a0100000000000b2'):
            return {}
        
        file_url = current_record['answers']['f2362800a0100000000000b2']['file_url']
        header, records_descuentos = self.upfile.get_file_to_upload(file_url=file_url, form_id=current_record['form_id'])

        if not records_descuentos:
            return {}
        
        #print("--- descuentos:",records_descuentos)
        dict_emails_descuentos = {}
        error_descuentos = []
        descuentos_aceptados = ["anticipo", "desmontaje de modems", "queja no atendida", "cobro improcedente"]
        
        for rec_des in records_descuentos:
            email_rec = str(rec_des[1]).lower().strip()
            division_rec = str(rec_des[2]).lower().strip()
            tecnologia_rec = str(rec_des[3]).lower().strip()
            subtotal_default = rec_des[6]

            if division_rec == "psr" or tecnologia_rec == "psr":
                full_name = "psr"
            else:
                if division_rec not in ["metro", "sur", "norte", "occidente"]:
                    error_descuentos.append(rec_des + ["División debe ser metro, sur, norte u occidente",])
                    continue
                if tecnologia_rec not in ["fibra", "cobre"]:
                    error_descuentos.append(rec_des + ["Tecnología debe ser fibra o cobre"])
                    continue
                full_name = f"{tecnologia_rec}_{division_rec}"
            
            if rec_des[0] and not isinstance(rec_des[0], (int, float)):
                error_descuentos.append(rec_des + ["El descuento debe ser de tipo número"])
                continue
            if rec_des[4] and not isinstance(rec_des[4], (int, float)):
                error_descuentos.append(rec_des + ["El porcentaje de descuento debe ser de tipo número"])
                continue
            if subtotal_default and not isinstance(subtotal_default, (int, float)):
                error_descuentos.append(rec_des + ["El subtotal de la OC debe ser de tipo número"])
                continue
            
            descripcion_descuento = rec_des[5]
            if not descripcion_descuento and not subtotal_default:
                error_descuentos.append( rec_des + ["Se requiere la Descripción del descuento"] )
                continue
            if descripcion_descuento:
                descripcion_descuento = descripcion_descuento.lower().strip().replace('($)', '')
                if not any( desc_acepted in descripcion_descuento for desc_acepted in descuentos_aceptados ):
                    error_descuentos.append(rec_des + ["Valor no aceptado en la Descripción del descuento"])
                    continue

            dict_emails_descuentos.setdefault(full_name, [])
            dict_emails_descuentos[full_name].append({
                'email': email_rec, 
                'descuento': rec_des[0], 
                'porcentaje_descuento': rec_des[4],
                'descripcion': descripcion_descuento,
                'default_subtotal_oc': subtotal_default
            })
        if error_descuentos:
            return {'error': error_descuentos, 'header': header}

        return dict_emails_descuentos

    def get_retenciones_resico(self):
        """
        Consulta en el catalogo de Contratistas 1.0 un diccionario con la lista de contratistas y si aplica Retención RESICO o no

        Return: Diccionario de contratistas y si aplican retencion RESICO
        """
        mango_query = { "selector": { "_id": { "$gt": None } }, "limit":10000, "skip":0 }
        records_contratistas_catalog = lkf_api.search_catalog(self.CATALOGO_CONTRATISTAS_ID, mango_query)
        
        return { 
            r['5f344a0476c82e1bebc991d6']: {
                'resico_cobre': r.get('623cb114fe4f97bb0f5848a6'),
                'resico_fibra': r.get('623cb114fe4f97bb0f5848a7')
            } 
            for r in records_contratistas_catalog 
        }

    def get_price_list(self):
        """
        Consulta en Mongo los registros que existen para la forma de Precios Fibra

        Return: Diccionario con la lista de los precios para folios de Fibra
        """
        prices = self.get_records(self.FORM_ID_PRECIOS_FTTH, select_columns=['folio', 'answers'])

        price_list = {}
        for price_ans in prices:
            answers = price_ans['answers']
            code = answers['abc00000000000000000a001'] #codigo de producto
            price_name = answers['aaa00000000000000000a001'] #nombre del producto
            sale_price = answers['bbb00000000000000000b001'] #precio de venta
            buy_price = answers['ccc00000000000000000c001'] #precio de compra
            price_list[ code ] = {
                'code': code, 
                'price_name': price_name,
                'sale_price': sale_price, 
                'buy_price': buy_price
            }
        return price_list

    def get_price_list_cobre(self):
        """
        Consulta en Mongo los registros que existen para la forma de Precios Cobre

        Return: Diccionario con la lista de los precios para folios de Cobre
        """
        prices = self.get_records(self.FORM_ID_PRECIOS_COBRE, select_columns=['folio', 'answers'])
        # aaa00000000000000000a004 : puede ser MAQTEL, MIGRACION ó CONTRATISTA
        # aaa00000000000000000a002 : puede ser A0, PSR ó A4
        # aaa00000000000000000a008 : Monto del precio
        dict_prices = {}
        for price in prices:
            dict_prices.setdefault( price['answers'].get('aaa00000000000000000a004'), {} ).update({
                price['answers'].get('aaa00000000000000000a002'): price['answers'].get('aaa00000000000000000a008')
            })
        return dict_prices

    def validate_emails_descuentos(self, form_connections, list_descuentos, map_users_email, map_email_connections ):
        """
        Se procesan las conexiones que tienen compartida la forma para despues validar que los emails de los descuentos
        tengan compartidas las formas de ésta division y tecnologia

        Args:
            form_connections (dict): Conexiones de la forma
            list_descuentos (list): Lista de descuentos
            map_users_email (dict): Es un diccionario con el usuario y email cuando son diferentes
            map_email_connections (dict): Es un diccionario que se va a completar con el id de la conexion y email

        Return:
            Descuentos y emails que no se encontraron
        """
        emails_connections = []
        
        for connection in form_connections.get('connections', []):
            conn_email = connection['email'].lower()
            conn_user = connection.get('username', '').lower()
            emails_connections.append( conn_email )
            if conn_user != conn_email:
                map_users_email[conn_user] = conn_email
            if connection.get('id'):
                map_email_connections[ int(connection['id']) ] = conn_email
        
        # print('+++ +++ form_connections =',form_connections)

        if form_connections.get('coworkers'):
            for connection_id, coworkers in form_connections.get('coworkers', {}).items():
                if coworkers:
                    for worker in coworkers:
                        worker_email = worker['email'].lower()
                        worker_user = worker.get('username', '').lower()
                        emails_connections.append(worker_email)
                        if worker_user != worker_email:
                            map_users_email[worker_user] = worker_email
                        if worker.get('id'):
                            map_email_connections[ int(worker['id']) ] = worker_email

        # Se validan los descuentos
        emails_not_found = []
        descuentos = []
        for dict_descuentos in list_descuentos:
            emails_des = dict_descuentos.get('email')
            if emails_des not in emails_connections:
                if not map_users_email.get(emails_des):
                    emails_not_found.append(emails_des)
                    continue
                emails_des = map_users_email[emails_des]
            descuentos.append([
                emails_des, dict_descuentos.get('descripcion'), dict_descuentos.get('descuento'), dict_descuentos.get('porcentaje_descuento'), 
                dict_descuentos.get('default_subtotal_oc'), dict_descuentos.get('comentarios')
            ])

        return descuentos, emails_not_found
    
    def recupera_liberados_forma(self, FORMA_LIBERACION, folios_carga, is_cobre=False):
        """
        Consulta en MongoDB los registros de la forma de Liberacion que están con estatus Liberado y que están para salir en Orden de Compra

        Args:
            FORMA_LIBERACION (int): ID del formulario de liberacion
            folios_carga (list): Lista de folios por si queremos consultar solo algunos, si no se manda se consultan todos los registros pendientes
            is_cobre (bool): Si es Cobre no se consideran las TN y TE

        Return:
            Registros de liberacion encontrados
        """
        extra_filters = {'answers.f2361400a010000000000005':'liberado'}
        if is_cobre:
            extra_filters['answers.f2361400a010000000000006.f2361400a0100000000000b6'] = {'$nin': ['tn', 'te']}
        return self.get_records( FORMA_LIBERACION, folios_carga, extra_filters, ['folio', 'user_id', 'form_id', 'answers', '_id'] )

    def get_all_contratistas_from_catalog(self):
        mango_query = { "selector": { "_id": { "$gt": None } }, "limit":10000, "skip":0 }
        records_contratistas = lkf_api.search_catalog(self.CATALOGO_CONTRATISTAS_ID, mango_query)
        #print '----------- records_contratistas =',records_contratistas
        dict_contratistas = { 
            int(r.get('5f344a0476c82e1bebc991d6', 0)): {
                'socio_comercial': r.get('614e4cd2c1770ff99f38ac33', ''),
                'razon_social_fibra': r.get('618057ba8f81fd9179bcd329', ''),
                'razon_social_cobre': r.get('6180593cb518bbdc7cde8d8d', ''),
                'liberado_de_conecta': False if not r.get('63bed6a0cd55b21466e6f929') or r.get('63bed6a0cd55b21466e6f929', '').lower() == 'no' else True,
                'contratista_carso': False if not r.get('665f70d3a7463635ed0e0b81') or r.get('665f70d3a7463635ed0e0b81', '').lower() == 'no' else True
            } for r in records_contratistas 
        }
        return dict_contratistas

    def _procesar_descuentos(self, descuentos, email_of_connection, total_oc, totalDescuento20porc):
        """
        Procesa los descuentos que se van a aplicar en la orden de compra

        Args:
            descuentos (list): Lista de descuentos que se obtivieron del excel
            email_of_connection (str): Email de la conexion a la cual se aplica el descuento
            total_oc (float): Subtotal de la orden de compra
            totalDescuento20porc (float): Monto de descuento aplicado por 20 %

        Return:
            Diccionario con el descuento total, el porcentaje, el subtotal y descuentos que se aplicaron
        """
        descuento = 0
        porcentaje_descuento = 0
        default_subtotal = 0
        dict_descuentos_apply = {}
        descuento_used = []

        for i, record in enumerate(descuentos):
            if record[0] != email_of_connection:
                continue
            if record[4]:
                default_subtotal = record[4]
                descuento_used.append(i)
                continue
            desc_desc, monto, porc = record[1:4]
            if monto:
                descuento += monto
                dict_descuentos_apply[desc_desc] = {'val': monto, 'type': 'monto'}
            elif porc:
                porcentaje_descuento += porc
                dict_descuentos_apply[desc_desc] = {'val': porc, 'type': 'porcentaje'}
            descuento_used.append(i)

        for i in sorted(descuento_used, reverse=True):
            del descuentos[i]

        if (descuento + totalDescuento20porc) > total_oc:
            return f'No se pudo crear la OC para el contratista: {email_of_connection} ya que el descuento rebasa el total de la OC Descuento: {descuento}, Descuento 20%: {totalDescuento20porc}, Total de la OC: {total_oc}'

        return {
            'descuento': descuento,
            'porcentaje_descuento': porcentaje_descuento,
            'default_subtotal': default_subtotal,
            'dict_descuentos_apply': dict_descuentos_apply
        }

    """
    Funciones para Ordenes de Compra FTTH
    """
    ###########################################################################
    # Funciones para consultar ordenes de servicio y validar que no esten ya en OC
    ###########################################################################
    def query_oc_folios(self, form_id , folios):
        """
        Funcion que prepara el query para consulta de folios en Ordenes de Compra

        Args:
            form_id (int): ID del formulario de ORden de Compra
            folios (list): Lista de folios de orden de servicio a buscar en las Ordenes de Compra

        Return:
            Query para consulta de folios en orden de compra
        """
        query = {
            'form_id': form_id, 
            'deleted_at' : {'$exists':False}, 
            'answers.f1962000000000000000fc10.f19620000000000000001fc1': {'$in': folios}
        }
        select_columns = {'folio':1 , 'answers.f1962000000000000000fc10':1}
        return query, select_columns

    def get_folios_of_oc(self, oc_folios_cr):
        """
        Procesa los registros de orden de compra encontrados y regresa una lista de los folios y telefonos de las Ordenes de Servicio

        Args:
            oc_folios_cr (list): Registros de Orden de Compra

        Return:
            Lista de folios y telefonos de las Ordenes de Servicio
        """
        folios_oc = []
        for record in oc_folios_cr:
            for folio_group in record['answers'].get('f1962000000000000000fc10', []):
                folios_oc.append( f"{folio_group.get('f19620000000000000001fc1')}_{folio_group.get('f19620000000000000001fc2')}" )
        return folios_oc

    def get_order_by_connection(self, form_id, folios_telefonos, OC_CONTRATISTA, only_connections=[]):
        """
        Consulta los registros de Orden de Servicio y revisa cuales folios ya están en Orden de Compra

        Args:
            form_id (int): ID de la forma de Orden de Servicio
            folios_telefonos (list): Lista de folios y telefonos que están liberados
            OC_CONTRATISTA (int): ID de la forma de Orden de Compra
            only_connections (list): Lista de conexiones por si se requiere consultar solo para algunos contratistas

        Return:
            folios_by_connection: Folios y telefonos que se van a integrar a Orden de Compra
            folios_id: Diccionario de folios-telefonos con su informacion completa en el registro
            status_pago_folios: Diccionario con folios que no se consideran o que ya estan en Orden de Compra
        """
        folios = [ f[:8] for f in folios_telefonos ]
        query_answers = {'connection_id' : {'$exists':True}}

        if only_connections:
            query_answers['connection_id'] = {'$in': only_connections}
        print(f"_____ Se consultan los registros de OS {form_id} _____")
        result = self.get_records(form_id, folios, query_answers, ['folio', 'connection_id', 'answers'])

        folios_by_connection = {}
        folios_id = {}
        status_pago_folios = {'no_aplica':[], 'pagada':[], 'otra_oc': [] }
        # if result.count() > 0:
        # Buscar si no exixte una orden de compra con ese folio
        print(f"_____ Se revisa que los folios NO esten en OC {OC_CONTRATISTA} _____")
        query_oc, select_columns = self.query_oc_folios(OC_CONTRATISTA, folios)
        oc_folios_cr = self.cr.find(query_oc, select_columns )
        folios_telefonos_in_oc = self.get_folios_of_oc(oc_folios_cr)

        for res in result:
            folio_os = res['folio']
            folio_telefono = f"{folio_os}_{res['answers'].get('f1054000a010000000000005')}"
            
            if folio_telefono in folios_telefonos_in_oc:
                status_pago_folios['otra_oc'].append(folio_telefono)
                continue

            if folio_os in folios:
                folios.pop(folios.index(folio_os))
            
            conn = res['connection_id']
            folios_by_connection.setdefault(conn, {'before_february': []})
            folios_by_connection[conn]['before_february'].append(folio_telefono)

            folios_id[folio_telefono] = res
        status_pago_folios['no_aplica'] = folios
        return folios_by_connection, folios_id, status_pago_folios

    ###########################################################################
    # Funciones para Procesar cada liberacion y OS para calcular el precio de cada concepto a aplicar
    ###########################################################################
    def get_price(self, price_list, code, price_type):
        return price_list.get(code, {}).get(price_type, 0)
    
    def get_migracion_price(self, migration, order, price_list, payment_connection_id):
        if migration[0] == 1:
            if payment_connection_id in [self.ID_CONTRATISTA_TIPO_MAQTEL]:
                return ['Migracion VSI', self.get_price(price_list, 'PUAM9', 'buy_price')]
            return ['Migracion VSI', self.get_price(price_list, 'MVSI', 'buy_price')]
        if migration[1] == 1:
            print('migracion solo voz')
            if payment_connection_id in [self.ID_CONTRATISTA_TIPO_MAQTEL]:
                return ['Migracion solo Voz', self.get_price(price_list, 'PUAM10', 'buy_price')]
            return ['Migracion solo Voz', self.get_price(price_list, 'MSV', 'buy_price')]
        return ['',0]

    def calcula_precio_excedente(self, answers, code_excedente, price_list):
        """
        Calcula el precio del metraje adicional

        Args:
            answers (dict): answers del registro de OS
            code_excedente (str): codigo del precio
            price_list (dict): precios fibra

        Return:
            total_excedente: Calculo del precio excedente por el metraje adicional
            precio_excedente: Precio del excedente que se obtiene de los precios ftth
        """
        metraje_adicional = answers.get('f1054000a020000000000bd7')
        if metraje_adicional:
            precio_excedente = price_list[code_excedente]['buy_price']
            total_excedente = int(metraje_adicional) * float(precio_excedente)
            return total_excedente, precio_excedente
        return 0, 0

    def get_product_name(self, answers, price_list, payment_connection_id, conn_carso, answers_lib):
        """
        Se procesan los precios para obtener el que corresponda segun el código

        Args:
            answers (dict): answers del registro de OS
            price_list (dict): precios ftth
            payment_connection_id (int): Id de la conexion
            conn_carso (list): connexiones de CARSO

        Return:
            code (str): Codigo del producto
            name (str): Nombre del producto
            excedente (float): Metraje adicional multiplicado por el precio
            precio_excedente (float): Precio del metraje excedente
        """
        excedente = 0
        precio_excedente = 0
        code = 'B'
        name = ''
        
        # metraje_to_product = int(answers.get('f1054000a02000000000007a', answers.get('f1054000a0200000000000d7', 0)))

        # cambio el metraje de obtenerlo de la OS a la Liberacion
        metraje_to_product = int( answers_lib.get('f2361400a010000000000002', 0) )
        if metraje_to_product > 300:
            metraje_to_product = 300
        
        '''
        # Para los folios que son de acapulco se va a cobrar por default aerea de 100
        '''
        # record_is_for_acapulco = self.folio_aplica_contingencia(answers)
        record_is_for_acapulco = False
        if record_is_for_acapulco:
            metraje_to_product = 100
            answers['f1054000a020000000000004'] = 'aerea'

        tipo_instalacion = answers.get('f1054000a020000000000004')
        if tipo_instalacion:
            code += 'S' if tipo_instalacion == 'subterranea' else 'A'

        # Se agrega el M para el caso que sea la conexión de MAQTEL
        if payment_connection_id == self.ID_CONTRATISTA_TIPO_MAQTEL:
            code += 'M'
        elif payment_connection_id in conn_carso:
            code += 'C'
        code_excedente = code+'301'

        tecnologia_record = answers.get('f1054000a020000000000022', '')

        # Ya no se va a cobrar el VSI por tanto desde aqui lo quito
        if tecnologia_record == 'vsi':
            tecnologia_record = ''

        code += '00' if (tecnologia_record == 'vsi' and metraje_to_product == 0) else str(metraje_to_product)
        
        try:
            excedente = "0"
            precio_excedente = 0
            if "300" in code or "301" in code:
                excedente, precio_excedente = self.calcula_precio_excedente(answers,code_excedente,price_list)
            name = price_list[code]['price_name'] if metraje_to_product > 0 else ''
        except Exception as e:
            print('*********************************************** excedente ', e)
        return code, name, excedente, precio_excedente

    def obtener_claves_por_conexion(self, payment_connection_id, id_tecnicos_directos, conn_carso):
        """
        Devuelve las claves de precios para todos los conceptos según el payment_connection_id.
        
        Args:
            payment_connection_id (int): id de la conexion
            id_tecnicos_directos (list): Lista de conexiones de Tecnicos directos
            conn_carso (list): Lista de conexiones de CARSO

        Return:
            diccionario con claves y conceptos que aplican segun la conexion
        """
        claves_dict = {
            self.ID_CONTRATISTA_TIPO_MAQTEL: {  # MAQTEL
                'incentivo_psr': 'PSRMI',
                'reparacion_instalaciones': 'PSRM',
                'reparacion_instalaciones_con_incentivo': 'PSRMCI',
                'reparacion_radial': 'PUAM8',
                'radial_cepa': 'PUAM7',
                'radial_banqueta': 'PUAM6',
                'migracion_exitosa': 'MVCAVFVMAQ',
                'desmontaje_migracion': 'DESMIGRACIONMAQ',
                'instalacion_poste': 'IDP25MAQ'
            },
            "carso": {  # CARSO
                'incentivo_psr': 'PSRCMI',
                'reparacion_instalaciones': 'PSRCM',
                'reparacion_instalaciones_con_incentivo': 'PSRCMCI',
                'reparacion_radial': 'PUAC8',
                'radial_cepa': 'PUAC7',
                'radial_banqueta': 'PUAC6',
                'migracion_exitosa': 'MVCAVFVCAR',
                'desmontaje_migracion': 'DESMIGRACIONCAR',
                'instalacion_poste': 'IDP25CAR'
            },
            "tecnicos_directos": {  # Técnicos Directos
                'incentivo_psr': 'PSRTPI',
                'reparacion_instalaciones': 'PSRTP',
                'reparacion_instalaciones_con_incentivo': 'PSRTPCI',
                'reparacion_radial': 'RDTR1',
                'radial_cepa': 'RECL1',
                'radial_banqueta': 'RADIALEB1',
                'migracion_exitosa': 'MVCAVFV',
                'desmontaje_migracion': 'DESMIGRACION',
                'instalacion_poste': 'IDP25'
            },
            "default": {  # Cualquier contratista
                'incentivo_psr': 'PSRCI',
                'reparacion_instalaciones': 'PSRC',
                'reparacion_instalaciones_con_incentivo': 'PSRCCI',
                'reparacion_radial': 'RDTR1',
                'radial_cepa': 'RECL1',
                'radial_banqueta': 'RADIALEB1',
                'migracion_exitosa': 'MVCAVFV',
                'desmontaje_migracion': 'DESMIGRACION',
                'instalacion_poste': 'IDP25'
            }
        }

        # Seleccionar claves según el payment_connection_id
        if payment_connection_id == self.ID_CONTRATISTA_TIPO_MAQTEL:
            return claves_dict[self.ID_CONTRATISTA_TIPO_MAQTEL]
        elif payment_connection_id in id_tecnicos_directos:
            return claves_dict["tecnicos_directos"]
        elif payment_connection_id in conn_carso:
            return claves_dict["carso"]
        return claves_dict["default"]

    def obtener_total(self, cantidad, clave, price_list):
        """
        Calcula el total multiplicando la cantidad por el precio de compra.
        """
        precio = price_list.get(clave, {}).get('buy_price', 0)
        return cantidad * precio

    def make_estimacion_row(self, price_list, order, paco, payment_connection_id, price_list_cobre, conn_carso, answers_lib={}):
        answers = order['answers']

        # Obtener metraje actual y tecnología
        metrajeActual = int(answers.get('f1054000a02000000000007a', answers.get('f1054000a0200000000000d7', 0)))
        tecnologia_record = answers.get('f1054000a020000000000022', '')

        # Determinar tecnología
        # Ya no se va a cobrar el VSI por tanto desde aqui lo quito
        tecnologia = '' if tecnologia_record.lower() == 'vsi' else (tecnologia_record or 'sin tecnologia')

        # Obtener lista de nombre de migración y precio
        migration = ['','']
        migration_price_list = self.get_migracion_price(migration, answers, price_list, payment_connection_id)

        # Validación de metros adicionales
        metros_adicionales = answers.get('f1054000a020000000000bd7', 0) if metrajeActual >= 300 else 0

        # Determinar tipo de carga
        tipo_os = answers.get('f1054000a010000000000021', '').lower().replace(' ', '_')
        charge_type = 'bajante_voz'
        if tipo_os in ('ts_voz', 'migración_voz', 'migracion_voz' ):
            charge_type = 'voz'
        elif tipo_os == 'ts_total':
            charge_type = 'bajante_voz'

        # Ajustar tipo de carga en función de migración y lista de precios
        if migration[1] == 1:
            charge_type = 'bajante'
        elif migration_price_list[0].lower() == 'migracion solo voz':
            charge_type = 'voz'
        
        # Obtener datos de contingencia y producto
        # record_is_for_acapulco = self.folio_aplica_contingencia(answers)
        record_is_for_acapulco = False

        code, name, excedente, precio_excedente = self.get_product_name(answers, price_list, payment_connection_id, conn_carso, answers_lib)

        # Determinar el precio de bajante y actualizar migration_price_list según el tipo de cargo
        bajante_price = 0
        if charge_type in ('bajante','bajante_voz'):
            bajante_price = self.get_price(price_list, code,'buy_price')
        if charge_type == 'bajante' or migration_price_list[1] == '':
            migration_price_list = ['',0]
        if charge_type == 'voz':
            bajante_price = self.get_price(price_list, code,'buy_price')
            name = migration_price_list[0]
            code = 'MVS'
        if code in ('BA00', 'BS00'):
            migration_price_list = self.get_migracion_price([1,0], answers, price_list, payment_connection_id)
        
        """
        Calculando los totales de los conceptos que se cobran
        """
        conceptos = {
            'reparacion_radial': '5ebeaf5df6fcb50881282dc5',
            'radial_cepa': '5ebeaf5df6fcb50881282dc6',
            'radial_banqueta': '5ebeaf5df6fcb50881282dc7',
            'migracion_exitosa': '649711a6ccc16f1189087d45',
            'instalacion_poste': 'f2361400a010000000000f17',
            'desmontaje_migracion': '64c81ec3ca956450a2169a44',
            # Campos para PSR
            'incentivo_psr': '6726ff1164633c2f15ba7af4',
            'reparacion_instalaciones': '6726ff1164633c2f15ba7af5',
            'reparacion_instalaciones_con_incentivo': '6726ff1164633c2f15ba7af6',
        }

        claves_precio = self.obtener_claves_por_conexion(payment_connection_id, self.id_tecnicos_directos, conn_carso)
        # Obtener las cantidades desde answers_lib
        cantidades = {concepto: answers_lib.get(clave, 0) for concepto, clave in conceptos.items()}
        # Calcular totales de manera dinámica
        totales = {concepto: self.obtener_total(cantidades[concepto], claves_precio.get(concepto, ''), price_list) for concepto in conceptos}

        """
        Obteniendo los totales para los campos A4 y PSR
        """
        type_proyecto = answers.get('633d9f63eb936fb6ec9bf580', '')
        is_psr = type_proyecto == 'psr'
        campos_a4 = [0, 0, 0, 0, 0, 0, 0, 0]
        campos_psr = [0, 0, 0]
        campos_radiales = [0, 0, 0]
        campos_extra = [0, 0, 0]
        if tipo_os[:2] == 'a4' or is_psr:
            bajante_price = 0
            migration_price_list[1] = 0
            excedente = 0
            if is_psr:
                """
                === === INCENTIVO PSR
                    PSRMI = Maqtel
                    PSRCMI = Contratista Migrado
                    PSRCI = Contratista

                === === REPARACION DE INSTALACIONES CON INCENTIVO
                    PSRMCI = Maqtel
                    PSRCMCI = Contratista Migrado
                    PSRCCI = Contratista

                === === REPARACIÓN DE INSTALACIONES
                    PSRM = Maqtel
                    PSRCM = Contratista Migrado
                    PSRC = Contratista
                """
                codigo_psr = 'PSRC'
                if payment_connection_id == self.ID_CONTRATISTA_TIPO_MAQTEL:
                    codigo_psr = 'PSRM'
                elif payment_connection_id in conn_carso:
                    codigo_psr = 'PSRCM'
                # total_incentivo_psr = totales['incentivo_psr'] if not 'incentivo_psr' in conceptos_cobrados_psr else 0
                total_reparacion_instalaciones = self.get_price(price_list, codigo_psr, 'buy_price')
                # total_reparacion_instalaciones_con_incentivo = totales['reparacion_instalaciones_con_incentivo'] if not 'reparacion_instalaciones_con_incentivo' in conceptos_cobrados_psr else 0
                campos_psr = [0, total_reparacion_instalaciones, 0]
            else:

                nivel_de_pago = 'contratista' 
                if payment_connection_id == self.ID_CONTRATISTA_TIPO_MAQTEL:
                    nivel_de_pago = 'maqtel'
                elif payment_connection_id in conn_carso:
                    nivel_de_pago = 'migrado'

                campos_a4[ 0 ] = price_list_cobre[ nivel_de_pago ][ 'a4' ]
                name = 'A4'

                # EJEMPLO DE CALCULO EN COBRE ===== columna_total = valor_del_campo * price_list[tipo_trabajo][year][infra][nivel].get(map_product_name,-1)
                # a4_par_principal = answers_lib.get('5f033e1248598b3eda0e34c4', 0)# PRUEBAS ELÉCTRICAS DE PAR PRINCIPAL
                # a4_par_secundario = answers_lib.get('5f033e1248598b3eda0e34c5', 0)# PRUEBAS ELÉCTRICAS DE PAR SECUNDARIO
                # a4_reporte_ivr = answers_lib.get('5f033e1248598b3eda0e34c6', 0)# REPORTE DE IVR, PARA LIQUIDACIÓN DEL SERVICIO
                # a4_rosetas = answers_lib.get('5f033e1248598b3eda0e34c7', 0)# RECEPCIÓN, MANEJO Y ALMACENAJE DE ROSETAS. (PRECIO POR ROSETA), (2)
                # a4_modem = answers_lib.get('5f033e1248598b3eda0e34c8', 0)# MANEJO, CUSTODIA, ENTREGA Y PUESTA EN SERVICIO DE MODEM EN LA CASA DEL CLIENTE....
                # a4_claro = answers_lib.get('5f033e1248598b3eda0e34c9', 0)# ACTIVACIÓN EXITOSA DE CLARO VIDEO (VÍA TEK o IVR) EN LA CASA DEL CLIENTE
                # a4_montaje_puente = answers_lib.get('5f033e1248598b3eda0e34ca', 0)# MONTAJE DE PUENTE NUEVO EN DISTRIBUIDOR GENERAL
                # a4_desmontaje_puente = answers_lib.get('5f033e1248598b3eda0e34cb', 0)# DESMONTAJE DE PUENTE EN DISTRIBUIDOR GENERAL

                # precios_a4_cobre = price_list_cobre['a4']['2020']['sin_ie']['bajo']
                # total_a4_par_principal = a4_par_principal * precios_a4_cobre.get('pruebas_eléctricas_de_par_principal', -1)
                # total_a4_par_secundario = a4_par_secundario * precios_a4_cobre.get('pruebas_eléctricas_de_par_secundario', -1)
                # total_a4_reporte_ivr = a4_reporte_ivr * precios_a4_cobre.get('reporte_de_ivr,_para_liquidación_del_servicio', -1)
                # total_a4_rosetas = a4_rosetas * precios_a4_cobre.get('recepción,_manejo_y_almacenaje_de_rosetas._(precio_por_roseta),_(2)', -1)
                # total_a4_modem = a4_modem * precios_a4_cobre.get('manejo,_custodia,_entrega_y_puesta_en_servicio_de_modem_en_la_casa_del_cliente._(se_hace_toda_la_administración_desde_el_almacén_telmex_hasta_el_domicilio_del_cliente,_se_hace_la_instalación_y_prueba_de_navegación_en_la_casa_del_cliente).', -1)
                # total_a4_claro = a4_claro * precios_a4_cobre.get('activación_exitosa_de_claro_video_(vía_tek_o_ivr)_en_la_casa_del_cliente', -1)
                # total_a4_montaje_puente = a4_montaje_puente * precios_a4_cobre.get('montaje_de_puente_nuevo_en_distribuidor_general', -1)
                # total_a4_desmontaje_puente = a4_desmontaje_puente * precios_a4_cobre.get('desmontaje_de_puente_en_distribuidor_general', -1)

                # campos_a4 = [ total_a4_par_principal, total_a4_par_secundario, total_a4_reporte_ivr, total_a4_rosetas, total_a4_modem, total_a4_claro, total_a4_montaje_puente, total_a4_desmontaje_puente ]
        else:
            """
            NO es A4 y tampoco PSR... considerando los demas campos
            """
            campos_radiales = [ totales['reparacion_radial'], totales['radial_cepa'], totales['radial_banqueta'] ]
            campos_extra = [ totales['migracion_exitosa'], totales['desmontaje_migracion'], totales['instalacion_poste'] ]
        # ==================================================================================================
        total = bajante_price + migration_price_list[1] + float(excedente) + sum(campos_radiales) + sum(campos_extra) + sum(campos_a4) + sum(campos_psr)
        
        # Se agrega el bono "Prioridad"
        apply_bono_prioridad = False
        # apply_bono_prioridad = type_proyecto == 'prioridad'
        # if apply_bono_prioridad:
        #     total += self.bono_prioridad
        
        # Identificando si el folio está marcado con descuento de 15 dias de retardo
        descuento15dias = answers.get('601c7ae006478d9cbee17e00', 'no')
        descuentoCobroMinimo = answers.get('5fc9269ce5363f7e3b9e3867', 'no')
        descuentos_por = []

        """
        Revisando descuento por desfase de 15 días ó cobro mínimo
        """
        folioDescuento20porc = 0
        if not record_is_for_acapulco:
            if (descuento15dias != 'no') or (descuentoCobroMinimo != 'no'):
                descuento_20_porciento = total * self.porcentaje_descuento_x_desfase
                folioDescuento20porc += descuento_20_porciento
            if descuento15dias != 'no':
                descuentos_por.append('desfase_15_dias_en_carga')
            if descuentoCobroMinimo != 'no':
                descuentos_por.append('cobro_minimo')

        """
        Descuento por modificación en el Metraje
        """
        metrajeAnteriorModificado = answers.get('6021ba39dae34bd70dcd40b5', 0)
        if metrajeAnteriorModificado and not record_is_for_acapulco:
            descuento_20_porciento = total * self.porcentaje_descuento_x_desfase
            folioDescuento20porc += descuento_20_porciento
            descuentos_por.append('metraje_modificado')

        if record_is_for_acapulco:
            descuentos_por.append('contingencia')

        row = [
            order['folio'], #folio
            answers['f1054000a010000000000005'], #telefono
            answers.get('f1054000a0200000000000a3', ''), #ont
            p_utils.get_today(str_format='%m/%d/%Y'), # time.strftime("%m/%d/%Y"), #fecha entrega
            'PCS', #filial
            paco, #paco
            1, #cantidad
            name, #trabajo
            bajante_price, #precio
        ]
        row += migration_price_list
        row += [
            total, #precios
            answers['f1054000a010000000000021'], #tipo os
            tecnologia, #tecnologia
            metros_adicionales, #metros adicionales
            excedente, #Total metros adicionales
            precio_excedente, #precio excedente
        ]
        row += campos_radiales
        row.append(descuentos_por) # Por que se aplica descuento
        row += campos_a4
        row += campos_extra
        row.append(apply_bono_prioridad)

        if is_psr:
            row += campos_psr

        return row, folioDescuento20porc

    def get_folio_info(self, record_lib, price_list, order, payment_connection_id, price_list_cobre, conn_carso):
        """
        Se obtiene la informacion del folio procesado

        Args:
            record_lib (dict): Registro de liberacion
            price_list (list): Precios de Fibra
            order (dict): Registro de Orden de Servicio
            payment_connection_id (int): id de la conexión
            price_list_cobre (list): Precios de Cobre

        Return:
            row (list): Conceptos que se van a cobrar
            folioDescuento20porc (float): Descuentos de 20 %
        """
        answers_lib_record = record_lib['answers']
        paco = answers_lib_record['f2361400a010000000000001']
        row, folioDescuento20porc = self.make_estimacion_row(price_list, order, paco, payment_connection_id, price_list_cobre, conn_carso, answers_lib=answers_lib_record)
        return row, folioDescuento20porc

    ###########################################################################
    # Funciones para Crear las Ordenes de Compra de FTTH
    ###########################################################################
    def get_folios_num(self, form_id, folio_num):
        """
        Se consultan las Ordenes de Compra que se han creado con la ejecucion en proceso y se obtiene el último consecutivo

        Args:
            form_id (int): ID de la forma de Orden de Compra
            folio_num (str): folio del registro de la ejecucion

        Return:
            max_num (int): Ultimo numero consecutivo del folio de la orden creada.
        """
        folio_num = folio_num + '-'
        query = {'form_id':form_id, 'deleted_at':{'$exists':False}, 'folio': {'$regex': folio_num}}
        select_columns = {'folio':1}
        result = self.cr.find(query, select_columns)
        max_num = 0
        for folio in result:
            if folio['folio'].find('-') > 0:
                num = folio['folio'].split('-')[1]
                try:
                    num = int(num)
                except:
                    num = 0
                if num > max_num:
                    max_num = num
                if num == max_num:
                    max_num += 1
        return max_num

    def cambia_estatus_de_liberados_a_orden_de_compra(self, folios_finales, LIBERACION_PAGOS, set_status='orden_de_compra'):
        query = {'f2361400a010000000000005': set_status}
        try:
            response_multi_patch = lkf_api.patch_multi_record(query, LIBERACION_PAGOS, record_id=folios_finales, jwt_settings_key='USER_JWT_KEY', threading=True)
            # print('teeemp print -- response_multi_patch =',response_multi_patch)
        except:
            print('*********************************************** cambia el estatus liberado a orden compra')
        # for response in response_multi_patch:
        #     if response.get('status_code') and response['status_code'] >= 200 and response['status_code'] < 300:
        #         return True
        return response_multi_patch

    def update_estatus_historico(self, origen, destino, folios, forma, other_fields={}, res_type='legacy'):
        query = {
            lkf_obj.f['field_id_cargado_desde_script']: 'sí',
            'f1054000a030000000000e20':{
                "-1":{
                    'f1054000a030000000000e21':origen,
                    'f1054000a030000000000e22':destino,
                    'f1054000a030000000000e23':datetime.now().strftime("%Y-%m-%d")
                }
            }
        }
        if other_fields:
            query.update(other_fields)
        response = {}
        try:
            response = lkf_api.patch_multi_record(query, forma, record_id=folios, threading=True)
        except Exception as e:
            print('***********************************************', e)
        # if res_type == 'legacy':
        #     if len(response.keys()) > 0:
        #         response =  response[response.keys()[0]]
        #         print('legacy response',response )
        #     if response.get('status_code',0)  >= 200 and response.get('status_code',0) < 300:
        #             return True
        return response

    def create_oc_and_update_status(self, metadata_oc, connection_id, LIBERACION_PAGOS, FORMA_ORDEN_SERVICIO, tecnologia, division,\
        conexiones_con_bono={}, list_folios_bonos=[]):
        folio_bonificacion = metadata_oc.pop('folio_bonificacion', '') if isinstance(metadata_oc, dict) else ''

        # New function to create oc and update status ocs and libs
        errors_to_create = []
        email_of_connection = metadata_oc.get('answers',{}).get('5a9f3d79f776480b120240b8','')

        list_ids_liberaciones = []
        list_ids_os = []
        for folio_in_oc in metadata_oc.get('answers', {}).get('f1962000000000000000fc10', []):
            list_ids_liberaciones.append( folio_in_oc.pop('_id_record_liberacion') )
            list_ids_os.append( folio_in_oc.pop('_id_record_os') )

        if not list_folios_bonos and metadata_oc.get('folios_con_bono'):
            list_folios_bonos = metadata_oc.pop('folios_con_bono')
        # Creo la Orden de compra
        response_oc = lkf_api.post_forms_answers(metadata_oc, jwt_settings_key='USER_JWT_KEY')
        # Proceso el resultado de la creación
        status_code = response_oc.get('status_code', 0)
        if status_code >= 200 and status_code < 300:
            folio_oc_creada = response_oc.get('json',{}).get('folio','')
            new_record = '/api/infosync/form_answer/{}/'.format( response_oc.get('content', {}).get('id', response_oc.get('json', {}).get('id', '')) )
            try:
                if connection_id:
                    response_2 = lkf_api.assigne_connection_records( connection_id, [new_record,])
                    print('response assigne oc=',response_2)
                    if response_2.get('status_code', 0) in [401, 500]:
                        errors_to_create.append('No se pudo asignar la OC %s a la conexion %s'%(folio_oc_creada, email_of_connection))
            except Exception as e:
                print('Error al asignar el registro: ',str(e))
            cambio_estatus_lib_pagos = None
            if tecnologia == 'cobre':
                cambio_estatus_lib_pagos = self.cambia_estatus_de_liberados_a_orden_de_compra(list_ids_liberaciones, LIBERACION_PAGOS, set_status='liberadoscon')
            elif tecnologia == 'fibra':
                cambio_estatus_lib_pagos = self.cambia_estatus_de_liberados_a_orden_de_compra(list_ids_liberaciones, LIBERACION_PAGOS)
            # Si el contratista no tiene permiso para Facturar NO se actualizarán las OS
            new_status_os = {
                'f1054000a030000000000012':'estimacion',
                'f1054000a030000000000013':'por_facturar',
                '5f40131c9bca6a32f518d9a9': folio_oc_creada
            }
            
            # Ahora actualiza los estatus de las Órdenes de Servicio
            if cambio_estatus_lib_pagos:
                estatus = self.update_estatus_historico('LIBERACION DE PAGOS', 'ORDEN DE COMPRA', list_ids_os, FORMA_ORDEN_SERVICIO, other_fields=new_status_os)

            """
            Actualizacion de OS de PSR
            """
            if metadata_oc.get('update_os_libs'):
                dict_os_update = metadata_oc['update_os_libs'].get('os', {})
                for forma_os, ids_os in dict_os_update.items():
                    res_update_psr_os = self.update_estatus_historico('LIBERACION DE PAGOS', 'ORDEN DE COMPRA', ids_os, forma_os, other_fields=new_status_os)
                    print('+++ res_update_psr_os =',res_update_psr_os)
                dict_libs_update = metadata_oc['update_os_libs'].get('libs', {})
                for forma_lib, ids_lib in dict_libs_update.items():
                    status_lib = 'liberadoscon' if forma_lib in (self.FORMA_LIBERACION_COBRE, self.FORMA_LIBERACION_COBRE_SURESTE, self.FORMA_LIBERACION_COBRE_NORTE, self.FORMA_LIBERACION_COBRE_OCCIDENTE) else 'orden_de_compra'
                    res_update_psr_libs = self.cambia_estatus_de_liberados_a_orden_de_compra(ids_lib, forma_lib, set_status=status_lib)
                    print('+++ res_update_psr_libs =',res_update_psr_libs)

            # Reviso si trae un descuento por Bonificación para actualizar el registro de ese descuento
            # if folio_bonificacion:
            #     print('Descuento Bonificación utilizado {}'.format(folio_bonificacion))
            #     datas_update_bonificacion = {
            #         '602ecf84fad280c9e6ff5f3c': 'aplicado', 
            #         '60403e22f371a6cb232888bd': folio_oc_creada,
            #         '602ed130e3df39f75d10406c': division,
            #         '602ed130e3df39f75d10406d': tecnologia
            #     }
            #     response_bonificacion = lkf_api.patch_multi_record(datas_update_bonificacion, 66446, folios=[folio_bonificacion,], jwt_settings_key='USER_JWT_KEY', threading=True)
            #     print('Respuesta aplicado set: ',response_bonificacion)
            # if list_folios_bonos:
            #     dict_set_folio_complemento = {'6307959a84d401df3a3f684f': folio_oc_creada}
            #     response_bono_complemento = lkf_api.patch_multi_record(dict_set_folio_complemento, FORMA_ORDEN_SERVICIO, folios=list_folios_bonos, jwt_settings_key='USER_JWT_KEY', threading=True)
            #     print('response_bono_complemento=',response_bono_complemento)
            #     fols_error_504 = []
            #     for fol, resp in response_bono_complemento.items():
            #         if resp.get('status_code', 0) != 202:
            #             fols_error_504.append( fol )
            #         #    continue
            #         if resp.get('status_code', 300) >= 300:
            #             print('eeeeeeeeeeeeeeeerror al pegar folio para bono en el folio {} response {}'.format(fol, resp))
            #     if fols_error_504:
            #         self.retry_update_records( FORMA_ORDEN_SERVICIO, fols_error_504, dict_set_folio_complemento, is_complemento=True )

        elif status_code == 400:
            print('response_oc=',response_oc)
            contratista_error = email_of_connection if email_of_connection else connection_id
            msg_error_back = response_oc.get('json', {}).get('error', '')#.encode('utf-8')
            errors_to_create.append(f'No se pudo crear la OC para el contratista: {contratista_error} {msg_error_back}')
        else:
            errors_to_create.append( f'Ocurrió un error al crear la OC: {response_oc}' )
        return errors_to_create
    
    def create_oc_contista(self, folios_by_connection, folio_payment, folio_oc, descuentos, LIBERACION_PAGOS, FORMA_ORDEN_SERVICIO, \
        map_email_connections, number_week, division, dict_oc_fecha_nomina):
        errors_to_create = []
        send_mail = False;
        send_push_notification = False;
        dict_count = {}
        dict_metadatas = {}
        ocs_creadas = 0
        for connection_id, info_connection in folios_by_connection.items():
            print("+++++++++++++++++ connection_id:",connection_id)
            for form_id_oc_contratista, dict_types_oc in info_connection.items():
                for type_oc, folios in dict_types_oc.items():
                    if not folios:
                        continue
                    if not dict_count.get(form_id_oc_contratista):
                        dict_count[ form_id_oc_contratista ] = self.get_folios_num( form_id_oc_contratista, folio_oc )
                    if not dict_metadatas.get(form_id_oc_contratista):
                        dict_metadatas[ form_id_oc_contratista ] = lkf_api.get_metadata(form_id_oc_contratista)
                    metadata = dict_metadatas[form_id_oc_contratista].copy()
                    answers = {}
                    metadata['folio'] = folio_oc + '-' + str( dict_count[form_id_oc_contratista] )
                    dict_count[form_id_oc_contratista] += 1
                    answers['f19620000000000000000fc5'] = 'por_facturar'
                    answers['f19620000000000000000fc9'] = len(folios.keys())
                    answers['f1962000000000000000fc10'] = []
                    answers['601346b08d12cc2721043c66'] = number_week
                    total_oc = 0
                    
                    email_of_connection = map_email_connections.get(connection_id)
                    
                    
                    totalDescuento20porc = 0
                    list_areas = []
                    for folio, detail in folios.items():
                        answers['f1962000000000000000fc10'].append(detail)
                        total_oc += detail['f1962000000000000001fc10']
                        metadata['connection_id'] = connection_id
                        totalDescuento20porc += detail.pop('descuento_20_porc')
                        if not detail['666798abf2ea5ac6c31cc955'] in list_areas:
                            list_areas.append( detail['666798abf2ea5ac6c31cc955'] )
                    answers['6667987d5a0e458726912348'] = self.list_to_str( list_areas )

                    descuento_info = self._procesar_descuentos(descuentos, email_of_connection, total_oc, totalDescuento20porc)
                    if isinstance( descuento_info, str ):
                        errors_to_create.append(descuento_info)
                        continue

                    descuento = descuento_info.get('descuento')
                    porcentaje_descuento = descuento_info.get('porcentaje_descuento')
                    default_subtotal = descuento_info.get('default_subtotal')
                    dict_descuentos_apply = descuento_info.get('dict_descuentos_apply')

                    if default_subtotal:
                        total_oc = default_subtotal
                    total_oc = total_oc - descuento

                    for descripcion_descuento, detail_descuento in dict_descuentos_apply.items():
                        value_descuento = detail_descuento.get('val', 0)
                        if detail_descuento['type'] == 'porcentaje':
                            value_descuento = total_oc * (value_descuento/float(100))
                        if "anticipo" in descripcion_descuento:
                            answers['f19620000000000000000f7c'] = p_utils.add_coma(value_descuento)
                        elif "desmontaje de modems" in descripcion_descuento:
                            answers['665e0d3ddd21dc84aae05e49'] = p_utils.add_coma(value_descuento)
                        elif "queja no atendida" in descripcion_descuento:
                            answers['665e0d3ddd21dc84aae05e4a'] = p_utils.add_coma(value_descuento)
                        elif "cobro improcedente" in descripcion_descuento:
                            answers['665e0d3ddd21dc84aae05e4b'] = p_utils.add_coma(value_descuento)
                    
                    if porcentaje_descuento:
                        monto_desccuento = total_oc * (porcentaje_descuento / float(100))
                        total_oc = total_oc - monto_desccuento

                    if totalDescuento20porc:
                        total_oc = total_oc - totalDescuento20porc

                    retencion_resico = 0
                    resico_fibra = dict_oc_fecha_nomina.get( str(connection_id), {} ).get('resico_fibra', False)
                    if resico_fibra and resico_fibra.lower() != 'no':
                        retencion_resico = total_oc * 0.0125
                        answers['621fe75ad98a2471ed6308f8'] = p_utils.add_coma(retencion_resico)

                    iva_oc = total_oc * 0.16
                    total_con_iva = (total_oc + iva_oc) - retencion_resico
                    answers['f19620000000000000000fc8'] = 'por_pagar'
                    answers['6061f8492ec2a3c070a86619'] = p_utils.add_coma(totalDescuento20porc) #descuento total 20%
                    answers['f19620000000000000000f7a'] = p_utils.add_coma(total_oc) #subtotal
                    answers['f19620000000000000000f7b'] = p_utils.add_coma(iva_oc) #iva
                    answers['f19620000000000000000fc7'] = p_utils.add_coma(total_con_iva) #total
                    answers['5a9f3d79f776480b120240b8'] = email_of_connection
                    answers.update({
                        '5c7eee84f851c24c2864910a': 'no', # Factura Trabajada
                        '5e6a86157e0431c5d15bcaf6': 'no' # Factura Cargada a SAP
                    })
                    metadata['answers'] = answers
                    metadata_extra = {}
                    metadata_agregar_script = {"device_properties":{"system": "SCRIPT","process":"PROCESO CARGA ORDEN COMPRA CONTRATISTA", "accion":'GENERA OC CONTRATISTA', "folio carga":folio_oc, "archive":"orden_de_compra.py"}}
                    metadata["properties"] = metadata_agregar_script
                    error_to_create = self.create_oc_and_update_status(metadata, connection_id, LIBERACION_PAGOS, FORMA_ORDEN_SERVICIO, 'fibra', division)
                    if not error_to_create:
                        ocs_creadas += 1
                    else:
                        errors_to_create.extend(error_to_create)
        return errors_to_create, ocs_creadas

    def update_records_status(self, folios, status, FORMA_ORDEN_SERVICIO, status_contratista=None):
        update =  {
            'f1054000a030000000000012':status,
            lkf_obj.f['field_id_cargado_desde_script']: 'sí'
        }
        if status_contratista:
            update.update({'f1054000a030000000000013':status_contratista})
        response = lkf_api.patch_multi_record(update, FORMA_ORDEN_SERVICIO, folios=folios, jwt_settings_key='USER_JWT_KEY', threading=True)
        return response

    def generate_ocs_fibra(self, current_record, LIBERACION_PAGOS, FORMA_ORDEN_SERVICIO, OC_CONTRATISTA, map_email_connections, descuentos, only_connections, number_week, \
        price_list_fibra, division, price_list_cobre, retenciones_resico, conn_carso, ocs_to_psr):
        #busca los folios que esten como liberados en la forma Liberacion de pagos
        print(f"_____ Se consultan los folios liberados para la forma {LIBERACION_PAGOS} _____")
        registros_liberacion = self.recupera_liberados_forma(LIBERACION_PAGOS, [])
        folio_oc = current_record.get('folio')
        folios = []
        #---------------------------------------------
        info_registros_liberacion = {}
        for r_lib in registros_liberacion:
            folios.append(r_lib['folio'])
            info_registros_liberacion[r_lib['folio']] = r_lib
        #---------------------------------------------
        ocs_creadas = 0
        msg_response = ''
        if info_registros_liberacion:
            # Primero recupero la conexión de los folios a los se les generará la OC y los que no aplican por estar pagados o en alguna otra OC
            total_folios = len(folios)
            print("total_folios=",total_folios)
            folios_by_connection, folios_ids, status_pago_folios = self.get_order_by_connection(FORMA_ORDEN_SERVICIO, folios, OC_CONTRATISTA, only_connections=only_connections)
            folios_by_connection_and_forms = {}
            for payment_connection_id, dict_payment_folios in folios_by_connection.items():
                payment_folios = dict_payment_folios.get('before_february', []) # + dict_payment_folios.get('february_and_more', [])
                # =================================
                # Aqui tengo el id de la conexion y los folios que le corresponden a esa conexion
                # en la función get_order_by_connection ya analicé que los folios no estén en alguna OC de las que utilizamos actualmente
                # Ya puedo consultar si el contratista NO genera facturas para crear los registros en otra forma
                folios_by_connection_and_forms.setdefault(payment_connection_id, {})
                #===================================
                # Si el folio no está en los que no aplica, pagados o en otra OC entonces se prepara su registro
                for type_folio in dict_payment_folios:
                    folios_by_connection_and_forms[payment_connection_id].setdefault(OC_CONTRATISTA, {})
                    
                    for payment_folio in dict_payment_folios[type_folio]:
                        info_record_os = folios_ids[payment_folio]
                        folio_is_psr = info_record_os.get('answers', {}).get('633d9f63eb936fb6ec9bf580', '') == 'psr'
                        record_lib = info_registros_liberacion.get( payment_folio.replace('_', '') )
                        if not record_lib:
                            record_lib = info_registros_liberacion.get( payment_folio.split('_')[0] )
                        if not record_lib:
                            print('No se encontro info de liberacion para = ',payment_folio)
                            continue
                        fila, folioDescuento20porc = self.get_folio_info(record_lib, price_list_fibra, info_record_os, payment_connection_id, price_list_cobre, conn_carso) # paso los registros ya consultados en folios_ids



                        # HASTA AQUI VOY !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


                        folio_oc_rec = fila[0] #FOLIO f19620000000000000001fc1
                        telefono_oc_rec = fila[1] #TELEFONO f19620000000000000001fc2
                        ont_oc_rec = fila[2] #ONT
                        fecha_entrega_oc_rec = fila[3]  #FECHA ENTREGA
                        filial_oc_rec = fila[4] #PCI (FILIAL)
                        paco_oc_rec = fila[5] #PACO f19620000000000000001fc3
                        cantidad_oc_rec = fila[6] #CANTIDAD
                        trabajo_oc_rec = fila[7] #TRABAJO REALIZADO f19620000000000000001fc4
                        precio_oc_rec = fila[8] #PRECIO f19620000000000000001fc5
                        precio_oc_vsi = fila[10] #PRECIO VSI f19620000000000000001fc6
                        precio_oc_met_adi = fila[14] #METROS ADICIONALES f19620000000000000001fc7
                        precio_oc_adicionales = fila[16] #PRECIO ADICIONALES f19620000000000000001fc8
                        precio_oc_total_adicionales = fila[15]#TOTAL ADICIONALES f19620000000000000001fc9
                        total_oc_rec = fila[11] #TOTAL IMPORTE A PAGAR f1962000000000000001fc10
                        tipo_tarea_oc_rec = fila[11]
                        tecnologia_oc_rec = fila[12]
                        _total_reparacion_radial = fila[17]
                        _total_radial_cepa = fila[18]
                        _total_radial_banqueta = fila[19]
                        str_descuentos_pos = fila[20]
                        
                        fecha_liquidacion = info_record_os.get('answers', {}).get('f1054000a02000000000fa02')
                        area_os = info_record_os.get('answers', {}).get('f1054000a0100000000000a2', '').upper().replace('_', ' ')
                        for_oc = 'normal'

                        #folio_payment[payment_folio] = {
                        folio_payment = {
                            'f19620000000000000001fc1' : folio_oc_rec,
                            'f19620000000000000001fc2' : telefono_oc_rec,
                            '62deccbcf1cac3245da9314d' : fecha_liquidacion,
                            '666798abf2ea5ac6c31cc955' : area_os,
                            'f19620000000000000001fc3' : paco_oc_rec,
                            'f19620000000000000001fc4' : trabajo_oc_rec,
                            'f19620000000000000001fc5' : precio_oc_rec,
                            'f19620000000000000001fc6' : precio_oc_vsi,
                            'f19620000000000000001fc7' : precio_oc_met_adi,
                            'f19620000000000000001fc8' : precio_oc_adicionales,
                            'f19620000000000000001fc9' : precio_oc_total_adicionales,
                            'f1962000000000000001fc10' : total_oc_rec,
                            '5ebedac400bef6f9b61bb863': _total_reparacion_radial,
                            '5ebedac400bef6f9b61bb864': _total_radial_cepa,
                            '5ebedac400bef6f9b61bb865': _total_radial_banqueta,
                            'descuento_20_porc': folioDescuento20porc,
                            # Se integran conceptos de A4
                            '5f0367db263081d4d60e34a9' : fila[21], #NUEVO CAMPO PARA EL CONCEPTO DE A4
                            # los demas conceptos de A4 ya no aplican
                            # '5f0367db263081d4d60e34aa' : fila[22], #total_a4_par_secundario
                            # '5f0367db263081d4d60e34ab' : fila[23], #total_a4_reporte_ivr
                            # '5f0367db263081d4d60e34ac' : fila[24], #total_a4_rosetas
                            # '5f0367db263081d4d60e34ad' : fila[25], #total_a4_modem
                            # '5f0367db263081d4d60e34ae' : fila[26], #total_a4_claro
                            # '5f0367db263081d4d60e34af' : fila[27], #total_a4_montaje_puente
                            # '5f0367db263081d4d60e34b0' : fila[28], #total_a4_desmontaje_puente
                            '6497150f3f35c6b5cd087d16' : fila[29], #total_migracion_exitosa
                            '64c81f473f6a4e86b5169a47' : fila[30], # Desmontaje en migracion
                            '5c647760d5351b000dc99870' : fila[31], # INSTALACIÓN DE POSTE DE 25'
                            '_id_record_liberacion': str( record_lib['_id'] ),
                            '_id_record_os': str( info_record_os.get('_id') )
                            }
                        if fila[32]: # Aplica bono prioridad
                            folio_payment['66d77401ca302e0003417ee7'] = self.bono_prioridad
                        if str_descuentos_pos:
                            print('dddddescuento por=',str_descuentos_pos)
                            folio_payment.update( { '60231d3a4524c60430be8e17': str_descuentos_pos } )
                        if folio_is_psr:
                            folio_payment['672cfb27388bff96a3650582'] = fila[-2] # Reparacion de Instalaciones
                            folio_payment['f19620000000000000001fc4'] = 'PSR'
                            # ocs_to_psr.setdefault(payment_connection_id, []).append(folio_payment)
                            # continue
                        folios_by_connection_and_forms[payment_connection_id][OC_CONTRATISTA].setdefault(for_oc, {}).update( { payment_folio: folio_payment } )
            if folios_by_connection_and_forms:
                #print'hasta aqui los folios serian estos', folios
                errors_to_create, ocs_creadas = self.create_oc_contista(folios_by_connection_and_forms, None, folio_oc, descuentos, LIBERACION_PAGOS, \
                    FORMA_ORDEN_SERVICIO, map_email_connections, number_week, division, retenciones_resico)
                if errors_to_create:
                    msg_response = self.list_to_str(errors_to_create)
                if status_pago_folios['no_aplica']:
                    response_update = self.update_records_status(status_pago_folios['no_aplica'], 'orden_de_compra', FORMA_ORDEN_SERVICIO)

                if status_pago_folios['pagada']:
                    response_update = self.update_records_status(status_pago_folios['pagada'], 'orden_de_compra', FORMA_ORDEN_SERVICIO, status_contratista='pagada')
            else:
                msg_response = 'No hay registros para OC'
        else:
            msg_response = 'No hay registros para OC'
        return msg_response, ocs_creadas

    """
    Funciones para Ordenes de Compra COBRE
    """
    def get_payed_order(self, folios, OC_CONTRATISTA):
        """
        Se revisa si los folios ya están en alguna Orden de Compra

        Args:
            folios (list): folios que se van a integrar en Orden de Compra

        Return:
            diccionario con folios que ya estan otra orden de compra
        """
        print("_____ Consulta si los folios estan en OC _____")
        query_oc, select_columns = self.query_oc_folios(OC_CONTRATISTA, folios)
        oc_folios_cr = self.cr.find(query_oc, select_columns )
        folios_oc = self.get_folios_of_oc(oc_folios_cr)

        status_pago_folios = {'no_aplica':[], 'pagada':[], 'otra_oc': [] }
        for folio in folios:
            if folio in folios_oc:
                status_pago_folios['otra_oc'].append(folio)
        return status_pago_folios
    
    def make_estimacion_row_cobre(self, fields_liberacion, folio_lib, price_list, map_campos, conn_carso, conn_id, order_psr):
        print(f'\n=== price_list: {price_list}\n')
        """
        make estimacion row recibe el registro de liberacion y hace el calculo del pago
        fields_liberacion es la lista del grupo repetitivo con n folios a liberar
        regresa una lista con todos los registros a liberar.
        """
        rows = []
        nivel_de_pago = 'contratista'
        if conn_id in conn_carso:
            nivel_de_pago = 'migrado'
        elif conn_id == self.ID_CONTRATISTA_TIPO_MAQTEL:
            nivel_de_pago = 'maqtel'

        for group_field in fields_liberacion:
            # Se inicializa arr_detalle con puros ceros en los campos que se cobran
            arr_detalle = [0] * len(map_campos)
            
            tipo_trabajo = group_field.pop('f2361400a0100000000000b6', '')

            # if tipo_trabajo != 'a4':
            if tipo_trabajo not in ['a4', 'a2']:
                tipo_trabajo = 'psr' if order_psr else 'a0'

            for idx, map_field in enumerate(map_campos):
                map_field_id = map_field['field_id']
                if group_field.get(map_field_id):
                    value = group_field[map_field_id]
                    try:
                        total_field = value * price_list[ nivel_de_pago ][ tipo_trabajo ]
                    except Exception as e:
                        print(f'------------ error en el precio para el folio {folio_lib} msg: {e}')
                        print(f'nivel_de_pago= {nivel_de_pago} tipo_trabajo= {tipo_trabajo} FOLIO= {folio_lib}')
                        return f'Ocurrió un error al obtener el precio para el folio: {folio_lib}'
                    arr_detalle[idx] = total_field

            rows.append(arr_detalle)
        return rows

    def get_folio_info_cobre(self, record_lib, FORMA_ORDEN_SERVICIO, price_list, oc_ids_dict, map_campos, oc_ids, order, date_february, conn_carso, total_20_row=False):
        answers_lib = record_lib['answers']
        folio_lib = str(record_lib['folio'])
        paco = answers_lib.get('f2361400a010000000000001',None)
        fields_liberacion = answers_lib['f2361400a010000000000006']

        response = { 'f19620000000000000001fc1' : order.get('folio') }

        if order:
            msg_folio_calc = f"+ + + Calculando el renglon del folio = {order['folio']} "
            os_answers = order.get('answers',{})
            conn_id = order.get('connection_id', None)
            response['connection_id'] = conn_id
            type_proyecto = os_answers.get('633d9f63eb936fb6ec9bf580', '')
            order_psr = type_proyecto == 'psr'
            rows = self.make_estimacion_row_cobre(fields_liberacion, folio_lib, price_list, map_campos, conn_carso, conn_id, order_psr)
            if not rows or isinstance(rows, str):
                return rows
            
            response['f19620000000000000001fc2'] = os_answers.get('f1054000a010000000000005')
            response['f19620000000000000001fc3'] = paco

            row_totals = [sum(r) for r in rows]
            total_folio_os = sum(row_totals)
            msg_folio_calc += 'Importe a Pagar. Solo conceptos = {} '.format(total_folio_os)

            # Identificando si el folio está marcado con descuento de 15 dias de retardo
            descuentos_por = []
            descuento15dias = os_answers.get('601c7ae006478d9cbee17e00', 'no')
            descuentoCobroMinimo = os_answers.get('5fc9269ce5363f7e3b9e3867', 'no')
            descuento_20_porciento = 0
            if (descuento15dias != 'no') or (descuentoCobroMinimo != 'no'):
                #print '... ... folio marcado para descuento de 20% 15 dias: {} Cobro Minimo: {}'.format( descuento15dias.encode('utf-8'), descuentoCobroMinimo.encode('utf-8') )
                descuento_20_porciento = total_folio_os * self.porcentaje_descuento_x_desfase
                if total_20_row:
                    total_folio_os = total_folio_os - descuento_20_porciento
                msg_folio_calc += 'Menos descuento {} = {} '.format(descuento_20_porciento, total_folio_os)
            if descuento15dias != 'no':
                descuentos_por.append('desfase_15_dias_en_carga')
            if descuentoCobroMinimo != 'no':
                descuentos_por.append('cobro_minimo')

            # apply_bono_prioridad = type_proyecto == 'prioridad'
            # if apply_bono_prioridad:
            #     total_folio_os += self.bono_prioridad
            #     response['66d77401ca302e0003417ee7'] = self.bono_prioridad

            os_fecha_liq = os_answers.get('5a1eecfbb43fdd65914505a1', '')
            response['62deccbcf1cac3245da9314d'] = os_fecha_liq
            response['666798abf2ea5ac6c31cc955'] = os_answers.get('f1054000a0100000000000a2', '').upper().replace('_', ' ')
            anio_liq = os_fecha_liq.split('-')[0]
            date_fecha_liquidacion = p_utils.str_to_date( os_fecha_liq )

            bono_to_apply = 0
            if not os_answers.get('6307959a84d401df3a3f684f'):
                bono_to_apply = os_answers.get('630105cde99330bff32df7a0', 0)
            if bono_to_apply:
                response['bono_to_apply'] = bono_to_apply
                msg_folio_calc += '... Trae bono Complemento A0 de {}'.format(bono_to_apply)
            # 20230821 El bono de complementos alta 0 ya no se aplicara a nivel de grupo repetitivo, ahora sera en el total
            print(msg_folio_calc)
            response['f1962000000000000001fc10'] = total_folio_os
            if descuentos_por:
                print('dddddescuento por=',descuentos_por)
                response['60231d3a4524c60430be8e17'] = descuentos_por
            for row_id, this_row in enumerate(rows):
                if row_id == 0:
                    response.update({ oc_ids[idx]: oc_ids_dict[oc_ids[idx]] + row for idx, row in enumerate(this_row)})
                else:
                    response.update({ oc_ids[idx]: response[oc_ids[idx]] + row for idx, row in enumerate(this_row)})

            os_tipo_os = os_answers.get('f1054000a0100000000000a1', '')
            if os_tipo_os in ['EI', 'RI']:
                os_tipo_os = 'QI'
            response['anio_liq'] = anio_liq
            response['tipo_os'] = os_tipo_os
            response['f19620000000000000001fc4'] = os_answers.get('f1054000a0100000000000a1','')
            response['descuento_20_porciento'] = descuento_20_porciento
            response['february_and_more'] = date_fecha_liquidacion >= date_february

        return response

    def evalua_folios_agregados(self, grupo_de_folios, monto_a_evaluar, folios_agregados, MONTO_MAXIMO_POR_OC):
        for fol_eval, foliosImporte in grupo_de_folios.items():
            if fol_eval not in folios_agregados:
                if monto_a_evaluar + foliosImporte['f1962000000000000001fc10'] <= MONTO_MAXIMO_POR_OC:
                    folios_agregados.append(fol_eval)
                    return foliosImporte, fol_eval
        return {}, ''
    
    def agrupa_ocs_by_monto_maximo(self, payments, MONTO_MAXIMO_POR_OC):
        ORDENES_A_GENERAR = []
        temp_oc = {'importeTotal': 0, 'foliosToOC': []}
        folios_agregados = []
        for numFolio, datosFolio in payments.items():
            while temp_oc['importeTotal'] < MONTO_MAXIMO_POR_OC:
                foliosEncontrados, folio_encontrado = self.evalua_folios_agregados(payments, temp_oc['importeTotal'], folios_agregados, MONTO_MAXIMO_POR_OC)
                if foliosEncontrados:
                    temp_oc['importeTotal'] += foliosEncontrados['f1962000000000000001fc10']
                    temp_oc['foliosToOC'].append(foliosEncontrados)
                else:
                    break
            if temp_oc['foliosToOC']:
                ORDENES_A_GENERAR.append(temp_oc)
            temp_oc = {'importeTotal': 0, 'foliosToOC': []}
            if numFolio not in folios_agregados:
                temp_oc['importeTotal'] = datosFolio['f1962000000000000001fc10']
                temp_oc['foliosToOC'].append(datosFolio)
                folios_agregados.append(numFolio)

        return ORDENES_A_GENERAR

    def get_oc_contista_metadata(self, connection_id, folio_payment, folio_oc, descuentos, FORMA_ORDEN_SERVICIO, map_email_connections, oc_count, number_week, metadata, \
        dict_oc_fecha_nomina, total_20_row=False):
        oc_count += 1 #get_folios_num(OC_CONTRATISTA, folio_oc)

        metadata['properties'] = self.get_metadata_properties('orden_de_compra.py', 'GENERA OC CONTRATISTA', process='PROCESO CARGA ORDEN COMPRA CONTRATISTA', folio_carga=folio_oc)
        
        metadata['connection_id'] = connection_id
        if FORMA_ORDEN_SERVICIO:
            metadata['folio'] = folio_oc + '-' + str(oc_count)
        
        answers = {
            'f19620000000000000000fc5': 'por_facturar',
            'f19620000000000000000fc9': len(folio_payment),
            'f1962000000000000000fc10': [],
            '601346b08d12cc2721043c66': number_week,
        }
        
        email_of_connection = map_email_connections.get(connection_id)
        
        total_oc = 0
        totalDescuento20porc = 0
        total_bono_apply = 0
        
        list_folios_con_bono = []
        list_areas = []

        for folio in folio_payment:
            detail = folio if type(folio) == dict else folio_payment.get(folio)
            #TODO for incesario la info ya se tiene
            answers['f1962000000000000000fc10'].append(detail)
            total_oc += detail['f1962000000000000001fc10']
            if not total_20_row:
                totalDescuento20porc += detail.pop('descuento_20_porciento', detail.pop('descuento_20_porc', 0))
            if detail.get('bono_to_apply'):
                total_bono_apply += detail.pop('bono_to_apply')
                list_folios_con_bono.append(detail['f19620000000000000001fc1'])
            if not detail['666798abf2ea5ac6c31cc955'] in list_areas:
                list_areas.append( detail['666798abf2ea5ac6c31cc955'] )
        answers['6667987d5a0e458726912348'] = self.list_to_str( list_areas )
        msg_subtotal_oc = f'... ... subtotal con la suma de renglones = {total_oc} '
        msg_subtotal_oc += f'Alta 0 = {total_bono_apply} '
        total_oc += total_bono_apply
        
        descuento_info = self._procesar_descuentos(descuentos, email_of_connection, total_oc, totalDescuento20porc)
        if isinstance( descuento_info, str ):
            return descuento_info

        descuento = descuento_info.get('descuento')
        porcentaje_descuento = descuento_info.get('porcentaje_descuento')
        default_subtotal = descuento_info.get('default_subtotal')
        dict_descuentos_apply = descuento_info.get('dict_descuentos_apply')

        if default_subtotal:
            total_oc = default_subtotal
        total_oc = total_oc - descuento

        for descripcion_descuento, detail_descuento in dict_descuentos_apply.items():
            value_descuento = detail_descuento.get('val', 0)
            if detail_descuento['type'] == 'porcentaje':
                value_descuento = total_oc * (value_descuento/float(100))
            if "anticipo" in descripcion_descuento:
                answers['f19620000000000000000f7c'] = p_utils.add_coma(value_descuento)
            elif "desmontaje de modems" in descripcion_descuento:
                answers['665e0d3ddd21dc84aae05e49'] = p_utils.add_coma(value_descuento)
            elif "queja no atendida" in descripcion_descuento:
                answers['665e0d3ddd21dc84aae05e4a'] = p_utils.add_coma(value_descuento)
            elif "cobro improcedente" in descripcion_descuento:
                answers['665e0d3ddd21dc84aae05e4b'] = p_utils.add_coma(value_descuento)
        
        if porcentaje_descuento:
            monto_desccuento = total_oc * (porcentaje_descuento / float(100))
            total_oc = total_oc - monto_desccuento

        if totalDescuento20porc:
            total_oc = total_oc - totalDescuento20porc

        msg_subtotal_oc += ' Descuento = {} '.format(descuento)

        retencion_resico = 0
        resico_cobre = dict_oc_fecha_nomina.get( str(connection_id), {} ).get('resico_cobre', False)
        if resico_cobre and resico_cobre.lower() != 'no':
            retencion_resico = total_oc * 0.0125
            answers['621fe75ad98a2471ed6308f8'] = p_utils.add_coma(retencion_resico)

        msg_subtotal_oc += 'Subtotal Final = {}'.format(total_oc)
        print(msg_subtotal_oc)
        iva_oc = total_oc * 0.16
        total_con_iva = (total_oc + iva_oc) - retencion_resico
        answers.update({
            'f19620000000000000000fc8': 'por_pagar',
            '6061f8492ec2a3c070a86619': p_utils.add_coma(totalDescuento20porc), #descuento total 20%
            'f19620000000000000000f7a': p_utils.add_coma(total_oc), #subtotal
            'f19620000000000000000f7b': p_utils.add_coma(iva_oc), #iva
            'f19620000000000000000fc7': p_utils.add_coma(total_con_iva), #total
            '5a9f3d79f776480b120240b8': email_of_connection,
            '5c7eee84f851c24c2864910a': 'no', # Factura Trabajada
            '5e6a86157e0431c5d15bcaf6': 'no' # Factura Cargada a SAP
        })
        if total_bono_apply:
            answers['62e8618607b8e5d101ed3f8c'] = p_utils.add_coma(total_bono_apply)
        if list_folios_con_bono:
            answers['f19620000000000000000fc6'] = 'Folios Complemento Alta 0: {}'.format(self.list_to_str(list_folios_con_bono))
        metadata['answers'] = answers
        metadata['folios_con_bono'] = list_folios_con_bono
        return metadata

    def generate_ocs_cobre(self, current_record, LIBERACION_PAGOS, FORMA_ORDEN_SERVICIO, OC_CONTRATISTA, map_email_connections, descuentos, only_connections, number_week, \
        price_list_cobre, division, dict_oc_fecha_nomina, conn_carso, ocs_to_psr):
        map_campos = [{
            'field_id': '681c0e22e3d9bc611e3a5187',
            'name': 'PSR',
            'oc_field_id': '682bc981733bc1ca31734da0'
        },{
            'field_id': '681c0e22e3d9bc611e3a5188',
            'name': 'A4',
            'oc_field_id': '682bc981733bc1ca31734d9f'
        },{
            'field_id': '681c0e22e3d9bc611e3a5189',
            'name': 'A0',
            'oc_field_id': '682bc981733bc1ca31734d9e'
        },{
            'field_id': '6916c12d5ab0bd965da971b3',
            'name': 'A2',
            'oc_field_id': '6916c0d1e6bbebbebfa971b6'
        }]
        desc_20_porc_as_row = True

        # TODO esto se puede mejorar
        map_ids, oc_ids = [], []
        for a in map_campos:
            map_ids.append(a['field_id'])
            oc_ids.append(a['oc_field_id'])

        os_vs_oc_field_id = {d['field_id']:d['oc_field_id'] for d in map_campos}
        oc_ids_dict = {oc_ids[idx]:0 for idx, a in enumerate(os_vs_oc_field_id)}
        
        
        #busca los folios que esten como liberados en la forma Liberacion de pagos
        oc_count = 0
        folios = []
        msg_response = ''
        ocs_creadas = 0
        
        print(f"_____ Se obtienen los folios liberados de la forma {LIBERACION_PAGOS} _____")
        registros_liberacion_cr = self.recupera_liberados_forma(LIBERACION_PAGOS, [], is_cobre=True)
        folio_oc = current_record.get('folio')
        group_ocs_cobre = {}
        folios_carga_liberados = []
        registros_liberacion = []
        for os_liberada in registros_liberacion_cr:
            folio_liberado = os_liberada['folio']
            folios_carga_liberados.append( folio_liberado[:8] if len(folio_liberado) > 8 else folio_liberado )
            registros_liberacion.append(os_liberada)
        if not folios_carga_liberados:
            msg_response = 'No hay registros para OC'
            return msg_response, ocs_creadas
        print("folios_carga_liberados=",len(folios_carga_liberados))
        
        print("_____ Obtiene los registros de OS _____")
        
        some_connections = {}
        if only_connections:
            some_connections['connection_id'] = {'$in': only_connections}
        
        os_consultadas = p_utils.get_records_existentes(FORMA_ORDEN_SERVICIO, folios_carga_liberados, extra_params=some_connections, os_with_phone=True)
        if not os_consultadas:
            msg_response = 'No hay registros para OC'
            return msg_response, ocs_creadas

        folios_en_oc = self.get_payed_order(folios_carga_liberados, OC_CONTRATISTA)
        
        dict_dates_by_connection = {}
        for os_liberada in registros_liberacion:
            order = os_consultadas.get( os_liberada['folio'], None )
            
            if not order:
                print(f"Folio - lib: {os_liberada['folio']} NO se encontro registro de OS, o bien, el folio es de contratista que no genera OCs")
                continue
            
            folio_telefono = '{}_{}'.format( order['folio'], order['answers'].get('f1054000a010000000000005') )
            
            if os_liberada['folio'] in folios_en_oc['otra_oc']:
                print('Este folio ya se encuentra en otra Orden de compra = ',folio_telefono)
                continue
            
            if not order.get('connection_id', False):
                print('Este folio marca error porque no tiene conexion =',folio_telefono)
                continue

            folio_is_psr = order['answers'].get('633d9f63eb936fb6ec9bf580', '') == 'psr'
            folios.append(os_liberada['folio'])
            conn = order['connection_id']
            if not dict_dates_by_connection.get(conn, False):
                # str_date_for_nomina = dict_oc_fecha_nomina.get( str(conn), {} ).get('fecha_nomina', '')
                # if not str_date_for_nomina:
                str_date_for_nomina = '2022-02-01'
                dict_dates_by_connection[ conn ] = datetime.strptime( str_date_for_nomina, '%Y-%m-%d' )
            date_february = dict_dates_by_connection[ conn ]

            fila_dict = self.get_folio_info_cobre(os_liberada, FORMA_ORDEN_SERVICIO, price_list_cobre, oc_ids_dict, map_campos, oc_ids, order, date_february, conn_carso, total_20_row=desc_20_porc_as_row)
            if not fila_dict:
                continue
            
            if isinstance(fila_dict, str):
                return fila_dict, ocs_creadas
            
            connection_id = fila_dict.get('connection_id',0)
            
            fila_dict.update({
                '_id_record_os': str(order['_id']),
                '_id_record_liberacion': str(os_liberada['_id'])
            })

            # if folio_is_psr:
            #     ocs_to_psr.setdefault(connection_id, []).append(fila_dict)
            #     continue

            '''
            Agrupando los folios por año de liquidacion
            '''
            # os_anio_liq = fila_dict.pop('anio_liq')
            
            # 2024-01-12 Se solicita ya no hacer la agrupacion por año de liquidacion, por lo que se deja un año fijo
            # se conservan los cambios por si en algun momento se regresa a la agrupacion anual.
            os_anio_liq = 1

            os_tipo = fila_dict.pop('tipo_os')
            pos_tipo_os = os_tipo if os_tipo in ['TN', 'QI'] else 'all'
            
            if not group_ocs_cobre.get( os_anio_liq ):
                group_ocs_cobre[ os_anio_liq ] = {
                    'TN': {},
                    'QI': {},
                    'all': {},
                }
            if not group_ocs_cobre[ os_anio_liq ][ pos_tipo_os ].get(connection_id):
                group_ocs_cobre[ os_anio_liq ][ pos_tipo_os ][connection_id] = {}
            group_ocs_cobre[ os_anio_liq ][ pos_tipo_os ][connection_id][ folio_telefono ] = fila_dict
        
        if len(folios) > 0:
            all_errors_to_create = []
            group_ocs_to_create = {}
            for anio, dict_tipos in group_ocs_cobre.items():
                print('+++++ Creando ocs para año:',anio)
                for tipo_orden, connection_os_info in dict_tipos.items():
                    print('----- Creando ocs para Tipo de OS', tipo_orden)
                    #TODO QUITAR FOLIOS DE ORDEN DE COMPRA Y LOS YA PAGADAS
                    for id_connection, payments in connection_os_info.items():
                        if only_connections and id_connection not in only_connections:
                            continue
                        
                        ORDENES_A_GENERAR = self.agrupa_ocs_by_monto_maximo(payments, self.MONTO_MAXIMO_POR_OC)
                        
                        # Agrupo las OCs a crear por el contratista al que pertenecen
                        if not group_ocs_to_create.get( id_connection ):
                            #group_ocs_to_create[ id_connection ] = []
                            group_ocs_to_create[ id_connection ] = {'others': []}
                        where_set_ocs = 'others'
                        group_ocs_to_create[ id_connection ][ where_set_ocs ].extend( ORDENES_A_GENERAR )
            print(f"_____ Obtengo los metadatos de la forma de OC {OC_CONTRATISTA} _____")
            metadata_form = lkf_api.get_metadata(form_id = OC_CONTRATISTA)

            for id_conexion, dict_ocs_to_create in group_ocs_to_create.items():
                for type_oc_create, ocs_to_create in dict_ocs_to_create.items():
                    print('------- Creando OCs para contratista', id_conexion)
                    print('------- OCs a crear', len(ocs_to_create))
                    ocs_sorted = sorted( ocs_to_create, key=lambda i:i['importeTotal'], reverse=True )
                    for i, oc_to_create in enumerate(ocs_sorted):
                        folios_2_update = []
                        foliosByPaco = oc_to_create['foliosToOC']
                        foliosPaymentInMontoMaximo = {}
                        for infoFolio in foliosByPaco:
                            foliosPaymentInMontoMaximo[ infoFolio['_id_record_os'] ] = infoFolio
                            folios_2_update.append(infoFolio['f19620000000000000001fc1'])
                        metadata_copy = metadata_form.copy()

                        metadata_oc = self.get_oc_contista_metadata(id_conexion, foliosPaymentInMontoMaximo, folio_oc, descuentos, FORMA_ORDEN_SERVICIO, map_email_connections, oc_count, number_week, metadata_copy, \
                            dict_oc_fecha_nomina, total_20_row=desc_20_porc_as_row)
                        # else:
                        print('len folios de la OC',len(folios_2_update))
                        list_folios_con_bono = []
                        if type(metadata_oc) == dict:
                            list_folios_con_bono = metadata_oc.pop('folios_con_bono')
                        if type(metadata_oc) == str:
                            error_create_oc = [metadata_oc,]
                        else:
                            error_create_oc = self.create_oc_and_update_status(metadata_oc, id_conexion, LIBERACION_PAGOS, FORMA_ORDEN_SERVICIO, 'cobre', division, list_folios_bonos=list_folios_con_bono)
                        if error_create_oc:
                            all_errors_to_create.extend(error_create_oc)
                        else:
                            ocs_creadas += 1

            if all_errors_to_create:
                msg_response = self.list_to_str(all_errors_to_create)
        else:
            msg_response = 'No hay registros para OC'
        return msg_response, ocs_creadas

    def run_script_set_folio_oc(self):
        """
        Ejecuta script que se encarga de procesar las Ordenes Creadas para pegar el folio en las OS
        """
        for_update_hoy = datetime.now()
        for_update_ayer = for_update_hoy - timedelta(days=1)
        for_update_maniana = for_update_hoy + timedelta(days=1)
        res = lkf_api.run_script({
            "script_id": self.SCRIPT_ID_SET_FOLIO_OC,
            "desde": datetime.strftime(for_update_ayer, '%Y-%m-%d'),
            "hasta": datetime.strftime(for_update_maniana, '%Y-%m-%d')
        })

    def inicia_proceso_generar_ocs(self, only_connections, dict_info_connection, conn_carso):
        """
        Se arranca el proceso para generar Órdenes de Compra parar los contratistas

        Args:
            only_connections (list): Emails de contratistas a los que solo se van a considerar para generar su orden de compra
                                    si la lista esta vacía, se genera Órdenes para todos los contratistas

            dict_info_connection (dict): Diccionario con la información de los contratistas

        Return:
            Lista de Órdenes de compra creadas
        """

        # Se obtienen los descuentos desde el archivo excel
        dict_emails_descuentos = self.get_descuentos_en_xls()
        if dict_emails_descuentos.get('error'):
            file_errores_desc = p_utils.upload_error_file(dict_emails_descuentos['header'], dict_emails_descuentos['error'], current_record['form_id'], file_field_id='f2362800a010000000000005')
            current_record['answers'].update(file_errores_desc)
            return p_utils.set_status_proceso(current_record, record_id, 'error')

        # Calculo el número de semana que aparecerá en las Órdenes de Compra
        number_week = p_utils.calcula_numero_semana()

        print("_____ Se consulta la lista de precios FIBRA _____")
        price_list_fibra = self.get_price_list()
        print("_____ Consulta la lista de precios Cobre _____")
        price_list_cobre = self.get_price_list_cobre()
        
        # descuentos_bonificacion = get_descuentos_bonificacion()
        retenciones_resico = self.get_retenciones_resico()

        dict_general_msg_error = {}
        dict_general_msg_ok = {}
        dict_form_connections = {}
        map_users_email, map_email_connections = {}, {}
        ocs_to_psr = {}

        for div in self.all_divisiones:
            tecnologia = div.get('tecnologia')
            division = div.get('division')
            tecnologia_division = f"{tecnologia}_{division}"
            dict_general_msg_error[ tecnologia_division] = []
            dict_general_msg_ok[ tecnologia_division] = 0
            print("====================================================")
            print( f"{tecnologia} {division}" )
            print("====================================================")

            # IDs de las formas de Orden de Servicio, Liberacion y Orden de Compra
            FORMA_ORDEN_SERVICIO, LIBERACION_PAGOS, OC_CONTRATISTA = p_utils.get_id_os(division, tecnologia)
            
            # Se consultan las conexiones que tienen compartida la forma de Orden de Servicio y se actualiza el diccionario
            if not dict_form_connections.get(FORMA_ORDEN_SERVICIO):
                print(f"_____ consultando usuarios que tienen compartida la forma de OS: {FORMA_ORDEN_SERVICIO} _____")
                dict_form_connections[FORMA_ORDEN_SERVICIO] = lkf_api.get_form_connections(FORMA_ORDEN_SERVICIO)

            # Se revisa que los emails de los descuentos sean correctos
            form_connections = dict_form_connections[FORMA_ORDEN_SERVICIO]
            descuentos, emails_not_found = self.validate_emails_descuentos( form_connections, dict_emails_descuentos.get( tecnologia_division, [] ), map_users_email, map_email_connections )
            if emails_not_found:
                dict_general_msg_error[ tecnologia_division ].append( ' no se encontraron los emails para Descuento: ' + self.list_to_str(emails_not_found) )
                continue

            # Se empiezan a procesar las Ordenes de compra según la Tecnologia
            if tecnologia == 'fibra':
                msg_response, ocs_creadas = self.generate_ocs_fibra(current_record, LIBERACION_PAGOS, FORMA_ORDEN_SERVICIO, OC_CONTRATISTA, map_email_connections, descuentos, \
                    only_connections, number_week, price_list_fibra, division, price_list_cobre, retenciones_resico, conn_carso, ocs_to_psr)
            elif tecnologia == 'cobre':
                msg_response, ocs_creadas = self.generate_ocs_cobre(current_record, LIBERACION_PAGOS, FORMA_ORDEN_SERVICIO, OC_CONTRATISTA, map_email_connections, descuentos, \
                    only_connections, number_week, price_list_cobre, division, retenciones_resico, conn_carso, ocs_to_psr)

            if msg_response:
                dict_general_msg_error[ tecnologia_division ].append( msg_response )
            if ocs_creadas:
                dict_general_msg_ok.update( { tecnologia_division: ocs_creadas } )

        



        # if ocs_to_psr:
        #     metadata_oc_PSR = lkf_api.get_metadata(self.FORMID_OC_PSR)

        #     for connection_id_for_oc_psr, folios_to_oc_psr in ocs_to_psr.items():
        #         conexion_psr = int(connection_id_for_oc_psr)
        #         info_connection = {'id': conexion_psr, 'email': dict_connections.get(conexion_psr, {}).get('email')}

        #         folios_psr_afiliados, folios_psr_no_afiliados = [], []

        #         # Generan las OC de PSR
        #         if folios_psr_no_afiliados:
        #             metadata_psr_copy = metadata_oc_PSR.copy()
                    
        #             metadata_oc_psr = self.get_oc_contista_metadata(conexion_psr, folios_to_oc_psr, current_record['folio'], [], None, map_email_connections, 0, number_week, metadata_psr_copy, \
        #                     retenciones_resico, total_20_row=True)
                    
        #             if type(metadata_oc_psr) == str:
        #                 dict_general_msg_error.setdefault('PSR', []).append( metadata_oc_psr )
        #                 continue
                    
        #             res_create_oc_psr = self.create_oc_and_update_status(metadata_oc_psr, conexion_psr, None, None, '', '')

        #             print('\n\n --- res_create_oc_psr =',res_create_oc_psr)
        #             if not res_create_oc_psr:
        #                 dict_general_msg_ok.setdefault('PSR', 0)
        #                 dict_general_msg_ok['PSR'] += 1
        #             else:
        #                 dict_general_msg_error.setdefault('PSR', []).append( self.list_to_str(res_create_oc_psr) )
        
        # Respuestas finales despues de la ejecucion
        print("============= dict_general_msg_error=",dict_general_msg_error)
        print("============= dict_general_msg_ok=",dict_general_msg_ok)
        
        general_msg_error = [ \
            f"{tec_div_err.upper().replace('_', ' ')}: {self.list_to_str(list_err)}" \
            for tec_div_err, list_err in dict_general_msg_error.items() if list_err \
        ]

        general_msg_ok = [ \
            f"{tec_div_ok.upper().replace('_', ' ')}: {ocs_ok} ordenes creadas" \
            for tec_div_ok, ocs_ok in dict_general_msg_ok.items() if ocs_ok \
        ]

        current_record['answers']['5f10d2efbcfe0371cb2fbd39'] = 'ordenes_generadas'
        if general_msg_error:
            current_record['answers']['5fd05319cd189468810100c9'] = self.list_to_str(general_msg_error)
            current_record['answers']['5f10d2efbcfe0371cb2fbd39'] = 'error'
        if general_msg_ok:
            current_record['answers']['5fd05319cd189468810100c8'] = self.list_to_str(general_msg_ok)
        response = lkf_api.patch_record(current_record, record_id, jwt_settings_key='USER_JWT_KEY')
        
        # Se ejecuta script para pegar el folio de Orden de Compra en las Ordenes de Servicio
        self.run_script_set_folio_oc()
    
    def orden_de_compra(self):
        """ Se inicia el proceso para generar las Ordenes de Compra """
        p_utils.set_status_proceso(current_record, record_id, 'procesando')
        
        # Solo generar las Órdenes de Compra para la siguiente lista de contratistas
        connections_in_xls = self.get_only_connections()
        if connections_in_xls.get('error'):
            str_emails_not_found = self.list_to_str( connections_in_xls['error'] )
            return p_utils.set_status_proceso(current_record, record_id, 'error', f"Emails no encontrados, favor de revisar: {str_emails_not_found}")
        only_connections = connections_in_xls.get('result', [])
        dict_info_connection = connections_in_xls.get('info_connections', {})



        all_contratistas_1_0 = self.get_all_contratistas_from_catalog()
        contratistas_precio_carso = [ idUser for idUser, valsUser in all_contratistas_1_0.items() if valsUser.get('contratista_carso') ]



        return self.inicia_proceso_generar_ocs(only_connections, dict_info_connection, contratistas_precio_carso)

if __name__ == '__main__':
    print("--- --- --- Se empiezan a generar las Ordenes de Compra --- --- ---")
    lkf_obj = GenerarOrdenDeCompra(settings, sys_argv=sys.argv, use_api=True)

    lkf_obj.console_run()

    current_record = lkf_obj.current_record
    lkf_api = lkf_obj.lkf_api
    
    # Configuraciones de JWT de usuarios. 
    # Por default JWT_KEY trae la sesion de la cuenta donde se instala el modulo, es decir el jwt de la cuenta padre
    # Ojo con esto porque deberia estar en base pero como que no lo hizo bien, tons desde aqui lo intentare, solo por ahora
    jwt_parent = lkf_api.get_jwt(api_key=settings.config['APIKEY'], user=settings.config['USERNAME'])
    # Probar con APIKEY_JWT_KEY
    config['JWT_KEY'] = jwt_parent

    # Usuario que está enviando el registro
    jwt_complete = simplejson.loads(sys.argv[2])
    config['USER_JWT_KEY'] = jwt_complete["jwt"].split(' ')[1]
    
    # Admin PCLink
    # ToDo ... Este jwt hay que cambiarlo por un JWT_KEY_ADMIN
    jwt_admin = lkf_api.get_jwt(api_key='398bd78880b1675a4a8d06d8a89e712ad9b499fb', user='adminpclink@operacionpci.com.mx')
    config['JWT_KEY_ADMIN'] = jwt_admin
    
    # Se actualiza el settings con los jwts que agregamos
    settings.config.update(config)

    # Utils
    from pci_get_connection_db import CollectionConnection
    colection_connection = CollectionConnection(1259, settings)
    cr_admin = colection_connection.get_collections_connection()

    from pci_base_utils import PCI_Utils
    p_utils = PCI_Utils(cr=lkf_obj.cr, cr_admin=cr_admin, lkf_api=lkf_api, net=lkf_obj.net, settings=settings, lkf_obj=lkf_obj)

    record_id =  lkf_obj.record_id

    lkf_obj.orden_de_compra()