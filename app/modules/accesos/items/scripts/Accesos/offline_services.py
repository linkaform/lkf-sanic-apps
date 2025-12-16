# coding: utf-8
from hmac import new
import os
import pytz
import sys, simplejson, json
import time
import tempfile
import unicodedata
from bson.objectid import ObjectId
from linkaform_api import settings
from account_settings import *

from accesos_utils import Accesos
from datetime import datetime

class Accesos(Accesos):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)
        
        centralized_fields = {
            'categoria':'686807d46e41614d708f6fc9',
            'icono_categoria':'686807d46e41614d708f6fca',
            'sub_categoria': '686807a7ee7705c5c8eb181a',
            'icono_sub_categoria': '686807a7ee7705c5c8eb181b',
            'incidencia': '663973809fa65cafa759eb97',
            'area': '663e5d44f5b8a7ce8211ed0f',
            'ubicacion': '663e5c57f5b8a7ce8211ed0b',
            'address': '663a7e0fe48382c5b1230902',
            'address_complement': '663a7f79e48382c5b123090a',
            'address_email': '663a7ee1e48382c5b1230907',
            'tipo_de_area': '663e5e68f5b8a7ce8211ed18',
            'num_de_habitacion': '680977786d022b9bff6e3645',
            'piso': '680977786d022b9bff6e3646',
            'address_name': '663a7e0fe48382c5b1230901',
            'address_phone': '663a7ee1e48382c5b1230906',
            'address_geolocation': '663e5c8cf5b8a7ce8211ed0c',
            'area_city': '6654187fc85ce22aaf8bb070',
            'area_status': '663e5e4bf5b8a7ce8211ed15',
            'area_state': '663e5e4bf5b8a7ce8211ed14',
            'area_qr_code': '663e5e4bf5b8a7ce8211ed13',
            'area_tag_id': '6762f7b0922cc2a2f57d4044',
            'area_foto': '6763096aa99cee046ba766ad',
            'ubicacion_nombre_comercial': '667468e3e577b8b98c852aaa',
            'address_type': '663a7f67e48382c5b1230908',
            'ubicacion_country': '663a7ca6e48382c5b12308fa',
            'nombre_del_recorrido': '6645050d873fc2d733961eba',
            'usuario_id': '638a9a99616398d2e392a9f5',
            'usuario_nombre_completo': '638a9a7767c332f5d459fc81',
            'usuario_username': '6759e4a7a9a6e13c7b26da33',
            'usuario_email': '638a9a7767c332f5d459fc82',
            'usuario_phone': '67be0c43a31e5161c47f2bba',
            'empleado_nombre_completo': '62c5ff407febce07043024dd',
            'empleado_departamento': '663bc4ed8a6b120eab4d7f1e',
            'empleado_puesto': '663bc4c79b8046ce89e97cf4',
            'empleado_rfc': '663bcbe2274189281359eb71',
            'empleado_estatus_disponibilidad': '663bcbe2274189281359eb78',
            'tipo_de_equipo': '6639a9d9d38959539f59eb9f',
            'falla_concepto': '66397bae9e8b08289a59ec86',
            'falla_subconcepto': '679124a8483c5220455bcb99',
            'empleado_apoyo_nombre_completo': '663bd36eb19b7fb7d9e97ccb',
            'empleado_apoyo_id': '663bd466b19b7fb7d9e97cdc',
            'empleado_apoyo_estatus_disponibilidad': '663bd5c0b6e749213859eb72',
            'area_salida': '663fb45992f2c5afcfe97ca8',
            'visita_autorizada_nombre_completo': '5ea0693a0c12d5a8e43d37df',
            'visita_autorizada_curp': '5ea0897550b8dfe1f4d83a9f',
            'visita_autorizada_email': '5ea069562f8250acf7d83aca',
            'visita_autorizada_telefono': '663ec042713049de31e97c93',
            'visita_autorizada_foto': '5ea35de83ab7dad56c66e045',
            'visita_autorizada_identificacion': '65ce34985fa9df3dbf9dd2d0',
            'visita_autorizada_razon_social': '65fc814fb170488cf4d44c51',
            'visita_autorizada_email_contratista': '65fc814fb170488cf4d44c53',
            'visita_autorizada_estatus': '5ea1bd280ae8bad095055e61',
            'estados_state': '663a7dd6e48382c5b12308ff',
            'estados_state_code': '663a7dd6e48382c5b1230900',
            'proveedores_nombre_comercial': '667468e3e577b8b98c852aaa',
            'proveedores_razon_social': '6687f2f37b2c023e187d6252',
            'proveedores_rfc': '667468e3e577b8b98c852aab',
            'proveedores_email_contacto': '66bfd647cd15883ed163e9b5',
            'proveedores_telefono': '66bfd666cd15883ed163e9b6',
            'proveedores_web': '66bfd66ecd15883ed163e9b7',
            'lockers_id': '66480101786e8cdb66e70124',
            'lockers_tipo': '66ccfec6acaa16b31e5593a3',
            'lockers_estatus': '663961d5390b9ec511e97ca5',
            'objetos_categoria': '66ce23efc5c4d148311adf86',
            'objetos_descripcion': '66ce23efc5c4d148311adf87',
            'objetos_nombre': '66ce2441d63bb7a3871adeaf',
        }
        # self.f.update(centralized_fields)
        # forced_values = set(centralized_fields.values())
        # for k, v in list(self.f.items()):
        #     if v in forced_values and k not in centralized_fields:
        #         del self.f[k]
        # self.f.update(centralized_fields)
        
        self.incidence_filter = {
            'reporta_incidencia': "",
            'fecha_hora_incidencia':"",
            'ubicacion_incidencia':"",
            'area_incidencia': "",
            'incidencia':"",
            'comentario_incidencia': "",
            'tipo_dano_incidencia': "",
            'dano_incidencia':"",
            'evidencia_incidencia': [],
            'documento_incidencia':[],
            'prioridad_incidencia':"",
            'notificacion_incidencia':"",
            'datos_deposito_incidencia': [],
            'tags':[],
            'categoria':"",
            'sub_categoria':"",
            'incidente':"",
            'nombre_completo_persona_extraviada':"",
            'edad':"",
            'color_piel':"",
            'color_cabello':"",
            'estatura_aproximada':"",
            'descripcion_fisica_vestimenta':"",
            'nombre_completo_responsable':"",
            'parentesco':"",
            'num_doc_identidad':"",
            'telefono':"",
            'info_coincide_con_videos':"",
            'responsable_que_entrega':"",
            'responsable_que_recibe':"",
            'afectacion_patrimonial_incidencia':[],
            'personas_involucradas_incidencia': [],
            'acciones_tomadas_incidencia':[],
            'seguimientos_incidencia':[],
            'valor_estimado':"",
            'pertenencias_sustraidas':"",
            'placas':"",
            'tipo':"",
            'marca':"",
            'modelo':"",
            'color':"",
        }
        
        self.check_area_filter = {
            "tag_id": "",
            "ubicacion": "",
            "area": "",
            "tipo_de_area": "",
            "foto_del_area": [],
            "evidencia_incidencia": [],
            "incidencias": [],
            "comentario_check_area": "",
            "status_check_area": "",
        }
        
        self.f.update({
            'bitacora_rondin_url': '690cefdca2dff2f469da17e0',
            'cantidad_areas_inspeccionadas': '68a7b68a22ac030a67b7f8f8'
        })
        
    def clean_text(self, texto):
        """
        Limpia texto: minúsculas, espacios y puntos por guiones bajos, elimina acentos
        """
        if not isinstance(texto, str):
            return ""
        
        texto = texto.lower()                # Minúsculas
        texto = texto.replace(" ", "_")      # Espacios → guiones bajos
        texto = texto.replace(".", "_")      # Puntos → guiones bajos
        
        # Eliminar acentos
        texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
        
        return texto

    def get_user_catalogs(self):
        soter_catalogs = [
            self.LISTA_INCIDENCIAS_CAT_ID,
            self.SUB_CATEGORIAS_INCIDENCIAS_ID,
            self.CATEGORIAS_INCIDENCIAS_ID,
            self.AREAS_DE_LAS_UBICACIONES_CAT_ID,
            self.UBICACIONES_CAT_ID,
            self.CONFIGURACION_RECORRIDOS_ID,
            self.USUARIOS_ID,
            self.CONF_AREA_EMPLEADOS_CAT_ID,
            self.TIPO_DE_EQUIPO_ID,
            self.LISTA_FALLAS_CAT_ID,
            self.CONF_AREA_EMPLEADOS_AP_CAT_ID,
            self.VISITA_AUTORIZADA_CAT_ID,
            self.ESTADO_ID,
            self.PROVEEDORES_CAT_ID,
            self.LOCKERS_CAT_ID,
            self.TIPO_ARTICULOS_PERDIDOS_CAT_ID,
        ]
        dbs = {}
        try:
            fields_invertido = {v: k for k, v in self.f.items()}
            for catalog_id in soter_catalogs:
                item = {}
                version = "00.00"
                info_catalog = self.lkf_api.get_catalog_id_fields(catalog_id)
                catalog_name = self.clean_text(info_catalog.get('catalog', {}).get('name', ''))
                catalog_fields = info_catalog.get('catalog', {}).get('fields', [])
                catalog_updated_at = info_catalog.get('catalog', {}).get('updated_at', '')
                
                field_items = {}
                for field in catalog_fields:
                    if not field.get('field_type') in ['catalog']:
                        field_items.update({
                            field.get('field_id'): fields_invertido.get(field.get('field_id'), self.clean_text(field.get('label', '')))
                        })
                
                if catalog_updated_at:
                    date_part = catalog_updated_at[:10]
                    dt = datetime.strptime(date_part, '%Y-%m-%d')
                    version = f"{dt.year % 100:02d}.{dt.month:02d}"
                
                item = {
                    'db_name': f'catalog_records_{info_catalog.get("catalog", {}).get("catalog_id", 0)}',
                    'field_name': field_items,
                    'version': version,
                    'host': '',
                    'filter': ''
                }
                dbs[catalog_name] = item
        except Exception as e:
            return {'status_code': 400, 'msg': 'error', 'data': str(e)}
        return {'status_code': 200, 'msg': 'success', 'data': dbs}
    
    def get_folio_incidencia(self, record_id):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_INCIDENCIAS,
                "_id": ObjectId(record_id)
            }},
            {"$limit": 1},
            {"$sort": {"created_at": -1}},
            {"$project": {
                "_id": 0,
                "folio": "$folio"
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = self.unlist(response)
        return format_response

    def sync_incidence_to_lkf(self, record):
        status = {}
        record_id = record.pop('_id', None)
        record = record.get('record', {})
        folio = self.get_folio_incidencia(record_id)
        payload = {k: record[k] for k in self.incidence_filter.keys() if k in record}
            
        if isinstance(record, dict) and 'status_code' in record:
            return record
        elif isinstance(record, dict) and folio:
            folio = folio.get('folio', '')
            response = self.update_incidence(payload, folio)
        else:
            payload.update({'record_id': record_id})
            response = acceso_obj.create_incidence(payload)

        record = self.cr_db.get(record_id)
        if response.get('status_code') in [200, 201, 202]:
            record['status'] = 'synced'
            self.cr_db.save(record)
            status = {'status_code': 200, 'type': 'success', 'msg': 'Record synced successfully', 'data': {}}
        else:
            record['status'] = 'error'
            self.cr_db.save(record)
            status = {'status_code': 400, 'type': 'error', 'msg': response, 'data': {}}
        return status

    def get_couch_record(self, _id, _rev=None):
        if not _id:
            return {'status_code': 400, 'type': 'error', 'msg': 'ID is required', 'data': {}}
        
        record = self.cr_db.get(_id, revs_info=True)
        if not record:
            return {'status_code': 404, 'type': 'error', 'msg': 'Record not found', 'data': {}}

        current_rev = record.rev
        all_revs = [r['rev'] for r in record['_revs_info'] if r['status'] == 'available']

        media = []
        if _rev == current_rev:
            attachments = record.get("_attachments", {})
            print('✅ Revisión actual encontrada')
            # for name in attachments:
            #     attachment = self.cr_db.get_attachment(_id, name)
            #     data = attachment.read()
            #     upload_image = self.upload_image_from_couchdb(data, name, self.BITACORA_INCIDENCIAS, self.f['evidencia_incidencia'])
            #     media.append(upload_image)
            # record['status'] = 'received'
            # self.cr_db.save(record)
            return record
        elif _rev in all_revs:
            print('⚠️ Revisión vieja')
            return {'status_code': 461, 'type': 'error', 'msg': 'Old revision found', 'data': {}}
        else:
            print('🕓 Revisión aún no propagada')
            return {'status_code': 462, 'type': 'error', 'msg': 'Revision not yet propagated', 'data': {}}

    def upload_image_from_couchdb(self, image_data, attachment_name, id_forma_seleccionada, id_field):
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, attachment_name)

        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(image_data)

        rb_file = open(temp_file_path, 'rb')
        dir_file = {'File': rb_file}

        try:
            upload_data = {'form_id': id_forma_seleccionada, 'field_id': id_field}
            upload_url = self.lkf_api.post_upload_file(data=upload_data, up_file=dir_file)
            rb_file.close()
        except Exception as e:
            rb_file.close()
            os.remove(temp_file_path)
            print("Error al subir el archivo:", e)
            return {"error": "Fallo al subir el archivo"}

        try:
            file_url = upload_url['data']['file']
            update_file = {'file_name': attachment_name, 'file_url': file_url}
        except KeyError:
            print('No se pudo obtener la URL del archivo')
            update_file = {"error": "Fallo al obtener la URL del archivo"}
        finally:
            os.remove(temp_file_path)
        return update_file
    
    def assign_user_inbox(self, data):
        user_name = data.get(self.USUARIOS_OBJ_ID, {}).get(self.mf['nombre_usuario'], '')
        self.cr_db = self.lkf_api.couch.set_db(f'clave_{self.user_id}')
        nombre_recorrido = data.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.mf['nombre_del_recorrido'], '')
        ubicacion_recorrido = data.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.Location.f['location'], '')
        
        recorrido_info = self.get_info_recorrido(nombre_recorrido, ubicacion_recorrido)
        
        #! Revisar timezone en bitacora si sera necesario
        # user_data = self.lkf_api.get_user_by_id(self.user_id)
        # user_timezone = user_data.get('timezone', 'America/Mexico_City')

        status = {}
        lat = 0.0
        long = 0.0
        if len(self.geolocation) > 1:
            lat = self.geolocation[0]
            long = self.geolocation[1]
        epoc_today = int(time.time())
        format_check_areas = self.get_area_images(data.get(self.f['grupo_areas_visitadas'], []))
        for i in format_check_areas:
            i['checked'] = False
            i['checked_at'] = ''
            i['check_area_id'] = ''
        inbox_record = {
            "_id": self.record_id,
            "type": "rondin",
            "inbox": True,
            "status": "synced",
            "status_rondin": "new",
            "created_at": epoc_today,
            "updated_at": epoc_today,
            "created_by_id": self.user_id,
            "created_by_name": self.user_name,
            "geolocation": {
                "lat": lat,
                "long": long
            },
            "record": {
                "user_name": user_name,
                "nombre_rondin": nombre_recorrido,
                "ubicacion_rondin": ubicacion_recorrido,
                "duracion_estimada": recorrido_info.get('duracion_estimada', ''),
                "fecha_programada": data.get(self.f['fecha_programacion'], ''),
                "fecha_inicio": "",
                "fecha_finalizacion": "",
                "fecha_pausa": "",
                "fecha_reanudacion": "",
                "ultimo_check_area_id": "",
                "check_areas": format_check_areas,
            }
        }
        try:
            result = self.cr_db.save(inbox_record)
            if result:
                status = {'status_code': 200, 'type': 'success', 'msg': 'Inbox assigned successfully', 'data': {
                    'assigned_user_id': self.user_id,
                    'assigned_user': user_name,
                    'bitacora_record_id': self.record_id,
                    'bitacora_ubicacion': data.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.Location.f['location'], ''),
                    'bitacora_nombre_rondin': data.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.mf['nombre_del_recorrido'], ''),
                    'bitacora_fecha_programada': data.get(self.f['fecha_programacion'], ''),
                }}
        except Exception as e:
            status = {'status_code': 400, 'type': 'error', 'msg': str(e), 'data': {}}
        return status

    def get_area_images(self, areas):
        location = self.answers.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.Location.f['location'], '')
        format_areas = [area.get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.Location.f['area'], '') for area in areas]
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": 121677, #TODO: Modularizar id
                f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.Location.f['area']}": {"$in": format_areas}
            }},
            {"$project": {
                "_id": 0,
                "tag_id": f"$answers.{self.f['area_tag_id']}",
                "ubicacion": f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}",
                "area": f"$answers.{self.Location.f['area']}",
                "tipo_de_area": f"$answers.{self.Location.TIPO_AREA_OBJ_ID}.{self.f['tipo_de_area']}",
                "foto_del_area": f"$answers.{self.f['area_foto']}",
            }}
        ]
        res = self.cr.aggregate(query)
        format_res = list(res)
        return format_res
    
    def get_info_recorrido(self, nombre_recorrido, ubicacion_recorrido):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": 121742, #TODO: Modularizar id
                f"answers.{self.f['nombre_del_recorrido']}": nombre_recorrido,
                f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": ubicacion_recorrido
            }},
            {"$limit": 1},
            {"$project": {
                "_id": 0,
                "duracion_estimada": f"$answers.{self.f['duracion_estimada']}",
            }}
        ]
        res = self.cr.aggregate(query)
        format_res = {}
        if res:
            res = list(res)
            format_res = self.unlist(res)
        return format_res
    
    def sync_check_area_to_lkf(self, record):
        status = {}
        rondin_id = record.get('rondin_id', '')
        record_id = record.pop('_id', None)
        record = record.get('record', {})
        payload = {k: record[k] for k in self.check_area_filter.keys() if k in record}
            
        if isinstance(record, dict) and 'status_code' in record:
            return record
        else:
            payload.update({
                'record_id': record_id,
                'rondin_id': rondin_id
            })
            response = self.create_check_area(payload)

        record = self.cr_db.get(record_id)
        if response.get('status_code') in [200, 201, 202]:
            record['status'] = 'received'
            record['folio'] = response.get('json', {}).get('folio', '')
            self.cr_db.save(record)
            status = {'status_code': 200, 'type': 'success', 'msg': 'Record received successfully', 'data': {}}
            
            #! 1. Obtener la bitacora del rondin en Linkaform y obtener las areas ya revisadas
            time.sleep(5)
            bitacora_in_lkf = self.get_bitacora_by_id(rondin_id)
            checks_in_lkf = []
            for item in bitacora_in_lkf.get('areas_del_rondin', []):
                if item.get('fecha_hora_inspeccion_area'):
                    checks_in_lkf.append(item.get('incidente_area'))
                
            #! 2. Obtener la bitacora del rondin en CouchDB y obtener las areas ya revisadas
            bitacora_in_couch = self.cr_db.get(rondin_id)
            ultimo_check_area_id = bitacora_in_couch.get('record', {}).get('ultimo_check_area_id', '')
            checks_in_couch = bitacora_in_couch.get('record', {}).get('check_areas', [])
            format_checks_in_couch = []
            for item in checks_in_couch:
                #! 2.1 Se compara si el check area ya existe en la bitacora de Linkaform
                if item.get('checked') and not item.get('area') in checks_in_lkf:
                    format_checks_in_couch.append(item.get('check_area_id'))

            #! 3. Si el ultimo check area es igual al check area que se acaba de crear y hay nuevos checks
            #! se actualiza la bitacora en Linkaform
            if ultimo_check_area_id and ultimo_check_area_id == record_id and format_checks_in_couch:
                new_checks = self.cr_db.find({
                    "selector": {
                        "_id": {"$in": format_checks_in_couch}
                    }
                })
                new_areas = {}
                for check in new_checks:
                    new_areas[check.get('record', {}).get('area')] = check.get('record', {})
                    new_areas[check.get('record', {}).get('area')].update({
                        'fecha_check': check.get('created_at', ''),
                        'record_id': check.get('_id', '')
                    })
                new_incidencias = bitacora_in_couch.get('record', {}).get('incidencias', [])
                bitacora_response = self.update_bitacora(bitacora_in_lkf, new_incidencias, new_areas)
                print("bitacora_response", bitacora_response)
        else:
            record['status'] = 'error'
            self.cr_db.save(record)
            status = {'status_code': 400, 'type': 'error', 'msg': response, 'data': {}}
        return status
    
    def get_bitacora_by_id(self, record_id):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                "_id": ObjectId(record_id)
            }},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "answers": 1
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = self.unlist(response)
        return format_response

    def parse_date_for_sorting(self, date_str):
        if not date_str or not date_str.strip():
            return datetime.max
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.max

    def format_incidencias_to_bitacora(self, bitacora_in_lkf, new_incidencias, new_areas):
        incidencias_list = []
        incidencias_existentes = bitacora_in_lkf.get('bitacora_rondin_incidencias', [])
        
        for incidencia in new_incidencias:
            fecha_incidencia = incidencia.get('fecha_incidencia')
            fecha_str = ""
            if fecha_incidencia:
                try:
                    s = fecha_incidencia.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(s)
                    fecha_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    fecha_str = ""
            
            ya_existe = False
            for inc_existente in incidencias_existentes:
                if (inc_existente.get('tipo_de_incidencia') == incidencia.get('incidente') and
                    inc_existente.get('categoria') == incidencia.get('categoria') and
                    inc_existente.get('nombre_area_salida') == incidencia.get('area') and
                    inc_existente.get('fecha_hora_incidente_bitacora') == fecha_str):
                    ya_existe = True
                    break
            
            if not ya_existe:
                new_item = {
                    self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID: {
                        self.f['nombre_area_salida']: incidencia.get('area'),
                    },
                    self.f['fecha_hora_incidente_bitacora']: fecha_str,
                    self.LISTA_INCIDENCIAS_CAT_OBJ_ID: {
                        self.f['categoria']: incidencia.get('categoria', ''),
                        self.f['sub_categoria']: incidencia.get('sub_categoria', ''),
                        self.f['incidente']: incidencia.get('incidente', ''),
                    },
                    self.f['incidente_open']: incidencia.get('otro_incidente', ''),
                    self.f['comentario_incidente_bitacora']: incidencia.get('comentario', ''),
                    self.f['incidente_accion']: incidencia.get('accion', ''),
                    self.f['incidente_evidencia']: incidencia.get('evidencia', []),
                    self.f['incidente_documento']: incidencia.get('documento', []),
                }
                incidencias_list.append(new_item)
        
        for item in new_areas.values():
            ts = item.get('fecha_check')
            fecha_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""
            area = item.get('area', '')
            
            for incidencia in item.get('incidencias', []):
                ya_existe = False
                for inc_existente in incidencias_existentes:
                    if (inc_existente.get('tipo_de_incidencia') == incidencia.get('incidente') and
                        inc_existente.get('categoria') == incidencia.get('categoria') and
                        inc_existente.get('nombre_area_salida') == area and
                        inc_existente.get('fecha_hora_incidente_bitacora') == fecha_str):
                        ya_existe = True
                        break
                
                if not ya_existe:
                    new_item = {
                        self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID: {
                            self.f['nombre_area_salida']: area,
                        },
                        self.f['fecha_hora_incidente_bitacora']: fecha_str,
                        self.LISTA_INCIDENCIAS_CAT_OBJ_ID: {
                            self.f['categoria']: incidencia.get('categoria', ''),
                            self.f['sub_categoria']: incidencia.get('sub_categoria', ''),
                            self.f['incidente']: incidencia.get('incidente', ''),
                        },
                        self.f['incidente_open']: incidencia.get('otro_incidente', ''),
                        self.f['comentario_incidente_bitacora']: incidencia.get('comentario', ''),
                        self.f['incidente_accion']: incidencia.get('accion', ''),
                        self.f['incidente_evidencia']: incidencia.get('evidencia', []),
                        self.f['incidente_documento']: incidencia.get('documento', []),
                    }
                    incidencias_list.append(new_item)
        
        for incidencia in incidencias_existentes:
            new_item = {
                self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID: {
                    self.f['nombre_area_salida']: incidencia.get('nombre_area_salida', ''),
                },
                self.f['fecha_hora_incidente_bitacora']: incidencia.get('fecha_hora_incidente_bitacora', ''),
                self.LISTA_INCIDENCIAS_CAT_OBJ_ID: {
                    self.f['categoria']: incidencia.get('categoria', ''),
                    self.f['sub_categoria']: incidencia.get('sub_categoria', ''),
                    self.f['incidente']: incidencia.get('tipo_de_incidencia', ''),
                },
                self.f['incidente_open']: incidencia.get('incidente_open', ''),
                self.f['comentario_incidente_bitacora']: incidencia.get('comentario_incidente_bitacora', ''),
                self.f['incidente_accion']: incidencia.get('incidente_accion', ''),
                self.f['incidente_evidencia']: incidencia.get('incidente_evidencia', []),
                self.f['incidente_documento']: incidencia.get('incidente_documento', []),
            }
            incidencias_list.append(new_item)
        return incidencias_list

    def update_bitacora(self, bitacora_in_lkf, new_incidencias, new_areas):
        answers={}
        areas_list = []
        conf_recorrido = {}
        
        incidencias_list = self.format_incidencias_to_bitacora(bitacora_in_lkf, new_incidencias, new_areas)
        answers[self.f['bitacora_rondin_incidencias']] = incidencias_list
        
        for item in bitacora_in_lkf.get('areas_del_rondin', []):
            nombre_area = item.get('incidente_area')
            check = new_areas.get(nombre_area)
            if check:
                ts = check.get('fecha_check')
                fecha_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else ""
                item.update({
                    'fecha_hora_inspeccion_area': fecha_str,
                    'foto_evidencia_area_rondin': check.get('evidencia_incidencia', []),
                    'comentario_area_rondin': check.get('comentario_check_area', ''),
                    'url_registro_rondin': f"https://app.linkaform.com/#/records/detail/{check.get('record_id', '')}",
                })

        for key, value in bitacora_in_lkf.items():
            if key == 'new_user_complete_name':
                answers[self.USUARIOS_OBJ_ID] = {
                    self.f['new_user_complete_name']: value,
                    self.f['new_user_id']: [self.user_id],
                    self.f['new_user_email']: [self.user_email]
                }
            elif key == 'fecha_programacion':
                answers[self.f['fecha_programacion']] = value
            elif key == 'fecha_inicio_rondin':
                answers[self.f['fecha_inicio_rondin']] = value
            elif key == 'fecha_fin_rondin':
                answers[self.f['fecha_fin_rondin']] = value
            elif key == 'estatus_del_recorrido' and value:
                answers[self.f['estatus_del_recorrido']] = value
            elif key == 'incidente_location':
                conf_recorrido.update({
                    self.f['ubicacion_recorrido']: value
                })
            elif key == 'nombre_del_recorrido':
                conf_recorrido.update({
                    self.f['nombre_del_recorrido']: value
                })
            elif key == 'estatus_del_recorrido':
                answers[self.f['estatus_del_recorrido']] = value
            elif key == 'areas_del_rondin':
                for item in value:
                    areas_list.append({
                        self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                            self.f['nombre_area']: item.get('incidente_area', ''),
                        },
                        self.f['fecha_hora_inspeccion_area']: item.get('fecha_hora_inspeccion_area', ''),
                        self.f['foto_evidencia_area_rondin']: item.get('foto_evidencia_area_rondin', []),
                        self.f['comentario_area_rondin']: item.get('comentario_area_rondin', ''),
                        self.f['url_registro_rondin']: item.get('url_registro_rondin', '')
                    })
                    
        all_areas_sorted = sorted(
            areas_list,
            key=lambda x: self.parse_date_for_sorting(x.get(self.f['fecha_hora_inspeccion_area'], ''))
        )
        answers[self.f['areas_del_rondin']] = all_areas_sorted
        answers[self.f['estatus_del_recorrido']] = 'en_proceso'
        answers[self.CONFIGURACION_RECORRIDOS_OBJ_ID] = conf_recorrido
        if not answers.get(self.f['fecha_inicio_rondin']):
            answers[self.f['fecha_inicio_rondin']] = all_areas_sorted[0].get(self.f['fecha_hora_inspeccion_area'], '') if len(all_areas_sorted) > 0 else ''

        if answers:
            metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_RONDINES)
            metadata.update(self.get_record_by_folio(bitacora_in_lkf.get('folio'), self.BITACORA_RONDINES, select_columns={'_id': 1}, limit=1))

            metadata.update({
                'properties': {
                    "device_properties": {
                        "system": "Addons",
                        "process":"Actualizacion de Bitacora", 
                        "accion":'rondines_cache', 
                        "folio": bitacora_in_lkf.get('folio'), 
                        "archive": "rondines_cache.py"
                    }
                },
                'answers': answers,
                '_id': bitacora_in_lkf.get('_id')
            })
            res = self.net.patch_forms_answers(metadata)
            return res
        
    def create_check_area(self, data):
        # metadata = self.lkf_api.get_metadata(form_id=self.CHECK_UBICACIONES)
        answers = {}
        metadata = self.lkf_api.get_metadata(form_id=137161) #TODO: Modularizar id
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de check area",
                    "Action": "create_check_area",
                    "File": "accesos/app.py"
                }
            },
        })
        if data.get('record_id'):
            metadata.update({
                "id": data.pop('record_id')
            })
        if data.get('rondin_id'):
            rondin_id = data.pop('rondin_id')
            answers[self.f['bitacora_rondin_url']] = f"https://app.linkaform.com/#/records/detail/{rondin_id}"
        #---Define Answers
        answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]={}
        answers[self.f['check_status']] = "continuar_siguiente_punto_de_inspección"
        for key, value in data.items():
            if key == 'tag_id':
                answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID].update({
                    self.f['area_tag_id']: value,
                    self.Location.f['location']: [data.get('ubicacion', '')],
                    self.Location.f['area']: [data.get('area', '')],
                    self.f['tipo_de_area']: [data.get('tipo_de_area', '')],
                    self.f['area_foto']: [data.get('foto_del_area', '')],
                })
            elif key == 'evidencia_incidencia':
                answers[self.f['foto_evidencia_area']] = value
            elif key == 'incidencias':
                incidencias = data.get('incidencias', [])
                if incidencias:
                    incidencias_list = []
                    for incidencia in incidencias:
                        item = {}
                        if incidencia.get('categoria'):
                            item = {self.LISTA_INCIDENCIAS_CAT_OBJ_ID: {
                                self.f['categoria']: incidencia.get('categoria', ''),
                                self.f['sub_categoria']: incidencia.get('sub_categoria', ''),
                                self.f['incidente']: incidencia.get('incidente', ''),
                            }}
                        item.update({
                            self.f['incidente_open']: incidencia.get('otro_incidente', ''),
                            self.f['incidente_comentario']: incidencia.get('comentario', ''),
                            self.f['incidente_accion']: incidencia.get('accion', ''),
                            self.f['incidente_evidencia']: incidencia.get('evidencia', ''),
                            self.f['incidente_documento']: incidencia.get('documento', ''),
                        })
                        incidencias_list.append(item)
                    answers[self.f['grupo_incidencias_check']] = incidencias_list
            elif key == 'comentario_check_area':
                answers[self.f['comentario_check_area']] = value
            elif key == 'status_check_area':
                answers[self.f['check_status']] = value
            else:
                continue
            
        
        metadata.update({'answers':answers})
        return self.lkf_api.post_forms_answers(metadata)
    
    def delete_rondines(self, records):
        status = {}
        answers = {}
        bad_items = []
        good_items = []
        
        if not records:
            return {'status_code': 400, 'type': 'error', 'msg': 'No records provided', 'data': {}}
        
        db_name = f'clave_{self.user_id}'
        self.cr_db = self.lkf_api.couch.set_db(db_name)
        for item in records:
            _id = item.get('_id', None)
            _rev = item.get('_rev', None)
            
            if not _id or not _rev:
                bad_items.append(item)
                continue
            
            record = self.get_couch_record(_id=_id, _rev=_rev)
            
            if record.get('status_code') in [400, 404, 461, 462]:
                bad_items.append(item)
                continue
            
            if record.get('status_rondin') == 'deleted':
                good_items.append(_id)
                record['inbox'] = False
                record['status'] = 'received'
                self.cr_db.save(record)
        
        answers[self.f['estatus_del_recorrido']] = 'cancelado'
        if good_items:
            res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.BITACORA_RONDINES, record_id=good_items)
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                status = {'status_code': 200, 'type': 'success', 'msg': 'Rondines deleted successfully', 'data': {}}
            else: 
                status = {'status_code': 400, 'type': 'error', 'msg': res, 'data': {}}
        if bad_items:
            status.update({'data': {'bad_items': bad_items, 'good_items': good_items}})
        return status
    
    def complete_rondines(self, records):
        status = {}
        answers = {}
        bad_items = []
        good_items = []
        
        if not records:
            return {'status_code': 400, 'type': 'error', 'msg': 'No records provided', 'data': {}}
        
        db_name = f'clave_{self.user_id}'
        self.cr_db = self.lkf_api.couch.set_db(db_name)
        for item in records:
            _id = item.get('_id', None)
            _rev = item.get('_rev', None)
            
            if not _id or not _rev:
                bad_items.append(item)
                continue
            
            record = self.get_couch_record(_id=_id, _rev=_rev)
            
            if record.get('status_code') in [400, 404, 461, 462]:
                bad_items.append(item)
                continue
            
            if record.get('status_rondin') == 'completed':
                good_items.append(_id)
                record['inbox'] = False
                record['status'] = 'received'
                self.cr_db.save(record)
        
        answers[self.f['estatus_del_recorrido']] = 'realizado'
        if good_items:
            res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.BITACORA_RONDINES, record_id=good_items)
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                status = {'status_code': 200, 'type': 'success', 'msg': 'Rondines completed successfully', 'data': {}}
            else: 
                status = {'status_code': 400, 'type': 'error', 'msg': res, 'data': {}}
        if bad_items:
            status.update({'data': {'bad_items': bad_items, 'good_items': good_items}})
        return status
    
    def get_user_data(self, user_id):
        query = [{"$match": {
            "deleted_at": {"$exists": False},
            "form_id": 129958, #TODO: Modularizar id
            f"answers.{self.mf['id_usuario']}": user_id
        }},
        {"$limit": 1},
        {"$sort": {"created_at": -1}},
        {"$project": {
            "_id": 0,
            "id": f"$answers.{self.mf['id_usuario']}",
            "name": f"$answers.{self.mf['nombre_usuario']}",
            "email": f"$answers.{self.mf['email_visita_a']}",
        }}]
        reponse = self.format_cr(self.cr.aggregate(query))
        format_response = self.unlist(reponse)
        return format_response
    
    def reasignar_rondines(self, records, user_to_assign):
        status = {}
        answers = {}
        bad_items = []
        good_items = []
        
        user_id = user_to_assign.get('id', 0)
        name = user_to_assign.get('name', '')
        user_data = self.get_user_data(user_id=user_id)
        email = user_data.get('email', '')
        
        if not records:
            return {'status_code': 400, 'type': 'error', 'msg': 'No records provided', 'data': {}}
        
        db_name = f'clave_{self.user_id}'
        self.cr_db = self.lkf_api.couch.set_db(db_name)
        for item in records:
            _id = item.get('_id', None)
            _rev = item.get('_rev', None)
            
            if not _id or not _rev:
                bad_items.append(item)
                continue
            
            record = self.get_couch_record(_id=_id, _rev=_rev)
            
            if record.get('status_code') in [400, 404, 461, 462]:
                bad_items.append(item)
                continue
            
            if record:
                good_items.append(_id)
                record['inbox'] = False
                record['status_rondin'] = 'deleted'
                record['status'] = 'received'
                self.cr_db.save(record)
        
        answers[self.USUARIOS_OBJ_ID] = {
            self.mf['nombre_usuario']: name,
            self.mf['id_usuario']: [user_id],
            self.mf['email_visita_a']: [email],
        }
        if good_items:
            res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.BITACORA_RONDINES, record_id=good_items)
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                status = {'status_code': 200, 'type': 'success', 'msg': 'Rondines assigned successfully', 'data': {}}
            else: 
                status = {'status_code': 400, 'type': 'error', 'msg': res, 'data': {}}
        if bad_items:
            status.update({'data': {'bad_items': bad_items, 'good_items': good_items}})
        return status

    def get_active_guards(self):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.REGISTRO_ASISTENCIA,
                f"answers.{self.f['fecha_inicio_turno']}": {"$exists": True},
                f"answers.{self.f['fecha_cierre_turno']}": {"$exists": False},
            }},
            {"$project": {
                "_id": 0,
                "created_by_id": 1,
                "created_by_name": 1,
                "created_by_email": 1
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = []
        if response:
            for item in response:
                new_item = {
                    'guard_id': item.get('created_by_id', 0),
                    'guard_name': item.get('created_by_name', ''),
                    'guard_email': item.get('created_by_email', ''),
                }
                format_response.append(new_item)
        response = {'status_code': 200, 'type': 'success', 'msg': 'Active guards retrieved successfully', 'data': format_response}
        return response
        
if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv)
    acceso_obj.console_run()
    data_rondin = acceso_obj.current_record
    acceso_obj.user_name = data_rondin.get('created_by_name', '')
    acceso_obj.user_id = data_rondin.get('created_by_id', acceso_obj.user.get('user_id', 0))
    acceso_obj.user_email = data_rondin.get('created_by_email', acceso_obj.user.get('email', ''))
    acceso_obj.geolocation = data_rondin.get('geolocation', [])
    script_attr = acceso_obj.data
    data = acceso_obj.data.get('data', {})
    option = data.get("option", script_attr.get('option', ''))
    _id = data.get("_id", None)
    _rev = data.get("_rev", None)
    records = data.get("records", [])
    user_to_assign = data.get("user_to_assign", {})

    response = {}
    if option == 'get_user_catalogs':
        response = acceso_obj.get_user_catalogs()
    elif option == 'sync_to_lkf':
        db_name = f'clave_{acceso_obj.user_id}'
        acceso_obj.cr_db = acceso_obj.lkf_api.couch.set_db(db_name)
        record = acceso_obj.get_couch_record(_id=_id, _rev=_rev)
        record = dict(record)
        type_sync = record.get('type', '')
        
        if type_sync == 'incidencia':
            response = acceso_obj.sync_incidence_to_lkf(record=record)
        elif type_sync == 'check_area':
            response = acceso_obj.sync_check_area_to_lkf(record=record)
        elif type_sync == 'error':
            response = record
        else:
            response = {'status_code': 400, 'type': 'error', 'msg': 'Unknown error', 'data': {
                'type_sync': type_sync,
                'record': record,
                'db_name': db_name,
            }}

    elif option == 'assign_user_inbox':
        response = acceso_obj.assign_user_inbox(data=acceso_obj.answers)
    elif option == 'complete_rondines':
        response = acceso_obj.complete_rondines(records=records)
    elif option == 'delete_rondines':
        response = acceso_obj.delete_rondines(records=records)
    elif option == 'reasignar_rondines':
        response = acceso_obj.reasignar_rondines(records=records, user_to_assign=user_to_assign)
    elif option == 'get_active_guards':
        response = acceso_obj.get_active_guards()
    else:
        response = {'status_code': 400, 'type': 'error', 'msg': 'Invalid option', 'data': {}}

    sys.stdout.write(simplejson.dumps(response))