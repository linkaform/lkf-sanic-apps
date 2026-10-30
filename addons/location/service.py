# -*- coding: utf-8 -*-
'''
Licencia BSD
Copyright (c) 2024 Infosync / LinkaForm.
Todos los derechos reservados.

Se permite la redistribución y el uso en formas de código fuente y binario, con o sin modificaciones, siempre que se cumplan las siguientes condiciones:

1. Se debe conservar el aviso de copyright anterior, esta lista de condiciones y el siguiente descargo de responsabilidad en las redistribuciones del código fuente.
2. Se debe reproducir el aviso de copyright anterior, esta lista de condiciones y el siguiente descargo de responsabilidad en la documentación y/u otros materiales proporcionados con las distribuciones en formato binario.
3. Ni el nombre del Infosync ni los nombres de sus colaboradores pueden ser utilizados para respaldar o promocionar productos derivados de este software sin permiso específico previo por escrito.
'''
# Version migrada a Sanic de addons/location/app.py -- ver
# knowledge/patterns/legacy_script_migration.md (lkf-claude) para el playbook.
# Agrega el CRUD de "Ubicaciones" (Pantalla Explorador del front clave10) que
# antes solo tenia lectura (get_location_address).

import re

from bson import ObjectId

from linkaform_api import base
from lkf_addons.base.app import Base
from lkf_addons.tools.FacetSearchMixin import FacetSearchMixin


# Un area sin marca "Utilizar Area en:" cuenta para el uso si su tipo de area coincide.
# TODO: quitar cuando todas las cuentas tengan sus areas marcadas.
USO_TIPO_COMPAT = {
    'casetas': ('caseta', 'casetas'),
    }


class Location(FacetSearchMixin, Base):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.kwargs['MODULES'] = self.kwargs.get('MODULES',[])
        if self.__class__.__name__ not in kwargs:
            self.kwargs['MODULES'].append(self.__class__.__name__)

        #use self.lkm.catalog_id() to get catalog id
        # forms
        self.AREAS_DE_LAS_UBICACIONES = self.lkm.form_id('areas_de_las_ubicaciones', 'id')
        self.UBICACIONES = self.lkm.form_id('ubicaciones', 'id')
        # catalgos
        self.UBICACIONES_CAT = self.lkm.catalog_id('ubicaciones')
        self.UBICACIONES_CAT_ID = self.UBICACIONES_CAT.get('id')
        self.UBICACIONES_CAT_OBJ_ID = self.UBICACIONES_CAT.get('obj_id')

        self.AREAS_DE_LAS_UBICACIONES_CAT = self.lkm.catalog_id('areas_de_las_ubicaciones')
        self.AREAS_DE_LAS_UBICACIONES_CAT_ID = self.AREAS_DE_LAS_UBICACIONES_CAT.get('id')
        self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID = self.AREAS_DE_LAS_UBICACIONES_CAT.get('obj_id')

        self.AREAS_DE_LAS_UBICACIONES_SALIDA = self.lkm.catalog_id('areas_de_las_ubicaciones_salidas')
        self.AREAS_DE_LAS_UBICACIONES_SALIDA_ID = self.AREAS_DE_LAS_UBICACIONES_SALIDA.get('id')
        self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID = self.AREAS_DE_LAS_UBICACIONES_SALIDA.get('obj_id')

        self.TIPO_AREA = self.lkm.catalog_id('tipo_de_areas')
        self.TIPO_AREA_ID = self.TIPO_AREA.get('id')
        self.TIPO_AREA_OBJ_ID = self.TIPO_AREA.get('obj_id')

        # Empleados con acceso a una ubicacion (tab "Empleados" del detalle).
        self.CONF_AREA_EMPLEADOS = self.lkm.form_id('configuracion_areas_y_empleados', 'id')
        self.EMPLEADOS = self.lkm.form_id('empleados', 'id')
        self.EMPLEADOS_CAT_OBJ_ID = (self.lkm.catalog_id('empleados') or {}).get('obj_id') \
            or (self.lkm.catalog_id('employee') or {}).get('obj_id')

        self.f.update( {
            'location':'663e5c57f5b8a7ce8211ed0b',
            'location_id':'68101945f4996c72247baac4',
            'area':'663e5d44f5b8a7ce8211ed0f',
            'area_state':'663e5e4bf5b8a7ce8211ed14',
            'area_status':'663e5e4bf5b8a7ce8211ed15',
            'area_qr_code':'663e5e4bf5b8a7ce8211ed13',
            'new_city': '6654187fc85ce22aaf8bb070',
            'area_salida':'663fb45992f2c5afcfe97ca8',
            # Checkbox "Utilizar Area en:" (pases, incidencias, rondines, ...)
            'utilizar_area_en':'6a9756e4faa39a6f6edeeb82',
            'tipo_de_area':'663e5e68f5b8a7ce8211ed18',
        }
        )

    def get_location_address(self, location_name):
        location_address = {}
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.UBICACIONES,
            f"answers.{self.f['location']}":location_name
            }
        query = [
            {'$match': match_query },
            {'$project':
                {'_id': 1,
                    'folio': "$folio",
                    'location': f"$answers.{self.f['location']}",
                    'address_name': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_name']}",
                    'address': {'$first':f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address']}"},
                    'address2': {'$first':f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address2']}"},
                    'address_type': {'$first':f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_type']}"},
                    'address_geolocation': {'$first':f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_geolocation']}"},
                    'state': {'$first':f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['state']}"},
                    'city': {'$first':f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['city']}"},
                    'zip_code': {'$first':f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['zip_code']}"},
                    'country': {'$first':f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['country']}"},
                    'phone': {'$first':f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['phone']}"},
                    'email': {'$first':f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['email']}"},
                    }
            }
            ]
        res = self.cr.aggregate(query)
        for x in res:
            location_address = x
        return location_address

    def get_area_address(self, location_name, area_name):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.AREAS_DE_LAS_UBICACIONES,
            f"answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}":location_name,
            f"answers.{self.f['area']}":area_name
            }
        query = [
            {'$match': match_query },
            {'$project':
                {'_id': 1,
                    'folio': "$folio",
                    'area': f"$answers.{self.f['area']}",
                    'location': f"$answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}",
                    'address_name': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_name']}",
                    'address': {'$cond': [
                        {'$isArray': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address']}"},
                        {'$first':  f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address']}"},
                        f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address']}"
                    ]},
                    'address2': {'$cond': [
                        {'$isArray': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address2']}"},
                        {'$first':  f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address2']}"},
                        f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address2']}"
                    ]},
                    'address_type': {'$cond': [
                        {'$isArray': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_type']}"},
                        {'$first':  f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_type']}"},
                        f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_type']}"
                    ]},
                    'address_geolocation': {'$cond': [
                        {'$isArray': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_geolocation']}"},
                        {'$first':  f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_geolocation']}"},
                        f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_geolocation']}"
                    ]},
                    'state': {'$cond': [
                        {'$isArray': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['state']}"},
                        {'$first':  f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['state']}"},
                        f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['state']}"
                    ]},
                    'city': {'$cond': [
                        {'$isArray': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['new_city']}"},
                        {'$first':  f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['new_city']}"},
                        f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['new_city']}"
                    ]},
                    'zip_code': {'$cond': [
                        {'$isArray': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['zip_code']}"},
                        {'$first':  f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['zip_code']}"},
                        f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['zip_code']}"
                    ]},
                    'country': {'$cond': [
                        {'$isArray': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['country']}"},
                        {'$first':  f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['country']}"},
                        f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['country']}"
                    ]},
                    'phone': {'$cond': [
                        {'$isArray': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['phone']}"},
                        {'$first':  f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['phone']}"},
                        f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['phone']}"
                    ]},
                    'email': {'$cond': [
                        {'$isArray': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['email']}"},
                        {'$first':  f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['email']}"},
                        f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['email']}"
                    ]},
                }
            }
            ]
        res = self.cr.aggregate(query)
        area_address = {}
        for x in res:
            area_address = x
        if not area_address:
            area_address = self.get_location_address(location_name)
        return area_address

    def get_areas_by_location(self, location_name):
        """
        Obtiene todas las areas de una ubicacion
        return:
        lista de areas
        """
        match_query = {
            "deleted_at": {"$exists": False},
            "form_id": self.AREAS_DE_LAS_UBICACIONES,
        }
        if type(location_name) == str:
            match_query[f"answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}"] = location_name
        elif type(location_name) == list:
            match_query[f"answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}"] = {"$in": location_name}

        area_path = f"answers.{self.f['area']}"
        data = self.format_cr(self.cr.find(match_query, {area_path: 1}).sort(area_path, 1), ids_label_dct={'area': self.f['area']})
        result = set(x.get('area') for x in data if x.get('area'))
        result = list(result)
        return result

    def get_areas_por_uso(self, location_names, uso=None):
        """
        Obtiene las areas de una o varias ubicaciones aplicando la marca
        "Utilizar Area en:" (self.f['utilizar_area_en']).
        Por ubicacion: si al menos un area esta marcada con `uso`, solo se
        regresan esas; si ninguna lo esta, se regresan todas las de esa ubicacion.
        uso=None no aplica marca: regresa todas las areas de cada ubicacion.
        Por compatibilidad (ver USO_TIPO_COMPAT), un area sin marca tambien
        cuenta si su tipo de area corresponde al uso pedido.
        return:
        {ubicacion: [nombre_area, ...]}
        """
        if not location_names:
            return {}
        if not isinstance(location_names, list):
            location_names = [location_names]
        location_names = [l for l in location_names if l]
        if not location_names:
            return {}

        location_path = f"answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}"
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.AREAS_DE_LAS_UBICACIONES,
                location_path: {"$in": location_names},
            }},
            {'$project': {
                '_id': 0,
                'location': f"${location_path}",
                'area': f"$answers.{self.f['area']}",
                'usos': {'$ifNull': [f"$answers.{self.f['utilizar_area_en']}", []]},
                'tipo': f"$answers.{self.TIPO_AREA_OBJ_ID}.{self.f['tipo_de_area']}",
            }},
        ]

        tipos_compat = USO_TIPO_COMPAT.get(uso, ())
        todas = {}
        marcadas = {}
        for row in self.cr.aggregate(query):
            location = self.unlist(row.get('location'))
            area = self.unlist(row.get('area'))
            if not location or not area:
                continue
            # utilizar_area_en es checkbox: llega como lista de valores
            usos = row.get('usos') or []
            if not isinstance(usos, list):
                usos = [usos]
            tipo = (self.unlist(row.get('tipo')) or '').strip().lower()
            todas.setdefault(location, set()).add(area)
            if (uso and uso in usos) or (tipo and tipo in tipos_compat):
                marcadas.setdefault(location, set()).add(area)

        return {
            location: sorted(marcadas.get(location) or areas)
            for location, areas in todas.items()
            }

    def get_areas_by_location_salidas(self, location_name):
        options={}
        catalog_id = self.AREAS_DE_LAS_UBICACIONES_SALIDA_ID
        form_id = self.PASE_ENTRADA
        group_level = options.get('group_level',1)
        return self.catalogo_view(catalog_id, form_id, options=options)

    def get_area_status(self, location, area, state='activa'):
        if not isinstance(location, list):
            location = [location]
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.AREAS_DE_LAS_UBICACIONES,
            f"answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}": {"$in": location},
            f"answers.{self.f['area']}":area,
            f"answers.{self.f['area_state']}":state,
        }
        response = self.format_cr(self.cr.find(match_query, {f"answers.{self.f['area_status']}":1}), get_one=True)
        res = response.get('area_status', 'No Configurada')
        return res.title()

    def get_area_record_by_name(self, name, select_cols=[], get_one=True):
        """ Busca area por nombre y regresa registros que cumplan con el nombre.
        Si se le solicita select_cols, solo regresa las columnas solicitadas
        Args:
            name: Nombre del area
            select_cols (opcional): lista de nombres o id de los campos deseados
            get_one (ocpional): La funcion regresa 1 dato al menos que se indique false
        Returns:
            record id directo del cr de la base de datos
        """
        select_c = {}
        if select_cols:
            for c in select_cols:
                try:
                    ObjectId(c)
                    is_field_id = True
                except:
                    is_field_id = False
                r = f'answers.{c}' if is_field_id else c
                select_c[r] = 1
        name_id = self.f['area']
        if select_c:
            cr_res = self.cr.find({
                        'deleted_at': {'$exists': False},
                        'form_id': self.AREAS_DE_LAS_UBICACIONES,
                        f'answers.{name_id}':name
                        }, select_c)
        else:
            cr_res = self.cr.find({
                        'deleted_at': {'$exists': False},
                        'form_id': self.AREAS_DE_LAS_UBICACIONES,
                        f'answers.{name_id}':name
                        })
        return self.format_cr(cr_res, get_one=get_one)

    def update_status_habitacion(self, name, status):
        """ Esta funcion actualiza el status de una areas segun su nombre
        Args:
            name: nombre del area
            status: nuevo status
        Returns:
            El resultado directo del patch
        """
        status_id = self.f['area_state']
        answers = {self.f['area_state']:status}
        record_id = self.get_area_record_by_name(name, ['folio']).get('_id')
        return self.lkf_api.patch_multi_record( answers = answers, form_id=self.AREAS_DE_LAS_UBICACIONES, record_id=[record_id])

    # ============================================
    # Pantalla Explorador de Ubicaciones (clave10 front)
    # ============================================

    def get_ubicacion_by_id(self, record_id):
        """ Obtiene el detalle de una única ubicación por su ID de registro
        (mismo shape de campos que produce get_location_address).
        """
        if not record_id:
            raise self.LKFException({'msg': 'record_id es requerido.', 'status_code': 400})

        query = [
            {'$match': {
                '_id': ObjectId(record_id),
                'form_id': self.UBICACIONES,
                'deleted_at': {'$exists': False},
            }},
            {'$project': {
                '_id': 1,
                'folio': '$folio',
                'location': f"$answers.{self.f['location']}",
                'address_name': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_name']}",
                'address': {'$first': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address']}"},
                'address2': {'$first': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address2']}"},
                'address_type': {'$first': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_type']}"},
                'address_geolocation': {'$first': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_geolocation']}"},
                'state': {'$first': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['state']}"},
                'city': {'$first': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['city']}"},
                'zip_code': {'$first': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['zip_code']}"},
                'country': {'$first': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['country']}"},
                'phone': {'$first': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['phone']}"},
                'email': {'$first': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['email']}"},
            }},
        ]
        response = self.format_cr(self.cr.aggregate(query))
        response = self.unlist(response)
        if not response:
            raise self.LKFException({'msg': 'Ubicación no encontrada', 'status_code': 404})

        location_name = response.get('location', '')
        response['areas_count'] = len(self.get_areas_by_location(location_name))
        response['record_id'] = str(response.get('_id', record_id))
        response.pop('_id', None)
        return response

    # key del filtro (front) -> campo de get_location_address (mismo nombre
    # que en self.f, dentro del catálogo de contacto).
    UBICACION_FILTER_FIELDS = {
        'estado': 'state',
        'ciudad': 'city',
        'pais': 'country',
    }

    # key de search_fields (front) -> campo proyectado en la consulta.
    UBICACION_SEARCH_FIELDS = ('folio', 'location', 'address', 'city', 'state')

    def get_catalog_ubicaciones_formatted(self, locations=None, dynamic_filters=None, limit=25,
                                          skip=0, search='', search_fields=None, ubicacion='', facets=None):
        """ Catálogo paginado del explorador de Ubicaciones, mismo contrato que
        get_catalog_areas_formatted: una sola consulta para todas las locations,
        con dynamic_filters, búsqueda y paginación en Mongo.

        locations: nombres de las ubicaciones del top-nav ([] = todas).
        dynamic_filters: [{key, value}] con las keys de get_filters_ubicaciones
            (estado, ciudad, area, areas).
        search / search_fields: búsqueda por regex (sin mayúsculas) en los campos
            de UBICACION_SEARCH_FIELDS; search_fields vacío = todos.
        ubicacion: compatibilidad con la llamada vieja de una sola ubicación.
        facets: filtros del buscador avanzado (ver ubicaciones_search_fields).

        Returns: {records, total_records, total_pages, actual_page, records_on_page}
        """
        limit = int(limit or 0)
        skip = int(skip or 0)
        locations = [l for l in (locations or []) if l]
        if ubicacion and ubicacion not in locations:
            locations.append(ubicacion)

        match_query, etapas = self._ubicaciones_query(locations)
        query = [{'$match': match_query}, *etapas]

        filtros = self._ubicaciones_match_filtros(dynamic_filters)
        busqueda = self._ubicaciones_match_busqueda(search, search_fields)
        condiciones = [c for c in (filtros, busqueda) if c]
        condiciones += self.build_facets_match(self.ubicaciones_search_fields(), facets)
        if condiciones:
            query.append({'$match': {'$and': condiciones} if len(condiciones) > 1 else condiciones[0]})

        pagina = [{'$sort': {'location': 1}}, {'$skip': skip}]
        if limit:
            pagina.append({'$limit': limit})
        # area_names solo sirve para el filtro "area"; no viaja al front.
        pagina.append({'$project': {'area_names': 0}})
        query.append({'$facet': {
            'records': pagina,
            'total': [{'$count': 'total'}],
        }})

        res = next(self.cr.aggregate(query), {}) or {}
        records = res.get('records', [])
        for r in records:
            r['record_id'] = str(r.pop('_id', ''))
        total_records = (res.get('total') or [{}])[0].get('total', 0)

        return {
            'records': records,
            'total_records': total_records,
            'total_pages': (total_records + limit - 1) // limit if limit else 1,
            'actual_page': (skip // limit) + 1 if limit else 1,
            'records_on_page': len(records),
        }

    def ubicaciones_search_fields(self):
        """ Campos del buscador avanzado de Ubicaciones. Los paths son los campos
        proyectados por _ubicaciones_query (no answers.*); las llaves de los
        filtros son las del panel (get_filters_ubicaciones). """
        return {
            'folio': {'label': 'Folio', 'paths': ['folio']},
            'location': {'label': 'Nombre', 'paths': ['location']},
            'address': {'label': 'Dirección', 'paths': ['address', 'address2']},
            'estado': {
                'label': 'Estado',
                'paths': ['state'],
                'options': lambda: [{'value': v, 'label': v} for v in self._distintos_contacto('state')],
            },
            'ciudad': {
                'label': 'Ciudad',
                'paths': ['city'],
                'options': lambda: [{'value': v, 'label': v} for v in self._distintos_contacto('city')],
            },
            'pais': {'label': 'País', 'paths': ['country']},
            'area': {
                'label': 'Área',
                'paths': ['area_names'],
                'options': lambda: [{'value': v, 'label': v} for v in self._nombres_de_areas()],
            },
            'areas': {
                'label': '¿Contiene áreas?',
                'paths': ['areas_count'],
                'options': [{'value': 'con', 'label': 'Con áreas'}, {'value': 'sin', 'label': 'Sin áreas'}],
                'value_match': {
                    'con': {'areas_count': {'$gt': 0}},
                    'sin': {'areas_count': 0},
                },
            },
        }

    def get_search_fields_ubicaciones(self):
        return self.search_fields_config(self.ubicaciones_search_fields())

    def get_search_counts_ubicaciones(self, locations=None, facets=None, candidates=None):
        match_query, etapas = self._ubicaciones_query([l for l in (locations or []) if l])
        return self.count_facet_candidates(
            match_query, self.ubicaciones_search_fields(), facets, candidates, pipeline=etapas)

    def _ubicaciones_query(self, locations):
        """ $match base y etapas que proyectan los campos del listado (contacto
        y áreas por ubicación); los filtros y facets van sobre lo proyectado. """
        match_query = {
            "deleted_at": {"$exists": False},
            "form_id": self.UBICACIONES,
        }
        if locations:
            match_query[f"answers.{self.f['location']}"] = {"$in": locations}

        def contacto(campo):
            # Algunos registros guardan el campo como lista y otros como valor suelto.
            path = f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f[campo]}"
            return {'$cond': [{'$isArray': path}, {'$first': path}, path]}
        loc_area = f"$answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}"
        etapas = [
            {'$project': {
                '_id': 1,
                'folio': '$folio',
                'location': f"$answers.{self.f['location']}",
                'address_name': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_name']}",
                'address': contacto('address'),
                'address2': contacto('address2'),
                'address_type': contacto('address_type'),
                'address_geolocation': contacto('address_geolocation'),
                'state': contacto('state'),
                'city': contacto('city'),
                'zip_code': contacto('zip_code'),
                'country': contacto('country'),
                'phone': contacto('phone'),
                'email': contacto('email'),
            }},
            # areas_count y area_names dentro de la consulta (y no después de
            # paginar) para que los filtros de áreas y los totales salgan bien.
            # Cuenta nombres de área distintos, igual que get_areas_by_location.
            {'$lookup': {
                'from': self.cr.name,
                'let': {'loc': '$location'},
                'pipeline': [
                    {'$match': {
                        'form_id': self.AREAS_DE_LAS_UBICACIONES,
                        'deleted_at': {'$exists': False},
                        '$expr': {'$eq': [loc_area, '$$loc']},
                    }},
                    {'$group': {'_id': f"$answers.{self.f['area']}"}},
                ],
                'as': 'areas_info',
            }},
            {'$addFields': {
                'areas_count': {'$size': '$areas_info'},
                'area_names': '$areas_info._id',
            }},
            {'$project': {'areas_info': 0}},
        ]
        return match_query, etapas

    def _ubicaciones_match_filtros(self, dynamic_filters):
        """ dynamic_filters -> condición de $match sobre los campos proyectados. """
        condiciones = []
        for item in dynamic_filters or []:
            key = item.get('key')
            value = item.get('value')
            valores = [v for v in (value if isinstance(value, list) else [value]) if v]
            if not valores:
                continue
            if key in self.UBICACION_FILTER_FIELDS:
                condiciones.append({self.UBICACION_FILTER_FIELDS[key]: {'$in': valores}})
            elif key == 'area':
                # Ubicaciones que tienen al menos una de las áreas elegidas.
                condiciones.append({'area_names': {'$in': valores}})
            elif key == 'areas':
                # Con ambas opciones (o ninguna) no se filtra.
                if set(valores) == {'con'}:
                    condiciones.append({'areas_count': {'$gt': 0}})
                elif set(valores) == {'sin'}:
                    condiciones.append({'areas_count': 0})
        if not condiciones:
            return {}
        return {'$and': condiciones} if len(condiciones) > 1 else condiciones[0]

    def _ubicaciones_match_busqueda(self, search, search_fields):
        """ search sobre search_fields (vacío = todos) como $or de regex. """
        texto = (search or '').strip()
        if not texto:
            return {}
        campos = [c for c in (search_fields or []) if c in self.UBICACION_SEARCH_FIELDS] \
            or list(self.UBICACION_SEARCH_FIELDS)
        regex = {'$regex': re.escape(texto), '$options': 'i'}
        return {'$or': [{c: regex} for c in campos]}

    # Campos del empleado: los de "dentro del catalogo" vienen en la copia del
    # catalogo de empleados que guarda Configuracion de areas y empleados; la
    # foto solo esta en la forma Empleados.
    EMPLEADO_UBICACION_FIELDS = {
        'areas_group': '663cf9d77500019d1359eb9f',
        'nombre': '62c5ff407febce07043024dd',
        'puesto': '663bc4c79b8046ce89e97cf4',
        'departamento': '663bc4ed8a6b120eab4d7f1e',
        'email': '6759e4a7a9a6e13c7b26da33',
        'email_usuario': '638a9a7767c332f5d459fc82',
        'telefono': '67be0c43a31e5161c47f2bba',
        'disponibilidad': '663bcbe2274189281359eb78',
        'user_id': '638a9a99616398d2e392a9f5',
        'foto': '663bcbe2274189281359eb70',
    }

    def get_empleados_by_ubicacion(self, ubicacion):
        """ Empleados con acceso a la ubicacion: registros de Configuracion de
        areas y empleados con al menos un area de esa ubicacion en su grupo de
        areas. estatus = disponibilidad del empleado.

        Returns: [{record_id, user_id, nombre, puesto, departamento, email,
                   telefono, foto: [{file_url}], estatus}]
        """
        if not ubicacion:
            raise self.LKFException({'msg': 'La ubicación es requerida.', 'status_code': 400})

        f = self.EMPLEADO_UBICACION_FIELDS
        emp = f"$answers.{self.EMPLEADOS_CAT_OBJ_ID}"

        def primero(campo):
            path = f"{emp}.{f[campo]}"
            return {'$cond': [{'$isArray': path}, {'$first': path}, path]}

        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.CONF_AREA_EMPLEADOS,
                f"answers.{f['areas_group']}.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['location']}": ubicacion,
            }},
            {'$project': {
                '_id': 1,
                'user_id': primero('user_id'),
                'nombre': primero('nombre'),
                'puesto': primero('puesto'),
                'departamento': primero('departamento'),
                'email': {'$ifNull': [primero('email'), primero('email_usuario')]},
                'telefono': primero('telefono'),
                'estatus': primero('disponibilidad'),
            }},
            {'$sort': {'nombre': 1}},
        ]
        # Un empleado puede tener varios registros de configuracion: se deja uno
        # por user_id (o por nombre si no tiene usuario).
        empleados, vistos = [], set()
        for e in self.cr.aggregate(query):
            llave = ('u', e['user_id']) if e.get('user_id') is not None else ('n', e.get('nombre'))
            if llave in vistos:
                continue
            vistos.add(llave)
            empleados.append(e)

        # Foto desde la forma Empleados, en una sola consulta: por user_id y,
        # si el empleado no tiene usuario, por nombre.
        user_ids = [e['user_id'] for e in empleados if e.get('user_id') is not None]
        nombres = [e['nombre'] for e in empleados if e.get('nombre')]
        fotos_por_user, fotos_por_nombre = {}, {}
        if user_ids or nombres:
            user_path = f"answers.{self.USUARIOS_OBJ_ID}.{f['user_id']}"
            nombre_path = f"answers.{f['nombre']}"
            cursor = self.cr.find({
                'deleted_at': {'$exists': False},
                'form_id': self.EMPLEADOS,
                '$or': [{user_path: {'$in': user_ids}}, {nombre_path: {'$in': nombres}}],
            }, {user_path: 1, nombre_path: 1, f"answers.{f['foto']}": 1})
            for doc in cursor:
                a = doc.get('answers', {})
                foto = [{'file_url': x.get('file_url')} for x in (a.get(f['foto']) or []) if isinstance(x, dict) and x.get('file_url')]
                if not foto:
                    continue
                uid = (a.get(self.USUARIOS_OBJ_ID) or {}).get(f['user_id'])
                for u in (uid if isinstance(uid, list) else [uid]):
                    if u is not None:
                        fotos_por_user.setdefault(u, foto)
                if a.get(f['nombre']):
                    fotos_por_nombre.setdefault(a[f['nombre']], foto)

        result = []
        for e in empleados:
            result.append({
                'record_id': str(e.get('_id', '')),
                'user_id': e.get('user_id'),
                'nombre': e.get('nombre') or '',
                'puesto': e.get('puesto') or '',
                'departamento': e.get('departamento') or '',
                'email': e.get('email') or '',
                'telefono': e.get('telefono') or '',
                'foto': fotos_por_user.get(e.get('user_id')) or fotos_por_nombre.get(e.get('nombre')) or [],
                'estatus': e.get('estatus') or '',
            })
        return result

    def get_filters_ubicaciones(self):
        """ Config de filtros del explorador de Ubicaciones, mismo shape que
        get_filters_areas. Las opciones salen de los valores capturados en el
        form 'ubicaciones'.
        """
        return [
            {
                "defaultDisplayOpen": True,
                "key": "estado",
                "label": "Estado",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in self._distintos_contacto(self.UBICACION_FILTER_FIELDS['estado'])]
            },
            {
                "defaultDisplayOpen": False,
                "key": "ciudad",
                "label": "Ciudad",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in self._distintos_contacto(self.UBICACION_FILTER_FIELDS['ciudad'])]
            },
            {
                "defaultDisplayOpen": False,
                "key": "area",
                "label": "Área",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in self._nombres_de_areas()]
            },
            {
                "defaultDisplayOpen": False,
                "key": "areas",
                "label": "¿Contiene áreas?",
                "type": "multiple",
                "options": [
                    {"label": "Con áreas", "value": "con"},
                    {"label": "Sin áreas", "value": "sin"},
                ]
            },
        ]

    def _distintos_contacto(self, campo):
        """ Valores distintos de un campo del contacto de las ubicaciones, para
        las opciones del panel y del buscador. """
        field = f"answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f[campo]}"
        data = self.cr.distinct(field, {
            "deleted_at": {"$exists": False},
            "form_id": self.UBICACIONES,
        })
        valores = {str(x).strip() for x in data if x is not None and str(x).strip()}
        return sorted(valores, key=lambda v: v.lower())

    def _nombres_de_areas(self):
        """ Nombres distintos de las áreas registradas, para el filtro "area"
        del explorador de Ubicaciones. """
        data = self.cr.distinct(f"answers.{self.f['area']}", {
            "deleted_at": {"$exists": False},
            "form_id": self.AREAS_DE_LAS_UBICACIONES,
        })
        valores = {str(x).strip() for x in data if x is not None and str(x).strip()}
        return sorted(valores, key=lambda v: v.lower())

    def exists_ubicacion(self, nombre):
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.UBICACIONES,
                f"answers.{self.f['location']}": nombre,
            }},
            {'$project': {'_id': 1}},
            {'$limit': 1},
        ]
        res = self.format_cr(self.cr.aggregate(query))
        return True if res else False

    # Campos del catalogo de contacto que no estan en self.f.
    CONTACTO_STATUS_FIELD = '663a7f67e48382c5b1230909'

    def _contacto_answers(self, nombre, direccion='', colonia='', ciudad='', estado='', pais='',
                          codigo_postal='', telefono='', email='', geolocalizacion=None):
        """ {campo: valor} del contacto, solo con los campos que traen valor. """
        valores = {
            self.f['address']: direccion,
            self.f['address2']: colonia,
            self.f['city']: ciudad,
            self.f['state']: estado,
            self.f['zip_code']: codigo_postal,
            self.f['country']: pais,
            self.f['phone']: telefono,
            self.f['email']: email,
        }
        valores = {k: v.strip() if isinstance(v, str) else v for k, v in valores.items()}
        valores = {k: v for k, v in valores.items() if v}
        if geolocalizacion:
            valores[self.f['address_geolocation']] = geolocalizacion
        return valores

    def _get_contacto_catalogo(self, nombre):
        """ Registro del catálogo contacto con ese address_name exacto, o {}.
        Se valida el nombre en el resultado: search_catalog puede regresar un
        registro que no coincide (p. ej. con un nombre que no existe). """
        if not nombre:
            return {}
        res = self.lkf_api.search_catalog(self.CONTACTO_CAT_ID, {
            'selector': {f"answers.{self.f['address_name']}": nombre},
            'limit': 50,
        }) or []
        for registro in res:
            if isinstance(registro, dict) and registro.get(self.f['address_name']) == nombre:
                return registro
        return {}

    def _lkf_error(self, response, titulo):
        """ Convierte una respuesta de error de la API de LKF en LKFException. """
        detalle = response.get('json') if isinstance(response, dict) else response
        msgs = []
        if isinstance(detalle, dict):
            for campo in detalle.values():
                if isinstance(campo, dict) and campo.get('msg'):
                    label = campo.get('label', '')
                    msgs.append(f"{label}: {', '.join(campo['msg'])}" if label else ', '.join(campo['msg']))
        msg = '; '.join(msgs) or str(detalle)
        raise self.LKFException({'title': titulo, 'msg': msg, 'status_code': 400})

    def _crear_contacto_catalogo(self, nombre, contacto, tipo='Direccion'):
        """ Da de alta un registro en el catálogo contacto. contacto: {campo: valor}
        de _contacto_answers. Nunca actualiza registros existentes: un PATCH a un
        contacto viejo (_id de CouchDB) terminó creando un duplicado. """
        catalog_answers = {
            self.f['address_name']: nombre,
            self.f['address_type']: tipo or 'Direccion',
            self.CONTACTO_STATUS_FIELD: 'Activo',
            **contacto,
        }
        metadata = self.lkf_api.get_catalog_metadata(catalog_id=self.CONTACTO_CAT_ID)
        metadata.update({'answers': catalog_answers})
        res_catalogo = self.lkf_api.post_catalog_answers(metadata)
        if not isinstance(res_catalogo, dict) or res_catalogo.get('status_code') not in (200, 201, 202):
            self._lkf_error(res_catalogo, 'No se pudo registrar la dirección')
        return res_catalogo

    def create_contacto(self, nombre='', tipo='Direccion', direccion='', colonia='', ciudad='',
                        estado='', pais='', codigo_postal='', telefono='', email='',
                        geolocalizacion=None):
        """ Alta de un contacto (dirección) en el catálogo contacto, desde el
        botón "+" del selector de dirección de la ubicación. """
        nombre = (nombre or '').strip()
        if not nombre:
            raise self.LKFException({'msg': 'El nombre del contacto es requerido.', 'status_code': 400})
        if self._get_contacto_catalogo(nombre):
            raise self.LKFException({'title': 'Contacto duplicado', 'msg': f'Ya existe un contacto llamado "{nombre}".', 'status_code': 400})
        contacto = self._contacto_answers(nombre, direccion, colonia, ciudad, estado, pais,
                                          codigo_postal, telefono, email, geolocalizacion)
        self._crear_contacto_catalogo(nombre, contacto, tipo)
        return {'nombre_direccion': nombre}

    def _contacto_ubicacion_desde_catalogo(self, registro):
        """ Grupo de contacto de la ubicación a partir de un registro del
        catálogo: address_name suelto y el resto como lista, igual que los
        registros existentes. El estatus del contacto no va en la ubicación. """
        omitir = {'_id', '_rev', 'created_at', 'updated_at', 'folio', self.CONTACTO_STATUS_FIELD}
        grupo = {}
        for campo, valor in registro.items():
            if campo in omitir or valor in (None, '', [], {}):
                continue
            if campo == self.f['address_name']:
                grupo[campo] = valor
            else:
                grupo[campo] = valor if isinstance(valor, list) else [valor]
        return grupo

    def create_new_ubicacion(self, nombre='', direccion='', colonia='', ciudad='',
                              estado='', pais='', codigo_postal='', telefono='',
                              email='', geolocalizacion=None, contacto=None):
        """ Crea una ubicacion nueva en el form 'ubicaciones'.

        contacto: address_name de un contacto existente del catálogo (lo que
        manda el front, elegido en el selector o recién dado de alta con
        create_contacto). La ubicación apunta a él y el catálogo no se toca.
        Sin contacto se mantiene el flujo anterior: se da de alta un contacto
        con el nombre de la ubicación y los datos de dirección recibidos.

        El contacto es un campo de catalogo (contacto): LKF solo acepta valores
        que existan en ese catalogo, asi que primero se crea el registro del
        catalogo (si no existe) y luego la ubicacion apuntando a el. En la
        ubicacion el nombre va como texto y el resto de los campos como lista,
        igual que los registros existentes.
        """
        nombre = (nombre or '').strip()
        if not nombre:
            raise self.LKFException({'msg': 'El nombre de la ubicación es requerido.', 'status_code': 400})
        if self.exists_ubicacion(nombre):
            raise self.LKFException({'title': 'Ubicación duplicada', 'msg': f'Ya existe una ubicación llamada "{nombre}".', 'status_code': 400})

        contacto = (contacto or '').strip()
        if contacto:
            registro = self._get_contacto_catalogo(contacto)
            if not registro:
                raise self.LKFException({'title': 'Contacto no encontrado', 'msg': f'No existe el contacto "{contacto}" en el catálogo.', 'status_code': 404})
            contacto_ubicacion = self._contacto_ubicacion_desde_catalogo(registro)
        else:
            valores = self._contacto_answers(nombre, direccion, colonia, ciudad, estado, pais,
                                             codigo_postal, telefono, email, geolocalizacion)

            # 1) Contacto en el catalogo
            if not self._get_contacto_catalogo(nombre):
                self._crear_contacto_catalogo(nombre, valores)

            # 2) Ubicacion apuntando al contacto
            contacto_ubicacion = {self.f['address_name']: nombre, self.f['address_type']: ['Direccion']}
            contacto_ubicacion.update({k: [v] for k, v in valores.items()})

        answers = {
            self.f['location']: nombre,
            self.CONTACTO_CAT_OBJ_ID: contacto_ubicacion,
        }

        metadata = self.lkf_api.get_metadata(form_id=self.UBICACIONES)
        metadata.update({
            'properties': {
                'device_properties': {
                    'system': 'Addons',
                    'process': 'Creacion de Ubicacion',
                    'accion': 'create_new_ubicacion',
                    'file': 'location/service.py',
                },
            },
            'answers': answers,
        })
        response = self.lkf_api.post_forms_answers(metadata)
        if not isinstance(response, dict) or response.get('status_code') not in (200, 201, 202):
            self._lkf_error(response, 'No se pudo crear la ubicación')
        return response

    def update_ubicacion(self, record_id='', nombre_actual='', nombre=None, contacto=None):
        """ Actualiza una ubicación existente.

        contacto: nombre (address_name) de un registro del catálogo contacto.
        La ubicación solo se apunta a ese contacto; el catálogo nunca se
        modifica desde aquí (el contacto puede ser compartido por otras
        ubicaciones/áreas, y el PATCH a contactos viejos los duplicaba). Para
        una dirección nueva, el front da de alta el contacto con
        create_contacto y luego lo elige.
        """
        if not record_id and not nombre_actual:
            raise self.LKFException({'msg': 'Se requiere record_id o nombre_actual de la ubicación.', 'status_code': 400})

        if record_id:
            current = self.get_ubicacion_by_id(record_id)
        else:
            current = self.get_location_address(nombre_actual)
            record_id = str(current.get('_id', ''))

        if not current:
            raise self.LKFException({'msg': 'Ubicación no encontrada.', 'status_code': 404})

        answers = {}
        nombre_anterior = current.get('location') or nombre_actual
        nombre = (nombre or '').strip()
        if nombre and nombre != nombre_anterior:
            answers[self.f['location']] = nombre

        contacto = (contacto or '').strip()
        if contacto and contacto != current.get('address_name'):
            registro = self._get_contacto_catalogo(contacto)
            if not registro:
                raise self.LKFException({'title': 'Contacto no encontrado', 'msg': f'No existe el contacto "{contacto}" en el catálogo.', 'status_code': 404})
            answers[self.CONTACTO_CAT_OBJ_ID] = self._contacto_ubicacion_desde_catalogo(registro)

        if not answers:
            return {'status_code': 200, 'msg': 'Sin cambios'}

        response = self.lkf_api.patch_multi_record(answers=answers, form_id=self.UBICACIONES, record_id=[record_id])
        if isinstance(response, dict) and response.get('status_code') not in (None, 200, 201, 202, 204):
            self._lkf_error(response, 'No se pudo actualizar la ubicación')
        return response
