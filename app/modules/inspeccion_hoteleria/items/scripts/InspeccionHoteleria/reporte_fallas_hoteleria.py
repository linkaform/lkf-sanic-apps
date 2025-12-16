# -*- coding: utf-8 -*-
from ast import mod
import enum
from pickle import NONE
import re
import sys, simplejson
import datetime
import unicodedata
from copy import deepcopy
from collections import Counter

from inspeccion_hoteleria_utils import Inspeccion_Hoteleria

from account_settings import *
from bson import ObjectId
import datetime

class Inspeccion_Hoteleria(Inspeccion_Hoteleria):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)

        self.cr_inspeccion = self.net.get_collections(collection='inspeccion_hoteleria')
        
        self.labels_to_exclude = [
            'Nombre de la Camarista',
            'Habitación Remodelada',
            'Fotografía',
            'Comentarios',
            '¿La habitación es suite?',
            'Comentarios Generales',
            'STATUS AUDITORIA',
            'DIAS EN PROCESO',
            'status_auditoria',
            'dias_en_proceso'
        ]
        
        self.ids_to_exclude = [
            '67f81a13a48f0a56cf242558',
            '680bb736c2009c72987ba955',
            '680bb736c2009c72987ba957',
            '680bb736c2009c72987ba959',
            '680bb736c2009c72987ba95b',
            '680bb736c2009c72987ba95d',
            '680bb736c2009c72987ba95f',
            '680bb736c2009c72987ba961',
            '680bb736c2009c72987ba963',
            '680bb736c2009c72987ba965',
            '680bb736c2009c72987ba967'
        ]
        
        self.fallas_dict = {}

        self.f.update({
            'tipo_ubicacion': '683d2970bb02c9bb7a0bfe1c',
            'habitacion_remodelada': '67f0844734855c523e1390d7',
            'ubicacion_nombre': '663e5c57f5b8a7ce8211ed0b',
            'tipo_area': '663e5e68f5b8a7ce8211ed18',
            'status_auditoria': '67f0844734855c523e139132',
            'tipo_area_habitacion': '663e5e68f5b8a7ce8211ed18',
            'numero_habitacion': '680977786d022b9bff6e3645',
            'piso_habitacion': '680977786d022b9bff6e3646',
            'nombre_area_habitacion': '663e5d44f5b8a7ce8211ed0f',
            'nombre_camarista': '67f0844734855c523e1390d6'
        })

        self.form_ids = {
            'hi_parque_fundidora': self.HI_PARQUE_FUNDIDORA,
            'crowne_plaza_torreon': self.CROWNE_PLAZA_TORREN,
            'travo': self.TRAVO,
            'hie_tecnologico': self.HIE_TECNOLGICO,
            'wyndham_garden_mcallen': self.WYNDHAM_GARDEN_MCALLEN,
            'istay_victoria': self.ISTAY_VICTORIA,
            'hie_torreon': self.HIE_TORREN,
            'hilton_garden_silao': self.HILTON_GARDEN_SILAO,
            'ms_milenium': self.MS_MILENIUM,
            'istay_monterrey_historico': self.ISTAY_MONTERREY_HISTRICO,
            'hie_guanajuato': self.HIE_GUANAJUATO,
            'hie_silao': self.HIE_SILAO,
            'istay_ciudad_juarez': self.ISTAY_CIUDAD_JUREZ,
            'crowne_plaza_mty': self.CROWNE_PLAZA_MONTERREY,
            'hie_galerias': self.HIE_GALERIAS,
            'holiday_inn_tijuana': self.HOLIDAY_INN_TIJUANA,
        }

        self.hotel_name_abreviatura = {
            'HILTON GARDEN SILAO': 'HGI SILAO',
            'HOLIDAY INN TIJUANA': 'HI TIJUANA ZONA RIO',
            'WYNDHAM GARDEN MCALLEN': 'MCALLEN',
        }
        self.my_hotels_ids = []

        #TODO variable temporal para obtener el nombre del hotel segun el nombre de la forma
        self.form_name_hotel_name = {
            'Revisión de Habitaciones HIE Guanajuato': self.HIE_GUANAJUATO,
            'Revisión de Habitaciones Crowne Plaza Torreón': self.CROWNE_PLAZA_TORREN,
            'Revisión de Habitaciones HI Parque Fundidora': self.HI_PARQUE_FUNDIDORA,
            'Revisión de Habitaciones HIE Galerias': self.HIE_GALERIAS,
            'Revisión de Habitaciones Crowne Plaza Monterrey': self.CROWNE_PLAZA_MONTERREY,
            'Revisión de Habitaciones HIE Silao': self.HIE_SILAO,
            'Revisión de Habitaciones HIE Tecnológico': self.HIE_TECNOLGICO,
            'Revisión de Habitaciones HIE Torreón': self.HIE_TORREN,
            'Revisión de Habitaciones Hilton Garden Silao': self.HILTON_GARDEN_SILAO,
            'Revisión de Habitaciones Holiday Inn Tijuana': self.HOLIDAY_INN_TIJUANA,
            'Revisión de Habitaciones ISTAY Ciudad Juárez': self.ISTAY_CIUDAD_JUREZ,
            'Revisión de Habitaciones ISTAY Monterrey Histórico': self.ISTAY_MONTERREY_HISTRICO,
            'Revisión de Habitaciones ISTAY Victoria': self.ISTAY_VICTORIA,
            'Revisión de Habitaciones MS Milenium': self.MS_MILENIUM,
            'Revisión de Habitaciones TRAVO': self.TRAVO,
            'Revisión de Habitaciones WYNDHAM GARDEN MCALLEN': self.WYNDHAM_GARDEN_MCALLEN,
        }


    def normalize_types(self, obj):
        if isinstance(obj, list):
            return [self.normalize_types(x) for x in obj]
        elif isinstance(obj, dict):
            return {k: self.normalize_types(v) for k, v in obj.items()}
        elif isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return obj
        
    def normaliza_texto(self, texto):
        if not isinstance(texto, str):
            return ""
        texto = texto.lower()
        texto = texto.replace(" ", "_")
        texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('ascii')
        return texto
    
    def limpia_keys_dict(self, dic):
        return {k.replace('.', '_'): v for k, v in dic.items()}

    @property
    def my_hotels(self):
        if not self.my_hotels_ids:
            # forms = self.lkf_api.get_all_forms()
            user_id = self.user.get('user_id')
            # user_id = 7742
            forms = self.lkf_api.get_user_forms(user_id)
            all_forms = forms.get('data')
            #TODO cambiar a obtener ids de la forma
            forms = [f['name'] for f in all_forms if f.get('name')]
            my_hotels = []
            # for f in forms:
            #     if self.form_name_hotel_name.get(f):
            #     my_hotels.append(self.form_name_hotel_name.get(f))
            my_hotels = [self.form_name_hotel_name[f] for f in forms if self.form_name_hotel_name.get(f)]
            # my_hotels = [f['form_id'] for f in forms if f.get('form_id')]
            self.my_hotels_ids = my_hotels
        return self.my_hotels_ids


    def get_hoteles(self):
        # print('mis hoteles', self.my_hotels)
        # query = [
        #     {'$match': {
        #         "deleted_at": {"$exists": False},
        #         "form_id": self.Location.UBICACIONES,
        #         f"answers.{self.f['tipo_ubicacion']}": "hotel",
        #     }},
        #     {'$project': {
        #         '_id': 0,
        #         'nombre_hotel': f"$answers.{self.Location.f['location']}",
        #     }},
        # ]

        # result = self.format_cr(self.cr.aggregate(query))
        # TODO
        # Temp se descarta corporativo mexico porque no cuenta con una forma de inspeccion
        my_hotels_set = set(self.my_hotels)
        # result = [
        #     h for h in result
        #     if h.get('nombre_hotel', '').strip().upper() != 'CORPORATIVO MEXICO'
        # ]
        filtered_form_ids = [
            {'nombre_hotel': name.upper().replace('_', ' ')}
            for name, form_id in self.form_ids.items()
            if form_id in my_hotels_set
        ]
        # * Cambia MCALLEN por WYNDHAM GARDEN MCALLEN para que sea el nombre valido en la inspeccion
        # for h in filtered_form_ids:
        #     if h.get('nombre_hotel', '').strip().upper() == 'MCALLEN':
        #         h['nombre_hotel'] = 'WYNDHAM GARDEN MCALLEN'
        
        hoteles = {
            'hoteles': filtered_form_ids
        }
        return hoteles
    
    def get_cantidad_si_y_no(self, forms_id_list=[]):
        match_query = {
            "deleted_at": {"$exists": False},
        }

        if len(forms_id_list) > 1:
            match_query.update({
                "form_id": {"$in": forms_id_list},
            })
        else:
            match_query.update({
                "form_id": self.unlist(forms_id_list),
            })

        query = [
            {'$match': match_query},
            {'$project': {
                '_id': 1,
                'paresAnswers': { '$objectToArray': "$answers" }
            }},
            {'$unwind': "$paresAnswers"},
            {'$match': {
                "paresAnswers.v": { '$in': [ "sí", "no" ] }
            }},
            {'$group': {
                '_id': "$paresAnswers.v",
                'total': { '$sum': 1 }
            }},
            {'$project': {
                '_id': 0,
                'respuesta': '$_id',
                'total': 1
            }},
        ]

        result = self.format_cr(self.cr.aggregate(query))
        
        return result
    
    def get_cantidad_habitaciones(self, ubicaciones_list=[]):

        if isinstance(ubicaciones_list, list):
            ubicaciones_list = [
                str(u).replace('_', ' ').upper() for u in ubicaciones_list
            ]

        if isinstance(ubicaciones_list, list):
            ubicaciones_list = [
                self.hotel_name_abreviatura.get(u.replace('_', ' ').upper(), u)
                for u in ubicaciones_list
            ]

        match_query = {
            "deleted_at": {"$exists": False},
            f"answers.{self.Location.TIPO_AREA_OBJ_ID}.{self.f['tipo_area']}": "Habitación",
        }

        if isinstance(ubicaciones_list, list) and len(ubicaciones_list) > 1:
            match_query.update({
               f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": {"$in": ubicaciones_list}
            })
        elif isinstance(ubicaciones_list, list) and len(ubicaciones_list) == 1:
            match_query.update({
               f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": self.unlist(ubicaciones_list)
            })

        query = [
            {'$match': match_query},
            {
                '$count': "totalHabitaciones"
            }
        ]

        result = self.format_cr(self.cr.aggregate(query))
        result = self.unlist(result)

        return result

    def get_cantidad_inspecciones_y_remodeladas(self, forms_id_list=[], anio=None, cuatrimestres=None):
        match_query = {
            "deleted_at": {"$exists": False},
        }

        if len(forms_id_list) > 1:
            match_query.update({
                "form_id": {"$in": forms_id_list}
            })
        else:
            match_query.update({
                "form_id": self.unlist(forms_id_list)
            })
    
        # Pipeline para agregar año y cuatrimestre
        pipeline = [
            {'$match': match_query},
            {'$addFields': {
                "_anio": {"$year": "$created_at"},
                "_mes": {"$month": "$created_at"}
            }},
            {'$addFields': {
                "_cuatrimestre": {
                    "$ceil": {"$divide": ["$_mes", 4]}
                }
            }},
        ]
    
        # Filtro por año y cuatrimestre si se pasan como parámetro
        match_cuatrimestre = {}
        if anio is not None:
            match_cuatrimestre["_anio"] = anio
        if cuatrimestres:
            match_cuatrimestre["_cuatrimestre"] = {"$in": cuatrimestres}
        if match_cuatrimestre:
            pipeline.append({"$match": match_cuatrimestre})
    
        status_validos = ["completada", "proceso", "incompleta"]
    
        pipeline += [
            {'$project': {
                'status_completada': {
                    '$cond': [
                        { '$in': [f"$answers.{self.f['status_auditoria']}", status_validos] },
                        1,
                        0
                    ]
                },
                'habitacion_remodelada_si': {
                    '$cond': [
                        {
                            '$and': [
                                { '$eq': [f"$answers.{self.f['habitacion_remodelada']}", "sí"] },
                                { '$eq': [f"$answers.{self.f['status_auditoria']}", "completada"] }
                            ]
                        },
                        1,
                        0
                    ]
                }
            }},
            {
                '$group': {
                    '_id': None,
                    'total_inspecciones_completadas': { '$sum': "$status_completada" },
                    'total_habitaciones_remodeladas': { '$sum': "$habitacion_remodelada_si" }
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'total_inspecciones_completadas': 1,
                    'total_habitaciones_remodeladas': 1
                }
            }
        ]
    
        result = self.format_cr(self.cr.aggregate(pipeline))
        result = self.unlist(result)
    
        return result
    
    def resumen_cuatrimestres(self, calificaciones_dict):
        calificaciones = calificaciones_dict.get('cuatrimestres', [])
        if not calificaciones:
            return {
                'max_global': None,
                'min_global': None,
                'promedio_global': None
            }
    
        max_global = max(item['max'] for item in calificaciones)
        min_global = min(item['min'] for item in calificaciones)
        promedio_global = round(sum(item['promedio'] for item in calificaciones) / len(calificaciones), 2)
    
        return {
            'max_global': max_global,
            'min_global': min_global,
            'promedio_global': promedio_global
        }

    def get_calificaciones(self, forms_id_list=[], anio=None, cuatrimestres=None):
        match_query = {
            "deleted_at": {"$exists": False},
        }

        if len(forms_id_list) > 1:
            match_query.update({
                "form_id": {"$in": forms_id_list},
            })
        else:
            match_query.update({
                "form_id": self.unlist(forms_id_list),
            })

        query = [
            {'$match': match_query},
            {
                "$lookup": {
                    "from": "voucher",
                    "let": { "vid": { "$toObjectId": "$voucher_id" } },
                    "pipeline": [
                        { "$match": { "$expr": { "$eq": [ "$_id", "$$vid" ] } } },
                        { "$project": { "_id": 0, "max_points": "$grading.max_points" } }
                    ],
                    "as": "voucherInfo"
                }
            },
            {
                "$unwind": {
                    "path": "$voucherInfo",
                    "preserveNullAndEmptyArrays": False
                }
            },
            {
                "$match": {
                    "points": { "$type": "double" }
                }
            },
            {
                "$addFields": {
                    "calificacion": {
                        "$multiply": [
                            { "$divide": [ "$points", "$voucherInfo.max_points" ] },
                            100
                        ]
                    }
                }
            },
            {
                "$addFields": {
                    "_fecha": {
                        "$cond": [
                            {
                                "$in": [
                                    { "$type": "$start_date" },
                                    [ "double", "int", "long", "decimal" ]
                                ]
                            },
                            { "$toDate": { "$multiply": [ "$start_date", 1000 ] } },
                            "$start_date"
                        ]
                    }
                }
            },
            {
                "$addFields": {
                    "_anio": { "$year":  "$_fecha" },
                    "_mes":  { "$month": "$_fecha" }
                }
            },
            {
                "$addFields": {
                    "_cuatrimestre": {
                        "$ceil": { "$divide": [ "$_mes", 4 ] }
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "anio":         "$_anio",
                        "cuatrimestre": "$_cuatrimestre"
                    },
                    "maxCalif": { "$max": "$calificacion" },
                    "minCalif": { "$min": "$calificacion" },
                    "avgCalif": { "$avg": "$calificacion" }
                }
            },
            {
                "$project": {
                    "_id":          0,
                    "anio":         "$_id.anio",
                    "cuatrimestre": "$_id.cuatrimestre",
                    "max":          { "$round": [ "$maxCalif", 2 ] },
                    "min":          { "$round": [ "$minCalif", 2 ] },
                    "promedio":     { "$round": [ "$avgCalif", 2 ] }
                }
            }
        ]

        match_filter = {}
        if anio is not None:
            match_filter["anio"] = anio
        if cuatrimestres:
            match_filter["cuatrimestre"] = {"$in": cuatrimestres}
        if match_filter:
            query.append({"$match": match_filter})

        query.append({
            "$sort": {
                "anio": 1,
                "cuatrimestre": 1
            }
        })

        result = self.format_cr(self.cr.aggregate(query))

        calificaciones = {
            'cuatrimestres': result,
        }

        resumen = self.resumen_cuatrimestres(calificaciones)
        calificaciones['resumen'] = resumen

        return calificaciones

    def porcentaje_propiedades_inspeccionadas(self, total_habitaciones, total_inspecciones):
        if total_habitaciones == 0:
            return 0.0
    
        porcentaje = (total_inspecciones / total_habitaciones) * 100
        return round(porcentaje, 2)

    def get_forms_id_list(self, hoteles=None):
        print("hoteles", hoteles)
        
        if not hoteles:
            my_hotels_set = set(self.my_hotels)
            filtered_ids = [fid for fid in self.form_ids.values() if fid in my_hotels_set]

            return filtered_ids

        hoteles_normalizados = [
            hotel.lower().replace(' ', '_') for hotel in hoteles
        ]

        ids = [
            self.form_ids[nombre]
            for nombre in hoteles_normalizados
            if nombre in self.form_ids
        ]

        return ids

    def get_cuatrimestres_by_hotel(self, hoteles=[], anio=None, cuatrimestres=None):
        forms_id_list = self.get_forms_id_list(hoteles)
        match_query = {
            "deleted_at": {"$exists": False},
        }

        if len(forms_id_list) > 1:
            match_query.update({
                "form_id": {"$in": forms_id_list}, # type: ignore
            }) # type: ignore
        else:
            match_query.update({
                "form_id": self.unlist(forms_id_list),
            })

        query = [
            {'$match': match_query},
            {
                "$lookup": {
                    "from": "voucher",
                    "let": { "vid": { "$toObjectId": "$voucher_id" } },
                    "pipeline": [
                        { "$match": { "$expr": { "$eq": [ "$_id", "$$vid" ] } } },
                        { "$project": { "_id": 0, "max_points": "$grading.max_points" } }
                    ],
                    "as": "voucherInfo"
                }
            },
            {
                "$unwind": {
                    "path": "$voucherInfo",
                    "preserveNullAndEmptyArrays": False
                }
            },
            {
                "$match": {
                    "points": { "$type": "double" }
                }
            },
            {
                "$addFields": {
                    "calificacion": {
                        "$multiply": [
                            { "$divide": [ "$points", "$voucherInfo.max_points" ] },
                            100
                        ]
                    }
                }
            },
            {
                "$addFields": {
                    "_fecha": {
                        "$cond": [
                            {
                                "$in": [
                                    { "$type": "$start_date" },
                                    [ "double", "int", "long", "decimal" ]
                                ]
                            },
                            { "$toDate": { "$multiply": [ "$start_date", 1000 ] } },
                            "$start_date"
                        ]
                    }
                }
            },
            {
                "$addFields": {
                    "_anio": { "$year":  "$_fecha" },
                    "_mes":  { "$month": "$_fecha" }
                }
            },
            {
                "$addFields": {
                    "_cuatrimestre": {
                        "$ceil": { "$divide": [ "$_mes", 4 ] }
                    }
                }
            },
            {
                "$group": {
                    "_id": {
                        "form_id": "$form_id",
                        "anio": "$_anio",
                        "cuatrimestre": "$_cuatrimestre"
                    },
                    "maxCalif": { "$max": "$calificacion" },
                    "minCalif": { "$min": "$calificacion" },
                    "avgCalif": { "$avg": "$calificacion" }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "form_id": "$_id.form_id",
                    "anio": "$_id.anio",
                    "cuatrimestre": "$_id.cuatrimestre",
                    "max": { "$round": [ "$maxCalif", 2 ] },
                    "min": { "$round": [ "$minCalif", 2 ] },
                    "promedio": { "$round": [ "$avgCalif", 2 ] }
                }
            }
        ]

        match_filter = {}
        # Si pides los 3 cuatrimestres, ajusta el año del cuatrimestre 3
        if anio is not None and cuatrimestres and set(cuatrimestres) == {1, 2, 3}:
            query.append({
                "$match": {
                    "$or": [
                        {"anio": anio, "cuatrimestre": {"$in": [1, 2]}},
                        {"anio": anio - 1, "cuatrimestre": 3}
                    ]
                }
            })
        else:
            if anio is not None:
                match_filter["anio"] = anio
            if cuatrimestres:
                match_filter["cuatrimestre"] = {"$in": cuatrimestres}
            if match_filter:
                query.append({"$match": match_filter})

        query.append({
            "$sort": {
                "form_id": 1,
                "anio": 1,
                "cuatrimestre": 1
            }
        })

        result = self.format_cr(self.cr.aggregate(query))

        form_id_to_hotel = {v: k for k, v in self.form_ids.items()}
        for item in result:
            item["hotel"] = form_id_to_hotel.get(item["form_id"], item["form_id"])

        hoteles_list = []
        agrupados = {}

        for item in result:
            hotel = item["hotel"]
            if hotel not in agrupados:
                agrupados[hotel] = []
            agrupados[hotel].append({
                "anio": item["anio"],
                "cuatrimestre": item["cuatrimestre"],
                "max": item["max"],
                "min": item["min"],
                "promedio": item["promedio"]
            })

        for hotel, cuatrimestres in agrupados.items():
            hoteles_list.append({
                "hotel": hotel,
                "cuatrimestres": cuatrimestres
            })

        return hoteles_list

    def get_fallas(self, forms_id_list=[], anio=None, cuatrimestres=None):
        match_query = {
            "deleted_at": {"$exists": False},
        }
    
        if len(forms_id_list) > 1:
            match_query["form_id"] = {"$in": forms_id_list}
        else:
            match_query["form_id"] = self.unlist(forms_id_list)
    
        group_fields = {"_id": "$form_id"}
        fallas_dict_without_dots = self.limpia_keys_dict(self.fallas_dict)
        for nombre_falla, id_falla in fallas_dict_without_dots.items():
            group_fields[nombre_falla] = { # type: ignore
                "$sum": {
                    "$cond": [
                        {"$eq": [f"$answers.{id_falla}", "no"]},
                        1,
                        0
                    ]
                }
            }
    
        # Pipeline con año y cuatrimestre
        pipeline = [
            {"$match": match_query},
            {"$addFields": {
                "_anio": {"$year": "$created_at"},
                "_mes": {"$month": "$created_at"}
            }},
            {"$addFields": {
                "_cuatrimestre": {
                    "$ceil": {"$divide": ["$_mes", 4]}
                }
            }},
        ]
    
        # Filtro por año y cuatrimestre si se pasan como parámetro
        match_cuatrimestre = {}
        if anio is not None:
            match_cuatrimestre["_anio"] = anio
        if cuatrimestres:
            match_cuatrimestre["_cuatrimestre"] = {"$in": cuatrimestres}
        if match_cuatrimestre:
            pipeline.append({"$match": match_cuatrimestre})
    
        pipeline.append({"$group": group_fields})
    
        result_por_hotel = self.format_cr(self.cr.aggregate(pipeline))
        result_totales = deepcopy(result_por_hotel)
        form_id_to_hotel = {str(v): k for k, v in self.form_ids.items()}
        for item in result_por_hotel:
            item["hotel"] = form_id_to_hotel.get(str(item["_id"]), item["_id"])
            del item["_id"]
    
        totales = Counter()
        for item in result_totales:
            for k, v in item.items():
                if k != "_id":
                    totales[k] += v

        totales_list = [{"falla": k, "total": v} for k, v in totales.items()]
        totales_list.sort(key=lambda x: x["total"], reverse=True)

        return {
            "por_hotel": result_por_hotel,
            "totales": totales_list
        }

    def get_habitaciones_by_hotel(self, hotel_name, fallas=None):
        hotel_name_list = [hotel_name.lower().replace(' ', '_')]
        form_id = self.get_forms_id_list(hotel_name_list)
        form_id = self.unlist(form_id)

        if hotel_name in self.hotel_name_abreviatura:
            hotel_name = self.hotel_name_abreviatura[hotel_name]

        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.Location.AREAS_DE_LAS_UBICACIONES,
                f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_nombre']}": hotel_name,
                f"answers.{self.Location.TIPO_AREA_OBJ_ID}.{self.f['tipo_area_habitacion']}": "Habitación",
            }},
            {'$project': {
                '_id': 0,
                'nombre_area_habitacion': f"$answers.{self.f['nombre_area_habitacion']}",
                'numero_habitacion': f"$answers.{self.f['numero_habitacion']}",
            }},
            {
            '$lookup': {
                'from': 'form_answer',
                'let': {
                    'nombre_hab': '$nombre_area_habitacion'
                },
                'pipeline': [
                    {
                        '$match': {
                            '$expr': {
                                '$and': [
                                {'$eq': ['$form_id', form_id]},
                                {'$eq': [f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area_habitacion']}", "$$nombre_hab"]}
                                ]
                            }
                        }
                    },
                    {
                        '$sort': {'created_at': -1}
                    },
                    {
                        '$limit': 1
                    },
                    {
                        '$project': {
                            '_id': 1
                        }
                    }
                ],
                'as': 'inspeccion'
            }
            },
            {
            '$addFields': {
                'inspeccion_id': {
                    '$cond': [
                        {'$gt': [{'$size': '$inspeccion'}, 0]},
                        {'$arrayElemAt': ['$inspeccion._id', 0]},
                        None
                    ]
                }
            }
            },
            {
                '$project': {
                    'nombre_area_habitacion': 1,
                    'numero_habitacion': 1,
                    'inspeccion_id': 1
                }
            }
        ]

        habitaciones = list(self.cr.aggregate(query))
        habitaciones_id = [hab.get('inspeccion_id') for hab in habitaciones if hab.get('inspeccion_id')]
        if habitaciones_id:
            query = {"_id": {"$in": habitaciones_id}}
            res = self.cr_inspeccion.find(query)
            inspecciones = list(res)
            inspecciones_dict = {x['_id']: x for x in inspecciones}
        else:
            inspecciones_dict = {}
        for hab in habitaciones:
            inspeccion_id = hab.get('inspeccion_id')
            if inspecciones_dict.get(inspeccion_id):
                hab['inspeccion_habitacion'] = inspecciones_dict[inspeccion_id]
            else:
                hab['inspeccion_habitacion'] = None

        habitaciones = self.normalize_types(habitaciones)
        if fallas:
            fallas_normalizadas = set(self.normaliza_texto(f) for f in fallas)
            for hab in habitaciones:
                inspeccion_habitacion = hab.get('inspeccion_habitacion') # type: ignore
                if inspeccion_habitacion and inspeccion_habitacion.get('fallas') == 0:  # type: ignore
                    hab['inspeccion_habitacion'] = None # type: ignore
                    hab['sin_fallas'] = True # type: ignore
                else:
                    inspeccion = hab.get('inspeccion_habitacion') # type: ignore
                    if inspeccion and 'field_label' in inspeccion:
                        labels = inspeccion['field_label'].values() # type: ignore
                        labels_normalizadas = set(self.normaliza_texto(l) for l in labels)
                        if not any(falla in labels_normalizadas for falla in fallas_normalizadas):
                            hab['inspeccion_habitacion'] = None # type: ignore
        else:
            #TODO Mejorar este proceso, se repite el mismo proceso que arriba solo que lo hace cuando no hay fallas
            for hab in habitaciones:
                inspeccion_habitacion = hab.get('inspeccion_habitacion') # type: ignore
                if inspeccion_habitacion and inspeccion_habitacion.get('fallas') == 0:  # type: ignore
                    hab['inspeccion_habitacion'] = None # type: ignore
                    hab['sin_fallas'] = True # type: ignore
                else:
                    hab['inspeccion_habitacion'] = None # type: ignore

        return {
            'habitaciones': habitaciones,
        }
    
    def get_room_data(self, hotel_name, room_id):
        hotel_name_list = [hotel_name.lower().replace(' ', '_')]
        form_id = self.get_forms_id_list(hotel_name_list)
        form_id = self.unlist(form_id)

        query = [
            {
                '$match': {
                    "deleted_at": {"$exists": False},
                    "form_id": form_id,
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area_habitacion']}": room_id,
                }
            },
            {
              '$sort': {
                   'created_at': -1
                }
            },
            {
                '$limit': 1
            },
            {
                '$project': {
                    '_id': 1,
                    'habitacion': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area_habitacion']}",
                    'habitacion_remodelada': f"$answers.{self.f['habitacion_remodelada']}",
                    'nombre_camarista': f"$answers.{self.f['nombre_camarista']}",
                    'created_by_name': "$created_by_name",
                    'created_at': "$created_at",
                    'updated_at': "$updated_at",
                }
            },
            {
                '$lookup': {
                    'from': 'inspeccion_hoteleria',
                    'localField': '_id',
                    'foreignField': '_id',
                    'as': 'inspeccion'
                }
            },
            {'$project': {
                    '_id': 1,
                    'habitacion': '$habitacion',
                    'habitacion_remodelada': '$habitacion_remodelada',
                    'nombre_camarista': '$nombre_camarista',
                    'created_by_name': '$created_by_name',
                    'created_at': '$created_at',
                    'updated_at': '$updated_at',
                    'inspeccion': {'$first': '$inspeccion'}
                }
            },
        ]
        result = self.cr.aggregate(query)
        x = {}
        for x in result:
            x['_id'] = str(x['_id'])
            x['inspeccion'].pop('_id', None)
            x['created_at'] = self.get_date_str(x['created_at'])
            x['updated_at'] = self.get_date_str(x['updated_at'])
            if x['inspeccion'].get('created_at'):
                x['inspeccion'].pop('created_at', None)
        if not x:
            return {"mensaje": "No hay inspección para esta habitación"}
        return x

    def get_table_habitaciones_inspeccionadas(self, forms_id_list=[]):
        match_query = {
            "deleted_at": {"$exists": False},
        }

        if len(forms_id_list) > 1:
            match_query["form_id"] = {"$in": forms_id_list}
        else:
            match_query["form_id"] = self.unlist(forms_id_list)

        query = [
            {'$match': match_query},
            {'$project': {
                '_id': 1,
                'habitacion': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area_habitacion']}",
                'hotel': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_nombre']}",
                'nombre_camarista': f"$answers.{self.f['nombre_camarista']}",
                'created_at': '$created_at',
            }},
            {
                '$lookup': {
                    'from': 'inspeccion_hoteleria',
                    'localField': '_id',
                    'foreignField': '_id',
                    'as': 'inspeccion'
                }
            },
            {
                '$unwind': {
                    'path': '$inspeccion',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$addFields': {
                    'inspeccion': '$inspeccion'
                }
            }
        ]
        result = self.cr.aggregate(query)

        output = []
        for doc in result:
            inspeccion = doc.get('inspeccion', {})
            created_at = doc.get('created_at')
            if isinstance(created_at, datetime.datetime):
                fecha_str = created_at.strftime('%d/%m/%Y')
            else:
                fecha_str = ""

            if inspeccion:
                output.append({
                    'habitacion': doc.get('habitacion'),
                    'hotel': doc.get('hotel'),
                    'nombre_camarista': doc.get('nombre_camarista'),
                    'grade': inspeccion.get('grade'),
                    'total_aciertos': inspeccion.get('aciertos'),
                    'total_fallas': inspeccion.get('fallas'),
                    'created_at': fecha_str
                })

        return output
    
    def get_mejor_y_peor_habitacion(self, forms_id_list=[], anio=None, cuatrimestres=None):
        match_query = {
            "deleted_at": {"$exists": False},
        }
    
        if len(forms_id_list) > 1:
            match_query["form_id"] = {"$in": forms_id_list}
        else:
            match_query["form_id"] = self.unlist(forms_id_list)
    
        pipeline = [
            {'$match': match_query},
            {'$addFields': {
                "_anio": {"$year": "$created_at"},
                "_mes": {"$month": "$created_at"}
            }},
            {'$addFields': {
                "_cuatrimestre": {
                    "$ceil": {"$divide": ["$_mes", 4]}
                }
            }},
        ]
    
        # Filtro por año y cuatrimestre si se pasan como parámetro
        match_cuatrimestre = {}
        if anio is not None:
            match_cuatrimestre["_anio"] = anio
        if cuatrimestres:
            match_cuatrimestre["_cuatrimestre"] = {"$in": cuatrimestres}
        if match_cuatrimestre:
            pipeline.append({"$match": match_cuatrimestre})
    
        pipeline += [
            {'$project': {
                    '_id': 1,
                    'habitacion': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area_habitacion']}",
                    'hotel': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_nombre']}",
                }
            },
            {
                '$lookup': {
                    'from': 'inspeccion_hoteleria',
                    'localField': '_id',
                    'foreignField': '_id',
                    'as': 'inspeccion'
                }
            },
            {
                '$unwind': {
                    'path': '$inspeccion',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$addFields': {
                    'max_points': '$inspeccion.max_points',
                    'obtained_points': '$inspeccion.obtained_points',
                    'grade': '$inspeccion.grade',
                    'fallas': '$inspeccion.fallas',
                    'aciertos': '$inspeccion.aciertos',
                }
            },
            {
                '$group': {
                    '_id': {
                        'habitacion': '$habitacion',
                        'hotel': '$hotel'
                    },
                    'grades': {'$push': '$grade'},
                    'fallas': {'$push': '$fallas'},
                    'max_points': {'$push': '$max_points'},
                    'obtained_points': {'$push': '$obtained_points'},
                    'aciertos': {'$push': '$aciertos'},
                    'total_inspecciones': {'$sum': 1},
                }
            }
        ]
    
        result = list(self.cr.aggregate(pipeline))

        inspecciones_validas = [i for i in result if i.get('fallas') and len(i['fallas']) > 0]

        if not inspecciones_validas:
            mejor = peor = None
        else:
            # Mejor: la de menor cantidad de fallas
            mejor = min(inspecciones_validas, key=lambda x: min(x['fallas']))
            # Peor: la de mayor cantidad de fallas
            peor = max(inspecciones_validas, key=lambda x: max(x['fallas']))
    
        return {
            'mejor_habitacion': mejor,
            'habitacion_mas_fallas': peor
        }
    
    def get_graph_radar(self, forms_id_list=None, anio=None, cuatrimestres=None):
        query = {"form_id": {"$in": forms_id_list}}
        projection = {"_id": 1, "sections": 1, "created_at": 1}
        res = list(self.cr_inspeccion.find(query, projection))
        list_of_ids = [r['_id'] for r in res]
    
        match_query = {
            "deleted_at": {"$exists": False},
            "_id": {"$in": list_of_ids}
        }
    
        if len(forms_id_list) > 1: # type: ignore
            match_query.update({
                "form_id": {"$in": forms_id_list}, # type: ignore
            }) # type: ignore
        else:
            match_query.update({
                "form_id": self.unlist(forms_id_list),
            })
    
        pipeline = [
            {'$match': match_query},
            {'$addFields': {
                "_anio": {"$year": "$created_at"},
                "_mes": {"$month": "$created_at"}
            }},
            {'$addFields': {
                "_cuatrimestre": {
                    "$ceil": {"$divide": ["$_mes", 4]}
                }
            }},
        ]
    
        # Filtro por año y cuatrimestre si se pasan como parámetro
        match_cuatrimestre = {}
        if anio is not None:
            match_cuatrimestre["_anio"] = anio
        if cuatrimestres:
            match_cuatrimestre["_cuatrimestre"] = {"$in": cuatrimestres}
        if match_cuatrimestre:
            pipeline.append({"$match": match_cuatrimestre})
    
        pipeline.append({'$project': {
            '_id': 1,
            'hotel': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_nombre']}",
        }})
    
        result = self.format_cr(self.cr.aggregate(pipeline))
    
        hotel_by_id = {str(item['_id']): item['hotel'] for item in result}
        for r in res:
            r['_id'] = str(r['_id'])
            r_id = r['_id']
            r['hotel'] = hotel_by_id.get(r_id, None)
    
        return {
            'radar_data': res
        }

    def get_fotografias(self, forms_id_list=None):
        query = {}
        projection = {"_id": 1, "media": 1, "field_label": 1}
        res = list(self.cr_inspeccion.find(query, projection))
        list_of_ids = [r['_id'] for r in res]

        match_query = {
            "deleted_at": {"$exists": False},
            "_id": {"$in": list_of_ids}
        }

        if len(forms_id_list) > 1: # type: ignore
            match_query.update({
                "form_id": {"$in": forms_id_list}, # type: ignore
            }) # type: ignore
        else:
            match_query.update({
                "form_id": self.unlist(forms_id_list),
            })

        query = [
            {'$match': match_query},
            {'$project': {
                '_id': 1,
                'hotel': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_nombre']}",
                'habitacion': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area_habitacion']}",
            }},
        ]

        result = self.format_cr(self.cr.aggregate(query))

        # Mapea _id a hotel y habitacion
        info_by_id = {
            str(item['_id']): {
                'hotel': item.get('hotel'),
                'habitacion': item.get('habitacion')
            }
            for item in result
        }

        for r in res:
            r['_id'] = str(r['_id'])
            info = info_by_id.get(r['_id'], {})
            r['hotel'] = info.get('hotel')
            r['habitacion'] = info.get('habitacion')

            # Formatea media: agrega file_url y la falla relacionada
            media = r.get('media', {})
            field_label = r.get('field_label', {})
            new_media = {}
            for key, files in media.items():
                falla = field_label.get(key, None)
                new_media[key] = [
                    {'file_url': f['file_url'], 'falla': falla}
                    for f in files if 'file_url' in f
                ]
            r['media'] = new_media

        return {
            'hoteles_fotografias': res
        }
    
    def get_comentarios(self, forms_id_list=None):
        query = {}
        res = list(self.cr_inspeccion.find(query))
        list_of_ids = [r['_id'] for r in res]

        match_query = {
            "deleted_at": {"$exists": False},
            "_id": {"$in": list_of_ids}
        }

        if len(forms_id_list) > 1: # type: ignore
            match_query.update({
                "form_id": {"$in": forms_id_list}, # type: ignore
            }) # type: ignore
        else:
            match_query.update({
                "form_id": self.unlist(forms_id_list),
            })

        query = [
            {'$match': match_query},
            {'$project': {
                '_id': 1,
                'hotel': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_nombre']}",
                'habitacion': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area_habitacion']}",
            }},
        ]

        result = self.format_cr(self.cr.aggregate(query))

        hotel_by_id = {str(item['_id']): item['hotel'] for item in result}
        info_by_id = {
            str(item['_id']): {
                'hotel': item.get('hotel'),
                'habitacion': item.get('habitacion')
            }
            for item in result
        }
        for r in res:
            r['_id'] = str(r['_id'])
            info = info_by_id.get(r['_id'], {})
            r['hotel'] = info.get('hotel')
            r['habitacion'] = info.get('habitacion')
            r.pop('created_at', None)  # Elimina created_at si existe
            # Formatea media: solo deja el id y los file_url
            media = r.get('media', {})
            new_media = {}
            for key, files in media.items():
                # Solo file_url en cada diccionario
                new_media[key] = [{'file_url': f['file_url']} for f in files if 'file_url' in f]
            r['media'] = new_media

        return {
            'hoteles_comentarios': res
        }

    def get_cards(self, forms_id_list=[], anio=None, cuatrimestres=None):
        match_query = {
            "deleted_at": {"$exists": False},
        }
    
        if len(forms_id_list) > 1:
            match_query.update({
                "form_id": {"$in": forms_id_list},
            })
        else:
            match_query.update({
                "form_id": self.unlist(forms_id_list),
            })
    
        # Pipeline para agregar año y cuatrimestre
        query = [
            {'$match': match_query},
            {'$addFields': {
                "_anio": {"$year": "$created_at"},
                "_mes": {"$month": "$created_at"}
            }},
            {'$addFields': {
                "_cuatrimestre": {
                    "$ceil": {"$divide": ["$_mes", 4]}
                }
            }},
        ]
    
        # Filtro por año y cuatrimestre si se pasan como parámetro
        match_cuatrimestre = {}
        if anio is not None:
            match_cuatrimestre["_anio"] = anio
        if cuatrimestres:
            match_cuatrimestre["_cuatrimestre"] = {"$in": cuatrimestres}
        if match_cuatrimestre:
            query.append({"$match": match_cuatrimestre})
    
        query += [
            {'$project': {
                '_id': 1,
                'habitacion_remodelada': f"$answers.{self.f['habitacion_remodelada']}",
                'habitacion': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area_habitacion']}",
            }},
            {
            '$lookup': {
                'from': 'inspeccion_hoteleria',
                'localField': '_id',
                'foreignField': '_id',
                'as': 'inspeccion'
            }
            },
            {
            '$unwind': {
                'path': '$inspeccion',
                'preserveNullAndEmptyArrays': True
            }
            },
            {
            '$group': {
                '_id': '$_id',
                'habitacion': {'$first': '$habitacion'},
                'remodelada': {
                '$max': {
                    '$cond': [
                    {'$eq': ['$habitacion_remodelada', 'sí']},
                    1,
                    0
                    ]
                }
                },
                'fallas': {'$max': '$inspeccion.fallas'},
                'aciertos': {'$max': '$inspeccion.aciertos'},
                'grade_max': {'$max': '$inspeccion.grade'},
                'grade_min': {'$min': '$inspeccion.grade'},
                'grade_avg': {'$avg': '$inspeccion.grade'}
            }
            },
            {
            '$group': {
                '_id': None,
                'habitaciones_remodeladas': {'$sum': '$remodelada'},
                'inspecciones_realizadas': {'$sum': 1},
                'total_fallas': {'$sum': '$fallas'},
                'total_aciertos': {'$sum': '$aciertos'},
                'grade_max': {'$max': '$grade_max'},
                'grade_min': {'$min': '$grade_min'},
                'grade_avg': {'$avg': '$grade_avg'}
            }
            },
            {
            '$project': {
                '_id': 0,
                'habitaciones_remodeladas': 1,
                'inspecciones_realizadas': 1,
                'total_fallas': 1,
                'total_aciertos': 1,
                'grade_max': 1,
                'grade_min': 1,
                'grade_avg': {'$round': ['$grade_avg', 2]}
            }
            }
        ]
        result = self.cr.aggregate(query)
        result = list(result)
        
        return result
    
    def get_report(self, anio=None, cuatrimestres=None, hoteles=[]):
        # Normaliza los nombres de hoteles usando las abreviaturas si corresponde
        if hoteles:
            hoteles_actualizados = []
            for hotel in hoteles:
                encontrado = False
                hotel_norm = hotel.lower().replace(' ', '_')
                for k, v in self.hotel_name_abreviatura.items():
                    v_norm = v.lower().replace(' ', '_')
                    k_norm = k.lower().replace(' ', '_')
                    if v_norm == hotel_norm:
                        hoteles_actualizados.append(k_norm)
                        encontrado = True
                        break
                if not encontrado:
                    hoteles_actualizados.append(hotel_norm)
            hoteles = hoteles_actualizados

        forms_id_list = self.get_forms_id_list(hoteles)
        self.get_labels(forms_id_list=forms_id_list)

        total_habitaciones = self.get_cantidad_habitaciones(ubicaciones_list=hoteles)

        total_inspecciones_y_remodeladas = self.get_cantidad_inspecciones_y_remodeladas(forms_id_list=forms_id_list, anio=anio, cuatrimestres=cuatrimestres)

        propiedades_inspeccionadas = self.porcentaje_propiedades_inspeccionadas(
           total_habitaciones.get('totalHabitaciones', 0) if total_habitaciones else 0,
           total_inspecciones_y_remodeladas.get('total_inspecciones_completadas', 0) if total_inspecciones_y_remodeladas else 0
        )
        
        calificacion_x_hotel_grafica = self.get_cuatrimestres_by_hotel(hoteles=hoteles, anio=anio, cuatrimestres=[1, 2, 3])

        fallas = self.get_fallas(forms_id_list=forms_id_list, anio=anio, cuatrimestres=cuatrimestres)
        
        habitaciones_inspeccionadas = self.get_table_habitaciones_inspeccionadas(forms_id_list=forms_id_list)

        mejor_y_peor_habitacion = self.get_mejor_y_peor_habitacion(forms_id_list=forms_id_list, anio=anio, cuatrimestres=cuatrimestres)

        graph_radar = self.get_graph_radar(forms_id_list=forms_id_list, anio=anio, cuatrimestres=cuatrimestres)

        hoteles_fotografias = self.get_fotografias(forms_id_list=forms_id_list)

        hoteles_comentarios = self.get_comentarios(forms_id_list=forms_id_list)
        
        rooms_details = self.get_rooms_details(forms_id_list=forms_id_list, anio=anio, cuatrimestres=cuatrimestres)

        cards = self.get_cards(forms_id_list=forms_id_list, anio=anio, cuatrimestres=cuatrimestres)
        cards = self.unlist(cards)

        report_data = {
            'cards': cards,
            'porcentaje_propiedades_inspeccionadas': propiedades_inspeccionadas,
            'calificacion_x_hotel_grafica': calificacion_x_hotel_grafica,
            'fallas': fallas,
            'table_habitaciones_inspeccionadas': habitaciones_inspeccionadas,
            'mejor_y_peor_habitacion': mejor_y_peor_habitacion,
            'graph_radar': graph_radar,
            'hoteles_fotografias': hoteles_fotografias,
            'hoteles_comentarios': hoteles_comentarios,
            'rooms_details': rooms_details,
        }

        return report_data

    def get_pdf(self, record_id, template_id=131835, name_pdf='Inspeccion de Habitacion'):
        return self.lkf_api.get_pdf_record(record_id, template_id=template_id, name_pdf=name_pdf, send_url=True)
    
    def get_labels(self, forms_id_list=[]):
        form_id = [self.REVISON_HABITACION] # * Toma el id de la forma maestro para no demorar tanto
        form_data = self.lkf_api.get_form_for_answer(self.REVISON_HABITACION)
        fields = form_data[0].get('fields', [])
        for field in fields:
            if not field.get('catalog'):
                if not field.get('label') in self.labels_to_exclude and not field.get('field_id') in self.ids_to_exclude:
                    self.fallas_dict.update({
                        self.normaliza_texto(field.get('label')): field.get('field_id')
                    })
                        
    def get_rooms_details(self, forms_id_list=None, anio=None, cuatrimestres=None):
        query = {"form_id": {"$in": forms_id_list}}
        res = list(self.cr_inspeccion.find(query))
        list_of_ids = [r['_id'] for r in res]

        match_query = {
            "deleted_at": {"$exists": False},
            "_id": {"$in": list_of_ids}
        }

        if len(forms_id_list) > 1: # type: ignore
            match_query.update({
                "form_id": {"$in": forms_id_list}, # type: ignore
            }) # type: ignore
        else:
            match_query.update({
                "form_id": self.unlist(forms_id_list),
            })

        pipeline = [
            {'$match': match_query},
            {'$addFields': {
                "_anio": {"$year": "$created_at"},
                "_mes": {"$month": "$created_at"}
            }},
            {'$addFields': {
                "_cuatrimestre": {
                    "$ceil": {"$divide": ["$_mes", 4]}
                }
            }},
        ]

        match_cuatrimestre = {}
        if anio is not None:
            match_cuatrimestre["_anio"] = anio
        if cuatrimestres:
            match_cuatrimestre["_cuatrimestre"] = {"$in": cuatrimestres}
        if match_cuatrimestre:
            pipeline.append({"$match": match_cuatrimestre})

        pipeline.append({
            '$project': {
                '_id': 1,
                'hotel': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_nombre']}",
                'habitacion': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area_habitacion']}",
            }
        })

        result = self.format_cr(self.cr.aggregate(pipeline))

        info_by_id = {
            str(item['_id']): {
                'hotel': item.get('hotel'),
                'habitacion': item.get('habitacion')
            }
            for item in result
        }

        filtered_ids = set(info_by_id.keys())
        filtered_res = [r for r in res if str(r['_id']) in filtered_ids]

        for r in filtered_res:
            r['_id'] = str(r['_id'])
            info = info_by_id.get(r['_id'], {})
            r['hotel'] = info.get('hotel')
            r['habitacion'] = info.get('habitacion')
            r.pop('created_at', None)
            media = r.get('media', {})
            new_media = {}
            for key, files in media.items():
                new_media[key] = [{'file_url': f['file_url']} for f in files if 'file_url' in f]
            r['media'] = new_media

        return filtered_res

if __name__ == '__main__':
    module_obj = Inspeccion_Hoteleria(settings, sys_argv=sys.argv, use_api=False)
    module_obj.console_run()
    data = module_obj.data.get('data', {})
    option = data.get('option', 'get_report')
    anio = data.get('anio', None)
    cuatrimestres = data.get('cuatrimestres', None)
    hoteles = data.get('hoteles', [])
    hotel_name = data.get('hotel_name', 'CROWNE PLAZA MTY')
    room_id = data.get('room_id', 'Habitación 326')
    fallas = data.get('fallas', ['plafon_fuera_de_la_habitacion'])
    record_id = data.get('record_id', None)
    if option == 'get_hoteles':
        response = module_obj.get_hoteles()
    elif option == 'get_report':
        response = module_obj.get_report(anio=anio, cuatrimestres=cuatrimestres, hoteles=hoteles)
    elif option == 'get_habitaciones_by_hotel':
        response = module_obj.get_habitaciones_by_hotel(hotel_name=hotel_name, fallas=fallas)
    elif option == 'get_room_data':
        response = module_obj.get_room_data(hotel_name=hotel_name, room_id=room_id)
    elif option == 'get_room_pdf':
        response = module_obj.get_pdf(record_id=record_id)

    # print('response=', response)
    if data.get('test'):
        print('end')
    else:
        print(simplejson.dumps(response, indent=3))
        module_obj.HttpResponse({"data": response})