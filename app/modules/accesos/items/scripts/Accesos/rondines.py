# coding: utf-8
from datetime import date
import sys, simplejson
from tkinter import N
from bson import ObjectId
from linkaform_api import settings
from account_settings import *
from datetime import datetime
import calendar

from accesos_utils import Accesos

class Accesos(Accesos):
    
    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)
        
        self.CONFIGURACION_RECORRIDOS_FORM = self.lkm.form_id('configuracion_de_recorridos','id')

        self.f.update({
            'rondin_area': '663e5d44f5b8a7ce8211ed0f',
            'foto_area': '6763096aa99cee046ba766ad',
            'porcentaje_de_areas_inspeccionadas': '689a7ecfbf2b4be31039388e',
            'cantidad_areas_inspeccionadas': '68a7b68a22ac030a67b7f8f8',
        })
        
        self.rondin_keys = {
            'nombre_rondin': '6645050d873fc2d733961eba',
            'duracion_estimada': '6854459836ea891d9d2be7d9',
            'ubicacion': '663e5c57f5b8a7ce8211ed0b',
            'areas': '6645052ef8bc829a5ccafaf5',
            'grupo_areas':'66462aa5d4a4af2eea07e0d1',
            'grupo_asignado': '638a9ab3616398d2e392a9fa',
            'fecha_hora_programada': 'abcde0001000000000010001',
            'programar_anticipacion': 'abcde0002000000000010001',
            'cuanto_tiempo_de_anticipacion': 'abcde0002000000000010004',
            'cuanto_tiempo_de_anticipacion_expresado_en': 'abcde0002000000000010005',
            'tiempo_para_ejecutar_tarea': 'abcde0001000000000010004',
            'tiempo_para_ejecutar_tarea_expresado_en': 'abcde0001000000000010005',
            'la_tarea_es_de': 'abcde0001000000000010006',
            'se_repite_cada': 'abcde0001000000000010007',
            'sucede_cada': 'abcde0001000000000010008',
            'sucede_recurrencia': 'abcde0001000000000010009',
            'en_que_minuto_sucede': 'abcde0001000000000010010',
            'cada_cuantos_minutos_se_repite': 'abcde0001000000000010011',
            'en_que_hora_sucede': 'abcde0001000000000010012',
            'cada_cuantas_horas_se_repite': 'abcde0001000000000010013',
            'que_dias_de_la_semana': 'abcde0001000000000010014',
            'en_que_semana_sucede': 'abcde0001000000000010015',
            'que_dia_del_mes': 'abcde0001000000000010016',
            'cada_cuantos_dias_se_repite': 'abcde0001000000000010017',
            'en_que_mes': 'abcde0001000000000010018',
            'cada_cuantos_meses_se_repite': 'abcde0001000000000010019',
            'la_recurrencia_cuenta_con_fecha_final': '64374e47a208e5c0ff95e9bd',
            'fecha_final_recurrencia': 'abcde0001000000000010099',
            'accion_recurrencia': 'abcde00010000000a0000001',
            'grupo_asignado_rondin':'671055aaa487da57ba57b294',
            'id_grupo':'639b65dfaf316bacfc551ba2',
            'cron_id':'abcde0001000000000000000',
            'status':'abcde00010000000a0000000',
            'fecha1':'abcde000100000000000f000',
            'fecha2':'abcde000100000000000f001'
        }
        
    def create_rondin(self, rondin_data: dict = {}):
        """Crea un rondin con los datos proporcionados.
        Args:
            rondin_data (dict): Un diccionario con los datos del rondin.
        Returns:
            response: La respuesta de la API de Linkaform al crear el rondin.
        """
        #! Data hardcoded for testing purposes
        #! Ejemplo rondin de recurrencia diaria
        # rondin_data = {
        no_use_data = {
            #! ======== PRIMERA PAGINA - INFORMACION GENERAL
            'nombre_rondin': 'Ejemplo rondin Nov 8',
            'duracion_estimada': '30 minutos',
            'ubicacion': 'Planta Monterrey',
            'areas': [
                'Almacén de inventario',
                'Sala de Juntas Planta Baja',
                'Caseta 6 Poniente',
                'Antenas',
            ],
            'grupo_asignado': '',
            #! ======== SEGUNDA PAGINA - FECHA Y HORA DE INICIO
            'fecha_hora_programada': '2025-11-05 15:00:00',
            #! ======== SEGUNDA PAGINA - ANTICIPACION
            'programar_anticipacion': 'no', # 'si' o 'no'
            'cuanto_tiempo_de_anticipacion': '', # numero decimal
            'cuanto_tiempo_de_anticipacion_expresado_en': '', # 'minutos', 'horas', 'dias', 'semanas', 'mes'
            #! ======== SEGUNDA PAGINA - TIEMPO PARA EJECUTAR LA TAREA
            'tiempo_para_ejecutar_tarea': 30,
            'tiempo_para_ejecutar_tarea_expresado_en': 'minutos',
            #! ======== SEGUNDA PAGINA - RECURRENCIA
            'la_tarea_es_de': 'cuenta_con_una_recurrencia', # 'es_de_única_ocación'
            'se_repite_cada': 'diario', # 'hora', 'diario', 'semana', 'mes', 'año', 'configurable'
            'sucede_cada': 'igual_que_la_primer_fecha',
            #! ======== SEGUNDA PAGINA - RECURRENCIA CONFIGURABLE
            'sucede_recurrencia': [], # 'minuto', 'hora', 'dia_de_la_semana', 'dia_del_mes', 'mes'
            #! ======== SEGUNDA PAGINA - RECURRENCIA CONFIGURABLE - MINUTO
            'en_que_minuto_sucede': '', # numero decimal
            'cada_cuantos_minutos_se_repite': '', # numero decimal
            #! ======== SEGUNDA PAGINA - RECURRENCIA CONFIGURABLE - HORA
            'en_que_hora_sucede': '', # numero decimal
            'cada_cuantas_horas_se_repite': '', # numero decimal
            #! ======== SEGUNDA PAGINA - RECURRENCIA CONFIGURABLE - DIA DE LA SEMANA
            'que_dias_de_la_semana': [], # ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
            #! ======== SEGUNDA PAGINA - RECURRENCIA CONFIGURABLE - DIA DEL MES
            'que_dia_del_mes': '', # numero decimal que no deberia ser decimal
            'cada_cuantos_dias_se_repite': '', # numero decimal que no deberia ser decimal
            #! ======== SEGUNDA PAGINA - RECURRENCIA CONFIGURABLE - MES
            'en_que_mes': '', # 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
            'cada_cuantos_meses_se_repite': '', # numero decimal que no deberia ser decimal
            #! ======== SEGUNDA PAGINA - EN QUE SEMANA SUCEDE
            'en_que_semana_sucede': 'todas_las_semanas', # 'primera_semana_del_mes', 'segunda_semana_del_mes', 'tercera_semana_del_mes', 'cuarta_semana_del_mes', 'quinta_semana_del_mes'
            #! ======== SEGUNDA PAGINA - FECHA FINAL DE RECURRENCIA SOLO SI ES DE UNICA OCASION
            'la_recurrencia_cuenta_con_fecha_final': 'no', # 'si' o 'no'
            'fecha_final_recurrencia': '', # 'YYYY-MM-DD HH:MM:SS'
            #! ======== SEGUNDA PAGINA - ACCION DE RECURRENCIA
            'accion_recurrencia': 'programar' # 'programar', 'pausar' o 'eliminar'
        }
        answers = {}
        rondin_data['ubicacion'] = self.get_ubicacion_geolocation(location=rondin_data.get('ubicacion', ''))
        rondin_data['areas'] = self.get_areas_details(areas_list=rondin_data.get('areas', []))
        
        for key, value in rondin_data.items():
            if key == 'ubicacion':
                answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {
                    self.Location.f['location']: value.get('location', ''),
                    self.f['address_geolocation']: value.get('geolocation', [])
                }
            elif key == 'grupo_asignado':
                answers[self.GRUPOS_CAT_OBJ_ID] = {
                    self.rondin_keys[key]: value
                }
            elif key == 'areas':
                areas_list = []
                for area in value:
                    area_dict = {
                        self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                            self.Location.f['area']: area.get('area', ''),
                            self.f['geolocalizacion_area_ubicacion']: [{
                                'latitude': area.get('latitude', 0),
                                'longitude': area.get('longitude', 0)
                            }],
                            self.f['foto_area']: area.get('image', []),
                            self.f['area_tag_id']: [area.get('tag_id', [])]
                        }
                    }
                    areas_list.append(area_dict)
                answers[self.rondin_keys[key]] = areas_list
            elif key == 'sucede_recurrencia' and ('dia_del_mes' in value or 'mes' in value):
                actual_day = datetime.now().day
                answers[self.rondin_keys['que_dia_del_mes']] = int(actual_day)
                answers[self.rondin_keys[key]] = value
            elif value == '':
                pass
            else:
                answers[self.rondin_keys[key]] = value
        response = self.create_register(
            module='Accesos',
            process='Creacion de un rondin',
            action='rondines',
            file='accesos/app.py',
            form_id=121742, #TODO Modularizar este ID
            answers=answers
        )
        return response
        
    def create_register(self, module: str, process: str, action: str, file: str, form_id: int, answers: dict):
        """Crea un registro en Linkaform con los metadatos y respuestas proporcionadas.

        Args:
            module (str): El nombre del módulo que está ejecutando la acción.
            process (str): El nombre del proceso que se está ejecutando.
            action (str): El nombre del script que se está ejecutando.
            file (str): La ruta del archivo donde se encuentra el app del modulo utilizado(Ej. jit/app.py).
            form_id (str): El ID de la forma en Linkaform.
            answers (dict): El diccionario de respuestas ya formateado.
            
        Returns:
            response: La respuesta de la API de Linkaform al crear el registro.
        """
        metadata = self.lkf_api.get_metadata(form_id=form_id)
        
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": module,
                    "Process": process,
                    "Action": action,
                    "File": file
                }
            },
        })
        
        metadata.update({'answers':answers})
        response = self.lkf_api.post_forms_answers(metadata)
        return response
    
    def create_incidencia_by_rondin(self, data):
        # data = {
        #     'reporta_incidencia': "Emiliano Zapata",
        #     'fecha_hora_incidencia': "2025-10-24 13:07:16",
        #     'ubicacion_incidencia':"Planta Monterrey",
        #     'area_incidencia': "Recursos eléctricos",
        #     'categoria': "Intrusión y seguridad",
        #     'sub_categoria':"Alteración del orden",
        #     'incidente':"Drogadicto",
        #     # "tipo_incidencia": "Otro incidente",
        #     'comentario_incidencia': "comentario random",
        #     'evidencia_incidencia': [],
        #     'documento_incidencia':[],
        #     'acciones_tomadas_incidencia':[],
        #     "prioridad_incidencia": "leve",
        #     "notificacion_incidencia": "no",
        # }
        status = {}
        response = self.create_incidence(data)
        if response.get('status_code') in [200, 201, 202]:
            status = {'status_code': 200, 'type': 'success', 'msg': 'Record created successfully', 'data': {}}
        else:
            status = {'status_code': 400, 'type': 'error', 'msg': response, 'data': {}}
        return status
        
    def delete_rondin(self, folio: str):
        """Elimina un rondin por su folio.
        Args:
            folio (str): El folio del rondin a eliminar.
        Returns:
            dict: Un diccionario con el estado de la operación.
        Raises:
            Exception: Si el folio no es proporcionado.
        """
        if not folio:
            raise Exception("Folio is required to delete a rondin.")
        
        response = self.cr.delete_one({
            'form_id': 121742, # TODO Modularizar este ID
            'folio': folio
        })
        
        if response.deleted_count > 0:
            response = self.detail_response(202)
        else:
            response = self.detail_response(404)
        return response
    
    def detail_response(self, status_code: int):
        """Devuelve un mensaje detallado según el código de estado HTTP.
        Args:
            status_code (int): El código de estado HTTP devuelto por la API.
        Returns:
            dict: Un diccionario con el estado y el mensaje correspondiente.
        """
        if status_code in [200, 201, 202]:
            return {"status": "success", "message": "Operation completed successfully."}
        elif status_code in [400, 404]:
            return {"status": "error", "message": "Bad request or resource not found."}
        elif status_code in [500, 502, 503]:
            return {"status": "error", "message": "Server error, please try again later."}
        else:
            return {"status": "error", "message": "Unexpected error occurred."}
        
    def edit_areas_rondin(self, areas, folio, record_id):
        metadata = self.lkf_api.get_metadata(form_id=self.CONFIGURACION_RECORRIDOS_FORM)
        metadata.update(self.get_record_by_folio(record_id, self.CONFIGURACION_RECORRIDOS_FORM, select_columns={'_id':1}, limit=1))

        full_rondin =self. get_rondin_by_id(record_id)
        print(simplejson.dumps(full_rondin, indent=4))

        answers = {}
        answers[self.rondin_keys['grupo_asignado_rondin']] = {}

        for key, value in full_rondin.items():
            if key == 'nombre_del_rondin':
                print("21323", key)
                answers.update({f"{self.rondin_keys['nombre_rondin']}":value})
            elif key == 'ubicacion':
                answers[self.Location.UBICACIONES_CAT_OBJ_ID]={
                    self.rondin_keys['ubicacion']: full_rondin.get('ubicacion', ''),
                    self.f['address_geolocation']: [full_rondin.get('ubicacion_geolocation',{})]
                }
            elif key == 'grupo_asignado_rondin':
                answers[key].append({
                    self.rondin_keys['grupo_asignado']: full_rondin.get('grupo_asignado', ""),
                    self.rondin_keys['id_grupo']: full_rondin.get('id_grupo', ""),
                })
       
            else:
                if key in self.rondin_keys: 
                    answers.update({
                        f"{self.rondin_keys[key]}": value
                    })

        if areas:
                areas_list = []
                for a in areas:
                    obj = {f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}":{
                            self.f['rondin_area'] : a.get('rondin_area', ''),
                            self.f['foto_area']:a.get('foto_area', ''),
                            self.f['geolocalizacion_area_ubicacion'] :a.get('geolocalizacion_area_ubicacion', ''),
                            self.f['area_tag_id'] :a.get('area_tag_id', ''),
                        }}
                    areas_list.append(obj)
        answers.update({self.rondin_keys['areas']:areas_list})

        metadata.update({
            'properties': {
                "device_properties":{
                    "system": "Addons",
                    "process":"Actualizacion de Areas Rondin", 
                    "accion":'edit_areas_rondin', 
                    "folio": folio, 
                    "archive": "rondines.py"
                }
            },
            'answers': answers,
            '_id': record_id
        })
        res= self.net.patch_forms_answers(metadata)
        return res

    def format_rondin_by_id(self, data):
        fotos_de_areas = []
        puntos_de_control = []
        for item in data.get('areas', []):
            foto_area_data = item.get('foto_area', [])
            foto_url = ""
            if foto_area_data:
                primer_elemento = foto_area_data[0]
                if isinstance(primer_elemento, list) and len(primer_elemento) > 0:
                    foto_url = primer_elemento[0].get('file_url', '')
                elif isinstance(primer_elemento, dict):
                    foto_url = primer_elemento.get('file_url', '')
            
            new_item = {
                "id": item.get('area_tag_id', [])[0] if len(item.get('area_tag_id', [])) > 0 else "",
                "nombre_area": item.get('rondin_area', ''),
                "foto_area": foto_url,
            }
            if new_item.get('foto_area'):
                fotos_de_areas.append(new_item)
            new_item = {
                "id": item.get('area_tag_id', [])[0] if len(item.get('area_tag_id', [])) > 0 else "",
                "nombre_area": item.get('rondin_area', ''),
                "geolocation_area": item.get('geolocalizacion_area_ubicacion', [])[0] if len(item.get('geolocalizacion_area_ubicacion', [])) > 0 else {},
            }
            if new_item.get('geolocation_area'):
                puntos_de_control.append(new_item)
        data.update({
            "recurrencia": data.get('recurrencia').replace('_', ' ').title() if data.get('recurrencia') else 'No Recurrente',
            "estatus_rondin": data.get('estatus_rondin').replace('_', ' ').title() if data.get('estatus_rondin') else 'No Especificado',
            "ubicacion_geolocation": data.get('ubicacion_geolocation', [])[0] if len(data.get('ubicacion_geolocation', [])) > 0 else {},
            "images_data": fotos_de_areas,
            "map_data": puntos_de_control,
        })
        return data

    def format_incidencias_rondines(self, data, area):
        format_data = []
        for item in data:
            incidencias = item.get('incidencias_rondin', [])
            for index, incidencia in enumerate(incidencias):
                if area:
                    incidencia_area = incidencia.get('nombre_area_salida', '')
                    if incidencia_area != area:
                        continue
                    
                format_item = {
                    "id": item.get('_id',''),
                    "folio": item.get('folio',''),
                    "ref_number": index,
                    "ubicacion_incidente": item.get('ubicacion', ''),
                    "area_incidente": incidencia.get('nombre_area_salida', ''),
                    "nombre_del_recorrido": item.get('nombre_recorrido', ''),
                    "fecha_hora_incidente": incidencia.get('fecha_hora_incidente_bitacora', ''),
                    "categoria": incidencia.get('categoria', 'General'),
                    "subcategoria": incidencia.get('sub_categoria', 'General'),
                    "incidente": incidencia.get('tipo_de_incidencia', incidencia.get('incidente_open', '')),
                    "accion_tomada": incidencia.get('incidente_accion', ''),
                    "comentarios": incidencia.get('comentario_incidente_bitacora', ''),
                    "evidencias": incidencia.get('incidente_evidencia', []),
                    "documentos": incidencia.get('incidente_documento', []),
                }
                format_data.append(format_item)
        return format_data
    
    def format_rondines_images(self, data):
        format_data = []
        for index, item in enumerate(data):
            format_item = {
                "id": item.get('_id',''),
                "folio": item.get('folio',''),
                "ref_number": index,
                "ubicacion": item.get('ubicacion', ''),
                "nombre_recorrido": item.get('nombre_recorrido', ''),
                "nombre_area": item.get('rondin_area', ''),
                "fecha_y_hora_check": item.get('fecha_hora_inspeccion_area', ''),
                "comentario_check": item.get('comentario_area_rondin', ''),
                "url_check": item.get('url_registro_rondin', ''),
                "fotos_check": item.get('foto_evidencia_area_rondin', []),
            }
            format_data.append(format_item)
        return format_data

    def format_bitacora_rondines(self, data):
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        days_in_month = calendar.monthrange(current_year, current_month)[1]
        
        format_data = []
        
        for item in data:
            hora_agrupada = item.get('hora_agrupada', '')
            categorias_raw = item.get('categorias', [])
            
            categorias_formateadas = []
            
            # Procesar cada categoría (recorrido)
            for categoria in categorias_raw:
                nombre_recorrido = categoria.get('nombre_recorrido', '')
                bitacora_rondines = categoria.get('bitacora_rondines', [])
                
                areas_recorrido = []
                if bitacora_rondines:
                    primera_bitacora = bitacora_rondines[0]
                    areas_del_rondin = primera_bitacora.get('areas_del_rondin', [])
                    areas_recorrido = [
                        {'rondin_area': area.get('rondin_area', ''), 'area_tag_id': area.get('area_tag_id', [])}
                        for area in areas_del_rondin
                    ]
                
                hora_valida = ''
                if bitacora_rondines:
                    fecha_programacion = bitacora_rondines[0].get('fecha_programacion', '')
                    if fecha_programacion:
                        try:
                            hora_valida = str(datetime.strptime(fecha_programacion, '%Y-%m-%d %H:%M:%S').hour)
                        except Exception:
                            try:
                                hora_valida = str(datetime.strptime(fecha_programacion, '%Y-%m-%d %H:%M').hour)
                            except Exception:
                                pass
                
                areas_formateadas = []
                
                for area in areas_recorrido:
                    nombre_area = area.get('rondin_area', '')
                    area_tag_id = area.get('area_tag_id', [])
                    area_tag = area_tag_id[0] if area_tag_id else ''
                    
                    estados = []
                    for dia in range(1, days_in_month + 1):
                        estado = self._get_estado_area_dia(
                            bitacora_rondines, 
                            area_tag, 
                            nombre_area, 
                            dia, 
                            current_year, 
                            current_month,
                            hora_valida
                        )
                        
                        g_id = ""
                        for bitacora in bitacora_rondines:
                            areas_del_rondin = bitacora.get('areas_del_rondin', [])
                            fecha_inicio = bitacora.get('fecha_inicio_rondin', '')
                            
                            if not fecha_inicio:
                                continue
                            
                            try:
                                fecha_bitacora = datetime.strptime(fecha_inicio, '%Y-%m-%d %H:%M:%S')
                            except Exception:
                                try:
                                    fecha_bitacora = datetime.strptime(fecha_inicio, '%Y-%m-%d %H:%M')
                                except Exception:
                                    continue
                            
                            if fecha_bitacora.year != current_year or fecha_bitacora.month != current_month or fecha_bitacora.day != dia:
                                continue
                            
                            for area_check in areas_del_rondin:
                                area_nombre = area_check.get('rondin_area', '')
                                if area_nombre != nombre_area:
                                    continue
                                
                                fecha_check = area_check.get('fecha_hora_inspeccion_area', '')
                                if not fecha_check:
                                    continue
                                
                                url = area_check.get('url_registro_rondin', '')
                                if url:
                                    g_id_part = url.split('detail/')[-1]
                                    g_id = g_id_part.split('?')[0].split('#')[0].strip('/')
                                    break
                            
                            if g_id:
                                break
                        
                        estados.append({
                            "dia": dia,
                            "estado": estado,
                            "record_id": g_id if estado not in ["none", "no_inspeccionada", "no_aplica"] else "",
                        })
                    
                    areas_formateadas.append({
                        "nombre": nombre_area,
                        "estados": estados
                    })
                
                resumen_estados = []
                for dia in range(1, days_in_month + 1):
                    estado_bitacora, bitacora_id = self._get_estado_bitacora_dia(
                        bitacora_rondines,
                        dia,
                        current_year,
                        current_month,
                        hora_valida
                    )
                    
                    resumen_estados.append({
                        "dia": dia,
                        "estado": estado_bitacora,
                        "record_id": bitacora_id if estado_bitacora not in ["none", "no_inspeccionada", "no_aplica"] else "",
                    })
                
                # Agregar esta categoría al array
                categorias_formateadas.append({
                    "titulo": nombre_recorrido,
                    "areas": areas_formateadas,
                    "resumen": resumen_estados
                })
            
            # Agregar el item con todas sus categorías
            format_data.append({
                "hora": hora_agrupada,
                "categorias": categorias_formateadas
            })
        
        return format_data
    
    def format_bitacoras_mes(self, bitacoras_data, nombre_recorrido):
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        days_in_month = calendar.monthrange(current_year, current_month)[1]
        
        bitacoras_por_dia = {}
        for bitacora in bitacoras_data:
            created_at = bitacora.get('created_at')
            if isinstance(created_at, str):
                try:
                    fecha_bitacora = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                except Exception:
                    try:
                        fecha_bitacora = datetime.strptime(created_at.split()[0], '%Y-%m-%d')
                    except Exception:
                        continue
            elif isinstance(created_at, datetime):
                fecha_bitacora = created_at
            else:
                continue
            
            dia = fecha_bitacora.day
            estatus = bitacora.get('estatus_del_recorrido', '')
            incidencias = bitacora.get('bitacora_rondin_incidencias', [])

            
            estado = self._mapear_estado_bitacora(estatus, incidencias)
            
            if dia not in bitacoras_por_dia or bitacoras_por_dia[dia]['created_at'] < created_at:
                bitacoras_por_dia[dia] = {
                    'estado': estado,
                    'created_at': created_at,
                    'record_id': str(bitacora.get('_id', ''))
                }
        
        estados = []
        for dia in range(1, days_in_month + 1):
            if dia in bitacoras_por_dia:
                estado = bitacoras_por_dia[dia]['estado']
                record_id = bitacoras_por_dia[dia]['record_id']
            else:
                fecha_dia = datetime(current_year, current_month, dia)
                if fecha_dia.date() < now.date():
                    estado = "no_inspeccionada"
                else:
                    estado = "none"
                record_id = ""
            
            estados.append({
                "dia": dia,
                "estado": estado,
                "record_id": record_id
            })
        
        hoy = now.day
        estado_dia_actual = estados[hoy - 1] if hoy <= days_in_month else estados[-1]
        
        format_data = {
            "recorrido": {
                "nombre": nombre_recorrido,
                "estados": estados
            },
            "estadoDia": estado_dia_actual
        }
        
        return format_data

    def format_check_by_id(self, data: dict):
        """
        Formatea los detalles de un check por su ID de registro.
        Args:
            data (dict): Datos del check.
        Returns:
            dict: Un diccionario con los detalles formateados del check.
        """
        incidencias_area = []
        for incidencia in data.get('incidencias', []):
            nombre_area_incidencia = incidencia.get('nombre_area_salida', '')
            if nombre_area_incidencia != data.get('rondin_area', ''):
                continue
            incidencia_formateada = {
                "fecha_hora_incidente": incidencia.get('fecha_hora_incidente_bitacora', ''),
                "categoria": incidencia.get('categoria', 'General'),
                "subcategoria": incidencia.get('sub_categoria', 'General'),
                "incidente": incidencia.get('tipo_de_incidencia', incidencia.get('incidente_open', '')),
                "accion_tomada": incidencia.get('incidente_accion', ''),
                "comentarios": incidencia.get('comentario_incidente_bitacora', ''),
                "evidencias": incidencia.get('incidente_evidencia', []),
                "documentos": incidencia.get('incidente_documento', []),
            }
            incidencias_area.append(incidencia_formateada)
            
        checks_mes = self.get_rondin_checks(data.get('rondin_area', ''), data.get('ubicacion', ''))
        
        format_data = {
            'area': data.get('rondin_area', ''),
            'checks_mes': checks_mes,
            'fotos': [{'pic_name': item.get('name', ''),'pic_url': item.get('file_url', '')} for item in data.get('foto_evidencia_area_rondin', [])],
            'hora_de_check': data.get('fecha_hora_inspeccion_area', ''),
            'ubicacion': data.get('ubicacion', ''),
            'tiempo_traslado': data.get('duracion_traslado_area', ''),
            'comentarios': data.get('comentario_area_rondin', ''),
            'incidencias': incidencias_area,
        }
        return format_data
    
    def format_rondin_checks(self, checks_data):
        """
        Formatea los checks del mes en el formato requerido por el frontend.
        
        Args:
            checks_data (list): Lista de checks del mes con sus incidencias
            area_nombre (str): Nombre del área
        
        Returns:
            dict: Datos formateados con estructura de estados por día
        """
        # Obtener el mes y año actuales
        now = datetime.now()
        current_year = now.year
        current_month = now.month
        days_in_month = calendar.monthrange(current_year, current_month)[1]
        
        # Crear diccionario para mapear días a checks
        checks_por_dia = {}
        for check in checks_data:
            created_at = check.get('created_at')
            if isinstance(created_at, str):
                try:
                    fecha_check = datetime.strptime(created_at, '%Y-%m-%d')
                except Exception:
                    continue
            elif isinstance(created_at, datetime):
                fecha_check = created_at
            else:
                continue
            
            dia = fecha_check.day
            check_area = check.get('check_area', {})
            incidencias = check.get('incidencias', [])
            
            # Determinar estado del check
            estado = self._get_estado_check(incidencias, self.unlist(check_area.get('rondin_area', '')))
            
            # Guardar el check (si hay múltiples checks en un día, mantener el último)
            if dia not in checks_por_dia or checks_por_dia[dia]['created_at'] < created_at:
                checks_por_dia[dia] = {
                    'estado': estado,
                    'created_at': created_at,
                    'record_id': str(check.get('_id', ''))
                }
        
        # Crear lista de estados para todos los días del mes
        estados = []
        for dia in range(1, days_in_month + 1):
            if dia in checks_por_dia:
                estado = checks_por_dia[dia]['estado']
                record_id = checks_por_dia[dia]['record_id']
            else:
                # Determinar si es día pasado, presente o futuro
                fecha_dia = datetime(current_year, current_month, dia)
                if fecha_dia.date() < now.date():
                    estado = "no_inspeccionada"
                else:
                    estado = "none"
                record_id = ""
            
            estados.append({
                "dia": dia,
                "estado": estado,
                "record_id": record_id
            })
        
        # Obtener el estado del día actual
        hoy = now.day
        estado_dia_actual = estados[hoy - 1] if hoy <= days_in_month else estados[-1]
        
        format_data = {
            "area": {
                "nombre": self.unlist(checks_data[0].get('rondin_area', '')),
                "estados": estados
            },
            "estadoDia": estado_dia_actual
        }
        
        return format_data
    
    def get_average_rondin_duration(self, location: str, rondin_name: str):
        query = [
            {"$match": {
                "form_id": self.BITACORA_RONDINES,
                "deleted_at": {"$exists": False},
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.f['nombre_del_recorrido']}": rondin_name,
                f"answers.{self.f['duracion_rondin']}": {"$exists": True}
            }},
            {"$group": {
                "_id": None,
                "average_duration": {
                    "$avg": {
                        "$ifNull": [f"$answers.{self.f['duracion_rondin']}", 0]
                    }
                }
            }},
            {"$project": {
                "_id": 0,
                "average_duration": {"$round": ["$average_duration", 2]}
            }}
        ]
        
        response = self.format_cr(self.cr.aggregate(query))
        format_response = 0
        if response:
            format_response = self.unlist(response).get('average_duration', 0)
        return format_response

    def get_rondines(self, date_from=None, date_to=None, limit=20, offset=0):
        """Lista los rondines según los filtros proporcionados.
        Params:
            date_from (str): Fecha de inicio del filtro.
            date_to (str): Fecha de fin del filtro.
            limit (int): Número máximo de rondines a devolver.
            offset (int): Número de rondines a omitir desde el inicio.
        Returns:
            list: Lista de rondines con sus detalles.
        """
        match = {
            "form_id": self.CONFIGURACION_DE_RECORRIDOS_FORM,
            "deleted_at": {"$exists": False},
        }
        
        if date_from:
            match.update({
                "created_at": {"$gte": date_from}
            })
        if date_to:
            match.update({
                "created_at": {"$lte": date_to}
            })
        
        query = [
            {"$match": match},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "ubicacion": f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}",
                "nombre_del_rondin": f"$answers.{self.rondin_keys['nombre_rondin']}",
                "checkpoints": {"$size": {"$ifNull": [f"$answers.{self.rondin_keys['areas']}", []]}},
                "recurrencia": {"$ifNull": [f"$answers.{self.rondin_keys['la_tarea_es_de']}", 'No Recurrente']},
                "duracion_estimada": f"$answers.{self.rondin_keys['duracion_estimada']}",
                "asignado_a": {"$ifNull": [f"$answers.{self.GRUPOS_CAT_OBJ_ID}.{self.rondin_keys['grupo_asignado']}", 'No Asignado']},
                "fecha_hora_programada": f"$answers.{self.rondin_keys['fecha_hora_programada']}",
                "cada_cuantos_dias_se_repite": f"$answers.{self.rondin_keys['cada_cuantos_dias_se_repite']}",
                "areas": f"$answers.{self.rondin_keys['areas']}.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area']}",
            }},
            {"$sort": {"folio": -1}},
            {"$skip": offset},
            {"$limit": limit}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = []
        if response:
            for item in response:
                item['recurrencia'] = item['recurrencia'].replace('_', ' ').title() if item.get('recurrencia') else 'No Recurrente'
                format_response.append(item)
        return format_response
    
    def get_rondin_by_id(self, record_id: str):
        """Obtiene los detalles de un rondin por su ID de registro.
        Args:
            record_id (str): El ID del registro del rondin.
        Returns:
            dict: Un diccionario con los detalles del rondin.
        Raises:
            Exception: Si el ID del registro no es proporcionado.
        """
        if not record_id:
            raise Exception("Record ID is required to get rondin details.")
        
        query = [
            {"$match": {
                "_id": ObjectId(record_id),
                "form_id": self.CONFIGURACION_DE_RECORRIDOS_FORM,
                "deleted_at": {"$exists": False}
            }},
            {"$project": {
                "_id": 0,
                "folio": 1,
                "nombre_del_rondin": f"$answers.{self.rondin_keys['nombre_rondin']}",
                "recurrencia": {"$ifNull": [f"$answers.{self.rondin_keys['la_tarea_es_de']}", 'No Recurrente']},
                "asignado_a": {"$ifNull": [f"$answers.{self.GRUPOS_CAT_OBJ_ID}.{self.rondin_keys['grupo_asignado']}", 'No Asignado']},
                "ubicacion": f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}",
                "ubicacion_geolocation": f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['address_geolocation']}",
                "estatus_rondin": f"$answers.{self.f['status_cron']}",
                "fecha_inicio_rondin": f"$answers.{self.f['fecha_primer_evento']}",
                "duracion_esperada_rondin": {"$ifNull": [f"$answers.{self.rondin_keys['duracion_estimada']}", "No especificada"]},
                "fecha_final_rondin": {"$ifNull": [f"$answers.{self.f['fecha_final_recurrencia']}", "Sin fecha final"]},
                "cantidad_de_puntos": {"$size": {"$ifNull": [f"$answers.{self.rondin_keys['areas']}", []]}},
                "areas": f"$answers.{self.rondin_keys['areas']}",
                "la_recurrencia_cuenta_con_fecha_final":f"$answers.{self.rondin_keys['la_recurrencia_cuenta_con_fecha_final']}",
                "grupo_asignado_rondin":f"$answers.{self.rondin_keys['grupo_asignado_rondin']}",
                "id_grupo":f"$answers.{self.rondin_keys['id_grupo']}",
                "cron_id":f"$answers.{self.rondin_keys['cron_id']}",
                "programar_anticipacion":f"$answers.{self.rondin_keys['programar_anticipacion']}",
                "accion_recurrencia":f"$answers.{self.rondin_keys['accion_recurrencia']}",
                "en_que_mes":f"$answers.{self.rondin_keys['en_que_mes']}",
                "en_que_semana_sucede":f"$answers.{self.rondin_keys['en_que_semana_sucede']}",
                "que_dias_de_la_semana":f"$answers.{self.rondin_keys['que_dias_de_la_semana']}",
                "sucede_recurrencia":f"$answers.{self.rondin_keys['sucede_recurrencia']}",
                "sucede_cada":f"$answers.{self.rondin_keys['sucede_cada']}",
                "se_repite_cada":f"$answers.{self.rondin_keys['se_repite_cada']}",
                "tiempo_para_ejecutar_tarea_expresado_en":f"$answers.{self.rondin_keys['tiempo_para_ejecutar_tarea_expresado_en']}",
                "tiempo_para_ejecutar_tarea":f"$answers.{self.rondin_keys['tiempo_para_ejecutar_tarea']}",
                "fecha_hora_programada":f"$answers.{self.rondin_keys['fecha_hora_programada']}",
                "fecha1":f"$answers.abcde000100000000000f000",
                "fecha2":f"$answers.abcde000100000000000f001",
            }},
        ]

        response = self.format_cr(self.cr.aggregate(query))
        response = self.unlist(response)
        format_response = {}
        if response:
            format_response = self.format_rondin_by_id(response)
            location = response.get('ubicacion', '')
            rondin_name = response.get('nombre_del_rondin', '')
            duracion_promedio = self.get_average_rondin_duration(location=location, rondin_name=rondin_name)
            format_response['duracion_promedio'] = duracion_promedio
        return format_response

    def get_ubicacion_geolocation(self, location: str):
        """
        Obtiene la geolocalización de una ubicación específica.
        Args:
            location (str): El nombre de la ubicación.
        Returns:
            dict: Un diccionario con la ubicación y su geolocalización.
        """
        query = [
            {"$match": {
                "form_id": self.Location.UBICACIONES,
                "deleted_at": {"$exists": False},
                f"answers.{self.Location.f['location']}": location,
            }},
            {"$project": {
                "_id": 0,
                "location": f"$answers.{self.Location.f['location']}",
                "geolocation": f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_geolocation']}",
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        response = self.unlist(response)
        return response
        
    def get_areas_details(self, areas_list: list):
        """
        Obtiene los detalles necesarios de las áreas proporcionadas.
        Args:
            areas_list (list): Lista de áreas.
        Returns:
            list: Lista de áreas con su geolocalización y foto.
        """
        query = [
            {"$match": {
                "form_id": self.Location.AREAS_DE_LAS_UBICACIONES,
                "deleted_at": {"$exists": False},
                f"answers.{self.Location.f['area']}": {"$in": areas_list},
            }},
            {"$project": {
                "_id": 0,
                "area": f"$answers.{self.Location.f['area']}",
                "geolocation": f"$answers.{self.f['geolocalizacion_area_ubicacion']}",
                "image": f"$answers.{self.f['foto_area']}",
                "tag_id": f"$answers.{self.f['area_tag_id']}",
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        return response

    def get_catalog_areas(self, ubicacion=""):
        #Obtener areas disponibles para rondin
        if ubicacion:
            options = {
                'startkey': [ubicacion],
                'endkey': [f"{ubicacion}\n",{}],
                'group_level':2
            }

            catalog_id = self.AREAS_DE_LAS_UBICACIONES_CAT_ID
            form_id = 121742
            return self.catalogo_view(catalog_id, form_id, options)
        else:
            raise Exception("Ubicacion is required.")

    def get_catalog_areas_formatted(self, ubicacion=""):
        #Obtener areas disponibles para rondin
        if ubicacion:
            options = {
                'startkey': [ubicacion],
                'endkey': [f"{ubicacion}\n",{}],
                'group_level':2
            }

            catalog_id = self.AREAS_DE_LAS_UBICACIONES_CAT_ID
            form_id = 121742
            areas = self.catalogo_view(catalog_id, form_id, options)
            response = self.get_areas_details(areas)
            areas_formateadas = []
            for r in response:
                areas_formateadas.append({
                    "rondin_area": r.get("area", ""), 
                    "geolocalizacion_area_ubicacion": [
                        {
                            "latitude": r.get("latitude", 0.0),
                            "longitude": r.get("longitude", 0.0) 
                        }
                    ],
                    "area_tag_id": [r.get("tag_id", "")],  
                    "foto_area": r.get("image", [])  
                })
            print("RESPONSE",simplejson.dumps(areas_formateadas, indent=3))
            return areas_formateadas
        else:
            raise Exception("Ubicacion is required.")

    def get_incidencias_rondines(self, location=None, area=None, date_from=None, date_to=None, limit=20, offset=0):
        """Lista las incidencias de los rondines según los filtros proporcionados.
        Params:
            date_from (str): Fecha de inicio del filtro.
            date_to (str): Fecha de fin del filtro.
            limit (int): Número máximo de incidencias a devolver.
            offset (int): Número de incidencias a omitir desde el inicio.
        Returns:
            list: Lista de incidencias con sus detalles.
        """
        match = {
            "form_id": self.BITACORA_RONDINES,
            "deleted_at": {"$exists": False},
            f"answers.{self.f['bitacora_rondin_incidencias']}": {
                "$type": "array",
                "$not": {"$size": 0}
            }
        }
        
        if location:
            match.update({
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": location
            })
        if date_from:
            match.update({
                "created_at": {"$gte": date_from}
            })
        if date_to:
            match.update({
                "created_at": {"$lte": date_to}
            })
        
        query = [
            {"$match": match},
            {"$sort": {"created_at": -1}},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "ubicacion": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}",
                "nombre_recorrido": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}",
                "incidencias_rondin": f"$answers.{self.f['bitacora_rondin_incidencias']}",
            }},
            {"$skip": offset},
            {"$limit": limit}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = []
        if response:
            format_response = self.format_incidencias_rondines(response, area)
        return format_response

    def get_rondines_images(self, location=None, area=None, date_from=None, date_to=None, limit=20, offset=0):
        """Lista las imágenes de los rondines según los filtros proporcionados.
        Params:
            date_from (str): Fecha de inicio del filtro.
            date_to (str): Fecha de fin del filtro.
            limit (int): Número máximo de imágenes a devolver.
            offset (int): Número de imágenes a omitir desde el inicio.
        Returns:
            list: Lista de imágenes con sus detalles.
        """
        match = {
            "form_id": self.BITACORA_RONDINES,
            "deleted_at": {"$exists": False},
            f"answers.{self.f['grupo_areas_visitadas']}": {
                "$type": "array",
                "$not": {"$size": 0}
            }
        }
        
        unwind_match = {
            f"answers.{self.f['grupo_areas_visitadas']}.{self.f['foto_evidencia_area_rondin']}": {
                "$exists": True,
                "$not": {"$size": 0}
            }
        }
        
        if location:
            match.update({
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": location
            })
        if area:
            unwind_match.update({
                f"answers.{self.f['grupo_areas_visitadas']}.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.Location.f['area']}": area
            })
        if date_from:
            match.update({
                "created_at": {"$gte": date_from}
            })
        if date_to:
            match.update({
                "created_at": {"$lte": date_to}
            })
        
        query = [
            {"$match": match},
            {"$sort": {"created_at": -1}},
            {'$unwind': f"$answers.{self.f['grupo_areas_visitadas']}"},
            {"$match": unwind_match},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "areas_recorrido": f"$answers.{self.f['grupo_areas_visitadas']}",
                "ubicacion": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}",
                "nombre_recorrido": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}",
            }},
            {"$skip": offset},
            {"$limit": limit}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = []
        if response:
            format_response = self.format_rondines_images(response)
        print("format_response", simplejson.dumps(format_response, indent=4))
        return format_response

    def get_bitacora_rondines(self, location=None):
        match = {
            "deleted_at": {"$exists": False},
            "form_id": self.BITACORA_RONDINES,
            #! TEST PURPOSES
            # f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}": {"$in": ["Recorrido cada 4 horas", "Recorrido 1 vez al Mes"]},
            # f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}": {"$in": ["Recorrido cada 4 horas"]},
            f"answers.{self.f['fecha_programacion']}": {"$type": "string", "$ne": ""}, 
            "$expr": {
                "$and": [
                    { "$eq": [ { "$year": "$created_at" }, { "$year": "$$NOW" } ] }, #TODO: Cambiar a mes por parametro
                    { "$eq": [ { "$month": "$created_at" }, { "$month": "$$NOW" } ] }, #TODO: Cambiar a mes por parametro
                ]
            }
        }
        

        if location:
            match.update({
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": location,
            })
        
        query = [
            {"$match": match},
            {"$project": {
                "_id": 1,
                "answers": 1,
                "hora_agrupada": {
                    "$hour": {
                        "$dateFromString": {
                            "dateString": f"$answers.{self.f['fecha_programacion']}",
                            "format": "%Y-%m-%d %H:%M:%S",
                            "onError": None
                        }
                    }
                },
                "nombre_recorrido": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}",
                "recorridos": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}",
                "bitacora_rondines": "$answers"
            }},
            {"$group": {
                "_id": {
                    "hora": "$hora_agrupada",
                    "nombre_recorrido": "$nombre_recorrido"
                },
                "recorridos": {"$first": "$recorridos"},
                "bitacora_rondines": {
                    "$push": {
                        "_id": "$_id",
                        "answers": "$answers"
                    }
                }
            }},
            {"$group": {
                "_id": "$_id.hora",
                "categorias": {
                    "$push": {
                        "nombre_recorrido": "$_id.nombre_recorrido",
                        "recorridos": "$recorridos",
                        "bitacora_rondines": "$bitacora_rondines"
                    }
                }
            }},
            {"$project": {
                "_id": 0,
                "hora_agrupada": {
                    "$concat": [
                        {"$cond": [{"$lt": ["$_id", 10]}, "0", ""]},
                        {"$toString": "$_id"},
                        ":00"
                    ]
                },
                "categorias": 1
            }},
            {"$sort": {"hora_agrupada": 1}}
        ]

        response = self.format_cr(self.cr.aggregate(query))
        format_resp = []
        if response:
            format_resp = self.format_bitacora_rondines(response)
        return format_resp

    def get_check_by_id(self, record_id: str):
        """
        Obtiene los detalles de un check por su ID de registro.
        Args:
            record_id (str): El ID del registro del check.
        Returns:
            dict: Un diccionario con los detalles del check.
        Raises:
            Exception: Si el ID del registro no es proporcionado.
        """
        if not record_id:
            return self.LKFException({'title': 'Advertencia', 'msg': 'El ID del registro no fue proporcionado.'})

        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                "$expr": {
                    "$and": [
                        { "$eq": [ { "$year": "$created_at" }, { "$year": "$$NOW" } ] }, #TODO: Cambiar a mes por parametro
                        { "$eq": [ { "$month": "$created_at" }, { "$month": "$$NOW" } ] }, #TODO: Cambiar a mes por parametro
                        {"$anyElementTrue": {
                            "$map": {
                                "input": {
                                    "$ifNull": [f"$answers.{self.f['grupo_areas_visitadas']}", []]
                                },
                                "as": "check",
                                "in": {
                                    "$regexMatch": {
                                        "input": f"$$check.{self.f['url_registro_rondin']}",
                                        "regex": record_id
                                    }
                                }
                            }
                        }}
                    ]
                }
            }},
            {"$unwind": f"$answers.{self.f['grupo_areas_visitadas']}"},
            {"$match": {
                "$expr": {
                    "$regexMatch": {
                        "input": f"$answers.{self.f['grupo_areas_visitadas']}.{self.f['url_registro_rondin']}",
                        "regex": record_id
                    }
                }
            }},
            {"$project": {
                "_id": 0,
                "ubicacion": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}",
                "nombre_recorrido": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}",
                "area": f"$answers.{self.f['grupo_areas_visitadas']}",
                "incidencias": f"$answers.{self.f['bitacora_rondin_incidencias']}",
            }}
        ]

        response = self.format_cr(self.cr.aggregate(query))
        response = self.unlist(response)
        format_response = {}
        if response:
            format_response = self.format_check_by_id(response)
        return format_response
    
    def get_bitacora_by_id(self, record_id):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                "_id": ObjectId(record_id),
            }},
            {"$project": {
                "_id": 0,
                "answers": 1
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = {}
        if response:
            response = self.unlist(response)
            bitacoras_mes = self.get_bitacoras_mes(response.get('incidente_location', ''), response.get('nombre_del_recorrido', ''))
            format_response.update({
                "bitacoras_mes": bitacoras_mes,
                "fecha_hora_programada": response.get('fecha_programacion', ''),
                "fecha_inicio": response.get('fecha_inicio_rondin', ''),
                "fecha_fin": response.get('fecha_fin_rondin', ''),
                "duracion": response.get('duracion_rondin', ''),
                "estatus": response.get('estatus_del_recorrido', ''),
                "recurrencia": response.get('fecha_programacion', ''),
                "areas_a_inspeccionar": response.get('areas_del_rondin', []),
                "incidencias": response.get('bitacora_rondin_incidencias', []),
            })
        return format_response
    
    def get_bitacoras_mes(self, location, nombre_recorrido):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}": nombre_recorrido,
                "$expr": {
                    "$and": [
                        {"$eq": [{"$year": "$created_at"}, {"$year": "$$NOW"}]},
                        {"$eq": [{"$month": "$created_at"}, {"$month": "$$NOW"}]}
                    ]
                }
            }},
            {"$project": {
                "_id": 1,
                "answers": 1,
                "created_at": 1,
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = []
        if response:
            format_response = self.format_bitacoras_mes(response, nombre_recorrido)
        return format_response

    def get_rondin_checks(self, area, location):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.CHECK_UBICACIONES,
                f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.Location.f['area']}": area,
                "$expr": {
                    "$and": [
                        {"$eq": [{"$year": "$created_at"}, {"$year": "$$NOW"}]},
                        {"$eq": [{"$month": "$created_at"}, {"$month": "$$NOW"}]}
                    ]
                }
            }},
            {"$project": {
                "_id": 1,
                "answers": 1,
                "created_at": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$created_at",
                        "timezone": "America/Mexico_City"
                    }
                }
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = []
        if response:
            format_response = self.format_rondin_checks(response)
        return format_response
    
    def _get_estado_check(self, incidencias, area_nombre):
        """
        Determina el estado de un check según su información.
        
        Args:
            check_area (dict): Información del área visitada en el check
            incidencias (list): Lista de incidencias de la bitácora
            area_nombre (str): Nombre del área a evaluar
        
        Returns:
            str: Estado del check ("finalizado", "incidencias", etc.)
        """
        # Verificar si hay incidencias para esta área
        tiene_incidencias = False
        for incidencia in incidencias:
            nombre_area_incidencia = incidencia.get('nombre_area_salida', '')
            if nombre_area_incidencia == area_nombre:
                tiene_incidencias = True
                break
        
        if tiene_incidencias:
            return "incidencias"
        
        # Si no hay incidencias, el check está finalizado
        return "finalizado"
    
    def _get_estado_bitacora_dia(self, bitacora_rondines, dia, year, month, hora_valida):
        """
        Determina el estado de una bitácora en un día específico.
        
        Returns:
            tuple: (estado, bitacora_id)
                - "finalizado": Bitácora completada
                - "incidencias": Bitácora con incidencias
                - "no_inspeccionada": Día pasado donde debía haber bitácora pero no se hizo
                - "no_aplica": Día pasado donde no estaba programada ninguna bitácora
                - "none": Día futuro o presente sin bitácora
        """
        for bitacora in bitacora_rondines:
            fecha_inicio = bitacora.get('fecha_inicio_rondin', '')
            estatus_bitacora = bitacora.get('estatus_del_recorrido', '')
            incidencias = bitacora.get('bitacora_rondin_incidencias', [])

            bitacora_id = str(bitacora.get('_id', ''))
            areas_del_rondin = bitacora.get('areas_del_rondin', [])
            for area in areas_del_rondin:
                url = area.get('url_registro_rondin', '')
                if url:
                    break
            
            if not fecha_inicio:
                continue
            
            try:
                fecha_bitacora = datetime.strptime(fecha_inicio, '%Y-%m-%d %H:%M:%S')
            except Exception:
                try:
                    fecha_bitacora = datetime.strptime(fecha_inicio, '%Y-%m-%d %H:%M')
                except Exception:
                    continue
            
            if fecha_bitacora.year != year or fecha_bitacora.month != month or fecha_bitacora.day != dia:
                continue
            
            if hora_valida:
                try:
                    hora_inicio = fecha_bitacora.hour
                    hora_esperada = int(hora_valida)
                    
                    if not (hora_esperada <= hora_inicio <= hora_esperada + 1):
                        continue
                except Exception:
                    pass
            
            if incidencias and len(incidencias) > 0:
                return ('incidencias', bitacora_id)
            
            if estatus_bitacora in ['realizado', 'cerrado']:
                return ("finalizado", bitacora_id)
            elif estatus_bitacora == 'cancelado':
                return ("cancelado", bitacora_id)
            else:
                return ("finalizado", bitacora_id)
        
        # No se encontró bitácora para este día
        now = datetime.now()
        fecha_evaluada = datetime(year, month, dia)
        
        # Si es día futuro o presente
        if fecha_evaluada.date() >= now.date():
            return ("none", "")
        
        # Si es día pasado, verificar si estaba programada una bitácora
        # Verificar si había una bitácora programada (pero no ejecutada) para ese día
        estaba_programada, bitacora_programada = self._verificar_bitacora_programada(dia, year, month, hora_valida, bitacora_rondines)
        
        if estaba_programada:
            estatus_bitacora_programada = bitacora_programada.get('estatus_del_recorrido', '')
            if estatus_bitacora_programada == 'cancelado':
                return ("cancelado", "")
            else:
                return ("no_inspeccionada", "")
        else:
            return ("no_aplica", "")
    
    def _get_estado_area_dia(self, bitacora_rondines, area_tag_id, nombre_area, dia, year, month, hora_valida):
        """
        Determina el estado de un área en un día específico.
        
        Returns:
            str: Estado del área
                - "finalizado": Área visitada
                - "incidencias": Área con incidencias
                - "no_inspeccionada": Día pasado donde debía visitarse pero no se hizo
                - "no_aplica": Día pasado donde no estaba programada la visita
                - "none": Día futuro o presente sin visita
        """
        for bitacora in bitacora_rondines:
            areas_del_rondin = bitacora.get('areas_del_rondin', [])
            incidencias = bitacora.get('bitacora_rondin_incidencias', [])
            fecha_inicio = bitacora.get('fecha_inicio_rondin', '')
            
            if not fecha_inicio:
                continue
            
            try:
                fecha_bitacora = datetime.strptime(fecha_inicio, '%Y-%m-%d %H:%M:%S')
            except Exception:
                try:
                    fecha_bitacora = datetime.strptime(fecha_inicio, '%Y-%m-%d %H:%M')
                except Exception:
                    continue
            
            if fecha_bitacora.year != year or fecha_bitacora.month != month or fecha_bitacora.day != dia:
                continue
            
            if hora_valida:
                try:
                    hora_inicio = fecha_bitacora.hour
                    hora_esperada = int(hora_valida)
                    
                    if not (hora_esperada <= hora_inicio <= hora_esperada + 1):
                        continue
                except Exception:
                    pass
            
            # Verificar incidencias para esta área
            for incidencia in incidencias:
                nombre_area_incidencia = incidencia.get('nombre_area_salida', '')
                
                if nombre_area_incidencia == nombre_area:
                    return "incidencias"
            
            # Verificar si el área fue visitada
            for area_check in areas_del_rondin:
                area_nombre = area_check.get('rondin_area', '')
                
                if area_nombre != nombre_area:
                    continue
                
                fecha_check = area_check.get('fecha_hora_inspeccion_area', '')
                
                if fecha_check:
                    return "finalizado"
        
        # No se encontró visita para este día
        now = datetime.now()
        fecha_evaluada = datetime(year, month, dia)
        
        # Si es día futuro o presente
        if fecha_evaluada.date() >= now.date():
            return "none"
        
        # Si es día pasado, verificar si estaba programada una bitácora
        estaba_programada, bitacora_programada = self._verificar_bitacora_programada(dia, year, month, hora_valida, bitacora_rondines)
        
        if estaba_programada:
            estatus_bitacora_programada = bitacora_programada.get('estatus_del_recorrido', '')
            if estatus_bitacora_programada == 'cancelado':
                return "cancelado"
            else:
                return "no_inspeccionada"
        else:
            return "no_aplica"
    
    def _mapear_estado_bitacora(self, estatus_bitacora, incidencias):
        if incidencias and len(incidencias) > 0:
            return 'incidencias'

        estados_map = {
            'realizado': 'finalizado',
            'cerrado': 'finalizado',
            'completado': 'finalizado',
            'finalizado': 'finalizado',
            'cancelado': 'no_inspeccionada',
            'pendiente': 'none',
            'en_proceso': 'none',
        }
        
        status_normalizado = estatus_bitacora.lower().strip() if estatus_bitacora else ''
        for key, value in estados_map.items():
            if key in status_normalizado:
                return value
        return 'finalizado' if estatus_bitacora else 'none'
    
    def pause_or_play_rondin(self, record_id, paused=True):
        answers = {
            self.rondin_keys['accion_recurrencia']: 'pausar' if paused else 'programar',
        }
        response = self.lkf_api.patch_multi_record(answers=answers, form_id=self.CONFIGURACION_RECORRIDOS_FORM, record_id=[record_id])
        if response.get('status_code') in [200, 201, 202]:
            return {'status_code': 200, 'type': 'success', 'msg': 'Rondin paused successfully', 'data': {}}
        else:
            return {'status_code': 400, 'type': 'error', 'msg': response, 'data': {}}
    
    def update_rondin(self, folio, rondin_data: dict = {}):
        answers = {}
        
        for key, value in rondin_data.items():
            if key == 'ubicacion':
                answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {
                    self.Location.f['location']: value
                }
            elif key == 'grupo_asignado':
                answers[self.GRUPOS_CAT_OBJ_ID] = {
                    self.rondin_keys[key]: value
                }
            elif key == 'areas':
                areas_list = []
                for area in value:
                    area_dict = {
                        self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                            self.Location.f['area']: area
                        }
                    }
                    areas_list.append(area_dict)
                answers[self.rondin_keys["grupo_areas"]] = areas_list
            elif value == '':
                pass
            else:
                answers[self.rondin_keys[key]] = value
        response = self.lkf_api.patch_multi_record( answers = answers, form_id=121742, folios=[folio])
        return response

    def _verificar_bitacora_programada(self, dia, year, month, hora_valida, bitacora_rondines):
        """
        Verifica si había una bitácora programada para un día específico.
        
        Args:
            dia (int): Día del mes
            year (int): Año
            month (int): Mes
            hora_valida (str): Hora esperada del recorrido
            bitacora_rondines (list): Lista de bitácoras del recorrido
        
        Returns:
            bool: True si había bitácora programada, False si no
        """
        # Buscar si existe alguna bitácora con fecha_programacion para ese día
        for bitacora in bitacora_rondines:
            fecha_programacion = bitacora.get('fecha_programacion', '')
            
            if not fecha_programacion:
                continue
            
            try:
                fecha_prog = datetime.strptime(fecha_programacion, '%Y-%m-%d %H:%M:%S')
            except Exception:
                try:
                    fecha_prog = datetime.strptime(fecha_programacion, '%Y-%m-%d %H:%M')
                except Exception:
                    continue
            
            # Verificar si la programación era para este día
            if fecha_prog.year != year or fecha_prog.month != month or fecha_prog.day != dia:
                continue
            
            # Verificar la hora si es necesario
            if hora_valida:
                try:
                    hora_programada = fecha_prog.hour
                    hora_esperada = int(hora_valida)
                    
                    if hora_esperada <= hora_programada <= hora_esperada + 1:
                        return True, bitacora
                except Exception:
                    pass
            else:
                return True, bitacora
        
        return False, {}
    
if __name__ == "__main__":
    class_obj = Accesos(settings, sys_argv=sys.argv, use_api=False)
    class_obj.console_run()
    data = class_obj.data.get('data',{})
    option = data.get("option", '')
    rondin_data = data.get("rondin_data", {})
    date_from = data.get("date_from", None)
    date_to = data.get("date_to", None)
    limit = data.get("limit", 20)
    offset = data.get("offset", 0)
    folio = data.get("folio", '')
    record_id = data.get("record_id", '')
    ubicacion = data.get("ubicacion", None)
    area = data.get("area", None)
    paused = data.get("paused", True)
    areas = data.get("areas", [])

    if option == 'create_rondin':
        response = class_obj.create_rondin(rondin_data=rondin_data)
    elif option == 'create_incidencia_by_rondin':
        response = class_obj.create_incidencia_by_rondin(data=rondin_data)
    elif option == 'delete_rondin':
        response = class_obj.delete_rondin(folio=folio)
    elif option == 'edit_areas_rondin':
        response = class_obj.edit_areas_rondin(areas=areas, folio=folio, record_id=record_id)
    elif option == 'get_rondines':
        response = class_obj.get_rondines(date_from=date_from, date_to=date_to, limit=limit, offset=offset)
    elif option == 'get_catalog_areas':
        response = class_obj.get_catalog_areas(ubicacion=ubicacion)
    elif option == 'get_rondin_by_id':
        response = class_obj.get_rondin_by_id(record_id=record_id)
    elif option == 'get_incidencias_rondines':
        response = class_obj.get_incidencias_rondines(location=ubicacion, area=area, date_from=date_from, date_to=date_to, limit=limit, offset=offset)
    elif option == 'get_rondines_images':
        response = class_obj.get_rondines_images(location=ubicacion, area=area, date_from=date_from, date_to=date_to, limit=limit, offset=offset)
    elif option == 'get_bitacora_rondines':
        response = class_obj.get_bitacora_rondines(location=ubicacion)
    elif option == 'get_check_by_id':
        response = class_obj.get_check_by_id(record_id=record_id)
    elif option == 'get_bitacora_by_id':
        response = class_obj.get_bitacora_by_id(record_id=record_id)
    elif option == 'get_catalog_areas_formatted':
        response = class_obj.get_catalog_areas_formatted(ubicacion=ubicacion)
    elif option == 'pause_or_play_rondin':
        response = class_obj.pause_or_play_rondin(record_id=record_id, paused=paused)
    elif option == 'update_rondin':
        response = class_obj.update_rondin(folio=folio,rondin_data=rondin_data)
    else:
        response = {"msg": "Empty"}
    class_obj.HttpResponse({"data": response})