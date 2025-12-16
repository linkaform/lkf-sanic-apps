# -*- coding: utf-8 -*-

import sys, simplejson
from datetime import datetime, timedelta, date
from copy import deepcopy

import urllib.request
import xml.etree.ElementTree as ET

from lkf_addons.produccion_pci.app import Produccion_PCI


class Produccion_PCI(Produccion_PCI):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

        
        self.CATALOGO_CONTRATISTAS = self.lkm.catalog_id('catalogo_de_contratistas_10',{} )
        self.CATALOGO_CONTRATISTAS_ID = self.CATALOGO_CONTRATISTAS.get('id')
        self.CATALOGO_CONTRATISTAS_OBJ_ID = self.CATALOGO_CONTRATISTAS.get('obj_id')


        self.FORM_ID_CARGA_PROD = self.lkm.form_id('carga_de_produccin_diaria_por_contratistaiasa','id')
        self.FORM_ID_EXPEDIENTES_DE_TECNICOS = self.lkm.form_id('expedientes_de_tcnicosiasa','id')
        
        # self.ORDEN_SERVICIO_FIBRA = self.lkm.form_id('orden_de_servicio_metro_ftthiasa','id')
        # self.ORDEN_SERVICIO_COBRE = self.lkm.form_id('orden_de_servicio_metro_cobreiasa','id')
        # self.ORDEN_SERVICIO_FIBRA_OCCIDENTE = self.lkm.form_id('orden_de_servicio_occidente_ftthiasa','id')
        # self.ORDEN_SERVICIO_COBRE_OCCIDENTE = self.lkm.form_id('orden_de_servicio_occidente_cobreiasa','id')
        # self.ORDEN_SERVICIO_FIBRA_NORTE = self.lkm.form_id('orden_de_servicio_norte_ftthiasa','id')
        # self.ORDEN_SERVICIO_COBRE_NORTE = self.lkm.form_id('orden_de_servicio_norte_cobreiasa','id')
        # self.ORDEN_SERVICIO_FIBRA_SURESTE = self.lkm.form_id('orden_de_servicio_sur_ftthiasa','id')
        # self.ORDEN_SERVICIO_COBRE_SURESTE = self.lkm.form_id('orden_de_servicio_sur_cobreiasa','id')

        # # Aqui los ids de las formas de liberacion
        # self.FORMA_LIBERACION_FIBRA = self.lkm.form_id('liberacin_de_pagos_socio', 'id')
        # self.FORMA_LIBERACION_FIBRA_SURESTE = self.lkm.form_id('liberacin_de_pagos_sur_socio', 'id')
        # self.FORMA_LIBERACION_FIBRA_NORTE = self.lkm.form_id('liberacin_de_pagos_norte_socio', 'id')
        # self.FORMA_LIBERACION_FIBRA_OCCIDENTE = self.lkm.form_id('liberacin_de_pagos_occidente_socio', 'id')
        # self.FORMA_LIBERACION_COBRE = self.lkm.form_id('liberacin_de_pagos_cobre_socio', 'id')
        # self.FORMA_LIBERACION_COBRE_SURESTE = self.lkm.form_id('liberacin_de_pagos_sur_cobre_socio', 'id')
        # self.FORMA_LIBERACION_COBRE_NORTE = self.lkm.form_id('liberacin_de_pagos_norte_cobre_socio', 'id')
        # self.FORMA_LIBERACION_COBRE_OCCIDENTE = self.lkm.form_id('liberacin_de_pagos_occidente_cobre_socio', 'id')

        # # Aqui los ids de las formas de orden de compra
        # self.FORMA_ORDEN_COMPRA_FIBRA = self.lkm.form_id('orden_compra_contratista_ftth_metro_socio', 'id')
        # self.FORMA_ORDEN_COMPRA_FIBRA_SURESTE = self.lkm.form_id('orden_compra_contratista_ftth_sur_socio', 'id')
        # self.FORMA_ORDEN_COMPRA_FIBRA_NORTE = self.lkm.form_id('orden_compra_contratista_ftth_norte_socio', 'id')
        # self.FORMA_ORDEN_COMPRA_FIBRA_OCCIDENTE = self.lkm.form_id('orden_compra_contratista_ftth_occidente_socio', 'id')
        # self.FORMA_ORDEN_COMPRA_COBRE = self.lkm.form_id('orden_compra_contratista_cobre_metro_socio', 'id')
        # self.FORMA_ORDEN_COMPRA_COBRE_SURESTE = self.lkm.form_id('orden_compra_contratista_cobre_sur_socio', 'id')
        # self.FORMA_ORDEN_COMPRA_COBRE_NORTE = self.lkm.form_id('orden_compra_contratista_cobre_norte_socio', 'id')
        # self.FORMA_ORDEN_COMPRA_COBRE_OCCIDENTE = self.lkm.form_id('orden_compra_contratista_cobre_occidente_socio', 'id')
        self.FORM_ID_PRECIOS_FTTH = self.lkm.form_id('precios_fibra_socio', 'id')
        self.FORM_ID_PRECIOS_COBRE = self.lkm.form_id('precios_cobre_socio', 'id')

        self.FORMA_GENERAR_LIBERACIONES_Y_OCS = self.lkm.form_id('generar_liberaciones_fibra_y_cobre_socio', 'id')

        # Formas complemento para la validacion de facturas
        self.FORMA_COMPLEMENTOS_PAGO = self.lkm.form_id('contratistas_para_complementos_de_pago', 'id')
        self.FORMA_PAGOS_SAP = self.lkm.form_id('pagos_sap_complementos_de_pagos', 'id')
        self.FORMA_CONFIGS_VALIDACIONES = self.lkm.form_id('configuracin_de_validaciones', 'id')

        # Script que se ejecuta para pegar el folio de OC en las OS
        self.SCRIPT_ID_SET_FOLIO_OC = self.lkm.script_id('set_folio_oc_to_os', 'id')

        self.ID_CONTRATISTA_TIPO_MAQTEL = 17798
        self.id_tecnicos_directos = [2071, 2072, 2073]

        self.MONTO_MAXIMO_POR_OC = 200000 # Monto maximo por OCs en Cobre
        self.dias_para_marcar_desfase = 15 # Maximo de dias permitidos para carga antes de marcar como cobro minimo
        self.porcentaje_descuento_x_desfase = 0.05 # Porcentaje de descuento por folios marcados con desfase en carga

        # Equivalencias de las formas de orden de servicio en las cuentas de SC y en Admin
        self.dict_equivalences_forms_id = { 
            self.ORDEN_SERVICIO_FIBRA : 11044,
            self.ORDEN_SERVICIO_COBRE : 10540,
            self.ORDEN_SERVICIO_FIBRA_OCCIDENTE : 21953,
            self.ORDEN_SERVICIO_COBRE_OCCIDENTE : 25929,
            self.ORDEN_SERVICIO_FIBRA_NORTE : 21954,
            self.ORDEN_SERVICIO_COBRE_NORTE : 25928,
            self.ORDEN_SERVICIO_FIBRA_SURESTE : 16343,
            self.ORDEN_SERVICIO_COBRE_SURESTE : 25927
        }

        self.dict_ids_os_pdf = {
            self.ORDEN_SERVICIO_FIBRA: '5a8aefa7b43fdd100602f7be',
            self.ORDEN_SERVICIO_FIBRA_SURESTE: '5ad14051f851c220dd0eb772',
            self.ORDEN_SERVICIO_FIBRA_NORTE: '5ad14687f851c23d8a4d95c9',
            self.ORDEN_SERVICIO_FIBRA_OCCIDENTE: '5ad4b4a9b43fdd7af0f65899',
            self.ORDEN_SERVICIO_COBRE: '5ad13efef851c23d8a4d95af',
            self.ORDEN_SERVICIO_COBRE_SURESTE: '5ad13e8cf851c220dd0eb769',
            self.ORDEN_SERVICIO_COBRE_NORTE: '5ad13f49f851c2510b0d210a',
            self.ORDEN_SERVICIO_COBRE_OCCIDENTE: '5ad13f95f851c2467770da9e'
        }

        self.all_divisiones = [
            {'tecnologia':'fibra','division':'metro'}, {'tecnologia':'fibra','division':'sur'}, 
            {'tecnologia':'fibra','division':'norte'}, {'tecnologia':'fibra','division':'occidente'},
            {'tecnologia':'cobre','division':'metro'}, {'tecnologia':'cobre','division':'sur'}, 
            {'tecnologia':'cobre','division':'norte'}, {'tecnologia':'cobre','division':'occidente'}
        ]

        self.f.update({
            'xls_email_contratistas': '60105b997b3c64bb35043c3c',
            'field_id_cargado_desde_script': '5e17674c50f45bac939c932e',
            'field_no_serie_contratista': '68e4619b219b1bd06a01a272',
            'field_no_serie_tecnico': '68e5920a535224073205c2f3',
        })

    def get_contratista_complemento( self, id_contratista, get_full_records=False ):
        """
        Consulta en la forma Contratistas para Complementos de Pago filtrando por el id del contratista
        se obtiene el dato para Contratista formato de complemento

        Args:
            id_contratista (int): ID de la conexion

        Return:
            lista de formato de complemento segun los registros encontrados
        """
        record_contratistas_complemento = self.get_records(
            self.FORMA_COMPLEMENTOS_PAGO, 
            query_answers={ f'answers.62d071173eeb3a67815c74fe.{self.CATALOGO_CONTRATISTAS_OBJ_ID}.5f344a0476c82e1bebc991d6': [ str(id_contratista) ] },
            select_columns=['folio', 'answers']
        )

        if get_full_records:
            return record_contratistas_complemento

        contratista_complemento = []
        for r in record_contratistas_complemento:
            print('Contratista complemento',r['folio'])
            contratista_complemento.append(r['answers'].get('62d071930a1b1ff9eaa3c0f4', ''))
        return contratista_complemento

    def get_only_connections(self):
        """ Se lee excel de emails con las conexiones a las que se va a liberar y crear OC """
        
        # Se va a leer la lista de contratistas que el usuario requiera desde un excel
        if not self.answers.get( self.f['xls_email_contratistas'] ):
            return {}

        # Se leen los emails del excel
        file_url = self.answers[ self.f['xls_email_contratistas'] ]['file_url']
        header_contratistas, records_contratistas = self.read_file( file_url )

        # Se obtienen las conexiones de la cuenta padre
        all_connections = self.lkf_api.get_all_connections()

        dict_emails_connections = { infCon['email']: infCon['id'] for infCon in all_connections if infCon.get('email') and infCon.get('id') }
        dict_info_connection = { infCon['id']: infCon for infCon in all_connections if infCon.get('id') }

        emails_not_exists, emails_connections = [], []
        for email_contratista in records_contratistas:
            email_record = email_contratista[0]
            if not dict_emails_connections.get( email_record ):
                emails_not_exists.append( email_record )
                continue
            emails_connections.append( dict_emails_connections[ email_record ] )
        
        if emails_not_exists:
            return {'error': emails_not_exists}

        return {'result': emails_connections, 'info_connections': dict_info_connection}

    # def get_metadata_properties(self, name_script, accion, process='', folio_carga=''):
    #     dict_properties = {
    #         'device_properties': {
    #             'system': 'SCRIPT',
    #             'process': process,
    #             'accion': accion,
    #             'archive': name_script
    #         }
    #     }
    #     if folio_carga:
    #         dict_properties['device_properties']['folio carga'] = folio_carga
    #     return dict_properties

    def get_xml_root(self, file_url, get_all_root=False, xml_downloaded=False):
        """
        Obtiene la raíz de un archivo XML, ya sea desde una URL o desde un objeto XML ya descargado.

        Args:
            file_url (str): URL o ruta del archivo XML. Si `xml_downloaded` es True, se espera que sea el objeto XML.
            get_all_root (bool, optional): Si True, retorna también el objeto raíz del XML. Default es False.
            xml_downloaded (bool, optional): Si True, indica que `file_url` ya es un archivo abierto u objeto similar. Default es False.

        Returns:
            Atributos y objeto raíz (si get_all_root es True)
        """
        xmlobj = file_url if xml_downloaded else urllib.request.urlopen(file_url)
        
        try:
            tree = ET.parse(xmlobj)
            root = tree.getroot()
            dict_attribs = {a.lower():b for a,b  in root.attrib.items()}
            
            if get_all_root:
                return dict_attribs, root
            return dict_attribs
        
        except Exception as e:
            error_msg = f'XML dañado, favor de revisar: {e}'
            return (error_msg, None) if get_all_root else error_msg

    def integration_get_dict_node(self, node_to_process):
        """
        Se procesan los elementos que componen el xml de la factura para regresar un diccionario con el nombre y valor del elemento

        Args:
            node_to_process : Nodos del xml de la factura

        Return:
            Diccionario de elementos y valor
        """
        dict_attribs = {a.lower():b for a,b  in node_to_process.attrib.items()}
        for r in node_to_process:
            name_tag = r.tag.lower().replace('{http://www.sat.gob.mx/cfd/3}', '')
            name_tag = name_tag.replace('{http://www.sat.gob.mx/cfd/4}', '')

            list_nodes = []
            if 'pagos' in name_tag:
                dict_info_pago = {a.lower():b for a,b  in r.attrib.items()}
                if dict_info_pago:
                    list_nodes.append(dict_info_pago)
            for rr in r:
                dict_parent = {a.lower():b for a,b  in r.attrib.items()}
                dict_node = self.integration_get_dict_node(rr)
                dict_node.update({'info_parent': dict_parent})
                list_nodes.append(dict_node)
            if not list_nodes:
                list_nodes = {a.lower():b for a,b  in r.attrib.items()}
            if 'percepciones' in name_tag:
                dict_list_nodes = {a.lower():b for a,b  in r.attrib.items()}
                dict_list_nodes.update({
                    'percepciones': list_nodes
                })
                list_nodes = dict_list_nodes
            if dict_attribs.get(name_tag) and type(dict_attribs.get(name_tag)) == list and type(list_nodes) == list:
                dict_attribs[name_tag] += list_nodes
            else:
                dict_attribs[name_tag] = list_nodes
        return dict_attribs

    def next_step_process(self, accion="Generar Liberaciones", name_script="ejecuta_liberacion_de_folios.py", status_pass='generar_liberaciones'):
        metadata = self.lkf_api.get_metadata(self.FORMA_GENERAR_LIBERACIONES_Y_OCS)
        metadata['properties'] = self.get_metadata_properties(name_script, accion, "Proceso automatizado para liberación de folios", self.folio)
        metadata['answers'] = {
            '5f10d2efbcfe0371cb2fbd39': status_pass,
            '61eff4589ee4743986088809': 'sí'
        }
        res_create_est = self.lkf_api.post_forms_answers(metadata)
        print('res_create_est=',res_create_est)
        return res_create_est

    def notify_error(self, field_id, lbl, msg):
        """
        Marca error al enviar el registro

        Args:
            field_id (str): Id del campo donde se marca el error
            lbl (str): Label del campo en la forma
            msg (str): Mensaje de error que se presenta al usuario
        """
        raise Exception( simplejson.dumps({field_id: {'msg': [msg], 'label': lbl, 'error': []}}) )