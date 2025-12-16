# -*- coding: utf-8 -*-
"""
Script para la carga de Complementos de Pago
"""
import sys, simplejson, re
from datetime import datetime
from produccion_pci_utils import Produccion_PCI

from account_settings import *

class CargaComplementosPago( Produccion_PCI ):
    """docstring for CargaComplementosPago"""
    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        
        self.dict_cols_names = {
            'cuenta': { 'list_accepted': ['cuenta_por_defecto'], 'required': True },
            'fecha': { 'list_accepted': ['fecha_de_transferencia'], 'required': True },
            'hora': { 'list_accepted': [], 'required': True },
            'sucursal': { 'list_accepted': [], 'required': True },
            'descripcion': { 'list_accepted': [], 'required': True },
            'cargo/abono': { 'list_accepted': [], 'required': True },
            'importe': { 'list_accepted': ['importe_de_transferencia'], 'required': True },
            'referencia': { 'list_accepted': [], 'required': True },
            'concepto': { 'list_accepted': ['nombre_sn'], 'required': True },
            'tecnologia': { 'list_accepted': [], 'required': True },
            'numeros_de_facturas': { 'list_accepted': [], 'required': True },
        }

    def detectar_tipo_excel(self, header):
        """Detecta si el archivo es tipo 'fibra' o 'cobre'."""
        headers_fibra = ['factura', 'm._de_pago', 'razon_social', 'monto_de_factura', 'fecha_de_pago']
        return 'fibra' if header == headers_fibra else 'cobre'

    def procesar_cobre(self, records, errores):
        """Procesa los registros tipo COBRE."""
        for record in records:
            if not record[-2]:
                errores.append(record + ['Se requiere el numero de factura'])
                continue
            record[-2] = f"{record[-2]}:{record[-1]}"
            record[-1] = 'COBRE'
        
        return ['#', 'descripcion', 'cuenta', 'referencia', 'importe', 'concepto','fecha_de_transferencia', 'numeros_de_facturas', 'tecnologia',
            'hora', 'cargo/abono', 'sucursal']

    def procesar_fibra(self, records):
        """Procesa los registros tipo FIBRA."""
        for record in records:
            # Insertando campos vacíos antes de los últimos elementos
            record.insert(-1, 'FTTH')     # tecnologia
            record.insert(-1, '')         # fecha_de_transferencia
            record.insert(-1, '')         # concepto
            record.insert(-1, '')         # cuenta
            record.extend(['', '', ''])   # hora, cargo/abono, sucursal

        return ['numeros_de_facturas', 'descripcion', 'concepto', 'importe', 'tecnologia', 'hora', 'cargo/abono', 'sucursal',
            'fecha_de_transferencia', 'cuenta', 'referencia', '#']

    def eval_header_names(self, header_sin_acentos):
        # Reemplazo en la cabecera el nombre de la columna según el valor aceptado
        header_sin_acentos = self.replace_name_col( self.dict_cols_names, header_sin_acentos )

        required_cols = [ i for i in self.dict_cols_names if self.dict_cols_names[i]['required'] ]
        required_not_found = list( set(required_cols) - set(header_sin_acentos) )
        return required_not_found, self.dict_cols_names

    def replace_name_col(self, column_map, headers):
        """
        Reemplaza nombres alternativos de columnas en `headers` usando `column_map`.

        Args:
            column_map (dict): Diccionario con claves como nombres estándar
                y valores como {'list_accepted': [alternativos]}.
            headers (list): Lista de nombres de columnas a revisar.

        Returns:
            list: Lista de nombres de columnas con reemplazos aplicados.
        """
        for standard_name, config in column_map.items():
            if standard_name not in headers:
                accepted_aliases = config.get('list_accepted', [])
                for alias in accepted_aliases:
                    try:
                        idx = headers.index(alias)
                        headers[idx] = standard_name
                        break  # Solo reemplazamos una vez
                    except ValueError:
                        continue
        return headers

    def eval_fecha( self, fecha_xls ):
        if isinstance(fecha_xls, str):
            fecha_xls = fecha_xls.replace("'", '')
            print('fecha_xls=',fecha_xls)
            try:
                # Asume formato 'DDMMYYYY'
                d = datetime.strptime( '{}-{}-{}'.format(fecha_xls[:2], fecha_xls[2:4], fecha_xls[4:]), '%d-%m-%Y' )
            except:
                return False
            return datetime.strftime( d, '%Y-%m-%d' )
        return datetime.strftime( fecha_xls, '%Y-%m-%d' )

    def rmv_other_caracteres( self, val ):
        to_remove = ['&', '#', ';']
        for r in to_remove:
            val = val.replace(r, '')
        return val

    def concepto_formated( self, c ):
        c = c.lower()
        try:
            x_found = re.search(r"x\d+", c).group(0)
        except:
            x_found = ''
        if x_found:
            c = c.replace(x_found, '')
        c = self.rmv_other_caracteres(c)
        return c.strip().upper()

    def get_contratistas_para_complementos( self, concepto ):
        """
        Se consulta en la forma Contratistas para Complementos de Pago
        filtrando el concepto en el campo Contratista Formato de Complemento
        """
        records_contratistas_para_complementos = self.get_records(
            self.FORMA_COMPLEMENTOS_PAGO, 
            query_answers={'answers.62d071930a1b1ff9eaa3c0f4': concepto},
            select_columns=['folio', 'answers', 'form_id', '_id']
        )
        return [rc for rc in records_contratistas_para_complementos]

    def get_emails_to_group( self, record_contratista ):
        """
        Se procesan los registros de Contratistas para Complementos
        se obtiene la lista de emails de los campos en grupos repetitivos
        """
        emails_to_group = set()
        for rec_contratista in record_contratista:
            # Se procesa el grupo repetitivo Contratistas y se obtienen los emails del campo de catalogo de contratistas 1.0
            for set_contratista in rec_contratista.get('answers', {}).get('62d071173eeb3a67815c74fe', []):
                listEmail = set_contratista.get(self.CATALOGO_CONTRATISTAS_OBJ_ID, {}).get('5f344a0476c82e1bebc991d8', [])
                if listEmail:
                    emails_to_group.add(listEmail[0])
            
            # Se procesa el grupo repetitivo Correos- Email y se obtienen del campo Email
            for set_emails in rec_contratista.get('answers', {}).get('630fe7754f9b7d85aa28a4fa', []):
                emails_to_group.add(set_emails.get('630fe786917101cc1828a52b', ''))
        return emails_to_group

    def review_exists( self, concepto, monto, tecnologia, fecha_formated, num_facturas ):
        record_pagos_sap = lkf_obj.cr.find_one({
            'form_id': self.FORMA_PAGOS_SAP,
            'deleted_at': {'$exists': False},
            'answers.62d06e922fd9244967a3c167': concepto,
            'answers.62d06e922fd9244967a3c16a': monto,
            'answers.62d0748e8cd47e93d17e5c9e': tecnologia,
            'answers.62d06e922fd9244967a3c168': fecha_formated,
            'answers.630f95d541d890298a787482': num_facturas
        }, {'folio': 1})
        return record_pagos_sap

    def update_contratistas_para_complementos( self, emails_to_group, record_contratista ):
        for rec_contratista in record_contratista:
            if rec_contratista['answers'].get('630fe7754f9b7d85aa28a4fa', []) != emails_to_group:
                rec_contratista['answers']['630fe7754f9b7d85aa28a4fa'] = emails_to_group
                res_update_contratista_para_complemento = lkf_api.patch_record( rec_contratista, jwt_settings_key='USER_JWT_KEY' )
                print('res update contratista para Complementos por emails=',res_update_contratista_para_complemento)
            else:
                print(f"{rec_contratista['folio']} ya tiene todos los usuarios, no es necesario actualizar")

    def carga_complementos(self):
        print('... ... Cargando complementos ... ...')
        current_record['answers'].pop('62d0d433ef9bfef1c2632a60', None)
        p_utils.set_status_proceso(current_record, record_id, 'procesando', field_status='62d0d433ef9bfef1c2632a5f', field_msg='62d0d433ef9bfef1c2632a61')

        # Se lee el archivo excel
        file_url = current_record['answers']['62d0d433ef9bfef1c2632a5e'][0].get('file_url')
        header, records = p_utils.read_file(file_url)

        if isinstance(header, dict) and header.get('error'):
            return p_utils.set_status_proceso( current_record, record_id, 'error', msg=header['error'], field_status='62d0d433ef9bfef1c2632a5f', field_msg='62d0d433ef9bfef1c2632a61' )

        header_sin_acentos = p_utils.header_without_acentos(header)

        # Se prepara la cabecera y registros que aplican segun la Tecnologia
        error_records = []
        tipo = self.detectar_tipo_excel(header_sin_acentos)
        header_sin_acentos = self.procesar_cobre(records, error_records) if tipo == 'cobre' else self.procesar_fibra(records)
        
        if error_records:
            error_file = p_utils.upload_error_file(header + ['Error',], error_records, current_record['form_id'], file_field_id='62d0d433ef9bfef1c2632a60')
            current_record['answers'].update(error_file)
            return p_utils.set_status_proceso(current_record, record_id, 'error', field_status='62d0d433ef9bfef1c2632a5f', field_msg='62d0d433ef9bfef1c2632a61')

        # Reviso que el documento tenga las columnas requeridas para el proceso, de lo contrario se manda error
        cols_not_found, dict_all_names = self.eval_header_names( header_sin_acentos )
        if cols_not_found:
            return p_utils.set_status_proceso( current_record, record_id, 'error', msg='No se encontraron las columnas: {}'.format( self.list_to_str( cols_not_found ) ), 
                field_status='62d0d433ef9bfef1c2632a5f', field_msg='62d0d433ef9bfef1c2632a61' )
        
        # Se obtiene un diccionario con el nombre de la columna y posición en el excel
        dict_header = self.make_header_dict(header_sin_acentos)

        # Obtenemos la posición de las columnas que vamos a ocupar para el proceso
        pos_cuenta = dict_header.get('cuenta')
        pos_fecha = dict_header.get('fecha')
        pos_hora = dict_header.get('hora')
        pos_sucursal = dict_header.get('sucursal')
        pos_descripcion = dict_header.get('descripcion')
        pos_cargo = dict_header.get('cargo/abono')
        pos_importe = dict_header.get('importe')
        pos_referencia = dict_header.get('referencia')
        pos_concepto = dict_header.get('concepto')
        pos_tecnologia = dict_header.get('tecnologia')
        pos_numeros_de_facturas = dict_header.get('numeros_de_facturas', None)

        # Se prepara los metadatos de la forma donde crearemos los registros para Pagos SAP
        metadata = lkf_api.get_metadata(self.FORMA_PAGOS_SAP)
        metadata['properties'] = self.get_metadata_properties('complementos_pagos_carga.py', 'CREAR REGISTRO DE PAGO', process="Carga Pagos a Complementos", folio_carga=self.folio)
        records_created = 0

        # Se procesan los registros
        for rec in records:
            metadata_copy = metadata.copy()

            # Se evalua que lleve una fecha correcta
            fecha_formated = self.eval_fecha( rec[pos_fecha] )
            if not fecha_formated:
                error_records.append( rec + [ 'Error al procesar la Fecha', ] )
                continue
            
            # Se define la tecnologia
            tecnologia = 'ftth' if rec[pos_tecnologia].lower() == 'fibra' else rec[pos_tecnologia].lower()
            tecnologia = tecnologia.strip().lower()
            
            # Se buscan los registros de la forma de contratistas para complementos de pago filtrando por el concepto
            concepto = self.concepto_formated(rec[pos_concepto])
            record_contratista = self.get_contratistas_para_complementos(concepto)
            if not record_contratista:
                error_records.append( rec + ['El contratista aún no tiene registro en la forma Contratistas para Complementos de Pago',] )
                continue

            # Se obtienen los emails de los registros encontrados
            list_emails_to_group = self.get_emails_to_group(record_contratista)
            emails_to_group = [ {'630fe786917101cc1828a52b': e} for e in list_emails_to_group ]
            print('emails_to_group=',emails_to_group)
            
            monto = p_utils.add_coma(rec[pos_importe])
            nums_de_facturas = rec[pos_numeros_de_facturas]
            
            # Se prepara answers para el registro a crear
            metadata_copy['answers'] = {
                '62d06e922fd9244967a3c167': concepto,
                '62d06e922fd9244967a3c168': fecha_formated,
                '62d06e922fd9244967a3c169': rec[pos_cuenta],
                '62d0748e8cd47e93d17e5c9e': tecnologia,
                '62d06e922fd9244967a3c16a': monto,
                '62d06e922fd9244967a3c16b': 'pendientes',
                '630fe7754f9b7d85aa28a4fa': emails_to_group
            }

            # Si hay numeros de factura se integran al answers
            if nums_de_facturas:
                metadata_copy['answers']['630f95d541d890298a787482'] = nums_de_facturas

            # Antes de crear el registro se debe revisar si ya existe para no duplicar
            exists_other_record = self.review_exists( concepto, monto, tecnologia, fecha_formated, nums_de_facturas )
            if exists_other_record:
                error_records.append( rec + [f"Ya existe un registro con los mismos datos, con el folio {exists_other_record['folio']}"] )
                continue

            # Se crea el registro en la forma Pagos SAP
            res_create = lkf_api.post_forms_answers(metadata_copy, jwt_settings_key='USER_JWT_KEY')
            print('res_create=',res_create)
            if res_create.get('status_code') != 201:
                error_records.append( rec + ['Error al crear el registro {}'.format(p_utils.arregla_msg_error_sistema(res_create)), ] )
                continue
            
            records_created += 1
            print('Actualizando emails en registros de contratistas para Complementos')
            self.update_contratistas_para_complementos( emails_to_group, record_contratista )

        records_error = len(error_records)
        msg_final = f'Cargados correctamente: {records_created} Errores: {records_error}'

        # current_record['answers']['62d0d433ef9bfef1c2632a61'] = f'Cargados correctamente: {records_created} Errores: {records_error}'
        # current_record['answers']['62d0d433ef9bfef1c2632a5f'] = 'carga_terminada'
        
        if error_records:
            error_file = p_utils.upload_error_file(header + ['Error',], error_records, self.form_id, file_field_id='62d0d433ef9bfef1c2632a60')
            current_record['answers'].update(error_file)
            # current_record['answers']['62d0d433ef9bfef1c2632a5f'] = 'error'
            return p_utils.set_status_proceso(current_record, record_id, 'error', msg=msg_final, field_status='62d0d433ef9bfef1c2632a5f', field_msg='62d0d433ef9bfef1c2632a61')
        
        # lkf_api.patch_record(current_record, record_id, jwt_settings_key='USER_JWT_KEY')
        return p_utils.set_status_proceso(current_record, record_id, 'carga_terminada', msg=msg_final, field_status='62d0d433ef9bfef1c2632a5f', field_msg='62d0d433ef9bfef1c2632a61')
        # set_status_proceso(self, current_record, record_id, status_set, msg='', field_status='5f10d2efbcfe0371cb2fbd39', field_msg='5fd05319cd189468810100c9' ):

if __name__ == '__main__':
    lkf_obj = CargaComplementosPago(settings, sys_argv=sys.argv)
    lkf_api = lkf_obj.lkf_api
    current_record = lkf_obj.current_record
    record_id =  lkf_obj.record_id

    from pci_base_utils import PCI_Utils
    p_utils = PCI_Utils(cr=lkf_obj.cr, lkf_api=lkf_api, settings=settings, lkf_obj=lkf_obj)
    
    lkf_obj.carga_complementos()