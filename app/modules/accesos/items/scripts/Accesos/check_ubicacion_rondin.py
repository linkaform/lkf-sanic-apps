# coding: utf-8
import json
from math import e
import sys, simplejson
from datetime import datetime
import pytz
from bson import ObjectId

from accesos_utils import Accesos

from account_settings import *
from datetime import datetime, timedelta

class Accesos(Accesos):
    
    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        
        self.f.update({
            'folio_del_check': '688a584dfa0d4a318d9ff389'
        })
        
    def get_recorridos_by_area(self, ubicacion, area_rondin):
        """
        Recibe: El area que se buscara en la configuracion de recorridos
        Retorna: Una lista de objetos con los nombres y ids de los recorridos que tengan esa area
        Error: Arroja una exception
        """
        if not area_rondin:
            raise Exception('No se proporciono el area a buscar en la configuracion de recorridos')

        query = [
            {
                '$match': {
                    'deleted_at': {'$exists': False},
                    'form_id': self.CONFIGURACION_DE_RECORRIDOS_FORM,
                    f"answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": ubicacion,
                    f"answers.{self.f['grupo_de_areas_recorrido']}": {'$exists': True}
                }
            },
            {'$unwind':f"$answers.{self.f['grupo_de_areas_recorrido']}"},
            {'$project':
                {
                    'area':f"$answers.{self.f['grupo_de_areas_recorrido']}.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area']}",
                    'nombre_recorrido':f"$answers.{self.f['nombre_del_recorrido']}",
                    'ubicacion_recorrido': f"$answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_recorrido']}"
                }
            },
            {'$match':
                {'area':area_rondin}
            }
        ]
        recorridos = self.format_cr(self.cr.aggregate(query))
        return recorridos

    def search_rondin_by_name(self, names=[], status_list=['programado', 'en_proceso']):
        """
        Recibe: Una lista de nombres de recorridos y una lista de estatus para filtrar los recorridos
        Retorna: En formato de lista el primer rondin que cumpla con los criterios
        Error: 
        """
        format_names = []
        for name in names:
            format_names.append(name.get('nombre_recorrido', ''))

        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.f['nombre_del_recorrido']}": {"$in": format_names},
                f"answers.{self.f['estatus_del_recorrido']}": {"$in": status_list},
            }},
            {'$project': {
                '_id': 1,
                'fecha_programacion': f"$answers.{self.f['fecha_programacion']}",
                'answers': f"$answers"
            }},
            {'$sort': {'fecha_programacion': 1}},
            {'$limit': 1}
        ]

        rondin = self.format_cr(self.cr.aggregate(query))
        return rondin

    def check_area_in_rondin(self, data_rondin, area_rondin, rondin, record_id):
        """
        Recibe: Las answers del check de ubicacion, el area que se hice check de ubicacion y el registro de rondin
        Retorna: La respuesta de la api al hacer el patch de un registro
        Error: La respuesta de la api al hacer el patch de un registro
        """
        tz = pytz.timezone('America/Mexico_City')
        today = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        rondin = self.unlist(rondin)
        format_id_rondin = rondin.get('_id', '')
        rondin_en_progreso = True
        answers={}

        # print('rondinnnnnnnnnnnnnnnnn', simplejson.dumps(rondin, indent=3))

        if not rondin.get('fecha_inicio_rondin'):
            rondin['fecha_inicio_rondin'] = today

        conf_recorrido = {}
        for key, value in rondin.items():
            if key == 'fecha_programacion':
                answers[self.f['fecha_programacion']] = value
            elif key == 'fecha_inicio_rondin':
                answers[self.f['fecha_inicio_rondin']] = value
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
                areas_rondin = {}
                items = []
                for index, item in enumerate(value):
                    if item.get('incidente_area', '') == area_rondin:
                        obj = {
                            self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                                self.f['nombre_area']: area_rondin
                            },
                            self.f['fecha_hora_inspeccion_area']: today,
                            self.f['foto_evidencia_area_rondin']: data_rondin.get(self.f['foto_evidencia_area'], []),
                            self.f['comentario_area_rondin']: data_rondin.get(self.f['comentario_check_area'], ''),
                            self.f['url_registro_rondin']: f"https://app.linkaform.com/#/records/detail/{record_id}"
                        }
                    else:
                        obj = {
                            self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                                self.f['nombre_area']: item.get('incidente_area', '')
                            },
                            self.f['fecha_hora_inspeccion_area']: item.get('fecha_hora_inspeccion_area', ''),
                            self.f['foto_evidencia_area_rondin']: item.get('foto_evidencia_area_rondin', []),
                            self.f['comentario_area_rondin']: item.get('comentario_area_rondin', '')
                        }
                    items.append(obj)

                items_sorted = sorted(
                    items,
                    key=lambda x: not bool(x.get(self.f['fecha_hora_inspeccion_area'], '').strip())
                )

                rondin_en_progreso = True
                for idx, obj in enumerate(items_sorted):
                    if not obj.get(self.f['fecha_hora_inspeccion_area']):
                        rondin_en_progreso = True
                    else:
                        rondin_en_progreso = False
                    areas_rondin[str(idx)] = obj

                answers[self.f['areas_del_rondin']] = areas_rondin
            else:
                pass

        answers[self.CONFIGURACION_RECORRIDOS_OBJ_ID] = conf_recorrido
        answers[self.f['estatus_del_recorrido']] = 'en_proceso' if rondin_en_progreso else 'realizado'
        answers[self.f['fecha_fin_rondin']] = today if data_rondin.get(self.f['check_status'], '') == 'finalizado' else ''
        
        format_list_incidencias = []
        for incidencia in rondin.get('bitacora_rondin_incidencias', []):
            inc = incidencia.get(self.f['tipo_de_incidencia'])
            if inc:
                incidencia.pop(self.f['tipo_de_incidencia'], None)
                incidencia.update({
                    self.LISTA_INCIDENCIAS_CAT_OBJ_ID: {
                        self.f['tipo_de_incidencia']: inc
                    }
                })
                format_list_incidencias.append(incidencia)
            
        rondin['bitacora_rondin_incidencias'] = format_list_incidencias
             
        for incidencia in data_rondin.get(self.f['grupo_incidencias_check'], []):
            rondin['bitacora_rondin_incidencias'].append(incidencia)
        
        incidencias_list = rondin['bitacora_rondin_incidencias']
        incidencias_dict = {str(idx): incidencia for idx, incidencia in enumerate(incidencias_list)}
        answers[self.f['bitacora_rondin_incidencias']] = incidencias_dict
        
        if data_rondin.get(self.f['check_status']) == 'finalizado':
            answers[self.f['estatus_del_recorrido']] = 'realizado'

        # print("ans", simplejson.dumps(answers, indent=4))

        if answers:
            res= self.lkf_api.patch_multi_record(answers=answers, form_id=self.BITACORA_RONDINES, record_id=[format_id_rondin])
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                return res
            else: 
                return res
            
    def get_areas_recorrido(self, record_id):
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.CONFIGURACION_DE_RECORRIDOS_FORM,
                "_id": ObjectId(record_id)
            }},
            {'$project': {
                '_id': 0,
                'areas_recorrido': f'$answers.{self.f["grupo_de_areas_recorrido"]}'
            }},
            {'$limit': 1}
        ]

        res = self.format_cr(self.cr.aggregate(query))
        formatted_res = self.unlist(res)
        formatted_res = formatted_res.get('areas_recorrido', [])
        return formatted_res

    def create_rondin(self, data_rondin, area_rondin, register_id, nombres_recorrido=[]):
        nombre_recorrido = ''
        ubicacion_recorrido = ''
        record_id = ''

        for nombre in nombres_recorrido:
            nombre_recorrido = nombre.get('nombre_recorrido', '')
            ubicacion_recorrido = nombre.get('ubicacion_recorrido', '')
            record_id = nombre.get('_id', '')

        # Validar record_id antes de continuar
        if not record_id:
            raise Exception("No se encontró un record_id válido para obtener las áreas del recorrido.")

        areas_recorrido = self.get_areas_recorrido(record_id)

        metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_RONDINES)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de Rondin",
                    "Action": "check_ubicacion_rondin",
                    "File": "accesos/check_ubicacion_rondin.py"
                }
            },
        })
        answers = {}

        tz = pytz.timezone('America/Mexico_City')
        today = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

        answers[self.f['fecha_programacion']] = today
        answers[self.f['fecha_inicio_rondin']] = today

        answers[self.CONFIGURACION_RECORRIDOS_OBJ_ID] = {
            self.f['ubicacion_recorrido']: ubicacion_recorrido,
            self.f['nombre_del_recorrido']: nombre_recorrido
        }
        answers[self.f['estatus_del_recorrido']] = 'en_proceso'
        answers[self.f['areas_del_rondin']] = [{
            self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                self.f['nombre_area']: area_rondin
            },
            self.f['fecha_hora_inspeccion_area']: today,
            self.f['foto_evidencia_area_rondin']: data_rondin.get(self.f['foto_evidencia_area'], []),
            self.f['comentario_area_rondin']: data_rondin.get(self.f['comentario_check_area'], ''),
            self.f['url_registro_rondin']: f"https://app.linkaform.com/#/records/detail/{register_id}"
        }]

        for area in areas_recorrido:
            if not area.get('incidente_area') == area_rondin:
                answers[self.f['areas_del_rondin']].append({
                    self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                        self.f['nombre_area']: area.get('incidente_area', '')
                    },
                })

        answers[self.f['bitacora_rondin_incidencias']] = self.answers.get(self.f['grupo_incidencias_check'], [])

        metadata.update({'answers':answers})
        # print(simplejson.dumps(metadata, indent=3))

        ##############################
        #TODO Asignar a usuario
        ###############################

        res = self.lkf_api.post_forms_answers(metadata)
        return res
    
    def get_employee_name(self, user_id):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.CONF_AREA_EMPLEADOS,
                f"answers.{self.EMPLOYEE_OBJ_ID}.{self.mf['id_usuario']}": user_id
            }},
            {"$project": {
                "_id": 0,
                "employee_name": f"$answers.{self.EMPLOYEE_OBJ_ID}.{self.mf['nombre_empleado']}"
            }},
            {"$limit": 1}
        ]

        employee_name = self.unlist(self.format_cr(self.cr.aggregate(query)))
        employee_name = employee_name.get('employee_name', '')
        if not employee_name:
            employee_name = 'Nombre no registrado'
        return employee_name
    
    def format_grupo_incidencias(self, grupo_incidencias):
        format_grupo_incidencias = []
        employee_name = self.get_employee_name(self.user.get('user_id', ''))
        tz = pytz.timezone('America/Mexico_City')
        fecha_actual = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        for incidencia in grupo_incidencias:
            if incidencia.get(self.LISTA_INCIDENCIAS_CAT_OBJ_ID):
                incidente = incidencia.get(self.LISTA_INCIDENCIAS_CAT_OBJ_ID, {}).get(self.incidence_fields['incidencia'], '')
            else:
                incidente = incidencia.get(self.f['incidente_open'], '')
            format_grupo_incidencias.append({
                self.f['folio_del_check']: self.folio,
                self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID: {
                    self.mf['nombre_empleado']: employee_name
                },
                self.incidence_fields['fecha_hora_incidencia']: fecha_actual,
                self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                    self.f['incidente_location']: self.unlist(self.answers.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['incidente_location'], [])),
                    self.f['incidente_area']: self.unlist(self.answers.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['incidente_area'], []))
                },
                self.incidence_fields['tipo_incidencia']: incidente,
                self.incidence_fields['comentario_incidencia']: incidencia.get(self.f['incidente_comentario'], ''),
                self.incidence_fields['evidencia_incidencia']: incidencia.get(self.f['incidente_evidencia'], []),
                self.incidence_fields['documento_incidencia']: incidencia.get(self.f['incidente_documento'], []),
                self.incidence_fields['prioridad_incidencia']: incidencia.get(self.incidence_fields['prioridad_incidencia'], 'baja'),
                self.incidence_fields['notificacion_incidencia']: incidencia.get(self.incidence_fields['notificacion_incidencia'], 'no'),
            })
        return format_grupo_incidencias
    
    def create_incidence(self, answers):
        """
        Crea una incidencia en la bitacora de incidencias
        """
        metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_INCIDENCIAS)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de Incidencia",
                    "Action": "check_ubicacion_rondin",
                    "File": "accesos/check_ubicacion_rondin.py"
                }
            },
            'answers': answers
        })
        res = self.lkf_api.post_forms_answers(metadata)
        return res

    def has_guard_started_shift(self):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.EMPLEADOS,
                f"answers.{self.USUARIOS_OBJ_ID}.{self.mf['id_usuario']}": self.user.get('user_id'),
            }},
            {"$project": {
                "_id": 0,
                "nombre_completo": f"$answers.{self.USUARIOS_OBJ_ID}.{self.mf['nombre_usuario']}"
            }},
            {"$lookup": {
                "from": "form_answer",
                "let": {
                    "nombre_comp": "$nombre_completo"
                },
                "pipeline": [
                    {"$match": {
                        "deleted_at": {"$exists": False},
                        "form_id": 135386,
                        "$expr": {
                            "$eq": [
                                f"$answers.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}", 
                                "$$nombre_comp"
                            ]
                        }
                    }},
                    {"$project": {
                        "_id": 0,
                        "estatus": f"$answers.{self.checkin_fields['checkin_type']}"
                    }},
                    {"$sort": {"created_at": -1}},
                    {"$limit": 1}
                ],
                "as": "checkin_records"
            }},
            {"$project": {
                "checkin_records": 1
            }},
        ]
        response = self.format_cr(self.cr.aggregate(query))
        response = self.unlist(response)
        if response:
            turno = self.unlist(response.get('checkin_records', [])).get('estatus', '')
            if turno == 'cerrar_turno':
                msg = 'No haz iniciado turno, debes iniciar tu turno en la forma de Check In Manual, revisala y vuelve a intentar hacer un check.'
                self.LKFException({'msg': msg, 'title': 'Sin Turno'})
            else:
                pass

if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv, use_api=True)
    acceso_obj.console_run()
    record_id = json.loads(sys.argv[1])
    record_id = record_id.get('_id', '').get('$oid', '')
    # Validacion de turno
    # acceso_obj.has_guard_started_shift()
    # print('answers', simplejson.dumps(acceso_obj.answers, indent=3))
    acceso_obj.load(module='Location', **acceso_obj.kwargs)
    cat_area_rondin = acceso_obj.answers.get(acceso_obj.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {})
    nombre_area_rondin = acceso_obj.unlist(cat_area_rondin.get(acceso_obj.f['nombre_area'], []))
    nombre_ubicacion_rondin = acceso_obj.unlist(cat_area_rondin.get(acceso_obj.Location.f['location'], []))
    # print('nombre_area_rondin', nombre_area_rondin)

    nombres_recorrido = acceso_obj.get_recorridos_by_area(nombre_ubicacion_rondin, nombre_area_rondin)
    # print('nombres_recorrido', nombres_recorrido)

    rondin = acceso_obj.search_rondin_by_name(names=nombres_recorrido)
    # print('rondin', rondin)

    if not rondin:
        if not nombres_recorrido:
            print('No se encontro ningun recorrido con el area proporcionada.')
        else:
            print('No se encontro un rondin con el area proporcionada. Creando uno nuevo...')
            response = acceso_obj.create_rondin(acceso_obj.answers, nombre_area_rondin, record_id, nombres_recorrido)
    else:
        rondin_areas = acceso_obj.unlist(rondin).get('areas_del_rondin', [])
        for area in rondin_areas:
            if nombre_area_rondin == area.get('incidente_area', ''):
                print('Se encontro el area en un rondin en proceso...')
                fecha_area_registrada = area.get('fecha_hora_inspeccion_area', '')
                if fecha_area_registrada:
                    tz = pytz.timezone('America/Mexico_City')
                    fecha_reg = datetime.strptime(fecha_area_registrada, '%Y-%m-%d %H:%M:%S')
                    fecha_reg = tz.localize(fecha_reg)
                    ahora = datetime.now(tz)
                    ha_pasado_una_hora = (ahora - fecha_reg) >= timedelta(hours=1)
                    if ha_pasado_una_hora:
                        print('========>')
                        print('========> Ha pasado mas de una hora desde el ultimo check en esta area')
                        print('========>')
                        rondines = acceso_obj.get_rondines_by_status()
                        acceso_obj.close_rondines(rondines)
                        response = acceso_obj.create_rondin(acceso_obj.answers, nombre_area_rondin, record_id, nombres_recorrido)
                        nombre_area_rondin = ''
                    else:
                        print('========>')
                        print('========> Ya se hizo un check en esta area hace menos de una hora, no se puede actualizar el rondin actual ni crear uno nuevo.')
                        print('========>')
                        nombre_area_rondin = ''

        if nombre_area_rondin:
            print('Entra a actualizar check')
            resultado = acceso_obj.check_area_in_rondin(data_rondin=acceso_obj.answers, area_rondin=nombre_area_rondin, rondin=rondin, record_id=record_id)

    grupo_incidencias = acceso_obj.answers.get(acceso_obj.f['grupo_incidencias_check'], [])
    if grupo_incidencias:
        format_grupo_incidencias = acceso_obj.format_grupo_incidencias(grupo_incidencias)
        for incidencia in format_grupo_incidencias:
            acceso_obj.create_incidence(answers=incidencia)