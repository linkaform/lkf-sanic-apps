# -*- coding: utf-8 -*-
import re, sys, simplejson
import random, os, shutil, wget, zipfile, collections
from datetime import datetime
from produccion_pci_utils import Produccion_PCI

from account_settings import *

class Produccion_PCI( Produccion_PCI ):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

        self.list_tareas_solo_vsi = ['TS1L7VGPI', 'TS2L7VGPI']
        self.equivalcens_map_observa = { 'observaciones': ['OBSERVACIONES CLARO VIDEO', 'observaciones claro video', 'obs. claro video', 'observaciones cv']}

    def checa_liberacion_pago(self, form_id, folios):
        record = lkf_obj.get_records(form_id=form_id, folio=folios, select_columns=['folio'])
        liberados = [rec['folio'] for rec in record]
        return liberados

    def get_count_folios_in_db(self, form_id, folios ):
        records_os = self.get_records(form_id=form_id, folio=folios, select_columns=['folio'])
        dict_records_os = {}
        for r in records_os:
            dict_records_os.setdefault( r['folio'], 0 )
            dict_records_os[ r['folio'] ] += 1
        return dict_records_os

    def get_all_folios_ya_liberados(self, id_lib, foliosTelefonos, folios, records, id_os):
        foliosTelefonos_ya_liberados = []
        ya_liberados = self.checa_liberacion_pago(id_lib, foliosTelefonos)
        print('ya_liberados=',ya_liberados)
        ya_liberados_by_folio = self.checa_liberacion_pago(id_lib, folios)
        print('ya_liberados_by_folio=',ya_liberados_by_folio)
        folios_a_buscar_duplicado = []
        
        dict_ids_forms_oc = { 
            self.ORDEN_SERVICIO_FIBRA: self.FORMA_ORDEN_COMPRA_FIBRA, 
            self.ORDEN_SERVICIO_FIBRA_SURESTE: self.FORMA_ORDEN_COMPRA_FIBRA_SURESTE, 
            self.ORDEN_SERVICIO_FIBRA_NORTE: self.FORMA_ORDEN_COMPRA_FIBRA_NORTE, 
            self.ORDEN_SERVICIO_FIBRA_OCCIDENTE: self.FORMA_ORDEN_COMPRA_FIBRA_OCCIDENTE, 
            self.ORDEN_SERVICIO_COBRE: self.FORMA_ORDEN_COMPRA_COBRE, 
            self.ORDEN_SERVICIO_COBRE_SURESTE: self.FORMA_ORDEN_COMPRA_COBRE_SURESTE, 
            self.ORDEN_SERVICIO_COBRE_NORTE: self.FORMA_ORDEN_COMPRA_COBRE_NORTE, 
            self.ORDEN_SERVICIO_COBRE_OCCIDENTE: self.FORMA_ORDEN_COMPRA_COBRE_OCCIDENTE, 
        }
        
        for record in records:
            folio = self.strip_special_characters(record[0])
            rec_telefono = record[1]
            rec_foliotelefono = '{}{}'.format(folio, rec_telefono)
            if rec_foliotelefono in ya_liberados:
                foliosTelefonos_ya_liberados.append( rec_foliotelefono )
                print('Folio ya liberado por foliotelefono = ',folio)
                continue
            if folio in ya_liberados_by_folio:
                folios_a_buscar_duplicado.append(folio)
        if folios_a_buscar_duplicado:
            dict_records_os = self.get_count_folios_in_db( id_os, folios_a_buscar_duplicado )
            for record in records:
                folio = self.strip_special_characters(record[0])
                if folio not in folios_a_buscar_duplicado:
                    continue
                rec_telefono = record[1]
                rec_foliotelefono = '{}{}'.format(folio, rec_telefono)
                if dict_records_os.get(folio, 0) < 2:
                    # foliosTelefonos_ya_liberados.append(rec_foliotelefono)
                    print('Folio ya liberado por folio y no esta duplicado... lo dejo avanzar para revisar si ya esta en OC = ',folio)
                    # continue
                folio_is_in_oc = get_folio_in_oc( dict_ids_forms_oc[id_os], folio, rec_telefono )
                if folio_is_in_oc:
                    foliosTelefonos_ya_liberados.append(rec_foliotelefono)
                    print('Folio ya liberado por folio {} si esta duplicado pero ya está en OC {} con el telefono {}'.format(folio, folio_is_in_oc, rec_telefono))
                    continue
        return foliosTelefonos_ya_liberados
    
    def get_autorizacion_contratistas(self, filter_autorizacion):
        mango_query = { 
            "selector": { "answers": { '$and':[ filter_autorizacion ] } },
            "limit":10000,"skip":0
        }
        records_contratistas = lkf_api.search_catalog(self.CATALOGO_CONTRATISTAS_ID, mango_query)
        return [ int(cont.get('5f344a0476c82e1bebc991d6',0)) for cont in records_contratistas ]

    def get_contratistas_no_autorizados_liberacion(self):
        return self.get_autorizacion_contratistas( { "5fcab88c51dfeb3d86212027": { "$eq": "No" } } )

    def get_contratistas_autorizados_pdf(self):
        return self.get_autorizacion_contratistas( { "5fac1c22380db843149b7330": { "$eq": "Sí" } } )

    # def get_only_connections(self):
    #     # Se va a leer la lista de contratistas que el usuario requiera desde un excel
    #     if not current_record['answers'].get('60105b997b3c64bb35043c3c'):
    #         return {}

    #     # Se leen los emails del excel
    #     file_url = current_record['answers']['60105b997b3c64bb35043c3c']['file_url']
    #     header_contratistas, records_contratistas = p_utils.read_file( file_url )

    #     # Se obtienen las conexiones de la cuenta padre
    #     all_connections = p_utils.get_all_connections()

    #     dict_emails_connections = { infCon['email']: infCon['id'] for infCon in all_connections if infCon.get('email') and infCon.get('id') }

    #     emails_not_exists, emails_connections = [], []
    #     for email_contratista in records_contratistas:
    #         email_record = email_contratista[0]
    #         if not dict_emails_connections.get( email_record ):
    #             emails_not_exists.append( email_record )
    #             continue
    #         emails_connections.append( dict_emails_connections[ email_record ] )
        
    #     if emails_not_exists:
    #         return {'error': emails_not_exists}

    #     return {'result': emails_connections}

    def get_os_for_liberacion(self, form_id, contratistas_no_autorizados, contratistas_autorizados_pdf, tecnologia, only_connections):
        dict_pdf_memo_by_form = {
            self.ORDEN_SERVICIO_COBRE: ['5ad13efef851c23d8a4d95af', '5a623e30f851c2271179f823'],
            self.ORDEN_SERVICIO_COBRE_SURESTE: ['5ad13e8cf851c220dd0eb769', '5a623e30f851c2271179f823'],
            self.ORDEN_SERVICIO_COBRE_NORTE: ['5ad13f49f851c2510b0d210a', '5a623e30f851c2271179f823'],
            self.ORDEN_SERVICIO_COBRE_OCCIDENTE: ['5ad13f95f851c2467770da9e', '5a623e30f851c2271179f823'],
            self.ORDEN_SERVICIO_FIBRA_SURESTE: ['5ad14051f851c220dd0eb772', '5a623ed8b43fdd2b2bffb905'],
            self.ORDEN_SERVICIO_FIBRA_OCCIDENTE: ['5ad4b4a9b43fdd7af0f65899', '5a623faff851c227180570a0'],
            self.ORDEN_SERVICIO_FIBRA_NORTE: ['5ad14687f851c23d8a4d95c9', '5a623f3af851c2270c8dc073'],
            self.ORDEN_SERVICIO_FIBRA: ['5a8aefa7b43fdd100602f7be', '5a623e71b43fdd2b2d5a5893']
        }
        field_id_cliente = 'f1054000a0100000000000c5' if tecnologia == 'fibra' else '58e6d4cff851c244a78f35ca'
        
        query = {'form_id': form_id, 'deleted_at': {'$exists': False}, 

            # 'folio': {'$in': [
            #     "54336160", "54353191", "54372016", "54381766", "54384631", "15821946", "15868257", "15805948", "15838828", "15852207", "15859571", "15860547", "15863927", "15894223", "15895260", "15908445", "15916687", 
            #     "15917650", "15935987", "15957727", "16124070", "54405242", "15649397", "54415970", "54381686", "54376454", "54408934", "54406796", "15701921", "54373807", "54407507", "54411656", "54417108", "54427541", 
            #     "16125272", "16129543", "16172937", "16177574", "16178686", "16185349", "16188925", "16201320", "16213747", "16225257", "16226431", "16227368", "16235121", "16237413", "16245719", "16253253", "54387205", 
            #     "54413752", "54415517", "54370191", "54384475", "54382369", "54414108", "54388070", "54420286", "54385315", "54426151", "54356389", "54361355", "54362948", "54343909", "54361619", "54351747", "54347627", 
            #     "54351246", "54336991", "54406325", "54380470", "54381810", "54387039", "54378518", "54400187", "54402718", "54402767", "54397619", "54400193", "54403905", "54407297", "54404003", "54386809", "54404212", 
            #     "54415076", "54405325", "54405720", "54406224", "54370669", "54396952", "54384864", "54392433", "54387509", "54401488", "54410531", "54383744", "54379777", "54399587", "54405072", "54414209", "54415812", 
            #     "54416653", "54364103", "54386672", "54408039", "28390810", "28391667", "28393482", "28402695", "28406089", "28410054", "28419328", "28423464", "28429045"
            # ]},

            'created_at': {
                '$gte': datetime.strptime('2020-10-26 00:00:00', "%Y-%m-%d %H:%M:%S")
            },
            'connection_id': {'$exists': True},
            'answers.f1054000a030000000000002':'liquidada',
            'answers.f1054000a030000000000013': 'en_proceso',
            # 'answers.f1054000a030000000000012':{'$in':['estimacion','paco']},
            'answers.f1054000a030000000000012': 'pendiente',
            f'answers.{field_id_cliente}': {'$exists': True},
            'answers.633d9f63eb936fb6ec9bf580': {'$nin': ['cfe']},

            # Para las liberaciones no se consideran los folios marcados por más de 30 días, a menos que ya estén en Entrada 50
            '$or': [
                {'answers.601c7ae006478d9cbee17e00': {'$nin': ['sí']}},
                {'answers.5efa00c62542e523f391c636': {'$exists': True}}
            ]
            
        }
        
        liberando_cobre = tecnologia == 'cobre'

        if only_connections:
            query['connection_id'] = {'$in': only_connections}

        select_columns = {'folio':1, 'form_id': 1, 'answers':1, 'connection_id':1}
        print('##################### query=',query)
        records_found = self.cr.find(query, select_columns)        
        """
        Identificar los folios y telefonos de PSR
        """
        records_to_lib, fols_sin_pdf = [], []
        fields_pdfs_memo = dict_pdf_memo_by_form[ form_id ]
        for temp_record in records_found:
            folio_record_found = temp_record['folio']
            temp_answer = temp_record['answers']
            telefono_record_found = temp_answer.get('f1054000a010000000000005')
            
            # Los folios de los contratistas que generan en la otra forma de OC se van a ignorar
            if temp_record.get('connection_id',0) not in contratistas_no_autorizados:
                # En COBRE no se estan liberando las QUEJAS
                if liberando_cobre and temp_answer.get('f1054000a0100000000000a1', '') in ('QI', 'RI', 'EI', 'TN', 'TE'):
                    continue
                
                records_to_lib.append(temp_record)
                
                # Busco los registros que no tengan PDF para despues revisar si el contratista esta Autorizado o no
                if not temp_answer.get( fields_pdfs_memo[ 0 ] ) and not temp_answer.get( fields_pdfs_memo[ 1 ] ):
                    # El contratista deberia estar Autorizado para liberarse sin PDF, de lo contrario se va a marcar error
                    if temp_record.get('connection_id') not in contratistas_autorizados_pdf:
                        fols_sin_pdf.append( f'{folio_record_found}_{telefono_record_found}' )

        return records_to_lib, fols_sin_pdf

    def get_info_os(self, form_id, folios, telefonos):
        query = {'form_id':  form_id, 'deleted_at' : {'$exists':False}, 
            'folio':{'$in':folios},
            'answers.f1054000a010000000000005': {'$in': telefonos},
            'answers.f1054000a030000000000013':{'$in':['pendiente','en_proceso']}, 
            'answers.f1054000a030000000000012':{'$nin':['error_validacion']},
            'answers.f1054000a030000000000002':'liquidada'}
        select_columns = {'folio':1,'user_id':1,'form_id':1, 'answers':1,'_id':1,'connection_id':1}
        record = self.cr.find(query, select_columns)
        existentes = {'{}{}'.format(rec['folio'], rec['answers'].get('f1054000a010000000000005')):rec for rec in record}
        return existentes

    def prepare_os_for_update(self, registro_orden_servicio, answers, paco, metraje, tipo_de_instalacion, tecnologia_os):
        if tipo_de_instalacion:
            answers['f1054000a020000000000004'] = tipo_de_instalacion
        answers['f1054000a030000000000150'] = paco
        answers['f1054000a030000000000012'] = 'paco'

        if answers.get('f1054000a020000000000022') and tecnologia_os != answers['f1054000a020000000000022']:
            if metraje == 0 and tecnologia_os == 'vsi':
                answers['f1054000a0200000000000d7'] = '0'
            elif metraje > 0 and tecnologia_os == '':
                answers['f1054000a020000000000022'] = ''
        if tecnologia_os:
            answers['f1054000a020000000000022'] = tecnologia_os
        if metraje > 300:
            answers['f1054000a0200000000000d7'] = '300'
            answers['f1054000a020000000000bd7'] = str(int(metraje - 300))
        else:
            answers['f1054000a0200000000000d7'] = str(metraje)

        registro_orden_servicio['answers'] = answers
        return registro_orden_servicio

    def update_estatus_historico(self, origen, destino, folios, forma, other_fields={}, res_type='legacy'):
        query = {
            lkf_obj.f['field_id_cargado_desde_script']: 'sí',
            'f1054000a030000000000e20':{
                "-1":{
                    'f1054000a030000000000e21':origen,
                    'f1054000a030000000000e22':destino,
                    'f1054000a030000000000e23':p_utils.get_date_now(only_date=True)
                }
            }
        }
        if other_fields:
            query.update(other_fields)
        response = {}
        try:
            # if config.get('USER_JWT_KEY') and config['USER_JWT_KEY']:
            #     print "-- se va por USER_JWT_KEY"
            #     response = lkf_api.patch_multi_record(query, forma, record_id=folios, jwt_settings_key='USER_JWT_KEY', threading=True)
            # else:
            response = lkf_api.patch_multi_record(query, forma, record_id=folios, threading=True)
        except Exception as e:
            print('***********************************************', e)
        if res_type == 'legacy':
            if len(response.keys()) > 0:
                response =  response[response.keys()[0]]
                print('legacy response',response )
            if response.get('status_code',0)  >= 200 and response.get('status_code',0) < 300:
                return True
        return response

    def procesa_liberaciones(self, registros_acumulados, id_os, records, dict_pos_record, dict_ids_record):
        print('-------------------- registros_acumulados',registros_acumulados)
        response_liberaciones = {}
        error_comentarios_extra = []
        list_folios_liberados = []
        folios_registrados = []
        #try:
        if True:
            #resgistrar en la forma Liberacion de pagos
            libs_exitosas = 0
            libs_erroneas = 0
            if registros_acumulados:
                all_response_libera_pago = lkf_api.post_forms_answers_list(registros_acumulados, jwt_settings_key='USER_JWT_KEY')
                print('++++++++++++++ all_response_libera_pago:',all_response_libera_pago)
                for response_libera_pago in all_response_libera_pago:
                    status_code = response_libera_pago.get('status_code', 0)
                    #print 'status_code=',status_code
                    json = response_libera_pago.get('json', {})
                    #print 'NO EXISTE Y VA A TRONAR POR QUE LO CAMBIOAMOS PARA SACAR LOS FOLIOS Q SSI SE HICIERON reg_inserta ahora json',json
                    if status_code >= 200 and status_code <300:
                        if json.get('folio'):
                            folio_ok = json['folio']
                        else:
                            folio_ok = response_libera_pago['folio']
                        #print "********** folio registrado ", reg_inserta['folio']
                        folios_registrados.append( dict_ids_record[ folio_ok ] )
                        list_folios_liberados.append( records[ dict_pos_record[ folio_ok ] ] + ['Liberado correctamente',] )
                        libs_exitosas += 1
                    else:
                        libs_erroneas += 1
                        if json.get('folio'):
                            folio_error = json['folio']
                        else:
                            folio_error = response_libera_pago['folio']
                        if status_code == 400:
                            error_comentarios_extra.append(records[dict_pos_record[folio_error]] + [p_utils.arregla_msg_error_sistema(response_libera_pago)])
                            continue
                            for er in json:
                                val_er = json[er]
                                if 'msg' in val_er:
                                    error_comentarios_extra.append(records[dict_pos_record[folio_error]] + ['Folio ' +folio_error+' '+ val_er['label'] + ' ' + val_er['msg'][0],])
                                else:
                                    for er2 in val_er:
                                        val_er2 = val_er[er2]
                                        for er3 in val_er2:
                                            val_er3 = val_er2[er3]
                                            if 'msg' in val_er3:
                                                #error_comentarios_extra.append( 'Folio ' + folio_error + ' ' + val_er3['label'] + ' ' + val_er3['msg'][0] )
                                                error_comentarios_extra.append(records[dict_pos_record[folio_error]] + ['Folio ' + folio_error + ' ' + val_er3['label'] + ' ' + val_er3['msg'][0] ,])
                        elif status_code == 401:
                            error_comentarios_extra.append(records[dict_pos_record[folio_error]] + ['No autorizado para crear Folio ' + folio_error,])
                        elif status_code == 404:
                            error_comentarios_extra.append(records[dict_pos_record[folio_error]] + ['Folio ' +folio_error+' No fue encontrado',])
                        elif status_code == 500:
                            error_comentarios_extra.append(records[dict_pos_record[folio_error]] + ['Error en el Servidor al contestar Folio ' + folio_error+', Contactar Administrador!',])
                        elif status_code > 500:
                            error_comentarios_extra.append(records[dict_pos_record[folio_error]] + ['Error en el Servidor al contestar Folio ' + folio_error+', Volver a Intentar!',])
                        else:
                            error_comentarios_extra.append(records[dict_pos_record[folio_error]] + ['Error desconocido para el Folio ' + folio_error,])

            #error_file = p_utils.upload_error_file(header + ['error',],  record_errors, CAGA_LIBERACION, file_field_id='f2362800a010000000000005')
            if error_comentarios_extra:
                print('error_comentarios_extra=', error_comentarios_extra)
                response_liberaciones.update({'list_errores': error_comentarios_extra})
            if list_folios_liberados:
                response_liberaciones.update({'list_liberados': list_folios_liberados})
            response_liberaciones.update({'libs_exitosas': libs_exitosas, 'libs_erroneas': libs_erroneas})

        update_status_fields = {'f1054000a030000000000013':'por_facturar'}
        print('folios', folios_registrados)
        update_res = self.update_estatus_historico('en_proceso', 'por_facturar', folios_registrados, id_os, update_status_fields, res_type='threading')
        return response_liberaciones

    def get_value_metraje(self, rec):
        value = 0
        if rec[9] and rec[10]:
            return 300 + rec[10]
        for n, val in enumerate(rec):
            if not val:
                continue
            if n in (8, 9, 10):
                value = val if n==10 else 300 if n == 9 else 250
            else:
                value = (n+1) * 25 # Agregara valores de 25 en 25 segun la posicion
        return value
    
    def make_liberaciones_for_fibra(self, current_record, record_id, answers, header, records, tecnologia, division, id_os, id_lib, fols_sin_pdf, **kwargs):
        # CONCEPTOS MINIMOS PARA A4 EN LAS POSICIONES = 34 a 42
        


        # TODO: Estos for me los puedo ahorrar y de una vez armarlo cuando se estan procesando los folios
        folios = [self.strip_special_characters(rec[0]) for rec in records]
        telefonos = [rec[1] for rec in records]
        foliosTelefonos = ['{}{}'.format(self.strip_special_characters(rec[0]), rec[1]) for rec in records]



        print('folios= len', len(folios))
        
        total_folios_telefonos_liberados = self.get_all_folios_ya_liberados( id_lib, foliosTelefonos, folios, records, id_os )
        
        orden_servicio_existe = self.get_info_os(id_os, folios, telefonos)
        print('cantidad de orden_servicio_existe =', len(orden_servicio_existe))
        folios_no_listos = list(set(foliosTelefonos) - set(orden_servicio_existe))
        print('cantidad folios no listos', len(folios_no_listos))
        print('folios no listos=', folios_no_listos)
        orders_to_patch = []
        record_errors_final = []
        dict_pos_record = {}
        dict_ids_record = {}
        detail_records = {}
        date_to_mayor_300m = p_utils.str_to_date('2022-09-01')
        for pos_rec, record in enumerate(records):
            folio = self.strip_special_characters(record[0])
            
            # Se obtiene el metraje y el tipo de instalacion
            metraje = self.get_value_metraje(record[5:16])
            tipo_de_instalacion = ''
            if metraje:
                tipo_de_instalacion = 'aerea'
            else:
                metraje = self.get_value_metraje(record[16:27])
                if metraje:
                    tipo_de_instalacion = 'subterranea'
            
            # Tecnología es VSI cuando el tipo de tarea empieza por TS
            tecnologia_os = ''
            if record[2][:2].lower() != 'a4' and not metraje and not tecnologia_os:
                if '7V' not in record[2]:
                    record_errors_final.append(record+["Error de Metraje y Tecnologia",])
                    continue
            
            rec_telefono = record[1]
            rec_folio_telefono = '{}_{}'.format(folio, rec_telefono)
            rec_foliotelefono = '{}{}'.format(folio, rec_telefono)
            
            if rec_foliotelefono in total_folios_telefonos_liberados:
                print('folio ya liberado', folio)
                continue
            
            if rec_foliotelefono in folios_no_listos:
                msg = f"Folio {folio} No esta en el status correcto para ser procesado"
                print(msg)
                record_errors_final.append(record + ["El Folio no esta en el status correcto ",])
                continue
            
            if rec_folio_telefono in fols_sin_pdf:
                record_errors_final.append(record + ["El registro no tiene PDF",])
                continue
            
            #verifica si el folio existe
            if rec_foliotelefono in orden_servicio_existe.keys():
                o_s = orden_servicio_existe[rec_foliotelefono]
                answers = o_s['answers']
                
                # Esta validacion esta de mas porque ya se filtra desde el query inicial
                # estatus_cobranza_contratista = answers.get('f1054000a030000000000013',False)
                # if estatus_cobranza_contratista in ['pagada', 'por_pagar']:
                #     print('status de cobranza:' ,estatus_cobranza_contratista)
                #     record_errors_final.append(record+["El folio %s estatus_cobranza_contratista pagada o por pagar. " % folio,])
                #     continue 
                # if not estatus_cobranza_contratista:
                #     print('contratista', folio)
                #     record_errors_final.append(record+["No se econtro un status de pago contratista " % folio,])
                #     continue 
                
                if metraje > 1125:
                    record_errors_final.append(record+["Metraje excedido "+str(metraje),])
                    continue
                '''
                Agrego validiación para NO aceptar metrajes mayores a 300 Mts si no están en la forma Folios permitidos para liberación Fibra
                '''
                if metraje > 300:
                    telefono = answers.get('f1054000a010000000000005',0)
                    fecha_liquidada = answers.get('f1054000a02000000000fa02')
                    date_fecha_liquidada = p_utils.str_to_date(fecha_liquidada)
                    continua_por_liquidacion_desde_agosto = date_fecha_liquidada >= date_to_mayor_300m
                    if not continua_por_liquidacion_desde_agosto and not find_folio_in_permitidos_liberacion(folio, telefono, division):
                        '''
                        Si el folio no está en la forma de Autorizaciones, entonces debe traer la etiqueta Autorizado por PIC
                        '''
                        autorizado_por_pic = answers.get('5fd3cde61b0c8e82ae9d4d60', False)
                        if not autorizado_por_pic or autorizado_por_pic == 'no':
                            record_errors_final.append(record+["Se requiere autorización de metraje para poder continuar con la liberación"])
                            continue
                
                dict_pos_record.update({rec_foliotelefono: pos_rec})
                dict_ids_record.update({rec_foliotelefono: str( o_s['_id'] )})
                registro_orden_servicio = self.prepare_os_for_update(o_s, {}, current_record['folio'], metraje, tipo_de_instalacion, tecnologia_os)
                registro_orden_servicio['records'] = [str( o_s['_id'] ),]
                registro_orden_servicio['folio'] = rec_foliotelefono
                orders_to_patch.append(registro_orden_servicio)

                # Trabajando los radiales
                indices_default_cero = [30, 31, 32, 34, 35]
                for i_def0 in indices_default_cero:
                    record[i_def0] = 0 if not record[i_def0] else record[i_def0]

                detail_records.update({
                    rec_foliotelefono:{
                        'f2361400a010000000000001':current_record['folio'], # Utilizare el Folio del registro de carga como si fuera el PACO
                        'f2361400a010000000000002':metraje,
                        'f2361400a010000000000003':'', # Comentarios
                        'f2361400a010000000000004':tecnologia_os,
                        'f2361400a010000000000005':'liberado',
                        '5ebeaf5df6fcb50881282dc7': int(record[30]), # RADIAL EN BANQUETA
                        '5ebeaf5df6fcb50881282dc6': int(record[31]), # RADIAL EN CEPA LIBRE
                        '5ebeaf5df6fcb50881282dc5': int(record[32]), # REPARACION DE TROPEZON EN RADIAL
                        # Conceptos para A4
                        '5f033e1248598b3eda0e34c4': record[36],
                        '5f033e1248598b3eda0e34c5': record[37],
                        '5f033e1248598b3eda0e34c6': record[38],
                        '5f033e1248598b3eda0e34c7': record[39],
                        '5f033e1248598b3eda0e34c8': record[40],
                        '5f033e1248598b3eda0e34c9': record[41],
                        '5f033e1248598b3eda0e34ca': record[42],
                        '5f033e1248598b3eda0e34cb': record[43],
                        '649711a6ccc16f1189087d45': record[34],
                        'f2361400a010000000000f17': record[35],
                        '64c81ec3ca956450a2169a44': record[27], # Desmontaje en Migracion
                        # Conceptos para PSR
                        '6726ff1164633c2f15ba7af4': record[44], # INCENTIVO PSR
                        '6726ff1164633c2f15ba7af5': record[45], # REPARACION DE INSTALACIONES
                        '6726ff1164633c2f15ba7af6': record[46], # REPARACION DE INSTALACIONES CON INCENTIVO
                    }
                })
        print("++++++++ orders_to_patch:",orders_to_patch)
        patch_res = {}
        if orders_to_patch:
            patch_res = lkf_api.bulk_patch(orders_to_patch, id_os, jwt_settings_key='USER_JWT_KEY', threading=True)
        metadata_fibra = lkf_api.get_metadata(form_id=id_lib)
        registros_acumulados = []
        for order_folio, response in patch_res.items():
            if response.get('status_code') != 202:
                print('... error en bulk_patch {} : {}'.format(order_folio, str(response)))
            if detail_records.get(order_folio):
                new_metadata = metadata_fibra.copy()
                proceso_orden_servicio = response['status_code'] in (200, 201, 202, 204, 205)
                if proceso_orden_servicio:
                    new_metadata['folio'] = str(order_folio)
                    answers_para_meta = detail_records[order_folio]
                    new_metadata.update({
                        "properties": {"device_properties":{"system": "SCRIPT","process":"PROCESO LIBERACION DE PAGOS", "accion":"Liberacion", "folio carga":current_record['folio'], "archive":"generar_liberaciones_fibra_cobre.py"}}
                    })
                    new_metadata['answers'] = answers_para_meta
                    registros_acumulados.append(new_metadata)
                else:
                    print('MENOS 1 Q NO SE HIZO BIEN', order_folio)
                    msg_error = f"El folio {order_folio} no fue encontrado para su edicion" if response['status_code'] == 404 else f"Error al actualizar el folio {order_folio} {response}"
                    record_errors_final.append( records[ dict_pos_record[ order_folio ] ] + [ msg_error, ] )
            else:
                print('... ... queeeeee raro no esta en el detail_records =',order_folio)
        response_liberaciones = self.procesa_liberaciones(registros_acumulados, id_os, records, dict_pos_record, dict_ids_record)
        response_liberaciones['list_errores'] = record_errors_final + response_liberaciones.get('list_errores', [])

        libs_by_connection = {}

        def update_dicts_libs( str_name_list ):
            for rec_lib in response_liberaciones.get(str_name_list, []):
                f = str( rec_lib[0] )
                conexion_id = orden_servicio_existe.get( f, {} ).get( 'connection_id', 0 )
                if conexion_id:
                    libs_by_connection.setdefault(conexion_id, { str_name_list: [] })
                    libs_by_connection[conexion_id][str_name_list].append( rec_lib )

            if response_liberaciones.get(str_name_list):
                response_liberaciones[str_name_list].insert(0,header)

        update_dicts_libs( 'list_errores' )
        update_dicts_libs( 'list_liberados' )

        return response_liberaciones, libs_by_connection

    def get_detail_record_cobre(self, record, map_campos_cobre, conexion, division, tipo_trabajo='', is_psr=False):
        registro_detalle = {}

        if is_psr:
            registro_detalle['681c0e22e3d9bc611e3a5187'] = 1
        elif tipo_trabajo.lower() == 'a4':
            registro_detalle['681c0e22e3d9bc611e3a5188'] = 1
        elif tipo_trabajo.lower() == 'a2':
            registro_detalle['6916c12d5ab0bd965da971b3'] = 1
        else:
            registro_detalle['681c0e22e3d9bc611e3a5189'] = 1

        # Determinar tipo de trabajo y ajustar el nivel de pago
        if tipo_trabajo in ['QI', 'RI', 'EI']:
            tipo_trabajo = 'QI'
        
        # Recorrer campos y asignar valores a registro_detalle
        for i, field_id in map_campos_cobre.items():
            if tipo_trabajo in ['QI', 'TN'] and not is_psr:
                registro_detalle[field_id] = 0
            elif i == 20:
                # Condición para field_id específico según la division
                registro_detalle['f2361400a010000000000f30' if division != 'sur' else field_id] = record[i]
            else:
                registro_detalle[field_id] = record[i]
        
        # Asignar campos específicos para tipo_trabajo 'QI' y 'TN' cuando no es PSR
        # if tipo_trabajo == 'QI' and not is_psr:
        #     registro_detalle[ map_campos_cobre[21] ] = 1
        #     registro_detalle[ map_campos_cobre[0] ] = record[0]
        # if tipo_trabajo == 'TN':
        #     registro_detalle[ map_campos_cobre[22] ] = 1
        #     registro_detalle[ map_campos_cobre[0] ] = record[0]
        
        '''
        Si es A4 y nivel de pago bajo se agregan conceptos por default y todo lo demás es 0
        '''
        if (tipo_trabajo == 'A4') and not is_psr:
            for i, field_id in map_campos_cobre.items():
                registro_detalle[field_id] = 0
            map_campos_cobre_a4_minimo = ['5f033e1248598b3eda0e34c4', '5f033e1248598b3eda0e34c5','5f033e1248598b3eda0e34c6','5f033e1248598b3eda0e34c7',\
                '5f033e1248598b3eda0e34c8','5f033e1248598b3eda0e34c9','5f033e1248598b3eda0e34ca','5f033e1248598b3eda0e34cb']
            for min_a4 in map_campos_cobre_a4_minimo:
                registro_detalle[ min_a4 ] = 1
            # registro_detalle[ map_campos_cobre[0] ] = record[0]


        if tipo_trabajo in ['A7', 'A9', 'AE', 'AT']:
            tipo_trabajo = 'A0'
        if tipo_trabajo in ['D1', 'D2', 'D3', 'D4', 'TE']:
            tipo_trabajo = 'CD'

        registro_detalle.update({
            'f2361400a0100000000000b6': tipo_trabajo.lower(), # Agrego el tipo de trabajo
            'f2361400a0100000000000d6': 'sin_ie', # Infraestructura
        }) # Agrego el año de trabajo
        return registro_detalle

    def make_liberaciones_for_cobre(self, current_record, record_id, answers, header, records, tecnologia, division, id_os, id_lib, fols_sin_pdf, **kwargs):
        #id_os, id_lib = p_utils.get_id_os(answers.get('5f10d39c36da2addb92fbcd3',''), tecnologia)
        folios = [self.strip_special_characters(rec[0]) for rec in records]
        telefonos = [rec[1] for rec in records]
        foliosTelefonos = ['{}{}'.format(self.strip_special_characters(rec[0]), rec[1]) for rec in records]
        
        #ya_liberados = self.checa_liberacion_pago(id_lib, foliosTelefonos)
        total_folios_telefonos_liberados = self.get_all_folios_ya_liberados( id_lib, foliosTelefonos, folios, records, id_os )
        
        orden_servicio_existe = self.get_info_os(id_os, folios, telefonos)
        folios_no_listos = list(set(foliosTelefonos) - set(orden_servicio_existe))
        record_errors_final = []
        proceso_valida_os = {}
        detail_records = {}
        folios_validos = []
        dict_pos_record = {}
        dict_ids_record = {}
        orders_tu_patch = []
        registros_acumulados = []
        map_campos_cobre = {
            0: 'f2361400a0100000000000a6', # Folio
            # 5: 'f2361400a0100000000000f5', # Construccion de linea de cliente basica de 1 par (bajante)
            # 6: 'f2361400a0100000000000f9', # Plusvalia por tramo adicional de 50m. con bajante de 1 par
            # 7: 'f2361400a010000000000f19', # Bonificacion por distancia y volumen de 1 a 5 o.s construidas
            # 8: 'f2361400a010000000000f20', # Bonificacion por distancia y volumen de 6 a 15 o.s construidas
            # 9: 'f2361400a010000000000f21', # Bonificacion por distancia y volumen de 16 a 25 o.s construidas
            # 10: 'f2361400a010000000000f22', # Bonificacion por distancia y volumen mas de 25 o.s construidas
            # 11: 'f2361400a010000000000f23', # Montaje de puente en distribuidor general
            # 12: '60f1b780aea80a7b76393a1e', # Construccion o rehabilitacion de cableado interior para 1 aparato ---- ESTE NO SE LLENA
            # 13: 'f2361400a010000000000f27', # Cableado interior adicional para el dit con splitter con proteccion (extension)
            # 14: 'f2361400a010000000000f17', # INSTALACIÓN DE POSTE DE 25'
            # 15: 'f2361400a010000000000f28', # Pruebas de transmision de datos vdsl en roseta de datos con equipo homologado
            # 16: 'f2361400a010000000000f26', # Cableado interior 1 aparato y modem para infinitum (dit con splitter con proteccion)
            # 17: '5d5f2c42e1b88601d9aecba1', # IDENTIFICACION DE NUMERO TELEFONICO EN RED PRINCIPAL, INCLUYE MARCACION *080 ---- Aplica para SUR
            # 18: '5d5f2c42e1b88601d9aecba2', # IDENTIFICACION DE NUMERO TELEFONICO EN RED SECUNDARIA, INCLUYE MARCACION *080 ---- Aplica para SUR
            # 19: 'f2361400a010000000000f29', # UBICACIÓN DEL CLIENTE Y PRUEBA DE TRANSMISION VDSL EN TERMINAL AEREA
            # 20: '5d5f2c42e1b88601d9aecba4', # PRUEBA DE TRANSMISION VDSL ADICIONAL EN TERMINAL AREA
            # 21: '5f5f7df6241d67b2c237e12b', # QUEJAS
            # 22: '5ebe1b461b45ea3bb0282dcc', # Migración a TBA
            # 23: '609d51063480a16b03f7721c', # Línea de cliente básica de 1 par (bajante) (sin modem)
            # 32: '6726ff1164633c2f15ba7af4', # INCENTIVO PSR
            # 33: '6726ff1164633c2f15ba7af5', # REPARACIÓN DE INSTALACIONES
            # 34: '6726ff1164633c2f15ba7af6', # REPARACION DE INSTALACIONES CON INCENTIVO
        }
        libs_by_connection = {}
        dict_new_answers = {}


        for pos_rec, record in enumerate(records):
            folio = self.strip_special_characters(record[0])
            if folio == '':
                continue
            rec_telefono = record[1]
            rec_folio_telefono = '{}_{}'.format(folio, rec_telefono)
            rec_foliotelefono = '{}{}'.format(folio, rec_telefono)
            if rec_foliotelefono in total_folios_telefonos_liberados:
                print('folio ya liberado', folio)
                continue
            if rec_foliotelefono in folios_no_listos:
                msg = "Folio %s No esta en el status correcto para ser procesado" % folio
                print(msg)
                record_errors_final.append(record + ["El Folio no esta en el status correcto ",])
                continue
            if rec_folio_telefono in fols_sin_pdf:
                record_errors_final.append(record + ["El registro no tiene PDF",])
                continue
            if rec_foliotelefono in orden_servicio_existe.keys():
                orden = orden_servicio_existe[rec_foliotelefono]
                answers = {}
                conexion = orden.get('connection_id',0)
                estatus_cobranza_contratista = orden.get('answers',{}).get('f1054000a030000000000012',False)
                if estatus_cobranza_contratista in ['pagada', 'por_pagar']:
                    print('status de cobranza' ,folio)
                    record_errors_final.append(record+["El folio %s estatus_cobranza_contratista pagada o por pagar. " % folio,])
                    continue 
                if not estatus_cobranza_contratista:
                    print('contratista', folio)
                    record_errors_final.append(record+["El folio %s estatus_cobranza_contratista. No econtro un status de pago contratista " % folio,])
                    continue 
                '''
                Validaciones para liberar el tipo de precio para las A4
                '''
                tipo_trabajo = record[2][:2]
                a4_telefono = record[1]
                '''
                =====================================================
                '''
                dict_new_answers[ rec_foliotelefono ] = orden.get('answers', {})
                record_is_psr = orden.get('answers',{}).get('633d9f63eb936fb6ec9bf580', '') == 'psr'
                detail_records.update({rec_foliotelefono: self.get_detail_record_cobre(record, map_campos_cobre, conexion, division, tipo_trabajo=tipo_trabajo, is_psr=record_is_psr)})
                dict_pos_record.update({rec_foliotelefono: pos_rec})
                dict_ids_record.update({rec_foliotelefono: str( orden['_id'] )})
                # Esto de evaluate_answer_values ya no se ocupa porque en este modulo no se trabajan todos los campos
                # registro_orden_servicio = evaluate_answer_values(orden, record, answers)
                # registro_orden_servicio['folios'] = [folio,]
                # registro_orden_servicio['folio'] = rec_foliotelefono
                # orders_tu_patch.append(registro_orden_servicio)
                folios_validos.append(folio)
        patch_res = {}
        if orders_tu_patch:
            patch_res = lkf_api.bulk_patch(orders_tu_patch, id_os, jwt_settings_key='USER_JWT_KEY', threading=True)
            print('patch_res',patch_res)
        
        metadata_cobre = lkf_api.get_metadata(form_id=id_lib)
        # for order_folio, response in patch_res.items():
        #     if detail_records.get(order_folio):
        #         proceso_orden_servicio = False
        #         if response['status_code'] in (200, 201, 202, 204, 205):
        #             proceso_orden_servicio = True
        #         elif response['status_code'] == 404:
        #             record_errors_final.append(records[dict_pos_record[order_folio]] + ["El folio %s no fue encontrado para su edicion"%(order_folio),])
        #         elif response['status_code'] == 400:
        #             # Probable error por folio duplicado, se reintenta ahora con el patch simple
        #             orden_servicio_existe[order_folio]['answers'].update( dict_new_answers.get(order_folio, {}) )
        #             res_simple_patch = lkf_api.patch_record( orden_servicio_existe[order_folio] )
        #             print('res_simple_patch =',res_simple_patch)
        #             if res_simple_patch.get('status_code', 0) == 202:
        #                 proceso_orden_servicio = True
        #             else:
        #                 record_errors_final.append(records[dict_pos_record[order_folio]] + ["Error al acutalizar el folio %s "%order_folio ,str(res_simple_patch),])
        #         else:
        #             try:
        #                 record_errors_final.append(records[dict_pos_record[order_folio]] + ["Error al acutalizar el folio %s "%order_folio ,str(response['content']),])
        #             except:
        #                 record_errors_final.append(records[dict_pos_record[order_folio]] + ["Error al acutalizar el folio %s "%order_folio ,str(response),])

        #         if proceso_orden_servicio:
        for order_folio, data_to_lib in detail_records.items():
            registro_arreglo = [data_to_lib,]
            new_metadata = metadata_cobre.copy()
            new_metadata['folio'] = str(order_folio)
            new_metadata.update({
                "properties": {"device_properties":{"system": "SCRIPT","process":"PROCESO LIBERACION DE PAGOS", "accion":"Liberacion", "folio carga":current_record['folio'], "archive":"liberacion_de_folios.py"}}
            })
            answers_para_meta = {'f2361400a010000000000001':current_record['folio'],
                                'f2361400a010000000000005':'liberado',
                                'f2361400a010000000000006':registro_arreglo}
            new_metadata['answers'] = answers_para_meta
            registros_acumulados.append(new_metadata)
        # else:
        #     print('MENOS 1 Q NO SE HIZO BIEN', order_folio)
        response_liberaciones = self.procesa_liberaciones(registros_acumulados, id_os, records, dict_pos_record, dict_ids_record)
        if response_liberaciones.get('list_errores') and response_liberaciones['list_errores']:
            total_errores_records = record_errors_final + response_liberaciones.get('list_errores')
            response_liberaciones.update({'list_errores': total_errores_records})
        else:
            response_liberaciones.update({'list_errores': record_errors_final})


        # Separando la lista de errores por contratista
        def update_dicts_libs( str_name_list ):
            for rec_lib in response_liberaciones.get(str_name_list, []):
                f = str( rec_lib[0] )
                conexion_id = orden_servicio_existe.get( f, {} ).get( 'connection_id', 0 )
                if conexion_id:
                    libs_by_connection.setdefault(conexion_id, { str_name_list: [] })
                    libs_by_connection[conexion_id][str_name_list].append( rec_lib )

            if response_liberaciones.get(str_name_list):
                response_liberaciones[str_name_list].insert(0,header)

        update_dicts_libs( 'list_errores' )
        update_dicts_libs( 'list_liberados' )
        
        return response_liberaciones, libs_by_connection

    def remove_ceros( self, list_to_remove ):
        new_list_sin_ceros = [['' if m==0 else m for m in l] for l in list_to_remove]
        return new_list_sin_ceros

    def process_rows_for_libs(self, records_for_liberacion, all_contratistas_1_0, tecnologia, division):
        dict_ids_folio_telefono, expedientes_found = {}, {}
        records_libs = []
        for rec in records_for_liberacion:
            try:
                entero_folio = int( rec.get('folio') )
            except Exception as e:
                print('>>>>>>>>>>>>>>>>>> Error el folio no es entero Tecnologia: {0} Division: {1} Folio: {2}'.format(tecnologia, division, rec.get('folio')))
                continue

            if len( rec.get('folio') ) != 8:
                print('>>>>>>>>>>>>>>>>>> Error el folio no tiene 8 digitos Tecnologia: {0} Division: {1} Folio: {2}'.format(tecnologia, division, rec.get('folio')))
                continue

            ans = rec.get('answers',{})
            connection_id = rec.get('connection_id',0)

            # 20240906 no se deben estimar los folios del contratista 16019
            # Esto esta bien pinche... despues revisar como puedo mejorar el query para filtrar este tipo de cosas
            if connection_id == 16019:
                continue

            os_record_telefono = ans.get('f1054000a010000000000005','')
            fecha_de_liquidacion = ans.get( '5a1eecfbb43fdd65914505a1' if tecnologia=='cobre' else 'f1054000a02000000000fa02', '' )
            proyecto_os = ans.get('633d9f63eb936fb6ec9bf580', '')
            os_record_folio = rec['folio']
            os_record_id = str(rec['_id'])
            dict_ids_folio_telefono[ os_record_id ] = {'folio': os_record_folio, 'telefono': os_record_telefono}

            # Para el cobro minimo tenía la validacion de si no habia conexion 
            # if not connection_id
            # Ahora se va a cambiar por el os_has_minimo
            os_has_minimo = ans.get('5fc9269ce5363f7e3b9e3867', 'no') != 'no'
            if not os_has_minimo:
                os_has_minimo = ans.get('601c7ae006478d9cbee17e00', 'no') != 'no'

            socio_comercial = ''
            
            # Esto del Socio Comercial no estoy seguro que aplique para el modulo

            # if not connection_id:
            #     # Buscare con el expedinte en la forma Expedientes Técnicos para ver que Contratista le corresponde
            #     expediente = ans.get( 'f1054000a010000000000007', ans.get('f1054000a0100000000000d6', '0') )
            #     print('========= Folio= {} no tiene conexion... buscando a que contratista le pertenece con el expediente= {}'.format(os_record_folio, expediente))
            #     if not expedientes_found.get(expediente):
            #         expedientes_found[ expediente ] = p_utils.find_in_lista_tecnicos(0, expediente, find_by_expediente=True)
            #     conn_os = expedientes_found.get(expediente)
            #     print('contratista encontrado=',conn_os)
            #     if conn_os:
            #         conn_os = int(conn_os)
            #         # 20241206 Folios con expediente del contratista 16019 no se estiman
            #         if conn_os == 16019:
            #             continue
                    
            #         catalog_sc = all_contratistas_1_0.get(conn_os, {}).get('socio_comercial', '')
            #         catalog_rs = all_contratistas_1_0.get(conn_os, {}).get( 'razon_social_{}'.format(tecnologia) )
            #         socio_comercial, str_detail_sc = p_utils.get_socio_comercial(tecnologia, fecha_de_liquidacion, conn_os, dict_connections_sc, catalog_rs, catalog_sc)
                    
            #         print('socio_comercial=',socio_comercial)
            #     if not conn_os or not socio_comercial:
            #         print('No se encontro conexion con el expediente, o bien, no se encontro socio comercial en el catalogo... se define de acuerdo a la tecnologia')
            #         socio_comercial = 'REDES' if tecnologia == 'fibra' else 'IACON'

            nombre_contratista = ''
            
            # El nombre del contratista no estoy que aplique para el modulo porque solo es informativo en las estimaciones

            # if connection_id:
            #     catalog_sc = all_contratistas_1_0.get(connection_id, {}).get('socio_comercial', '')
            #     catalog_rs = all_contratistas_1_0.get(connection_id, {}).get( 'razon_social_{}'.format(tecnologia) )
            #     socio_comercial, str_detail_sc = p_utils.get_socio_comercial(tecnologia, fecha_de_liquidacion, connection_id, dict_connections_sc, catalog_rs, catalog_sc)
                
            #     nombre_contratista = name_default if name_default else dict_info_connection.get(connection_id, {}).get('first_name', '')

            validacion_de_sistemas = ans.get('66b25bedd23f3efc6902bb5d', '')
            record_is_cfe = proyecto_os == 'cfe'

            folio_join_telefono = '{}{}'.format( os_record_folio, os_record_telefono )
                
            tipo_tarea = ans.get( 'f1054000a0100000000000a4', ans.get('f1054000a010000000000021', '') )
            clase = tipo_tarea[2:4]
            is_clase_10_20 = clase in ['10', '20']

            tipo_trabajo = tipo_tarea[:2].lower()
            record_is_a4 = tipo_trabajo == 'a4'
            
            cope_record = ans.get('f1054000a010000000000002','').replace('_',' ').upper()

            list_rec = [
                os_record_folio, 
                os_record_telefono, 
                tipo_tarea, 
                cope_record, 
                'PC INDUSTRIAL S.A. DE C.V.', 
            ]

            if tecnologia == 'cobre':
                '''
                Empezando análisis de COBRE...
                '''
                # Linea de cliente basica de 1 par (bajante).- Default es 1, si Tipo de Tarea empieza por TE el valor es 0
                un_par_bajante = 1
                # Cableado interior adicional para el dit con splitter con proteccion (extension).- Si el tipo de tarea empieza por TE lleva 1
                # y depende de lo que cargue el contratista en el campo Cantidad de extensiones, pero el maximo es 3, si no hay info con que sea TE lleva 1 por default
                cantidad_extensiones = ans.get('5f7f627c6ca87fa5ca92cd1c',0)
                cableado_interior_extension = 3 if cantidad_extensiones > 3 else cantidad_extensiones
                
                metros_bajante = ans.get('f1054000a02000000000007a', ans.get('f1054000a020000000000007',0))
                montaje_puente_dist_gral = ans.get('5f1721afa63c9a750b820486',0)
                cableado_interior_modem_infinitum = ans.get('5f1721afa63c9a750b820489',0)
                # Cuando es solo PIC (que ya paso más de un mes) poner en metros bajante un aleatorio de entre 20 y 50
                if not connection_id or os_has_minimo:
                    if not all_contratistas_1_0.get(connection_id, {}).get('socio_comercial', '') or not connection_id:
                        metros_bajante = random.randint(20, 50)
                    tipo_instalacion = 'aerea'
                    # plusvalia_tramo_adicional = 2
                    montaje_puente_dist_gral = 2
                    cableado_interior_modem_infinitum = 1
                if re.match(r"^TE|^te", tipo_tarea):
                    un_par_bajante = 0
                    plusvalia_tramo_adicional = 0
                    if cantidad_extensiones == 0:
                        cableado_interior_extension = 1
                else:
                    # Plusvalia por tramo adicional de 50m. con bajante de 1 par.- si Tipo de Tarea empieza por TE pone 0, cualquier otro permite del 0 al 5
                    # para obtener el valor dependerá de los metrajes
                    # 0 a 50 = 0; 51 a 100 = 1; 101 a 150 = 2; 151 a 200 = 3; 201 a 250 = 4; 251 en adelante = 5
                    # Calcula plusvalia_tramo_adicional en función de metros_bajante
                    plusvalia_tramo_adicional = min(5, max(0, (metros_bajante - 1) // 50))

                '''
                ***************************************************
                '''
                list_rec.append( 0 if is_clase_10_20 else un_par_bajante )
                list_rec.append(plusvalia_tramo_adicional)
                list_rec.append(ans.get('5f1721afa63c9a750b820482',0)) # Bonificacion por distancia y volumen de 1 a 5 o.s construidas
                list_rec.append(ans.get('5f1721afa63c9a750b820483',0)) # Bonificacion por distancia y volumen de 6 a 15 o.s construidas
                list_rec.append(ans.get('5f1721afa63c9a750b820484',0)) # Bonificacion por distancia y volumen de 16 a 25 o.s construidas
                list_rec.append(ans.get('5f1721afa63c9a750b820485',0)) # Bonificacion por distancia y volumen mas de 25 o.s construidas
                
                # Montaje de puente en distribuidor general
                if not montaje_puente_dist_gral:
                    montaje_puente_dist_gral = 1 if is_clase_10_20 else 2
                list_rec.append(montaje_puente_dist_gral)
                
                # Construccion o rehabilitacion de cableado interior para 1 aparato.- Solo se llena en las Estimaciones
                # if proceso == 'estimaciones':
                val_construccion_rehabilitacion = ans.get('605cd146f499106724acb8c7', 0)
                val_construccion_rehabilitacion = 1 if (is_clase_10_20 and not val_construccion_rehabilitacion) else 0
                
                list_rec.append(val_construccion_rehabilitacion)
                list_rec.append(cableado_interior_extension)
                list_rec.append(ans.get('5f1721afa63c9a750b820487',0)) # INSTALACIÓN DE POSTE DE 25'
                list_rec.append(ans.get('5f1721afa63c9a750b820488',0)) # Pruebas de transmision de datos vdsl en roseta de datos con equipo homologado
                list_rec.append(0 if is_clase_10_20 else cableado_interior_modem_infinitum)
                if division == 'sur' and tipo_tarea[0] == 'D':
                    list_rec.append(ans.get('5f1721afa63c9a750b82048a',0)) # IDENTIFICACION DE NUMERO TELEFONICO EN RED PRINCIPAL, INCLUYE MARCACION *080
                    list_rec.append(ans.get('5f1721afa63c9a750b82048b',0)) # IDENTIFICACION DE NUMERO TELEFONICO EN RED SECUNDARIA, INCLUYE MARCACION *080
                else:
                    list_rec.append(0)
                    list_rec.append(0)
                list_rec.append(ans.get('5f1721afa63c9a750b82048c',0)) # UBICACIÓN DEL CLIENTE Y PRUEBA DE TRANSMISION VDSL EN TERMINAL AEREA
                list_rec.append(ans.get('5f1721afa63c9a750b82048d',0)) # PRUEBA DE TRANSMISION VDSL ADICIONAL EN TERMINAL AREA
                list_rec.append(ans.get('5f90e812f84ca4590ebc5947',0)) # QUEJA
                list_rec.append(ans.get('5f90e812f84ca4590ebc5946',0)) # Migración TBA

                # Línea de cliente básica de 1 par (bajante) (sin modem)
                if is_clase_10_20:
                    val_cliente_basica = ans.get('609bf813b3f4e5c00cf76ee0', 0)
                    val_cliente_basica = 1 if not val_cliente_basica else val_cliente_basica
                    list_rec.append( val_cliente_basica )
                else:
                    list_rec.append(0)
                # Otras varias columnas llegan de las nuevas columnas que se agregaron en la carga de producción, revisar notas en el excel de las estimaciones
                '''
                Validaciones para estimar las A4
                '''
                if record_is_a4:
                    # TODAS LAS A4 SE PAGARAN A PRECIO BAJO
                    for i in range(5, 24):
                        list_rec[ i ] = 0
                    list_rec.extend([1] * 8)
                else:
                    list_rec.extend([0] * 8)

                list_rec.extend([0] * 3)

                if record_is_cfe:
                    for i in range(5, 35):
                        list_rec[ i ] = 0
                # Agrego la columna Tipo de Tarea Clase 10 y 20
                list_rec.append(tipo_tarea if is_clase_10_20 else '')
            else:
                '''
                Empezando análisis de FIBRA...
                '''
                # Para los tipos A4 y FC no se estiman ni liberan
                tipo_instalacion = ans.get('f1054000a020000000000004','')
                metros_bajante = ans.get('f1054000a02000000000007a', ans.get('f1054000a0200000000000d7',''))

                # Metros bajante y tipo de instalación serán aleatorios cuando es solo PIC
                if not connection_id or os_has_minimo:
                    if not tipo_instalacion:
                        tipo_instalacion = random.choice( ['aerea', 'subterranea'] )
                    if not metros_bajante or not all_contratistas_1_0.get(connection_id, {}).get('socio_comercial', ''):
                        metros_bajante = random.choice( ['25', '50', '75'] )

                if not metros_bajante and connection_id > 0:
                    print('>>>>>>>>>>>>>>>>>> Error con el metraje Tecnologia: {0} Division: {1} Folio: {2} Connection id: {3}'.format(tecnologia, division, rec.get('folio'), connection_id))
                    continue
                # Bajante aereo de 25m .- Tipo de Instalación es Aerea y Metros Bajante es 25 entonces lleva valor de 1
                # Se repite lo mismo para 75, 100, 125, 150, 175, 200, 250 y 300 m.
                list_bajante_aereo = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                list_bajante_subterranea = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                dict_mts_x_pos = {'25': 0, '50': 1, '75': 2, '100': 3, '125': 4, '150': 5, '175': 6, '200': 7, '250': 8}
                # MIGRA EXIT VOZ COBRE A VOZ FO CON VISITA .- Siempre lleva 1 en Fibra
                # Si empieza por TS y termina por 7VG lleva 1 y ya no lleva metraje
                migracion_exitosa_voz_cobre_a_fibra = 0
                migracion_exitosa_vsi = ''
                # if re.match(r"^TS.*7VG$|^ts.*7vg$", tipo_tarea):
                if ('7V' in tipo_tarea) and not is_clase_10_20:
                    migracion_exitosa_voz_cobre_a_fibra = 1
                    #print '{} Tipo de tarea lleva 7V y no es de clase 10 y 20 por tanto no se cobra bajante= {}'.format(rec.get('folio'), tipo_tarea)
                else:
                    mts_adicionales = ans.get('f1054000a020000000000bd7',0)

                    # Algunos tipos de tarea solo se paga el vsi y no se considera el metraje
                    if record_is_a4:
                        metros_bajante = '0'
                        mts_adicionales = 0

                    if isinstance(mts_adicionales, str):
                        mts_adicionales = int(mts_adicionales)
                    
                    if metros_bajante:
                        metros_bajante = str(metros_bajante)

                    if tipo_instalacion == 'aerea':
                        if metros_bajante == '300':
                            if mts_adicionales > 0:
                                list_bajante_aereo[9] = 1
                                list_bajante_aereo[10] = mts_adicionales
                            else:
                                list_bajante_aereo[9] = 1
                        elif metros_bajante != '0':
                            if metros_bajante not in dict_mts_x_pos:
                                print('>>>>>>>>>>>>>>>>>> Error con el metraje Tecnologia: {0} Division: {1} Folio: {2}'.format(tecnologia, division, rec.get('folio')))
                                continue
                            list_bajante_aereo[ dict_mts_x_pos[metros_bajante] ] = 1
                    elif tipo_instalacion == 'subterranea':
                        if metros_bajante == '300':
                            if mts_adicionales > 0:
                                list_bajante_subterranea[9] = 1
                                list_bajante_subterranea[10] = mts_adicionales
                            else:
                                list_bajante_subterranea[9] = 1
                        elif metros_bajante != '0':
                            if metros_bajante not in dict_mts_x_pos:
                                print('>>>>>>>>>>>>>>>>>> Error con el metraje Tecnologia: {0} Division: {1} Folio: {2}'.format(tecnologia, division, rec.get('folio')))
                                continue
                            list_bajante_subterranea[ dict_mts_x_pos[metros_bajante] ] = 1
                list_rec.extend(list_bajante_aereo)
                list_rec.extend(list_bajante_subterranea)
                # Estos radiales solo aplican para Fibra Metro

                # Si el tipo de trabajo empieza con FC solo se cobran los bajantes, lo demás ya no
                if tipo_trabajo == 'fc' or record_is_a4 or record_is_cfe:
                    radial_banqueta = ''
                    radial_cepa = ''
                    reparacion_tropezon = ''
                else:
                    radial_banqueta = ans.get('5f1f5efb3198fe9c5ccef32d','') # Radial en banqueta
                    radial_cepa = ans.get('5f1f5efb3198fe9c5ccef32e','') # Radial en cepa libre
                    reparacion_tropezon = ans.get('5f1f5efb3198fe9c5ccef32f','') # Reparacion de tropezon en radial

                # Se integra el concepto Desmontaje en Migracion
                # solo aplica en tipos de tarea TS Clase de Servicio 1L y 2L con etapa 7S, tecnología G ejm ( TS1L7SG y  TS2L7SG)
                # no afecta al 7V ya que sera 7S tons se descarta en automático
                # MAQTEL el unico contratista que tiene otros precios un poco mas altos, tambien te pasare su precio
                desmontaje_en_migracion = 0
                if ('7S' in tipo_tarea) and (clase in ['1L', '2L']) and (tipo_trabajo == 'ts') and ('G' in tipo_tarea):
                    desmontaje_en_migracion = 1
                list_rec.append( desmontaje_en_migracion )

                visitas_adicionales = '' # Visitas adicional / cada insfraestructura nueva
                conexion_bajante_x_fusion = '' # Conexion de bajante de F.O. por fusion

                # INSTALACIÓN DE POSTE DE 25'
                instalacion_poste = ans.get('5f1721afa63c9a750b820487',0)

                list_rec.extend([visitas_adicionales, conexion_bajante_x_fusion, radial_banqueta, radial_cepa, reparacion_tropezon, migracion_exitosa_vsi, migracion_exitosa_voz_cobre_a_fibra, instalacion_poste])
                # ============ Integro los conceptos minimos que se cobran si son a4 ============
                if record_is_a4 and not record_is_cfe:
                    list_rec.extend([1] * 8 + [0] * 3)
                else:
                    list_rec.extend([0] * 11)
                # ====================================================================================
                list_rec.append( ans.get('5ff63afdde49fee5e218a474', '') ) # Dirección
                list_rec.append( ans.get('f1054000a0100000000000d5', '') ) # Distrito
                list_rec.append( ans.get('f1054000a020000000000aa1', '') ) # Terminal
                list_rec.append( ans.get('f1054000a020000000000aa2', '') ) # Puerto
            
            # Area
            list_rec.append( ans.get('f1054000a0100000000000a2', '').upper().replace('_', ' ') )
            # Fecha de Liquidacion
            list_rec.append(fecha_de_liquidacion)
            # Agrego el nombre del Contratista al final de la fila
            list_rec.append( nombre_contratista )
            
            # Para Fibra si el folio ya estuvo en una estimación previa se incluirá el mensaje FOLIO AUDITADO
            if tecnologia == 'fibra':
                list_rec.append( 'FOLIO AUDITADO' if ans.get('f1054000a030000000000012', '') == 'estimacion' else '' )

            list_rec.append( proyecto_os.upper() )
            list_rec.append( validacion_de_sistemas.upper() )
            list_rec.append( socio_comercial )

            records_libs.append(list_rec)

        return records_libs
    
    def liberacion_de_folios(self, current_record):
        p_utils.set_status_proceso(current_record, record_id, 'procesando')
        all_liberaciones = {}
        header_cobre = ["Folio", "Teléfono", "Tipo de tarea", "COPE", "Empresa", "Linea de cliente basica de 1 par (bajante)", "Plusvalia por tramo adicional de 50m. con bajante de 1 par", "Bonificacion por distancia y volumen de 1 a 5 o.s construidas",\
            "Bonificacion por distancia y volumen de 6 a 15 o.s construidas", "Bonificacion por distancia y volumen de 16 a 25 o.s construidas", "Bonificacion por distancia y volumen mas de 25 o.s construidas", \
            "Montaje de puente en distribuidor general", "Construccion o rehabilitacion de cableado interior para 1 aparato", "Cableado interior adicional para el dit con splitter con proteccion (extension)", "INSTALACIÓN DE POSTE DE 25'", \
            "Pruebas de transmision de datos vdsl en roseta de datos con equipo homologado", "Cableado interior 1 aparato y modem para infinitum (dit con splitter con proteccion)", \
            "IDENTIFICACION DE NUMERO TELEFONICO EN RED PRINCIPAL, INCLUYE MARCACION *080", "IDENTIFICACION DE NUMERO TELEFONICO EN RED SECUNDARIA, INCLUYE MARCACION *080", "UBICACIÓN DEL CLIENTE Y PRUEBA DE TRANSMISION VDSL EN TERMINAL AEREA", \
            "PRUEBA DE TRANSMISION VDSL ADICIONAL EN TERMINAL AREA", "QUEJA", "Migración a TBA", "Línea de cliente básica de 1 par (bajante) (sin modem)",\
            "PRUEBAS ELÉCTRICAS DE PAR PRINCIPAL", "PRUEBAS ELÉCTRICAS DE PAR SECUNDARIO", "REPORTE DE IVR, PARA LIQUIDACIÓN DEL SERVICIO", "RECEPCIÓN, MANEJO Y ALMACENAJE DE ROSETAS. (PRECIO POR ROSETA), (2)",\
            "MANEJO, CUSTODIA, ENTREGA Y PUESTA EN SERVICIO DE MODEM EN LA CASA DEL CLIENTE. (SE HACE TODA LA ADMINISTRACIÓN DESDE EL ALMACÉN TELMEX HASTA EL DOMICILIO DEL CLIENTE, SE HACE LA INSTALACIÓN Y PRUEBA DE NAVEGACIÓN EN LA CASA DEL CLIENTE).",\
            "ACTIVACIÓN EXITOSA DE CLARO VIDEO (VÍA TEK o IVR) EN LA CASA DEL CLIENTE", "MONTAJE DE PUENTE NUEVO EN DISTRIBUIDOR GENERAL", "DESMONTAJE DE PUENTE EN DISTRIBUIDOR GENERAL", "INCENTIVO PSR", "REPARACIÓN DE INSTALACIONES", \
            "REPARACION DE INSTALACIONES CON INCENTIVO", "Tipo de tarea clase 10 y 20", "Area", "Fecha de Liquidación", "Contratista", "Proyecto", "Validacion de sistemas", "Socio Comercial"]
        header_fibra = ["Folio", "Teléfono", "Tipo de tarea", "COPE", "Empresa", "Bajante aereo de 25m", "Bajante aereo de 50m", "Bajante aereo de 75m", "Bajante aereo de 100m", "Bajante aereo de 125m", "Bajante aereo de 150m", \
            "Bajante aereo de 175m", "Bajante aereo de 200m", "Bajante aereo de 250m", "Bajante aereo de 300m (incluye dos fusiones)", "Plusvalia", \
            "Bajante subterraneo de 25m", "Bajante subterraneo de 50m", "Bajante subterraneo de 75m", "Bajante subterraneo de 100m", "Bajante subterraneo de 125m", "Bajante subterraneo de 150m", "Bajante subterraneo de 175m", \
            "Bajante subterraneo de 200m", "Bajante subterraneo de 250m", "Bajante subterraneo de 300m (incluye dos fusiones)", "Plusvalia", "Desmontaje en Migración", \
            "Visitas adicional / cada insfraestructura nueva", "Conexion de bajante de F.O. por fusion", "Radial en banqueta", "Radial en cepa libre", "Reparacion de tropezon en radial", \
            "Migracion exitosa de servicio de voz en cobre a voz en fibra optica (VSI)", "MIGRA EXIT VOZ COBRE A VOZ FO CON VISITA", "INSTALACIÓN DE POSTE DE 25'", \

            "PRUEBAS ELÉCTRICAS DE PAR PRINCIPAL", "PRUEBAS ELÉCTRICAS DE PAR SECUNDARIO", "REPORTE DE IVR, PARA LIQUIDACIÓN DEL SERVICIO", "RECEPCIÓN, MANEJO Y ALMACENAJE DE ROSETAS. (PRECIO POR ROSETA), (2)",\
            "MANEJO, CUSTODIA, ENTREGA Y PUESTA EN SERVICIO DE MODEM EN LA CASA DEL CLIENTE. (SE HACE TODA LA ADMINISTRACIÓN DESDE EL ALMACÉN TELMEX HASTA EL DOMICILIO DEL CLIENTE, SE HACE LA INSTALACIÓN Y PRUEBA DE NAVEGACIÓN EN LA CASA DEL CLIENTE).",\
            "ACTIVACIÓN EXITOSA DE CLARO VIDEO (VÍA TEK o IVR) EN LA CASA DEL CLIENTE", "MONTAJE DE PUENTE NUEVO EN DISTRIBUIDOR GENERAL", "DESMONTAJE DE PUENTE EN DISTRIBUIDOR GENERAL", "INCENTIVO PSR", "REPARACIÓN DE INSTALACIONES", "REPARACION DE INSTALACIONES CON INCENTIVO", \

            "Dirección", "Distrito", "Terminal Optica", "Puerto", "Area", "Fecha de Liquidación", \
            "Contratista", "FOLIO AUDITADO", "Proyecto", "Validacion de sistemas", "Socio Comercial"]
        # Se consultan los contratistas que no estan autorizados para Generar Orden de Compra
        contratistas_no_autorizados = self.get_contratistas_no_autorizados_liberacion()
        print('Contratistas no autorizados: ',contratistas_no_autorizados)

        # Se consultan los contratistas que tienen permitido liberar sin pdfs de facturas
        contratistas_autorizados_pdf = self.get_contratistas_autorizados_pdf()
        print('Contratistas autorizados PDF: ',contratistas_autorizados_pdf)
        
        # Solo aplicar las liberaciones para la siguiente lista de contratistas
        connections_in_xls = self.get_only_connections()
        if connections_in_xls.get('error'):
            str_emails_not_found = self.list_to_str( connections_in_xls['error'] )
            return p_utils.set_status_proceso(current_record, record_id, 'error', f"Emails no encontrados, favor de revisar: {str_emails_not_found}")
        only_connections = connections_in_xls.get('result', [])

        # all_contratistas_1_0 = p_utils.get_all_contratistas_from_catalog()
        all_contratistas_1_0 = {}
        answers = current_record['answers']

        # Se procesan las liberaciones iterando folio y tecnologia
        for div in self.all_divisiones:
            tecnologia = div.get('tecnologia')
            division = div.get('division')
            tec_y_div = f'{tecnologia}_{division}'
            print("====================================================")
            print(f'{tecnologia} {division}')
            print("====================================================")

            header = header_cobre if tecnologia == 'cobre' else header_fibra
            
            # IDs de las formas de Orden de Servicio y Liberacion
            id_os, id_lib, id_oc = p_utils.get_id_os(division, tecnologia)

            # Se consultan los registros que se van a liberar
            records_for_liberacion, fols_sin_pdf = self.get_os_for_liberacion(id_os, contratistas_no_autorizados, contratistas_autorizados_pdf, tecnologia, only_connections)
            print('******** Total records:',len(records_for_liberacion))

            records_total_for_libs = self.process_rows_for_libs(records_for_liberacion, all_contratistas_1_0, tecnologia, division)

            kwargs_vars = {}
            if tecnologia == 'fibra':
                response_liberaciones, libs_by_connection = self.make_liberaciones_for_fibra(current_record, record_id, answers, header, records_total_for_libs, tecnologia, division, id_os, id_lib, fols_sin_pdf, **kwargs_vars)
            elif tecnologia == 'cobre':
                response_liberaciones, libs_by_connection = self.make_liberaciones_for_cobre(current_record, record_id, answers, header, records_total_for_libs, tecnologia, division, id_os, id_lib, fols_sin_pdf, **kwargs_vars)
            all_liberaciones[ tec_y_div ] = response_liberaciones
            
            for id_con, dict_libs in libs_by_connection.items():
                all_liberaciones_by_connection.setdefault( id_con, {'errores_libs': {}, 'ok_libs': {}} )
                errores_libs = dict_libs.get('list_errores', [])
                ok_libs = dict_libs.get('list_liberados', [])
                if errores_libs:
                    errores_libs.insert(0, header)
                    all_liberaciones_by_connection[ id_con ][ 'errores_libs' ][ tec_y_div ] = errores_libs
                if ok_libs:
                    ok_libs.insert(0, header)
                    all_liberaciones_by_connection[ id_con ][ 'ok_libs' ][ tec_y_div ] = ok_libs

        """
        # Armando los archivos de error y exitosos
        """
        hojas_errores = {}
        hojas_liberados = {}
        cant_errores = []
        cant_libs = []
        for divTec, infoLibs in all_liberaciones.items():
            name_div_tec = divTec.replace('_',' ')
            errores_libs = infoLibs.get('list_errores', [])
            if errores_libs:
                errores_libs_no_ceros = self.remove_ceros(errores_libs)
                hojas_errores[divTec] = errores_libs_no_ceros
                cant_errores.append( "{} {} folios con error".format(name_div_tec.upper(), len(errores_libs)) )
            cant_libs.append( "{0} {1} folios liberados correctamente".format(name_div_tec.upper(), infoLibs.get('libs_exitosas',0)) )
            if infoLibs.get('msg_error_exception'):
                cant_errores.append( "{} Error al liberar {}".format(name_div_tec.upper(), infoLibs['msg_error_exception']) )
            if infoLibs.get('list_liberados', []):
                libs_exitosas_no_ceros = self.remove_ceros( infoLibs.get('list_liberados', []) )
                hojas_liberados[divTec] = libs_exitosas_no_ceros

        '''
        Empiezo con el envio de correo a los contratistas con sus archivos de liberacion
        '''
        # for c_id, dict_libs in all_liberaciones_by_connection.items():
        #     answers_email = {}
        #     email_contratista = dict_info_connection.get( c_id, {} ).get('email', '')
        #     if email_contratista:
        #         metadata_form = metadata_for_email.copy()
        #         answers_email.update({
        #             '60198329a402aab8a989a805': email_contratista,
        #             '60198329a402aab8a989a80c': 'liberaciones'
        #         })
        #         errores_libs = dict_libs.get('errores_libs', {})
        #         ok_libs = dict_libs.get('ok_libs', {})
        #         if errores_libs:
        #             file_errores_libs_connection = p_utils.upload_error_file(["Folio",], [0,], FORM_ID_EMAIL_CONTRATISTAS, file_field_id='60198329a402aab8a989a80b', content_sheets=errores_libs)
        #             file_errores_libs_connection['60198329a402aab8a989a80b'].update({'file_name':'Folios con errores de liberacion.xlsx'})
        #             answers_email.update( file_errores_libs_connection )
        #         if ok_libs:
        #             file_ok_libs_connection = p_utils.upload_error_file(["Folio",], [0,], FORM_ID_EMAIL_CONTRATISTAS, file_field_id='60198329a402aab8a989a809', content_sheets=ok_libs)
        #             file_ok_libs_connection['60198329a402aab8a989a809'].update({'file_name':'Folios liberados correctamente.xlsx'})
        #             answers_email.update( file_ok_libs_connection )
        #         metadata_form.update( { "answers": answers_email } )
        #         response_create_for_email = lkf_api.post_forms_answers(metadata_form, jwt_settings_key='USER_JWT_KEY')
        #         print "-> response email para {0}: {1}".format(email_contratista, str(response_create_for_email))

        if cant_errores:
            status_final = 'error'
            current_record['answers']['5fd05319cd189468810100c9'] = self.list_to_str(cant_errores)
        else:
            status_final = 'liberaciones_generadas'
        current_record['answers']['5f10d2efbcfe0371cb2fbd39'] = status_final
        current_record['answers']['5fd05319cd189468810100c8'] = self.list_to_str(cant_libs)
        if hojas_errores:
            file_errores_libs = p_utils.upload_error_file(["Folio",], [0,], current_record['form_id'], file_field_id='f2362800a010000000000005', content_sheets=hojas_errores)
            current_record['answers'].update(file_errores_libs)
        if hojas_liberados:
            file_libs = p_utils.upload_error_file(["Folio",], [0,], current_record['form_id'], file_field_id='60148b838ca35fcf1a055854', content_sheets=hojas_liberados)
            file_libs['60148b838ca35fcf1a055854'].update({'file_name':'Folios Liberados Correctamente.xlsx'})
            current_record['answers'].update(file_libs)
        response = lkf_api.patch_record(current_record, record_id, jwt_settings_key='USER_JWT_KEY')

        # Avanza al siguiente paso si es del proceso Automatizado
        automatico_contratistas = current_record['answers'].get('61eff4589ee4743986088809', 'no') != 'no'
        if automatico_contratistas:
            # Se pasa al proceso de Orden de Compra
            self.pass_orden_compra_process()

    def get_record_for_ocs(self):
        record_4_ocs = self.cr.find({
            'form_id': self.FORMA_GENERAR_LIBERACIONES_Y_OCS,
            'deleted_at': {'$exists': False},
            'answers.5f10d2efbcfe0371cb2fbd39': 'en_espera_de_proceso_orden_de_compra',
            'answers.f2362800a0100000000000b2': {'$exists': True}
        }, {'answers': 1, 'form_id': 1, 'folio': 1, '_id': 1}).sort('created_at',-1).limit(1)
        try:
            return record_4_ocs.next()
        except:
            return {}

    def pass_orden_compra_process(self):
        record_for_ocs = self.get_record_for_ocs()
        if record_for_ocs:
            record_for_ocs['properties'] = self.get_metadata_properties('liberacion_de_folios.py', "Generar Orden de Compra", process='Liberaciones automatizadas', folio_carga=self.folio)
            record_for_ocs['answers'].update({
                '5f10d2efbcfe0371cb2fbd39': 'generar_orden_de_compra'
            })
            res_update_process_ocs = lkf_api.patch_record(record_for_ocs, jwt_settings_key='USER_JWT_KEY')
            print('res_update_process_ocs=',res_update_process_ocs)
        else:
            print('NOOOOO hay registro para procesar las OC automatizadas')

if __name__ == '__main__':
    print("--- --- --- Se empieza la liberacion de folios --- --- ---")
    # lkf_obj = base.LKF_Base(settings, sys_argv=sys.argv, use_api=True)
    lkf_obj = Produccion_PCI(settings, sys_argv=sys.argv, use_api=True)

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
    
    lkf_obj.liberacion_de_folios(current_record)