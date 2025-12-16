# -*- coding: utf-8 -*-
import re, sys, datetime, simplejson
import random, os, shutil, wget, zipfile, collections
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from copy import deepcopy
from produccion_pci_utils import Produccion_PCI

from account_settings import *

global forms_dict, TIPOS_TAREAS_ENCONTRADAS

class Produccion_PCI( Produccion_PCI ):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.RECORDS_PASSED = 0
        self.GLOBAL_COMMUNICATION = ""
        self.dir_form_connection = {}
        self.forms_dict = {}
        self.ALL_CONNECTIONS = {}
        self.USERS = {}
        self.TIPOS_TAREAS_ENCONTRADAS = {'fibra':[], 'cobre': []}

        self.list_tareas_solo_vsi = ['TS1L7VGPI', 'TS2L7VGPI']

        self.equivalcens_map_observa = { 'observaciones': ['OBSERVACIONES CLARO VIDEO', 'observaciones claro video', 'obs. claro video', 'observaciones cv']}



    
    def make_copy_os(self,  answers_iasa, form_id_os_iasa, current_folio, os_folio, connection_id, data_os_copy=None ):
        metadata_to_copy_os = self.get_metadata_properties('carga_de_produccion.py', 'ACTUALIZACION', process='PROCESO CARGA DE PRODUCCION HIBRIDO', folio_carga=current_folio)
        if data_os_copy:
            data_os_copy['answers'].update(answers_iasa)
            data_os_copy['properties'] = metadata_to_copy_os
            res_create_os_iasa = lkf_api.patch_record(data_os_copy, jwt_settings_key='USER_JWT_KEY')
        else:
            metadata_os_iasa = lkf_api.get_metadata( form_id_os_iasa )
            metadata_os_iasa.update({
                'folio': os_folio,
                'properties': metadata_to_copy_os,
                'answers': answers_iasa
            })
            res_create_os_iasa = lkf_api.post_forms_answers(metadata_os_iasa, jwt_settings_key='USER_JWT_KEY')
        
        print('res_create_os_iasa=',res_create_os_iasa)
        
        if res_create_os_iasa.get('status_code') == 201:
            new_record = '/api/infosync/form_answer/' + str(res_create_os_iasa.get('json', {}).get('id')) +'/'
            print('*** asignando a:',connection_id)
            response_assign = lkf_api.assigne_connection_records( connection_id, [new_record,], jwt_settings_key='JWT_KEY')
            print('----->response assigne for update:',response_assign)
            return {}
        if res_create_os_iasa.get('status_code') == 202:
            return {}
        return { 
            'error': p_utils.arregla_msg_error_sistema( res_create_os_iasa ) 
        }

    """
    # Cambiar estatus del proceso
    """
    def set_status_proceso(self,  current_record, record_id, status_set, msg='' ):
        current_record['answers']['f1074100a010000000000002'] = msg
        current_record['answers']['f1074100a010000000000005'] = status_set
        response = lkf_api.patch_record(current_record, record_id,  jwt_settings_key='USER_JWT_KEY')
        return str(record_id), response

    """
    # Descomprimir archivos zip para obtener los pdfs y Distómetros
    """
    def get_files_names(self, nueva_ruta, namefile, read_distometros=False):
        files_dir = os.listdir(nueva_ruta)
        error_por_extension = []
        folios_in_zip = {}
        
        extensiones_img = [".jpg",".jpeg",".png", ".JPG", '.JPEG']
        arr_extenciones = extensiones_img + [".pdf", ".PDF"]

        for file_barrido in files_dir:
            ruta_pdf, archivo_pdf = os.path.split(file_barrido)
            namefile_pdf = os.path.splitext(archivo_pdf)[0]
            extension_pdf = os.path.splitext(archivo_pdf)[1]
            
            if namefile_pdf == namefile:
                # Esto para que no tome en cuenta el archivo zip que contiene todos los documentos
                continue
            
            if extension_pdf not in arr_extenciones:
                error_por_extension.append( namefile_pdf )
                continue
            
            if read_distometros and extension_pdf not in extensiones_img:
                error_por_extension.append( archivo_pdf )
                continue

            folios_in_zip.update( { namefile_pdf: nueva_ruta+archivo_pdf } )
        
        if error_por_extension:
            return 'error', error_por_extension

        return folios_in_zip, error_por_extension

    def descomprimeZips(self,  zip_field, current_folio, rutaSave ):
        ruta_destino = "/tmp/"
        filetmp = random.randint(0, 1000)
        nuevo_directorio = "{}_{}_{}/".format(rutaSave, filetmp, current_folio)
        nueva_ruta = ruta_destino + nuevo_directorio
        directorio_temporal = p_utils.crea_directorio_temporal(nueva_ruta)
        if directorio_temporal:
            # Procesesa el zip
            os.chdir(nueva_ruta)
            ruta_zip = zip_field.get('file_url')
            nombre_zip = zip_field.get('file_name')
            ruta_original, archivo_nombre_original = os.path.split(nombre_zip)
            fileoszip = wget.download(ruta_zip,nueva_ruta)
            path, file = os.path.split(fileoszip)
            namefile = os.path.splitext(file)[0]
            extension = os.path.splitext(file)[1]
            try:
                archivo_zip = zipfile.ZipFile(nueva_ruta+file)
            except Exception as e:
                print("++++++++++++++++++++++ Error:",e)
                return 'error', 'El archivo zip está dañado o no es de tipo .zip', nueva_ruta, None

            for i, f in enumerate(archivo_zip.filelist):
                f.filename = p_utils.rename_file_extract(f.filename).replace(' ', '_')
                archivo_zip.extract(f, nueva_ruta)
            
            read_distos = rutaSave == "cargaPorduccionDistometros"
            folios_in_zip, error_por_extension = self.get_files_names( nueva_ruta, namefile, read_distometros=read_distos )
            return folios_in_zip, error_por_extension, nueva_ruta, None
            archivo_zip.close()
            try:
                os.remove(nueva_ruta+file)
            except Exception as e:
                print ("************ error al borrar=",e)
        else:
            return 'error', 'Error al crear el directorio temporal', nueva_ruta, None

    def rmv_psr_created(self, id_connection_assigned, form_id, folio, telefono, area):
        print(f'+++++++++++ Borrando registro de PSR Admin y cuenta padre form_id {form_id} folio {folio}')
        colection_connection = CollectionConnection(id_connection_assigned, settings)
        cr_contratista = colection_connection.get_collections_connection()

        query_to_restore, select_columns = p_utils.query_folio_preorder(form_id, folio, telefono, area)
        rmv_contratista = cr_contratista.delete_one(query_to_restore)
        print("++ Eliminado contratista =", rmv_contratista.deleted_count)

        rmv_admin = cr_admin.delete_one(query_to_restore)
        print("++ Eliminado admin =", rmv_admin.deleted_count)

    def desasignar_registro(self, id_connection_assigned, user_id_old, form_id, folio, telefono, area, answers_before_assign, is_updating_record=False):
        if is_updating_record:
            return
        print('+++++++++++ desasignando el registro original')
        print('------ error en el update desasignando registro form_id {} folio {}'.format(form_id, folio))
        
        colection_connection = CollectionConnection(id_connection_assigned, settings)
        cr_contratista = colection_connection.get_collections_connection()

        query_to_restore, select_columns = p_utils.query_folio_preorder(form_id, folio, telefono, area)
        rmv_contratista = cr_contratista.delete_one(query_to_restore)
        print('+++ rmv_contratista',rmv_contratista)
        unset_conn = cr_admin.update_one(query_to_restore,{"$unset":{'connection_id':''}})
        print('+++ unset_conn:',unset_conn)

        data_set = { 'user_id': user_id_old }
        if answers_before_assign:
            data_set['answers'] = answers_before_assign

        reset_pci = cr_admin.update_one(query_to_restore,{"$set": data_set})
        print('+++ reset_pci',reset_pci)

    def check_os_cobre(self, folio, telefono):
        record_cobre = cr_admin.find_one({
            'form_id': {'$in': [10540, 25927, 25928, 25929]},
            'deleted_at': {'$exists': False},
            'folio': folio,
            'answers.f1054000a010000000000005': telefono,
            'connection_id': {'$exists': False},
            'answers.f1054000a030000000000012': {'$in': ['pendiente', 'reintento']}
        }, {'answers': 1, 'folio': 1, 'form_id': 1})
        return record_cobre

    def create_record_cambio_tec(self,  os_cobre, alfanumerico, alfanumerico_pic, puerto, terminal_optica, current_folio, email_conexion ):
        metadata_cambio = lkf_api.get_metadata(p_utils.FORM_ID_CAMBIO_TECNOLOGIA)
        metadata_cambio['answers'] = {
            '667091a65afe99d4ceba0392': os_cobre['folio'], # Folio
            'f1054000a010000000000005': os_cobre['answers']['f1054000a010000000000005'], # Telefono
            'f1054000a0100000000000d6': os_cobre['answers']['f1054000a010000000000007'], # Expediente del tecnico
            '5eb091915ae0d087df1163de': os_cobre['answers']['5eb091915ae0d087df1163de'], # Tecnico PIC
            'f1054000a010000000000021': os_cobre['answers']['f1054000a0100000000000a4'], # Tipo de tarea
            'f1054000a0100000000000d5': os_cobre['answers']['f1054000a010000000000003'], # Distrito
            'f1054000a010000000000002': os_cobre['answers']['f1054000a010000000000002'].upper().replace('_', ' '), # Cope
            'f1054000a0200000000000a3': alfanumerico_pic,
            self.f['field_no_serie_contratista']: alfanumerico,
            'f1054000a020000000000aa2': puerto, # Puerto
            'f1054000a020000000000aa1': terminal_optica,
            '6670a0a6fe5560837d1cc9bc': 'pendiente',
            '667ffbe32ad9765effae6bf5': email_conexion
        }
        if os_cobre['answers'].get('633d9f63eb936fb6ec9bf580'):
            metadata_cambio['answers']['633d9f63eb936fb6ec9bf580'] = os_cobre['answers']['633d9f63eb936fb6ec9bf580'] # Proyecto
        metadata_agregar_script = {"device_properties":{"system": "SCRIPT","process":"Cambio de Tecnologia", "accion":'Crear registro', "folio carga":current_folio, "archive":"carga_de_produccion_py3.py"}}
        metadata_cambio["properties"] = metadata_agregar_script
        resp_create = lkf_api.post_forms_answers(metadata_cambio, jwt_settings_key='JWT_KEY_ADMIN')
        return resp_create

    def prepare_record(self, record, metadata, pos_field_id, folio, connection_id, RECORDS_PASSED, tecnologia_orden='fibra', hibrida=False, form_id_turno='', current_record = {}, copes_consultados={}, cambio_tecnologia='', records_for_cambio_tec=[], info_cope={}, \
        pos_tipo=0, pos_telefono=0, datos_tecnico={}, permisos_contratista={}, dict_info_connections={}, header_dict={}):
        ###
        ### returns a dict with the instruccions of create or update
        ###
        result = {'create': {}, 'update':{}}
        try:
            telefono_registro = int(record[pos_telefono])
        except Exception as e:
            print(e)
            result['create']['error'] = 'Error en el telefono, favor de revisar'
            return result
        actual_record = False
        descuento15dias = False
        metadata['form_id'] = form_id_turno
        print("*********************** metadata form id: {} folio:{} telefono:{}************".format(metadata['form_id'], folio, telefono_registro))
        if tecnologia_orden in ('cobre', 'hibrida', 'fibra', 'migracion'):
            actual_record = p_utils.check_folio(self.dict_equivalences_forms_id[ metadata['form_id'] ], folio, telefono_registro, info_cope['area'])
        
        if tecnologia_orden == 'fibra' and cambio_tecnologia in ('si', 'sí'):
            print("... ... Folio para Cambio de tecnologia... revisando si existe registro en Cobre y no esta en proceso de cobranza")
            folio_telefono = '{}_{}'.format(folio, telefono_registro)
            if folio_telefono in records_for_cambio_tec:
                result['create']['error'] = 'Este folio y telefono ya está en proceso de Cambio de Tecnologia'
                return result
            os_cobre_found = self.check_os_cobre(folio, telefono_registro)
            if not os_cobre_found and not actual_record:
                result['create']['error'] = 'No se encontro registro en Cobre o está en proceso de liberacion'
                return result
            if os_cobre_found and actual_record:
                result['create']['error'] = 'Este folio y telefono no puede ser cargado porque existe en ambas tecnologias'
                return result
            if os_cobre_found:
                print("Registro encontrado en la forma {} creando registro de Cambio de tecnologia".format(os_cobre_found['form_id']))

                pos_alfanumerico = self.position_field_in_xls( pos_field_id, None, by_field_id=[self.f['field_no_serie_contratista']] )
                alfanumerico = record[pos_alfanumerico] if pos_alfanumerico else ''
                alfanumerico_pic = os_cobre_found['answers'].get('f1054000a020000000000003', '')
                
                puerto = record[ header_dict['puerto'] ] if header_dict.get('puerto') else None
                
                terminal_optica = record[ header_dict['terminal_optica'] ] if header_dict.get('terminal_optica') else ''
                
                resp_create_cambio = self.create_record_cambio_tec( os_cobre_found, alfanumerico, alfanumerico_pic, puerto, terminal_optica, current_record['folio'], dict_info_connections.get(connection_id, {}).get('username', '') )
                print('resp_create_cambio =',resp_create_cambio)
                if resp_create_cambio.get('status_code') != 201:
                    result['create']['error'] = 'Ocurrió un error al crear el registro de cambio de tecnologia'
                    return result
                print("Borrando el registro de OS Cobre ",os_cobre_found['_id'])
                resp_delete_os_cobre = p_utils.delete_record(id_record=os_cobre_found['_id'], jwt_settings_key='JWT_KEY_ADMIN')
                # TTTTTTTTTTTTTTOOOOOOOOOOODO
                result['cambio_tecnologia'] = folio
                return result

        payed_record = p_utils.check_folio_pagado(folio)
        result = {'create': {}, 'update':{}}

        can_create_records = False
        autorizaciones_carga_folio = []
        
        # esto por los cambios de Degradados
        if not pos_tipo:
            tipo_tarea_is_queja = False
        else:
            tipo_tarea_is_queja = str( record[ pos_tipo ] ).upper()[0:2] in ('QI','RI','EI')
        
        if not actual_record:

            """
            Se busca en PSR
            """
            os_in_psr = p_utils.review_psr_exists(folio, telefono_registro)
            # print('+++ +++ +++ os_in_psr =',os_in_psr)

            if not os_in_psr:
                result['create']['error'] = 'Verifica que tu folio sea el correcto y se encuentre liquidado completado en PIC Movil'
                return result

            # if os_in_psr:
            print('OS se encontro en PSR')
            autorizaciones_carga_folio.append('pic')
            answers_psr = os_in_psr.get('answers', {})

            this_record = self.create_order_format(record, metadata, pos_field_id, folio, is_update=False, found_record={}, tecnologia_orden=tecnologia_orden, hibrida=hibrida, form_id_turno=form_id_turno, current_record=current_record,\
                info_cope=info_cope, pos_tipo=pos_tipo, can_create_records=can_create_records, connection_id_base=connection_id, pos_telefono=pos_telefono, autorizaciones_carga_folio=autorizaciones_carga_folio,\
                tipo_tarea_is_queja=tipo_tarea_is_queja, descuentoXdesfase=descuento15dias, datos_tecnico=datos_tecnico, permisos_contratista=permisos_contratista, answers_psr=answers_psr)
            
            if os_in_psr:
                this_record['folio_psr'] = os_in_psr.get('folio')
                this_record['answers']['633d9f63eb936fb6ec9bf580'] = 'psr'
            result['create'] = this_record
        else:
            if payed_record:
                self.RECORDS_PASSED += 1
                self.GLOBAL_COMMUNICATION += 'Folio: %s previamente pagado. '%(folio)
                result['create']['error'] = 'Folio: %s previamente pagado. '%(folio)
                return result

            if actual_record:
                can_be_updated = p_utils.validate_record_status(actual_record)

                # actual_record es el registro de OS en Admin, se valida con la cuenta padre
                other_conexion = p_utils.uploaded_by_other_connection(actual_record, self.account_id)
                #print('puede actualizar por otra conexion ? other_conexion : ',other_conexion,'**** ')
            
            # Bandera para permitir modificar el registro de Admin o no
            continue_to_update = False
            msg_error_folio_vencido = ''

            if  not can_be_updated:
                #Si no se puede actualizar marcalrlo como bloqueado
                self.RECORDS_PASSED += 1
                #self.GLOBAL_COMMUNICATION += 'Folio: %s no puede ser actualizado por el estatus en el que esta actualmente. '%(folio)
                result['update']['error'] = 'Folio: %s no puede ser actualizado por el estatus en el que esta actualmente. '%(folio)
                result['update']['can_upload_pdf'] = True
                return result
            elif other_conexion == 'by_other':
                #aqui la condicion se cambio con other_conexion by_other por by_others para que pasara la condicion
                #print('comentarize lo siguiente para pruebas')
                self.RECORDS_PASSED += 1
                self.GLOBAL_COMMUNICATION += 'Folio duplicado: %s Cargado por otro Contratista. '%(folio)
            elif other_conexion == 'cuenta_padre':
                self.RECORDS_PASSED += 1

                # Hasta aqui se encuentra que el registro original ya lo tiene la Cuenta Padre
                # Revisar si ya existe la copia, si no existe no lo dejo avanzar
                record_copy_os = p_utils.check_folio(metadata['form_id'], folio, telefono_registro, info_cope['area'], in_this_account=True)
                if not record_copy_os:
                    result['update']['error'] = f'Folio: {folio} ya fue cargado por la cuenta padre.'
                    return result
                
                # Existe el registro Copia, se entiende que se va a actualizar información
                # Se revisa que la copia la tenga la conexion que hace la carga
                other_conexion_copy = p_utils.uploaded_by_other_connection(record_copy_os, connection_id)
                if other_conexion_copy == 'by_other':
                    result['update']['error'] = f'Folio: {folio} Cargado por otro Contratista.'
                    return result

                record_copy_os['form_id'] = metadata['form_id']
                continue_to_update = {'exists_copy': True, 'record_copy': record_copy_os}
                # print('+++ +++ record_copy_os =',record_copy_os)
                # stop
            else:
                autorizaciones_carga_folio = p_utils.find_folio_autorizado(folio, actual_record['answers'].get('f1054000a010000000000005', 0), info_cope['division'], tecnologia_orden)
                print('autorizaciones_carga_folio=',autorizaciones_carga_folio)
                if not actual_record.get('connection_id'):
                    field_id_fecha_liq = 'f1054000a02000000000fa02' if tecnologia_orden == 'fibra' else '5a1eecfbb43fdd65914505a1'
                    # fecha_liquidada = actual_record.get('answers',{}).get(field_id_fecha_liq,'')
                    # Se deja de utilizar la fecha de liquidación... se cambia por la fecha de creacion
                    fecha_liquidada = actual_record['created_at'].strftime("%Y-%m-%d")
                    if fecha_liquidada:
                        date_fecha_liquidada = datetime.datetime.strptime(fecha_liquidada, '%Y-%m-%d')
                        fecha_actual = datetime.datetime.now()
                        diff_dates = fecha_actual - date_fecha_liquidada
                        dias_transcurridos = diff_dates.days
                        if dias_transcurridos > self.dias_para_marcar_desfase and not autorizaciones_carga_folio:
                            descuento15dias = True
                            msg_error_folio_vencido = 'Folio cargado correctamente, recuerda que tienes 14 días después de la fecha de liquidación para cargar tu folio, de lo contrario tendrá un descuento del 20% por gastos administrativos por cargas desfasadas'
                else:
                    can_create_records = True
                
                # Buscando información del COPE del registro que ya está creado
                cope_record_exists = actual_record.get('answers', {}).get('f1054000a010000000000002', '').replace('_', ' ')
                if not copes_consultados.get( cope_record_exists ):
                    reg_catalogo = p_utils.get_cope_in_catalogo( cope_record_exists, jwt_settings_key='JWT_KEY_ADMIN' )
                    if len(reg_catalogo) != 1:
                        result['update'] = {'error': 'No se encontró el cope del registro en el catálogo o está duplicado'}
                        return result
                    copes_consultados[ cope_record_exists ] = reg_catalogo
                info_cope = copes_consultados[ cope_record_exists ][0]
                if not info_cope:
                    result['update'] = {'error': 'Error al encontrar el cope, favor de revisar con soporte'}
                    print("fallo en los copes consultados para:",cope_record_exists)
                    return result
                # ---------------------------------------------------------
                # Si el registro está marcado como "Asignado a IASA" no se permite la carga
                if actual_record.get('answers', {}).get('620bdcae41e4154ec993bf0c', '') == 'sí':
                    # Debe estar autorizado para que pueda ser cargado
                    grupo_historial = actual_record.get('answers', {}).get('f1054000a030000000000e20', [])
                    all_status_os = [h['f1054000a030000000000e22'] for h in grupo_historial if h.get('f1054000a030000000000e22')]
                    if 'Autorizado IASA' not in all_status_os:
                        result['update'] = {'error': 'Este folio no puede ser cargado ya que fue Asignado a IASA'}
                        return result
                
                continue_to_update = {'exists_copy': False}

            
            if continue_to_update:
                answers_before_assign = deepcopy( actual_record['answers'] )
                this_record = self.create_order_format(record, metadata, pos_field_id, folio, is_update=True, found_record=actual_record, tecnologia_orden=tecnologia_orden, hibrida=hibrida, form_id_turno=form_id_turno, current_record=current_record,\
                    info_cope=info_cope, pos_tipo=pos_tipo, can_create_records=can_create_records, connection_id_base=connection_id, pos_telefono=pos_telefono, autorizaciones_carga_folio=autorizaciones_carga_folio,\
                    tipo_tarea_is_queja=tipo_tarea_is_queja, descuentoXdesfase=descuento15dias, datos_tecnico=datos_tecnico, permisos_contratista=permisos_contratista)
                

                # print('\n\n this_record =',this_record)
                # stop

                if other_conexion == 'assigne' and not this_record.get('error'):
                    new_record = '/api/infosync/form_answer/' + str(actual_record['_id']) +'/'
                    print('*** asignando a:',connection_id)
                    print('registro original se asigna a ',settings.config['ACCOUNT_ID'])
                    response_assign = lkf_api.assigne_connection_records( settings.config['ACCOUNT_ID'], [new_record,], jwt_settings_key='JWT_KEY_ADMIN')
                    print('----->response assigne for update:',response_assign)
                    this_record.update({'assigned_to': connection_id, 'user_id_old': actual_record.get('user_id')})
                this_record['answers']['_id'] = str(actual_record['_id'])
                this_record['_id'] = str(actual_record['_id'])
                this_record['folio_record_admin'] = actual_record['folio']
                this_record['answers_before_assign'] = answers_before_assign
                this_record.update( continue_to_update )
                result['update'] = this_record
                if msg_error_folio_vencido:
                    if result['update'].get('alerts', []):
                        result['update']['alerts'].append(msg_error_folio_vencido)
                    else:
                        result['update']['alerts'] = [msg_error_folio_vencido,]

        return result

    def eval_tipo_tarea_queja(self, tipo_tarea, area):
        if str(tipo_tarea).upper() in ["QILPZOM", "QI1LPZOM", "QI1LPZOS", "QILMLPZON", "QI1LPOZS", "QI1LPZOH", "R12LPZOT"]:
            if area in ['chiapas', 'tabasco']:
                return True
            else:
                return False
        return True

    def create_order_format(self, record, metadata, pre_os_field_id, folio, is_update=False, found_record={}, tecnologia_orden='fibra', hibrida=False, form_id_turno='', current_record={}, info_cope={}, pos_tipo=None, \
        can_create_records=False, connection_id_base=0, pos_telefono=None, autorizaciones_carga_folio=[], tipo_tarea_is_queja=False, descuentoXdesfase=False, datos_tecnico={}, permisos_contratista={}, answers_psr={}):
        print("----->info_cope",info_cope)
        answer = found_record.get('answers',{})
        proyecto_record = answer.get('633d9f63eb936fb6ec9bf580', '')
        is_cfe = proyecto_record == 'cfe'
        cargado_desde_pic = answer.get('5eb0326a9e6fda7cb11163f1','')
        tecnico_pic = answer.get('5eb091915ae0d087df1163de','')
        is_cargado_desde_pic = (cargado_desde_pic == 'sí' or tecnico_pic != '')
        cobro_minimo = (answer.get('5fc9269ce5363f7e3b9e3867', 'no') != 'no')
        ###
        ### Craete new record
        ###
        this_record = {
            'folio': found_record.get('folio')
        }
        record_existente = 'si' if answer else ''
        error = []
        alerts = []
        aerea = subterranea = None
        if tecnologia_orden == 'cobre':
            field_id_metraje = 'f1054000a020000000000007'
            field_id_expediente = 'f1054000a010000000000007'
            id_field_tipo_tarea = 'f1054000a0100000000000a4'
            field_id_fecha_liq = '5a1eecfbb43fdd65914505a1'
            answer['5a209f2cf851c21f9e2b7f50'] = 'pci'
            answer['f1054000a030000000000013'] = 'en_proceso'
        elif tecnologia_orden == 'fibra':
            field_id_metraje = 'f1054000a0200000000000d7'
            field_id_expediente = 'f1054000a0100000000000d6'
            id_field_tipo_tarea = 'f1054000a010000000000021'
            field_id_fecha_liq = 'f1054000a02000000000fa02'
            answer['f1054000a030000000000013'] = 'en_proceso'


        if answers_psr:
            # print('-- --- -- --- --- --- --- answers_psr =',json.dumps(answers_psr, indent=4)
            answer.update({
                'f1054000a010000000000002': answers_psr.get('f1054000a010000000000002').lower().replace(' ', '_'), # : info_cope.get('cope',''), # cope
                'f1054000a0100000000000a2': answers_psr.get('66eb90ae4a3470f509f0129e').lower().replace(' ', '_'), # : info_cope.get('area',''), # area
                'f1054000a0100000000000c2': answers_psr.get('66eb90ae4a3470f509f0129d').lower().replace(' ', '_'), # : info_cope.get('subdireccion',''), # subdireccion
                'f1054000a0100000000000b2': answers_psr.get('66eb90ae4a3470f509f0129c').lower().replace(' ', '_'), # : division, # Division
                '5eb091915ae0d087df1163de': answers_psr.get('5eb091915ae0d087df1163de'), #: tecnico,
                'f1054000a010000000000005': answers_psr.get('f1054000a010000000000005'), #: telefono
                field_id_expediente: answers_psr.get('f1054000a0100000000000d6'),
                id_field_tipo_tarea: answers_psr.get('f1054000a010000000000021'),
                field_id_fecha_liq: answers_psr.get('66eb905a9abafdd48af01241'),
            })
            if tecnologia_orden == 'fibra':
                answer.update({
                    'f1054000a0100000000000d5': answers_psr.get('f1054000a0100000000000d5'),
                    'f1054000a0200000000000a3': answers_psr.get('f1054000a0200000000000a3')
                })
            is_cargado_desde_pic = True

        bonificaciones_cases_found = 0
        bonificaciones_added = 0
        metraje_cargado = 0

        tipo_tarea_record = answer.get(id_field_tipo_tarea, '')

        if folio:
            if not tipo_tarea_record:
                tipo_tarea_record = record[pos_tipo]
            clase_tipo_tarea = str(tipo_tarea_record)[2:4]
            is_clase_10_20 = clase_tipo_tarea in ['10', '20']
        else:
            is_clase_10_20 = False
        if is_clase_10_20:
            answer['609bf813b3f4e5c00cf76ee0'] = 1
        mtts_before = {}
        pos_expediente = pre_os_field_id.pop('pos_expediente')

        plain_data_cope = info_cope.get('plain_data', {})
        # plain_data_contratista = permisos_contratista.get('plain_data', {})
        kwargs_to_expediente = {
            'cope': plain_data_cope.get('5d641731ddd3adcc24778a9d'),
            'abreviatura_cope': plain_data_cope.get('5d641731ddd3adcc24778a9e'),
            'area': plain_data_cope.get('5d641731ddd3adcc24778a9c'),
            'subdireccion': plain_data_cope.get('5d641731ddd3adcc24778a9b'),
            'division_pic_movil': plain_data_cope.get('5d77bd96eeb32658ce522ec4'),
            'division': plain_data_cope.get('5d641731ddd3adcc24778a9a'),
            'nombre_tecnico': tecnico_pic,

            # Datos del contratista
            'nombre_contratista': permisos_contratista.get('nombre_contratista'),
            'razon_social': permisos_contratista.get('razon_social'),
            'division_contratista': permisos_contratista.get('division_contratista'),
            'telefono_contratista': permisos_contratista.get('telefono_contratista'),
            'correo_contratista': permisos_contratista.get('correo_contratista'),
            'socio_comercial': permisos_contratista.get('socio_comercial'),
            'current_record_folio': current_record['folio'],
            'info_iasa': permisos_contratista.get('info_iasa')
        }

        for pos, element in pre_os_field_id.items():
            lbl = element.get('label','')
            if is_cargado_desde_pic:
                if lbl in ['Tipo de Tarea', 'Teléfono', 'Telefono', 'Fecha Liquidada', 'Fecha de Liquidacion']:
                    continue
                elif lbl == 'Distrito' and (answer.get('f1054000a0100000000000d5',False) or answer.get('f1054000a010000000000003',False)):
                    continue
                elif lbl in ['Alfanumérico', 'Modem - Numero de Serie']: # elif lbl == 'Alfanumérico' and answer.get('f1054000a0200000000000a3',False) and len(str(answer.get('f1054000a0200000000000a3', ''))) == 12:
                    continue
            if str(pos).find('-') > 0:
                position = int(pos.split('-')[0])
            else:
                position = pos

            '''
            * Validaciones para las Bonificaciones, solo debe hacer 0-1 y en una de las Bonificaciones
            '''
            # Se manda mensaje de error si trae dato en POSTE 25' pero no está autorizado
            if lbl in ["Instalacion de Poste de 25' en cualquier tipo de Terreno", "INSTALACIÓN DE POSTE DE 25'"]:
                if "instalacion_de_poste_de_25'_en_cualquier_tipo_de_terreno" not in autorizaciones_carga_folio and record[position]:
                    error.append('Tienes que enviar correo de autorización de cope, cualquier duda contacta soporte')
            
            
            # ToDo : Mejorar estooooooooooooo
            if lbl in ["Bonificacion por distancia y volumen de 1 a 5 o.s construidas","Bonificacion por distancia y volumen de 6 a 15 o.s construidas", "Bonificacion por distancia y volumen de 16 a 25 o.s construidas","Bonificacion por distancia y volumen mas de 25 o.s construidas"]:
                if info_cope.get('aplica_bonificaciones', '') == 'no' or tipo_tarea_is_queja or cobro_minimo:
                    record[position] = 0
                if record[position]:
                    bonificaciones_cases_found += 1
                    bonificaciones_added += 1
                    if bonificaciones_cases_found > 1:
                        error.append('Solo puede agregar una Bonificacion')
                    if (type(record[position]) != int) or (record[position] not in [0,1]):
                        error.append('El valor de la Bonificación debe ser 0 ó 1')
                else:
                    answer.pop( element.get('field_id', ''), None )
            elif lbl in ["Montaje de puente en distribuidor general", "INSTALACIÓN DE POSTE DE 25'"]:
                if tipo_tarea_is_queja:
                    record[position] = 0
                elif cobro_minimo:
                    record[position] = 2 if lbl == "Montaje de puente en distribuidor general" else 0
                if record[position]:
                    bonificaciones_added += 1
                    if record[position] not in [0,1,2]:
                        error.append('{} El valor debe ser entre 0 y 2'.format(lbl))
                else:
                    answer.pop( element.get('field_id', ''), None )
            elif lbl in ["Pruebas de transmision de datos vdsl en roseta de datos con equipo homologado", "IDENTIFICACION DE NUMERO TELEFONICO EN RED PRINCIPAL, INCLUYE MARCACION *080", "IDENTIFICACION DE NUMERO TELEFONICO EN RED SECUNDARIA, INCLUYE MARCACION *080", "UBICACIÓN DEL CLIENTE Y PRUEBA DE TRANSMISION VDSL EN TERMINAL AEREA", "PRUEBA DE TRANSMISION VDSL ADICIONAL EN TERMINAL AREA"]:
                if tipo_tarea_is_queja or cobro_minimo:
                    record[position] = 0
                if record[position]:
                    bonificaciones_added += 1
                    if record[position] not in [0,1]:
                        error.append('{} El valor debe ser entre 0 y 1'.format(lbl))
                else:
                    answer.pop( element.get('field_id', ''), None )
            elif lbl in ["Radial en banqueta", "Radial en cepa libre"]:
                if tipo_tarea_is_queja or cobro_minimo:
                    record[position] = 0
                if record[position]:
                    bonificaciones_added += 1
                    if (type(record[position]) != int) or (record[position] not in range(0,41)):
                        error.append('{} El valor debe ser entre 0 y 40'.format(lbl))
                else:
                    answer.pop( element.get('field_id', ''), None )
            elif lbl in ["Reparacion de tropezon en radial"]:
                if tipo_tarea_is_queja or cobro_minimo:
                    record[position] = 0
                if record[position]:
                    bonificaciones_added += 1
                    if (type(record[position]) != int) or (record[position] not in range(0,21)):
                        error.append('{} El valor debe ser entre 0 y 20'.format(lbl))
                else:
                    answer.pop( element.get('field_id', ''), None )
            elif lbl in ["Cableado interior 1 aparato y modem para infinitum (dit con splitter con proteccion)"]:
                if tipo_tarea_is_queja:
                    record[position] = 0
                if pos_tipo and str(record[pos_tipo])[:2].upper() != 'TE' and not tipo_tarea_is_queja:
                    record[position] = 1
                    bonificaciones_added += 1
                if is_clase_10_20:
                    if record[position]:
                        alerts.append('El concepto Cableado interior 1 aparato y modem para infinitum (dit con splitter con proteccion) NO está permitido para las clases 10 y 20')
                    record[position] = 0
                if not record[position]:
                    answer.pop( element.get('field_id', ''), None )
                if cobro_minimo:
                    record[position] = 1
            elif lbl in ["Cableado interior adicional para el dit con splitter con proteccion (extension)", "Migración TBA"]:
                if tipo_tarea_is_queja or cobro_minimo:
                    record[position] = 0
                if not record[position]:
                    answer.pop( element.get('field_id', ''), None )
            elif lbl in ["QUEJAS"]:
                if tipo_tarea_is_queja:
                    record[position] = 1
                if record[position]:
                    if bonificaciones_added > 0:
                        error.append('No puede mezclar QUEJAS con otros conceptos')
                else:
                    answer.pop( element.get('field_id', ''), None )
            if lbl == "Construccion o rehabilitacion de cableado interior para 1 aparato":
                if is_clase_10_20:
                    record[position] = 1
            if lbl in ["Instalacion de Poste de 25' en cualquier tipo de Terreno", "INSTALACIÓN DE POSTE DE 25'"]:
                if "instalacion_de_poste_de_25'_en_cualquier_tipo_de_terreno" not in autorizaciones_carga_folio:
                    value_to_add = 0 if lbl == "INSTALACIÓN DE POSTE DE 25'" else ''
                    record[position] = value_to_add
            
            '''
            * Termino validaciones para Bonificaciones
            '''
            if element['scritp_type'] == 'folio' and type(position) == int:
                this_record.update({'folio':str(folio) })
                if len(str(folio)) != 8:
                    this_record.update({'error':  ['Longitud de folio diferente de 8',]})
            elif element['scritp_type'] == 'etapa' and type(position) == int:
                if record[position]:
                    this_record.update({'etapa': str(record[position])})
            elif element['scritp_type'] == 'contratista' and type(position) == int:
                if record[position]:
                    connection_id = p_utils.get_connection_id_by_email(str(record[position]).lower(), tecnologia_orden, form_id_turno, self.ALL_CONNECTIONS)
                    if connection_id:
                        this_record.update({'connection_id': connection_id})
                    if str(record[position]) and not connection_id:
                        #this_record.update({'error':  ['Correo de conexion equivocado o forma de %s no compartida'%(tecnologia_orden),]})
                        error.append('Correo de conexion equivocado o forma de %s no compartida'%(tecnologia_orden))
            elif element['scritp_type'] == 'tipo' and type(position) == int:
                if record[position]:
                    this_record.update({'tipo': str(record[position])[:2].upper()})
                    answer.update({"f1054000a0100000000000a1": str(record[position])[:2].upper()})
            elif element['scritp_type'] == 'clase' and type(position) == int:
                if record[position]:
                    this_record.update({'clase': str(record[position])})
            elif element['scritp_type'] == 'usuario_pic_reporta' and type(position) == int:
                if record[position]:
                    this_record.update({'usuario_pic_reporta': str(record[position])})
                    answer['f1054000a030000000000111'] = str(record[position])
            elif element['scritp_type'] in ['aerea', 'subterranea'] and type(position) == int:
                type_mts = element['scritp_type']
                mts = record[position]
                if isinstance(mts, str):
                    mts = mts.strip()
                
                mts = mts if mts else 0
                try:
                    mts = int(mts)
                except Exception as e:
                    print(e)
                    error.append('Valor no aceptado en el metraje: {}'.format(mts))

                if not mtts_before:
                    mtts_before = {type_mts: mts}
                else:
                    current_mtts = mts if mts else 0
                    print('mtts_before=',mtts_before)
                    print('current_mtts=',current_mtts)
                    val_before = list( mtts_before.values() )

                    # No se puede permitir intentar cargar dos metrajes al mismo tiempo
                    if val_before[0] and current_mtts:
                        error.append("No se pueden cargar dos metrajes diferentes, favor de revisar")

                    if val_before and val_before[0] and val_before[0] > current_mtts:
                        type_mts = list(mtts_before.keys())[0]
                        mts = val_before[0]
                    # Se permite cargar metrajes de cero solo para los tipos de tarea que solo cobran VSI
                    if not mts and tipo_tarea_record not in self.list_tareas_solo_vsi:
                        print('requiere metraje 1')
                        error.append("Se requiere metraje")
                
                aerea = type_mts == 'aerea'
                subterranea = type_mts == 'subterranea'
                if aerea:
                    this_record.update({'aerea': str(mts)})
                if cobro_minimo:
                    mts = 75
                # Hay tipos de tarea donde solo se cobra el VSI por tanto el metraje se deja como 0
                if tecnologia_orden == 'fibra':
                    if tipo_tarea_record in self.list_tareas_solo_vsi:
                        mts = 0
                
                if mts or mts == 0:
                    metraje_cargado = mts
                    answer.update({'f1054000a020000000000004':type_mts})
                    answer.update(p_utils.set_metros_bajante(mts, tecnologia_orden, hibrida, field_id_metraje, error=error))
            elif element['scritp_type'] == 'tecnico' and type(position) == int:
                field_id_nombre_tecnico = 'f1054000a02000000000fa04'
                if tecnologia_orden == 'cobre':
                    field_id_nombre_tecnico = '59e1280bb43fdd7cd6fc9f63'
                # Si el registro ya tiene Clave del Técnico ya no se editará ni la clave ni el nombre
                if not answer.get('f1054000a02000000000fb04', False):
                    if datos_tecnico:
                        answer[field_id_nombre_tecnico] = datos_tecnico.get('nombre', '')
                        answer['f1054000a02000000000fb04'] = datos_tecnico.get('clave', '')
                    else:
                        folio_tecnico = record[position]
                        folio_tecnico_inicial = ''
                        if folio_tecnico != '':
                            try:
                                folio_tecnico_inicial = folio_tecnico[0:2]
                            except Exception as e:
                                print(e)
                                folio_tecnico_inicial = folio_tecnico
                            if folio_tecnico_inicial == "T-":
                                nombre_tecnico_recuperado = p_utils.get_nombre_tecnico(folio_tecnico)
                                if nombre_tecnico_recuperado.strip() != '':
                                    answer[field_id_nombre_tecnico] = nombre_tecnico_recuperado
                                    answer['f1054000a02000000000fb04'] = folio_tecnico
                                else:
                                    this_record.update({'error': ['La clave del tecnico es incorrecta o no tiene nombre la clave del tecnico en el Listado de Tecnicos', ]})
                            else:
                                answer[field_id_nombre_tecnico] = folio_tecnico
                        else:
                            error.append('Debe llevar clave o nombre del tecnico')

            elif element['scritp_type'] == 'fecha_de_asignacion' and type(position) == int:
                fecha_asignacion_rec = record[position]
                try:
                    fecha_validada = p_utils.compara_fecha_rango(fecha_asignacion_rec)
                    if not fecha_validada:
                        error.append('La fecha de asignacion no es valida ya que es menor al 2019 o mayor al dia de hoy')
                except Exception as e:
                    print('======================= FALLO EN LA FECHA',e)
                    error.append('La fecha de Asignacion no es formato de fecha correcto {}'.format(str(e)))

            elif element['scritp_type'] == 'fecha_de_liquidacion' and type(position) == int:
                fecha_liquidacion_rec = record[position]
                if fecha_liquidacion_rec != '':
                    try:
                        fecha_validada = p_utils.compara_fecha_rango(fecha_liquidacion_rec)
                        if not fecha_validada:
                            error.append('La fecha de liquidacion no es valida ya que es menor al 2019 o mayor al dia de hoy')
                        else:
                            print("fecha liquidacion :",fecha_liquidacion_rec)
                    except Exception as e:
                        print(e)
                        error.append('La fecha de Liquidacion no es formato de fecha correcto')

            elif element['scritp_type'] == 'cope' and type(position) == int:
                cope_recu = record[position]

            elif element['scritp_type'] == 'num_serie' and type(position) == int:
                if record[position]:
                    answer[self.f['field_no_serie_contratista']] = record[position]
            if type(position) != int:
                if position not in ['clase','tipo','tipo de tarea', 'etapa']:
                    answer.update(lkf_api.make_infosync_json(position, element, best_effort=True))
            else:
                try:
                    if record_existente == 'si':
                        if element.get('label') and element['label'] not in ['Telefono', 'Teléfono','Tecnico','Division','AREA','COPE','Cable Par','Modem - Numero de Serie','Tipo de Tarea','Fecha de Liquidacion','Expediente del Tecnico','Expediente del Técnico','Expediente Del Tecnico']:
                            if record[position] and isinstance(record[position], str):
                                record[position] = record[position].encode('utf8')
                                if re.search(ILLEGAL_CHARACTERS_RE, str(record[position])):
                                    print("********************* cadena no aceptada")
                                    record[position] = re.sub(ILLEGAL_CHARACTERS_RE,'?', str(record[position]))
                                    error.append('Caracteres no aceptados en: %s'%(str(record[position])))
                                else:
                                    record[position] = record[position].decode('utf8')
                                    answer.update(lkf_api.make_infosync_json(record[position], element, best_effort=True))
                            else:
                                try:
                                    answer.update(lkf_api.make_infosync_json(record[position], element, best_effort=True))
                                except Exception as e:
                                    print('[ERROR] al procesar el valor =',e)
                                    error.append(f"Error al procesar el valor {record[position]} para el campo {element['label']}")
                    else:
                        if record[position] and isinstance(record[position], str):
                            if element.get('label') and element['label'] == 'Tipo de Tarea':
                                
                                # Valido el tipo de tarea con el catálogo
                                tipo_tarea_mayus = tipo_tarea_record or record[position].upper().strip()
                                if tipo_tarea_mayus not in TIPOS_TAREAS_ENCONTRADAS[ tecnologia_orden ]:
                                    tipo_tarea_in_catalog = p_utils.find_tipo_tarea_catalog(tipo_tarea_mayus, tecnologia_orden, jwt_settings_key='JWT_KEY_ADMIN')
                                    if tipo_tarea_in_catalog:
                                        TIPOS_TAREAS_ENCONTRADAS[tecnologia_orden].append( tipo_tarea_mayus )
                                else:
                                    tipo_tarea_in_catalog = True
                                
                                if not tipo_tarea_in_catalog:
                                    error.append('El Tipo de Tarea no se encontró en el catálogo Tipos de Tarea Factibles')
                                else:
                                    record[position] = record[position].upper()
                            record[position] = record[position].encode('utf8')
                            if re.search(ILLEGAL_CHARACTERS_RE, str(record[position])):
                                print("********************* cadena no aceptada")
                                record[position] = re.sub(ILLEGAL_CHARACTERS_RE,'?', str(record[position]))
                                error.append('Caracteres no aceptados en: %s'%(str(record[position])))
                            else:
                                record[position] = record[position].decode('utf8')
                                # Si el answers ya lleva valor en el campo que se va a integrar pues ya no tiene caso integrar lo del excel
                                if not answer.get( element.get('field_id') ):
                                    answer.update(lkf_api.make_infosync_json(record[position], element, best_effort=True))
                        else:
                            answer.update(lkf_api.make_infosync_json(record[position], element, best_effort=True))
                except Exception as e:
                    etiqueta_campo = element.get('label', '')
                    error.append('Favor de revisar bien el formato del archivo, no es posible convertir alguna celda del campo %s. Error: %s'%(etiqueta_campo, e.message))

        answer.update(p_utils.set_status_values(answer, is_update ))


        # Agrego el default 2 para cobro minimo en la Plusvalia de Cobre
        if tecnologia_orden == "cobre" and cobro_minimo:
            answer['5d324d8783e66ebc7d26f412'] = 2

        # Si la carga tiene desfase de 15 dias entonces se marca la OS
        if descuentoXdesfase and not is_cfe:
            answer['601c7ae006478d9cbee17e00'] = 'sí'


        # Otro check si el estatus de orden es false pues que ponga el default LIQUIDADA
        if not answer.get('f1054000a030000000000002'):
            answer['f1054000a030000000000002'] = 'liquidada'
        if not answer.get('5f0e23eaca2ca23aa12f21a9'):
            answer['5f0e23eaca2ca23aa12f21a9'] = p_utils.get_date_now()

        estatus_de_orden = answer.get('f1054000a030000000000002','')
        if estatus_de_orden == 'liquidada':
            if not aerea and not subterranea:
                if tecnologia_orden != 'cobre':
                    error.append('El Folio no tiene metraje trabajado')
                else:
                    answer['f1054000a020000000000007'] = 0
                    answer['f1054000a020000000000004'] = 'aerea'
                if tecnologia_orden == 'fibra':
                    alfanumerico = str(answer.get(self.f['field_no_serie_contratista'],''))
                    if not is_cargado_desde_pic:
                        if len(alfanumerico) != 12:
                            error.append('Longitud de alfanumerico diferente de 12')
                    terminal_optica = answer.get('f1054000a020000000000aa1','')
                    if terminal_optica:
                        try:
                            regex = re.compile('[a-z]|[A-Z]')
                            if len(terminal_optica) != 2:
                                error.append('Terminal Optica debe de contener 2 caracteres')
                            elif not regex.findall(terminal_optica[0]):
                                error.append('EL primer digito de la terminal optica debe de ser un caracter A-Z')
                            elif terminal_optica[1] not in '1234567890':
                                error.append('EL segundo digito de la terminal optica debe de ser un numero 0-9')
                        except Exception as e:
                            print(e)
                            print('pass sin terminal optica')
            if tecnologia_orden == 'fibra' and metraje_cargado > 300:
                direccion = answer.get('5ff63afdde49fee5e218a474','').strip()
                if not direccion:
                    error.append('Debe agregar información en la columna Dirección únicamente para folios FTTH con mas de 300 mts')
            
            if tecnologia_orden == 'cobre' and metraje_cargado > 300:
                permiso_cobre_mayor_300 = permisos_contratista.get('cobre_mayor_a_300', '')
                if not permiso_cobre_mayor_300 or permiso_cobre_mayor_300.lower() == 'no':
                    if 'cobre_mayor_a_300' not in autorizaciones_carga_folio:
                        error.append('Se requiere autorización para poder reportar este metraje')

        id_connection_for_exp = connection_id_base if connection_id_base else this_record.get('connection_id', current_record['user_id'])
        num_expediente = answer.get(field_id_expediente,0)

        if not can_create_records:
            if record_existente == 'si' or answers_psr:
                if 'expediente' not in autorizaciones_carga_folio:
                    permiso_expediente_contratista = 'si' if str(tecnico_pic).lower().strip() == 'pisaplex' else permisos_contratista.get('expediente', '')
                    if not permiso_expediente_contratista or permiso_expediente_contratista.lower() == 'no':

                        is_in_listado_tecnicos = p_utils.carga_prod_find_expediente(id_connection_for_exp, settings.config['ACCOUNT_ID'], num_expediente, **kwargs_to_expediente)
                        if not is_in_listado_tecnicos:
                            # Validar que el expediente esté en los Expedientes de Tecnicos en Admin y IASA, si no existe en alguno, se manda error
                            is_in_listado_tecnicos = p_utils.find_in_lista_tecnicos( 0, num_expediente, find_by_expediente=True )
                            print('-- -- -- -- response is_in_listado_tecnicos',is_in_listado_tecnicos)
                            # print('is_in_listado_tecnicos =',is_in_listado_tecnicos)
                            is_in_listado_tecnicos_admin = p_utils.find_in_lista_tecnicos( settings.config['ACCOUNT_ID'], num_expediente, find_in_admin=True )
                            print('-- -- -- -- response is_in_listado_tecnicos_admin',is_in_listado_tecnicos_admin)
                            list_expediente_not_found = []
                            if not is_in_listado_tecnicos_admin:
                                list_expediente_not_found.append( f'Expediente {num_expediente} no encontrado en Expedientes de Técnicos Admin' )
                            if not is_in_listado_tecnicos:
                                list_expediente_not_found.append( f'Expediente {num_expediente} no encontrado en Expedientes de Técnicos IASA' )
                            if list_expediente_not_found:
                                error.append( self.list_to_str(list_expediente_not_found) )

                            # stop

        # Si el folio está marcado como CFE se va a requerir el valor para el campo Zona
        if is_cfe and not answer.get('633d9f63eb936fb6ec9bf581'):
            error.append('El registro está marcado como CFE por lo que se requiere indicar si es Rural o Urbana')
        if not is_cfe: 
            if answer.get('633d9f63eb936fb6ec9bf581'):
                answer.pop('633d9f63eb936fb6ec9bf581')
            if proyecto_record and proyecto_record not in ['psr', 'degradado', 'contingencia', 'queja_especial']:
                answer.pop('633d9f63eb936fb6ec9bf580')
        
        this_record.update(metadata)

        # Para fibra hay tipos de tarea donde no se paga el metraje y solo se paga el vsi
        if tecnologia_orden == 'fibra':
            if tipo_tarea_record in self.list_tareas_solo_vsi:
                answer.update({
                    'f1054000a020000000000022': 'vsi'
                })
                alerts.append('Para este tipo de Tarea solo se permite cobrar el VSI')
            # Para Fibra siempre se requiere el Tipo de Material
            if not answer.get('6346f10c24cc48504673c5d9'):
                error.append('Se debe indicar el Tipo de Material')
        if info_cope and not is_cargado_desde_pic:
            answer.update({
                'f1054000a0100000000000b2':info_cope['division'],
                'f1054000a0100000000000c2':info_cope['subdireccion'],
                'f1054000a0100000000000a2':info_cope['area'],
                'f1054000a010000000000002':cope_recu.lower().replace('\xa0',' ').strip().replace(' ', '_')
            })
        
        accion_actualizacion = 'ACTUALIZACION' if record_existente == 'si' else 'CARGA INICIAL'

        metadata_extra = {}
        metadata_agregar_script = {"device_properties":{"system": "SCRIPT","process":"PROCESO CARGA DE PRODUCCION HIBRIDO", "accion":accion_actualizacion, "folio carga":current_record['folio'], "archive":"carga_de_produccion_py3.py"}}
        metadata_extra["properties"] = metadata_agregar_script
        this_record.update(metadata_extra)

        distrito_answer = answer.get('f1054000a0100000000000d5', '')
        if distrito_answer:
            distrito_answer = self.quita_FO_de_distrito(distrito_answer)
            if len(str(distrito_answer)) != 7:
                error.append('Longitud del Distrito es diferente de 7')
            answer['f1054000a0100000000000d5'] = distrito_answer

        # Los campos IDENTIFICACION DE NUMERO TELEFONICO EN RED PRINCIPAL, INCLUYE MARCACION *080, IDENTIFICACION DE NUMERO TELEFONICO EN RED SECUNDARIA, INCLUYE MARCACION *080
        # solo se aceptan para los Cambios de Domicilio, es decir, para los tipos de tarea que empiezan por D
        if tipo_tarea_record and str(tipo_tarea_record)[0] != 'D':
            answer.pop('5f1721afa63c9a750b82048a', None)
            #     answer.pop('5f1721afa63c9a750b82048a')
            answer.pop('5f1721afa63c9a750b82048b', None)
            #     answer.pop('5f1721afa63c9a750b82048b')
        
        if error:
            this_record.update({'error':  error})
        if alerts:
            this_record.update({'alerts': alerts})
        if record_existente == 'si':
            found_record['answers'].update(answer)
            this_record["answers"] = found_record['answers']
        else:
            this_record["answers"] = answer
        return this_record

    def quita_FO_de_distrito(self, distrito):
        try:
            if distrito[-2:].lower() == 'fo':
                new_distrito = distrito[:-2]
                if len(new_distrito) > 7:
                    return distrito[0:7]
                return new_distrito
            else:
                return distrito
        except Exception as e:
            print(e)
            return distrito

    def get_connection_id(self, form_id, user_id):
        if not self.ALL_CONNECTIONS.get(form_id):
            self.ALL_CONNECTIONS[form_id] = lkf_api.get_form_connections(form_id)
        form_connections = self.ALL_CONNECTIONS[form_id]
        if form_connections.get('connections'):
            for connection in form_connections['connections']:
                if connection['id'] == user_id:
                    return {'connection_id': int(connection['id']), 'user_of_connection':{}}
            for connection_id, coworkers in form_connections['coworkers'].items():
                if coworkers:
                    for worker in coworkers:
                        if worker['id'] == user_id:
                            return {'connection_id': int(connection_id), 'user_of_connection':worker}
        return {'connection_id': None, 'user_of_connection':{}}

    def get_id_contratista_from_tecnico(self, n_expediente_telmex):
        query = {
            'form_id': p_utils.FORM_ID_LISTADO_TECNICOS,
            'deleted_at': {'$exists': False},
            'answers.f1216500a010000000000001': n_expediente_telmex
        }
        select_columns = {
            'folio': 1,
            'answers.5f344a0476c82e1bebc991d5': 1, # Catalogo de Contratistas
            'answers.f1216500a010000000000004': 1, # Nombre del tecnico
            'answers.f1216500a010000000000005': 1, # Apellido paterno
            'answers.f1216500a010000000000006': 1 # Apellido materno
        }
        datos_tecnico = {}
        record_tecnico = cr.find(query, select_columns)
        for rtec in record_tecnico:
            answers_tec = rtec.get('answers', {})
            id_conexion_tec = 0
            datos_contratista_tec = answers_tec.get('5f344a0476c82e1bebc991d5', {}).get('5f344a0476c82e1bebc991d6', [])
            if datos_contratista_tec:
                id_conexion_tec = int( datos_contratista_tec[0] )
            datos_tecnico.update({
                'clave': rtec.get('folio'),
                'nombre': answers_tec.get('f1216500a010000000000004','')+' '+answers_tec.get('f1216500a010000000000005','')+' '+answers_tec.get('f1216500a010000000000006',''),
                'id_conexion': id_conexion_tec
            })
        return datos_tecnico

    def upload_docto(self, dir_docto, form_id_docto, def_field_id=''):
        upload_file = {}
        pdf_file = open(dir_docto, 'rb')
        pdf_file_dir = {'File': pdf_file}
        if def_field_id:
            field_id_docto = def_field_id
        else:
            field_id_docto = self.dict_ids_os_pdf[ form_id_docto ]
        upload_url = lkf_api.post_upload_file(data={'form_id': form_id_docto, 'field_id': field_id_docto}, up_file=pdf_file_dir, jwt_settings_key='JWT_KEY')
        print('-upload_url=',upload_url)
        try:
            file_url = upload_url['data']['file']
            print('Archivo cargado = {} :: {}'.format(dir_docto, file_url))
            upload_file = {field_id_docto: {'file_name':dir_docto.split('/')[-1], 'file_url':file_url}}
        except Exception as e:
            upload_file = {'error': 'Ocurrió un error al subir el documento, favor de contactar a Soporte'}
            print('Ocurrió un error al subir el documento:',str(e))
        pdf_file.close()

        # si no trae def_field_id entonces es la carga de PDF, hay que pegar también la fecha de carga
        if not def_field_id:
            upload_file['60882afbf33276990d3f8edf'] = p_utils.get_date_now()

        return upload_file

    def upload_pdf_disto(self, folio_record_os, form_id_record_os, files_found, def_field_id=''):
        dir_docto = files_found.get( folio_record_os, False )
        if dir_docto:
            file_uploaded = self.upload_docto(dir_docto, form_id_record_os, def_field_id=def_field_id)
            return file_uploaded
        return {}

    def get_data_zip( self, id_field_zip, permiso_sin_docto, docto_process ):
        val_field_zip = current_record.get('answers', {}).get(id_field_zip, {})
        doctos_found, doctos_error, ruta_doctos = {}, '', ''
        data_img_distos = {}
        if not val_field_zip:
            if not permiso_sin_docto:
                return 'error', f'Se requiere documento zip de {docto_process}', None, None
        else:
            doctos_found, doctos_error, ruta_doctos, data_img_distos = self.descomprimeZips( val_field_zip, current_record['folio'], f'cargaPorduccion{docto_process}' )
            if isinstance(doctos_found, str):
                return 'error', f"Ocurrió un error con el zip de {docto_process}: {self.list_to_str(doctos_error) if isinstance(doctos_error, list) else doctos_error}", None, None
        
        print(f'Documentos encontrados en zip de {docto_process}: {list(doctos_found.keys())} No tienen una extensión válida: {doctos_error}')
        return doctos_found, doctos_error, ruta_doctos, data_img_distos

    def get_form_id_turno(self, dif_type, area_cope_dir_inicial, tecnologia_orden):
        # Diccionario de mapeo para form_id_turno
        form_id_mapping = {
            'fibra': {
                'sur': self.ORDEN_SERVICIO_FIBRA_SURESTE,
                'occidente': self.ORDEN_SERVICIO_FIBRA_OCCIDENTE,
                'norte': self.ORDEN_SERVICIO_FIBRA_NORTE,
                'metro': self.ORDEN_SERVICIO_FIBRA
            },
            'cobre': {
                'sur': self.ORDEN_SERVICIO_COBRE_SURESTE,
                'occidente': self.ORDEN_SERVICIO_COBRE_OCCIDENTE,
                'norte': self.ORDEN_SERVICIO_COBRE_NORTE,
                'metro': self.ORDEN_SERVICIO_COBRE
            }
        }

        # Condición para fibra
        if dif_type == 'fibra' and tecnologia_orden != 'cobre':
            form_id_turno = form_id_mapping['fibra'].get(area_cope_dir_inicial['division'], '')
        # Condición para cobre
        elif dif_type == 'cobre' and tecnologia_orden in ['cobre', 'hibrida']:
            form_id_turno = form_id_mapping['cobre'].get(area_cope_dir_inicial['division'], '')
        else:
            form_id_turno = ''
        
        # Configurar connection_id si form_id_turno está vacío
        connection_id = '' if not form_id_turno else None
        
        return form_id_turno, connection_id

    def position_field_in_xls(self,  pos_field_id, by_name, by_field_id=[] ):
        for p, val in pos_field_id.items():
            if by_field_id:
                if val.get('field_id') in by_field_id:
                    return p
            else:
                if val.get('scritp_type') == by_name:
                    return p
        return None

    def prepare_record_admin( self, record_orden ):
        record_orden['form_id'] = self.dict_equivalences_forms_id[ record_orden['form_id'] ]
        record_orden.pop('alerts', None)
        record_orden.pop('aerea', None)
        record_orden.pop('user_id_old', None)
        record_orden.pop('assigned_to', None)
        record_orden.pop('answers_before_assign', None)
        return record_orden

    def create_record_fibra_cobre_hibrida(self, pos_field_id, records, header, current_record, parent_id, header_dict, pdfs_found, distometros_found, carga_sin_pdf, carga_sin_disto, dif_type='', 
        permisos_contratista={}, dict_info_connections={}, records_for_cambio_tec=[]):
        # print("Una sola funcion para fibra y cobre ....")
        record_errors = []
        records_ok = []
        create_json = {'created':{ 'order':0, 'duplicate':0 ,'total':0, 'errores':0},
        'uploaded':{'order':0, 'duplicate':0, 'total':0, 'errores':0},
        'error_file_records' : []}
        records_to_assign = {}
        records_before_assign = {}
        records_with_alerts = {}
        records_to_multi_post = []
        records_to_multi_patch = {}
        records_to_psr = {}
        fols_psr_to_update = []
        
        # IS_CARGA_TECNICO = current_record['form_id'] == FORM_ID_CARGA_TECNICOS
        IS_CARGA_TECNICO = False # Este tipo de carga no esta habilitada para las cuentas de Socios Comerciales
        
        copes_consultados = {}
        dict_pos_record = {}
        pos_tipo = 0
        pos_telefono = 0
        pos_tecnico = 0
        pos_expediente = 0
        pos_cambio_tecnologia = None
        for pos_rec, record in enumerate(records):
            hibrida = migracion = False
            
            # ==================== ToDo: Esta parte de la tecnologia se puede mejorar =====================
            tec = p_utils.get_order_tecnology(header, record)
            if dif_type == 'cobre' and tec in ('fibra', 'migracion'):
                continue
            elif dif_type == 'fibra' and tec == 'cobre':
                continue
            
            if header_dict.get('folio') and not str(record[header_dict['folio']]).strip():
                continue
            # Validacion adicional del telefono por el tema de Bajantes Degradados
            if header_dict.get('telefono') and not record[ header_dict['telefono'] ]:
                continue


            tecnologia_orden = str(record[header_dict['tecnologia_orden']]).strip().lower()
            if not tecnologia_orden or tecnologia_orden not in ['cobre','hibrida','migracion','fibra']:
                record_errors.append(record + ["Valores no validos en la columna TECNOLOGIA ORDEN o no esta en orden el formato que se intenta cargar.",])
                continue
            # ===============================================================================================
            try:
                cope_record = record[header_dict['cope']].strip().lower()
            except Exception as e:
                print(e)
                record_errors.append(record + ["COPE Inválido.",])
                continue
            
            if not copes_consultados.get( cope_record ):
                reg_catalogo = p_utils.get_cope_in_catalogo( cope_record, jwt_settings_key='JWT_KEY_ADMIN' )
                if not reg_catalogo:
                    print("Cope no encontrado en el catalogo:",cope_record)
                    record_errors.append(record + ["Cope no encontrado en el catalogo",])
                    continue
                
                if len(reg_catalogo) > 1:
                    record_errors.append(record + ["El cope se econtró más de una vez en el catálogo, favor de revisar con soporte"])
                    continue
                
                copes_consultados[ cope_record ] = reg_catalogo
            
            area_cope_dir_inicial = copes_consultados[ cope_record ][0]

            if area_cope_dir_inicial.get('error'):
                record_errors.append(record + [area_cope_dir_inicial['error'],])
                continue
            
            metadata = {}
            if area_cope_dir_inicial:
                form_id_turno, connection_id = self.get_form_id_turno(dif_type, area_cope_dir_inicial, tecnologia_orden)
                
                if not form_id_turno:
                    record_errors.append(record+['No se enconotró la forma de OS',])
                    continue
                
                pos_field_id = p_utils.get_pos_field_id_dict(header, form_id=form_id_turno, forms_dict=self.forms_dict, equivalcens_map_observa=self.equivalcens_map_observa)
                
                if not pos_field_id:
                    record_errors.append(record+['Error al obtener informacion de la forma de OS, favor de verificar que tenga la forma compartida y reprocesar',])
                    continue

                if not pos_tipo:
                    pos_tipo = self.position_field_in_xls( pos_field_id, 'tipo' )
                if not pos_telefono:
                    pos_telefono = self.position_field_in_xls( pos_field_id, None, by_field_id=['f1054000a010000000000005'] )
                if not pos_expediente:
                    pos_expediente = self.position_field_in_xls( pos_field_id, None, by_field_id=['f1054000a010000000000007', 'f1054000a0100000000000d6'] )
                if not pos_cambio_tecnologia:
                    pos_cambio_tecnologia = self.position_field_in_xls( pos_field_id, 'cambio_tecnologia' )

                cambio_tecnologia = record[ pos_cambio_tecnologia ].lower().strip() if pos_cambio_tecnologia else ''
                pos_field_id.update({'pos_expediente': pos_expediente})
                metadata = lkf_api.get_metadata(form_id=form_id_turno )
                connection_dir = self.get_connection_id(form_id_turno, parent_id)

                user_supervisor = False
                user_id = current_record['user_id']

                if not self.USERS.get(user_id):
                    # self.USERS[user_id] = lkf_api.get_connection_by_id(user_id, jwt_settings_key='JWT_KEY')
                    self.USERS[user_id] = p_utils.get_parent_id(user_id, all_info=True)

                user_info = self.USERS[user_id]

                if not user_info:
                    if not self.USERS.get(user_id):
                        self.USERS[user_id] = lkf_api.get_user_by_id(user_id, jwt_settings_key='JWT_KEY')
                    user_info = self.USERS[user_id]
                    user_supervisor = True
                # else:
                #     user_info = user_info['connection']
                if user_info.get('email'):
                    user_email = user_info['email']
                    if user_email != 'linkaform@operacionpci.com.mx' and not user_supervisor:
                        connection_validate_dir = p_utils.search_for_connection(user_email, form_id_turno, self.dir_form_connection)
                        print ('connection_validate_dir=',connection_validate_dir)
                        if not connection_validate_dir:
                            print ('xxxxxxxxxxxxxxxxxxxxxxx')
                            record_errors.append(record + ["Correo de conexion equivocado o forma no compartida",])
                            continue
            else:
                record_errors.append(record + ["Cope invalido, puede tener espacios en blanco al inicio o al final de la columna o no esta dado de alta en el catalogo de area cope",])
                continue
            if connection_dir.get('connection_id'):
                connection_id =  connection_dir['connection_id']
                user_of_connection = connection_dir['user_of_connection']
            if pos_field_id:

                if not pos_telefono:
                    pos_telefono = self.position_field_in_xls( pos_field_id, None, by_field_id=['f1054000a010000000000005'] )

                if tec == 'hibrida':
                    hibrida = True
                elif tec == 'migracion':
                    migracion = True
                this_record = {}

                # ------ Se obtiene el Folio del registro
                pos_folio = p_utils.get_record_folio(header_dict)
                if pos_folio is None:
                    folio = None
                else:
                    folio = str( record[ pos_folio ] ).strip()
                
                # ------ Se obtiene el Teléfono del registro
                try:
                    telefono_registro = int(record[pos_telefono])
                except Exception as e:
                    print(e)
                    record_errors.append(record + ["Error en el telefono, favor de revisar"])
                    continue
                
                # if folio:
                if True:

                    nombre_docto_a_buscar = folio if folio else str(telefono_registro)
                    
                    # Se revisa que existan los documentos de pdf y distometro si el contratista no esta autorizado para carga sin estos documentos
                    if nombre_docto_a_buscar not in pdfs_found.keys() and not carga_sin_pdf:
                        record_errors.append( record + ["El folio no trae su documento PDF"] )
                        print('El folio no trae su documento PDF {}'.format(nombre_docto_a_buscar))
                        continue
                    if nombre_docto_a_buscar not in distometros_found.keys() and not carga_sin_disto:
                        record_errors.append( record + ["El folio no trae su documento de Distómetro"] )
                        print('El folio no trae su documento Distómetro {}'.format(nombre_docto_a_buscar))
                        continue
                    
                    print('Documento encontrado para el Folio {}'.format(nombre_docto_a_buscar))
                    
                    dict_pos_record[ folio ] = pos_rec
                    datos_tecnico = {}
                    if IS_CARGA_TECNICO:
                        if not pos_tecnico:
                            pos_tecnico = self.position_field_in_xls( pos_field_id, 'tecnico' )
                            print('--------------- pos_tecnico:',pos_tecnico)
                        try:
                            expediente_telmex_tec = int( record[ pos_tecnico ] )
                        except Exception as e:
                            print(e)
                            record_errors.append(record + ["El expediente del técnico no se pudo convertir a entero",])
                            continue
                        datos_tecnico = self.get_id_contratista_from_tecnico(expediente_telmex_tec)
                        print('****** datos_tecnico=',datos_tecnico)
                        id_conexion_tec = datos_tecnico.get('id_conexion', 0)
                        if not id_conexion_tec:
                            record_errors.append(record + ["No se encontró la Conexión para este Técnico",])
                        connection_id = id_conexion_tec
                    this_record = self.prepare_record(record, metadata, pos_field_id, folio, connection_id, self.RECORDS_PASSED, dif_type, hibrida, form_id_turno, current_record, copes_consultados, cambio_tecnologia, records_for_cambio_tec, \
                        info_cope=area_cope_dir_inicial, pos_tipo=pos_tipo, pos_telefono=pos_telefono, datos_tecnico=datos_tecnico, permisos_contratista=permisos_contratista, dict_info_connections=dict_info_connections, header_dict=header_dict )
                    
                    # fol_mts_distometro = data_img.get(str(nombre_docto_a_buscar))
                    # print('\n      data_img= ',data_img)
                    # print('\n      buscando= ',str(nombre_docto_a_buscar))
                    # print('\n      fol_mts_distometro= ',fol_mts_distometro)

                    if this_record['create']:
                        if this_record['create'].get('error'):
                            error_create = [this_record['create']['error'],] if type(this_record['create']['error']) == str else this_record['create']['error']
                            record_errors.append( record + error_create )
                            continue
                        this_record['create']['answers'].update({'f1054000a030000000000115':'portal' if migracion else 'cope'})
                        arreglo_grupo_repetitivo_hst = {'f1054000a030000000000e21':'','f1054000a030000000000e22':'pendiente','f1054000a030000000000e23':datetime.datetime.now().strftime("%Y-%m-%d")}
                        this_record['create']['answers']['f1054000a030000000000e20'] = [arreglo_grupo_repetitivo_hst,]
                        this_record['create']['answers'].update({'5e17674c50f45bac939c932e':'sí'})
                        """
                        # Empiezo a cargar el documento pdf del folio
                        """
                        print('Parece que todo va en orden con el folio, entonces cargo su documento pdf')
                        folio_to_create = this_record['create']['folio']
                        form_id_to_create = this_record['create']['form_id']
                        telefono_to_create = this_record['create'].get('answers',{}).get('f1054000a010000000000005','')
                        area_to_create = this_record['create'].get('answers',{}).get('f1054000a0100000000000a2','')
                        pdf_uploaded = self.upload_pdf_disto( nombre_docto_a_buscar, form_id_to_create, pdfs_found )
                        if pdf_uploaded.get('error', False):
                            record_errors.append(record + [pdf_uploaded.get('error'),])
                            continue
                        this_record['create']['answers'].update(pdf_uploaded)
                        # Cargando el Distómetro
                        disto_uploaded = self.upload_pdf_disto( nombre_docto_a_buscar, form_id_to_create, distometros_found, def_field_id='5fff390f68b587d973f1958f' )
                        if disto_uploaded.get('error', False):
                            record_errors.append(record + [disto_uploaded.get('error'),])
                            continue
                        this_record['create']['answers'].update(disto_uploaded)

                        folio_psr = this_record['create'].pop('folio_psr', False)
                        
                        """
                        # Creando el registro.... se va a crear de lado de Admin y también de lado de IASA
                        """
                        # Se crea en Admin
                        this_record['create']['form_id'] = self.dict_equivalences_forms_id[form_id_to_create]

                        response_created_admin = lkf_api.post_forms_answers(this_record['create'], jwt_settings_key='JWT_KEY')
                        if response_created_admin.get('status_code') != 201:
                            record_errors.append(record + [ p_utils.arregla_msg_error_sistema(response_created_admin) ])
                            continue

                        # Ahora se crea en IASA
                        resp_copy = self.make_copy_os( this_record['create']['answers'], form_id_turno, current_record['folio'], folio, connection_id )
                        if resp_copy.get('error'):
                            record_errors.append(record + [resp_copy['error'],])
                            self.rmv_psr_created(settings.config['ACCOUNT_ID'], self.dict_equivalences_forms_id[form_id_to_create], folio_to_create, telefono_to_create, area_to_create)
                            continue

                        if folio_psr:
                            fols_psr_to_update.append( folio_psr )
                        
                        # Se actualizan los totales
                        create_json.update(p_utils.update_create_json(create_json, this_record))

                        # Mensajes en el excel
                        msg_exitoso = 'Folio CREADO con éxito'
                        if this_record['create'].get('alerts', []):
                            msg_exitoso = '{} :: {}'.format(msg_exitoso, self.list_to_str( this_record['create'].get('alerts', []) ))
                        records_ok.append(record+[msg_exitoso,])

                    elif this_record['update']:
                        is_updating_record_exists = this_record['update'].get('exists_copy', False)
                        record_os_copy = this_record['update'].get('record_copy')
                        form_id_to_update = this_record['update'].get('form_id')
                        folio_to_update = this_record['update'].get('folio')
                        folio_to_update = this_record['update'].pop('folio_record_admin', folio_to_update)
                        telefono_to_update = this_record['update'].get('answers',{}).get('f1054000a010000000000005','')
                        area_to_update = this_record['update'].get('answers',{}).get('f1054000a0100000000000a2','')
                        id_user_old = this_record['update'].get('user_id_old')
                        answers_prev = this_record['update'].get('answers_before_assign')

                        if this_record['update'].get('error'):
                            if this_record['update'].get('assigned_to'):
                                id_connection_assigned = this_record['update']['assigned_to']
                                self.desasignar_registro( settings.config['ACCOUNT_ID'], id_user_old, self.dict_equivalences_forms_id[form_id_to_update], folio_to_update, telefono_to_update, area_to_update, answers_prev )
                            if type(this_record['update']['error']) == str:
                                msg_error_record = this_record['update']['error']
                                if this_record['update'].get('can_upload_pdf', False):
                                    pdf_uploaded = self.upload_pdf_disto( nombre_docto_a_buscar, form_id_turno, pdfs_found )
                                    if pdf_uploaded.get('error', False):
                                        msg_error_record += ' Error al cargar el PDF {}'.format(pdf_uploaded.get('error'))
                                    else:
                                        res_upload_only_pdf = lkf_api.patch_multi_record(pdf_uploaded, self.dict_equivalences_forms_id[form_id_turno], folios=[folio_to_update,], jwt_settings_key='USER_JWT_KEY')
                                        print('Error por folio en cobranza... pero si se deja cargar pdf ',res_upload_only_pdf)
                                        msg_error_record += ' pero se actualizó el PDF correctamente'
                                record_errors.append(record + [msg_error_record,])
                                continue
                            else:
                                record_errors.append(record + this_record['update']['error'])
                                continue
                        cargado_desde_pic = this_record['update'].get('answers',{}).get('5eb0326a9e6fda7cb11163f1','')
                        tecnico_pic = this_record['update'].get('answers',{}).get('5eb091915ae0d087df1163de','')
                        is_cargado_desde_pic = (cargado_desde_pic == 'sí' or tecnico_pic != '')
                        if is_cargado_desde_pic:
                            this_record['update']['answers'].update({'5eb0326a9e6fda7cb11163f1':'no'})
                        this_record['update']['answers'].update({'5e17674c50f45bac939c932e':'sí'})

                        """
                        # Empiezo a cargar el documento pdf del folio
                        """
                        print('Parece que todo va en orden con el folio, entonces cargo su documento pdf')
                        pdf_uploaded = self.upload_pdf_disto( nombre_docto_a_buscar, form_id_to_update, pdfs_found )
                        if pdf_uploaded.get('error', False):
                            record_errors.append(record + [pdf_uploaded.get('error'),])
                            self.desasignar_registro( settings.config['ACCOUNT_ID'], id_user_old, self.dict_equivalences_forms_id[form_id_to_update], folio_to_update, telefono_to_update, area_to_update, answers_prev, is_updating_record_exists )
                            continue
                        this_record['update']['answers'].update(pdf_uploaded)
                        # Cargando el Distómetro
                        disto_uploaded = self.upload_pdf_disto( nombre_docto_a_buscar, form_id_to_update, distometros_found, def_field_id='5fff390f68b587d973f1958f' )
                        if disto_uploaded.get('error', False):
                            record_errors.append(record + [disto_uploaded.get('error'),])
                            self.desasignar_registro( settings.config['ACCOUNT_ID'], id_user_old, self.dict_equivalences_forms_id[form_id_to_update], folio_to_update, telefono_to_update, area_to_update, answers_prev, is_updating_record_exists )
                            continue
                        this_record['update']['answers'].update(disto_uploaded)

                        record_admin = self.prepare_record_admin( deepcopy( this_record['update'] ) )
                        response = lkf_api.patch_record(record_admin,  jwt_settings_key='JWT_KEY')
                        print("+++++ Actualizando folio:",folio_to_update)
                        print("++++++++++ response:",response)
                        try:
                            status_code = response['status_code']
                        except KeyError:
                            status_code = 500
                        if response['status_code'] in (200,201,202,204, 205):
                            if response['status_code'] != 205:
                                msg_exitoso = "Folio MODIFICADO con éxito"
                                if this_record['update'].get('alerts', []):
                                    msg_exitoso = '{} :: {}'.format(msg_exitoso, self.list_to_str( this_record['update'].get('alerts', []) ))
                                resp_copy = self.make_copy_os( this_record['update']['answers'], form_id_turno, current_record['folio'], folio_to_update, connection_id, data_os_copy=record_os_copy )
                                if resp_copy.get('error'):
                                    record_errors.append(record + [resp_copy['error'],])
                                    self.desasignar_registro( settings.config['ACCOUNT_ID'], id_user_old, self.dict_equivalences_forms_id[form_id_to_update], folio_to_update, telefono_to_update, area_to_update, answers_prev, is_updating_record_exists )
                                    continue
                                records_ok.append(record+[msg_exitoso,])
                                create_json.update(p_utils.update_create_json(create_json, this_record))
                        else:
                            if status_code == 404:
                                record_errors.append(record + ["No se pudo actualizar el registro ya que no se encontró",])
                            else:
                                if this_record['update'].get('assigned_to'):
                                    id_connection_assigned = this_record['update']['assigned_to']
                                    id_user_old = this_record['update']['user_id_old']
                                    self.desasignar_registro( settings.config['ACCOUNT_ID'], id_user_old, self.dict_equivalences_forms_id[form_id_to_update], folio_to_update, telefono_to_update, area_to_update, answers_prev, is_updating_record_exists )
                                msg_error_completo = p_utils.arregla_msg_error_sistema(response)
                                record_errors.append(record + [msg_error_completo,])
                    elif this_record.get('cambio_tecnologia'):
                        records_ok.append(records[ dict_pos_record[ this_record['cambio_tecnologia'] ] ] + ['Folio marcado para Cambio de Tecnologia',])
                        create_json['created']['total'] += 1
                        create_json['created']['order'] += 1
                    else:
                        create_json['created']['duplicate'] += 1
                        if folio not in self.GLOBAL_COMMUNICATION:
                            self.GLOBAL_COMMUNICATION += 'Folio: %s cargado previamente. '%folio
                
                # Esta validacion ya no aplica porque habrá casos donde no pongan el folio por Bajantes Degradados
                # else:
                #     print("Registro Vacio ************ ")
                #     continue
            else:
                record_errors.append(record + ["Forma de Orden de Servicio no compartida",])
        
        if records_to_multi_post:
            print('+++++records to create:',records_to_multi_post)
            all_create_records = lkf_api.post_forms_answers_list(records_to_multi_post, jwt_settings_key='USER_JWT_KEY')
            print('-----all_create_records',all_create_records)
            for create_record in all_create_records:
                if create_record.get('status_code',0) in (200,201,202,204, 205):
                    if create_record['status_code'] != 205:
                        print('todo ok...')
                        create_json['created']['total'] += 1
                        create_json['created']['order'] += 1
                        folio_creado = create_record['folio']
                        if folio_creado in records_before_assign.keys():
                            try:
                                new_record = '/api/infosync/form_answer/' + create_record['json']['id'] +'/'
                            except KeyError:
                                try:
                                    new_record = '/api/infosync/form_answer/' + create_record['content']['id'] +'/'
                                except Exception as e:
                                    print(e)
                                    new_record = ""
                            connection_id_for_record_creado = records_before_assign[folio_creado]
                            # if not records_to_assign.get(connection_id_for_record_creado):
                            #     records_to_assign[ connection_id_for_record_creado ] = []
                            # records_to_assign[ connection_id_for_record_creado ].append(new_record)
                            records_to_assign.setdefault(connection_id_for_record_creado, []).append(new_record)

                        msg_exitoso = 'Folio CREADO con éxito'
                        if records_with_alerts.get(folio_creado, []):
                            msg_exitoso = '{} :: {}'.format(msg_exitoso, self.list_to_str( records_with_alerts.get(folio_creado, []) ))
                        records_ok.append(records[dict_pos_record[create_record['folio']]] + [msg_exitoso,])
                        fols_psr_to_update.append( records_to_psr.get(folio_creado) )
                else:
                    #print('$#@!$#@!%$$##! 690')
                    msg_error_completo = p_utils.arregla_msg_error_sistema(create_record)
                    record_errors.append(records[dict_pos_record[create_record['folio']]] + [msg_error_completo,])
        print('....... ............ ............. fols_psr_to_update =',fols_psr_to_update)
        if fols_psr_to_update:
            resp_update_psr = lkf_api.patch_multi_record({'6670a0a6fe5560837d1cc9bc': 'autorizado'}, p_utils.FORM_ID_PSR, folios=fols_psr_to_update, jwt_settings_key='JWT_KEY_ADMIN', threading=True)
            print('... ............ ..... resp_update_psr =',resp_update_psr)
        if record_errors:
            try:
                if this_record.get('update'):
                    create_json['uploaded']['errores'] = len(record_errors)
                if this_record.get('create'):
                    create_json['created']['errores'] = len(record_errors)
            except Exception as e:
                print(e)
                create_json['created']['errores'] = len(record_errors)
            create_json['error_file_records'] =  record_errors
        if records_ok:
            create_json['records_ok'] = records_ok
        print("*****************************records_to_assign:",records_to_assign)
        for id_connection, records_for_connection in records_to_assign.items():
            response_assign = lkf_api.assigne_connection_records( id_connection, records_for_connection)
            print("respuesta assignacion",response_assign)
        return create_json

    def verify_same_cope(self, header, records):
        cope_row = -1
        pos = 0
        for c in header:
            if c.lower() == 'cope':
                cope_row = pos
                break
            pos +=1
        if cope_row >= 0:
            cope = records[0][pos]
        else:
            return {'error':'No existe la columna COPE en la cabezera del archivo'}
        return {'cope':cope}

    def get_cols_bonificaciones(self, header):
        cols_accepted = ['bonificacion_por_distancia_y_volumen_de_1_a_5_o.s_construidas', 'bonificacion_por_distancia_y_volumen_de_6_a_15_o.s_construidas', 'bonificacion_por_distancia_y_volumen_de_16_a_25_o.s_construidas', \
        'bonificacion_por_distancia_y_volumen_mas_de_25_o.s_construidas', 'montaje_de_puente_en_distribuidor_general', "instalacion_de_poste_de_25'", 'pruebas_de_transmision_de_datos_vdsl_en_roseta_de_datos_con_equipo_homologado', \
        'cableado_interior_1_aparato_y_modem_para_infinitum_(dit_con_splitter_con_proteccion)', 'identificacion_de_numero_telefonico_en_red_principal,_incluye_marcacion_*080', 'identificacion_de_numero_telefonico_en_red_secundaria,_incluye_marcacion_*080', \
        'ubicacion_del_cliente_y_prueba_de_transmision_vdsl_en_terminal_aerea', 'prueba_de_transmision_vdsl_adicional_en_terminal_area', 'radial_en_banqueta', 'radial_en_cepa_libre', 'reparacion_de_tropezon_en_radial', \
        'cableado_interior_adicional_para_el_dit_con_splitter_con_proteccion_(extension)', 'migracion_tba', 'direccion', 'construccion_o_rehabilitacion_de_cableado_interior_para_1_aparato']
        header_sin_acentos = p_utils.header_without_acentos(header)
        cols_not_found = list( set(cols_accepted) - set(header_sin_acentos) )
        no_necesarias = ['cableado_interior_adicional_para_el_dit_con_splitter_con_proteccion_(extension)', 'reparacion_de_tropezon_en_radial', 'radial_en_banqueta', 'radial_en_cepa_libre', 'migracion_tba', 'direccion']
        necesarias_not_found = list( set(cols_not_found) - set(no_necesarias) )
        return necesarias_not_found

    def get_tecnicos_by_conexion(self, parent_id):
        connections_users = p_utils.get_all_connections()
        return { infCon['id']: {'nombre': infCon.get('first_name'), 'username': infCon.get('username')} for infCon in connections_users if infCon.get('id') }

    def upload_bolsa_hibrido(self, current_record, form_id, header, records, RECORDS_PASSED=0):
        bonificaciones_not_found = self.get_cols_bonificaciones(header)
        if bonificaciones_not_found:
            return self.set_status_proceso( current_record, record_id, 'error', msg='El archivo no lleva las columnas: ' + self.list_to_str([nf.replace('_', ' ').capitalize() for nf in bonificaciones_not_found]) )

        different_copes = self.verify_same_cope(header, records)
        if different_copes.get('error'):
            return self.set_status_proceso( current_record, record_id, 'error', msg=different_copes['error'] )

        current_record['answers']['f1074100a010000000000cc1'] = different_copes.get('cope', '').title().replace('_', ' ')

        parent_id = p_utils.get_parent_id( current_record.get('user_id', 0) )
        # IASA - parent_id pues solo el id de iasa
        # parent_id = current_record.get('user_id', 0)
        ##################################################################################################################
        # Recupero los Tecnicos que tiene el Contratista en Plantilla Empresarial
        dict_info_connections = self.get_tecnicos_by_conexion(parent_id)
        # IASA - No aplica esta validacion de tecnicos. Los tecnicos se obtienen de plantilla empresarial
        # Los contratistas no van a tener plantilla empresarial, entonces no aplica
        # dict_tecnicos = {}
        # print('Tecnicos encontrados en Plantilla Empresarial=',dict_tecnicos.keys())
        ##################################################################################################################
        permisos_contratista = p_utils.get_permisos_contratista_from_catalog( parent_id )
        if not permisos_contratista:
            return self.set_status_proceso( current_record, record_id, 'error', msg='No se pudieron obtener los permisos del contratista' )
        print('cuenta: {0} parent_id obtenido: {1} permisos del contratista: {2}'.format( current_record.get('user_id', 0), parent_id, permisos_contratista ))

        # Obtengo la informacion de IASA y se la integro a los permisos de su contratista para despues usarlos
        data_admin_iasa = p_utils.get_permisos_contratista_from_catalog( parent_id, catalog_id_contratistas=self.CATALOGO_CONTRATISTAS_ID )
        permisos_contratista['info_iasa'] = data_admin_iasa
        print('permisos cuenta padre =',data_admin_iasa)

        """
        Obteniendo los folios de los pdfs y Distómetros
        """
        permiso_carga_sin_pdf = permisos_contratista.get('carga_sin_pdf', '')
        carga_sin_pdf = True
        if not permiso_carga_sin_pdf or permiso_carga_sin_pdf.lower() == 'no':
            carga_sin_pdf = False

        permiso_carga_sin_disto = permisos_contratista.get('carga_sin_distometro', '')
        carga_sin_disto = True
        if not permiso_carga_sin_disto or permiso_carga_sin_disto.lower() == 'no':
            carga_sin_disto = False
        






        pdfs_found, pdfs_error, ruta_pdfs, data_img_pdfs = self.get_data_zip( '5b99664fa53def000d9c6f94', carga_sin_pdf, 'PDFS' )
        if pdfs_found == 'error':
            return self.set_status_proceso(current_record, record_id, 'error', msg=pdfs_error)

        distometros_found, distometros_error, ruta_ditometros, data_img_distometros = self.get_data_zip('60a81c43a57544220ca210a7', carga_sin_disto, 'Distometros')
        if distometros_found == 'error':
            return self.set_status_proceso(current_record, record_id, 'error', msg=distometros_error)








        # zip_field_pdf = current_record.get('answers', {}).get('5b99664fa53def000d9c6f94',{})
        # if not zip_field_pdf:
        #     if carga_sin_pdf:
        #         pdfs_found, pdfs_error, ruta_pdfs = {}, '', ''
        #     else:
        #         return self.set_status_proceso( current_record, record_id, 'error', msg='Se requiere documento zip de pdfs' )
        # else:
        #     pdfs_found, pdfs_error, ruta_pdfs = self.descomprimeZips( zip_field_pdf, current_record['folio'], 'cargaPorduccionPDFS' )
        # if type(pdfs_found) == str:
        #     # Ocurrió un error con el zip de pdfs
        #     return self.set_status_proceso( current_record, record_id, 'error', msg='Ocurrió un error con el zip de pdfs: {}'.format(pdfs_error) )
        # print('Documentos encontrados en zip de pdfs: {} No tienen una extensión válida: {}'.format(list(pdfs_found.keys()), pdfs_error))

        # zip_field_distometro = current_record.get('answers', {}).get('60a81c43a57544220ca210a7',{})
        # if not zip_field_distometro:
        #     if carga_sin_disto:
        #         distometros_found, distometros_error, ruta_ditometros = {}, [], ''
        #     else:
        #         return self.set_status_proceso( current_record, record_id, 'error', msg='Se requiere documento zip de Distómetros' )
        # else:
        #     distometros_found, distometros_error, ruta_ditometros = self.descomprimeZips( zip_field_distometro, current_record['folio'], 'cargaPorduccionDistometros' )
        # if type(distometros_found) == str:
        #     # Ocurrió un error con el zip de pdfs
        #     return self.set_status_proceso( current_record, record_id, 'error', msg='Ocurrió un error con el zip de Distómetros: {}'.format(distometros_error) )
        # print('Documentos encontrados en zip de Distometros: {} No tienen una extensión válida: {}'.format(list(distometros_found.keys()), distometros_error))
        
        













        create_json_fibra =  {'created':{ 'order':0, 'duplicate':0 ,'total':0, 'errores':0},
                              'uploaded':{'order':0, 'duplicate':0, 'total':0, 'errores':0},
                              'error_file_records' : []}
        create_json_cobre = {'created':{ 'order':0, 'duplicate':0 ,'total':0, 'errores':0},
                              'uploaded':{'order':0, 'duplicate':0, 'total':0, 'errores':0},
                              'error_file_records' : []}
        
        pos_field_id, pos_field_cobre_id = {}, {}
        header_dict = p_utils.make_header_dict(header)
        

        # Se revisa que no haya folios duplicados en la carga
        pos_folio = p_utils.get_record_folio(header_dict)
        
        # Validacion ya no es necesaria por tema de Bajantes Degradados
        # if pos_folio is None:
        #     return self.set_status_proceso( current_record, record_id, 'error', msg='No se encontro la columna Folio en el documento de carga' )
        
        if pos_folio != None:
            all_folios_in_file = [ record[ pos_folio ] for record in records if record[ pos_folio ] ]
            duplicated_folios = [str(item) for item, count in collections.Counter(all_folios_in_file).items() if count > 1]
            print("duplicated_folios=",duplicated_folios)
            if duplicated_folios:
                return self.set_status_proceso( current_record, record_id, 'error', msg='No se permiten folios duplicados en un mismo proceso {}'.format(self.list_to_str(duplicated_folios)) )
        

        records_for_cambio_tec = p_utils.get_cambios_tecnologia()
        print('+++ records_for_cambio_tec =',records_for_cambio_tec)
        create_json_fibra.update(self.create_record_fibra_cobre_hibrida(pos_field_id, records, header, current_record, parent_id, header_dict, pdfs_found, distometros_found, carga_sin_pdf, carga_sin_disto, dif_type='fibra', permisos_contratista=permisos_contratista, dict_info_connections=dict_info_connections, records_for_cambio_tec=records_for_cambio_tec))
        create_json_cobre.update(self.create_record_fibra_cobre_hibrida(pos_field_cobre_id, records, header, current_record, parent_id, header_dict, pdfs_found, distometros_found, carga_sin_pdf, carga_sin_disto, dif_type='cobre', permisos_contratista=permisos_contratista, dict_info_connections=dict_info_connections, records_for_cambio_tec=records_for_cambio_tec))
        total_errors = len( create_json_fibra.get('error_file_records', []) ) + len( create_json_cobre.get('error_file_records', []) )
        print('total_errors=',total_errors)
        
        # Se eliminan las rutas temporales donde se descargo el pdf y distometro
        if ruta_pdfs:
            shutil.rmtree(ruta_pdfs)
        if ruta_ditometros:
            shutil.rmtree(ruta_ditometros)
        
        # Se integra un excel con los folios que se cargaron correctamente
        total_records_ok = create_json_fibra.get('records_ok',[]) + create_json_cobre.get('records_ok',[])
        if total_records_ok:
            file_ok = p_utils.upload_error_file(header + ['Resultado de la carga',], total_records_ok, form_id, file_field_id='5f088b6d7df8cf7fe42f215c')
            if type(file_ok) == str:
                return self.set_status_proceso( current_record, record_id, 'error', msg=file_ok )
            file_ok['5f088b6d7df8cf7fe42f215c'].update({'file_name':'Folios_procesados_correctamente.xlsx'})
            current_record['answers'].update(file_ok)
        print('<.><.> entra aca??????')
        create_json = p_utils.merge_json(create_json_fibra, create_json_cobre ,header, form_id)
        # print('\ncreate_json =',create_json)
        # stop
        
        # Si hay errores tambien se carga el documento
        if create_json.get('error_file'):
            current_record['answers'].update(create_json['error_file'])
        
        current_record['answers'].update(p_utils.get_bolsa_update_communication(create_json, total_errors))

            #Actualiza el status del la bolsa
        if self.GLOBAL_COMMUNICATION:
            if total_errors > 0:
                self.GLOBAL_COMMUNICATION += ' Existieron en la carga {} Folios con Error. Favor de revisar el archivo de folios con error'.format(total_errors)

            current_record['answers']['f1074100a010000000000002'] = "%s"%self.GLOBAL_COMMUNICATION
        if settings.GLOBAL_ERRORS:
            current_record['answers']['f1074100a010000000000005'] = 'error'


        response = lkf_api.patch_record(current_record, record_id, jwt_settings_key='USER_JWT_KEY')

    def query_get_permisions(self, user_email):
        query = {'form_id':  p_utils.UPLOAD_PERMISIONS, 'deleted_at' : {'$exists':False}, \
        'answers.5a04ddbdb43fdd102456b822':user_email}
        record = lkf_obj.cr.find_one(query, {'folio':1, 'answers':1})
        return record

    def check_upload_permisions(self, current_record):
        connection_id = current_record.get('connection_id', False)
        user_id = current_record['user_id']
        if connection_id:
            if not self.USERS.get(user_id):
                # self.USERS[user_id] = lkf_api.get_connection_by_id(user_id, jwt_settings_key='JWT_KEY')
                self.USERS[user_id] = p_utils.get_parent_id(user_id, all_info=True)
            user_info = self.USERS[user_id]
            if not user_info:
                if not self.USERS.get(connection_id):
                    self.USERS[connection_id] = lkf_api.get_connection_by_id(connection_id, jwt_settings_key='JWT_KEY')
                user_info = self.USERS[connection_id]
            user_email = user_info.get('email') # user_info['connection']['email'] if user_info.get('connection') else ''
        else:
            user_info = lkf_api.get_user_by_id(user_id, jwt_settings_key='JWT_KEY')
            user_email = user_info['email']
        
        print('email conexion =',user_email)
        permisions = self.query_get_permisions(user_email)
        if not permisions:
            return None
        return permisions['answers'].get('5a0a8371b43fdd2f5f2ad7cb')

    def carga_de_produccion(self, current_record):

        fields_clean = ['f1074100a010000000000002', 'f1074100a010000000000cc1', 'f1074100a010000000000003', '5f088b6d7df8cf7fe42f215c', 'f1074100a010000000000a12', \
        'f1074100a01000000000ac12', 'f1074100a010000000000a11', 'f1074100a010000000000a13']

        for field_clean in fields_clean:
            current_record['answers'].pop(field_clean, None)

        a, b = self.set_status_proceso(current_record, record_id, 'procesando')
        url = current_record['answers'].get('f1074100a010000000000001', {}).get('file_url')

        if not url:
            return self.set_status_proceso( current_record, record_id, 'error', msg='Debe cargar un documento excel con la carga de produccion' )

        try:
            header, records = p_utils.read_file(url)
        except Exception as e:
            print('[ERROR] al leer el excel =',e)
            return self.set_status_proceso( current_record, record_id, 'error', msg='El formato del archivo adjunto esta mal o puede tener fechas con año 1900. Favor de revisar que el formato sea xlsx o csv. Recuerda actualizar el estatus a Por Cargar' )

        if isinstance(header, dict) and header.get('error'):
            return self.set_status_proceso( current_record, record_id, 'error', msg=header['error'] )

        if not records:
            return self.set_status_proceso( current_record, record_id, 'error', msg='No Existen registros en el archivo' )

        permision_type = self.check_upload_permisions(current_record)
        print('permiso para Carga de Produccion =', permision_type)
        if permision_type:
            if permision_type == 'supervisor':
                print('========= ENTRA A SUPERVISOR ================')
                if not 'tecnologia_orden' in header and not 'tecnologia_de_orden' in header:
                    return self.set_status_proceso(current_record, record_id, 'error', 'El formato del archivo adjunto no contiene Tecnologia de la Orden. El formato debe de contener una columna con nombre TECNOLOGIA ORDEN')
                
                from carga_produccion_supervisor import upload_bolsa_supervisor
                return upload_bolsa_supervisor(current_record)
            elif permision_type == 'hibrido':
                print('========= ENTRA A HIBRIDO ================')
                if not 'tecnologia_orden' in header and not 'tecnologia_de_orden' in header:
                    return self.set_status_proceso(current_record, record_id, 'error', 'El formato del archivo adjunto no contiene Tecnologia de la Orden. El formato debe de contener una columna con nombre TECNOLOGIA ORDEN')
                
                return self.upload_bolsa_hibrido(current_record, current_record['form_id'], header, records )
            elif permision_type == 'contratista':
                print('============= ENTRA A CONTRATISTA ============')
                from carga_produccion_contratista import upload_bolsa_contratista
                return upload_bolsa_contratista(current_record)
        
        return self.upload_bolsa_hibrido(current_record, current_record['form_id'], header, records )


if __name__ == '__main__':
    print("--- --- --- Se empieza la carga de produccion --- --- ---")
    
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
    
    # Cuenta del contratista donde se instala el módulo
    # ToDo ... este JWT hay que quitarlo porque ya lo lleva en el default
    # jwt_iasa = lkf_api.get_jwt(api_key='2ab32e3d40f5d91f157a854111abfa9b8248cf25')
    # config['JWT_KEY_IASA'] = jwt_iasa
    
    # Se actualiza el settings con los jwts que agregamos
    settings.config.update(config)

    # Utils
    from pci_get_connection_db import CollectionConnection
    colection_connection = CollectionConnection(1259, settings)
    cr_admin = colection_connection.get_collections_connection()

    from pci_base_utils import PCI_Utils
    p_utils = PCI_Utils(cr=lkf_obj.cr, cr_admin=cr_admin, lkf_api=lkf_api, net=lkf_obj.net, settings=settings, lkf_obj=lkf_obj)

    # from validaciones_orden_servicio import ValidarOS
    # validar_os = ValidarOS(
    #     cr=lkf_obj.cr, 
    #     lkf_api=lkf_obj.lkf_api, 
    #     p_utils=p_utils, 
    #     form_id=lkf_obj.form_id, 
    #     current_record=lkf_obj.current_record,
    #     from_carga_prod=True
    # )

    record_id =  lkf_obj.record_id
    
    lkf_obj.carga_de_produccion(current_record)