# -*- coding: utf-8 -*-
"""
Se ejecuta en la forma Complementos de Pago Contratista cuando el estatus es Validar complementos
se buscan los registros de Pagos SAP pendientes y se evalúa que cuadre con los importes
se enlistan los registros donde se aplica la(s) factura(s) cargada(s)
"""
import sys, simplejson
from produccion_pci_utils import Produccion_PCI
from account_settings import *

class ComplementosDePago(Produccion_PCI):
    """docstring for ComplementosDePago"""
    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

        self.form_id_oc = {
            self.FORMA_ORDEN_COMPRA_FIBRA: {'tecnologia': 'FTTH', 'division': 'METRO'},
            self.FORMA_ORDEN_COMPRA_FIBRA_SURESTE: {'tecnologia': 'FTTH', 'division': 'SUR'},
            self.FORMA_ORDEN_COMPRA_FIBRA_NORTE: {'tecnologia': 'FTTH', 'division': 'NORTE'},
            self.FORMA_ORDEN_COMPRA_FIBRA_OCCIDENTE: {'tecnologia': 'FTTH', 'division': 'OCCIDENTE'},
            self.FORMA_ORDEN_COMPRA_COBRE: {'tecnologia': 'COBRE', 'division': 'METRO'},
            self.FORMA_ORDEN_COMPRA_COBRE_SURESTE: {'tecnologia': 'COBRE', 'division': 'SUR'},
            self.FORMA_ORDEN_COMPRA_COBRE_NORTE: {'tecnologia': 'COBRE', 'division': 'NORTE'},
            self.FORMA_ORDEN_COMPRA_COBRE_OCCIDENTE: {'tecnologia': 'COBRE', 'division': 'OCCIDENTE'}
        }

    def get_complementos(self, xml_dict):
        """
        Se busca la lista de Complementos que estan dentro del xml
        """
        list_complemento = []
        for i, v in xml_dict.items():
            if 'complemento' in i and isinstance( v, list ):
                list_complemento = v
        print('list_complemento=',simplejson.dumps(list_complemento, indent=4))
        return list_complemento

    def get_data_montos(self, info_pago):
        """
        Se obtienen los impuestos y Monto del xml
        """
        return {
            'impsaldoant': float( info_pago.get('impsaldoant', 0) ), 
            'imppagado': float( info_pago.get('imppagado', 0) ), 
            'monto': float( info_pago.get('monto', 0) ) 
        }

    def get_info_oc(self, uuid_xml, user_id):
        """
        Se busca el registro de Orden de Compra del contratista con el UUID de la factura

        Args:
            uuid_xml (str): UUID de la factura xml
            user_id (int): ID de la conexion (contratista)

        Return:
            Registro de orden de compra encontrada
        """
        rec_oc_found = lkf_obj.cr.find_one({
            'form_id': {'$in': [
                self.FORMA_ORDEN_COMPRA_FIBRA, 
                self.FORMA_ORDEN_COMPRA_FIBRA_SURESTE, 
                self.FORMA_ORDEN_COMPRA_FIBRA_NORTE, 
                self.FORMA_ORDEN_COMPRA_FIBRA_OCCIDENTE, 
                self.FORMA_ORDEN_COMPRA_COBRE, 
                self.FORMA_ORDEN_COMPRA_COBRE_SURESTE, 
                self.FORMA_ORDEN_COMPRA_COBRE_NORTE, 
                self.FORMA_ORDEN_COMPRA_COBRE_OCCIDENTE, 
            ]},
            'deleted_at': {'$exists': False},
            'connection_id': user_id,
            'answers.5d07e0956906388a4dc2a039': uuid_xml
        },{'form_id': 1, 'folio': 1})

        if not rec_oc_found:
            return {}
        
        info_oc = self.form_id_oc.get( rec_oc_found['form_id'], {} )
        info_oc.update({
            'folio': rec_oc_found['folio'],
            'form_id': rec_oc_found['form_id']
        })

        return info_oc

    def get_uuid_and_montos(self, xml_dict, fechapago):
        """
        Se procesa la informacion de la factura para obtener el UUID y la lista de impuestos y montos

        Args:
            xml_dict (dict): diccionario con la informacion del xml

        Return:
            UUID de la factura y lista de impuestos y monto
        """
        uuid_xml, list_montos_doctoRelacionado = '', []
        list_complemento = self.get_complementos(xml_dict)
        for c in list_complemento:
            if c.get('uuid'):
                uuid_xml = c['uuid']
            for name_i in c:
                # NUEVAS VARIACIONES ahora se va aporocesar los DoctoRelacionado dejando una lista de todos los montos encontrados
                # Los pagos se pueden aplicar si: 
                # 1. Alguno de los montos de cuadra a algun pago sap pendiente
                # 2. Si no se cumple lo primero, la suma de todos los montos cuadra con un pago pendiente
                if 'pagos' in name_i:
                    if type(c[name_i]) == list:
                        for pago in c[name_i]:
                            list_montos_doctoRelacionado.append( self.get_data_montos( pago ) )
                            if not fechapago:
                                fechapago = pago.get('fechapago','').split('T')[0]
                    elif type(c[name_i]) == dict:
                        pago = c[name_i]
                        list_montos_doctoRelacionado.append( self.get_data_montos( pago ) )
                        if not fechapago:
                            fechapago = pago.get('fechapago','').split('T')[0]
        print(f'.. .. fechapago = {fechapago}')
        return uuid_xml, list_montos_doctoRelacionado, fechapago

    def get_pagos_sap_pendiente(self, contratista_complemento, tecnologia_selected):
        """
        Pagos SAP Complementos de Pagos que pertenecen al contratista principal y que esta pendiente
        """
        return self.get_records(
            self.FORMA_PAGOS_SAP, 
            query_answers={
                'answers.62d06e922fd9244967a3c167': {'$in': contratista_complemento },
                'answers.62d06e922fd9244967a3c16b': 'pendientes',
                'answers.62d0748e8cd47e93d17e5c9e': tecnologia_selected.lower()
            }, 
            select_columns=['folio', 'form_id', '_id', 'answers']
        )

    def evaluate_monto_pago(self, importe_pagos, all_montos_found, total_factura ):

        def is_close( variacion_montos ):
            return -0.1 <= variacion_montos <= 0.1

        for monto_doctoRelacionado in all_montos_found:
            keys = ['monto', 'impsaldoant', 'imppagado']
            for k in keys:
                valor = monto_doctoRelacionado.get(k)
                diff = importe_pagos - valor
                print(f'{k} :: importe_pagos - {k} = {diff}')
                if is_close( diff ):
                    print('Coincidencia encontrada, eliminando monto relacionado...')
                    all_montos_found.remove(monto_doctoRelacionado)
                    return True
        
        # Segunda opción: suma de todos los imppagado
        total_all_montos_found = sum([ a.get('imppagado') for a in all_montos_found ])
        print('total_all_montos_found=',total_all_montos_found)
        variacion = total_all_montos_found - importe_pagos
        print('total_all_montos_found - importe_pagos = ',variacion)
        if is_close(variacion):
            print('Coincidencia por suma total, limpiando lista de montos...')
            all_montos_found *= 0
            return True
        
        # Tercera opción: comparar con total_factura
        variacion = importe_pagos - total_factura
        print('Evaluando contra total de la factura :: importe_pagos - total_factura =', variacion)
        if is_close(variacion):
            print('Coincidencia con total factura, marcando como pagado...')
            total_factura = 0
            return True
        
        return False

    def set_pago_aplicado(self, record_pago, new_group):
        record_pago['answers']['62d06e922fd9244967a3c16b'] = 'aplicada'
        record_pago['answers']['62d06e2d663076429e6ffa5c'] = new_group
        res_aplicado = lkf_api.patch_record(record_pago, jwt_settings_key='APIKEY_JWT_KEY')
        print('res_aplicado=',res_aplicado)

    def procesa_complemento(self):
        error_sets = []
        tecnologia_selected = self.answers.get('62d06f21a42290ef62632a74', '').upper()
        total_complementos = 0
        all_montos_found = []

        current_record['answers']['62793beeee0f419f7b6bfbaf'] = 'terminado'
        parent_id = p_utils.get_parent_id( self.record_user_id )
        dict_xml = {}
        group_complementos = self.answers.get('62d06e2d663076429e6ffa5c', [])
        fechapago = ''
        for complemento in group_complementos:
            """
            Para cada complemento leo su factura xml para buscar en qué Orden de Compra fue cargada
            """
            file_url = complemento.get('62d06e882fd9244967a3c165', [])[0].get('file_url', '')
            xml, root = self.get_xml_root(file_url, get_all_root=True)
            if isinstance(xml, str):
                # self.notify_error("62d06e882fd9244967a3c165", "Complemento XML", xml)
                return p_utils.set_status_proceso(current_record, record_id, 'error', msg=xml, field_status='62793beeee0f419f7b6bfbaf', field_msg='62793beeee0f419f7b6bfbb0')
            
            dict_xml = self.integration_get_dict_node(root)

            # Se busca el UUID
            uuid_xml, list_montos_doctoRelacionado, fechapago = self.get_uuid_and_montos(dict_xml, fechapago)
            
            # Se valida el Tipo de Comprobante
            tipo_de_comprobante = dict_xml.get('tipodecomprobante', '')
            print('tipo_de_comprobante=',tipo_de_comprobante)
            if tipo_de_comprobante.lower() != 'p':
                return p_utils.set_status_proceso(current_record, record_id, 'error', msg='Tipo de Comprobante no aceptado', field_status='62793beeee0f419f7b6bfbaf', field_msg='62793beeee0f419f7b6bfbb0')

            # Se consulta el registro de Orden de Compra donde está el uuid de la factura que se esta procesando
            info_oc = self.get_info_oc(uuid_xml, parent_id)
            print(f'************** uuid_xml= {uuid_xml} info_oc= {info_oc}')

            total_complemento = sum( [ com.get('imppagado') for com in list_montos_doctoRelacionado ] )
            complemento.update({
                '62792ee16fa283d88a102c30': info_oc.get('folio',''),
                '62792ee16fa283d88a102c31': info_oc.get('division',''),
                '62d06e882fd9244967a3c166': p_utils.add_coma(total_complemento)
            })

            all_montos_found.extend( list_montos_doctoRelacionado )
        
        # Si existió error en alguna de las facturas el estatus se marcara como error
        if error_sets:
            # self.notify_error("62d06e882fd9244967a3c165", "Complemento XML", self.list_to_str(error_sets))
            return p_utils.set_status_proceso(current_record, record_id, 'error', msg=self.list_to_str(error_sets), field_status='62793beeee0f419f7b6bfbaf', field_msg='62793beeee0f419f7b6bfbb0')
        else:
            """
            Se debe validar el total de las facturas con el pago a complementos pendientes
            """
            # Registro de contratistas para complementos donde el contratista que carga las facturas es parte del grupo
            record_contratista_complemento = self.get_contratista_complemento( parent_id, get_full_records=True )
            contratista_complemento = []
            cuentas_contratistas = []
            for r in record_contratista_complemento:
                print('Contratista complemento',r['folio'])
                contratista_complemento.append(r['answers'].get('62d071930a1b1ff9eaa3c0f4', ''))
                cuentas_contratistas += r['answers'].get('62d071173eeb3a67815c74fe', [])
            
            if contratista_complemento:
                # Se obtienen los registros de Pagos SAP
                record_pagos_sap = self.get_pagos_sap_pendiente(contratista_complemento, tecnologia_selected)
                print('all_montos_found=',all_montos_found)
                dict_errors = {}
                list_oks = []
                total_factura = float( dict_xml.get('total', 0) )
                
                # Se procesan los registros de Pagos SAP encontrados
                other_errors = []
                for pagos in record_pagos_sap:
                    folio_record_pago = pagos['folio']
                    print('********** procesando registro de pagos sap = ',folio_record_pago)
                    
                    # Se evalua el importe para ver si le queda algun monto, o bien, la suma de todos
                    importe_pagos = float( pagos['answers'].get('62d06e922fd9244967a3c16a', '0').replace(',', '') )
                    print('importe_pagos=',importe_pagos)

                    fecha_transferencia = pagos['answers'].get('62d06e922fd9244967a3c168', '').split(' ')[0]
                    print(f'fecha_transferencia= {fecha_transferencia} fechapago= {fechapago} importe_pagos= {importe_pagos}')
                    if fecha_transferencia != fechapago:
                        other_errors.append( 'La fecha de Transferencia del complemento {} no es igual a la del XML'.format(pagos['folio']) )
                        continue

                    is_accepted = self.evaluate_monto_pago( importe_pagos, all_montos_found, total_factura )
                    if is_accepted:
                        list_oks.append(folio_record_pago)
                        self.set_pago_aplicado(pagos, group_complementos)
                    else:
                        dict_errors[ folio_record_pago ] = p_utils.add_coma(importe_pagos)
                
                full_msg = ''
                if list_oks:
                    full_msg = 'Registros de Pago aplicados: {}'.format( self.list_to_str( list_oks ) )
                    current_record['answers']['62d23a29738a5d6da5632a4a'] = 'aplicado'
                    current_record['editable'] = False
                if dict_errors:
                    # print('dict_errors=',dict_errors)
                    current_record['answers']['62793beeee0f419f7b6bfbaf'] = 'error'
                    full_msg += ' Montos de Pago que no se encontraron en el complemento: {}'.format( self.list_to_str( dict_errors.values() ) )
                if other_errors:
                    current_record['answers']['62793beeee0f419f7b6bfbaf'] = 'error'
                    full_msg += self.list_to_str( other_errors )
                
                # if not list_oks:
                #     full_msg = 'No se encontraron Pagos SAP pendientes' if not full_msg else full_msg
                #     self.notify_error("62d06e882fd9244967a3c165", "Complemento XML", full_msg)
                
                current_record['answers']['62793beeee0f419f7b6bfbb0'] = full_msg
                lkf_api.patch_record(current_record, record_id, jwt_settings_key='USER_JWT_KEY')
            else:
                # self.notify_error("folio", "Folio", "El contratista no se encontró en algún registro de Contratistas para Complementos de Pago")
                return p_utils.set_status_proceso(current_record, record_id, 'error', 
                    msg='El contratista no se encontró en algún registro de Contratistas para Complementos de Pago', 
                    field_status='62793beeee0f419f7b6bfbaf', 
                    field_msg='62793beeee0f419f7b6bfbb0')

        # sys.stdout.write(simplejson.dumps({
        #     'status': 101,
        #     #'replace_ans': current_record['answers']
        #     'merge': {
        #         'primary': True,
        #         'replace': True,
        #         'answers': current_record['answers']
        #     },
        # }))
        

if __name__ == '__main__':
    lkf_obj = ComplementosDePago(settings, sys_argv=sys.argv)
    lkf_obj.console_run()
    lkf_api = lkf_obj.lkf_api
    current_record = lkf_obj.current_record
    record_id =  lkf_obj.record_id

    from pci_base_utils import PCI_Utils
    p_utils = PCI_Utils(cr=lkf_obj.cr, lkf_api=lkf_api, settings=settings, lkf_obj=lkf_obj)

    p_utils.set_status_proceso(current_record, record_id, 'procesando', msg='', field_status='62793beeee0f419f7b6bfbaf', field_msg='62793beeee0f419f7b6bfbb0')
    lkf_obj.procesa_complemento()