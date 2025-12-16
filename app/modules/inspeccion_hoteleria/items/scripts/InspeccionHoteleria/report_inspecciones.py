# -*- coding: utf-8 -*-
import sys, simplejson
from bson import ObjectId
import unicodedata

from linkaform_api import settings, base
from account_settings import *

from inspeccion_hoteleria_utils import Inspeccion_Hoteleria

class Inspeccion_Hoteleria(Inspeccion_Hoteleria):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        
        self.f.update({
            'state_name': '67b60b3f323c68b77070858f',
            'nes': '67b60531f2e5f0e87a807dbd',
            'supervisor_operativo': '67e2e232e85c5b95bf07a0b5',
            'gerente_operativo': '67e3ef85581f43e3b1a4b433',
            'zona': '67b60c8bdb7546044f29df19',
            'acciones_correctivas_set': '67bf64dca1d02113db11f200'
        })
        
        self.fallas_dict = {}
        
        self.ids_to_exclude = [
            '67bf5526231da356ca0b9c7d',
            '67da0a90bfe1a6b20e54c082',
            '67c08b9b59b0a1f41211f211',
            '67bf555bb985bd6a067f2aa5',
            '67bf64dca1d02113db11f200',
            '67c777dcb657dfe3608ed9a5',
            '67bf652522bcb70fd30b9c9d',
            '67bf652522bcb70fd30b9c9e',
            '67bf652522bcb70fd30b9c9f',
            '67c6001647ad36ab810b9deb',
            '67c1e6b3f081c66b134fa579',
            '67c1e6b3f081c66b134fa57a',
            '67c089c31b269be81867d62c',
            '67d1b65ca1cd07065ddcb404',
            '67d1b65ca1cd07065ddcb405',
            '67c089c31b269be81867d62d',
            '67c089c31b269be81867d62e',
        ]

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

    def format_fallas(self, list_fallas):
        """
        Formatea la lista de fallas con estructura: id, label, total
        """
        import re
        
        formatted_fallas = []
        
        for falla_key, count in list_fallas.items():
            if falla_key and falla_key.strip():  # Evitar claves vacías
                # Obtener el field_id del diccionario fallas_dict ANTES de formatear
                field_id = self.fallas_dict.get(falla_key, falla_key)  # Si no encuentra, usa la key como fallback
                
                # Formatear el label
                texto = re.sub(r'(\d)_', r'\1. ', falla_key, count=1)
                texto = texto.replace('_', ' ')
                texto = ' '.join(word.capitalize() for word in texto.split() if word)
                
                formatted_fallas.append({
                    'id': field_id,         # field_id original del diccionario
                    'label': texto,         # Label formateado
                    'total': count          # Cantidad
                })
        
        return formatted_fallas
    
    def normalize_label(self, label):
        if not label:
            return ''
        if isinstance(label, list):
            return str(label[0] if label else '').strip()
        return str(label).strip()

    def get_states(self):
        """
        Devuelve el catalogo de estados.
        Params:
            None
        Returns:
            list: Lista de estados con su nombre.
            Ejemplo: [{'name': 'Estado1'}, {'name': 'Estado2'}, ...
        """
        selector = {}
        fields = ["_id", f"answers.{self.f['state_name']}"]

        mango_query = {
            "selector": selector,
            "fields": fields,
            "limit": 3000,
        }

        res = self.lkf_api.search_catalog(129505, mango_query)
        if res:
            seen = set()
            format_res = []
            for r in res:
                state_name = r.get(self.f['state_name'], '')
                if state_name and state_name not in seen:
                    format_res.append({
                        'id': r['_id'],
                        'name': state_name
                    })
                    seen.add(state_name)
            res = format_res
        return res
    
    def get_nes(self, states=None):
        selector = {}
        
        if states:
            selector.update({
                f"answers.{self.f['state_name']}": {"$in": states},
            })
            
        fields = ["_id", f"answers.{self.f['nes']}", f"answers.{self.f['state_name']}"]
        
        mango_query = {
            "selector": selector,
            "fields": fields,
            "limit": 3000,
        }
        res = self.lkf_api.search_catalog(129504, mango_query)
        
        formated_res = []
        if res:
            for r in res:
                nes = r.get(self.f['nes'])
                state = r.get(self.f['state_name'])
                formated_res.append({
                    'id': r['_id'],
                    'nes': self.unlist(nes),
                    'state': self.unlist(state)
                })
        return formated_res

    def get_auditorias(self, states=[], fallas_list=[]):
        all_nes = self.get_nes(states)
        
        match = {
            "form_id": 129506,
            "deleted_at": {"$exists": False},
        }
        
        if states:
            match.update({
                f"answers.67b60531f2e5f0e87a807dbc.{self.f['state_name']}": {"$in": states}
            })
        
        query = [
            {"$match": match},
            {"$project": {
                '_id': 1,
                'created_at': 1,
                'state': f"$answers.67b60531f2e5f0e87a807dbc.{self.f['state_name']}",
                'label': f"$answers.67b60531f2e5f0e87a807dbc.{self.f['nes']}",
            }},
            {"$lookup": {
                "from": "inspeccion_collection",
                "let": {
                    "record_id": "$_id",
                },
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$eq": ["$_id", {"$toObjectId": "$$record_id"}]
                        }
                    }},
                    {"$project": {
                        "_id": 0,
                        "folio": 1,
                        "fallas": 1,
                        "field_label": 1,
                    }}
                ],
                "as": "audits"
            }},
            {"$project": {
                "_id": 1,
                "created_at": 1,
                "state": 1,
                "label": 1,
                "audits": "$audits",
                "has_audit": {"$gt": [{"$size": "$audits"}, 0]},
                "has_fallas": {
                    "$gt": [
                        {"$ifNull": [{"$arrayElemAt": ["$audits.fallas", 0]}, 0]},
                        0
                    ]
                },
            }},
            {"$sort": {
                "label": 1
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        nes_with_audits = set()
        final_response = []
        
        if response:
            for r in response:
                label = r.get('label', '')
                
                if not label or label == [] or (isinstance(label, list) and not any(label)):
                    continue
                    
                label_str = self.normalize_label(label)
                
                if not label_str:
                    continue
                    
                r['label'] = label_str
                
                if r.get('has_audit'):
                    if r.get('has_fallas'):
                        r['status'] = 'warning'
                    else:
                        r['status'] = 'done'
                else:
                    r['status'] = 'pending'
                
                nes_with_audits.add(label_str)
                final_response.append(r)
        
        for nes in all_nes:
            nes_label = self.normalize_label(nes['nes'])  # ← USAR FUNCIÓN AUXILIAR
            if nes_label and nes_label not in nes_with_audits:  # ← COMPARAR NORMALIZADO
                final_response.append({
                    '_id': nes['id'],
                    'created_at': None,
                    'state': nes['state'],
                    'label': nes_label,  # ← USAR NORMALIZADO
                    'status': 'pending',
                    'has_audit': False,
                    "audits": [],
                    'fallas': 0,
                    'has_fallas': False
                })
                
        if fallas_list:
            for r in final_response:
                if r.get('has_audit') and r.get('audits'):
                    audit = r['audits'][0] if r['audits'] else {}
                    audit_falla_ids = set()
                    
                    for key in audit.keys():
                        if key not in ['fallas', 'folio']:
                            audit_falla_ids.add(key)
                    
                    fallas_set = set(fallas_list)
                    has_target_falla = bool(audit_falla_ids.intersection(fallas_set))
                    
                    if not has_target_falla:
                        if r.get('has_fallas'):
                            r['status'] = 'info'
                        else:
                            r['status'] = 'pending'
                                                
        return final_response

    def get_auditoria_by_id(self, record_id):
        query = [
            {"$match": {
                "form_id": 129506,
                "_id": ObjectId(record_id),
            }},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "created_at": 1,
                "nes": f"$answers.67b60531f2e5f0e87a807dbc.{self.f['nes']}",
                "gerente": f"$answers.67b60531f2e5f0e87a807dbc.{self.f['gerente_operativo']}",
                "supervisor": f"$answers.67b60531f2e5f0e87a807dbc.{self.f['supervisor_operativo']}",
                "zona": f"$answers.67b60531f2e5f0e87a807dbc.{self.f['zona']}",
                "acciones_correctivas": {
                    "$size": {
                        "$ifNull": [f"$answers.{self.f['acciones_correctivas_set']}", []]
                    }
                },
            }},
            {"$sort": {"created_at": -1}},
            {"$limit": 1},
            {"$lookup": {
                "from": "inspeccion_collection",
                "let": {
                    "record_folio": "$folio",
                },
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$eq": ["$folio", "$$record_folio"]
                        }
                    }},
                    {"$project": {
                        "_id": 0,
                        "folio": 0,
                        "form_id": 0,
                    }}
                ],
                "as": "audit"
            }},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "created_at": 1,
                "nes": 1,
                "gerente_operativo": 1,
                "supervisor_operativo": 1,
                "zona": 1,
                "audit": 1,
                "acciones_correctivas": 1,
            }}
        ]
        
        response = self.cr.aggregate(query)
        response = list(response)
        response = self.unlist(response)
        response["_id"] = str(response["_id"])
        response['created_at'] = response['created_at'].strftime('%Y-%m-%d')
        return response

    def get_labels(self, form_id=None):
        form_data = self.lkf_api.get_form_for_answer(form_id)
        fields = form_data[0].get('fields', [])
        for field in fields:
            if not field.get('catalog'):
                if not field.get('field_type') == 'textarea':
                    if not field.get('field_type') == 'images':
                        if not field.get('field_id') in self.ids_to_exclude:
                            self.fallas_dict.update({
                                self.clean_text(field.get('label')): field.get('field_id')
                            })
        
    def get_list_fallas(self, states=None):
        match_query = {
            "deleted_at": {"$exists": False},
            "form_id": 129506,
        }
        
        if states:
            match_query.update({
                f"answers.67b60531f2e5f0e87a807dbc.{self.f['state_name']}": {"$in": states}
            })

        group_fields = {"_id": "$form_id"}
        for nombre_falla, id_falla in self.fallas_dict.items():
            group_fields[nombre_falla] = { #type: ignore
                "$sum": {
                    "$cond": [
                        {
                            "$or": [
                                {"$eq": [f"$answers.{id_falla}", "no_cumple"]},
                                {"$eq": [f"$answers.{id_falla}", "no_cumple_pero_muestra_seguimiento"]}
                            ]
                        },
                        1,
                        0
                    ]
                }
            }
    
        pipeline = [
            {"$match": match_query},
        ]

        pipeline.append({"$group": group_fields})
    
        response = self.cr.aggregate(pipeline)
        response = list(response)
        if response:
            response = self.unlist(response)
            response.pop('_id', None)
            response.pop('', None)
            format_fallas = self.format_fallas(response)
            return format_fallas
        return []

    def get_cards(self, states=None):
        all_nes = self.get_nes(states)

        match = {
            "form_id": 129506,
            "deleted_at": {"$exists": False},
        }
        
        if states:
            match.update({
                f"answers.67b60531f2e5f0e87a807dbc.{self.f['state_name']}": {"$in": states}
            })

        query = [
            {"$match": match},
            {"$project": {
                '_id': 1,
                'label': f"$answers.67b60531f2e5f0e87a807dbc.{self.f['nes']}"
            }},
            {"$lookup": {
                "from": "inspeccion_collection",
                "let": {
                    "record_id": "$_id",
                },
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$eq": ["$_id", {"$toObjectId": "$$record_id"}]
                        }
                    }},
                    {"$project": {
                        "_id": 0,
                        "fallas": 1,
                        "aciertos": 1,
                        "obtained_points": 1
                    }}
                ],
                "as": "audits"
            }},
            {"$project": {
                "_id": 0,
                "label": 1,
                "audits": "$audits",
            }},
        ]
        response = list(self.cr.aggregate(query))

        total_auditorias_registros = 0
        total_aciertos = 0
        total_fallas = 0
        calificaciones = []
        labels_con_auditoria = set()
        
        for record in response:
            audits = record.get('audits', [])
            if audits:
                audit = audits[0]
                total_auditorias_registros += 1
                
                aciertos = audit.get('aciertos', 0)
                fallas = audit.get('fallas', 0)
                obtained_points = audit.get('obtained_points', 0)
                
                total_aciertos += aciertos
                total_fallas += fallas
                calificaciones.append(obtained_points)
                
                label = record.get('label', [])
                if label:
                    label_str = str(label[0] if isinstance(label, list) else label).strip()
                    if label_str:
                        labels_con_auditoria.add(label_str)
        
        total_nes = len([nes for nes in all_nes if nes.get('nes')])
        nes_con_auditoria = len(labels_con_auditoria)
        inspecciones_pendientes = total_nes - nes_con_auditoria

        porcentaje_realizadas = (nes_con_auditoria / total_nes * 100) if total_nes > 0 else 0

        calificacion_maxima = max(calificaciones) if calificaciones else 0
        calificacion_minima = min(calificaciones) if calificaciones else 0
        calificacion_promedio = sum(calificaciones) / len(calificaciones) if calificaciones else 0
        
        return {
            'nes_con_auditoria': nes_con_auditoria,
            'total_auditorias': total_auditorias_registros,
            'inspecciones_pendientes': inspecciones_pendientes,
            'porcentaje_realizadas': round(porcentaje_realizadas, 2),
            'total_aciertos': total_aciertos,
            'total_fallas': total_fallas,
            'calificacion_maxima': round(calificacion_maxima, 2),
            'calificacion_minima': round(calificacion_minima, 2),
            'calificacion_promedio': round(calificacion_promedio, 2)
        }

    def get_table_section(self, states=None):
        match = {
            "form_id": 129506,
            "deleted_at": {"$exists": False},
        }
        
        if states:
            match.update({
                f"answers.67b60531f2e5f0e87a807dbc.{self.f['state_name']}": {"$in": states}
            })

        query = [
            {"$match": match},
            {"$project": {
                '_id': 1,
                'created_at': 1,
                'state': f"$answers.67b60531f2e5f0e87a807dbc.{self.f['state_name']}",
                'label': f"$answers.67b60531f2e5f0e87a807dbc.{self.f['nes']}"
            }},
            {"$lookup": {
                "from": "inspeccion_collection",
                "let": {
                    "record_id": "$_id",
                },
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$eq": ["$_id", {"$toObjectId": "$$record_id"}]
                        }
                    }},
                    {"$project": {
                        "_id": 0,
                        "form_id": 0,
                    }}
                ],
                "as": "audits"
            }},
            {"$project": {
                "_id": 1,
                "created_at": 1,
                "state": 1,
                "label": 1,
                "audits": "$audits",
            }},
        ]
        response = list(self.cr.aggregate(query))
        
        mejor_auditoria = None
        peor_auditoria = None
        mejor_puntaje = -1
        peor_puntaje = float('inf')
        
        auditorias_por_label = {}
        
        for record in response:
            audits = record.get('audits', [])
            if audits:
                audit = audits[0]
                obtained_points = audit.get('obtained_points', 0)
                
                label = record.get('label', [])
                label_str = str(label[0] if isinstance(label, list) else label) if label else ''
                
                if label_str:
                    auditorias_por_label[label_str] = auditorias_por_label.get(label_str, 0) + 1
                
                if obtained_points > mejor_puntaje:
                    mejor_puntaje = obtained_points
                    mejor_auditoria = {
                        'label': label_str,
                        'obtained_points': round(obtained_points, 2),
                        'fallas': audit.get('fallas', 0),
                        'aciertos': audit.get('aciertos', 0),
                        'cantidad_auditorias': 0
                    }
                
                if obtained_points < peor_puntaje:
                    peor_puntaje = obtained_points
                    peor_auditoria = {
                        'label': label_str,
                        'obtained_points': round(obtained_points, 2),
                        'fallas': audit.get('fallas', 0),
                        'aciertos': audit.get('aciertos', 0),
                        'cantidad_auditorias': 0
                    }
        
        if mejor_auditoria:
            mejor_auditoria['cantidad_auditorias'] = auditorias_por_label.get(mejor_auditoria['label'], 1)
        
        if peor_auditoria:
            peor_auditoria['cantidad_auditorias'] = auditorias_por_label.get(peor_auditoria['label'], 1)
        
        table_section = {
            'mejor_auditoria': mejor_auditoria,
            'peor_auditoria': peor_auditoria
        }
        
        for record in response:
            record['created_at'] = record['created_at'].strftime('%Y-%m-%d')
            record['_id'] = str(record['_id'])
            record['label'] = self.unlist(record['label'])
        
        return response, table_section

    def get_pdf(self, record_id, template_id=560, name_pdf='Auditoria'):
        return self.lkf_api.get_pdf_record(record_id, template_id=template_id, name_pdf=name_pdf, send_url=True)

    def get_pie_chart(self, states=None):
        match_query = {
            "deleted_at": {"$exists": False},
            "form_id": 129506,
        }
        
        if states:
            match_query.update({
                f"answers.67b60531f2e5f0e87a807dbc.{self.f['state_name']}": {"$in": states}
            })

        # CORREGIDO: Crear project_fields para incluir estado y todas las fallas
        project_fields = {
            "_id": 0,
            "state": f"$answers.67b60531f2e5f0e87a807dbc.{self.f['state_name']}",
        }
        
        # Agregar todos los campos de fallas al project
        for nombre_falla, id_falla in self.fallas_dict.items():
            project_fields[f"falla_{nombre_falla}"] = f"$answers.{id_falla}"

        # CORREGIDO: Agrupar por estado
        group_fields = {"_id": "$state"}  # ← Cambiar de form_id a estado
        
        for nombre_falla, id_falla in self.fallas_dict.items():
            group_fields[nombre_falla] = { #type: ignore
                "$sum": {
                    "$cond": [
                        {
                            "$or": [
                                {"$eq": [f"$falla_{nombre_falla}", "no_cumple"]},
                                {"$eq": [f"$falla_{nombre_falla}", "no_cumple_pero_muestra_seguimiento"]}
                            ]
                        },
                        1,
                        0
                    ]
                }
            }

        pipeline = [
            {"$match": match_query},
            {"$project": project_fields},  # ← Usar project_fields completo
            {"$group": group_fields}       # ← Agrupar por estado
        ]

        response = self.cr.aggregate(pipeline)
        response = list(response)
        
        # PROCESAR: Formatear respuesta por estado
        formatted_response = []
        for state_data in response:
            state_name = state_data.pop('_id', 'Sin Estado')
            state_data.pop('', None)  # Eliminar claves vacías
            
            format_fallas = self.format_fallas(state_data)
            
            formatted_response.append({
                'state': state_name,
                'fallas': format_fallas,
                'total_fallas': sum(falla['total'] for falla in format_fallas)
            })
        
        return formatted_response

if __name__ == "__main__":
    class_obj = Inspeccion_Hoteleria(settings, sys_argv=sys.argv, use_api=True)
    class_obj.console_run()
    data = class_obj.data.get('data', {})
    option = data.get('option', 'get_report')
    anio = data.get('anio', None)
    cuatrimestres = data.get('cuatrimestres', None)
    states = data.get('states', None)
    record_id = data.get('record_id', None)
    fallas_list = data.get('fallas_list', None)

    print('Inspeccion Hoteleria module loaded successfully.')

    if option == 'get_filters':
        states = class_obj.get_states()
        response = {
            'states': states
        }
    elif option == 'get_report':
        class_obj.get_labels(129506)
        cards = class_obj.get_cards(states=states)
        fallas = class_obj.get_list_fallas(states=states)
        table_section, mejor_peor_auditoria = class_obj.get_table_section(states=states)
        response = {
            'fallas': fallas,
            'cards': cards,
            'table_section': table_section,
            'mejor_peor_auditoria': mejor_peor_auditoria,
        }
    elif option == 'get_auditorias':
        auditorias = class_obj.get_auditorias(states=states, fallas_list=fallas_list)
        response = {
            'auditorias': auditorias
        }
    elif option == 'get_auditoria_by_id':
        auditoria = class_obj.get_auditoria_by_id(record_id=record_id)
        response = {
            'auditoria': auditoria,
        }
    elif option == 'get_pdf':
        pdf = class_obj.get_pdf(record_id=record_id)
        response = {
            'pdf': pdf,
        }
    elif option == 'get_pie_chart':
        class_obj.get_labels(129506)
        pie_chart = class_obj.get_pie_chart(states=states)
        response = {
            'pie_chart_data': pie_chart
        }
    
    sys.stdout.write(simplejson.dumps({
        'response': response
    }))