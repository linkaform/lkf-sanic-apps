# -*- coding: utf-8 -*-
"""
Script para validar el xml de la factura de contratistas
"""
import sys, simplejson, re

import warnings
from cryptography.utils import CryptographyDeprecationWarning

from datetime import datetime
from pytz import timezone

from produccion_pci_utils import Produccion_PCI
from account_settings import *
warnings.filterwarnings("ignore", category=CryptographyDeprecationWarning)

### Testing decoding, be carefull this could afect the rest of the system
# reload(sys)
# sys.setdefaultencoding('utf-8')


class ValidarFacturaContratista( Produccion_PCI ):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

    def monto_valido(self, monto, total, variacion):
        """
        Valida que el total de la factura sea igual o al menos dentro del margen de variacion
        con el monto de la Orden de Compra

        Args:
            monto (str | float): Monto del registro de Orden de Compra
            total (str | float): Total de la factura xml
            variacion (int): Margen que se permite si ambos montos no son iguales

        Return:
            bool si cumple con la validacion
        """
        if variacion == 1:
            return int(total) >= int(monto) - 1 and int(total) <= int(monto) + 1
        return float(total) >= float(monto) - variacion and float(total) <= float(monto) + variacion

    def get_value_key_xml(self, root, strValue):
        try:
            for at, val in root.attrib.items():
                if at.lower() == strValue.lower():
                    return val
        except:
            return ''

    def get_only_first_part(self, subcadena):
        array_encontrados = [ subcadena.find("DIVISION"), subcadena.find("AREA"), subcadena.find("COPE"), subcadena.find("FOLIO"), subcadena.find("SEMANA"), subcadena.find("PERIODO") ]
        try:
            posicion_encontrada = min([n for n in array_encontrados if n>0])
        except:
            posicion_encontrada = 0
        if posicion_encontrada>0:
            return subcadena[0:posicion_encontrada]
        else:
            return subcadena

    def search_value_in_description(self, descripcion, regexpSearch, group=1):
        try:
            return re.search(regexpSearch, descripcion).group(group)
        except AttributeError:
            return ''

    def extraer_metadatos_xml(self, root):
        """
        Procesa el contenido del xml para extraer la información que se requiere como campos y valor

        Args:
            root: Contenido del xml de la factura

        Return:
            Diccionario con los campos y valores obtenidos del xml de la factura
        """
        metaDataXml = {
            "LugarExpedicion": self.get_value_key_xml(root, "LugarExpedicion"),
            "FormaPago": self.get_value_key_xml(root, "FormaPago"),
            "Moneda": self.get_value_key_xml(root, "Moneda"),
            "CondicionesDePago": self.get_value_key_xml(root, "CondicionesDePago"),
            "Folio_xml": self.get_value_key_xml(root, "Folio"),
            "fecha": self.get_value_key_xml(root, "Fecha"),
            "rfc_emisor": '',
            "nombre_emisor": '',
            "RegimenFiscal_emisor": '',
            "uuid_xml": '',
            "FechaTimbrado": '',
            "Conceptos": []
        }

        for child in root:
            if "Emisor" in child.tag:
                metaDataXml["rfc_emisor"] = self.get_value_key_xml(child, "Rfc")
                metaDataXml["nombre_emisor"] = self.get_value_key_xml(child, "Nombre")
                metaDataXml["RegimenFiscal_emisor"] = self.get_value_key_xml(child, "RegimenFiscal")
            if "Complemento" in child.tag:
                for complementoChild in child:
                    if "TimbreFiscalDigital" in complementoChild.tag:
                        metaDataXml["uuid_xml"] = self.get_value_key_xml(complementoChild, "UUID")
                        metaDataXml["FechaTimbrado"] = self.get_value_key_xml(complementoChild, "FechaTimbrado")
            if "Conceptos" in child.tag:
                for ConceptosChild in child:
                    descripcion_obtenida = self.get_value_key_xml(ConceptosChild, "Descripcion")
                    descripcion = descripcion_obtenida.upper()
                    descripcion = descripcion.replace('DIVISIÓN','DIVISION')
                    descripcion = descripcion.replace('DIVISIóN','DIVISION')
                    descripcion = descripcion.replace('ÁREA','AREA')
                    descripcion = descripcion.replace('áREA','AREA')
                    metaDataXml["Conceptos"].append({
                        'ClaveProdServ': self.get_value_key_xml(ConceptosChild, "ClaveProdServ"),
                        'ClaveUnidad': self.get_value_key_xml(ConceptosChild, "ClaveUnidad"),
                        'Cantidad': self.get_value_key_xml(ConceptosChild, "Cantidad"),
                        'ValorUnitario': self.get_value_key_xml(ConceptosChild, "ValorUnitario"),
                        'Importe': self.get_value_key_xml(ConceptosChild, "Importe"),
                        'TipoInstalacion': self.get_only_first_part(descripcion),
                        'Division': self.search_value_in_description(descripcion, 'DIVISION:?\s*(\w+)'),
                        'Area': self.get_only_first_part( self.search_value_in_description(descripcion, 'AREA:?(.+)') ),
                        'Cope': self.get_only_first_part( self.search_value_in_description(descripcion, 'COPE:?(.+)') ),
                        'Folio': self.search_value_in_description(descripcion, 'FOLIO:?\s*([A-Z0-9]+-\d+(\/\d+)?)'),
                        'Semana': self.search_value_in_description(descripcion, '[SEMANA|SEMANAS|PERIODO]:?\s+((DEL\s+)?\d+\s+(AL|DE)\s+(\d+|\w+)\s+(AL\s+\d+\s+DE\s+\w+\s+(DE|DEL)\s+\d+|DE\s+\w+\s+DEL\s+\d+)?)|SEM\s+\d+')
                    })
        return metaDataXml

    def verifica_monto_xml(self, file_url, monto, validate_by_subtotal=False, variacion=1):
        """
        Se valida que el monto de la Orden de Compra corresponda al total de la factura xml
        Además, se lee xml y se obtienen los atributos y valores que se requieren para el proceso

        Args:
            file_url (str): URL del xml de la factura
            monto (float): Monto del registro de Orden de Compra
            validate_by_subtotal (bool): True si la validacion se hará con el subtotal de la factura, de lo contrario se valida con el Total
            variacion (int | float): Cantidad de variacion permitida entre montos a validar

        Return:
            El total del xml, atributos del xml, bool de la factura valida, atributos adicionales y contenido completo del xml
        """
        metaDataXml = {}
        extra_params_to_eval = {}
        dict_xml_complete = {}
        
        if variacion == 1:
            monto = str(monto).replace(',', '').split('.')[0]
        
        try:
            xml, root = self.get_xml_root(file_url, get_all_root=True)
            dict_xml_complete = self.integration_get_dict_node(root)
            
            extra_params_to_eval['formadepago'] = xml.get('formapago') or xml.get('formadepago', '')
            extra_params_to_eval['metododepago'] = xml.get('metodopago') or xml.get('metododepago', '')
            
            for child in root:
                if "Receptor" in child.tag:
                    extra_params_to_eval.update({
                        a.lower():b for a,b  in child.attrib.items()
                    })
            print('===== extra_params_to_eval=',extra_params_to_eval)
            
            total = float(xml.get('subtotal' if validate_by_subtotal else 'total', 0.0))
            if variacion == 1:
                total = str(total).replace(',', '').split('.')[0]
            
            print("******* total",total)
            print("******* monto",monto)
            
            if self.monto_valido(monto, total, variacion):
                metaDataXml = self.extraer_metadatos_xml(root)
                return 0, metaDataXml, True, extra_params_to_eval, dict_xml_complete
            
            return float(total), metaDataXml, False, extra_params_to_eval, dict_xml_complete
        
        except Exception as e:
            print("---------- error:", e)
            return -1, metaDataXml, False, extra_params_to_eval, dict_xml_complete

    def get_id_form_os(self, form_id_oc):
        """
        Se obtiene el id de la forma de Orden de Servicio segun la Orden de Compra

        Args:
            form_id_oc (int): Id de la forma de Orden de Compra

        Return:
            ID de la forma de orden de servicio
        """
        map_ids_os_by_oc = {
            self.FORMA_ORDEN_COMPRA_COBRE: self.ORDEN_SERVICIO_COBRE, 
            self.FORMA_ORDEN_COMPRA_COBRE_SURESTE: self.ORDEN_SERVICIO_COBRE_SURESTE, 
            self.FORMA_ORDEN_COMPRA_COBRE_NORTE: self.ORDEN_SERVICIO_COBRE_NORTE, 
            self.FORMA_ORDEN_COMPRA_COBRE_OCCIDENTE: self.ORDEN_SERVICIO_COBRE_OCCIDENTE,
            self.FORMA_ORDEN_COMPRA_FIBRA: self.ORDEN_SERVICIO_FIBRA, 
            self.FORMA_ORDEN_COMPRA_FIBRA_SURESTE: self.ORDEN_SERVICIO_FIBRA_SURESTE, 
            self.FORMA_ORDEN_COMPRA_FIBRA_NORTE: self.ORDEN_SERVICIO_FIBRA_NORTE, 
            self.FORMA_ORDEN_COMPRA_FIBRA_OCCIDENTE: self.ORDEN_SERVICIO_FIBRA_OCCIDENTE
        }
        return map_ids_os_by_oc.get(form_id_oc, False)

    def get_razon_social_factura_contratista( self, id_conexion ):
        mango_query = { 
            "selector": { 
                "answers": { 
                    '$and':[ { "5f344a0476c82e1bebc991d6": { "$eq": str( id_conexion ) } } ]
                }
            }
        }
        dict_rs = {}
        row_catalog = lkf_api.search_catalog(self.CATALOGO_CONTRATISTAS_ID, mango_query)
        if row_catalog:
            for r in row_catalog:
                fecha_facturacion = r.get('621d3062e20a70a963559a11') or '2021-11-01'
                dict_rs.update({
                    'fibra': r.get('618057ba8f81fd9179bcd329', ''),
                    'cobre': r.get('6180593cb518bbdc7cde8d8d', ''),
                    'fecha_validar_facturacion': fecha_facturacion,
                    'name_socio': r.get('614e4cd2c1770ff99f38ac33', ''),
                    'permiso_facturar': r.get('619e7a46c79af2f6eaf888c5', '')
                })
        return dict_rs

    def get_monto_complemento_pendiente( self, id_contratista ):
        """
        Consulta en la forma Pagos SAP con la lista de complementos que se encontró para saber si hay algún pago pendiente

        Args:
            id_contratista (int): ID de la conexion

        Return:
            Importe pendiente de Pagos SAP
        """
        contratista_complemento = self.get_contratista_complemento( id_contratista )

        if not contratista_complemento:
            return None
        
        record_pagos_sap = self.get_records(
            self.FORMA_PAGOS_SAP, 
            query_answers={
                'answers.62d06e922fd9244967a3c167': {'$in': contratista_complemento },
                'answers.62d06e922fd9244967a3c16b': 'pendientes'
            }, 
            select_columns=['folio', 'answers.62d06e922fd9244967a3c16a']
        )
        
        for pago_sap in record_pagos_sap:
            return pago_sap['answers'].get('62d06e922fd9244967a3c16a')

    def get_info_cope_os(self, os_form_id, fols_os, tels_os):
        """
        Se consulta informacion de las Ordenes de Servicio que componen la Orden de Compra

        Args:
            os_form_id (int): ID de la forma de Orden de Servicio
            fols_os (list): Lista de folios de Orden de Servicio
            tels_os (list): Lista de telefonos

        Return:
            Registros de Orden de servicio encontrados
        """
        records = self.get_records(
            os_form_id, folio=fols_os,
            query_answers={ 'answers.f1054000a010000000000005': {'$in': tels_os} },
            select_columns=[
                'folio', 
                'answers.f1054000a0100000000000b2', 
                'answers.f1054000a0100000000000a2', 
                'answers.f1054000a010000000000002', 
                'answers.5a1eecfbb43fdd65914505a1', 
                'answers.f1054000a02000000000fa02'
            ]
        )

        return records

    def get_fols_to_razon_social(self, info_os, field_fecha_liquidacion, fecha_validar_facturacion='2021-11-01'):
        fecha_to_evaluate = datetime.strptime(fecha_validar_facturacion, '%Y-%m-%d')
        list_fols_mayor_1_nov = []
        list_fols_menor_1_nov = []
        for ors in info_os:
            fecha_liquidada = ors.get('answers',{}).get(field_fecha_liquidacion,'')
            date_fecha_liquidada = datetime.strptime(fecha_liquidada, '%Y-%m-%d')
            if date_fecha_liquidada >= fecha_to_evaluate:
                list_fols_mayor_1_nov.append( ors.get('folio') )
            else:
                list_fols_menor_1_nov.append( ors.get('folio') )
        return list_fols_mayor_1_nov, list_fols_menor_1_nov
    
    def get_configuraciones_validaciones(self):
        """
        Se consulta registros de la forma Configuración de Validaciones con los filtros:
        Activo = Si y Validacion General = No

        Return:
            Registros de la forma configuracion de validaciones
        """
        return self.get_record_from_db(
            self.FORMA_CONFIGS_VALIDACIONES, 
            query_answers={
                'answers.631f4f0248743cdd01fe4b6c': 'sí',
                'answers.6491f61eb2e38c03b8398a18': 'no'
            },
            select_columns=['folio', 'answers']
        )

    def get_val_in_dict(self, name_to_search, dict_to_eval):
        for i in dict_to_eval:
            if i == name_to_search:
                return dict_to_eval[i]
        return None

    def search_value_in_all_dict( self, name_to_search, dict_complete ):
        # Busco en el primer nivel
        val_found = self.get_val_in_dict( name_to_search, dict_complete )
        if val_found:
            return val_found
        
        # Si no encontro nada en primer nivel recorro el diccionario hasta encontrar el valor
        for i in dict_complete:
            sub_item = dict_complete[i]
            if type(sub_item) == dict:
                val_found = self.search_value_in_all_dict(name_to_search, sub_item)
                if val_found:
                    return val_found
            elif type(sub_item) == list:
                for ii in sub_item:
                    val_found = self.search_value_in_all_dict(name_to_search, ii)
                    if val_found:
                        return val_found

    def eval_extra_params_factura(self, extra_params_to_eval, current_record, is_tecnologia_fibra, dict_rs_contratista, have_fols_mayores_1_nov, list_all_ids_forms, dict_xml_complete):
        # Se consulta el registro de la forma Configuracion de Validaciones
        configuracion_validaciones = self.get_configuraciones_validaciones()
        dict_txts_razon_social = {}

        if not configuracion_validaciones:
            return []

        def get_list_forms_aplica( str_list_forms ):
            return [ 
                int( form_aplica.split('_')[-1].strip().replace('(', '').replace(')', '') ) 
                for form_aplica in str_list_forms 
            ]

        # Se procesa el grupo repetitivo Razon Social
        for razones in configuracion_validaciones.get('answers', {}).get('6318d13144b1e9292d39b8b5', []):
            razon_principal = p_utils.quit_acentos( razones.get('6318d157e7dc26b52f2c4293', '').lower().replace(' ', '_') )
            dict_txts_razon_social[ razon_principal ] = {
                'vals_accepted': [ variante.strip().lower().replace(' ','').replace(',','').replace('.','') for variante in razones.get('6318d2136217e6d71339b8c1', '').split('/') ],
                'rfc_accepted': [ rfcs.strip() for rfcs in razones.get('6318d2136217e6d71339b8c2', '').split('/') ],
                'aplica_en': get_list_forms_aplica( razones.get('6318d2136217e6d71339b8c3', []) )
            }
        print('dict_txts_razon_social=',simplejson.dumps( dict_txts_razon_social, indent=4 ))
        
        # Se procesa el grupo repetitivo Validaciones Adicionales desde XML
        dict_adicionales_xml = []
        for adicional_xml in configuracion_validaciones.get('answers', {}).get('6318d2dc0d37da73390c3d1d', []):
            name_tag_xml = adicional_xml.get('6318d363a76a4d7dd439b87b', '').lower().strip()
            dict_adicionales_xml.append( {
                'name_tag': name_tag_xml,
                'vals_accepted': [ vals_aceptados.strip().lower() for vals_aceptados in adicional_xml.get('6318d363a76a4d7dd439b87c', '').split('/') ],
                'aplica_en': get_list_forms_aplica( adicional_xml.get('6318d363a76a4d7dd439b87d', []) )
            } )
        print ('dict_adicionales_xml=',simplejson.dumps( dict_adicionales_xml, indent=4 ))
        
        
        # Si se tiene información del contratista en el catalogo de contratistas 1.0 entra a revisión
        rfc_accepted, accepted_razon_social, errors_params = [], [], []
        current_form_id = current_record['form_id']
        if current_form_id in list_all_ids_forms:
            if dict_rs_contratista:
                tecnologia_to_rs = 'fibra' if is_tecnologia_fibra else 'cobre'
                
                razon_social_to_eval = dict_rs_contratista.get( tecnologia_to_rs ) or 'ingenieria_avanzada_en_redes' if tecnologia_to_rs == 'fibra' else 'ingenieria_avanzada_en_construccion'
                razon_social_to_eval = razon_social_to_eval.lower().replace(' ', '_')
                print('Razon social factura = ',razon_social_to_eval)

                rs_aplica_en = dict_txts_razon_social.get(razon_social_to_eval, {}).get('aplica_en', [])

                if current_form_id not in rs_aplica_en:
                    rs_aplica_en.append( current_form_id )

                if not dict_rs_contratista.get(tecnologia_to_rs):
                    have_fols_mayores_1_nov = True
                
                print('rs_aplica_en=',rs_aplica_en)
                print('-- razon_social_to_eval=',razon_social_to_eval)
                print('-- current_record form_id=',current_form_id)
                print('-- have_fols_mayores_1_nov=',have_fols_mayores_1_nov)
                if have_fols_mayores_1_nov:
                    accepted_razon_social = dict_txts_razon_social.get(razon_social_to_eval, {}).get('vals_accepted', [])
                    accepted_razon_social.append( razon_social_to_eval.replace('_', '') )
                    rfc_accepted = dict_txts_razon_social.get(razon_social_to_eval, {}).get('rfc_accepted', '')
                elif not is_tecnologia_fibra:
                    return []
            elif not is_tecnologia_fibra:
                # Si no tiene info en el catálogo y NO es una de las formas de Orden de Compra Fibra se deja pasar
                return []
        else:
            for razon_social, info_razon in dict_txts_razon_social.items():
                if current_form_id in info_razon.get('aplica_en'):
                    accepted_razon_social.extend( info_razon.get('vals_accepted', []) )
                    rfc_accepted.extend( info_razon.get('rfc_accepted') )

        print('accepted_razon_social=',accepted_razon_social)
        print('rfc_accepted=',rfc_accepted)
        
        if extra_params_to_eval.get('nombre', '').lower().replace(' ','').replace('.','').replace(',','').replace('\\n','').replace('\n','').replace('\\t','').replace('\t','') not in accepted_razon_social:
            errors_params.append( 'Razón Social NO válida: {}'.format(extra_params_to_eval.get('nombre')) )
        
        if extra_params_to_eval.get('rfc', '') not in rfc_accepted:
            errors_params.append( 'RFC NO válido: {}'.format(extra_params_to_eval.get('rfc')) )

        for dict_in_xml in dict_adicionales_xml:
            if current_form_id not in dict_in_xml.get('aplica_en', []):
                continue
            
            name_in_xml = dict_in_xml['name_tag']
            val = ''
            list_variantes = name_in_xml.split('/')
            for nn in list_variantes:
                nn = nn.lower().strip()
                val = self.search_value_in_all_dict(nn, dict_xml_complete)
                if val:
                    break
            
            if not val:
                errors_params.append( '{} NO se encontró valor'.format(list_variantes[0]) )
                continue

            accepted_xml = dict_in_xml.get('vals_accepted', [])
            if val.lower().replace(' ', '') not in accepted_xml:
                errors_params.append( '{} NO válido: {}'.format(list_variantes[0], val) )
        
        print('errors_params=',errors_params)
        
        return errors_params


    def get_str_list(self, list_to_proccess):
        str_return = ''
        str_return += ', '.join([a.upper().replace('_', ' ') for a in list_to_proccess if a])
        return str_return


    def validar_factura(self):
        """
        Validación de factura xml en la Orden de Compra
        """
        # Se valida que esté correctamente cargado el XML de la factura 
        file_xml = answers.get('f19620000000000000000fc2', {})
        if not file_xml:
            self.notify_error("f19620000000000000000fc2", "XML Factura CONTRATISTA", "No se encontró la factura XML")
        
        file_url = file_xml[0]['file_url'] if type(file_xml) == list else file_xml['file_url']

        if file_url.split('.')[-1].lower() != 'xml':
            self.notify_error("f19620000000000000000fc2", "XML Factura CONTRATISTA", "La factura debe ser un XML")
        
        monto = answers.get('f19620000000000000000fc7', '0')
        validacion_monto_xml, metaDataXml, facturaValida, extra_params_to_eval, dict_xml_complete = self.verifica_monto_xml(file_url, monto, validate_by_subtotal=False, variacion=1)
        
        list_ids_forms_ftth = [self.FORMA_ORDEN_COMPRA_FIBRA, self.FORMA_ORDEN_COMPRA_FIBRA_SURESTE, self.FORMA_ORDEN_COMPRA_FIBRA_NORTE, self.FORMA_ORDEN_COMPRA_FIBRA_OCCIDENTE]
        list_ids_forms_cobre = [self.FORMA_ORDEN_COMPRA_COBRE, self.FORMA_ORDEN_COMPRA_COBRE_SURESTE, self.FORMA_ORDEN_COMPRA_COBRE_NORTE, self.FORMA_ORDEN_COMPRA_COBRE_OCCIDENTE]
        
        os_form_id = self.get_id_form_os(current_record['form_id'])
        
        if not os_form_id:
            self.notify_error("folio", "Folio", "No se pudo obtener el id de la forma de Orden de Servicio. Favor de contactar a soporte")
        
        list_all_ids_forms = list_ids_forms_ftth + list_ids_forms_cobre

        connection_id = current_record.get( 'connection_id', current_record['user_id'] )

        info_os = None
        dict_rs_contratista = self.get_razon_social_factura_contratista( connection_id )
        print('dict_rs_contratista=',dict_rs_contratista)
        
        
        # Se revisa si el contratista tiene algun pago pendiente a SAP
        if dict_rs_contratista.get('permiso_facturar', '').lower() == 'no':
            monto_complemento_pendiente = self.get_monto_complemento_pendiente( connection_id )
            
            if monto_complemento_pendiente:
                self.notify_error("folio", "Folio", f'Se tiene un complemento pendiente por {monto_complemento_pendiente}')
        
        fols_os, tels_os = [], []
        for o in answers.get('f1962000000000000000fc10', []):
            fols_os.append( o['f19620000000000000001fc1'] )
            tels_os.append( int(o['f19620000000000000001fc2']) )
        
        print('------------->FOLS OS:',fols_os)
        
        info_os = self.get_info_cope_os(os_form_id, fols_os, tels_os)

        have_fols_mayores_1_nov = False
        
        is_tecnologia_fibra = current_record['form_id'] in list_ids_forms_ftth
        tecnologia_to_rs = 'fibra' if is_tecnologia_fibra else 'cobre'
        
        if dict_rs_contratista.get( tecnologia_to_rs ):
            # Reviso si existen folios con fecha de liquidacion menor al 01/nov
            field_fecha_liquidacion = 'f1054000a02000000000fa02' if is_tecnologia_fibra else '5a1eecfbb43fdd65914505a1'
            
            # Si vienen mezclados folios mayores y folios menores al 1/nov se manda error
            list_fols_mayor_1_nov, list_fols_menor_1_nov = self.get_fols_to_razon_social(info_os, field_fecha_liquidacion, fecha_validar_facturacion=dict_rs_contratista['fecha_validar_facturacion'])
            
            if list_fols_menor_1_nov:
                self.notify_error("folio", "Folio", f'Se encontraron folios con fecha de Liquidacion menor a 01/Nov/2021 {self.list_to_str( list_fols_menor_1_nov )}')
            
            have_fols_mayores_1_nov = True if list_fols_mayor_1_nov else False
        
        errors_params = self.eval_extra_params_factura(extra_params_to_eval, current_record, is_tecnologia_fibra, dict_rs_contratista, have_fols_mayores_1_nov, list_all_ids_forms, dict_xml_complete)
        if errors_params:
            self.notify_error("folio", "Folio", self.list_to_str(errors_params))
        
        if facturaValida:
            answers['f19620000000000000000fc5'] = 'factura_valida'
            answers['f19620000000000000000fc6'] = ''
            answers['5cf59bc653ceb8e0bccea84a'] = p_utils.get_date_now()
            
            months = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

            print('------------->ID OS:',os_form_id)
            
            # Se obtiene la lista de Areas, Divisiones y Copes
            list_areas, list_divisiones, list_copes = [], [], []
            if info_os:
                for i in info_os:
                    area = i.get('answers',{}).get('f1054000a0100000000000a2','')
                    division = i.get('answers',{}).get('f1054000a0100000000000b2','')
                    cope = i.get('answers',{}).get('f1054000a010000000000002','')
                    if not area in list_areas:
                        list_areas.append(area)
                    if not division in list_divisiones:
                        list_divisiones.append(division)
                    if not cope in list_copes:
                        list_copes.append(cope)
            
            str_list_areas = self.get_str_list(list_areas)
            str_list_divisiones = self.get_str_list(list_divisiones)
            str_list_copes = self.get_str_list(list_copes)
            print('str_list_areas: ',str_list_areas)
            print('str_list_divisiones: ',str_list_divisiones)
            print('str_list_copes: ',str_list_copes)

            # ----- Agrego la información Datos SAP --------------
            answers['5d07df4c2409837c09c2a023'] = metaDataXml["LugarExpedicion"]
            answers['5d07df4c2409837c09c2a024'] = metaDataXml["FormaPago"]
            answers['5d07df4c2409837c09c2a026'] = metaDataXml["Moneda"]
            answers['5d07df4c2409837c09c2a028'] = metaDataXml["CondicionesDePago"]
            answers['5d07df4c2409837c09c2a029'] = metaDataXml["Folio_xml"]
            if metaDataXml["fecha"]:
                answers['5d07e30b4716f21474873168'] = metaDataXml["fecha"].split('T')[0]
            answers['5d07df4c2409837c09c2a02b'] = metaDataXml["rfc_emisor"]
            answers['5d07df4c2409837c09c2a02c'] = metaDataXml["nombre_emisor"]
            answers['5d07df4c2409837c09c2a02d'] = metaDataXml["RegimenFiscal_emisor"]
            answers['5d07e0956906388a4dc2a039'] = metaDataXml["uuid_xml"]
            if metaDataXml["FechaTimbrado"]:
                answers['5d07e0956906388a4dc2a03a'] = metaDataXml["FechaTimbrado"].split('T')[0]
            if metaDataXml["Conceptos"]:
                ar_conceptos = []
                for concepto in metaDataXml["Conceptos"]:
                    semana = concepto['Semana']
                    print('*********************** Semana:',semana)
                    if not semana and metaDataXml["fecha"]:
                        only_date = metaDataXml["fecha"].split('T')[0]
                        a = datetime.strptime(only_date, "%Y-%m-%d")
                        w = a.isocalendar()[1]
                        semana = "Semana {} {} {}".format(w, months[a.month - 1], a.year)
                    dict_conceptos = {
                        '5d07e0580c4233fad7c29fcd': concepto['ClaveProdServ'],
                        '5d07e0580c4233fad7c29fce': concepto['ClaveUnidad'],
                        '5d07e0580c4233fad7c29fd0': concepto['TipoInstalacion'],
                        #'5d07e0580c4233fad7c29fd2': concepto['Division'],
                        '5d07e0580c4233fad7c29fd2': str_list_divisiones,
                        #'5d07e0580c4233fad7c29fd3': concepto['Area'],
                        '5d07e0580c4233fad7c29fd3': str_list_areas,
                        #'5d07e0580c4233fad7c29fd4': concepto['Cope'],
                        '5d07e0580c4233fad7c29fd4': str_list_copes,
                        '5d07e0580c4233fad7c29fd5': concepto['Folio'],
                        '5d07e0580c4233fad7c29fd6': semana
                        }
                    if concepto['Importe']:
                        dict_conceptos['5d07e0580c4233fad7c29fd8'] = float(concepto['Importe'])
                    if concepto['Cantidad']:
                        dict_conceptos['5d07e0580c4233fad7c29fcf'] = int(float(concepto['Cantidad']))
                    if concepto['ValorUnitario']:
                        dict_conceptos['5d07e0580c4233fad7c29fd7'] = float(concepto['ValorUnitario'])
                    ar_conceptos.append(dict_conceptos)
                answers['5d07df4c2409837c09c2a02e'] = ar_conceptos
            # ----------------------------------------------------
            answers['618bf9dbf2cb8a088c418bc4'] = extra_params_to_eval.get('nombre', '')
            answers['618bf9dbf2cb8a088c418bc5'] = extra_params_to_eval.get('rfc', '')
            current_record.update({'answers': answers})
        else:
            #answers['f19620000000000000000fc5'] = 'error_de_factura'
            if validacion_monto_xml == -1:
                msg_errors = 'EL formato de factura no ha sido identificado, favor de contactar a PCI para revisar el formato de tu XML.'
            else:
                msg_errors = f'El monto de la factura es de $ {validacion_monto_xml} cuando el de la orden de compra es de $ {monto} . Favor de revisar.'
                if errors_params:
                    msg_errors += self.list_to_str(errors_params)
            self.notify_error('f19620000000000000000fc2', 'XML Factura CONTRATISTA', msg_errors)

        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans': answers
        }))

if __name__ == '__main__':
    lkf_obj = ValidarFacturaContratista(settings, sys_argv=sys.argv, use_api=True)
    print(f"--- --- --- Validacion de factura del registro {lkf_obj.folio} --- --- ---")

    lkf_obj.console_run()
    current_record = lkf_obj.current_record
    lkf_api = lkf_obj.lkf_api
    answers = current_record['answers']

    from pci_base_utils import PCI_Utils
    p_utils = PCI_Utils()

    lkf_obj.validar_factura()