# coding: utf-8
from os import close
import re
import sys, simplejson, json, pytz
import time
import unicodedata
from datetime import datetime, timedelta, date
from bson import ObjectId

from linkaform_api import settings
from account_settings import *

from accesos_utils import Accesos
import random
from collections import defaultdict

class Accesos(Accesos):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)
        self.f.update({
            'tag_id_area_ubicacion': '6762f7b0922cc2a2f57d4044',
            'realizado_por': '68cd752bf911c0d6bb1e8e96',
            'comentarios_generales_rondin': '68d5cbdb12b8e764193190a7',
            'bitacora_comentario': '6639b6180bb793945af2742d',
            'status_check_ubicacion': '68e41c904da05123bf9326ee'
        })

    #! Utils functions ==========
    def parse_date_for_sorting(self, date_str):
        if not date_str or not date_str.strip():
            return datetime.max
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.max
    #! ===========================

    def create_cache(self):
        """
        Create a cache entry for a rondin.
        """
        data = {}
        data.update({
            '_id': ObjectId(self.record_id),
            'user_name': self.user_name,
            'location': self.location,
            'folio': self.folio,
            'timestamp': self.timestamp,
            'random': random.random(),
            'check_data': self.answers,
        })
        return self.create(data, collection='rondin_caches')

    def search_cache(self, winner_id=None, location=None, user_name=None):
        """
        Search active caches, optionally filtered by location.
        If both winner_id and location are provided, exclude the entry with that _id and location.
        """
        match_query = {}
        if location:
            match_query['location'] = location
        if winner_id and location:
            # Exclude the specific _id for that location
            match_query['_id'] = {'$ne': ObjectId(winner_id)}
        if user_name:
            match_query['user_name'] = user_name
        query = [
            {'$match': match_query}
        ]
        resp = self.cr_cache.aggregate(query)
        format_resp = list(resp)
        return format_resp

    def clear_cache(self, location=None, record_id=None, winner=None, list_ids=None):
        """
        Clear collection rondin_caches.
        """
        if location:
            self.cr_cache.delete_many({'location': location})
            return
        if record_id:
            self.cr_cache.delete_one({'_id': ObjectId(record_id)})
            return
        if winner:
            self.cr_cache.delete_one({'winner': True})
            return
        if list_ids:
            self.cr_cache.delete_many({'_id': {'$in': list_ids}})
            return
        
        self.cr_cache.delete_many({})

    def get_locations_cache(self):
        locations = set()
        for entry in cache:
            loc = entry.get('location')
            if loc:
                locations.add(loc)
        return locations
    
    def select_winner(self, cache):
        """
        Select a winner rondin from the cache for each location-user combination.
        Winner is the entry with the smallest timestamp per location-user within the last hour.
        If timestamps tie, use the smallest random value as tiebreaker.
        If all entries are older than 1 hour, select the oldest as closed_winner.
        There can be at most 1 winner and 1 closed_winner per location-user combination.
        Return a list of dicts with winner info.
        """
        winners = []
        by_location_user = defaultdict(list)
        now = time.time()
        
        # Agrupar por ubicación y usuario
        for item in cache:
            loc = item.get('location')
            user = item.get('user_name', '')
            if loc is not None and user:
                key = f"{loc}_{user}"
                by_location_user[key].append(item)

        for location_user_key, items in by_location_user.items():
            # Extract location and user from the first item (all have same location and user)
            location = items[0].get('location')
            user = items[0].get('user_name', '')
            
            # Separate items by age
            within_hour = []
            older_than_hour = []
            for item in items:
                ts = item.get('timestamp', 0)
                if ts and now - ts <= 900:
                    within_hour.append(item)
                else:
                    older_than_hour.append(item)

            # Winner: most recent within the last hour
            if within_hour:
                winner = min(
                    within_hour,
                    key=lambda x: (x.get('timestamp', float('inf')), x.get('random', float('inf')))
                )
                winners.append({
                    'winner_id': str(winner.get('_id')), 
                    'location': location, 
                    'user': user,
                    'winner_record': winner, 
                    'type': 'winner'
                })

            # Closed winner: oldest outside the last hour
            if older_than_hour:
                closed_winner = min(
                    older_than_hour,
                    key=lambda x: (x.get('timestamp', float('inf')), x.get('random', float('inf')))
                )
                winners.append({
                    'winner_id': str(closed_winner.get('_id')), 
                    'location': location, 
                    'user': user,
                    'winner_record': closed_winner, 
                    'type': 'closed_winner'
                })

        return winners
    
    def search_active_bitacora_by_rondin(self, recorridos):
        """
        Search for a bitacora by rondin name in form Bitacora Rondines.
        """
        format_names = []
        for recorrido in recorridos:
            format_names.append(recorrido.get('nombre_recorrido', ''))
        
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": self.location,
                f"answers.{self.USUARIOS_OBJ_ID}.{self.f['new_user_complete_name']}": self.user_name,
                # f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.f['nombre_del_recorrido']}": {"$in": format_names},
                f"answers.{self.f['estatus_del_recorrido']}": {'$in': ['en_proceso', 'programado']},
            }},
            {'$sort': {'created_at': -1}},
            {'$limit': 1},
            {'$project': {
                '_id': 1,
                'folio': 1,
                'fecha_programacion': f"$answers.{self.f['fecha_programacion']}",
                'answers': f"$answers"
            }},
        ]
        resp = self.format_cr(self.cr.aggregate(query))
        return resp

    def search_closed_bitacora_by_hour(self, location, search_hour):
        """
        Search for a bitacora by rondin name in form Bitacora Rondines.
        search_hour: string in format 'YYYY-MM-DD HH'
        """
        # Build regex to match the exact hour (e.g., '2024-06-10 15')
        fecha_regex = f"^{search_hour}:"

        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.USUARIOS_OBJ_ID}.{self.f['new_user_complete_name']}": self.user_name,
                f"answers.{self.f['estatus_del_recorrido']}": {"$in": ['cerrado', 'realizado']},
                f"answers.{self.f['fecha_inicio_rondin']}": {"$regex": fecha_regex}
            }},
            {'$sort': {'created_at': 1}},
            {'$limit': 1},
            {'$project': {
                '_id': 1,
                'folio': 1,
                'fecha_inicio_rondin': f"$answers.{self.f['fecha_inicio_rondin']}",
                'answers': f"$answers"
            }},
        ]
        resp = self.format_cr(self.cr.aggregate(query))
        return resp
    
    def update_bitacora(self, cache, rondin):
        """
        Recibe: Las answers del check de ubicacion, el area que se hice check de ubicacion y el registro de rondin
        Retorna: La respuesta de la api al hacer el patch de un registro
        Error: La respuesta de la api al hacer el patch de un registro
        """
        tz = pytz.timezone(self.timezone)
        today = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        rondin = self.unlist(rondin)
        rondin_en_progreso = True
        answers={}
        areas_list = []
        rondin_incidencias_list = rondin.get('bitacora_rondin_incidencias', [])
        incidencias_list = []
        for item in rondin_incidencias_list:
            new_item = {
                self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID: {
                    self.f['nombre_area_salida']: item.get('nombre_area_salida', ''),
                },
                self.f['fecha_hora_incidente_bitacora']: item.get('fecha_hora_incidente_bitacora', ''),
                self.LISTA_INCIDENCIAS_CAT_OBJ_ID: {
                    self.f['categoria']: item.get('categoria', ''),
                    self.f['sub_categoria']: item.get('sub_categoria', ''),
                    self.f['incidente']: item.get('tipo_de_incidencia', ''),
                },
                self.f['incidente_open']: item.get('incidente_open', ''),
                self.f['comentario_incidente_bitacora']: item.get('comentario_incidente_bitacora', ''),
                self.f['incidente_accion']: item.get('incidente_accion', ''),
                self.f['incidente_evidencia']: item.get('incidente_evidencia', []),
                self.f['incidente_documento']: item.get('incidente_documento', []),
            }
            incidencias_list.append(new_item)
        # print('rondinnnnnnnnnnnnnnnnn', simplejson.dumps(rondin, indent=3))

        if not rondin.get('fecha_inicio_rondin'):
            rondin['fecha_inicio_rondin'] = self.timestamp and datetime.fromtimestamp(self.timestamp, tz).strftime('%Y-%m-%d %H:%M:%S')

        conf_recorrido = {}
        for key, value in rondin.items():
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
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            area_name = (
                                item.get('incidente_area') or 
                                item.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['nombre_area'], '')
                            )
                            tag_value = (
                                item.get('tag_id_area_ubicacion') or 
                                item.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['tag_id_area_ubicacion'], '')
                            )
                            if isinstance(tag_value, list):
                                area_tag_id = tag_value
                            else:
                                area_tag_id = [tag_value] if tag_value else []
                            if area_name:
                                areas_list.append({
                                    self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                                        self.f['nombre_area']: area_name,
                                        self.f['tag_id_area_ubicacion']: area_tag_id
                                    },
                                    self.f['fecha_hora_inspeccion_area']: item.get('fecha_hora_inspeccion_area', ''),
                                    self.f['foto_evidencia_area_rondin']: item.get('foto_evidencia_area_rondin', []),
                                    self.f['comentario_area_rondin']: item.get('comentario_area_rondin', ''),
                                    self.f['url_registro_rondin']: item.get('url_registro_rondin', '')
                                })
                
                for cache_item in cache:
                    data_cache = cache_item.get('check_data', {})
                    area_name = self.unlist(
                        data_cache.get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {})
                        .get(self.Location.f['area'], '')
                    )
                    tag_value = data_cache.get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['tag_id_area_ubicacion'], '')
                    if isinstance(tag_value, list):
                        area_tag_id = tag_value
                    else:
                        area_tag_id = [tag_value] if tag_value else []
                    
                    if area_name:
                        grupo_incidencias = data_cache.get(self.f['grupo_incidencias_check'], [])
                        for item in grupo_incidencias:
                            item.update({
                                self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID: {
                                    self.f['nombre_area_salida']: area_name,
                                },
                                self.f['fecha_hora_incidente_bitacora']: cache_item.get('timestamp') and datetime.fromtimestamp(cache_item['timestamp'], tz).strftime('%Y-%m-%d %H:%M:%S')
                            })
                        incidencias_list.extend(data_cache.get(self.f['grupo_incidencias_check'], []))
                        area_record_id = str(cache_item.get('_id'))
                        nueva_area = {
                            self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                                self.f['nombre_area']: area_name,
                                self.f['tag_id_area_ubicacion']: area_tag_id
                            },
                            self.f['fecha_hora_inspeccion_area']: cache_item.get('timestamp') and datetime.fromtimestamp(cache_item['timestamp'], tz).strftime('%Y-%m-%d %H:%M:%S'),
                            self.f['foto_evidencia_area_rondin']: data_cache.get(self.f['foto_evidencia_area'], []),
                            self.f['comentario_area_rondin']: data_cache.get(self.f['comentario_check_area'], ''),
                            self.f['url_registro_rondin']: f"https://app.linkaform.com/#/records/detail/{area_record_id}",
                        }

                        reemplazado = False
                        for idx, area_existente in enumerate(areas_list):
                            nombre_existente = area_existente.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['nombre_area'], '')
                            fecha_existente = area_existente.get(self.f['fecha_hora_inspeccion_area'], '')
                            if nombre_existente == area_name and not fecha_existente:
                                areas_list[idx] = nueva_area
                                reemplazado = True
                                break

                        if not reemplazado:
                            areas_list.append(nueva_area)
            
            all_areas_sorted = sorted(
                areas_list,
                key=lambda x: self.parse_date_for_sorting(x.get(self.f['fecha_hora_inspeccion_area'], ''))
            )
            
            answers[self.f['areas_del_rondin']] = all_areas_sorted
            
            # Dedupe igual que en create_bitacora:
            # agrupar por (nombre_area normalizado, tags normalizados).
            # Si hay entradas con fecha en el grupo -> conservar todas las que tienen fecha.
            # Si ninguna tiene fecha -> conservar la primera (para mantener al menos una entrada).
            grouped = {}
            for a in all_areas_sorted:
                k = self._area_key(a)
                grouped.setdefault(k, []).append(a)

            final_list = []
            for k, items in grouped.items():
                with_date = [it for it in items if it.get(self.f['fecha_hora_inspeccion_area'])]
                if with_date:
                    # conservar todas las entradas que sí tienen fecha (manteniendo orden temporal)
                    final_list.extend(with_date)
                else:
                    # si ninguna tiene fecha, conservar la primera
                    final_list.append(items[0])

            answers[self.f['areas_del_rondin']] = final_list
            answers[self.f['bitacora_rondin_incidencias']] = incidencias_list
        else:
            pass

        answers[self.CONFIGURACION_RECORRIDOS_OBJ_ID] = conf_recorrido
        answers[self.f['fecha_fin_rondin']] = today if data_rondin.get(self.f['check_status'], '') == ['finalizado', 'realizado', 'cerrado'] else ''
        
        if data_rondin.get('answers', {}).get(self.f['check_status']) == 'finalizado':
            answers[self.f['estatus_del_recorrido']] = 'realizado'
        elif data_rondin.get('answers', {}).get(self.f['check_status']) == 'continuar_siguiente_punto_de_inspección':
            answers[self.f['estatus_del_recorrido']] = 'en_proceso'
            

        # print("ans", simplejson.dumps(answers, indent=4))
        if answers:
            metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_RONDINES)
            metadata.update(self.get_record_by_folio(rondin.get('folio'), self.BITACORA_RONDINES, select_columns={'_id': 1}, limit=1))

            metadata.update({
                'properties': {
                    "device_properties": {
                        "system": "Addons",
                        "process":"Actualizacion de Bitacora", 
                        "accion":'rondines_cache', 
                        "folio": rondin.get('folio'), 
                        "archive": "rondines_cache.py"
                    }
                },
                'answers': answers,
                '_id': rondin.get('_id')
            })
            res = self.net.patch_forms_answers(metadata)
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                return res
            else: 
                return res
            
    def normaliza_texto(self, texto):
        if not isinstance(texto, str):
            return ""
        # quitar acentos
        s = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
        s = s.lower()
        # reemplazar espacios/guiones por guion bajo
        s = re.sub(r'[\s\-]+', '_', s)
        # eliminar caracteres que no sean letras, dígitos o guion bajo (quita ' " @ , . etc.)
        s = re.sub(r'[^\w]', '', s)
        # colapsar guiones bajos repetidos y quitar bordes
        s = re.sub(r'_+', '_', s).strip('_')
        return s or texto.lower()
    
    def _area_key(self, a):
        try:
            name_raw = a.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['nombre_area'], '') or ''
        except Exception:
            name_raw = ''
        # normalizar nombre para comparar (quita acentos, espacios, puntuación)
        name = self.normaliza_texto(name_raw)
        tags = a.get(self.f['tag_id_area_ubicacion'], []) or []
        if not isinstance(tags, (list, tuple)):
            tags = [tags]
        # normalizar tags también por si vienen como texto
        norm_tags = tuple(self.normaliza_texto(t) if isinstance(t, str) else str(t) for t in tags)
        return (name, norm_tags)
            
    def create_bitacora(self, winner, recorridos, closed=False):
        """
        Create a bitacora entry from cache data.
        """
        nombre_del_recorrido = ""
        ubicacion_del_recorrido = ""
        id_del_recorrido = ""
        print('Recorridos encontrados:', recorridos)
        for recorrido in recorridos:
            nombre_del_recorrido = recorrido.get('nombre_recorrido')
            ubicacion_del_recorrido = recorrido.get('ubicacion_recorrido')
            id_del_recorrido = recorrido.get('_id')

        if id_del_recorrido:
            areas_recorrido = self.get_areas_recorrido(id_del_recorrido)
            print('Áreas del recorrido:', areas_recorrido)
        else:
            areas_recorrido = []
            nombre_del_recorrido = 'Recorrido Automático'
            ubicacion_del_recorrido = winner.get('location', self.location)

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

        tz = pytz.timezone(self.timezone)

        print('winner in bitacora:', winner)
        answers[self.f['fecha_programacion']] = winner.get('timestamp') and datetime.fromtimestamp(winner.get('timestamp'), tz).strftime('%Y-%m-%d %H:%M:%S')
        answers[self.f['fecha_inicio_rondin']] = winner.get('timestamp') and datetime.fromtimestamp(winner.get('timestamp'), tz).strftime('%Y-%m-%d %H:%M:%S')
        answers[self.USUARIOS_OBJ_ID] = {
            self.f['new_user_complete_name']: self.user_name,
            self.f['new_user_id']: [self.user_id],
            self.f['new_user_email']: [self.user_email],
        }
        answers[self.CONFIGURACION_RECORRIDOS_OBJ_ID] = {
            self.f['ubicacion_recorrido']: ubicacion_del_recorrido,
            self.f['nombre_del_recorrido']: nombre_del_recorrido
        }
        answers[self.f['estatus_del_recorrido']] = 'cerrado' if closed else 'en_proceso'
        check_areas_list = []
        incidencias_list = []
        for area in winner.get('checks', []):
            area_record_id = str(area.get('_id'))
            tag_value = area['check_data'].get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['tag_id_area_ubicacion'], '')
            grupo_incidencias = area['check_data'].get(self.f['grupo_incidencias_check'], [])
            for item in grupo_incidencias:
                item.update({
                    self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID: {
                        self.f['nombre_area_salida']: self.unlist(area['check_data'].get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.Location.f['area'], '')),
                    },
                    self.f['fecha_hora_incidente_bitacora']: area.get('timestamp') and datetime.fromtimestamp(area.get('timestamp'), tz).strftime('%Y-%m-%d %H:%M:%S'),
                })
            incidencias_list.extend(area['check_data'].get(self.f['grupo_incidencias_check'], []))
            if isinstance(tag_value, list):
                area_tag_id = tag_value
            else:
                area_tag_id = [tag_value] if tag_value else []
            format_area = {
                self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                    self.f['nombre_area']: self.unlist(area['check_data'].get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.Location.f['area'], [])),
                    self.f['tag_id_area_ubicacion']: area_tag_id
                },
                self.f['fecha_hora_inspeccion_area']: area.get('timestamp') and datetime.fromtimestamp(area.get('timestamp'), tz).strftime('%Y-%m-%d %H:%M:%S'),
                self.f['foto_evidencia_area_rondin']: area['check_data'].get(self.f['foto_evidencia_area'], []),
                self.f['comentario_area_rondin']: area['check_data'].get(self.f['comentario_check_area'], ''),
                self.f['url_registro_rondin']: f"https://app.linkaform.com/#/records/detail/{area_record_id}",
            }
            check_areas_list.append(format_area)
            
        check_areas_list.sort(key=lambda x: self.parse_date_for_sorting(x.get(self.f['fecha_hora_inspeccion_area'], '')))
        answers[self.f['areas_del_rondin']] = check_areas_list

        for area in areas_recorrido:
            if not area.get('incidente_area') == self.check_area:
                answers[self.f['areas_del_rondin']].append({
                    self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                        self.f['nombre_area']: area.get('incidente_area', '')
                    },
                })
        # Dedupe: agrupar por (nombre_area, tags). Si hay al menos una entrada con fecha,
        # eliminar las entradas sin fecha para esa agrupación. Si hay varias con fecha, conservarlas todas.
        grouped = {}
        final_list = []
        for a in answers[self.f['areas_del_rondin']]:
            k = self._area_key(a)
            grouped.setdefault(k, []).append(a)

        for k, items in grouped.items():
            with_date = [it for it in items if it.get(self.f['fecha_hora_inspeccion_area'])]
            if with_date:
                # conservar todas las entradas que sí tienen fecha
                final_list.extend(with_date)
            else:
                # si ninguna tiene fecha, conservar la primera (o todas si prefieres)
                final_list.append(items[0])

        answers[self.f['areas_del_rondin']] = final_list
        answers[self.f['bitacora_rondin_incidencias']] = incidencias_list

        metadata.update({'answers':answers})
        print(simplejson.dumps(metadata, indent=3))

        res = self.lkf_api.post_forms_answers(metadata)
        return res
    
    def search_rondin_by_area(self):
        """
        Search for a rondin by location and check_area in form Configuracion de Recorridos.
        """
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.CONFIGURACION_DE_RECORRIDOS_FORM,
                f"answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": self.location,
                f"answers.{self.f['grupo_de_areas_recorrido']}": {'$exists': True}
            }},
            {'$unwind': f"$answers.{self.f['grupo_de_areas_recorrido']}"},
            {'$project': {
                '_id': 1,
                'match_area': f"$answers.{self.f['grupo_de_areas_recorrido']}.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area']}",
                'nombre_recorrido': f"$answers.{self.f['nombre_del_recorrido']}",
                'ubicacion_recorrido': f"$answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_recorrido']}"
            }},
            {'$match': {
                'match_area': self.check_area
            }},
            {"$project": {
                "_id": 1,
                "nombre_recorrido": 1,
                "ubicacion_recorrido": 1
            }}
        ]
        resp = self.cr.aggregate(query)
        resp = list(resp)
        return resp
    
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

    def set_winners(self, winners_ids):
        for winner_id in winners_ids:
            self.cr_cache.update_one(
                {'_id': ObjectId(winner_id)},
                {'$set': {'winner': True}}
            )
            
    def update_check_ubicacion(self):
        # response = self.cr.update_one({
        #     'form_id': self.form_id,
        #     '_id': ObjectId(self.record_id),
        # },{'$set': {
        #     f'answers.{self.f["status_check_ubicacion"]}': 'Area no configurada'
        # }})
        answers = {self.f["status_check_ubicacion"]: 'Area no configurada'}
        response = self.lkf_api.patch_multi_record(answers=answers, form_id=self.form_id, record_id= [self.record_id,])
        if response.get('status_code') in (200,201,202):
            print(f"===== log: Status actualizado. Area no configurada.")
        return response.get('status_code')

    def search_closed_bitacora_by_time(self, location, search_dt, window_seconds=1200):
        """
        Buscar una bitácora cerrada para una ubicación dentro de una ventana de tiempo.
        - location: nombre/valor de la ubicación
        - search_dt: datetime (tz-aware) del check ganador
        - window_seconds: +/- segundos para buscar (por defecto 900 = 15min)
        Retorna la primera bitácora encontrada (orden asc por created_at) o [].
        """
        # asegurar datetime tz-aware
        search_dt = datetime.strptime(search_dt, "%Y-%m-%d %H:%M:%S")
        start_dt = None
        end_dt = None
        if not search_dt:
            return []
        try:
            # window en strings 'YYYY-MM-DD HH:MM:SS'
            start_dt = (search_dt - timedelta(seconds=window_seconds)).strftime('%Y-%m-%d %H:%M:%S')
            end_dt = (search_dt + timedelta(seconds=window_seconds)).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print('Error al calcular las fechas de inicio y fin.', e)
            return []

        fecha_field = f"answers.{self.f['fecha_inicio_rondin']}"
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.USUARIOS_OBJ_ID}.{self.f['new_user_complete_name']}": self.user_name,
                f"answers.{self.f['estatus_del_recorrido']}": {"$in": ['cerrado', 'realizado', 'programado']},
                # comparar como strings ISO 'YYYY-MM-DD HH:MM:SS' usando rango
                f"answers.{self.f['fecha_inicio_rondin']}": {"$gte": start_dt, "$lte": end_dt}
            }},
            {'$sort': {'created_at': 1}},
            {'$limit': 1},
            {'$project': {
                '_id': 1,
                'folio': 1,
                'fecha_inicio_rondin': f"${fecha_field}",
                'answers': f"$answers"
            }},
        ]
        resp = self.format_cr(self.cr.aggregate(query))
        return resp

if __name__ == "__main__":
    script_obj = Accesos(settings, sys_argv=sys.argv)
    script_obj.console_run()
    script_obj.cr_cache = script_obj.net.get_collections(collection='rondin_caches')
    # print(simplejson.dumps(script_obj.answers, indent=3))
    data_rondin = script_obj.current_record
    script_obj.user_name = data_rondin.get('created_by_name', '')
    script_obj.user_id = data_rondin.get('created_by_id', 0)
    script_obj.user_email = data_rondin.get('created_by_email', '')
    script_obj.timestamp = data_rondin.get('start_timestamp', '')
    script_obj.timezone = data_rondin.get('timezone', 'America/Mexico_City')
    tz = pytz.timezone(script_obj.timezone)
    # cache = script_obj.search_cache()
    # print('cache', cache)
    # script_obj.clear_cache()
    # breakpoint()

    location = script_obj.answers.get(script_obj.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {})
    script_obj.location = script_obj.unlist(location.get(script_obj.Location.f['location'], ''))
    check_area = script_obj.answers.get(script_obj.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {})
    script_obj.check_area = script_obj.unlist(check_area.get(script_obj.Location.f['area'], ''))
    
    #! 1. Obtener los recorridos existentes para el area ejecutada
    recorridos = script_obj.search_rondin_by_area()
    if not recorridos:
        print('===== log: No se encontró un recorrido para esta ubicación y área.')
        resp = script_obj.update_check_ubicacion()
        text_no_conf = 'Esta area no pertenece a este rondin.'
        script_obj.answers[script_obj.f['comentario_check_area']] = (
            script_obj.answers.get(script_obj.f['comentario_check_area'], '') + '\n' + text_no_conf
            if script_obj.answers.get(script_obj.f['comentario_check_area'], '') else text_no_conf
        )

    #! 2. Se crea un cache con la informacion de el check
    script_obj.create_cache()
    time.sleep(5)
    cache = script_obj.search_cache()

    #! 3. Se obtienen las ubicaciones(sin repetir) del cache
    cache_locations = script_obj.get_locations_cache()
    
    #! 4. Se verifica si ya hay ganadores y si no se buscan por ubicacion y si ya tiene tiempo el check
    winners = script_obj.select_winner(cache)
    winners_ids = [winner.get('winner_id') for winner in winners]
    script_obj.set_winners(winners_ids)
    cache = script_obj.search_cache()

    #! 5. Verificar si eres un ganador
    if script_obj.record_id in winners_ids:
        selected_winner = [winner for winner in winners if winner.get('winner_id') == script_obj.record_id]
        winner = selected_winner[0] if selected_winner else None
        if winner:
            winner_timestamp = winner.get('winner_record', {}).get('timestamp')
            winner_date = winner_timestamp and datetime.fromtimestamp(winner_timestamp, tz).strftime('%Y-%m-%d %H:%M:%S')
            now = datetime.now(tz)
            if winner_date:
                winner_dt = tz.localize(datetime.strptime(winner_date, '%Y-%m-%d %H:%M:%S'))
                diff = now - winner_dt
                winner_hour = winner_dt.strftime('%Y-%m-%d %H:%M:%S')
                
                #! Verificar si hay rondines que cerrar
                rondines = script_obj.get_rondines_by_status()
                print('Timezone:', script_obj.timezone)
                print('now:', now)
                print('winner_dt:', winner_dt)
                print('diff:', diff)
                response = script_obj.close_rondines(rondines, timezone=script_obj.timezone)
                if response:
                    print("response closed_rondines", response)
                else:
                    print("No hay rondines que cerrar")

                #! 7. Verificamos si ha pasado mas de 15 minutos de este check pasado
                if diff.total_seconds() > 900 and winner.get('type') == 'closed_winner':
                    print('Ha pasado más de 15 minutos desde el winner_date.')
                    #! 7-1 Se busca una bitacora cerrada para la hora en que se hizo este check
                    bitacora = script_obj.search_closed_bitacora_by_time(winner.get('location'), winner_hour)
                    time.sleep(5)
                    winner_checks = script_obj.search_cache(winner_id=winner.get('winner_id'), location=winner.get('location'), user_name=script_obj.user_name)
                    print('winner_checks:============', len(winner_checks))
                    #! 7-1-1 Se filtran los checks que pertenezcan a la hora del check ganador
                    window_seconds = 30 * 60  # 30 minutos
                    start_dt = winner_dt
                    end_dt = winner_dt + timedelta(seconds=window_seconds)
                    filter_winner_checks = []
                    for check in winner_checks:
                        check_timestamp = check.get('timestamp')
                        if not check_timestamp:
                            continue
                        check_dt = datetime.fromtimestamp(check_timestamp, tz)
                        if start_dt <= check_dt <= end_dt:
                            filter_winner_checks.append(check)
                    winner_checks = filter_winner_checks
                    winner_checks.append(winner.get('winner_record', {}))
                    if bitacora:
                        #! 7-1-2. Actualizar una bitacora ya cerrada con los checks perdidos
                        response = script_obj.update_bitacora(winner_checks, bitacora)
                        print('response:', response)
                    else:
                        #! 7-1-3. Crea una bitacora ya cerrada con los checks perdidos
                        winner_record = winner.get('winner_record', {})
                        winner_record.update({
                            'checks': winner_checks
                        })
                        response = script_obj.create_bitacora(winner=winner_record, recorridos=recorridos, closed=True)
                        print('response:', response)
                    clear_ids = [check.get('_id') for check in winner_checks]
                    clear_res = script_obj.clear_cache(list_ids=clear_ids)
                else:
                    #! 7-2-1 Se busca una bitacora activa para la hora en que se hizo este check
                    print('No ha pasado más de 1 hora desde el winner_date.')
                    bitacora = script_obj.search_active_bitacora_by_rondin(recorridos=recorridos)
                    print('bitacora activa encontrada:', bitacora)
                    time.sleep(5)
                    winner_checks = script_obj.search_cache(winner_id=winner.get('winner_id'), location=winner.get('location'), user_name=script_obj.user_name)
                    winner_checks.append(winner.get('winner_record', {}))
                    if bitacora:
                        #! 7-2-2. Actualizar una bitacora con los checks realizados
                        response = script_obj.update_bitacora(winner_checks, bitacora)
                        print('response:', response)
                    else:
                        #! 7-2-3. Crea una bitacora con los checks realizados
                        print('No se encontró una bitácora activa por rondín.')
                        winner_record = winner.get('winner_record', {})
                        winner_record.update({
                            'checks': winner_checks
                        })
                        response = script_obj.create_bitacora(winner=winner_record, recorridos=recorridos)
                        print('response:', response)
                    clear_ids = [check.get('_id') for check in winner_checks]
                    clear_res = script_obj.clear_cache(list_ids=clear_ids)
                        
        #! Ver cache final
        response = script_obj.search_cache()
        print('cache_final:', response)
    else:
        print('No eres ganador.')
