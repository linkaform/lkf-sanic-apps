# -*- coding: utf-8 -*-
### Linkaform Modules / Archivo de Módulo ###

import pytz
import calendar
import logging
import tempfile
import os
import re
import threading
import unicodedata
import uuid
import simplejson, time
import json
import base64
import random
from collections import defaultdict
from bson import ObjectId
from datetime import datetime, timedelta, time, date
import time as time_module
from copy import deepcopy
from math import ceil
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests
import jwt
import arrow

from pdf2image import convert_from_bytes
from zipfile import ZipFile
from linkaform_api import generar_qr
import io
from wallet.models import Pass, Generic, Barcode, Field


class MyPass(Pass):
    def json_dict(self):
        data = super().json_dict()
        if hasattr(self, "barcode") and self.barcode:
            data["barcode"] = self.barcode.json_dict()
        return data

print('--------------- ACCESOS APP --------------------')
from ..base.tools import *
from .models import AccesosModel
from lkf_addons.tools.OcrMixin import OcrMixin


# class Accesos(Employee, Location, Vehiculo, base.LKF_Base):
class Accesos(OcrMixin, AccesosModel):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)

    '''
    funciones internas: son funciones que solo se pueden mandar llamar dentro de este archivo. Si se hereda la clase
    esta función no puede ser invocada.

    pep-0008:
        _single_leading_underscore:
        weak “internal use” indicator. E.g. from M import * does not import objects whose names start with an underscore.
    '''

    def _do_access(self, access_pass, location, area, data):
        '''
        Registra el acceso del pase de entrada a ubicación.
        solo puede ser ejecutado después de revisar los accesos
        '''
        employee =  self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
        metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_ACCESOS)
        metadata.update({
            'properties': {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Ingreso de Personal",
                    "Action": 'Do Access',
                    "File": "accesos/app.py"
                }
            },
        })
        # metadata['folio'] = self.create_poruction_lot_number()

        try:
            pase = {
                    f"{self.mf['nombre_visita']}": access_pass['nombre'],
                    f"{self.mf['curp']}":access_pass['curp'],
                    ### Campos Select
                    f"{self.mf['empresa']}":[access_pass.get('empresa'),],
                    f"{self.pase_entrada_fields['perfil_pase_id']}": [access_pass['tipo_de_pase'],],
                    # f"{self.pase_entrada_fields['status_pase']}":[access_pass['estatus'],],
                    f"{self.pase_entrada_fields['status_pase']}":['Activo',],
                    f"{self.pase_entrada_fields['foto_pase_id']}": access_pass.get("foto",[]), #[access_pass['foto'],], #.get('foto','')
                    f"{self.pase_entrada_fields['identificacion_pase_id']}": access_pass.get("identificacion",[]) #[access_pass['identificacion'],], #.get('identificacion','')
                    }
        except Exception as e:
            self.LKFException({"msg":f"Error al crear registro ingreso, no se encontro: {e}"})

        answers = {
            f"{self.mf['tipo_registro']}": 'entrada',
            f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}":{
                f"{self.f['location']}":location,
                f"{self.f['area']}":area
                },
            f"{self.PASE_ENTRADA_OBJ_ID}":pase,
            f"{self.mf['codigo_qr']}": str(access_pass['_id']),
            f"{self.mf['fecha_entrada']}":self.today_str(employee.get('timezone', 'America/Monterrey'), date_format='datetime'),
        }
        vehiculos = data.get('vehiculo',[])
        if vehiculos:
            list_vehiculos = []
            for item in vehiculos:
                if item:
                    tipo = item.get('tipo','')
                    marca = item.get('marca','')
                    modelo = item.get('modelo','')
                    estado = item.get('estado','')
                    placas = item.get('placas','')
                    color = item.get('color','')
                    list_vehiculos.append({
                        self.AF.TIPO_DE_VEHICULO_OBJ_ID:{
                            self.mf['tipo_vehiculo']:tipo,
                            self.mf['marca_vehiculo']:marca,
                            self.mf['modelo_vehiculo']:modelo,
                        },
                        self.ESTADO_OBJ_ID:{
                            self.mf['nombre_estado']:estado,
                        },
                        self.mf['placas_vehiculo']:placas,
                        self.mf['color_vehiculo']:color,
                        self.mf['foto_vehiculo']:item.get('foto_vehiculo',[])
                    })
            answers[self.mf['grupo_vehiculos']] = list_vehiculos

        equipos = data.get('equipo',[])

        if equipos:
            list_equipos = []
            for item in equipos:
                tipo = item.get('tipo','').lower().replace(' ', '_')
                nombre = item.get('nombre','')
                marca = item.get('marca','')
                modelo = item.get('modelo','')
                color = item.get('color','')
                serie = item.get('serie','')
                list_equipos.append({
                    self.mf['tipo_equipo']:tipo,
                    self.mf['nombre_articulo']:nombre,
                    self.mf['marca_articulo']:marca,
                    self.mf['modelo_articulo']:modelo,
                    self.mf['color_articulo']:color,
                    self.mf['numero_serie']:serie,
                    self.mf['foto_equipo']:item.get('foto_equipo',[])
                })
            answers[self.mf['grupo_equipos']] = list_equipos

        gafete = data.get('gafete',{})
        if gafete:
            gafete_ans = {}
            gafete_ans[self.GAFETES_CAT_OBJ_ID] = {self.gafetes_fields['gafete_id']:gafete.get('gafete_id')}
            gafete_ans[self.LOCKERS_CAT_OBJ_ID] = {self.mf['locker_id']:gafete.get('locker_id')}
            gafete_ans[self.mf['documento']] = gafete.get('documento_garantia')
            answers.update(gafete_ans)
            self.update_gafet_status(answers)


        comment = data.get('comentario_acceso',[])
        comments_pase = data.get('comentario_pase',[])
        if comment or comments_pase:
            comment_list = []
            for c in comment:
                if c.get('comentario_pase'):
                    comment_list.append(
                        {
                            self.bitacora_fields['comentario']: c.get('comentario_pase'),
                            self.bitacora_fields['tipo_comentario'] :c.get('tipo_de_comentario').lower().replace(' ', '_')
                        }
                    )
            for c in comments_pase:
                if c.get('comentario_pase'):
                    comment_list.append(
                        {
                            self.bitacora_fields['comentario']:c.get('comentario_pase'),
                            self.bitacora_fields['tipo_comentario'] :c.get('tipo_de_comentario').lower().replace(' ', '_')
                        }
                    )
            if comment_list:
                answers.update({self.bitacora_fields['grupo_comentario']:comment_list})

        visit_list = data.get('visita_a',[])
        if visit_list:
            visit_list2 = []
            for c in visit_list:
                visit_list2.append(
                   { f"{self.bitacora_fields['visita']}":{
                       self.bitacora_fields['visita_nombre_empleado']:c.get('nombre'),
                       self.mf['id_usuario'] :[c.get('user_id')],
                       self.bitacora_fields['visita_departamento_empleado']:[c.get('departamento')],
                       self.bitacora_fields['puesto_empleado']:[c.get('puesto')],
                       self.mf['email_visita_a'] :[c.get('email')]
                   }}
                )
            answers.update({self.bitacora_fields['visita_a']:visit_list2})

        metadata.update({'answers':answers})
        response_create = self.lkf_api.post_forms_answers(metadata)
        return response_create

    def assets_access_pass(self, location):
        """
        Regresa diccionario con las areas, personas que puede visitar en esa ubicacion y los perfiles

        args:
            location (str|list): Nombre de la ubicacion

        returns:
            {
            Areas:[ lista de areas ],
            Vistia_a:[ lista de personas ]
            Perfiles:[ lista de prefiles ]
            }
        """
        ### Areas
        try:
            areas = self.Location.get_areas_by_location(location)
        except:
            areas = []
        ### Aquien Visita
        try:
            visita_a =  self.Employee.get_users_by_location_area(location_name=location)
            visita_a = [x['name'] for x in visita_a if x.get('name')]
        except:
            visita_a = []
        ### Perfiles de accesos
        # try:
        #     perfiles = self.get_pefiles_walkin(location)
        # except:
        #     perfiles = []
        try:
            config_modulo = self.get_config_modulo_seguridad(location)
            requerimientos = config_modulo.get('requerimientos',[])
            envios = config_modulo.get('envios',[])
            perfiles = config_modulo.get('tipos',[])
        except:
            Perfiles = []
            envios = []
            requerimientos = []
        res = {
            'Areas': areas,
            'Visita_a': visita_a,
            'Perfiles': perfiles,
            'requerimientos': requerimientos,
            'envios':envios,
            'Perfiles':perfiles

        }
        return res

    def assing_gafete(self, data_gafete, id_bitacora, tipo_movimiento):
        answers={}
        answers_return={}
        for key, value in data_gafete.items():
            if key == "gafete_id":
                answers[self.GAFETES_CAT_OBJ_ID] = {self.gafetes_fields['gafete_id']:data_gafete.get('gafete_id')}
                # answers_return[self.GAFETES_CAT_OBJ_ID] = {self.gafetes_fields['gafete_id']:""}
            elif key == "locker_id":
                answers[self.LOCKERS_CAT_OBJ_ID] = {self.mf['locker_id']:data_gafete.get('locker_id')}
                # answers_return[self.LOCKERS_CAT_OBJ_ID] = {self.mf['locker_id']:""}

            if  key == 'ubicacion' or key == 'area':
                if data_gafete['ubicacion'] and not data_gafete['area']:
                    answers[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]={self.f['location']:data_gafete.get('ubicacion')}
                    # answers_return[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]={self.f['location']:data_gafete.get('ubicacion')}
                elif data_gafete['area'] and not data_gafete['ubicacion']:
                    answers[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]={self.f['area']:data_gafete.get('area', "")}
                    # answers_return[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]={self.f['area']:data_gafete.get('area', "")}
                elif data_gafete['area'] and data_gafete['ubicacion']:
                    answers[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID] = {self.f['location']:data_gafete.get('ubicacion'),self.f['area']:data_gafete.get('area', "")}
                    # answers_return[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID] = {self.f['location']:data_gafete.get('ubicacion'),self.f['area']:data_gafete.get('area', "")}
            elif key == "status_gafete":
                answers[self.mf['status_gafete']]=data_gafete.get('status_gafete')
                # answers_return[self.mf['status_gafete']]=data_gafete.get('status_gafete')
            elif key == "documento":
                answers[self.mf['documento']] = data_gafete.get('documento')
                # answers_return[self.mf['documento']] = data_gafete.get('documento')
        if answers or answers_return:
            # ans={}
            # if tipo_movimiento=="salida":
            #     ans=answers_return
            # else:
            #     ans=answers
            res= self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_ACCESOS, record_id=[id_bitacora])
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                answers[self.mf['tipo_registro']] = tipo_movimiento.lower()
                res_gaf = self.update_gafet_status(answers)
                if res_gaf.get('status_code') == 201 or res_gaf.get('status_code') == 202:
                    return res
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def delete_article_concessioned(self, folio):
        list_records = []
        if len(folio) > 0:
            for element in folio:
                response = self.get_record_by_folio(element, self.CONCESSIONED_ARTICULOS, select_columns={'_id':1,})
                if response.get('_id'):
                    list_records.append("/api/infosync/form_answer/"+str(response['_id'])+"/")
                else:
                    self.LKFException('No se encontro el folio correspondiente')
        else:
            self.LKFException('Lista de folios vacia, ingrese folio')

        if len(list_records) > 0:
            return self.check_status_code(self.lkf_api.patch_record_list({"deleted_objects": list_records,}))
        else:
            self.LKFException('No se encontro los folios correspondiente')
            
    def delete_article_lost(self, folio):
        list_records = []
        if len(folio) > 0:
            for element in folio:
                response = self.get_record_by_folio(element, self.BITACORA_OBJETOS_PERDIDOS, select_columns={'_id':1,})
                if response.get('_id'):
                    list_records.append("/api/infosync/form_answer/"+str(response['_id'])+"/")
                else:
                    self.LKFException('No se encontro el folio correspondiente')
        else:
            self.LKFException('Lista de folios vacia, ingrese folio')

        if len(list_records) > 0:
            return self.check_status_code(self.lkf_api.patch_record_list({"deleted_objects": list_records,}))
        else:
            self.LKFException('No se encontro los folios correspondiente')

    def delete_failure(self, folio):
        list_records = []
        if len(folio) > 0:
            for element in folio:
                response = self.get_record_by_folio(element, self.BITACORA_FALLAS, select_columns={'_id':1,})
                if response.get('_id'):
                    list_records.append("/api/infosync/form_answer/"+str(response['_id'])+"/")
                else:
                    self.LKFException('No se encontro el folio correspondiente')
        else:
            self.LKFException('Lista de folios vacia, ingrese folio')

        if len(list_records) > 0:
            return self.check_status_code(self.lkf_api.patch_record_list({"deleted_objects": list_records,}))
        else:
            self.LKFException('No se encontro los folios correspondiente')

    def delete_incidence(self, folio):
        list_records = []
        if len(folio) > 0:
            for element in folio:
                response = self.get_record_by_folio(element, self.BITACORA_INCIDENCIAS, select_columns={'_id':1,})
                if response.get('_id'):
                    list_records.append("/api/infosync/form_answer/"+str(response['_id'])+"/")
                else:
                    self.LKFException('No se encontro el folio correspondiente')
        else:
            self.LKFException('Lista de folios vacia, ingrese folio')

        if len(list_records) > 0:
            return self.check_status_code(self.lkf_api.patch_record_list({"deleted_objects": list_records,}))
        else:
            self.LKFException('No se encontro los folios correspondiente')

    def delete_notes(self, folio):
        list_records = []
        if len(folio) > 0:
            for element in folio:
                response = self.get_record_by_folio(element, self.ACCESOS_NOTAS, select_columns={'_id':1,})
                if response.get('_id'):
                    list_records.append("/api/infosync/form_answer/"+str(response['_id'])+"/")
                else:
                    self.LKFException('No se encontro el folio correspondiente')
        else:
            self.LKFException('Lista de folios vacia, ingrese folio')

        if len(list_records) > 0:
            return self.check_status_code(self.lkf_api.patch_record_list({"deleted_objects": list_records,}))
        else:
            self.LKFException('No se encontro los folios correspondiente')

    def deliver_badge(self, folio):
        answers = {
            self.gafetes_fields['status_gafete']:'recibir_gafete',
        }
        if folio:
            return self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_GAFETES_LOCKERS, folios=[folio])
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def delete_paquete(self, folio):
        print("del", folio)

    def create_paquete(self, data_paquete):
        metadata = self.lkf_api.get_metadata(form_id=self.PAQUETERIA)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de Paquetes",
                    "Action": "nuevo_paquete",
                    "File": "accesos/app.py"
                }
            },
        })
        answers = {}
        for key, value in data_paquete.items():
            if key == 'ubicacion_paqueteria':
                answers[self.Location.UBICACIONES_CAT_OBJ_ID] = { self.mf['ubicacion']: value}
            elif  key == 'area_paqueteria':
                 answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID] = { self.mf['nombre_area']: value}
            elif  key == 'guardado_en_paqueteria':
                answers[self.LOCKERS_CAT_OBJ_ID] ={self.mf['locker_id']:value}
            elif key == 'proveedor':
                answers[self.PROVEEDORES_CAT_OBJ_ID] = {self.paquetes_fields['proveedor']:value}
            elif key == 'quien_recibe_paqueteria':
                answers[self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID] = {self.mf['nombre_empleado']:value}
            elif key == 'quien_recibe_otro':
                answers[self.paquetes_fields['quien_recibe_otro']] = value
            else:
                answers.update({f"{self.paquetes_fields[key]}":value})
        metadata.update({'answers':answers})
        res=self.lkf_api.post_forms_answers(metadata)
        return res

    def get_catalogo_paquetes(self):
        catalog_id = self.PROVEEDORES_CAT_ID
        form_id= self.PAQUETERIA
        return self.lkf_api.catalog_view(catalog_id, form_id)

    def get_active_guards_in_location(self, location, rol=None):
        match = {
            "deleted_at": {"$exists": False},
            "form_id": self.REGISTRO_ASISTENCIA,
            f"answers.{self.f['start_shift']}": {"$exists": True},
            f"answers.{self.f['end_shift']}": {"$exists": False},
            f"answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['ubicacion']}": location,
        }
        query = [
            {"$match": match},
            {"$project": {
                "_id": 1,
                "created_at": 1,
                "created_by_id": 1,
                "created_by_email": 1,
                "created_by_name": 1,
            }},
            {"$sort": {
                "created_at": -1
            }},
            {"$limit": 1}
        ]
        response = self.format_cr(self.cr.aggregate(query), get_one=True)
        return response

    def assigne_bitacora(self, answers, record_id):
        location = answers.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.f['ubicacion'], None)
        if not location:
            return
        user_info = self.get_active_guards_in_location(location=location)
        user_id = (user_info or {}).get('created_by_id')
        if user_id and record_id:
            return self.lkf_api.assigne_user_records(user_id, [record_id,])

    def update_delete_suplente(self, nombre_suplente=""):
        answers = {}
        user_id = self.user.get('user_id')
        user_status = self.get_employee_checkin_status(user_id, as_shift=True, available=False)
        if nombre_suplente:
            answers[self.checkin_fields['nombre_suplente']] = nombre_suplente
        folio = user_status.get(user_id, {}).get('folio')
        if answers or folio:
            return self.lkf_api.patch_multi_record( answers = answers, form_id=self.CHECKIN_CASETAS, folios=[folio])

    def force_quit_all_persons(self, location):
        match = {
            "deleted_at": {"$exists": False},
            "form_id": self.BITACORA_ACCESOS,
            f"answers.{self.mf['tipo_registro']}": "entrada",
        }
        if location:
            match[f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}"] = location

        query = [
            {'$match': match},
            {'$project': {
                '_id': 1,
            }},
        ]
        data = self.format_cr(self.cr.aggregate(query))
        format_data = {"data": data,
            "status_code": 200,
            "json": {
                "msg": "No hay personas dentro por registrar salida."
            }
        }
        if data:
            record_ids = [record.get('_id') for record in data]
            tz_mexico = pytz.timezone('America/Mexico_City')
            now = datetime.now(tz_mexico)
            fecha_hora_str = now.strftime("%Y-%m-%d %H:%M:%S")
            replace_answers = {
                self.mf['fecha_salida']: fecha_hora_str,
                self.mf['tipo_registro']: 'salida',
            }
            response = self.lkf_api.patch_multi_record(answers=replace_answers, form_id=self.BITACORA_ACCESOS, record_id=record_ids)
            if response.get('status_code') in [200, 201, 202]:
                response['json']['msg'] = f'Salida masiva en {location} ejecutada correctamente.'
                format_data = response
            else:
                self.LKFException({'title': 'Error', 'msg': 'Hubo un error al actualizar los registros.'})
        return format_data

    def do_access(self, qr_code, location, area, data):
        '''
        Valida pase de entrada y crea registro de entrada al pase
        '''
        access_pass = self.get_detail_access_pass(qr_code)
        if not qr_code and not location and not area:
            return False
        total_entradas = self.get_count_ingresos(qr_code)

        diasDisponibles = access_pass.get("limitado_a_dias", [])
        dias_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        tz = pytz.timezone("America/Mexico_City")
        hoy = datetime.now(tz)
        dia_semana = hoy.weekday()
        nombre_dia = dias_semana[dia_semana]
        if access_pass.get('estatus',"") == 'cancelado':
            self.LKFException({'msg':"El pase esta cancelado, edita la información o genera uno nuevo.","title":'Revisa la Configuración'})
        elif access_pass.get('estatus',"") == 'vencido':
            self.LKFException({'msg':"El pase esta vencido, edita la información o genera uno nuevo.","title":'Revisa la Configuración'})
        elif access_pass.get('estatus', '') == 'proceso':
            self.LKFException({'msg':"El pase no se ha sido completado aun, informa al usuario que debe completarlo primero.","title":'Requisitos faltantes'})

        if diasDisponibles:
            if nombre_dia not in diasDisponibles:
                dias_capitalizados = [dia.capitalize() for dia in diasDisponibles]

                if len(dias_capitalizados) > 1:
                    dias_formateados = ', '.join(dias_capitalizados[:-1]) + ' y ' + dias_capitalizados[-1]
                else:
                    dias_formateados = dias_capitalizados[0]

                self.LKFException({
                        'msg': f"Este pase no te permite ingresar hoy {nombre_dia.capitalize()}. Solo tiene acceso los siguientes dias: {dias_formateados}",
                        "title":'Aviso'
                    })

        limite_acceso = access_pass.get('limite_de_acceso')
        if len(total_entradas) > 0 and limite_acceso and int(limite_acceso) > 0:
            if total_entradas['total_records']>= int(limite_acceso) :
                self.LKFException({'msg':"Se ha completado el limite de entradas disponibles para este pase, edita el pase o crea uno nuevo.","title":'Revisa la Configuración'})

        timezone = pytz.timezone(self.user.get('timezone', 'America/Mexico_City'))
        fecha_actual = datetime.now(timezone).replace(microsecond=0)
        fecha_caducidad = access_pass.get('fecha_de_caducidad')
        fecha_obj_caducidad = datetime.strptime(fecha_caducidad, "%Y-%m-%d %H:%M:%S")
        fecha_caducidad = timezone.localize(fecha_obj_caducidad)

        # Se agrega 1 hora como margen de tolerancia
        fecha_caducidad_con_margen = fecha_caducidad + timedelta(hours=1)

        if fecha_caducidad_con_margen < fecha_actual:
            self.LKFException({'msg':"El pase esta vencido, ya paso su fecha de vigencia.","title":'Advertencia'})

        # Validación de tolerancia de entrada para pases de fecha fija
        fecha_visita = access_pass.get('fecha_de_expedicion')
        if fecha_visita:
            tipo_visita = access_pass.get('tipo_visita_pase', '')
            if tipo_visita == 'fecha_fija':
                config_accesos = self.get_config_accesos()
                grupo_requisitos = config_accesos.get('requisitos', [])

                tolerancia_entrada_previa = None
                tolerancia_entrada_posterior = None
                for req in grupo_requisitos:
                    if req.get('ubicacion') == location:
                        tolerancia_entrada_previa = req.get('tolerancia_de_entrada_previa')
                        tolerancia_entrada_posterior = req.get('tolerancia_de_entrada_posterior')
                        break

                DEFAULT_TOLERANCIA = 15
                usar_default_previa    = tolerancia_entrada_previa    in (None, '', 'None')
                usar_default_posterior = tolerancia_entrada_posterior in (None, '', 'None')
                tolerancia_entrada_previa    = DEFAULT_TOLERANCIA if usar_default_previa    else int(tolerancia_entrada_previa)
                tolerancia_entrada_posterior = DEFAULT_TOLERANCIA if usar_default_posterior else int(tolerancia_entrada_posterior)

                fecha_obj_visita = datetime.strptime(fecha_visita, "%Y-%m-%d %H:%M:%S")
                fecha_visita_tz = timezone.localize(fecha_obj_visita)
                fecha_inicio = fecha_visita_tz - timedelta(minutes=tolerancia_entrada_previa)
                fecha_fin    = fecha_visita_tz + timedelta(minutes=tolerancia_entrada_posterior)
                tz_nombre = fecha_actual.strftime('%Z')

                if fecha_actual < fecha_inicio:
                    self.LKFException({
                        'msg': f"Aún no es hora de entrada. Tu acceso estará disponible a partir de las {fecha_inicio.strftime('%Y-%m-%d %H:%M:%S')} {tz_nombre} ({tolerancia_entrada_previa} minutos antes de tu cita{', tiempo por defecto' if usar_default_previa else ''}).",
                        "title": 'Aviso'
                    })
                if fecha_actual > fecha_fin:
                    self.LKFException({
                        'msg': f"El tiempo de tolerancia ha expirado. Tu cita era a las {fecha_visita} {tz_nombre} con una tolerancia posterior de {tolerancia_entrada_posterior} minutos{' (tiempo por defecto)' if usar_default_posterior else ''}.",
                        "title": 'Acceso Denegado'
                    })

        if location not in access_pass.get("ubicacion",[]):
            msg = f"La ubicación {location}, no se encuentra en el pase. Pase valido para las siguientes ubicaciones: {access_pass.get('ubicacion',[])}."
            self.LKFException({'msg':msg,"title":'Revisa la Configuración'})

        if self.validate_access_pass_location(qr_code, location):
            self.LKFException("En usuario ya se encuentra dentro de una ubicacion")
        val_certificados = self.validate_certificados(qr_code, location)


        pass_dates = self.validate_pass_dates(access_pass)
        comentario_pase =  data.get('comentario_pase',[])
        if comentario_pase:
            values = {self.pase_entrada_fields['grupo_instrucciones_pase']:{
                -1:{
                self.pase_entrada_fields['comentario_pase']:comentario_pase,
                self.mf['tipo_de_comentario']:'caseta'
                }
            }
            }
            # self.update_pase_entrada(values, record_id=[str(access_pass['_id']),])
        res = self._do_access(access_pass, location, area, data)
        return res

    def do_attendance(self, asistencia_answers):
        metadata = self.lkf_api.get_metadata(form_id=self.REGISTRO_ASISTENCIA)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": 'Accesos',
                    "Process": 'Inicio de turno',
                    "Action": 'asistencia',
                    "File": 'accesos/app.py',
                }
            },
        })
        metadata.update({'answers':asistencia_answers})
        response = self.lkf_api.post_forms_answers(metadata)
        if response.get('status_code') in [200, 201, 202]:
            return True
        else:
            return self.LKFException({'title': 'Error en registro de asistencia', 'msg': {'response': response}})

    def do_checkin(self, location, area, employee_list=[], fotografia=[], check_in_manual={}, nombre_suplente="", checkin_id="", roles=[]):
        # Realiza el check-in en una ubicación y área específica.

        is_available = self.is_boot_available(location, area)
        user_id_actual = self.user.get('user_id')
        current_user = self.lkf_api.get_user_by_id(user_id_actual)
        user_name = current_user.get('name', '')

        #! Si is_boot_available no encontró el registro abierto (ej. condición de carrera),
        #! se hace una búsqueda explícita por estado abierto como salvaguarda.
        if is_available:
            open_record = self.get_open_checkin(location, area)
            if open_record:
                is_available = False
                checkin_id = open_record.get('_id', open_record.get('id', checkin_id))

        #! Si la caseta ya esta abierta, solo se agrega el guardia al turno existente.
        if not is_available:
            res = self.update_guards_checkin(
                [{'user_id': user_id_actual, 'name': user_name}],
                self.last_check_in.get('_id',''),
                location, area, current_user, nombre_suplente, fotografia)
            format_res = self.unlist(res)
            if format_res.get('status_code') in [200, 201, 202]:
                return format_res
            else:
                self.LKFException({'title': 'Error al hacer check-in', 'msg': format_res.get('json')})

        if employee_list:
            user_id = [self.user.get('user_id'),] + [x['user_id'] for x in employee_list]
        else:
            user_id = self.user.get('user_id')
        boot_config = self.Employee.get_users_by_location_area(
            location_name=location,
            area_name=area,
            user_id=user_id)
        if not boot_config:
            msg = f"User can not login to this area : {area} at location: {location} ."
            msg += f"Please check your configuration."
            self.LKFException(msg)
        else:
            allowed_users = [x['user_id'] for x in boot_config]
            if type(user_id) == int:
                user_id=[user_id]
            common_values = list(set(user_id) & set(allowed_users))
            not_allowed = [value for value in user_id if value not in common_values]
        if not_allowed:
            msg = f"Usuarios con ids {not_allowed}. "
            msg += f"No estan permitidos de hacer checking en esta area : {area} de la ubicacion {location} ."
            self.LKFException({'msg':msg,"title":'Error de Configuracion'})

        validate_status = self.get_employee_checkin_status(user_id)
        not_allowed = [uid for uid, u_data in validate_status.items() if u_data['status'] =='in']
        if not_allowed:
            msg = f"El usuario(s) con ids {not_allowed}. Se encuentran actualmente logeado en otra caseta."
            msg += f"Es necesario primero salirse de cualquier caseta antes de querer entrar a una casta"
            self.LKFException({'msg':msg,"title":'Accion Requerida!!!'})

        employee = self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
        if not employee:
            msg = f"Ningun empleado encontrado con email: {self.user.get('email')}"
            self.LKFException(msg)
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        employee['timezone'] = user_data.get('timezone','America/Monterrey')
        employee['name'] = employee['worker_name']
        employee['position'] = self.chife_guard
        timezone = employee.get('cat_timezone', employee.get('timezone', 'America/Monterrey'))
        data = self.lkf_api.get_metadata(self.CHECKIN_CASETAS)
        now_datetime =self.today_str(timezone, date_format='datetime')
        checkin = self.checkin_data(employee, location, area, 'in', now_datetime)
        employee_list.insert(0,employee)
        checkin = self.check_in_out_employees('in', now_datetime, checkin=checkin, employee_list=employee_list)


        data.update({
                'properties': {
                    "device_properties":{
                        "system": "Modulo Accesos",
                        "process": 'Checkin-Checkout',
                        "action": 'do_checkin',
                        "archive": "accesos_utils.py"
                    }
                },
                'answers': checkin
            })
        if check_in_manual:
            checkin.update({
                self.checkin_fields['checkin_image']: check_in_manual.get('image', []),
                self.checkin_fields['commentario_checkin_caseta']: check_in_manual.get('comment', '')
            })
        if fotografia:
            checkin.update({
                self.checkin_fields['fotografia_inicio_turno']: fotografia
            })

        resp_create = self.lkf_api.post_forms_answers(data)
        #TODO agregar nombre del Guardia Quien hizo el checkin
        if resp_create.get('status_code') == 201:
            resp_create['json'].update({'boot_status':{'guard_on_duty':user_data['name']}})
            asistencia_answers = {
                self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID: {
                    self.Location.f['location']: location,
                    self.Location.f['area']: area
                },
                self.f['tipo_guardia']: 'guardia_regular',
                self.checkin_fields['checkin_type']: 'iniciar_turno',
                self.f['image_checkin']: fotografia,
                self.f['grupo_roles']: roles
            }
            if nombre_suplente:
                asistencia_answers.update({
                    self.f['tipo_guardia']: 'guardia_suplente',
                    self.f['nombre_guardia_suplente']: nombre_suplente
                })
            attendance_ok = self.do_attendance(asistencia_answers)
            if attendance_ok is True:
                resp_create.update({'registro_de_asistencia': 'Correcto'})
            else:
                resp_create.update({'registro_de_asistencia': 'Error'})
        return resp_create

    def do_checkout_aux_guard(self, checkin_id=None, location=None, area=None, guards=[], forzar=False, comments=False):
        """
        Realiza el checkout de los guardias auxiliares especificados en guards.
        """
        employee = self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
        timezone = employee.get('cat_timezone', employee.get('timezone', 'America/Monterrey'))
        now_datetime = self.today_str(timezone, date_format='datetime')
        last_chekin = {}

        # Solo buscamos el último checkin de los guards especificados
        if not checkin_id and guards:
            last_chekin = self.get_guard_last_checkin(guards)
            checkin_id = last_chekin.get('_id')

        if not checkin_id:
            self.LKFException({
                "msg": "No encontramos un checking valido del cual podemos hacer checkout...", 
                "title": "Una Disculpa!!!"
            })

        record = self.get_record_by_id(checkin_id)
        checkin_answers = record['answers']
        folio = record['folio']

        # Realiza el checkout solo de los guards especificados
        data = self.lkf_api.get_metadata(self.CHECKIN_CASETAS)
        checkin_answers = self.check_in_out_employees('out', now_datetime, checkin=checkin_answers, employee_list=guards)
        data['answers'] = checkin_answers
        response = self.lkf_api.patch_record(data=data, record_id=checkin_id)
        return response

    # ============================================
    # Checkin manual de guardias con horarios (migrado de check_in_manual.py, hook)
    # ============================================

    def verify_guard_status(self, user_id, timezone):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.REGISTRO_ASISTENCIA,
                f"answers.{self.f['start_shift']}": {"$exists": True},
                f"answers.{self.f['end_shift']}": {"$exists": False},
                "user_id": user_id,
            }},
            {"$project": {
                "_id": 1,
                "created_at": 1,
                "estatus": f"$answers.{self.checkin_fields['checkin_type']}",
                "fecha_inicio": f"$answers.{self.f['start_shift']}",
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        if response:
            self.automatic_close_turn(records=response, timezone=timezone)
        return True

    def automatic_close_turn(self, records=[], timezone='America/Monterrey'):
        fecha_inicio = ''
        for record in records:
            fecha_inicio = record.get('fecha_inicio', '')
            if fecha_inicio:
                fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d %H:%M:%S')

            if fecha_inicio:
                tz = pytz.timezone(timezone if timezone else 'America/Monterrey')
                fecha_inicio = tz.localize(fecha_inicio)
                fecha_fin = fecha_inicio + timedelta(hours=8)
                now = datetime.now(tz)
                if now > fecha_fin:
                    fecha_cierre = fecha_fin.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    fecha_cierre = now.strftime('%Y-%m-%d %H:%M:%S')
            else:
                fecha_cierre = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            answers = {}
            answers[self.f['option_checkin']] = 'cerrar_turno'
            answers[self.f['comment_checkout']] = 'Cierre de turno automatico.'
            answers[self.f['end_shift']] = fecha_cierre
            if answers:
                record_id = record.get('_id', record.get('id'))
                self.lkf_api.patch_multi_record(answers=answers, form_id=self.REGISTRO_ASISTENCIA, record_id=[record_id,])

    def get_guard_data(self, guard_id, location, hora_inicio):
        default_shifts = {
            "T1": {"start": "06:00:00", "end": "14:00:00", "tolerance": 15, "max_delay": 120},
            "T2": {"start": "14:00:00", "end": "22:00:00", "tolerance": 15, "max_delay": 120},
            "T3": {"start": "22:00:00", "end": "06:00:00", "tolerance": 15, "max_delay": 120},
        }
        dt_inicio = datetime.strptime(hora_inicio, "%Y-%m-%d %H:%M:%S")
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.Employee.EMPLEADOS,
                f"answers.{self.USUARIOS_OBJ_ID}.{self.f['new_user_id']}": guard_id,
            }},
            {"$project": {
                "_id": 0,
                "dias_libres": f"$answers.{self.f['dias_libres']}",
            }},
            {"$lookup": {
                "from": "form_answer",
                "pipeline": [
                    {"$match": {
                        "deleted_at": {"$exists": False},
                        "form_id": self.HORARIOS,
                    }},
                    {"$unwind": f"$answers.{self.f['grupo_turnos']}"},
                    {"$match": {
                        "$expr": {
                            "$eq": [f"$answers.{self.f['grupo_turnos']}.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}", location]
                        }
                    }},
                    {"$project": {
                        "_id": 0,
                        "hora_inicio": f"$answers.{self.f['hora_entrada']}",
                        "hora_fin": f"$answers.{self.f['hora_salida']}",
                        "nombre_horario": f"$answers.{self.f['nombre_horario']}",
                        "tolerancia_retardo": f"$answers.{self.f['tolerancia_retardo']}",
                        "retardo_maximo": f"$answers.{self.f['retardo_maximo']}",
                        "ingreso_maximo": f"$answers.{self.f['ingreso_maximo']}",
                        "areas": f"$answers.{self.f['grupo_turnos']}",
                    }}
                ],
                "as": "turnos"
            }},
            {"$project": {
                "dias_libres": 1,
                "turnos": 1
            }}
        ]

        response = self.format_cr(self.cr.aggregate(query))
        response = self.unlist(response)

        turnos_db = response.get('turnos', [])
        turno_seleccionado = None
        min_diff_seconds = None

        if not turnos_db:
             turnos_db = []

        candidates_list = []
        for turno in turnos_db:
            candidates_list.append(turno)

        dt_inicio = dt_inicio.replace(microsecond=0)
        all_candidates_processed = []

        for turno in candidates_list:
            start_str = turno.get('hora_inicio')
            if not start_str: continue

            if len(start_str.split(':')) == 2:
                start_str += ":00"

            try:
                t_start = datetime.strptime(start_str, "%H:%M:%S").time()
            except ValueError:
                continue

            date_candidates = [
                datetime.combine(dt_inicio.date() - timedelta(days=1), t_start),
                datetime.combine(dt_inicio.date(), t_start),
                datetime.combine(dt_inicio.date() + timedelta(days=1), t_start)
            ]

            ingreso_maximo_min = int(turno.get('ingreso_maximo', 0) or 0)

            for start_dt in date_candidates:
                delta = dt_inicio - start_dt
                delta_seconds = delta.total_seconds()

                is_valid = False

                if delta_seconds < 0:
                    if abs(delta_seconds) <= (ingreso_maximo_min * 60):
                        is_valid = True
                else:
                    if delta_seconds <= 12 * 3600:
                         is_valid = True

                if is_valid:
                    all_candidates_processed.append({
                        "turno": turno,
                        "diff": abs(delta_seconds),
                        "start_dt": start_dt
                    })

        if all_candidates_processed:
            best = min(all_candidates_processed, key=lambda x: x['diff'])
            turno_seleccionado = best['turno']

        if not turno_seleccionado:
            for nome, datos in default_shifts.items():
                start_str = datos["start"]
                if len(start_str.split(':')) == 2: start_str += ":00"
                t_start = datetime.strptime(start_str, "%H:%M:%S").time()

                dcs = [
                   datetime.combine(dt_inicio.date() - timedelta(days=1), t_start),
                   datetime.combine(dt_inicio.date(), t_start),
                   datetime.combine(dt_inicio.date() + timedelta(days=1), t_start)
                ]

                closest = min(dcs, key=lambda d: abs((d - dt_inicio).total_seconds()))
                diff = abs((dt_inicio - closest).total_seconds())

                if min_diff_seconds is None or diff < min_diff_seconds:
                    min_diff_seconds = diff
                    turno_seleccionado = {**datos, "nombre_horario": nome}

        if turno_seleccionado:
            response.update({
                'hora_inicio': turno_seleccionado.get('hora_inicio') or turno_seleccionado.get('start'),
                'hora_fin': turno_seleccionado.get('hora_fin') or turno_seleccionado.get('end'),
                'nombre_horario': turno_seleccionado.get('nombre_horario'),
                'tolerancia_retardo': turno_seleccionado.get('tolerancia_retardo') or turno_seleccionado.get('tolerance', 0),
                'retardo_maximo': turno_seleccionado.get('retardo_maximo') or turno_seleccionado.get('max_delay', 0),
                'turno': turno_seleccionado.get('nombre_horario'),
            })
            if 'turnos' in response:
                del response['turnos']
        else:
             response['turno'] = 'sin_registro'
        return response

    def calculate_status(self, hora_inicio, guard_data):
        dt_inicio = datetime.strptime(hora_inicio, "%Y-%m-%d %H:%M:%S")
        minutos_inicio = dt_inicio.hour * 60 + dt_inicio.minute
        segundos_inicio = dt_inicio.second

        turno_inicio = guard_data.get('hora_inicio', '00:00:00')
        dt_turno_inicio = datetime.strptime(turno_inicio, "%H:%M:%S")
        minutos_turno_inicio = dt_turno_inicio.hour * 60 + dt_turno_inicio.minute
        segundos_turno_inicio = dt_turno_inicio.second

        tolerancia = int(guard_data.get('tolerancia_retardo', 0))
        retardo_maximo = int(guard_data.get('retardo_maximo', 0))

        delta_seconds = (minutos_inicio * 60 + segundos_inicio) - (minutos_turno_inicio * 60 + segundos_turno_inicio)
        minutos_retraso = delta_seconds / 60.0

        if minutos_retraso <= tolerancia:
            return "presente"
        elif tolerancia < minutos_retraso <= retardo_maximo:
            return "retardo"
        elif minutos_retraso > retardo_maximo:
            return "falta_por_retardo"
        else:
            return "presente"

    def check_in_manual(self, answers, user_id, timezone):
        #! Se cierra cualquier turno anterior que este abierto
        self.verify_guard_status(user_id, timezone)

        if answers.get(self.f['start_shift']):
            fecha_actual = answers.get(self.f['start_shift'])
        else:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            fecha_actual = now.strftime('%Y-%m-%d %H:%M:%S')

        answers.update({
            self.f['start_shift']: fecha_actual,
            self.f['option_checkin']: 'cerrar_turno',
        })

        #! Se obtiene la informacion del guardia como Horario y Turno en el que esta haciendo su check in
        location = answers.get(self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID, {}).get(self.f['location'], '')
        hora_inicio = answers.get(self.f['start_shift'], '')
        employee_data = self.get_guard_data(user_id, location, hora_inicio)
        answers.update({
            self.f['dias_libres']: employee_data.get('dias_libres', []),
            self.f['nombre_horario']: employee_data.get('nombre_horario', ''),
            self.f['hora_entrada']: employee_data.get('hora_inicio', ''),
            self.f['hora_salida']: employee_data.get('hora_fin', ''),
            self.f['tolerancia_retardo']: employee_data.get('tolerancia_retardo', 0),
            self.f['retardo_maximo']: employee_data.get('retardo_maximo', 0),
        })

        #! Se calcula status de la llegada del guardia
        status = self.calculate_status(hora_inicio, employee_data)
        answers.update({
            self.f['status_turn']: status,
        })
        return answers

    def get_last_check_in(self, guard_id, location, area):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.REGISTRO_ASISTENCIA,
                "user_id": guard_id,
                f"answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.Location.f['area']}": area,
                f"answers.{self.f['start_shift']}": {"$exists": True},
                f"answers.{self.f['end_shift']}": {"$exists": False},
            }},
            {"$sort": {"created_at": -1}},
            {"$limit": 1},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "answers": 1,
            }},
        ]
        response = self.format_cr(self.cr.aggregate(query))
        response = self.unlist(response)
        return response

    def delete_registro_asistencia(self, folio):
        """Elimina un registro de REGISTRO_ASISTENCIA por su folio."""
        if not folio:
            raise Exception("Folio is required to delete a registro.")
        response = self.cr.delete_one({
            'form_id': self.REGISTRO_ASISTENCIA,
            'folio': folio
        })
        return response.deleted_count > 0

    def check_out_manual(self, answers, user_id, timezone, record_id):
        last_check_in = self.get_last_check_in(user_id, answers.get(self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID, {}).get(self.Location.f['location'], ''), answers.get(self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID, {}).get(self.Location.f['area'], ''))
        if last_check_in and record_id != str(last_check_in.get('_id', '')):
            answers.update({
                self.f['start_shift']: last_check_in.get('fecha_inicio_turno', ''),
                self.f['comment_checkin']: last_check_in.get('comment_checkin', ''),
                self.f['image_checkin']: last_check_in.get('image_checkin', []),
                self.f['dias_libres']: last_check_in.get('dias_libres_empleado', []),
                self.f['nombre_horario']: last_check_in.get('nombre_horario', ''),
                self.f['hora_entrada']: last_check_in.get('hora_entrada', ''),
                self.f['hora_salida']: last_check_in.get('hora_salida', ''),
                self.f['tolerancia_retardo']: last_check_in.get('tolerancia_retardo', ''),
                self.f['retardo_maximo']: last_check_in.get('retardo_maximo', ''),
                self.f['status_turn']: last_check_in.get('status_turn', ''),
            })
            self.delete_registro_asistencia(last_check_in.get('folio', ''))

        if answers.get(self.f['end_shift']):
            fecha_actual = answers.get(self.f['end_shift'])
        else:
            tz = pytz.timezone(timezone)
            now = datetime.now(tz)
            fecha_actual = now.strftime('%Y-%m-%d %H:%M:%S')

        answers.update({
            self.f['end_shift']: fecha_actual,
        })
        return answers

    def set_work_hours(self, answers, start_time, end_time):
        dt_inicio = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        dt_cierre = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        delta = dt_cierre - dt_inicio
        horas = delta.total_seconds() / 3600
        answers.update({
            self.f['horas_trabajadas']: round(horas, 2),
        })
        return answers

    # ============================================
    # Check de ubicacion de rondin (migrado de check_ubicacion_rondin.py)
    # ============================================

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
                    'form_id': self.CONFIGURACION_RECORRIDOS_FORM,
                    f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": ubicacion,
                    f"answers.{self.f['grupo_de_areas_recorrido']}": {'$exists': True}
                }
            },
            {'$unwind':f"$answers.{self.f['grupo_de_areas_recorrido']}"},
            {'$project':
                {
                    'area':f"$answers.{self.f['grupo_de_areas_recorrido']}.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area']}",
                    'nombre_recorrido':f"$answers.{self.f['nombre_del_recorrido']}",
                    'ubicacion_recorrido': f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_recorrido']}"
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
        """
        tz = pytz.timezone('America/Mexico_City')
        today = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')
        rondin = self.unlist(rondin)
        format_id_rondin = rondin.get('_id', '')
        rondin_en_progreso = True
        answers={}

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
                            self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                                self.f['nombre_area']: area_rondin
                            },
                            self.f['fecha_hora_inspeccion_area']: today,
                            self.f['foto_evidencia_area_rondin']: data_rondin.get(self.f['foto_evidencia_area'], []),
                            self.f['comentario_area_rondin']: data_rondin.get(self.f['comentario_check_area'], ''),
                            self.f['url_registro_rondin']: f"https://app.linkaform.com/#/records/detail/{record_id}"
                        }
                    else:
                        obj = {
                            self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
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
            inc = incidencia.get(self.f['incidencia'])
            if inc:
                incidencia.pop(self.f['incidencia'], None)
                incidencia.update({
                    self.LISTA_INCIDENCIAS_CAT_OBJ_ID: {
                        self.f['incidencia']: inc
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

        if answers:
            res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.BITACORA_RONDINES, record_id=[format_id_rondin])
            return res

    def get_areas_recorrido_by_record(self, record_id):
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.CONFIGURACION_RECORRIDOS_FORM,
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

        if not record_id:
            raise Exception("No se encontró un record_id válido para obtener las áreas del recorrido.")

        areas_recorrido = self.get_areas_recorrido_by_record(record_id)

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
            self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
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
                    self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                        self.f['nombre_area']: area.get('incidente_area', '')
                    },
                })

        answers[self.f['bitacora_rondin_incidencias']] = data_rondin.get(self.f['grupo_incidencias_check'], [])

        metadata.update({'answers':answers})
        res = self.lkf_api.post_forms_answers(metadata)
        return res

    def get_employee_name(self, user_id):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.Employee.CONF_AREA_EMPLEADOS,
                f"answers.{self.Employee.EMPLOYEE_OBJ_ID}.{self.mf['id_usuario']}": user_id
            }},
            {"$project": {
                "_id": 0,
                "employee_name": f"$answers.{self.Employee.EMPLOYEE_OBJ_ID}.{self.mf['nombre_empleado']}"
            }},
            {"$limit": 1}
        ]

        employee_name = self.unlist(self.format_cr(self.cr.aggregate(query)))
        employee_name = employee_name.get('employee_name', '')
        if not employee_name:
            employee_name = 'Nombre no registrado'
        return employee_name

    def format_grupo_incidencias(self, grupo_incidencias, answers, folio):
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
                self.f['folio_del_check']: folio,
                self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID: {
                    self.mf['nombre_empleado']: employee_name
                },
                self.incidence_fields['fecha_hora_incidencia']: fecha_actual,
                self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                    self.f['incidente_location']: self.unlist(answers.get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['incidente_location'], [])),
                    self.f['incidente_area']: self.unlist(answers.get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['incidente_area'], []))
                },
                self.incidence_fields['tipo_incidencia']: incidente,
                self.incidence_fields['comentario_incidente_bitacora']: incidencia.get(self.f['comentario_incidente_bitacora'], ''),
                self.incidence_fields['evidencia_incidencia']: incidencia.get(self.f['incidente_evidencia'], []),
                self.incidence_fields['documento_incidencia']: incidencia.get(self.f['incidente_documento'], []),
                self.incidence_fields['prioridad_incidencia']: incidencia.get(self.incidence_fields['prioridad_incidencia'], 'baja'),
                self.incidence_fields['notificacion_incidencia']: incidencia.get(self.incidence_fields['notificacion_incidencia'], 'no'),
            })
        return format_grupo_incidencias

    def create_incidence_record(self, answers):
        """
        Crea una incidencia en la bitacora de incidencias a partir de un dict de answers ya formateado
        (distinto de create_incidence, que transforma datos crudos del formulario de incidencias).
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
                "form_id": self.Employee.EMPLEADOS,
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
                                f"$answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}",
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

    #! Utils functions ==========
    def parse_date_for_sorting(self, date_str):
        if not date_str or not date_str.strip():
            return datetime.max
        try:
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.max
    #! ===========================

    def create_cache(self, record_id, user_name, location, folio, timestamp, answers):
        """
        Create a cache entry for a rondin.
        """
        data = {}
        data.update({
            '_id': ObjectId(record_id),
            'user_name': user_name,
            'location': location,
            'folio': folio,
            'timestamp': timestamp,
            'random': random.random(),
            'check_data': answers,
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

    def get_locations_cache(self, cache):
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
        now = time_module.time()

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

    def search_active_bitacora_by_rondin(self, recorridos, location, user_name):
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
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.USUARIOS_OBJ_ID}.{self.f['new_user_complete_name']}": user_name,
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

    def search_closed_bitacora_by_hour(self, location, search_hour, user_name):
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
                f"answers.{self.USUARIOS_OBJ_ID}.{self.f['new_user_complete_name']}": user_name,
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

    def update_bitacora(self, cache, rondin, current_record, timezone, user_id, user_email, timestamp=None):
        """
        Recibe: Las answers del check de ubicacion, el area que se hice check de ubicacion y el registro de rondin
        Retorna: La respuesta de la api al hacer el patch de un registro
        Error: La respuesta de la api al hacer el patch de un registro
        """
        tz = pytz.timezone(timezone)
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
                    self.f['incidencia']: item.get('incidencia', ''),
                },
                self.f['incidente_open']: item.get('incidente_open', ''),
                self.f['comentario_incidente_bitacora']: item.get('comentario_incidente_bitacora', ''),
                self.f['incidente_accion']: item.get('incidente_accion', ''),
                self.f['incidente_evidencia']: item.get('incidente_evidencia', []),
                self.f['incidente_documento']: item.get('incidente_documento', []),
            }
            incidencias_list.append(new_item)

        if not rondin.get('fecha_inicio_rondin'):
            rondin['fecha_inicio_rondin'] = timestamp and datetime.fromtimestamp(timestamp, tz).strftime('%Y-%m-%d %H:%M:%S')

        conf_recorrido = {}
        for key, value in rondin.items():
            if key == 'new_user_complete_name':
                answers[self.USUARIOS_OBJ_ID] = {
                    self.f['new_user_complete_name']: value,
                    self.f['new_user_id']: [user_id],
                    self.f['new_user_email']: [user_email]
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

        answers[self.CONFIGURACION_RECORRIDOS_OBJ_ID] = conf_recorrido
        answers[self.f['fecha_fin_rondin']] = today if current_record.get(self.f['check_status'], '') == ['finalizado', 'realizado', 'cerrado'] else ''

        if current_record.get('answers', {}).get(self.f['check_status']) == 'finalizado':
            answers[self.f['estatus_del_recorrido']] = 'realizado'
        elif current_record.get('answers', {}).get(self.f['check_status']) == 'continuar_siguiente_punto_de_inspección':
            answers[self.f['estatus_del_recorrido']] = 'en_proceso'

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

    def create_bitacora(self, winner, recorridos, location, timezone, user_name, user_id, user_email, check_area, closed=False):
        """
        Create a bitacora entry from cache data.
        """
        nombre_del_recorrido = ""
        ubicacion_del_recorrido = ""
        id_del_recorrido = ""
        for recorrido in recorridos:
            nombre_del_recorrido = recorrido.get('nombre_recorrido')
            ubicacion_del_recorrido = recorrido.get('ubicacion_recorrido')
            id_del_recorrido = recorrido.get('_id')

        if id_del_recorrido:
            areas_recorrido = self.get_areas_recorrido(id_del_recorrido)
        else:
            areas_recorrido = []
            nombre_del_recorrido = 'Recorrido Automático'
            ubicacion_del_recorrido = winner.get('location', location)

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

        tz = pytz.timezone(timezone)

        answers[self.f['fecha_programacion']] = winner.get('timestamp') and datetime.fromtimestamp(winner.get('timestamp'), tz).strftime('%Y-%m-%d %H:%M:%S')
        answers[self.f['fecha_inicio_rondin']] = winner.get('timestamp') and datetime.fromtimestamp(winner.get('timestamp'), tz).strftime('%Y-%m-%d %H:%M:%S')
        answers[self.USUARIOS_OBJ_ID] = {
            self.f['new_user_complete_name']: user_name,
            self.f['new_user_id']: [user_id],
            self.f['new_user_email']: [user_email],
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
            if not area.get('incidente_area') == check_area:
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

        res = self.lkf_api.post_forms_answers(metadata)
        return res

    def search_rondin_by_area(self, location, check_area):
        """
        Search for a rondin by location and check_area in form Configuracion de Recorridos.
        """
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.CONFIGURACION_DE_RECORRIDOS_FORM,
                f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.f['grupo_de_areas_recorrido']}": {'$exists': True}
            }},
            {'$unwind': f"$answers.{self.f['grupo_de_areas_recorrido']}"},
            {'$project': {
                '_id': 1,
                'match_area': f"$answers.{self.f['grupo_de_areas_recorrido']}.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area']}",
                'nombre_recorrido': f"$answers.{self.f['nombre_del_recorrido']}",
                'ubicacion_recorrido': f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['ubicacion_recorrido']}"
            }},
            {'$match': {
                'match_area': check_area
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

    def update_check_ubicacion(self, record_id):
        answers = {self.f["status_check_ubicacion"]: 'Area no configurada'}
        response = self.lkf_api.patch_multi_record(answers=answers, form_id=self.CHECK_UBICACIONES, record_id=[record_id])
        return response.get('status_code')

    def search_closed_bitacora_by_time(self, location, user_name, search_dt, window_seconds=1200):
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
            return []

        fecha_field = f"answers.{self.f['fecha_inicio_rondin']}"
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.USUARIOS_OBJ_ID}.{self.f['new_user_complete_name']}": user_name,
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

    #! ============================================
    #! Rondines: API de gestion de recorridos (migrado de rondines.py)
    #! ============================================

    def _extract_record_id_from_url(self, registro_padre_value):
        """
        registro_padre puede ser URL completa:
        https://host/#/records/detail/6612abc123...
        o directo el _id. Retorna solo el ID.
        """
        if not registro_padre_value:
            return None
        if '/' in str(registro_padre_value):
            return registro_padre_value.rstrip('/').split('/')[-1]
        return registro_padre_value

    def _get_child_records(self, registro_padre):
        """
        Busca en MongoDB todos los hijos que apunten a este parent_id en registro_padre.
        """
        query = {
            'form_id': self.BITACORA_RONDINES,
            'deleted_at': {'$exists': False},
            f'answers.{self.rondin_keys["registro_padre"]}': registro_padre,
        }
        return list(self.cr.find(query))

    def rondin_asignado_a(self, asignado_a):
        """
        Crea grupo repetitivo de personas asignadas a un rondin.
        args:
            asignado_a (str): 'responsable_en_turno' o nombre de un empleado
        return:
            lista con elementos para el grupo asignado a del rondin
        """
        employee = {}
        visita_set = {}

        if not asignado_a or asignado_a == 'responsable_en_turno':
            # Usa el empleado del usuario actual (igual que access_pass_vista_a)
            employee = self.Employee.get_employee_data(
                user_id=self.user['user_id'], get_one=True
            )
            visita_set = self.visita_a_set_format(employee)
            return [visita_set] if visita_set else []

        # Es un nombre de persona específica
        employee = self.Employee.get_employee_data(name=asignado_a, get_one=True)
        visita_set = self.visita_a_set_format(employee)

        if visita_set and employee:
            return [visita_set]
        else:
            # Fallback: inserta solo el nombre si no encuentra en catálogo
            return [{
                self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID: {
                    self.mf['nombre_empleado']: asignado_a
                }
            }]

    def claim_rondin(self, record_id):
        """
        El usuario actual reclama este rondin.
        1. Determina si es padre o hijo
        2. Obtiene todos los registros relacionados (padre + hermanos, o hijos)
        3. Borra el inbox de CouchDB de los otros usuarios
        """
        # --- 1. Obtener el registro actual desde MongoDB ---
        record = self.get_record_by_id(record_id)
        if not record:
            return False, "Registro no encontrado"

        answers = record.get('answers', {})
        registro_padre = answers.get(self.rondin_keys['registro_padre'])

        # --- 2. Determinar familia de registros ---
        if registro_padre:
            # Es un hijo → buscar padre y todos los hermanos
            parent_id = self._extract_record_id_from_url(registro_padre)
            siblings = self._get_child_records(registro_padre)
            related_records = [r for r in siblings if str(r['_id']) != str(record_id)]
            parent_record = self.get_record_by_id(parent_id)
            if parent_record:
                related_records.append(parent_record)
        else:
            # Es padre → buscar todos sus hijos
            children = self._get_child_records(record_id)
            related_records = [r for r in children if str(r['_id']) != str(record_id)]

        # --- 3. Bloqueo atómico ---
        STATUS_FIELD = f'answers.{self.mf["estatus_del_recorrido"]}'

        related_ids = [r['_id'] for r in related_records]
        all_ids = related_ids + [record['_id']]

        if related_ids:
            # TODO utilizar session de mongo para que sea una transaccion ACID
            # Paso 1: Obtener exactamente cuáles están en 'programado'
            programados = list(self.cr.find(
                {'_id': {'$in': all_ids}, STATUS_FIELD: 'programado'},
                {'_id': 1}  # solo necesitamos el _id
            ))
            programados_ids = [r['_id'] for r in programados]

            if len(programados_ids) != len(all_ids):
                return False, "El rondin ya fue reclamado por otro usuario"

            #Paso 2: update_many solo sobre los que YO encontré en 'programado'
            result = self.cr.update_many(
                {'_id': {'$in': programados_ids}, STATUS_FIELD: 'programado'},
                {'$set': {STATUS_FIELD: 'reclamado'}}
            )

        # --- 4. El registro reclamado pasa a en_proceso ---
        self.cr.update_one(
            {'_id': ObjectId(record['_id'])},
            {'$set': {STATUS_FIELD: 'en_proceso'}}
        )

        if related_records:
            related_ids = [str(r['_id']) for r in related_records]
            self.lkf_api.patch_multi_record(
                answers={self.rondin_keys['status']: 'reclamado'},
                form_id=self.BITACORA_RONDINES,
                record_id=related_ids,
            )

        self.lkf_api.patch_multi_record(
            answers={self.mf['estatus_del_recorrido']: 'en_proceso'},
            form_id=self.BITACORA_RONDINES,
            record_id=[str(record['_id'])],
        )

        return True, {'claimed': record_id, 'unassinged_records': len(related_ids)}

    def delete_claimed_record(self, answers, current_record):
        usuario_obj = answers.get(self.USUARIOS_OBJ_ID, {})

        user_id = self.unlist(usuario_obj.get(self.mf['id_usuario'], []))

        if not user_id:
            return True

        rel_record_id = str(current_record['_id'])
        try:
            db_name = f"clave_{user_id}"
            couch_db = self.get_couch_user_db(db_name)
            couch_record = couch_db.get(rel_record_id)
            if couch_record:
                couch_db.delete(couch_record)
        except Exception as e:
            print(f"===== log: error al borrar registro reclamado en couch. user_id={user_id} record_id={rel_record_id} error={e}")
        return True

    def create_recorrido_rondin(self, rondin_data: dict = {}):
        """Crea un rondin con los datos proporcionados.
        Args:
            rondin_data (dict): Un diccionario con los datos del rondin.
        Returns:
            response: La respuesta de la API de Linkaform al crear el rondin.
        """
        answers = {}
        tipo_asignacion = rondin_data.get('tipo_asignacion', 'responsable_en_turno')
        ubicacion_result = self.get_ubicacion_geolocation(location=rondin_data.get('ubicacion', ''))
        rondin_data['ubicacion'] = ubicacion_result if ubicacion_result else rondin_data.get('ubicacion', '')
        areas_result = self.get_areas_details(areas_list=rondin_data.get('areas', []))
        rondin_data['areas'] = areas_result if areas_result else rondin_data.get('areas', [])
        for key, value in rondin_data.items():
            if key == 'ubicacion':
                if isinstance(value, dict):
                    answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {
                        self.Location.f['location']: value.get('location', ''),
                        self.f['address_geolocation']: value.get('geolocation', [])
                    }
                else:
                    # Llegó como string directo (geolocation no encontró nada)
                    answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {
                        self.Location.f['location']: value,
                        self.f['address_geolocation']: []
                    }
            elif key == 'area':
                if value:
                    answers[self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID] = {
                        self.mf['nombre_area_salida']: value
                    }
            elif key == 'grupo_asignado':
                answers[self.GRUPOS_CAT_OBJ_ID] = {
                    self.rondin_keys[key]: value
                }
            elif key == 'areas':
                areas_list = []
                for area in value:
                    if isinstance(area, dict):
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
                    else:
                        # Llegó como string directo (get_areas_details no encontró nada)
                        area_dict = {
                            self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                                self.Location.f['area']: area,
                                self.f['geolocalizacion_area_ubicacion']: [],
                                self.f['foto_area']: [],
                                self.f['area_tag_id']: []
                            }
                        }
                    areas_list.append(area_dict)
                answers[self.rondin_keys[key]] = areas_list
            elif key == "cron_id":
                answers[self.rondin_keys['cron_id']] = value
            elif key == 'sucede_recurrencia' and ('dia_del_mes' in value or 'mes' in value):
                actual_day = datetime.now().day
                answers[self.rondin_keys['que_dia_del_mes']] = int(actual_day)
                answers[self.rondin_keys[key]] = value
            elif value == '':
                pass
            elif key == 'tipo_rondin':
                answers[self.rondin_keys[key]] = value.lower()
            elif key == 'tipo_asignacion':
                answers[self.rondin_keys['tipo_asignacion']] = value
            elif key == 'asignado_a':
                if not value:
                    pass
                elif tipo_asignacion == 'grupo':
                    grupo_asignado = value[0] if isinstance(value, list) else value
                    answers[self.GRUPOS_CAT_OBJ_ID] = {
                        self.rondin_keys['grupo_asignado']: grupo_asignado,
                    }
                elif tipo_asignacion == 'persona_especifica':
                    nombre = value[0] if isinstance(value, list) else value
                    answers[self.rondin_keys['grupo_asignado_a']] = self.rondin_asignado_a(nombre)
                else:
                    # responsable_en_turno
                    answers[self.rondin_keys['grupo_asignado_a']] = self.rondin_asignado_a(value)
            else:
                answers[self.rondin_keys[key]] = value
        response = self.create_register(
            module='Accesos',
            process='Creacion de un rondin',
            action='rondines',
            file='accesos/app.py',
            form_id=self.CONFIGURACION_RECORRIDOS_FORM,
            answers=answers
        )
        return response

    def create_incidencia_by_rondin(self, data):
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

        answers = {
            self.rondin_keys['accion_recurrencia']: 'eliminar'
        }
        response = self.lkf_api.patch_multi_record(answers=answers, form_id=self.CONFIGURACION_RECORRIDOS_FORM, folios=[folio,])
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

        full_rondin = self.get_rondin_by_id(record_id)

        answers = {}
        answers[self.rondin_keys['grupo_asignado_rondin']] = []

        for key, value in full_rondin.items():
            if key == 'nombre_del_rondin':
                answers.update({f"{self.rondin_keys['nombre_rondin']}":value})
            elif key == 'ubicacion':
                answers[self.Location.UBICACIONES_CAT_OBJ_ID]={
                    self.rondin_keys['ubicacion']: full_rondin.get('ubicacion', ''),
                    self.f['address_geolocation']: [full_rondin.get('ubicacion_geolocation',{})]
                }
            elif key == 'grupo_asignado_rondin':
                answers[self.rondin_keys['grupo_asignado_rondin']].append({
                    self.rondin_keys['grupo_asignado']: full_rondin.get('grupo_asignado', ""),
                    self.rondin_keys['id_grupo']: full_rondin.get('id_grupo', ""),
                })
            else:
                if key in self.rondin_keys:
                    answers.update({
                        f"{self.rondin_keys[key]}": value
                    })

        areas_list = []
        if areas:
            for a in areas:
                obj = {f"{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}":{
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
        res = self.net.patch_forms_answers(metadata)
        return res

    def format_rondin_by_id(self, data):
        fotos_de_areas = []
        puntos_de_control = []

        # Normaliza cada area a las llaves que legacy realmente expone
        # ('rondin_area'/'area_tag_id', nunca 'incidente_area'/
        # 'tag_id_area_ubicacion') antes de leerlas o regresarlas -- ver nota
        # de colision de self.f mas abajo. Confirmado contra prod real:
        # legacy usa 'rondin_area' para el nombre pero 'area_tag_id' (no
        # 'tag_id_area_ubicacion') para el array de tag ids -- las dos
        # colisiones no se resuelven en la misma direccion.
        for item in data.get('areas', []):
            if 'incidente_area' in item:
                item.setdefault('rondin_area', item.pop('incidente_area'))
            if 'tag_id_area_ubicacion' in item:
                item.setdefault('area_tag_id', item.pop('tag_id_area_ubicacion'))

        for item in data.get('areas', []):
            foto_area_data = item.get('foto_area', [])
            foto_url = ""
            if foto_area_data:
                primer_elemento = foto_area_data[0]
                if isinstance(primer_elemento, list) and len(primer_elemento) > 0:
                    foto_url = primer_elemento[0].get('file_url', '')
                elif isinstance(primer_elemento, dict):
                    foto_url = primer_elemento.get('file_url', '')

            # NOTA: 'area_tag_id'/'tag_id_area_ubicacion' y 'rondin_area'/'incidente_area'
            # son alias del mismo field id (ver self.f en models.py). En legacy cada script
            # tenia su propio self.f aislado y no colisionaban; en la arquitectura nueva
            # self.f es compartido entre todos los scripts de la cuenta, y el override de
            # accesos_service.py (que agrega 'incidente_area'/'tag_id_area_ubicacion' para
            # check_ubicacion_rondin.py) puede ganar el mapeo inverso usado por format_cr/
            # _labels segun el orden de insercion. Se leen ambas variantes para no depender
            # de ese orden.
            area_tag_id_raw = item.get('area_tag_id') or item.get('tag_id_area_ubicacion') or []
            area_id = area_tag_id_raw[0] if len(area_tag_id_raw) > 0 else ""
            nombre = item.get('rondin_area') or item.get('incidente_area') or ''
            geo_list = item.get('geolocalizacion_area_ubicacion', [])
            geo = geo_list[0] if geo_list else {}

            if foto_url:
                fotos_de_areas.append({
                    "id": area_id,
                    "nombre_area": nombre,
                    "foto_area": foto_area_data,
                    "geolocation_area": geo,
                })

            puntos_de_control.append({
                "id": area_id,
                "nombre_area": nombre,
                "geolocation_area": geo,
                "foto_area": foto_area_data,
            })

        data.update({
            "recurrencia": data.get('recurrencia').replace('_', ' ').title() if data.get('recurrencia') else 'No Recurrente',
            "estatus_rondin": data.get('estatus_rondin').replace('_', ' ').title() if data.get('estatus_rondin') else 'No Especificado',
            "ubicacion_geolocation": (data.get('ubicacion_geolocation') or [{}])[0],
            "images_data": fotos_de_areas,
            "map_data": puntos_de_control,
        })
        return data

    def format_incidencias_rondines(self, data, area):
        format_data = []
        for item in data:
            incidencias = item.get('incidencias_rondin', [])
            for index, incidencia in enumerate(incidencias):
                # NOTA: 'nombre_area_salida'/'area' son alias del mismo field id
                # en self.mf (663fb45992f2c5afcfe97ca8, ver colision de self.f/
                # self.mf compartido explicada en format_rondin_by_id).
                incidencia_area_nombre = incidencia.get('area_salida',incidencia.get('nombre_area_salida',incidencia.get('area',''))) 
                if area:
                    if incidencia_area_nombre != area:
                        continue
                format_item = {
                    "id": item.get('_id',''),
                    "folio": item.get('folio',''),
                    "ref_number": index,
                    "ubicacion_incidente": item.get('ubicacion', ''),
                    "area_incidente": incidencia_area_nombre,
                    "nombre_del_recorrido": item.get('nombre_recorrido', ''),
                    "fecha_hora_incidente": incidencia.get('fecha_hora_incidente_bitacora', ''),
                    "categoria": incidencia.get('categoria', 'General'),
                    "subcategoria": incidencia.get('sub_categoria', 'General'),
                    # NOTA: 'incidencia'/'tipo_de_incidencia' e 'incidente_accion'/
                    # 'incidente_comentario' son alias del mismo field id respectivamente
                    # (ver comentario en format_rondin_by_id sobre la colision de self.f
                    # compartido). accesos_service.py agrega 'tipo_de_incidencia' e
                    # 'incidente_comentario' despues de que models.py define 'incidencia'
                    # e 'incidente_accion', ganando el mapeo inverso segun orden de merge.
                    "incidente": incidencia.get('incidencia') or incidencia.get('tipo_de_incidencia') or incidencia.get('incidente_open', ''),
                    "accion_tomada": incidencia.get('incidente_accion') or incidencia.get('incidente_comentario', ''),
                    "comentarios": incidencia.get('comentario_incidente_bitacora', ''),
                    "evidencias": incidencia.get('incidente_evidencia', []),
                    "documentos": incidencia.get('incidente_documento', []),
                    "link": incidencia.get('link', ""),
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
                # NOTA: 'rondin_area'/'incidente_area' son alias del mismo field id
                # (ver comentario en format_rondin_by_id). Se lee ambos por la misma
                # razon: el orden de merge de self.f puede hacer ganar cualquiera.
                "nombre_area": item.get('rondin_area') or item.get('incidente_area') or '',
                "fecha_y_hora_check": item.get('fecha_hora_inspeccion_area', ''),
                "comentario_check": item.get('comentario_area_rondin', ''),
                "url_check": item.get('url_registro_rondin', ''),
                "fotos_check": item.get('foto_evidencia_area_rondin', []),
            }
            format_data.append(format_item)
        return format_data

    def format_bitacora_rondines(self, data, timezone=None):
        if timezone:
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
            except Exception:
                now = datetime.now()
        else:
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
                            hora_valida,
                            timezone=timezone
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
                        hora_valida,
                        timezone=timezone
                    )

                    resumen_estados.append({
                        "dia": dia,
                        "estado": estado_bitacora,
                        "record_id": bitacora_id if estado_bitacora not in ["none", "no_aplica"] else "",
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

    def format_bitacoras_mes(self, bitacoras_data, nombre_recorrido, timezone=None):
        if timezone:
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
            except Exception:
                now = datetime.now()
        else:
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

    def format_check_by_id(self, data: dict, record_id: str, timezone=None):
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
                "incidente": incidencia.get('incidencia', incidencia.get('incidente_open', '')),
                "accion_tomada": incidencia.get('incidente_accion', ''),
                "comentarios": incidencia.get('comentario_incidente_bitacora', ''),
                "evidencias": incidencia.get('incidente_evidencia', []),
                "documentos": incidencia.get('incidente_documento', []),
            }
            incidencias_area.append(incidencia_formateada)

        checks_mes = self.get_rondin_checks(data.get('rondin_area', ''), data.get('ubicacion', ''), data.get('nombre_recorrido', ''), record_id, timezone=timezone)

        format_data = {
            'area': data.get('rondin_area', ''),
            'checks_mes': checks_mes,
            'fotos': [{'file_name': item.get('file_name', ''),'file_url': item.get('file_url', '')} for item in data.get('foto_evidencia_area_rondin', [])],
            'hora_de_check': data.get('fecha_hora_inspeccion_area', ''),
            'ubicacion': data.get('ubicacion', ''),
            'tiempo_traslado': data.get('duracion_traslado_area', ''),
            'comentarios': data.get('comentario_area_rondin', ''),
            'incidencias': incidencias_area,
        }
        return format_data

    def format_rondin_checks(self, checks_data, rec_id, timezone=None):
        """
        Formatea los checks del mes en el formato requerido por el frontend.

        Args:
            checks_data (list): Lista de checks del mes con sus incidencias
            rec_id (str): Id del check actualmente visualizado

        Returns:
            dict: Datos formateados con estructura de estados por día
        """
        if timezone:
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
            except Exception:
                now = datetime.now()
        else:
            now = datetime.now()
        current_year = now.year
        current_month = now.month
        days_in_month = calendar.monthrange(current_year, current_month)[1]

        # Crear diccionario para mapear días a lista de checks
        checks_por_dia = {}
        for check in checks_data:
            created_at = check.get('created_at')
            if isinstance(created_at, str):
                try:
                    # Intentar parsear con hora y minuto primero
                    fecha_check = datetime.strptime(created_at, '%Y-%m-%d %H:%M')
                except ValueError:
                    try:
                        # Fallback al formato solo fecha
                        fecha_check = datetime.strptime(created_at, '%Y-%m-%d')
                    except ValueError:
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

            # Guardar el check
            if dia not in checks_por_dia:
                checks_por_dia[dia] = []

            # Si created_at es datetime, formatearlo a string para consistencia en la respuesta
            created_at_str = created_at
            if isinstance(created_at, datetime):
                created_at_str = created_at.strftime('%Y-%m-%d %H:%M')

            checks_por_dia[dia].append({
                'estado': estado,
                'created_at': created_at_str,
                'record_id': str(check.get('_id', ''))
            })

        # Crear lista de estados para todos los días del mes
        estados = []
        for dia in range(1, days_in_month + 1):
            if dia in checks_por_dia:
                # Ordenar por fecha de creación
                checks_dia = sorted(checks_por_dia[dia], key=lambda x: x['created_at'])
                # El estado principal del día es el del último check
                ultimo_check = self.unlist([check for check in checks_dia if check.get('record_id') == rec_id]) or checks_dia[-1]
                estado = ultimo_check['estado']
                record_id = ultimo_check['record_id']
                registros = checks_dia
            else:
                # Determinar si es día pasado, presente o futuro
                fecha_dia = datetime(current_year, current_month, dia)
                if fecha_dia.date() < now.date():
                    estado = "no_inspeccionada"
                else:
                    estado = "none"
                record_id = ""
                registros = []

            estados.append({
                "dia": dia,
                "estado": estado,
                "record_id": record_id,
                "registros": registros
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

    def format_bitacora_record(self, record, area_details=False, timezone=None):
        areas = record.get("areas", [])
        if not isinstance(areas, list):
            areas = [areas] if areas else []
        areas_formateadas = []
        areas_default_images = {}
        areas_config = self.unlist(record.get('recorrido_config', []))
        if areas_config:
            areas_config = areas_config.get('areas_config', {})
            areas_default_images = {i.get('rondin_area', ''): i.get('foto_area', {}) for i in areas_config if i.get('foto_area')}
        for area in areas:
            area_con_contexto = {
                **area,
                "ubicacion": record.get("ubicacion", ""),
                "nombre_recorrido": record.get("nombre_recorrido", ""),
                "incidencias": record.get("incidencias", []),
            }
            record_id = str(area.get("url_registro_rondin", ""))
            detalle = self.format_check_by_id(area_con_contexto, record_id, timezone=timezone)
            if area_details:
                detalle = self.get_area_images([detalle], location=record.get("ubicacion", ""))
                detalle = detalle[0] if detalle else detalle
            areas_formateadas.append({
                "area": area.get("rondin_area", ""),
                "foto_default_area": self.unlist(areas_default_images.get(area.get('rondin_area', []))),
                "detalle": detalle,
            })

        incidencias = record.get("incidencias", [])
        if not isinstance(incidencias, list):
            incidencias = [incidencias] if incidencias else []

        incidencias_formateadas = []
        for inc in incidencias:
            incidencias_formateadas.append({
                "categoria": inc.get("categoria", ""),
                "subcategoria": inc.get("sub_categoria", ""),
                "incidente": inc.get("incidencia", ""),
                "area_incidente": inc.get("nombre_area_salida", ""),
                "fecha_hora_incidente": inc.get("fecha_hora_incidente_bitacora", ""),
                "accion_tomada": inc.get("incidente_accion", ""),
                "comentarios": inc.get("comentario_incidente_bitacora", ""),
                "evidencias": inc.get("incidente_evidencia", []),
                "documentos": inc.get("incidente_documento", []),
            })

        recorrido_config = record.get("recorrido_config", [])
        areas_config = recorrido_config[0].get("areas_config", []) if recorrido_config else []

        map_data = []
        for area_conf in areas_config:
            nombre = area_conf.get("rondin_area", "")
            tag_ids = area_conf.get("area_tag_id", [])
            geo_list = area_conf.get("geolocalizacion_area_ubicacion", [])
            foto_area = area_conf.get("foto_area", [])
            geo = geo_list[0] if geo_list else {}
            area_id = tag_ids[0] if tag_ids else nombre
            map_data.append({
                "id": area_id,
                "nombre_area": nombre,
                "geolocation_area": {
                    "latitude": geo.get("latitude", 0),
                    "longitude": geo.get("longitude", 0),
                },
                "foto_area": foto_area,
            })

        images_data = []
        for area in areas_formateadas:
            fotos = area.get("detalle", {}).get("fotos", [])
            for foto in fotos:
                images_data.append({
                    "id": area.get("area", ""),
                    "nombre_area": area.get("area", ""),
                    "foto_area": foto.get("file_url", ""),
                })

        format_checks_data = []
        checks_data = record.get('checks_data', [])
        for check in checks_data:
            new_item = {}
            new_item['fecha_check'] = check.get('fecha_hora_inspeccion_area', '')
            new_item['evidencias_check'] = check.get('foto_evidencia_area', [])
            new_item['comentarios_check'] = check.get('comentario_check_area', '')
            new_item['incidencias_check'] = check.get('grupo_incidencias_check', '')
            format_checks_data.append(new_item)

        return {
            "id": str(record.get("_id", "")),
            "folio": record.get("folio", ""),
            "created_at": str(record.get("created_at", "")),
            "updated_at": str(record.get("updated_at", "")),
            "ubicacion": record.get("ubicacion", ""),
            "nombre_recorrido": record.get("nombre_recorrido", ""),
            "asignado_a": record.get("asignado_a", ""),
            "tipo_rondin": record.get("tipo_rondin", ""),
            "fecha_hora_programada_inicio": record.get("fecha_hora_programada_inicio", ""),
            "fecha_hora_inicio": record.get("fecha_hora_inicio", ""),
            "fecha_hora_fin": record.get("fecha_hora_fin", ""),
            "estatus_recorrido": record.get("estatus_recorrido", ""),
            "duracion_rondin": record.get("duracion_rondin", ""),
            "motivo_cancelacion": record.get("motivo_cancelacion", ""),
            "comentario_general": record.get("comentario_general", ""),
            "comentarios_generales": record.get("comentarios_generales", []),
            "porcentaje_avance": record.get("porcentaje_avance", 0),
            "cantidad_areas_inspeccionadas": record.get("cantidad_areas_inspeccionadas", 0),
            "total_checks": len(areas),
            "areas": areas_formateadas,
            "incidencias": incidencias_formateadas,
            "images_data": images_data,
            "map_data": map_data,
            "checks_data": format_checks_data
        }

    def get_bitacora(self, date_from=None, date_to=None, area_details=False, limit: int = 15, offset: int = 0, ubicacion: str = "", nombre_rondin: str = "", timezone=None):
        año = datetime.now().year

        match_filters = {
            "deleted_at": {"$exists": False},
            "form_id": self.BITACORA_RONDINES,
        }

        if date_from and date_to:
            match_filters["created_at"] = {
                "$gte": date_from,
                "$lte": date_to
            }
        elif date_from:
            match_filters["created_at"] = {"$gte": date_from}
        elif date_to:
            match_filters["created_at"] = {"$lte": date_to}
        else:
            match_filters["$expr"] = {
                "$eq": [{"$year": "$created_at"}, año]
            }

        if ubicacion:
            match_filters[f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}"] = ubicacion
        if nombre_rondin:
            match_filters[f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}"] = nombre_rondin

        query = [
            {"$match": match_filters},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "created_at": 1,
                "updated_at": 1,
                "ubicacion": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}",
                "nombre_recorrido": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}",
                "recorrido_id": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}._id",  # ← id del recorrido
                "asignado_a": f"$answers.{self.USUARIOS_OBJ_ID}.{self.mf['nombre_usuario']}",
                "tipo_rondin": f"$answers.{self.f['tipo_rondin']}",
                "fecha_hora_programada_inicio": f"$answers.{self.f['fecha_hora_programada_inicio']}",
                "fecha_hora_inicio": f"$answers.{self.f['fecha_hora_inicio']}",
                "fecha_hora_fin": f"$answers.{self.f['fecha_hora_fin']}",
                "estatus_recorrido": f"$answers.{self.f['estatus_recorrido']}",
                "duracion_rondin": f"$answers.{self.f['duracion_rondin']}",
                "motivo_cancelacion": f"$answers.{self.f['motivo_cancelacion']}",
                "comentario_general": f"$answers.{self.f['comentario_general']}",
                "comentarios_generales": f"$answers.{self.f['comentarios_generales']}",
                "porcentaje_avance": f"$answers.{self.f['porcentaje_avance']}",
                "cantidad_areas_inspeccionadas": f"$answers.{self.f['cantidad_areas_inspeccionadas']}",
                "areas": f"$answers.{self.f['areas']}",
                "incidencias": f"$answers.{self.f['bitacora_rondin_incidencias']}",
            }},
            {"$lookup": {
                "from": self.cr.name,
                "let": { "nombre_rec": "$nombre_recorrido", "ubicacion_rec": "$ubicacion" },
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$form_id", self.CONFIGURACION_DE_RECORRIDOS_FORM]},
                                {"$eq": [f"$answers.{self.rondin_keys['nombre_rondin']}", "$$nombre_rec"]},
                                {"$eq": [f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}", "$$ubicacion_rec"]},
                                {"$not": {"$ifNull": ["$deleted_at", False]}}
                            ]
                        }
                    }},
                    {"$project": {
                        "_id": 0,
                        "areas_config": f"$answers.{self.rondin_keys['areas']}",
                    }},
                    {"$limit": 1}
                ],
                "as": "recorrido_config"
            }},
            {"$addFields": {
                "area_record_ids": {
                    "$filter": {
                        "input": {
                            "$map": {
                                "input": {"$ifNull": ["$areas", []]},
                                "as": "area",
                                "in": {
                                    "$convert": {
                                        "input": {
                                            "$arrayElemAt": [
                                                {"$split": [{"$ifNull": [f"$$area.{self.f['url_registro_rondin']}", ""]}, "/"]},
                                                -1
                                            ]
                                        },
                                        "to": "objectId",
                                        "onError": None,
                                        "onNull": None
                                    }
                                }
                            }
                        },
                        "as": "oid",
                        "cond": {"$ne": ["$$oid", None]}
                    }
                }
            }},
            {"$lookup": {
                "from": self.cr.name,
                "let": {"record_ids": "$area_record_ids"},
                "pipeline": [
                    {"$match": {
                        "$expr": {
                            "$and": [
                                {"$eq": ["$form_id", self.CHECK_UBICACIONES]},
                                {"$in": ["$_id", "$$record_ids"]}
                            ]
                        }
                    }},
                    {"$project": {
                        "_id": 1,
                        "answers": 1,
                    }}
                ],
                "as": "checks_data"
            }},
            {"$unset": "area_record_ids"},
            {"$sort": {"created_at": -1}},
            {"$skip": offset},
            {"$limit": limit}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        result = [self.format_bitacora_record(record, area_details, timezone=timezone) for record in response]
        return {"data": result, "total": len(result)}

    def get_recorridos(self, date_from=None, date_to=None, area_details=False, limit=20, offset=0):
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
            f"answers.{self.f['status_cron']}":{'$ne':'eliminado'}
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
                "folio":1,
                "accion_recurrencia": f"$answers.{self.rondin_keys['accion_recurrencia']}",
                "areas": f"$answers.{self.rondin_keys['areas']}",
                "areas_name": f"$answers.{self.rondin_keys['areas']}.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['nombre_area']}",
                "cantidad_de_puntos": {"$size": {"$ifNull": [f"$answers.{self.rondin_keys['areas']}", []]}},
                "cada_cuantas_horas_se_repite": f"$answers.{self.rondin_keys['cada_cuantas_horas_se_repite']}",
                "checkpoints": {"$size": {"$ifNull": [f"$answers.{self.rondin_keys['areas']}", []]}},
                "cron_id": f"$answers.{self.rondin_keys['cron_id']}",
                "dag_id": {"$ifNull": [f"$answers.{self.rondin_keys['dag_id']}", ""]},
                "duracion_estimada": f"$answers.{self.rondin_keys['duracion_estimada']}",
                "duracion_esperada_rondin": {"$ifNull": [f"$answers.{self.rondin_keys['duracion_estimada']}", "No especificada"]},
                "empleados_asignado": {
                    "$map": {
                        "input": {"$ifNull": [f"$answers.{self.rondin_keys['grupo_asignado_a']}", []]},
                        "as": "emp",
                        "in": f"$$emp.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}"
                    }
                },
                "en_que_mes": f"$answers.{self.rondin_keys['en_que_mes']}",
                "en_que_semana_sucede": f"$answers.{self.rondin_keys['en_que_semana_sucede']}",
                "estatus_rondin": f"$answers.{self.f['status_cron']}",
                "fecha1": f"$answers.{self.rondin_keys['fecha1']}",
                "fecha2": f"$answers.{self.rondin_keys['fecha2']}",
                "fecha_final_rondin": {"$ifNull": [f"$answers.{self.f['fecha_final_recurrencia']}", "Sin fecha final"]},
                "fecha_hora_programada": f"$answers.{self.rondin_keys['fecha_hora_programada']}",
                "fecha_inicio_rondin": f"$answers.{self.f['fecha_primer_evento']}",
                "grupo_asignado": {"$ifNull": [f"$answers.{self.GRUPOS_CAT_OBJ_ID}.{self.rondin_keys['grupo_asignado']}", None]},
                "id_grupo": {"$arrayElemAt": [f"$answers.{self.GRUPOS_CAT_OBJ_ID}.{self.rondin_keys['id_grupo']}", 0]},
                "la_recurrencia_cuenta_con_fecha_final": f"$answers.{self.rondin_keys['la_recurrencia_cuenta_con_fecha_final']}",
                "nombre_del_rondin": f"$answers.{self.rondin_keys['nombre_rondin']}",
                "programar_anticipacion": f"$answers.{self.rondin_keys['programar_anticipacion']}",
                "que_dias_de_la_semana": f"$answers.{self.rondin_keys['que_dias_de_la_semana']}",
                "recurrencia": {"$ifNull": [f"$answers.{self.rondin_keys['la_tarea_es_de']}", 'No Recurrente']},
                "se_repite_cada": f"$answers.{self.rondin_keys['se_repite_cada']}",
                "sucede_cada": f"$answers.{self.rondin_keys['sucede_cada']}",
                "sucede_recurrencia": f"$answers.{self.rondin_keys['sucede_recurrencia']}",
                "tiempo_para_ejecutar_tarea": f"$answers.{self.rondin_keys['tiempo_para_ejecutar_tarea']}",
                "tiempo_para_ejecutar_tarea_expresado_en": f"$answers.{self.rondin_keys['tiempo_para_ejecutar_tarea_expresado_en']}",
                "tipo_asignacion": f"$answers.{self.rondin_keys['tipo_asignacion']}",
                "tipo_rondin": {"$ifNull": [f"$answers.{self.rondin_keys['tipo_rondin']}", "qr"]},
                "ubicacion": f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}",
                "ubicacion_area": f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.Location.f['area_salida']}",
                "ubicacion_geolocation": f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['address_geolocation']}",
                "area": f"$answers.{self.f['area']}",
                "cada_cuantos_dias_se_repite": f"$answers.{self.rondin_keys['cada_cuantos_dias_se_repite']}",
            }},
            {"$sort": {"_id": -1}},
            {"$skip": offset},
            {"$limit": limit}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = []

        if response:
            for item in response:
                # 'area' en legacy es el area de salida/booth del rondin, lo
                # mismo que ya se proyecta aqui como 'ubicacion_area' -- no
                # viene de self.f['area'] (que colisiona de forma no
                # relacionada con 'rondin_area'/'incidente_area').
                if not item.get('area'):
                    if item.get('ubicacion_area'):
                        item['area'] = item['ubicacion_area']
                    else:
                        item.pop('area', None)
                data = self.format_rondin_by_id(item)
                location = item.get('ubicacion', '')
                rondin_name = item.get('nombre_del_rondin', '')

                duracion_promedio = self.get_average_rondin_duration(
                    location=location,
                    rondin_name=rondin_name
                )
                data['duracion_promedio'] = duracion_promedio
                if area_details:
                    data['areas'] = self.get_area_images(
                        data.get('areas', []),
                        location=data.get('ubicacion')
                    )

                format_response.append(data)
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
                "accion_recurrencia": f"$answers.{self.rondin_keys['accion_recurrencia']}",
                "areas": f"$answers.{self.rondin_keys['areas']}",
                "cada_cuantas_horas_se_repite": f"$answers.{self.rondin_keys['cada_cuantas_horas_se_repite']}",
                "cantidad_de_puntos": {"$size": {"$ifNull": [f"$answers.{self.rondin_keys['areas']}", []]}},
                "cron_id": f"$answers.{self.rondin_keys['cron_id']}",
                "dag_id": f"$answers.{self.rondin_keys['dag_id']}",
                "duracion_esperada_rondin": {"$ifNull": [f"$answers.{self.rondin_keys['duracion_estimada']}", "No especificada"]},
                "empleados_asignado": {
                    "$map": {
                        "input": {"$ifNull": [f"$answers.{self.rondin_keys['grupo_asignado_a']}", []]},
                        "as": "emp",
                        "in": f"$$emp.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}"
                    }
                },
                "en_que_mes": f"$answers.{self.rondin_keys['en_que_mes']}",
                "en_que_semana_sucede": f"$answers.{self.rondin_keys['en_que_semana_sucede']}",
                "estatus_rondin": f"$answers.{self.f['status_cron']}",
                "fecha1": f"$answers.{self.rondin_keys['fecha1']}",
                "fecha2": f"$answers.{self.rondin_keys['fecha2']}",
                "fecha_final_rondin": {"$ifNull": [f"$answers.{self.rondin_keys['fecha_final_recurrencia']}", "Sin fecha final"]},
                "fecha_hora_programada": f"$answers.{self.rondin_keys['fecha_hora_programada']}",
                "fecha_inicio_rondin": f"$answers.{self.f['fecha_primer_evento']}",
                "id_grupo": {"$arrayElemAt": [f"$answers.{self.GRUPOS_CAT_OBJ_ID}.{self.rondin_keys['id_grupo']}", 0]},
                "grupo_asignado": {"$ifNull": [f"$answers.{self.GRUPOS_CAT_OBJ_ID}.{self.rondin_keys['grupo_asignado']}",None]},
                "la_recurrencia_cuenta_con_fecha_final": f"$answers.{self.rondin_keys['la_recurrencia_cuenta_con_fecha_final']}",
                "nombre_del_rondin": f"$answers.{self.rondin_keys['nombre_rondin']}",
                "programar_anticipacion": f"$answers.{self.rondin_keys['programar_anticipacion']}",
                "que_dias_de_la_semana": f"$answers.{self.rondin_keys['que_dias_de_la_semana']}",
                "recurrencia": {"$ifNull": [f"$answers.{self.rondin_keys['la_tarea_es_de']}", 'No Recurrente']},
                "se_repite_cada": f"$answers.{self.rondin_keys['se_repite_cada']}",
                "sucede_cada": f"$answers.{self.rondin_keys['sucede_cada']}",
                "sucede_recurrencia": f"$answers.{self.rondin_keys['sucede_recurrencia']}",
                "tiempo_para_ejecutar_tarea": f"$answers.{self.rondin_keys['tiempo_para_ejecutar_tarea']}",
                "tiempo_para_ejecutar_tarea_expresado_en": f"$answers.{self.rondin_keys['tiempo_para_ejecutar_tarea_expresado_en']}",
                "tipo_asignacion": f"$answers.{self.rondin_keys['tipo_asignacion']}",
                "tipo_rondin": {"$ifNull": [f"$answers.{self.rondin_keys['tipo_rondin']}", "qr"]},
                "ubicacion": f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}",
                "ubicacion_area": f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.Location.f['area_salida']}",
                "ubicacion_geolocation": f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['address_geolocation']}",
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
            query = [
                {"$match": {
                    "form_id": self.Location.AREAS_DE_LAS_UBICACIONES,
                    "deleted_at": {"$exists": False},
                    f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}": ubicacion,
                    f"answers.{self.f['area_tag_id']}": {"$exists": True}
                }},
                {"$project": {
                    "_id": f"$answers.{self.mf['nombre_area']}",
                }}
            ]
            data = self.format_cr(self.cr.aggregate(query))
            data = [item.get('_id') for item in data]
            format_data = list(set(data))
            return format_data
        else:
            raise Exception("Ubicacion is required.")

    def catalago_grupos_recorridos(self):
        catalog_id = self.GRUPOS_CAT_ID
        form_id = self.CONFIGURACION_RECORRIDOS_FORM
        return self.catalogo_view(catalog_id, form_id)

    def catalogo_inspecciones(self):
        catalog_id = self.CATALOGO_FORMAS_CAT_ID
        form_id = self.CONFIGURACION_RECORRIDOS_FORM
        return self.catalogo_view(catalog_id, form_id)

    def get_catalog_areas_formatted(self, ubicacion=""):
        #Obtener areas disponibles para rondin
        if ubicacion:
            options = {
                'startkey': [ubicacion],
                'endkey': [f"{ubicacion}\n",{}],
                'group_level':2
            }

            catalog_id = self.AREAS_DE_LAS_UBICACIONES_CAT_ID
            form_id = self.CONFIGURACION_RECORRIDOS_FORM
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
                "link": f"$answers.{self.rondin_keys['link']}",
            }},
            {"$skip": offset},
            {"$limit": limit}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = []
        if response:
            format_response = self.format_incidencias_rondines(response, area)
        return format_response

    def get_rondines_images(self, location=None, areas=None, date_from=None, date_to=None, limit=20, offset=0):
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
            f"answers.{self.f['areas_del_rondin']}": {
                "$type": "array",
                "$not": {"$size": 0}
            }
        }

        unwind_match = {
            f"answers.{self.f['areas_del_rondin']}.{self.f['foto_evidencia_area_rondin']}": {
                "$exists": True,
                "$not": {"$size": 0}
            }
        }

        if location:
            match.update({
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}": location
            })
        if areas:
            unwind_match.update({
                f"answers.{self.f['areas_del_rondin']}.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.Location.f['area']}": {"$in": areas}
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
            {'$unwind': f"$answers.{self.f['areas_del_rondin']}"},
            {"$match": unwind_match},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "areas_recorrido": f"$answers.{self.f['areas_del_rondin']}",
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
        return format_response

    def get_bitacora_rondines(self, location=None, nombre_rondin=None, year=None, month=None, timezone=None):
        year_condition = { "$eq": [ { "$year": "$created_at" }, { "$year": "$$NOW" } ] }
        month_condition = { "$eq": [ { "$month": "$created_at" }, { "$month": "$$NOW" } ] }

        if year:
            year_condition = { "$eq": [ { "$year": "$created_at" }, int(year) ] }
        if month:
            month_condition = { "$eq": [ { "$month": "$created_at" }, int(month) ] }

        match = {
            "deleted_at": {"$exists": False},
            "form_id": self.BITACORA_RONDINES,
            f"answers.{self.f['fecha_programacion']}": {"$type": "string", "$ne": ""},
            "$expr": {
                "$and": [
                    year_condition,
                    month_condition
                ]
            }
        }

        if nombre_rondin:
            match.update({
                f"answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}": nombre_rondin,
            })
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
            format_resp = self.format_bitacora_rondines(response, timezone=timezone)
        return format_resp

    def get_check_by_id(self, record_id: str, timezone=None):
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
                                    "$ifNull": [f"$answers.{self.f['areas_del_rondin']}", []]
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
            {"$unwind": f"$answers.{self.f['areas_del_rondin']}"},
            {"$match": {
                "$expr": {
                    "$regexMatch": {
                        "input": f"$answers.{self.f['areas_del_rondin']}.{self.f['url_registro_rondin']}",
                        "regex": record_id
                    }
                }
            }},
            {"$project": {
                "_id": 0,
                "ubicacion": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}",
                "nombre_recorrido": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}",
                "area": f"$answers.{self.f['areas_del_rondin']}",
                "incidencias": f"$answers.{self.f['bitacora_rondin_incidencias']}",
            }}
        ]

        response = self.format_cr(self.cr.aggregate(query))
        response = self.unlist(response)
        format_response = {}
        if response:
            format_response = self.format_check_by_id(response, record_id, timezone=timezone)
        return format_response

    def get_all_checks(self, ubicacion: str = "", nombre_rondin: str = ""):
        año = datetime.now().year
        match_filters = {
            "deleted_at": {"$exists": False},
            "form_id": self.CHECK_UBICACIONES,
            "$expr": {
                "$eq": [{"$year": "$created_at"}, año]
            }
        }
        if ubicacion:
            match_filters[f"answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['location']}"] = ubicacion

        query = [
            {"$match": match_filters},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "created_at": 1,
                "updated_at": 1,
                "foto_evidencia_area": f"$answers.{self.f['foto_evidencia_area']}",
                "grupo_incidencias_check": f"$answers.{self.f['grupo_incidencias_check']}",
                "comentario_check_area": f"$answers.{self.f['comentario_check_area']}",
                "check_status": f"$answers.{self.f['check_status']}",
                "fecha_inspeccion_area": f"$answers.{self.f['fecha_inspeccion_area']}",
                "url_rondin": f"$answers.{self.f['url_rondin']}",
                "rondin_area": f"$answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['rondin_area']}",
                "tipo_de_area": f"$answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['tipo_de_area']}",
                "incidente_location": f"$answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['location']}",
                "area_tag_id": f"$answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['area_tag_id']}",
                "foto_area": f"$answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['foto_area']}",
            }},
            # Extraer ID del final de la URL
            {"$addFields": {
                "rondin_id_str": {
                    "$cond": {
                        "if": {"$and": [
                            {"$ne": ["$url_rondin", None]},
                            {"$ne": ["$url_rondin", ""]},
                        ]},
                        "then": {
                            "$let": {
                                "vars": {
                                    "match": {
                                        "$regexFind": {
                                            "input": "$url_rondin",
                                            "regex": r"([a-f0-9]{24})$"
                                        }
                                    }
                                },
                                "in": "$$match.match"
                            }
                        },
                        "else": None
                    }
                }
            }},
            {"$addFields": {
                "rondin_object_id": {
                    "$cond": {
                        "if": {"$ne": ["$rondin_id_str", None]},
                        "then": {"$toObjectId": "$rondin_id_str"},
                        "else": None
                    }
                }
            }},
            # Lookup a BITACORA_RONDINES
            {"$lookup": {
                "from": self.cr.name,
                "let": {"rondin_oid": "$rondin_object_id"},
                "pipeline": [
                    {"$match": {"$expr": {
                        "$and": [
                            {"$eq": ["$_id", "$$rondin_oid"]},
                            {"$ne": ["$$rondin_oid", None]}
                        ]
                    }}},
                    {"$project": {
                        "_id": 1,
                        "folio": 1,
                        "form_id": 1,  # agrega esto para ver qué forma es
                        "ubicacion": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.Location.f['location']}",
                        "nombre_recorrido": f"$answers.{self.CONFIGURACION_RECORRIDOS_OBJ_ID}.{self.mf['nombre_del_recorrido']}",
                        "asignado_a": f"$answers.{self.f['asignado_a']}",
                        "tipo_rondin": f"$answers.{self.f['tipo_rondin']}",
                        "fecha_hora_programada_inicio": f"$answers.{self.f['fecha_hora_programada_inicio']}",
                        "fecha_hora_inicio": f"$answers.{self.f['fecha_hora_inicio']}",
                        "estatus_recorrido": f"$answers.{self.f['estatus_recorrido']}",
                        "duracion_rondin": f"$answers.{self.f['duracion_rondin']}",
                        "comentario_general": f"$answers.{self.f['comentario_general']}",
                        "porcentaje_avance": f"$answers.{self.f['porcentaje_avance']}",
                        "cantidad_areas_inspeccionadas": f"$answers.{self.f['cantidad_areas_inspeccionadas']}",
                    }}
                ],
                "as": "rondin_info"
            }},
            {"$addFields": {
                "rondin": {"$arrayElemAt": ["$rondin_info", 0]}
            }},
            {"$sort": {"created_at": -1}},
            {"$limit": 100}
        ]

        response = self.format_cr(self.cr.aggregate(query))
        result = []

        for record in response:
            rondin = self.unlist(record.get("rondin_info")) or {}
            # Normaliza cada incidencia a las llaves que legacy expone
            # ('incidencia'/'incidente_accion', nunca 'tipo_de_incidencia'/
            # 'incidente_comentario') -- misma colision de self.f que en
            # format_incidencias_rondines.
            for inc in record.get("grupo_incidencias_check", []):
                if 'tipo_de_incidencia' in inc:
                    inc.setdefault('incidencia', inc.pop('tipo_de_incidencia'))
                if 'incidente_comentario' in inc:
                    inc.setdefault('incidente_accion', inc.pop('incidente_comentario'))
            result.append({
                "id": str(record.get("_id", "")),
                "folio": record.get("folio", ""),
                "created_at": str(record.get("created_at", "")),
                "updated_at": str(record.get("updated_at", "")),
                "url_rondin": record.get("url_rondin", ""),
                "rondin_area": record.get("rondin_area", []),
                "area_tag_id": record.get("area_tag_id", ""),
                "tipo_de_area": record.get("tipo_de_area", []),
                "incidente_location": record.get("incidente_location", []),
                "check_status": record.get("check_status", ""),
                "comentario_check_area": record.get("comentario_check_area", ""),
                "foto_evidencia_area": record.get("foto_evidencia_area", []),
                "foto_area": record.get("foto_area", []),
                "fecha_inspeccion_area": record.get("fecha_inspeccion_area", ""),
                "grupo_incidencias_check": record.get("grupo_incidencias_check", []),
                "rondin": {
                    "id": str(rondin.get("_id", "")),
                    "folio": rondin.get("folio", ""),
                    "ubicacion": rondin.get("ubicacion", ""),
                    "nombre_recorrido": rondin.get("nombre_recorrido", ""),
                    "asignado_a": rondin.get("nombre_emp", ""),
                    "tipo_rondin": rondin.get("tipo_rondin", ""),
                    "fecha_hora_programada_inicio": rondin.get("fecha_hora_programada_inicio", ""),
                    "fecha_hora_inicio": rondin.get("fecha_hora_inicio", ""),
                    "estatus_recorrido": rondin.get("estatus_recorrido", ""),
                    "duracion_rondin": rondin.get("duracion_rondin", ""),
                    "comentario_general": rondin.get("comentario_general", ""),
                    "porcentaje_avance": rondin.get("porcentaje_avance", ""),
                    "cantidad_areas_inspeccionadas": rondin.get("cantidad_areas_inspeccionadas", ""),
                } if rondin else {}
            })

        return {"data": result, "total": len(result)}

    def get_bitacora_by_id(self, record_id, timezone=None):
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
            bitacoras_mes = self.get_bitacoras_mes(response.get('incidente_location', ''), response.get('nombre_del_recorrido', ''), timezone=timezone)
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

    def get_bitacoras_mes(self, location, nombre_recorrido, timezone=None):
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
            format_response = self.format_bitacoras_mes(response, nombre_recorrido, timezone=timezone)
        return format_response

    def get_rondin_checks(self, area, location, nombre_recorrido, record_id, timezone=None):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.CHECK_UBICACIONES,
                f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.Location.f['area']}": area,
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
                "created_at": {
                    "$dateToString": {
                        "format": "%Y-%m-%d %H:%M",
                        "date": "$created_at",
                        "timezone": "America/Mexico_City"
                    }
                }
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        format_response = []
        if response:
            format_response = self.format_rondin_checks(response, record_id, timezone=timezone)
        return format_response

    def _get_estado_check(self, incidencias, area_nombre):
        """
        Determina el estado de un check según su información.

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

    def _get_estado_bitacora_dia(self, bitacora_rondines, dia, year, month, hora_valida, timezone=None):
        """
        Determina el estado de una bitácora en un día específico.

        Returns:
            tuple: (estado, bitacora_id)
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
        if timezone:
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
            except Exception:
                now = datetime.now()
        else:
            now = datetime.now()
        fecha_evaluada = datetime(year, month, dia)

        estaba_programada, bitacora_programada = self._verificar_bitacora_programada(dia, year, month, hora_valida, bitacora_rondines)
        if estaba_programada:
            estatus_bitacora_programada = bitacora_programada.get('estatus_del_recorrido', '')
            record_id = str(bitacora_programada.get('_id', ''))
            if estatus_bitacora_programada == 'cancelado':
                return ("cancelado", record_id)
            elif estatus_bitacora_programada == 'programado':
                return ("programado", record_id)
            elif estatus_bitacora_programada == 'realizado':
                return ("fuera_de_hora", record_id)
            else:
                return ("no_inspeccionada", record_id)

        if fecha_evaluada.date() > now.date():
            return ("none", "")
        elif fecha_evaluada.date() == now.date():
            return ("programado", "")
        else:
            return ("no_aplica", "")

    def _get_estado_area_dia(self, bitacora_rondines, area_tag_id, nombre_area, dia, year, month, hora_valida, timezone=None):
        """
        Determina el estado de un área en un día específico.

        Returns:
            str: Estado del área
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
        if timezone:
            try:
                tz = pytz.timezone(timezone)
                now = datetime.now(tz)
            except Exception:
                now = datetime.now()
        else:
            now = datetime.now()
        fecha_evaluada = datetime(year, month, dia)

        # Si es día pasado, verificar si estaba programada una bitácora
        estaba_programada, bitacora_programada = self._verificar_bitacora_programada(dia, year, month, hora_valida, bitacora_rondines)

        if estaba_programada:
            estatus_bitacora_programada = bitacora_programada.get('estatus_del_recorrido', '')
            if estatus_bitacora_programada == 'cancelado':
                return "cancelado"
            elif estatus_bitacora_programada == 'realizado':
                return "fuera_de_hora"
            else:
                return "no_inspeccionada"

        # Si es día futuro o presente
        if fecha_evaluada.date() > now.date():
            return "none"
        elif fecha_evaluada.date() == now.date():
            return "programado"
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
            'programado': 'programado',
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

    def run_cron(self, dag_id):
        response = self.lkf_api.run_cron(dag_id)
        return response

    def update_inspeccion(self, folio, rondin_data: dict = {}):
        answers = {}
        existing_record = self.get_rondin_by_id(folio)
        folio = existing_record.get("folio", "")
        existing_areas = existing_record.get("areas", [])
        if existing_areas and isinstance(existing_areas[0], list):
            existing_areas = existing_areas[0]

        inspeccion = rondin_data.get('inspeccion', '')
        prompt_inspeccion = rondin_data.get('prompt_inspeccion', '')
        areas_targets = rondin_data.get('areas', [])

        updated_areas = []
        for i, area_item in enumerate(existing_areas):
            area_nombre = area_item.get('rondin_area', '')
            should_update = (
                not areas_targets or
                areas_targets == ["todas"] or
                area_nombre in areas_targets
            )
            area_dict = {
                self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                    self.Location.f['area']: area_nombre,
                    self.f['area_tag_id']: area_item.get('area_tag_id', []),
                    self.f['foto_area']: area_item.get('foto_area', []),
                    self.f['geolocalizacion_area_ubicacion']: area_item.get('geolocalizacion_area_ubicacion', []),
                },
                self.CATALOGO_FORMAS_OBJ_ID: {
                    self.mf['nombre_forma']: inspeccion if should_update else area_item.get(self.CATALOGO_FORMAS_OBJ_ID, {}).get(self.mf['nombre_forma'], ''),
                    self.rondin_keys['grupo_id']: area_item.get(self.CATALOGO_FORMAS_OBJ_ID, {}).get(self.rondin_keys['grupo_id'], ['129870'])
                },
                self.rondin_keys['prompt_inspeccion']: prompt_inspeccion if should_update else area_item.get(self.rondin_keys['prompt_inspeccion'], '')
            }
            updated_areas.append(area_dict)

        answers[self.rondin_keys["areas"]] = {str(i): area for i, area in enumerate(updated_areas)}

        response = self.lkf_api.patch_multi_record(
            answers=answers,
            form_id=self.CONFIGURACION_RECORRIDOS_FORM,
            folios=[folio,]
        )
        return response

    def update_rondin(self, folio, rondin_data: dict = {}):
        answers = {}
        for key, value in rondin_data.items():
            if key == 'ubicacion':
                ubicacion_result = self.get_ubicacion_geolocation(location=value)
                ubicacion = ubicacion_result if ubicacion_result else value
                if isinstance(ubicacion, dict):
                    answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {
                        self.Location.f['location']: ubicacion.get('location', ''),
                        self.f['address_geolocation']: ubicacion.get('geolocation', [])
                    }
                else:
                    answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {
                        self.Location.f['location']: ubicacion,
                        self.f['address_geolocation']: []
                    }
            elif key == 'area':
                if value:
                    answers[self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID] = {
                        self.mf['nombre_area_salida']: value
                    }
            elif key == 'grupo_asignado':
                answers[self.GRUPOS_CAT_OBJ_ID] = {
                    self.rondin_keys[key]: value
                }
            elif key == 'asignado_a':
                answers[self.rondin_keys['grupo_asignado_a']] = self.rondin_asignado_a(value)
            elif key == 'areas':
                areas_list = []
                for area in value:
                    if isinstance(area, dict):
                        area_dict = {
                            self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                                self.Location.f['area']: area.get('area', ''),
                                self.f['geolocalizacion_area_ubicacion']: [{
                                    'latitude': area.get('latitude', 0),
                                    'longitude': area.get('longitude', 0)
                                }],
                                self.f['foto_area']: area.get('image', []),
                                self.f['area_tag_id']: [area.get('tag_id', [])]
                            },
                            self.CATALOGO_FORMAS_OBJ_ID: {},
                            self.rondin_keys['prompt_inspeccion']: ''
                        }
                    else:
                        area_dict = {
                            self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                                self.Location.f['area']: area,
                                self.f['geolocalizacion_area_ubicacion']: [],
                                self.f['foto_area']: [],
                                self.f['area_tag_id']: []
                            },
                            self.CATALOGO_FORMAS_OBJ_ID: {},
                            self.rondin_keys['prompt_inspeccion']: ''
                        }
                    areas_list.append(area_dict)
                answers[self.rondin_keys["areas"]] = areas_list

            elif key == 'sucede_recurrencia' and value and ('dia_del_mes' in value or 'mes' in value):
                actual_day = datetime.now().day
                answers[self.rondin_keys['que_dia_del_mes']] = int(actual_day)
                answers[self.rondin_keys[key]] = value
            elif key == 'tipo_rondin':
                if value:
                    answers[self.rondin_keys[key]] = value.lower()
            elif value == '' or value is None:
                pass
            else:
                answers[self.rondin_keys[key]] = value

        response = self.lkf_api.patch_multi_record(
            answers=answers,
            form_id=self.CONFIGURACION_RECORRIDOS_FORM,
            folios=[folio]
        )
        return response

    def _verificar_bitacora_programada(self, dia, year, month, hora_valida, bitacora_rondines):
        """
        Verifica si había una bitácora programada para un día específico.

        Returns:
            tuple: (bool, dict) True/bitacora si había bitácora programada, False/{} si no
        """
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

            if fecha_prog.year != year or fecha_prog.month != month or fecha_prog.day != dia:
                continue

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

    def asignar_recorrido(self, folio, asignado_a):
        if not folio:
            return self.LKFException({'title': 'Error', 'msg': 'No se proporciono el folio'})
        if not asignado_a:
            return self.LKFException({'title': 'Error', 'msg': 'No se proporciono el asignado_a'})

        answers = {}
        grupo = {}

        for index, nombre in enumerate(asignado_a):
            empleado_set = self.rondin_asignado_a(nombre)
            if empleado_set:
                grupo[(index + 1) * -1] = empleado_set[0]

        if grupo:
            answers[self.rondin_keys['grupo_asignado_a']] = {'0': list(grupo.values())[0]}

        res = self.lkf_api.patch_multi_record(
            answers=answers,
            form_id=self.CONFIGURACION_RECORRIDOS_FORM,
            folios=[folio]
        )
        return res

    def get_area_images(self, areas, location):
        format_areas = []
        for area in areas:
            if isinstance(area, dict):
                area = area.get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.Location.f['area'], '')
            if area:
                format_areas.append(area)
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.Location.AREAS_DE_LAS_UBICACIONES,
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

    #! ============================================
    #! Filtros de listados (migrado de filters.py)
    #! ============================================

    def _get_mongo_string_list(func):
        def wrapper(self, *args, **kwargs):
            config = func(self, *args, **kwargs)
            match_query_custom = config.get('query', {})
            form_id = config.get('form_id')
            project_fields = config.get('project', {})
            match_query = {"deleted_at": {"$exists": False}}
            if form_id:
                match_query["form_id"] = form_id
            match_query.update(match_query_custom)
            query = [{"$match": match_query}, {"$project": {"_id": 0, **project_fields}}]
            data = self.format_cr(self.cr.aggregate(query))
            format_data = []
            if data:
                for item in data:
                    format_data.append(item.get("value"))
                format_data = list(set(format_data))
            return format_data
        return wrapper

    def _get_mongo_distinct_list(func):
        def wrapper(self, *args, **kwargs):
            config = func(self, *args, **kwargs)
            field_name = config.get('field')
            form_id = config.get('form_id')
            match_query_custom = config.get('query', {})
            if not field_name:
                return []
            match_query = {"deleted_at": {"$exists": False}}
            if form_id:
                match_query["form_id"] = form_id
            match_query.update(match_query_custom)
            data = self.cr.distinct(field_name, match_query)
            return [str(item) for item in data if item is not None]
        return wrapper

    @_get_mongo_string_list
    def get_profiles(self):
        return {
            "form_id": self.CONF_PERFILES,
            "query": {
                f"answers.{self.PERFILES_OBJ_ID}.{self.mf['walkin']}": "Si"
            },
            "project": {
                "value": f"$answers.{self.PERFILES_OBJ_ID}.{self.mf['nombre_perfil']}"
            }
        }

    @_get_mongo_string_list
    def get_areas(self):
        return {
            "form_id": self.Location.AREAS_DE_LAS_UBICACIONES,
            "project": {
                "value": f"$answers.{self.mf['nombre_area']}"
            }
        }

    @_get_mongo_distinct_list
    def get_in_and_out_status(self):
        return {
            "form_id": self.BITACORA_ACCESOS,
            "field": f"answers.{self.mf['tipo_registro']}"
        }

    @_get_mongo_distinct_list
    def get_incidencias_estatus(self):
        return {
            "form_id": self.BITACORA_INCIDENCIAS,
            "field": f"answers.{self.incidence_fields['estatus']}"
        }

    @_get_mongo_distinct_list
    def get_incidencias_tipo(self):
        return {
            "form_id": self.BITACORA_INCIDENCIAS,
            "field": f"answers.{self.incidence_fields['incidencia']}"
        }

    @_get_mongo_distinct_list
    def get_fallas_estatus(self):
        return {
            "form_id": self.BITACORA_FALLAS,
            "field": f"answers.{self.fallas_fields['falla_estatus']}"
        }

    @_get_mongo_distinct_list
    def get_paqueteria_estatus(self):
        return {
            "form_id": self.PAQUETERIA,
            "field": f"answers.{self.paquetes_fields['estatus_paqueteria']}"
        }

    @_get_mongo_distinct_list
    def get_lockers_filter_list(self):
        return {
            "form_id": self.PAQUETERIA,
            "field": f"answers.{self.paquetes_fields['guardado_en_paqueteria']}"
        }

    @_get_mongo_distinct_list
    def get_cons_estatus(self):
        return {
            "form_id": self.CONCESSIONED_ARTICULOS,
            "field": f"answers.{self.cons_f['status_concesion']}"
        }

    @_get_mongo_distinct_list
    def get_cons_categoria(self):
        return {
            "form_id": self.CONCESSIONED_ARTICULOS,
            "field": f"answers.{self.cons_f['grupo_equipos']}.{self.cons_f['categoria_equipo_concesion']}"
        }

    @_get_mongo_distinct_list
    def get_cons_equipos(self):
        return {
            "form_id": self.CONCESSIONED_ARTICULOS,
            "field": f"answers.{self.cons_f['grupo_equipos']}.{self.cons_f['nombre_equipo']}"
        }

    @_get_mongo_distinct_list
    def get_perdidos_estatus(self):
        return {
            "form_id": self.BITACORA_OBJETOS_PERDIDOS,
            "field": f"answers.{self.perdidos_fields['estatus_perdido']}"
        }

    @_get_mongo_distinct_list
    def get_perdidos_cat(self):
        return {
            "form_id": self.BITACORA_OBJETOS_PERDIDOS,
            "field": f"answers.{self.perdidos_fields['articulo_seleccion_catalog']}.{self.cons_f['_categoria_equipo_concesion']}"
        }

    @_get_mongo_distinct_list
    def get_perdidos_art(self):
        return {
            "form_id": self.BITACORA_OBJETOS_PERDIDOS,
            "field": f"answers.{self.perdidos_fields['articulo_seleccion_catalog']}.{self.fallas_fields['falla_objeto_afectado']}"
        }

    @_get_mongo_distinct_list
    def get_perdidos_color(self):
        return {
            "form_id": self.BITACORA_OBJETOS_PERDIDOS,
            "field": f"answers.{self.perdidos_fields['color_perdido']}"
        }

    @_get_mongo_distinct_list
    def get_fallas_tipo(self):
        return {
            "form_id": self.BITACORA_FALLAS,
            "field": f"answers.{self.LISTA_FALLAS_CAT_OBJ_ID}.{self.fallas_fields['falla']}"
        }

    @_get_mongo_distinct_list
    def get_notas_estatus(self):
        return {
            "form_id": self.ACCESOS_NOTAS,
            "field": f"answers.{self.notes_fields['note_status']}"
        }

    @_get_mongo_distinct_list
    def get_proveedores(self):
        return {
            "form_id": self.PAQUETERIA,
            "field": f"answers.{self.paquetes_fields['proveedor_cat']}.{self.paquetes_fields['proveedor']}"
        }

    @_get_mongo_distinct_list
    def get_pases_status(self):
        return {
            "form_id": self.PASE_ENTRADA,
            "field": f"answers.{self.pase_entrada_fields['status_pase']}"
        }

    def get_filters_in_and_out(self):
        profiles  = self.get_profiles()
        estatus   = self.get_in_and_out_status()
        employees = self.get_employees_names()
        return [
            {
                "defaultDisplayOpen": True,
                "key": "status",
                "label": "Estatus",
                "type": "multiple",
                "options": [{"label": i.capitalize(), "value": i} for i in estatus]
            },
            {
                "defaultDisplayOpen": False,
                "key": "perfil_visita",
                "label": "Perfil",
                "type": "multiple",
                "options": [{"label": i, "value": i} for i in profiles]
            },
            {
                "defaultDisplayOpen": False,
                "key": "visita_a",
                "label": "Visita a",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in employees]
            }
        ]

    def get_filters_pases(self):
        profiles = self.get_profiles()
        estatus = self.get_pases_status()
        employees = self.get_employees_names()
        filters = [
            {
                "defaultDisplayOpen": True,
                "key": "status",
                "label": "Estatus",
                "type": "multiple",
                "options": [{"label": i.capitalize().replace("_", " "), "value": i} for i in estatus if i]
            },
            {
                "defaultDisplayOpen": False,
                "key": "perfil_visita",
                "label": "Perfil",
                "type": "multiple",
                "options": [{"label": i, "value": i} for i in profiles]
            },
            {
                "defaultDisplayOpen": False,
                "key": "visita_a",
                "label": "Visita a",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in employees]
            }
        ]
        return filters

    def get_filters_recorridos(self):
        asignado_a = self.get_employees_names()
        areas      = self.get_areas()
        return [
            {
                "defaultDisplayOpen": True,
                "key": "estatus_recorrido",
                "label": "Estatus",
                "type": "multiple",
                "options": [
                    {"label": "Corriendo", "value": "Corriendo"},
                    {"label": "Pausado",   "value": "Pausado"},
                    {"label": "Eliminado", "value": "Eliminado"},
                    {"label": "Sin Programar",   "value": "Sin Programar"},
                ]
            },
            {
                "defaultDisplayOpen": True,
                "key": "tipo_rondin",
                "label": "Tipo",
                "type": "multiple",
                "options": [
                    {"label": "QR",  "value": "qr"},
                    {"label": "NFC", "value": "nfc"},
                ]
            },
            {
                "defaultDisplayOpen": False,
                "key": "recurrencia",
                "label": "Recurrencia",
                "type": "multiple",
                "options": [
                    {"label": "Minuto",           "value": "Minuto"},
                    {"label": "Hora",             "value": "Hora"},
                    {"label": "Día de la semana", "value": "Dia de la Semana"},
                    {"label": "Día del mes",      "value": "Dia del Mes"},
                    {"label": "Mes",              "value": "Mes"},
                ]
            },
            {
                "defaultDisplayOpen": False,
                "key": "area",
                "label": "Área",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in areas]
            },
        ]

    def get_filters_rondines(self):
        asignado_a = self.get_employees_names()
        areas      = self.get_areas()
        return [
            {
                "defaultDisplayOpen": True,
                "key": "estatus_rondin",
                "label": "Estatus",
                "type": "multiple",
                "options": [
                    {"label": "Programado", "value": "Programado"},
                    {"label": "Realizado",  "value": "Realizado"},
                    {"label": "En Proceso", "value": "En Proceso"},
                    {"label": "Cancelado",  "value": "Cancelado"},
                    {"label": "Cerrado",    "value": "Cerrado"},
                ]
            },
            {
                "defaultDisplayOpen": False,
                "key": "incidencias",
                "label": "Tiene incidencias",
                "type": "single",
                "options": [
                    {"label": "Si", "value": "Si"},
                    {"label": "No", "value": "No"},
                ]
            },
            {
                "defaultDisplayOpen": False,
                "key": "asignado_a",
                "label": "Asignado a",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in asignado_a]
            },
            {
                "defaultDisplayOpen": False,
                "key": "area",
                "label": "Área",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in areas]
            },
        ]

    def get_filters_check_areas(self):
        areas = self.get_areas()
        asignado_a = self.get_employees_names()
        return [
            {
                "defaultDisplayOpen": False,
                "key": "incidencias",
                "label": "Tiene incidencias",
                "type": "single",
                "options": [
                    {"label": "Si", "value": "Si"},
                    {"label": "No", "value": "No"},
                ]
            },
            {
                "defaultDisplayOpen": False,
                "key": "asignado_a",
                "label": "Asignado a",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in asignado_a]
            },
            {
                "defaultDisplayOpen": False,
                "key": "area",
                "label": "Área",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in areas]
            },
        ]

    def get_filters_incidencias(self):
        estatuses = self.get_incidencias_estatus()
        tipos     = self.get_incidencias_tipo()
        reportado_por = self.get_employees_names()
        areas = self.get_areas()

        return [
            {
                "defaultDisplayOpen": True,
                "key": "estatus_incidencia",
                "label": "Estatus",
                "type": "multiple",
                "options": [{"label": i.capitalize(), "value": i} for i in estatuses]
            },
            {
                "defaultDisplayOpen": False,
                "key": "reportado_por",
                "label": "Reportado por",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in reportado_por]
            },
            {
                "defaultDisplayOpen": True,
                "key": "tipo_incidencia",
                "label": "Incidente",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in tipos]
            },
            {
                "defaultDisplayOpen": False,
                "key": "area",
                "label": "Lugar del incidente",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in areas]
            },
        ]

    def get_filters_incidencias_rondines(self):
        tipos     = self.get_incidencias_tipo()
        areas = self.get_areas()

        return [
            {
                "defaultDisplayOpen": True,
                "key": "tipo_incidencia",
                "label": "Incidente",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in tipos]
            },
            {
                "defaultDisplayOpen": False,
                "key": "area",
                "label": "Lugar del incidente",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in areas]
            },
        ]

    def get_filters_fallas(self):
        estatuses = self.get_fallas_estatus()
        tipos     = self.get_fallas_tipo()
        reportado_por = self.get_employees_names()
        areas = self.get_areas()

        return [
            {
                "defaultDisplayOpen": True,
                "key": "estatus_falla",
                "label": "Estatus",
                "type": "multiple",
                "options": [{"label": i.capitalize(), "value": i} for i in estatuses]
            },
            {
                "defaultDisplayOpen": False,
                "key": "reportado_por",
                "label": "Reportado por",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in reportado_por]
            },
            {
                "defaultDisplayOpen": True,
                "key": "tipo_falla",
                "label": "Falla",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in tipos]
            },
            {
                "defaultDisplayOpen": False,
                "key": "area",
                "label": "Lugar de la falla",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in areas]
            },
        ]

    def get_filters_paqueteria(self):
        estatuses = self.get_paqueteria_estatus()
        reportado_por = self.get_employees_names()
        areas = self.get_areas()
        lockers = self.get_lockers_filter_list()
        proveedor = self.get_proveedores()
        return [
            {
                "defaultDisplayOpen": True,
                "key": "estatus_paqueteria",
                "label": "Estatus",
                "type": "multiple",
                "options": [{"label": i.capitalize(), "value": i} for i in estatuses]
            },
            {
                "defaultDisplayOpen": False,
                "key": "quien_recibe_paqueteria",
                "label": "Quien recibe ",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in reportado_por]
            },
            {
                "defaultDisplayOpen": False,
                "key": "locker",
                "label": "Locker ",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in lockers]
            },
            {
                "defaultDisplayOpen": False,
                "key": "proveedor",
                "label": "Proveedor",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in proveedor]
            },
            {
                "defaultDisplayOpen": False,
                "key": "area_paqueteria",
                "label": "Área",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in areas]
            },
        ]

    def get_filters_concesionados(self):
        estatuses = self.get_cons_estatus()
        equipos = self.get_cons_equipos()
        reportado_por = self.get_employees_names()
        areas = self.get_areas()
        categoria = self.get_cons_categoria()

        return [
            {
                "defaultDisplayOpen": True,
                "key": "status_concesion",
                "label": "Estatus",
                "type": "multiple",
                "options": [{"label": i.capitalize(), "value": i} for i in estatuses]
            },
            {
                "defaultDisplayOpen": False,
                "key": "persona_nombre_concesion",
                "label": "Solicitante ",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in reportado_por]
            },
            {
                "defaultDisplayOpen": False,
                "key": "created_by",
                "label": "Creado por ",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in reportado_por]
            },
            {
                "defaultDisplayOpen": False,
                "key": "categoria_equipo_concesion",
                "label": "Categoría",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in categoria]
            },
            {
                "defaultDisplayOpen": False,
                "key": "nombre_equipo",
                "label": "Equipo ",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in equipos]
            },
            {
                "defaultDisplayOpen": False,
                "key": "area_paqueteria",
                "label": "Área",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in areas]
            },
        ]

    def get_filters_perdidos(self):
        estatus = self.get_perdidos_estatus()
        cat = self.get_perdidos_cat()
        art = self.get_perdidos_art()
        color = self.get_perdidos_color()
        reportado_por = self.get_employees_names()
        areas = self.get_areas()

        return [
            {
                "defaultDisplayOpen": True,
                "key": "estatus_p",
                "label": "Estatus",
                "type": "multiple",
                "options": [{"label": i.capitalize(), "value": i} for i in estatus]
            },
            {
                "defaultDisplayOpen": False,
                "key": "categoria",
                "label": "Categoría",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in cat]
            },
            {
                "defaultDisplayOpen": False,
                "key": "articulo",
                "label": "Artículo",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in art]
            },
            {
                "defaultDisplayOpen": False,
                "key": "color",
                "label": "Color",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in color]
            },
            {
                "defaultDisplayOpen": False,
                "key": "area_paqueteria",
                "label": "Área",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in areas]
            },
        ]

    def get_filters_notas(self):
        reportado_por = self.get_employees_names()
        estatus = self.get_notas_estatus()
        return [
            {
                "defaultDisplayOpen": True,
                "key": "estatus",
                "label": "Estatus",
                "type": "multiple",
                "options": [{"label": i.capitalize(), "value": i} for i in estatus]
            },
            {
                "defaultDisplayOpen": False,
                "key": "creador_por",
                "label": "Creado por",
                "type": "multiselect",
                "options": [{"label": i, "value": i} for i in reportado_por]
            },
        ]

    def do_checkout(self, checkin_id=None, location=None, area=None, guards=[], forzar=False, comments=False, fotografia=[], guard_id=None):
        """
        Se encarga de hacer el check out de un empleado.

        Args:
            checkin_id (str): Id del check in.
            location (str): Ubicacion.
            area (str): Area.
            guards (list): Lista de guardias.
            forzar (bool): Forzar el check out.
            comments (bool): Comentarios.
            fotografia (list): Fotografia.

        Returns:
            dict: Response.
        """

        if guard_id:
            user_id = guard_id
        elif guards:
            user_id = guards[0]
        else:
            user_id = self.user.get('user_id')

        employee =  self.Employee.get_employee_data(user_id=user_id, get_one=True)
        user_data = self.lkf_api.get_user_by_id(user_id)
        timezone = user_data.get('timezone', 'America/Monterrey')
        now_datetime =self.today_str(timezone, date_format='datetime')
        last_chekin = {}

        if not checkin_id:
            return self.LKFException({"msg":"No encontramos un checking valido del cual podemos hacer checkout...", "title": "Advertencia"})

        is_caseta_open = self.is_boot_available(location, area)
        if not is_caseta_open:
            msg = f"No se puede hacer check-out sin antes haber hecho check-in. Caseta: {location} - {area}."
            return self.LKFException({"msg":msg, "title": "Advertencia"})

        record = self.get_record_by_id(checkin_id)
        checkin_answers = record['answers']
        folio = record['folio']
        area = checkin_answers.get(self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID,{}).get(self.f['area'])
        location = checkin_answers.get(self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID,{}).get(self.f['location'])
        rec_guards = checkin_answers.get(self.checkin_fields['guard_group'])
        guards_in = sum(
            1
            for guard in rec_guards
            if not guard.get(self.checkin_fields['checkout_date'])
        )
        for guard in rec_guards:
            fecha_cierre_turno = guard.get(self.checkin_fields['checkout_date'])
            guard_id = self.unlist(guard.get(self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID, {}).get(self.mf['id_usuario']))
            actual_guard_id = self.unlist(employee.get('usuario_id'))
            if not fecha_cierre_turno and guards_in > 1 and guard_id == actual_guard_id:
                resp = self.do_checkout_aux_guard(user_id=guard_id, checkin_id=checkin_id, guards=[actual_guard_id], location=location, area=area, fotografia=fotografia)
                return resp

        if not guards:
            checkin_answers[self.checkin_fields['commentario_checkin_caseta']] = \
                checkin_answers.get(self.checkin_fields['commentario_checkin_caseta'],'')
            checkin_answers[self.checkin_fields['checkin_type']] = 'cerrada'
            checkin_answers[self.checkin_fields['boot_checkout_date']] = now_datetime
            checkin_answers[self.checkin_fields['forzar_cierre']] = 'regular'

            if comments:
                checkin_answers[self.checkin_fields['commentario_checkin_caseta']] += comments + ' '
            if forzar:
                checkin_answers[self.checkin_fields['commentario_checkin_caseta']] += f"Cerrado por: {employee.get('worker_name')}"
                checkin_answers[self.checkin_fields['forzar_cierre']] = 'forzar'

        data = self.lkf_api.get_metadata(self.CHECKIN_CASETAS)
        checkin_answers = self.check_in_out_employees('out', now_datetime, checkin=checkin_answers, employee_list=guards)
        data['answers'] = checkin_answers

        if fotografia:
            checkin_answers.update({
                self.checkin_fields['fotografia_cierre_turno']: fotografia
            })

        print('user_id usado=', user_id)
        print('employee timezone=', employee.get('cat_timezone'), employee.get('timezone'))
        print('timezone final=', timezone)
        print('now_datetime=', now_datetime)

        response = self.lkf_api.patch_record( data=data, record_id=checkin_id)
        if response.get('status_code') in [200, 201, 202]:
            if employee:
                record_id = self.search_guard_asistance(location, area, self.unlist(employee.get('usuario_id')))
                asistencia_answers = {
                    self.f['foto_cierre_turno']: fotografia,
                    self.checkin_fields['checkin_type']: 'cerrar_turno',
                }
                print('asistencia_answers', asistencia_answers)
                res = self.lkf_api.patch_multi_record(answers=asistencia_answers, form_id=self.REGISTRO_ASISTENCIA, record_id=record_id)
                if res.get('status_code') in [200, 201, 202]:
                    response.update({'registro_de_asistencia': 'Correcto'})
                else:
                    response.update({'registro_de_asistencia': 'Error'})
        elif response.get('status_code') == 401:
            return self.LKFException({"title": "Advertencia", "msg":"El guardia NO tiene permisos sobre el formulario de cierre de casetas"})
        return response

    def search_guard_asistance(self, location, area, guard):
        query = [
            {"$match": {
                "deleted_at":{"$exists":False},
                "form_id": self.REGISTRO_ASISTENCIA,
                f"answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['location']}": location,
                f"answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['area']}": area,
                f"answers.{self.f['fecha_cierre_turno']}": {"$exists": False},
                "created_by_id": guard,
            }},
            {"$sort": {"created_at": -1}},
            {"$project": {
                "_id": 1,
            }}
        ]
        resp = self.format_cr(self.cr.aggregate(query))
        format_resp = []
        if resp:
            format_resp = [r['_id'] for r in resp]
        return format_resp

    def do_out(self, qr, location, area, gafete_id=None, record_id=None):
        '''
            Realiza el cambio de estatus de la forma de bitacora, relacionada a la salida, como parametro
            es necesesario enviar el nombre del visitante que es el unico dato qu se encuentra en la forma
        '''
        response = False
        last_check_out = self.get_last_user_move(qr, location, record_id)
        print("last", last_check_out)
        if last_check_out.get('status_gafete') and last_check_out.get('status_gafete')!= "entregado":
            self.LKFException({"status_code":400, "msg":f"Se necesita liberar el gafete antes de regitrar la salida"})
        if not location:
            self.LKFException({"status_code":400, "msg":f"Se requiere especificar una ubicacion de donde se realizara la salida."})
        if not area:
            self.LKFException({"status_code":400, "msg":f"Se requiere especificar el area de donde se realizara la salida."})
        if last_check_out.get('ubicacion_entrada') != location:
            self.LKFException({"status_code":400, "msg":f"Este usuario ingreso en {location} y no puede salir en {last_check_out.get('ubicacion_entrada')}."})
        if last_check_out.get('folio'):
            folio = last_check_out.get('folio',0)
            checkin_date_str = last_check_out.get('checkin_date')
            checkin_date = self.date_from_str(checkin_date_str)
            tz_mexico = pytz.timezone('America/Mexico_City')
            now = datetime.now(tz_mexico)
            fecha_hora_str = now.strftime("%Y-%m-%d %H:%M:%S")
            duration = time_module.strftime('%H:%M:%S', time_module.gmtime(
                self.date_2_epoch(fecha_hora_str) - self.date_2_epoch(checkin_date_str)
            ))
            if self.user_in_facility(status_visita=last_check_out.get('status_visita')):
                answers = {
                    f"{self.mf['tipo_registro']}":'salida',
                    f"{self.mf['fecha_salida']}":fecha_hora_str,
                    f"{self.mf['duracion']}":duration,
                    f"{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}": {
                        f"{self.mf['nombre_area_salida']}": area,
                    },

                }
                response = self.lkf_api.patch_multi_record( answers=answers, form_id=self.BITACORA_ACCESOS, folios=[folio])
        if not response:
            self.LKFException({"status_code":400, "msg":f"El usuario no se encuentra dentro de la Ubicacion: {location}."})
        return response         

    def do_validacion_certificado(self, cert, detail=False):
        res = {}
        nombre = cert['nombre_permiso']
        status_doc = cert.get('status_doc_cetrificado', 'vencido')
        status = cert.get('status_cetrificado', 'pendiente')
        if detail:
            data = {}
            data['documento'] = status_doc
            data['autorizacion'] = status
        if status_doc.lower() == 'activo' and status.lower() == 'autorizado':
            if detail:
                data['status'] = 'Autorizado'
            else:
                res = "Autorizado"
        else:
            if detail:
                data['status'] = 'NO Autorizado'
            else:
                res = "NO Autroizado"
        if detail:
            res[nombre] = data
        return res

    def calcula_total_depositos(self, answers=None):
        if answers is None:
            answers = self.answers
        depositos = answers.get(self.incidence_fields['datos_deposito_incidencia'],[])
        return sum([x[self.incidence_fields['cantidad']] for x in depositos])

    def catalogos_pase_area(self, location_name):
        user_id= self.user.get("user_id")
        res={
            "areas_by_location" : self.Location.get_areas_by_location(location_name)
        }
        return res

    def catalogos_pase_location(self):
        user_id = self.user.get("user_id")
        match_query = {
            "deleted_at": {"$exists": False},
            "form_id": self.Employee.CONF_AREA_EMPLEADOS,
        }
        if user_id:
            match_query[f"answers.{self.Employee.EMPLOYEE_OBJ_ID}.{self.Employee.employee_fields['user_id_id']}"] = user_id

        query = [
            {'$match': match_query},
            {'$unwind': f"$answers.{self.mf['areas_grupo']}"},
            {'$project': {
                '_id': 0,
                'area': f"$answers.{self.mf['areas_grupo']}.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
                'nombre_area': f"$answers.{self.mf['areas_grupo']}.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}",
                'set_as': f"$answers.{self.mf['areas_grupo']}.{self.Employee.f['area_default']}",
            }},
        ]

        response = self.cr.aggregate(query)

        res = {
            'ubicaciones_user': [],
            'ubicaciones_default': [],
            'ubicaciones_detalle': [],
        }

        detalle_por_ubicacion = {}

        for x in response:
            area = x.get('area')
            set_as = x.get('set_as')
            nombre_area = x.get('nombre_area')
            es_default_area = set_as == 'default'

            # --- ubicaciones_user (sin duplicados) ---
            if area not in res['ubicaciones_user']:
                res['ubicaciones_user'].append(area)

            # --- ubicaciones_default ---
            if es_default_area and area not in res['ubicaciones_default']:
                res['ubicaciones_default'].append(area)

            # --- detalle por ubicación ---
            if area not in detalle_por_ubicacion:
                detalle_por_ubicacion[area] = {
                    'ubicacion': area,
                    'es_default': False,
                    'areas': [],
                }

            ya_existe = any(
                a['nombre_area'] == nombre_area and a['es_default'] == es_default_area
                for a in detalle_por_ubicacion[area]['areas']
            )
            if not ya_existe:
                detalle_por_ubicacion[area]['areas'].append({
                    'nombre_area': nombre_area,
                    'es_default': es_default_area,
                })

            if es_default_area:
                detalle_por_ubicacion[area]['es_default'] = True

        res['ubicaciones_detalle'] = list(detalle_por_ubicacion.values())

        return res

    def catalagos_pase_no_jwt(self, qr_code):
        # se quito porque ya no se edita el pase
        pass_selected= self.get_pass_custom(qr_code)
        res={"pass_selected":pass_selected}
        return res

    def catalogo_categoria(self, options={}):
        catalog_id = self.ESTADO_ID
        form_id = self.PASE_ENTRADA
        group_level = options.get('group_level',1)
        return self.catalogo_view(catalog_id, form_id)

    def catalogo_estados(self, options={}):
        catalog_id = self.ESTADO_ID
        form_id = self.PASE_ENTRADA
        return self.catalogo_view(catalog_id, form_id)

    def catalogo_incidencias(self, cat="", sub_cat=""):
        # selector = {} #Aqui filtras igual que con mongo de que answers.tal.tal: name_hotel
        # fields = ["_id"] #Aqui que te retorne los campos que quieras

        # mango_query = {
        #     "selector": selector,
        #     "fields": fields,
        #     "limit": 1000
        # }

        # row_catalog = self.lkf_api.search_catalog(self.LISTA_INCIDENCIAS_CAT_ID, mango_query)
        # print(f"Consulta de catálogo: {row_catalog}")



        catalog_id = self.LISTA_INCIDENCIAS_CAT_ID
        form_id = self.BITACORA_INCIDENCIAS
        options={}
        search=""
        # cat= ""
        # sub_cat= ""
        
        if cat and sub_cat:
            options = {
                "group_level": 3,
                "startkey": [cat,sub_cat],
                "endkey": [cat, f"{sub_cat}\n"]
            }
            search="incidence"
        else:
            if cat and not sub_cat:
                options = {
                    "group_level": 2,
                    "startkey": [cat],
                    "endkey": [f"{cat}\n"]
                }
                search="sub_catalog"
            if sub_cat and not cat:
                options = {
                    "group_level": 3,
                    "startkey": [sub_cat],
                    "endkey": [f"{sub_cat}\n"]
                }
                search="incidence"

        res = self.lkf_api.catalog_view(catalog_id, form_id, options)
        print("CATALGOO", catalog_id, form_id,res)
        formatted= {
            "selected":cat, 
            "data":res, 
            "type": search
        }
        if res == [None] and cat and not sub_cat:
            res_obj = self.catalogo_incidencias(cat="", sub_cat= cat)
            formatted["selected"] = cat
            formatted["data"] = res_obj["data"] 
            formatted["type"] = "incidence"
        print("formatedo", simplejson.dumps(formatted, indent=4))
        return formatted

    def catalogo_vehiculos(self, options={}):
        catalog_id = self.AF.TIPO_DE_VEHICULO_ID
        form_id = self.PASE_ENTRADA
        res= self.catalogo_view(catalog_id, form_id, options=options)
        return res

    def catalogo_tipo_equipo(self):
        catalog_id = self.TIPO_EQUIPOS_CAT_ID
        form_id = self.PASE_ENTRADA
        return self.catalogo_view(catalog_id, form_id)

    def catalogo_view(self, catalog_id, form_id, options={}, detail=False):
        catalog_id = catalog_id
        form_id = form_id
        res = self.lkf_api.catalog_view(catalog_id, form_id, options)
        if detail:
            if res and len(res) > 0:
                res = self._labels(res[0])
                res = {k:v[0] for k,v in res.items() if len(v)>0}
        return res

    def get_areas_by_locations(self, location_names):
        catalog_id = self.AREAS_DE_LAS_UBICACIONES_CAT_ID
        form_id = self.PASE_ENTRADA
        res_list = []
        response = {}

        if not isinstance(location_names, list):
            location_names = [location_names]

        if location_names:
            for l in location_names:
                options = {
                    'startkey': [l],
                    'endkey': [f"{l}\n",{}],
                    'group_level':2
                }
                res = self.catalogo_view(catalog_id, form_id, options)
                if res and isinstance(res, list):
                    res_list.extend(res)

            response.update({
                "areas_by_location": list(set(res_list))
            })

        return response

    def format_data_area(self, answers):
        formatted_data = {}
        formatted_data.update({
            'option': answers.get(self.f['option_update_qr'], ''),
            'ubicacion': answers.get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.Location.f['location'], ''),
            'area': answers.get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.Location.f['area'], ''),
            'qr_anterior': answers.get(self.f['anterior_qr'], ''),
            'qr_nuevo': answers.get(self.f['new_qr'], '')
        })
        return formatted_data

    def get_record_ubicacion(self, ubicacion=None, area=None, tag_id_area=None):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.Location.AREAS_DE_LAS_UBICACIONES,
        }
        if ubicacion:
            match_query.update({
                f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": ubicacion,
            })
        if area:
            match_query.update({
                f"answers.{self.Location.f['area']}": area
            })
        if tag_id_area:
            match_query.update({
                f"answers.{self.f['tag_id_area_ubicacion']}": tag_id_area
            })

        query = [
            {'$match': match_query },
            {'$project': {
                'folio': {'$ifNull': ['$folio', '']},
                '_id': 1,
                'ubicacion': f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}",
                'area': f"$answers.{self.Location.f['area']}",
                'tag_id_area': {'$ifNull': [f"$answers.{self.f['tag_id_area_ubicacion']}", '']},
            }},
            {'$limit': 1},
            {'$sort':{'folio':-1}},
        ]
        res = self.format_cr(self.cr.aggregate(query))
        res = self.unlist(res)
        return res

    def update_area_tag_id(self, data):
        option = data.get('option', '')
        ubicacion = data.get('ubicacion', None)
        area = data.get('area', None)
        tag_id = data.get('qr_anterior', None)

        area_ubicacion_data = None
        if option == 'seleccionar_area_y_ubicacion':
            area_ubicacion_data = self.get_record_ubicacion(ubicacion=ubicacion, area=area)
        elif option == 'escanear_qr_anterior':
            area_ubicacion_data = self.get_record_ubicacion(tag_id_area=tag_id)
            if not area_ubicacion_data:
                return {
                    'status': 'error',
                    'details': 'No se encontró el QR anterior en ningun area registrada, favor de verificar el QR escaneado.'
                }

        answers = {}
        record_id = (area_ubicacion_data or {}).get('_id', '')
        answers[self.f['tag_id_area_ubicacion']] = data.get('qr_nuevo', '')

        if answers:
            response = self.lkf_api.patch_multi_record(answers=answers, form_id=self.Location.AREAS_DE_LAS_UBICACIONES, record_id=[record_id])
            if response.get('status_code', 0) in [200, 201, 202]:
                return {
                    'status': 'success',
                    'details': 'QR actualizado correctamente',
                }
            else:
                return {
                    'status': 'error',
                    'details': 'Hubo un error al actualizar el QR',
                }
        return {
            'status': 'error',
            'details': 'Hubo un error inesperado, favor de revisar los logs...',
        }

    def get_attendance_records(self, guardias_dentro):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.REGISTRO_ASISTENCIA,
                "created_by_id": {"$in": guardias_dentro},
                f"answers.{self.f['start_shift']}": {"$exists": True},
                f"answers.{self.f['end_shift']}": {"$exists": False}
            }},
            {"$project": {
                "_id": 1,
                "timezone": 1,
            }}
        ]
        data = self.format_cr(self.cr.aggregate(query))
        return data

    def do_checkout_all(self):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.CHECKIN_CASETAS,
                f"answers.{self.checkin_fields['checkin_type']}": "abierta"
            }},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "timezone": 1,
                f"{self.checkin_fields['checkin_type']}": f"$answers.{self.checkin_fields['checkin_type']}",
                f"{self.mf['guard_group']}": f"$answers.{self.mf['guard_group']}"
            }}
        ]
        data = list(self.cr.aggregate(query))

        checkin_responses_details = []
        guardias_dentro = []
        for item in data:
            ahora = datetime.now(pytz.timezone(item.get('timezone', 'America/Mexico_City'))).replace(tzinfo=None)
            count_guardias_dentro = 0
            item['_id'] = str(item['_id'])
            registro_de_guardias = item.get(f'{self.mf["guard_group"]}', [])
            format_guardias_dentro = {}
            for index, guardia in enumerate(registro_de_guardias):
                checkin_date = guardia.get(self.checkin_fields['checkin_date'])
                if isinstance(checkin_date, str):
                    checkin_date = datetime.strptime(checkin_date, '%Y-%m-%d %H:%M:%S')
                if checkin_date \
                    and ahora > checkin_date + timedelta(hours=10) \
                    and guardia.get(self.checkin_fields['checkin_status']) == 'entrada':
                    guardias_dentro.append(self.unlist(guardia.get(self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID, {}).get(self.mf['id_usuario'], [])))
                    guardia[self.checkin_fields['checkin_status']] = 'salida'
                    guardia[self.checkin_fields['checkout_date']] = ahora.strftime('%Y-%m-%d %H:%M:%S')
                if guardia.get(self.checkin_fields['checkin_status']) == 'entrada':
                    count_guardias_dentro += 1
                format_guardias_dentro[index] = guardia
            if count_guardias_dentro == 0:
                item[self.checkin_fields['checkin_type']] = 'cerrada'
                item[self.checkin_fields['boot_checkout_date']] = ahora.strftime('%Y-%m-%d %H:%M:%S')

            answers = {}
            answers[self.checkin_fields['checkin_type']] = item.get(self.checkin_fields['checkin_type'])
            answers[self.mf["guard_group"]] = format_guardias_dentro
            folio = item.get('folio')
            if len(guardias_dentro) > 0:
                response = self.lkf_api.patch_multi_record(answers=answers, form_id=self.CHECKIN_CASETAS, folios=[folio,])
                checkin_responses_details.append({
                    'response': response,
                    'item': item
                })

        guardias_dentro = list(set(guardias_dentro))
        data = self.get_attendance_records(guardias_dentro)
        asistencia_responses_details = []
        if data:
            for item in data:
                timezone = item.get('timezone', 'America/Mexico_City')
                ahora = datetime.now(pytz.timezone(timezone)).replace(tzinfo=None)
                answers = {
                    self.f['fecha_cierre_turno']: ahora.strftime('%Y-%m-%d %H:%M:%S'),
                    self.f['comment_checkout']: 'Cierre de turno automatico - 10 horas'
                }
                response = self.lkf_api.patch_multi_record(answers=answers, form_id=self.REGISTRO_ASISTENCIA, record_id=[item.get('_id'),])
                asistencia_responses_details.append({
                    'response': response,
                    'item': item
                })
        return {
            'checkin_responses_details': checkin_responses_details,
            'asistencia_responses_details': asistencia_responses_details
        }

    def get_rondines_by_status(self, status_list=['programado', 'en_proceso']):
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                f"answers.{self.f['estatus_del_recorrido']}": {"$in": status_list},
            }},
            {'$project': {
                '_id': 1,
                'fecha_programacion': f"$answers.{self.f['fecha_programacion']}",
                'rondinero_id': f"$answers.{self.USUARIOS_OBJ_ID}.{self.mf['id_usuario']}",
                'answers': f"$answers",
                'timezone':1,
                'folio':1,
                'created_by_email':1,
            }},
            {'$sort': {
                'fecha_programacion': -1
            }},
        ]
        rondines = self.format_cr(self.cr.aggregate(query))
        return rondines

    def notificacion_rondin_no_arrancado(self, rondin, ahora, fecha_programacion, tolerancia=15):
        """
        Envia notificacion de que el rondin no se arranco, despues de tiempo marcado como tolerancia

        params:
        rondin: ronidn a evaluar
        tolerancia: tiempo en minutos
        """
        fecha_programacion_str = rondin.get('fecha_programacion')
        if ahora > fecha_programacion + timedelta(minutes=tolerancia):
            asignado_a = rondin.get('new_user_complete_name','No asignado')
            email_to = [rondin.get('created_by_email'), 'josepato@linkaform.com']
            titulo = f"Rondin: {rondin.get('nombre_del_recorrido')},  asignado a: {asignado_a}, no arrancado en: {rondin.get('incidente_location')}"
            msg = titulo
            msg += f"Fecha programada: {fecha_programacion_str} /"
            msg += f"Fecha actual: {ahora.strftime('%Y-%m-%d %H:%M')}  /"
            msg += f"Tolerancia: {tolerancia} minutos / "
            msg += f"Retardo en minutos: {round((ahora - fecha_programacion).total_seconds() / 60, 0)}  "
            data = {
                'email_from': 'no-reply@linkaform.com',
                'titulo': titulo,
                'nombre': titulo,
                'mensaje': msg,
                'enviado_desde': 'Bitacora de Rondines',
            }
            for email in email_to:
                data['email_to'] = email
                self.send_email_by_form(data)
        return True

    def close_rondines(self, list_of_rondines):
        """
        Cierra los rondines que esten en status programados y que tengan mas de 24 de programdos
        o en progreso y que tengan mas de 1 hr de su ultimo check.

        Si existe mas de un rondin con el mismo nombre en la misma ubicacion, se cierra el mas antiguo.
        """
        answers = {}
        ahora = datetime.now(pytz.timezone('America/Mexico_City'))

        rondines_expirados = []
        rondines_en_proceso_vencidos = []
        rondines_por_ubicacion_nombre = {}
        for rondin in list_of_rondines:
            user_id = self.unlist(rondin.get('rondinero_id', 0))
            user_data = self.lkf_api.get_user_by_id(user_id)
            user_timezone = user_data.get('timezone', 'America/Mexico_City')
            tz = pytz.timezone(user_timezone)
            ahora = datetime.now(tz)
            estatus = rondin.get('estatus_del_recorrido')
            fecha_programacion_str = rondin.get('fecha_programacion')
            ubicacion = rondin.get('incidente_location')
            nombre = rondin.get('nombre_del_recorrido')

            rondines_por_ubicacion_nombre[ubicacion] = rondines_por_ubicacion_nombre.get(ubicacion, [])
            if estatus == 'programado' and fecha_programacion_str:
                fecha_programacion = tz.localize(datetime.strptime(fecha_programacion_str, '%Y-%m-%d %H:%M:%S'))

                if nombre in rondines_por_ubicacion_nombre[ubicacion]:
                    rondines_expirados.append(rondin)
                else:
                    rondines_por_ubicacion_nombre[ubicacion].append(nombre)

                if ahora > fecha_programacion + timedelta(hours=24):
                    rondines_expirados.append(rondin)
            elif estatus == 'en_proceso':
                areas = rondin.get('areas_del_rondin', [])
                ultima_fecha = None
                for area in areas:
                    fecha_str = area.get('fecha_hora_inspeccion_area', '')
                    if fecha_str:
                        fecha = tz.localize(datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S'))
                        if not ultima_fecha or fecha > ultima_fecha:
                            ultima_fecha = fecha
                if ultima_fecha and ahora > ultima_fecha + timedelta(minutes=15):
                    rondines_en_proceso_vencidos.append(rondin)

        rondines_expirados = rondines_expirados + rondines_en_proceso_vencidos
        rondines_ids = [i.get('_id') for i in rondines_expirados]
        rondines_ids = list(set(rondines_ids))

        db_name = f'clave_{self.user.get("user_id")}'
        cr_db = self.get_couch_user_db(db_name)

        records = list(cr_db.find({
            "selector": {"_id": {"$in": rondines_ids}}
        }))

        for record in records:
            record['inbox'] = False
            record['status_user'] = 'closed'
        cr_db.update(records)

        answers[self.f['estatus_del_recorrido']] = 'cerrado'
        answers[self.f['fecha_fin_rondin']] = ahora.strftime('%Y-%m-%d %H:%M:%S')

        if answers:
            res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.BITACORA_RONDINES, record_id=rondines_ids)
            return res

    def calcluta_tiempo_traslados(self, answers):
        fecha_inicio = self.date_2_epoch(answers.get(self.f['fecha_inicio_rondin']))
        areas_visitadas = answers.get(self.f['areas_del_rondin'], [])
        areas_con_fecha = [
            (self.date_2_epoch(a.get(self.f['fecha_inspeccion_area'])), a)
            for a in areas_visitadas
        ]
        areas_con_fecha = sorted(
            [(epoch, a) for epoch, a in areas_con_fecha if epoch],
            key=lambda x: x[0]
        )

        if not areas_con_fecha:
            return answers

        if not fecha_inicio:
            fecha_inicio = areas_con_fecha[0][0]
            answers[self.f['fecha_inicio_rondin']] = fecha_inicio

        first_epoch = areas_con_fecha[0][0]
        for epoch, area in areas_con_fecha:
            area[self.f['duracion_traslado_area']] = round((epoch - first_epoch) / 60, 2)

        fecha_final = areas_con_fecha[-1][0]
        cantidad_inspeccionadas = len(areas_con_fecha)

        answers[self.f['duracion_rondin']] = round((fecha_final - fecha_inicio) / 60, 2)
        answers[self.f['porcentaje_obtenido_bitacora']] = (
            str(round((cantidad_inspeccionadas / len(areas_visitadas)) * 100, 2)) + '%'
        )
        answers[self.f['cantidad_areas_inspeccionadas']] = (
            f"{cantidad_inspeccionadas}/{len(areas_visitadas)}"
        )
        answers[self.f['areas_del_rondin']] = [a for _, a in areas_con_fecha] + [
            a for epoch, a in zip(
                [self.date_2_epoch(a.get(self.f['fecha_inspeccion_area'])) for a in areas_visitadas],
                areas_visitadas
            ) if not epoch
        ]

        if answers.get(self.f['estatus_del_recorrido']) in ['realizado', 'cerrado']:
            fecha_final_str = datetime.fromtimestamp(fecha_final).strftime('%Y-%m-%d %H:%M:%S')
            answers[self.f['fecha_fin_rondin']] = fecha_final_str
        return answers

    def get_and_set_areas_recorrido(self, answers):
        location = answers.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.Location.f['location'], '')
        area = answers.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.Location.f['area'], '')
        name_rondin = answers.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.mf['nombre_del_recorrido'], '')
        match = {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.CONFIGURACION_RECORRIDOS_FORM,
                f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.mf['nombre_del_recorrido']}": name_rondin
            }}
        if area:
            match["$match"].update(
                {f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.mf['nombre_area_salida']}": area}
                )
        query = [
            match,
            {"$project": {
                "_id": 0,
                "rondin_areas": f"$answers.{self.f['grupo_de_areas_recorrido']}",
                "tipo_asignacion": f"$answers.{self.rondin_keys['tipo_asignacion']}",
                "grupo_asignado_a": f"$answers.{self.rondin_keys['grupo_asignado_a']}",
                "id_grupo": f"$answers.{self.GRUPOS_CAT_OBJ_ID}.{self.mf['id_grupo']}",
                "roles": f"$answers.{self.f['grupo_roles']}"
            }}
        ]
        res = self.cr.aggregate(query)
        format_res = list(res)
        if format_res:
            areas_recorrido = self.unlist(format_res)
            answers[self.f['areas_del_rondin']] = areas_recorrido.get('rondin_areas', [])
            answers[self.rondin_keys['tipo_asignacion']] = areas_recorrido.get('tipo_asignacion')
            answers[self.rondin_keys['grupo_asignado_a']] = areas_recorrido.get('grupo_asignado_a', [])
            if areas_recorrido.get('id_grupo'):
                answers[self.GRUPOS_CAT_OBJ_ID] = {self.mf['id_grupo']:areas_recorrido['id_grupo']}
            return True
        return False

    def normalize_user(self, raw_user) -> dict:
        """
        Normaliza un usuario independientemente de si viene de:
        - un catálogo de LinkaForm (keys = field_obj_ids)
        - la API de grupos (keys = name, email, id, username)
        """
        if self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID in raw_user:
            catalog = raw_user[self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID]
            return {
                self.mf['nombre_usuario']: catalog.get(self.mf['nombre_empleado']),
                self.mf['id_usuario']:     catalog.get(self.mf['id_usuario']),
                self.mf['email_visita_a']: catalog.get(self.mf['email_visita_a']),
            }

        if 'name' in raw_user or 'email' in raw_user:
            return {
                self.mf['nombre_usuario']: raw_user.get('name'),
                self.mf['id_usuario']:     [raw_user.get('id')],
                self.mf['email_visita_a']: [raw_user.get('email')],
            }

        return {}

    def get_and_set_user(self, answers, record_id, current_record):
        tipo_asignacion = answers.get(self.rondin_keys['tipo_asignacion'])
        grupo_asignado_a = answers.get(self.rondin_keys['grupo_asignado_a'])
        if tipo_asignacion and tipo_asignacion in ('persona_especifica', 'grupo'):
            if tipo_asignacion == 'grupo':
                grupo_asignado_a = self.lkf_api.get_group_users(self.unlist(answers[self.GRUPOS_CAT_OBJ_ID][self.mf['id_grupo']]))
            new_metadata = deepcopy(current_record)
            new_metadata.pop('answers', None)
            new_metadata.pop('_id', None)
            for raw_user in grupo_asignado_a:
                user = self.normalize_user(raw_user)
                child_anwers = deepcopy(answers)
                child_anwers[self.rondin_keys['registro_padre']] = record_id
                if not answers.get(self.USUARIOS_OBJ_ID):
                    answers[self.USUARIOS_OBJ_ID] = user
                else:
                    child_anwers[self.USUARIOS_OBJ_ID] = user
                    parent_record = f"{self.settings.config['PROTOCOL']}://{self.settings.config['HOST']}/#/records/detail/" + record_id
                    child_anwers[self.rondin_keys['registro_padre']] = parent_record
                    new_metadata['answers'] = child_anwers
                    self.lkf_api.post_forms_answers(new_metadata)
        else:
            location = answers.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.Location.f['location'])
            user_info = self.get_active_guards_in_location(location)
            if not user_info:
                return False

            answers[self.USUARIOS_OBJ_ID] = {
                self.mf['nombre_usuario']: user_info.get('created_by_name', ''),
                self.mf['id_usuario']: [user_info.get('created_by_id', '')],
                self.mf['email_visita_a']: [user_info.get('created_by_email', '')],
            }
        return True

    # ============================================
    # Check de rondines por tag fisico (migrado de create_record_check.py)
    # IDs de formulario/campo dejados como literales, tal como en el legacy
    # (integracion especifica que no pasa por self.f/self.mf).
    # ============================================

    def get_key_answer(self, tagId):
        dic_res = {}
        match_query = {
            'deleted_at':{"$exists":False},
            '6762f7b0922cc2a2f57d4044':tagId,
        }
        mango_query = {"selector":
            {"answers":
                {"$and":[match_query]}
            },
            "limit":1,
            "skip":0
        }
        res = self.lkf_api.search_catalog(126716, mango_query)
        if len(res) > 0:
            dic_res['keyAnswers'] = res[0].get('6762f7e30c001206307d4053','')
            dic_res['location'] = res[0].get('663e5d44f5b8a7ce8211ed0f','')
            dic_res['ubicacion'] = res[0].get('663e5c57f5b8a7ce8211ed0b','')

        if dic_res :
            return dic_res
        return None

    def set_add_record_check(self, data_record, folio_bitacora_update):
        tag_id = data_record.get('tagId','')
        folio = data_record.get('folio','')
        ubicacion = data_record.get('ubicacion','')
        rondin = data_record.get('rondin','')
        dic_check = data_record.get('list_checks',[])
        comment = data_record.get('comment','')
        list_imgs = data_record.get('list_img',[])
        dic_catalog = self.get_key_answer(tag_id)
        answers_check = dic_catalog.get('keyAnswers','')
        location_check = dic_catalog.get('location','')
        list_check =  [key for key, value in dic_check.items() if value is True]
        if list_check != None:
            dic_response = {
                '674e31186a5f08049c82844c':{
                    '674e31186a5f08049c82844e':rondin,
                    '674e31186a5f08049c82844d':folio,
                },
                '674e2ac6e3e7c31132939288':{
                    '663e5c57f5b8a7ce8211ed0b':ubicacion,
                    '663e5d44f5b8a7ce8211ed0f':location_check,
                },
                '676461772f3a94a85b055e91' : 'rondin_programado',
                answers_check : list_check,
                '6740cbd734849293fe5a2735' : list_imgs,
                '6740cbd734849293fe5a2736' : comment,
            }
            metadata = self.lkf_api.get_metadata(126213)
            metadata['answers'] = dic_response
            dic_res = {'status_create':'400'}
            resp_create = self.lkf_api.post_forms_answers_list(metadata)
            if len(resp_create) == 1:
                data = resp_create[0].get('json',{})
                dic_res['status_create'] = resp_create[0].get('status_code','400')
                dic_res['id_request'] = str(data.get('id',''))
                dic_res['folio'] = data.get('folio','')
                res_update = self.update_bitacora_record(data_record, dic_res['id_request'], folio_bitacora_update)
                dic_res['res_update'] = res_update
            return dic_res
        else:
            return dic_res

    def update_bitacora_record(self, data, id_record, folio):
        location = data.get('location','')
        list_imgs = data.get('list_img',[])
        comment = data.get('comment','')
        str_url = f'https://app.linkaform.com/#/records/detail/{id_record}'

        answers_set = {
            '674e2e9eecf32979019392af':{
                '663e5d44f5b8a7ce8211ed0f':location,
            },
            '6760a908a43b1b0e41abad6b': self.today_str(date_format='datetime'),
            '66462b9d7124d1540f962087': list_imgs,
            '66462b9d7124d1540f962088': comment,
            '6750adb2936622aecd075607': str_url,
        }
        answers = {
            '66462aa5d4a4af2eea07e0d1':{'-1':answers_set}
        }
        res = self.lkf_api.patch_multi_record(answers = answers, form_id=126790, folios=[folio])
        return res

    def set_add_inspection_record(self, data):
        tag_id = data.get('tagId','')
        dic_check = data.get('list_checks',[])
        comment = data.get('comment','')
        list_imgs = data.get('list_img',[])
        dic_catalog = self.get_key_answer(tag_id)
        answers_check = dic_catalog.get('keyAnswers','')
        location_check = dic_catalog.get('location','')
        ubicacion_check = dic_catalog.get('ubicacion','')
        list_check =  [key for key, value in dic_check.items() if value is True]
        if list_check != None:
            dic_response = {
                '674e2ac6e3e7c31132939288':{
                    '663e5c57f5b8a7ce8211ed0b':ubicacion_check,
                    '663e5d44f5b8a7ce8211ed0f':location_check,
                },
                '676461772f3a94a85b055e91' : 'inspección_de_área',
                answers_check : list_check,
                '6740cbd734849293fe5a2735' : list_imgs,
                '6740cbd734849293fe5a2736' : comment,
            }
            metadata = self.lkf_api.get_metadata(126213)
            metadata['answers'] = dic_response
            dic_res = {'status_create':'400'}
            resp_create = self.lkf_api.post_forms_answers_list(metadata)
            if len(resp_create) == 1:
                dic_res['status_create'] = resp_create[0].get('status_code','400')
            return dic_res

    def set_add_record_bitacora_tag(self, tagId, config):
        res_catalog = self.get_information_catalog(tagId)
        ubication_location = res_catalog.get('ubication_location','')

        dic_response = {
            self.f['fecha_inicio_rondin']: self.today_str(date_format='datetime'),
            self.f['status_user'] : 'en_proceso',
            self.CONFIGURACION_RECORRIDOS_OBJ_ID : {
                self.mf['ubicacion']:ubication_location,
                self.f['nombre_recorrido']:config,
            },
        }
        metadata = self.lkf_api.get_metadata(126790)
        metadata['answers'] = dic_response
        resp_create = self.lkf_api.post_forms_answers_list(metadata)
        dic_res = {'status_request':'400'}
        if len(resp_create) == 1:
            data = resp_create[0].get('json',{})
            dic_res['status_request'] = resp_create[0].get('status_code','400')
            dic_res['id_request'] = str(data.get('id',''))
            dic_res['folio'] = data.get('folio','')
        return dic_res

    def get_information_catalog(self, tag_id):
        dic_res = {}
        match_query = {
            'deleted_at':{"$exists":False},
            '6762f7b0922cc2a2f57d4044':{"$eq":tag_id},
        }
        mango_query = {"selector":
            {"answers":
                {"$and":[match_query]}
            },
            "limit":1,
            "skip":0
        }
        res = self.lkf_api.search_catalog(126716, mango_query)
        for item in res:
            name_location = item.get('663e5d44f5b8a7ce8211ed0f','')
            type_location = item.get('663e5e68f5b8a7ce8211ed18','')
            image_location = item.get('6763096aa99cee046ba766ad',[])
            ubication_location = item.get('663e5c57f5b8a7ce8211ed0b','')
            direction_location = item.get('663a7e0fe48382c5b1230901','')
            last_record = self.get_last_record_check(name_location)

            dic_res = {
                "name_location": name_location,
                "type_location": type_location,
                "image_location": image_location,
                "ubication_location": ubication_location,
                "direction_location": direction_location,
                "last_record": last_record,
            }
        return dic_res

    def get_format_config(self, data):
        list_return = []
        for item in data:
            folio = item.get('folio','')
            nombre_rondin = item.get('nombre_rondin','')
            ubicacion = item.get('ubicacion','')
            area = item.get('area',[])
            list_return.append({
                "folio":folio,
                "nombre_rondin":nombre_rondin,
                "ubicacion":ubicacion,
                "area":area,
            })
        return list_return

    def get_config_rondines(self, tag_id):
        match_query = {
            "form_id":126796,
            "deleted_at": {"$exists":False},
        }
        if tag_id :
            match_query.update({"answers.6645052ef8bc829a5ccafaf5.674e2ac6e3e7c31132939288.6762f7b0922cc2a2f57d4044":{'$in':[tag_id,[tag_id]]}})

        query = [
            {"$match": match_query},
            {"$unwind": {
                "path": "$answers.6645052ef8bc829a5ccafaf5",
                "preserveNullAndEmptyArrays": True
            }},
            {"$group": {
                "_id": "$folio",
                "nombre_rondin": {"$first": "$answers.6645050d873fc2d733961eba"},
                "ubicacion": {"$first": "$answers.674e2ac399c0a2770c82843d.663e5c57f5b8a7ce8211ed0b"},
                "areas": {
                    "$addToSet": {
                        "nombre":"$answers.6645052ef8bc829a5ccafaf5.674e2ac6e3e7c31132939288.663e5d44f5b8a7ce8211ed0f",
                        "tagId":"$answers.6645052ef8bc829a5ccafaf5.674e2ac6e3e7c31132939288.6762f7b0922cc2a2f57d4044",
                    }
                }
            }},
            {"$project": {
                "_id": 1,
                "folio": "$_id",
                "nombre_rondin": 1,
                "ubicacion": 1,
                "area": "$areas"
            }}
        ]
        result = self.cr.aggregate(query)
        result_format = self.get_format_config(result)
        return result_format

    def update_record_rondin_tag(self, folio):
        answers = {
            '6639b2744bb44059fc59eb62' : 'realizado',
        }
        res = self.lkf_api.patch_multi_record(answers = answers, form_id=126790, folios=[folio])
        res.update({'status_request':res.get('status_code')})
        return res

    def get_data_tag(self, tag_id):
        dic_res = {
            'status_request':''
        }
        match_query = {
            'deleted_at':{"$exists":False},
        }
        mango_query = {"selector":
            {"answers":
                {"$and":[match_query]}
            },
            "limit":10000,
            "skip":0
        }
        res = self.lkf_api.search_catalog(126716, mango_query)
        catalog_list = []
        flag_find = False

        for item_catalog in res:
            _id_catalog =  str(item_catalog.get('_id',None))
            tag_id_catalog =  item_catalog.get('6762f7b0922cc2a2f57d4044',None)
            ubicacion_catalog =  item_catalog.get('663e5c57f5b8a7ce8211ed0b',None)
            nombre_area_catalog =  item_catalog.get('663e5d44f5b8a7ce8211ed0f',None)
            imagen_area_catalog =  item_catalog.get('6763096aa99cee046ba766ad',None)
            if tag_id_catalog == tag_id and tag_id :
                flag_find = True
                dic_res['status_request'] = 'included'
                dic_res['data_tag'] = {
                    'ubicacion_catalog': ubicacion_catalog,
                    'nombre_area_catalog': nombre_area_catalog,
                    'imagen_area_catalog': imagen_area_catalog,
                    'tag_id_catalog': tag_id_catalog,
                }
            catalog_list.append({
                'ubicacion_catalog': ubicacion_catalog,
                'nombre_area_catalog': nombre_area_catalog,
                'imagen_area_catalog': imagen_area_catalog,
                '_id_catalog': _id_catalog,
            })

        if not flag_find:
            dic_res['status_request'] = 'not_included'
            dic_res['catalog_list'] = catalog_list
        return dic_res

    def set_update_tag(self, tag_id, list_images_dic, id_catalog_record):
        res_update = {
            '6762f7b0922cc2a2f57d4044': tag_id,
            '6763096aa99cee046ba766ad': list_images_dic,
        }
        res_update = self.lkf_api.update_catalog_multi_record( res_update, 126716, record_id=[id_catalog_record])
        dic_res = {'status_request':'400'}
        dic_res['status_request'] = res_update.get('status_code','400')
        return dic_res

    def get_last_record_check(self, location):
        match_query = {
            "form_id":126213,
            "deleted_at": {"$exists":False},
        }
        if location :
            match_query.update({"answers.674e2ac6e3e7c31132939288.663e5d44f5b8a7ce8211ed0f":{'$in':[location,[location]]}})

        query = [
            {"$match": match_query},
            {"$project": {
                "_id": 1,
                "folio": "$_id",
                "created": "$created_at",
            }},
            {'$sort': {'created': -1 }},
            {'$limit':1}
        ]
        result = self.cr.aggregate(query)
        msg_return = ''
        date = ''
        for item in result:
            date = item.get('created','')

        if date and date != '':
            if isinstance(date, str):
                fecha_creada = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
            elif isinstance(date, datetime):
                fecha_creada = date

            fecha_actual = datetime.now()
            diferencia = fecha_actual - fecha_creada
            dias_transcurridos = diferencia.days

            if dias_transcurridos == 0:
                horas_transcurridas = diferencia.seconds // 3600
                minutos_transcurridos = (diferencia.seconds % 3600) // 60
                msg_return = f'Última inspección hace {horas_transcurridas} horas y {minutos_transcurridos} minutos'
            else:
                msg_return = f'Última inspección hace {dias_transcurridos} días'
        else:
            msg_return = f'No hay registros de inspección'
        return msg_return

    # ============================================
    # Actualizacion/creacion de areas (migrado de update_area.py, hook)
    # ============================================

    def format_data_area_config(self, answers):
        formatted_data = {}

        if answers.get(self.configuracion_area['qr_area']):
            formatted_data.update({
                'qr_area': answers.get(self.configuracion_area['qr_area'])
            })

        if answers.get(self.configuracion_area['foto_area']):
            formatted_data.update({
                'foto_area': answers.get(self.configuracion_area['foto_area'])
            })

        formatted_data.update({
            'option': answers.get(self.configuracion_area['option'], ''),
            'ubicacion': answers.get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.configuracion_area['ubicacion'], ''),
            'area': answers.get(self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.configuracion_area['area'], ''),
            'create_area': True if answers.get(self.configuracion_area['create_area']) == 'no' else False,
            'nombre_nueva_area': answers.get(self.configuracion_area['nombre_nueva_area'], ''),
            'geolocation_area': answers.get(self.f['geolocalizacion_area_ubicacion'], {}),
            'tipo_de_area': answers.get(self.Location.TIPO_AREA_OBJ_ID, {}).get(self.f['tipo_de_area'], '')
        })

        return formatted_data

    def get_area_ubicacion_record(self, ubicacion=None, area=None, tag_id_area=None):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.Location.AREAS_DE_LAS_UBICACIONES,
        }
        if ubicacion:
            match_query.update({
            f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.configuracion_area['ubicacion']}": ubicacion
            })
        if area:
            match_query.update({
            f"answers.{self.configuracion_area['area']}": area
            })
        if tag_id_area:
            match_query.update({
                f"answers.{self.f['area_tag_id']}": tag_id_area
            })

        query = [
            {'$match': match_query },
            {'$project': {
                'folio': {'$ifNull': ['$folio', '']},
                '_id': 1,
                'ubicacion': f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.configuracion_area['ubicacion']}",
                'area': f"$answers.{self.configuracion_area['area']}",
                'tag_id_area': {'$ifNull': [f"$answers.{self.f['area_tag_id']}", '']},
                'foto_area': {'$ifNull': [f"$answers.{self.f['area_foto']}", []]},
                'tipo_area': f"$answers.{self.Location.TIPO_AREA_OBJ_ID}.{self.f['tipo_de_area']}",
                'nombre_direccion': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['nombre_direccion']}",
                'pais_area': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['pais_area']}",
                'ciudad_area': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['ciudad_area']}",
                'colonia_area': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['colonia_area']}",
                'direccion_area': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['direccion_area']}",
                'geolocalizacion_area': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['geolocalizacion_area']}",
                'geolocation_especific': f"$answers.{self.f['geolocalizacion_area_ubicacion']}",
                'estatus_area': f"$answers.{self.f['estatus_area']}",
                'estatus': f"$answers.{self.f['estatus_config_area']}",
                'qr_area': f"$answers.{self.f['qr_area']}"
            }},
            {'$limit': 1},
            {'$sort':{'folio':-1}},
        ]
        res = self.format_cr(self.cr.aggregate(query))
        res = self.unlist(res)
        return res

    def update_area_config(self, data):
        ubicacion = data.get('ubicacion', '')
        area = data.get('area', '')
        result = {'statuss': 'ok', 'status_comment': ''}
        if not ubicacion:
            msg = 'La ubicacion no puede estar vacia.'
            self.LKFException({'msg': msg, 'title': 'Ubicacion vacia'})
            result['statuss'] = 'error'
            result['status_comment'] = 'La ubicacion no puede estar vacia.'
            return result
        area_ubicacion_data = self.get_area_ubicacion_record(ubicacion=ubicacion, area=area)
        if not area_ubicacion_data:
            msg = 'No se encontro el area especificada.'
            self.LKFException({'msg': msg, 'title': 'Area no encontrada'})
            result['statuss'] = 'error'
            result['status_comment'] = 'No se encontro el area especificada.'
            return result
        folio = area_ubicacion_data.get('folio', '')
        record_id = area_ubicacion_data.get('_id', '')

        answers={}
        geolocation_especific = {
            'latitude': area_ubicacion_data.get('latitude'),
            'longitude': area_ubicacion_data.get('longitude')
        }

        for key, value in area_ubicacion_data.items():
            if key == 'area':
                answers[self.configuracion_area['area']] = value
            elif key == 'ubicacion':
                answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {
                    self.configuracion_area['ubicacion']: value,
                }
            elif key == 'tipo_area':
                answers[self.Location.TIPO_AREA_OBJ_ID] = {
                    self.f['tipo_de_area']: value
                }
            elif key == 'nombre_direccion':
                answers[self.CONTACTO_CAT_OBJ_ID] = {
                    self.f['nombre_direccion']: value,
                    self.f['pais_area']: area_ubicacion_data.get('pais_area', []),
                    self.f['ciudad_area']: area_ubicacion_data.get('ciudad_area', []),
                    self.f['colonia_area']: area_ubicacion_data.get('colonia_area', []),
                    self.f['direccion_area']: area_ubicacion_data.get('direccion_area', []),
                    self.f['geolocalizacion_area']: area_ubicacion_data.get('geolocalizacion_area', [])
                }
            elif key == 'estatus_area':
                answers[self.f['estatus_area']] = value
            elif key == 'estatus':
                answers[self.f['estatus_config_area']] = value
            elif key == 'tag_id_area':
                answers[self.f['area_tag_id']] = data.get('qr_area') or value
            elif key == 'qr_area':
                answers[self.f['qr_area']] = value
            elif key == 'foto_area':
                answers[self.f['area_foto']] = data.get('foto_area') or value
            elif key == 'latitude' or key == 'longitude':
                answers[self.f['geolocalizacion_area_ubicacion']] = geolocation_especific
            else:
                pass

        if answers:
            metadata = self.lkf_api.get_metadata(form_id=self.Location.AREAS_DE_LAS_UBICACIONES)
            metadata.update({
                'properties': {
                    "device_properties":{
                        "system": "Addons",
                        "process":"Actualizacion de Area",
                        "accion":'update_area',
                        "folio": folio,
                        "archive": "incidencias.py"
                    }
                },
                'answers': answers,
                '_id': record_id
            })
            response = self.net.patch_forms_answers(metadata)
            result['response'] = response
        return result

    def get_area_contact_details(self, direccion):
        selector = {}
        selector.update({
            f"answers.{self.f['nombre_direccion']}": direccion,
        })
        fields = [
            "_id",
            f"answers.{self.f['nombre_direccion']}",
            f"answers.{self.f['pais_area']}",
            f"answers.{self.f['direccion_area']}",
            f"answers.{self.f['colonia_area']}",
            f"answers.{self.f['geolocalizacion_area']}",
            f"answers.{self.f['ciudad_area']}",
        ]
        mango_query = {
            "selector": selector,
            "fields": fields,
            "limit": 1,
        }
        res = self.lkf_api.search_catalog(131890, mango_query)
        res = self.unlist(res)
        if res:
            res.pop('_id', None)
            res.pop('_rev', None)
            res.pop('created_at', None)
            res.pop('updated_at', None)
        return res if res else {}

    def exists_area(self, ubicacion, area):
        query = [
            {'$match': {
                "deleted_at":{"$exists":False},
                "form_id": self.Location.AREAS_DE_LAS_UBICACIONES,
                f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.configuracion_area['ubicacion']}": ubicacion,
                f"answers.{self.configuracion_area['area']}": area
            }},
            {'$project': {
                '_id': 1,
            }},
            {'$limit': 1},
        ]
        res = self.format_cr(self.cr.aggregate(query))
        return True if res else False

    def create_new_area(self, data, geolocation_area=None):
        exists = self.exists_area(data.get('ubicacion', {}), data.get('nombre_nueva_area', ''))
        if exists:
            return {'status_comment': 'El area ya existe. Solo se actualizo la informacion rellenada.'}
        contact_details = self.get_area_contact_details(data.get('ubicacion', {}))
        answers = {
            self.mf['nombre_area']: data.get('nombre_nueva_area'),
            self.f['area_foto']: data.get('foto_area'),
            self.f['area_tag_id']: data.get('qr_area'),
            self.Location.UBICACIONES_CAT_OBJ_ID: {
                self.mf['nombre_ubicacion_salida']: data.get('ubicacion', ''),
            },
            self.Location.TIPO_AREA_OBJ_ID: {
                self.f['tipo_de_area']: data.get('tipo_de_area', '')
            },
            self.f['geolocalizacion_area_ubicacion']: geolocation_area if geolocation_area else {},
            self.CONTACTO_CAT_OBJ_ID: contact_details,
            self.f['estatus_config_area']: 'activa',
            self.f['estatus_area']: 'disponible',
        }
        response = self.create_register(
            module='Accesos',
            process='Creacion de una area',
            action='rondines',
            file='accesos/app.py',
            form_id=self.Location.AREAS_DE_LAS_UBICACIONES,
            answers=answers,
            geolocation_area=geolocation_area,
        )
        return response

    def create_register(self, module, process, action, file, form_id, answers, geolocation_area=None):
        """Crea un registro en Linkaform con los metadatos y respuestas proporcionadas."""
        metadata = self.lkf_api.get_metadata(form_id=form_id)
        if geolocation_area:
            if isinstance(geolocation_area, dict):
                metadata['geolocation'] = [geolocation_area.get('latitude',0), geolocation_area.get('longitude',0)]
            elif isinstance(geolocation_area, list):
                metadata['geolocation'] = geolocation_area

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

    def catalogo_config_area_empleado(self, bitacora, location=''):
        #TODO Verificar si objetos perdidos tambien necesita solo los empleados de una location
        #TODO Mejorar funcion, de momento funcional
        catalog_id = self.Employee.CONF_AREA_EMPLEADOS_CAT_ID
        if bitacora == 'Objetos Perdidos':
            form_id= self.BITACORA_OBJETOS_PERDIDOS
            response = self.lkf_api.catalog_view(catalog_id, form_id)
        elif bitacora == 'Incidencias':
            form_id= self.BITACORA_INCIDENCIAS
            if location:
                options = {
                    "group_level": 2,
                    "startkey": [
                        location
                    ],
                    "endkey": [
                        f"{location}\n",
                    ]
                }
            else:
                form_id= self.BITACORA_OBJETOS_PERDIDOS
                options = {}
            response = self.lkf_api.catalog_view(catalog_id, form_id, options) 
        return response

    def catalogo_config_area_empleado_apoyo(self):
        catalog_id = self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_ID
        form_id= self.BITACORA_FALLAS
        return self.lkf_api.catalog_view(catalog_id, form_id) 

    def catalogo_tipo_concesion(self,location="", tipo=""):
        catalog_id = self.ACTIVOS_FIJOS_CAT_ID
        form_id= self.CONCESSIONED_ARTICULOS
        options={}
        if location and tipo:
            options = {
                "group_level": 2,
                "startkey": [tipo],
                "endkey": [f"{tipo}\n"]
            }
        else:
            if location and not tipo:
                options = {}
            elif tipo and not location:
                self.LKFException('Location es requerido')
        response= self.catalogo_view(catalog_id, form_id, options)
        return response

    def catalogo_falla(self, tipo=""):
        options={}
        if tipo:
            options = {
                'startkey': [tipo],
                'endkey': [f"{tipo}\n",{}],
                'group_level':2
            }
        catalog_id = self.LISTA_FALLAS_CAT_ID
        form_id = self.BITACORA_FALLAS
        return self.catalogo_view(catalog_id, form_id, options)

    def catalogo_tipo_articulo(self, tipo=""):
        options={}
        if tipo:
            options = {
                'startkey': [tipo],
                'endkey': [f"{tipo}\n",{}],
                'group_level':2
            }
        catalog_id = self.TIPO_ARTICULOS_PERDIDOS_CAT_ID
        form_id = self.BITACORA_OBJETOS_PERDIDOS
        return self.catalogo_view(catalog_id, form_id, options)

    def check_status_code(self, data_response):
        for item in data_response:
            if 'status_code' in item[1]:
                return {'status_code':item[1]['status_code']}
            else:
                return {'status_code':'400'}

    def check_in_out_employees(self,  checkin_type, check_datetime, checkin={}, employee_list=[], **kwargs):
        checkin_status = 'entrada' if checkin_type == 'in' else 'salida'
        date_id = 'checkin_date' if checkin_type == 'in' else 'checkout_date'
        checkin[self.f['guard_group']] = checkin.get(self.f['guard_group'],[])
        if checkin_type == 'out':
            for guard in checkin[self.f['guard_group']]:
                user_id = int(self.unlist(guard.get(self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID,{})\
                    .get(self.Employee.employee_fields['user_id_jefes'],0)))
                if guard[self.checkin_fields['checkin_status']] != checkin_status:
                    if not employee_list:
                        guard[self.checkin_fields['checkin_status']] = checkin_status
                        guard[self.checkin_fields[date_id]] = check_datetime                    
                    elif user_id in employee_list:
                        guard[self.checkin_fields['checkin_status']] = checkin_status
                        guard[self.checkin_fields[date_id]] = check_datetime
        elif employee_list:
            for idx, guard in enumerate(employee_list):
                empl_cat = {}
                empl_cat[self.f['worker_name_b']] = guard.get('name')
                if isinstance(guard.get('usuario_id'), list):
                    empl_cat[self.f['user_id_b']] = [(guard.get('usuario_id', [])[0]),]
                else:
                    empl_cat[self.f['user_id_b']] = [guard.get('user_id'),]
                guard_data = {
                        self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID : empl_cat,
                        self.checkin_fields['checkin_position']:'guardiad_de_apoyo',
                        self.checkin_fields['checkin_status']:checkin_status,
                        self.checkin_fields[date_id]:check_datetime,
                       }
                if kwargs.get('employee_type'):
                    guard_data.update({self.checkin_fields['checkin_position']: kwargs['employee_type'] })
                elif idx == 0:
                    guard_data.update({self.checkin_fields['checkin_position']: self.chife_guard})
                else:
                    guard_data.update({self.checkin_fields['checkin_position']: self.support_guard})
                checkin[self.f['guard_group']] += [guard_data,]
        return checkin

    def checkin_data(self, employee, location, area, checkin_type, now_datetime):
        set_type = self.set_boot_status(checkin_type)
        checkin = {
            self.f['checkin_type']: set_type,
            self.f['boot_checkin_date'] : now_datetime,
            self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID : {
                self.f['location']: location,
                self.f['area']: area, 
                self.f['worker_name']: employee.get('worker_name'),
            },

        }
        return checkin

    def config_get_guards_positions(self):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.PUESTOS_GUARDIAS,
            }        
        unwind = {'$unwind': f"$answers.{self.f['guard_group']}"}
        query = [
            {'$match': match_query },
            {'$unwind': f"$answers.{self.f['guard_group']}"},
            {'$project':{
                "_id":0,
                'tipo_de_guardia': f"$answers.{self.f['guard_group']}.{self.mf['tipo_de_guardia']}",
                'puesto': f"$answers.{self.f['guard_group']}.{self.Employee.PUESTOS_OBJ_ID}.{self.f['worker_position']}"
                }
            },
            {'$unwind': f"$tipo_de_guardia"},
            {'$group':{
                '_id':{
                    'tipo_de_guardia':'$tipo_de_guardia'
                    },
                'puestos': {'$addToSet':'$puesto'}
                }
            },
            {'$project':{
                "_id":0,
                'tipo_de_guardia': '$_id.tipo_de_guardia',
                'puestos': '$puestos',
                }
            },
            {'$sort': {'tipo_de_guardia':1}}
            ]
        return self.format_cr_result(self.cr.aggregate(query))

    def create_article_concessioned(self, data_articles):
        #---Define Metadata
        metadata = self.lkf_api.get_metadata(form_id=self.CONCESSIONED_ARTICULOS)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de Concesion Unica",
                    "Action": "create_article_concessioned",
                    "File": "accesos/app.py"
                }
            },
        })
        #---Define Answers
        answers = {}
        for key, value in data_articles.items():
            if  key =='status_concesion':
                answers[self.cons_f['status_concesion']] = value
            if  key == 'solicita_concesion':
                answers[self.cons_f['solicita_concesion']] = value
            elif  key == 'persona_nombre_concesion':
                answers[self.cons_f['persona_catalog_concesion']] = { self.mf['nombre_guardia_apoyo'] : value}
            elif  key == 'caseta_concesion':
                answers[self.cons_f['area_catalog_concesion']] = { self.mf['nombre_area_salida']: value}
            elif  key == 'ubicacion_concesion':
                answers[self.cons_f['ubicacion_catalog_concesion']] = { self.mf['ubicacion']: value}
            elif  key == 'area_concesion':
                answers[self.cons_f['equipo_catalog_concesion']] =   { self.cons_f['area_concesion']: value}
            elif  key == 'equipo_concesion':
                answers[self.cons_f['equipo_catalog_concesion']] =   { self.cons_f['equipo_concesion']: value}
            else:
                answers.update({f"{self.cons_f[key]}":value})

        metadata.update({'answers':answers})
        return self.lkf_api.post_forms_answers(metadata)

    def create_article_lost(self, data_articles):
        #---Define Metadata
        metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_OBJETOS_PERDIDOS)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de Bitacora Articulo Perdido",
                    "Action": "create_article_lose",
                    "File": "accesos/app.py"
                }
            },
        })
        employee = self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
        #---Define Answers
        answers = {}
        for key, value in data_articles.items():
            if  key == 'tipo_articulo_perdido' or key == 'articulo_seleccion':
                if data_articles['tipo_articulo_perdido'] and not data_articles['articulo_seleccion']:
                    answers[self.perdidos_fields['tipo_articulo_catalog']] = {
                        self.perdidos_fields['tipo_articulo_perdido']: data_articles['tipo_articulo_perdido']
                        }
                elif data_articles['articulo_seleccion'] and not data_articles['tipo_articulo_perdido']:
                    answers[self.perdidos_fields['tipo_articulo_catalog']] = {
                        self.perdidos_fields['articulo_seleccion']: data_articles['articulo_seleccion']
                        }
                elif data_articles['articulo_seleccion'] and data_articles['tipo_articulo_perdido']: 
                    answers[self.perdidos_fields['tipo_articulo_catalog']] = {
                    self.perdidos_fields['tipo_articulo_perdido']:data_articles['tipo_articulo_perdido'],
                    self.perdidos_fields['articulo_seleccion']:data_articles['articulo_seleccion']}

            elif  key == 'ubicacion_perdido' or key == 'area_perdido':
                if data_articles['ubicacion_perdido'] and not data_articles['area_perdido']:
                    answers[self.perdidos_fields['ubicacion_catalog']] = {self.perdidos_fields['ubicacion_perdido']:data_articles['ubicacion_perdido']}
                elif data_articles['area_perdido'] and not data_articles['ubicacion_perdido']:
                    answers[self.perdidos_fields['ubicacion_catalog']] = {self.perdidos_fields['area_perdido']:data_articles['area_perdido']}
                elif data_articles['area_perdido'] and data_articles['ubicacion_perdido']: 
                    answers[self.perdidos_fields['ubicacion_catalog']] = {self.perdidos_fields['ubicacion_perdido']:data_articles['ubicacion_perdido'],
                    self.perdidos_fields['area_perdido']:data_articles['area_perdido']}
            elif key == 'quien_entrega_interno':
                answers[self.perdidos_fields['quien_entrega_catalog']] = {self.perdidos_fields['quien_entrega_interno']:value}
            elif key == 'locker_perdido':
                answers[self.perdidos_fields['locker_catalog']] = {self.perdidos_fields['locker_perdido']:value}
            else:
                answers.update({f"{self.perdidos_fields[key]}":value})
        metadata.update({'answers':answers})
        res=self.lkf_api.post_forms_answers(metadata)
        return res

    def create_badge(self, data_badge):
        #---Define Metadata
        metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_GAFETES_LOCKERS)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de gafete",
                    "Action": "create_badge",
                    "File": "accesos/app.py"
                }
            },
        })
        #---Define Answers
        answers = {}
        for key, value in data_badge.items():
            if  key == 'ubicacion_gafete':
                answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {self.mf['ubicacion']:value}
            elif  key == 'caseta_gafete':
                answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {self.mf['nombre_area']:value}
            elif  key == 'visita_gafete':
                answers[self.mf['catalog_visita']] = {self.mf['nombre_visita']:value}
            elif  key == 'gafete_id':
                answers[self.GAFETES_CAT_OBJ_ID] = {self.gafetes_fields['gafete_id']:value}
            else:
                answers.update({f"{self.gafetes_fields[key]}":value})

        metadata.update({'answers':answers})
        return self.lkf_api.post_forms_answers(metadata)
    
    def upload_ics(self, id_forma_seleccionada, id_field, ics_content={}, meetings=[]):
        temp_dir = tempfile.gettempdir()  # Obtener el directorio temporal
        temp_file_path = os.path.join(temp_dir, "invite.ics")  # Crear la ruta para invite.ics

        #Creacion del invite.ics
        invite_content = self._get_ics_file(meetings=meetings)
        ics_data = invite_content.get(1)
        ics_content = ics_data.decode('utf-8')

        with open(temp_file_path, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(ics_content)

        rb_file = open(temp_file_path, 'rb')  # Abrir el archivo para subirlo
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
            update_file = {'file_name': "invite.ics", 'file_url': file_url}
        except KeyError:
            print('No se pudo obtener la URL del archivo')
            update_file = {"error": "Fallo al obtener la URL del archivo"}
        finally:
            os.remove(temp_file_path)  # Borrar el archivo temporal

        return update_file

    def create_enviar_msj(self, data_msj, data_cel_msj=None, folio=None):
        if not data_msj.get('enviado_desde'):
            data_msj['enviado_desde'] = 'Modulo de Accesos'
        return self.send_email_by_form(data_msj)
    
    def send_msj_pase(self, data_cel_msj=None, pre_sms=False, account=''):
        """
        Envía un mensaje de texto a un número de celular con información personalizada sobre un pase de invitación.

        Este método genera un mensaje en función de los datos proporcionados en `data_cel_msj`. 
        Si `pre_sms` es `True`, indica que se enviara un mensaje pre-registro para completar el pase. 
        En caso contrario, incluirá el mensaje de cuando se completa el pase.

        Args:
            data_cel_msj (dict): Un diccionario con los datos necesarios para personalizar el mensaje. 
                Las claves esperadas son:
                    - 'nombre' (str): Nombre de la persona invitada.
                    - 'visita_a' (str): Nombre de la persona o entidad que invita.
                    - 'ubicacion' (str): Ubicación del evento o visita.
                    - 'link' (str): Enlace para completar el registro.
                    - 'fecha_desde' (str): Fecha de inicio de la invitación.
                    - 'fecha_hasta' (str): Fecha de finalización de la invitación.
                    - 'numero' (str): Número de teléfono al que se enviará el mensaje.
            pre_sms (bool): Si es `True`, se genera un mensaje con instrucciones de registro.
                            Si es `False`, se genera un mensaje de pase completado.

        Returns:
            dict: Un diccionario con el código de estado del envío. Por ejemplo:
                - {'status_code': 200} si el mensaje fue enviado exitosamente.
        """

        fecha_str_desde = data_cel_msj.get('fecha_desde', '')
        fecha_str_hasta = data_cel_msj.get('fecha_hasta', '')

        fecha_desde = datetime.strptime(fecha_str_desde, "%Y-%m-%d %H:%M:%S")
        if fecha_str_hasta:
            fecha_hasta = datetime.strptime(fecha_str_hasta, "%Y-%m-%d %H:%M:%S")

        mensaje=''
        if pre_sms:
            msg = f"Hola {data_cel_msj.get('nombre', '')}, {data_cel_msj.get('visita_a', '')} "
            msg += f"te invita a {data_cel_msj.get('ubicacion', '')} y creo un pase para ti."
            msg += f" Completa tus datos de registro aquí: {data_cel_msj.get('link', '')}"
            mensaje = msg
        else:
            if account == 'milenium':
                get_pdf_url = self.get_pdf(data_cel_msj.get('qr_code', ''), template_id=553)
                get_pdf_url = get_pdf_url.get('data', '').get('download_url', '')
            else:
                get_pdf_url = self.get_pdf(data_cel_msj.get('qr_code', ''))
                get_pdf_url = get_pdf_url.get('data', '').get('download_url', '')
            msg = f"Estimado {data_cel_msj.get('nombre', '')}, {data_cel_msj.get('visita_a', '')}"

            if data_cel_msj.get('fecha_desde', '') and not data_cel_msj.get('fecha_hasta', ''):
                fecha_desde_format = fecha_desde.strftime("%d/%m/%Y a las %H:%M")
                msg += f", te invita a {data_cel_msj.get('ubicacion', '')} el {fecha_desde_format}."
            elif data_cel_msj.get('fecha_desde', '') and data_cel_msj.get('fecha_hasta', ''):
                fecha_desde_format = fecha_desde.strftime("%d/%m/%Y")
                fecha_hasta_format = fecha_hasta.strftime("%d/%m/%Y")
                msg += f", te invita a {data_cel_msj.get('ubicacion', '')} "
                msg += f"del {fecha_desde_format} al {fecha_hasta_format}."

            msg += f" Descarga tu pase: {get_pdf_url}"
            mensaje = msg
        phone_to = data_cel_msj.get('numero', '')
        res =self.lkf_api.send_sms(phone_to, mensaje, use_api_key=True)
        if res:
            return {'status_code':200}

    def format_pass_sms(self, data_cel_msj=None, pre_sms=False, account=''):
        fecha_str_desde = data_cel_msj.get('fecha_desde', '')
        fecha_str_hasta = data_cel_msj.get('fecha_hasta', '')

        ubicaciones = data_cel_msj.get('ubicacion', '')
        ubicaciones_nombres = []
        for ubicacion in ubicaciones:
            nombre_ubicacion = ubicacion.get(self.Location.UBICACIONES_CAT_OBJ_ID, {}).get(self.mf['ubicacion'], '')
            if nombre_ubicacion:
                ubicaciones_nombres.append(nombre_ubicacion)

        if len(ubicaciones_nombres) == 1:
            ubicaciones_str = ubicaciones_nombres[0]
        elif len(ubicaciones_nombres) == 2:
            ubicaciones_str = f"{ubicaciones_nombres[0]} y {ubicaciones_nombres[1]}"
        elif len(ubicaciones_nombres) > 2:
            ubicaciones_str = f"{ubicaciones_nombres[0]}, {ubicaciones_nombres[1]} y {len(ubicaciones_nombres) - 2} más"
        else:
            ubicaciones_str = ''

        fecha_desde = datetime.strptime(fecha_str_desde, "%Y-%m-%d %H:%M:%S")
        if fecha_str_hasta:
            fecha_hasta = datetime.strptime(fecha_str_hasta, "%Y-%m-%d %H:%M:%S")

        mensaje=''
        if pre_sms:
            msg = f"Hola {data_cel_msj.get('nombre', '')}, {data_cel_msj.get('visita_a', '')} "
            msg += f"te invita a {ubicaciones_str} y creo un pase para ti."
            msg += f" Completa tus datos de registro aquí: {data_cel_msj.get('link', '')}"
            mensaje = msg
        else:
            if account == 'milenium':
                get_pdf_url = self.get_pdf(data_cel_msj.get('qr_code', ''), template_id=553)
                get_pdf_url = get_pdf_url.get('data', '').get('download_url', '')
            else:
                get_pdf_url = self.get_pdf(data_cel_msj.get('qr_code', ''))
                get_pdf_url = get_pdf_url.get('data', '').get('download_url', '')
            msg = f"Estimado {data_cel_msj.get('nombre', '')}, {data_cel_msj.get('visita_a', '')}"

            if data_cel_msj.get('fecha_desde', '') and not data_cel_msj.get('fecha_hasta', ''):
                fecha_desde_format = fecha_desde.strftime("%d/%m/%Y a las %H:%M")
                msg += f", te invita a {ubicaciones_str} el {fecha_desde_format}."
            elif data_cel_msj.get('fecha_desde', '') and data_cel_msj.get('fecha_hasta', ''):
                fecha_desde_format = fecha_desde.strftime("%d/%m/%Y")
                fecha_hasta_format = fecha_hasta.strftime("%d/%m/%Y")
                msg += f", te invita a {ubicaciones_str} "
                msg += f"del {fecha_desde_format} al {fecha_hasta_format}."

            msg += f" Descarga tu pase: {get_pdf_url}"
            mensaje = msg
        phone_to = data_cel_msj.get('numero', '')
        return mensaje, phone_to

    def send_sms_alprotel(self, phone_number, message, data_cel_msj=None, pre_sms=None, account=None):
        API_URL = f"http://api.alprotel.com/v1/sms"
        twilio_creds = self.lkf_api.get_user_twilio_creds(use_api_key=True, jwt_settings_key=False)
        alprotel_token = twilio_creds.get('json').get('alprotel_token')

        headers = {
            'Authorization': f'{alprotel_token}',
            'Content-Type': 'application/json'
        }

        data = {
            'para': phone_number,
            'texto': message
        }

        try:
            response = requests.post(API_URL, json=data, headers=headers)

            if response.status_code == 200:
                message_data = {
                    "phone_to": phone_number,
                    "body": message,
                    "status": "enviado desde alprotel",
                    "created_at": datetime.now(),
                }
                message_record = self.create(_object=message_data, is_json=True, collection="messages")
                return response.json()

        except Exception as e:
            return self.send_msj_pase(data_cel_msj=data_cel_msj, pre_sms=pre_sms, account=account)

    def send_sms_masiv(self, para, texto, masiv_user, masiv_token):
        API_URL = "https://api-sms.masivapp.com/send-message"
        token = base64.b64encode(f"{masiv_user}:{masiv_token}".encode()).decode()
        headers = {
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json'
        }
        data = {
            'to': para,
            'text': texto,
            "customdata": "CUS_ID_0125",
            "isLongmessage": True,
        }
        try:
            response = requests.post(API_URL, json=data, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": response.text, "status_code": response.status_code}
        except Exception as e:
            return {"error": str(e)}

    def format_message(self, data_cel_msj=None, pre_sms=False, account=''):
        fecha_str_desde = data_cel_msj.get('fecha_desde', '')
        fecha_str_hasta = data_cel_msj.get('fecha_hasta', '')

        fecha_desde = datetime.strptime(fecha_str_desde, "%Y-%m-%d %H:%M:%S")
        if fecha_str_hasta:
            fecha_hasta = datetime.strptime(fecha_str_hasta, "%Y-%m-%d %H:%M:%S")

        mensaje=''
        if pre_sms:
            msg = f"Hola {data_cel_msj.get('nombre', '')}, {data_cel_msj.get('visita_a', '')} "
            msg += f"te invita a {data_cel_msj.get('ubicacion', '')} y creo un pase para ti."
            msg += f" Completa tus datos de registro aquí: {data_cel_msj.get('link', '')}"
            mensaje = msg
        else:
            if account == 'milenium':
                get_pdf_url = self.get_pdf(data_cel_msj.get('qr_code', ''), template_id=553)
                get_pdf_url = get_pdf_url.get('data', '').get('download_url', '')
            else:
                get_pdf_url = self.get_pdf(data_cel_msj.get('qr_code', ''))
                get_pdf_url = get_pdf_url.get('data', '').get('download_url', '')
            msg = f"Estimado {data_cel_msj.get('nombre', '')}, {data_cel_msj.get('visita_a', '')}"

            if data_cel_msj.get('fecha_desde', '') and not data_cel_msj.get('fecha_hasta', ''):
                fecha_desde_format = fecha_desde.strftime("%d/%m/%Y a las %H:%M")
                msg += f", te invita a {data_cel_msj.get('ubicacion', '')} el {fecha_desde_format}."
            elif data_cel_msj.get('fecha_desde', '') and data_cel_msj.get('fecha_hasta', ''):
                fecha_desde_format = fecha_desde.strftime("%d/%m/%Y")
                fecha_hasta_format = fecha_hasta.strftime("%d/%m/%Y")
                msg += f", te invita a {data_cel_msj.get('ubicacion', '')} "
                msg += f"del {fecha_desde_format} al {fecha_hasta_format}."

            msg += f" Descarga tu pase: {get_pdf_url}"
            mensaje = msg
        phone_to = data_cel_msj.get('numero', '')
        return mensaje, phone_to

    def send_cel_msj(self, data_cel_msj):
        mensaje = data_cel_msj.get('mensaje', '')
        phone_to = data_cel_msj.get('numero', '')
        msg = self.lkf_api.send_sms(phone_to, mensaje, use_api_key=True)
        return msg

    def check_out_all_users(self):
        match_query_visitas = {
            "deleted_at": {"$exists": False},
            "form_id": self.BITACORA_ACCESOS,
            f"answers.{self.PASE_ENTRADA_OBJ_ID}.{self.pase_entrada_fields['status_pase']}": {"$in": ["Activo"]},
            f"answers.{self.bitacora_fields['status_visita']}": "entrada",
        }

        proyect_fields_visitas = {
            '_id': 1,
            'folio': f"$folio",
            'fecha_entrada': f"$answers.{self.mf['fecha_entrada']}",
            'estatus': f"$answers.{self.bitacora_fields['status_visita']}",
        }

        query_visitas = [
            {'$match': match_query_visitas},
            {'$project': proyect_fields_visitas},
        ]

        data = self.format_cr(self.cr.aggregate(query_visitas))

        lista_filtrada = []
        zona_horaria = pytz.timezone('America/Mexico_City')
        fecha_actual = datetime.now(zona_horaria)

        for item in data:
            fecha_entrada_sin_zona = datetime.strptime(item['fecha_entrada'], '%Y-%m-%d %H:%M:%S')
            fecha_entrada = zona_horaria.localize(fecha_entrada_sin_zona)

            diferencia = fecha_actual - fecha_entrada
    
            if diferencia.total_seconds() > 7200:
                lista_filtrada.append(item)

        if lista_filtrada:
            res = self.set_checkout_all_users(lista_filtrada)
        else:
            res = 'No hay registros para hacer checkout...'
        return res

    def set_checkout_all_users(self, data):
        folio_list = []
        for item in data:
            folio_list.append(item['folio'])

        tz_mexico = pytz.timezone('America/Mexico_City')
        now = datetime.now(tz_mexico)
        fecha_hora_str = now.strftime("%Y-%m-%d %H:%M:%S")
        duration = '02:00:00'
        answers = {
            f"{self.bitacora_fields['status_visita']}":'salida',
            f"{self.mf['fecha_salida']}":fecha_hora_str,
            f"{self.mf['duracion']}":duration,
        }

        response = self.lkf_api.patch_multi_record( answers=answers, form_id=self.BITACORA_ACCESOS, folios=folio_list)
        return response

    def create_enviar_msj_pase(self, folio=None):
        access_pass={"enviar_correo": ["enviar_sms"]}
        res_update= self.update_pass(access_pass=access_pass, folio=folio)
        return res_update

    def create_enviar_correo(self, folio=None, envio=[]):
        # TODO: Cambiar el front
        if "enviar_correo" in envio or "enviar_sms" in envio:
            access_pass={"enviar_correo": envio}
        else:
            access_pass={"enviar_correo_pre_registro": envio}
        res_update= self.update_pass(access_pass=access_pass, folio=folio)
        return res_update
     
    def create_failure(self, data_failures):
        #---Define Metadata
        metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_FALLAS)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de fallas",
                    "Action": "create_failure",
                    "File": "accesos/app.py"
                }
            },
        })
        #---Define Answers
        answers = {}
        for key, value in data_failures.items():
            if key == 'falla_ubicacion' or key == 'falla_caseta':
                if data_failures['falla_ubicacion'] and not data_failures['falla_caseta']:
                    answers[self.fallas_fields['falla_ubicacion_catalog']] = {self.fallas_fields['falla_ubicacion']:data_failures['falla_ubicacion']}
                elif data_failures['falla_caseta'] and not data_failures['falla_ubicacion']:
                    answers[self.fallas_fields['falla_ubicacion_catalog']] = {self.fallas_fields['falla_caseta']:data_failures['falla_caseta']}
                elif data_failures['falla_caseta'] and data_failures['falla_ubicacion']: 
                    answers[self.fallas_fields['falla_ubicacion_catalog']] = {self.fallas_fields['falla_ubicacion']:data_failures['falla_ubicacion'],
                    self.fallas_fields['falla_caseta']:data_failures['falla_caseta']}
            elif key == 'falla' or key== 'falla_objeto_afectado':
                answers[self.fallas_fields['falla_catalog']] = {self.fallas_fields['falla']:data_failures['falla'],
                self.fallas_fields['falla_subconcepto']:data_failures['falla_objeto_afectado']}
            elif key == 'falla_reporta_nombre':
                answers[self.fallas_fields['falla_reporta_catalog']] = {self.fallas_fields['falla_reporta_nombre']:value}
            elif key == 'falla_responsable_solucionar_nombre':
                answers[self.fallas_fields['falla_responsable_solucionar_catalog']] = {self.fallas_fields['falla_responsable_solucionar_nombre']:value}
            elif key == 'falla_grupo_seguimiento':
                seg = data_failures.get('falla_grupo_seguimiento',[])
                if seg:
                    seg_list = []
                    for item in seg:
                        print("item", item)
                        seg_list.append(
                            {
                                self.fallas_fields['falla_accion_realizada']:item.get('accion_correctiva_incidencia',''),
                                self.fallas_fields['falla_personas_involucradas']: item.get('incidencia_personas_involucradas',''),
                                self.fallas_fields['falla_evidencia_solucion']:item.get('incidencia_evidencia_solucion',''),
                                self.fallas_fields['falla_documento_solucion']: item.get('incidencia_documento_solucion',''),
                                self.fallas_fields['falla_fecha_seguimiento']:item.get('fecha_inicio_seg',''),
                                self.fallas_fields['falla_tiempo_transcurrido']:item.get('tiempo_transcurrido', '')
                            }
                        )
                    answers.update({self.fallas_fields['falla_grupo_seguimiento']:seg_list})
            else:
                answers.update({f"{self.fallas_fields[key]}":value})
        metadata.update({'answers':answers})
        return self.lkf_api.post_forms_answers(metadata)

    def create_incidence(self, data_incidences):
        #---Define Metadata
        metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_INCIDENCIAS)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de incidencias",
                    "Action": "create_incidence",
                    "File": "accesos/app.py"
                }
            },
        })
        if data_incidences.get('record_id'):
            metadata.update({
                "id": data_incidences.pop('record_id')
            })
        #---Define Answers
        answers = {}
        answers[self.incidence_fields['incidencia_catalog']]={}
        answers[self.incidence_fields['estatus']]="abierto"
        for key, value in data_incidences.items():
            if key == 'categoria':
                answers[self.incidence_fields['incidencia_catalog']].update({
                    self.incidence_fields['categoria']:data_incidences['categoria']
                })
            elif key == 'sub_categoria':
                answers[self.incidence_fields['incidencia_catalog']].update({
                    self.incidence_fields['sub_categoria']: data_incidences['sub_categoria']
                })
            elif key == 'incidente':
                answers[self.incidence_fields['incidencia_catalog']].update({
                    self.incidence_fields['incidente']: data_incidences['incidente']
                })

            elif key == 'ubicacion_incidencia' or key == 'area_incidencia':
                if data_incidences['ubicacion_incidencia'] and not data_incidences['area_incidencia']:
                    answers[self.incidence_fields['ubicacion_incidencia_catalog']] = {self.incidence_fields['ubicacion_incidencia']:data_incidences['ubicacion_incidencia']}
                elif data_incidences['area_incidencia'] and not data_incidences['ubicacion_incidencia']:
                    answers[self.incidence_fields['ubicacion_incidencia_catalog']] = {self.incidence_fields['area_incidencia']:data_incidences['area_incidencia']}
                elif data_incidences['area_incidencia'] and data_incidences['ubicacion_incidencia']: 
                    answers[self.incidence_fields['ubicacion_incidencia_catalog']] = {self.incidence_fields['ubicacion_incidencia']:data_incidences['ubicacion_incidencia'],
                    self.incidence_fields['area_incidencia']:data_incidences['area_incidencia']}
            elif key == 'reporta_incidencia':
                answers[self.incidence_fields['reporta_incidencia_catalog']] = {self.incidence_fields['reporta_incidencia']:value}
            elif key == 'personas_involucradas_incidencia':
                personas = data_incidences.get('personas_involucradas_incidencia',[])
                if personas:
                    personas_list = []
                    for c in personas:
                        personas_list.append(
                            {
                                self.incidence_fields['nombre_completo']:c.get('nombre_completo',""),
                                self.incidence_fields['puesto']:c.get('puesto',""),
                                self.incidence_fields['rol'] :c.get('rol',"").lower().replace(" ","_"),
                                self.incidence_fields['sexo'] :c.get('sexo',"").lower().replace(" ","_"),
                                self.incidence_fields['grupo_etario'] :c.get("grupo_etario").lower().replace(" ","_"),
                                self.incidence_fields['atencion_medica'] :c.get('atencion_medica',"").lower(),
                                self.incidence_fields['retenido'] :c.get('retenido',"").lower(),
                                self.incidence_fields['comentarios'] :c.get('comentarios',"")
                            }
                        )
                    answers.update({self.incidence_fields['personas_involucradas_incidencia']:personas_list})
            elif key == 'acciones_tomadas_incidencia':
                acciones = data_incidences.get('acciones_tomadas_incidencia',[])
                if acciones:
                    acciones_list = []
                    for c in acciones:
                        acciones_list.append(
                            {
                                self.incidence_fields['acciones_tomadas']:c.get('acciones_tomadas',""),
                                self.incidence_fields['llamo_a_policia'] :c.get('llamo_a_policia',""),
                                self.incidence_fields['autoridad'] :c.get('autoridad','').lower().replace(" ", "_"),
                                self.incidence_fields['numero_folio_referencia'] :c.get('numero_folio_referencia',""),
                                self.incidence_fields['responsable'] :c.get('responsable',""),
                            }
                        )
                    answers.update({self.incidence_fields['acciones_tomadas_incidencia']:acciones_list})
            elif key == 'seguimientos_incidencia':
                seg = data_incidences.get('seguimientos_incidencia',[])
                if seg:
                    seg_list = []
                    for c in seg:
                        seg_list.append(
                            {
                                self.incidence_fields['accion_correctiva_incidencia']:c.get('accion_correctiva_incidencia',""),
                                self.incidence_fields['incidencia_personas_involucradas'] :c.get('incidencia_personas_involucradas',""),
                                self.incidence_fields['fecha_inicio_seg'] :c.get('fecha_inicio_seg',""),
                                self.incidence_fields['tiempo_transcurrido'] : c.get('tiempo_transcurrido',"12 horas"),
                                self.incidence_fields['incidencia_documento_solucion'] :c.get('incidencia_documento_solucion'),
                                self.incidence_fields['incidencia_evidencia_solucion'] :c.get('incidencia_evidencia_solucion')
                            }
                        )
                    answers.update({self.incidence_fields['seguimientos_incidencia']:seg_list})
            elif key == 'afectacion_patrimonial_incidencia':
                ap = data_incidences.get('afectacion_patrimonial_incidencia',[])
                if ap:
                    ap_list = []
                    for c in ap:
                        ap_list.append(
                            {
                                self.incidence_fields['tipo_afectacion']:c.get('tipo_afectacion',"").lower().replace(" ","_"),
                                self.incidence_fields['descripcion_afectacion']:c.get('descripcion_afectacion',""),
                                self.incidence_fields['estatus_afectacion']:c.get('estatus_afectacion',"").lower().replace(" ", "_"),
                                self.incidence_fields['monto_estimado'] :c.get('monto_estimado',""),
                                self.incidence_fields['duracion_estimada'] :c.get('duracion_estimada',""),
                                self.incidence_fields['evidencia'] :c.get('evidencia'),
                                self.incidence_fields['documento'] :c.get('documento')
                            }
                        )
                        print("LISTA",ap_list)
                    answers.update({self.incidence_fields['afectacion_patrimonial_incidencia']:ap_list})
            elif key == 'datos_deposito_incidencia':
                depositos = data_incidences.get('datos_deposito_incidencia',[])
                if depositos:
                    depositos_list = []
                    for c in depositos:
                        depositos_list.append(
                            {
                                self.incidence_fields['tipo_deposito']:c.get('tipo_deposito',"").lower().replace(" ","_"),
                                self.incidence_fields['cantidad'] :c.get('cantidad',""),
                                self.incidence_fields['origen'] :c.get('origen',"")
                            }
                        )
                    answers.update({self.incidence_fields['datos_deposito_incidencia']:depositos_list})
            elif key == 'tags':
                tags = data_incidences.get('tags',[])
                if tags:
                    tag_list = []
                    for c in tags:
                        tag_list.append(
                            {
                                self.incidence_fields['tag']:c,
                            }
                        )
                    answers.update({self.incidence_fields['tags']:tag_list})
            elif key == 'prioridad_incidencia':
                answers[self.incidence_fields['prioridad_incidencia']] = f"{value}".lower()
            elif key == 'color_piel':
                answers[self.incidence_fields['color_piel']] =  f"{value}".lower().replace(" ", "_")
            else:
                answers.update({f"{self.incidence_fields[key]}":value})
        # print("RESPUESTAS", simplejson.dumps(answers, indent=4))
        metadata.update({'answers':answers})
        return self.lkf_api.post_forms_answers(metadata)

    def create_note(self, location, area, data_notes):
        '''
        '''
        #---Define Metadata
        metadata = self.lkf_api.get_metadata(form_id=self.ACCESOS_NOTAS)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de notas",
                    "Action": "Create Note",
                    "File": "accesos/app.py"
                }
            },
        })
        #---Define Answers
        employee = self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
        answers = {
            f"{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}":{
                self.f['location']:location,
                self.f['area']:area
            },
            f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}":{
                self.f['worker_name']:employee['worker_name'],
            }
                }
        #----Assign Values Keys
        for key, value in data_notes.items():
            if key == 'note_comments':
                answers[self.notes_fields['note_comments_group']] = answers.get(self.notes_fields['note_comments_group'],[])
                for comment in value:
                    answers[self.notes_fields['note_comments_group']].append({self.notes_fields['note_comments']:comment})
            elif  key == 'note_booth':
                answers[self.notes_fields['note_catalog_booth']] = {self.notes_fields['note_booth']:value}
            elif  key == 'note_guard':
                answers[self.notes_fields['note_catalog_guard']] = {self.notes_fields['note_guard']:value}
            else:
                answers.update({f"{self.notes_fields[key]}":value})
        #----Assign Time
        timezone = employee.get('cat_timezone', employee.get('timezone', 'America/Monterrey'))

        fecha_hora_str =self.today_str(timezone, date_format='datetime')
        answers.update({f"{self.notes_fields['note_open_date']}":fecha_hora_str})
        metadata.update({'answers':answers})
        return self.lkf_api.post_forms_answers(metadata)

    def _get_ics_file(self, meetings=[]):
        _logger = logging.getLogger(__name__)

        """Returns iCalendar file for the event invitation.
        :param meetings: List of meetings (each meeting is a dictionary with the required fields).
        :returns: A dict of .ics file content for each meeting.
        """
        result = {}

        def ics_datetime(idate, allday=False, tz_name='UTC'):
            if idate:
                tz = pytz.timezone(tz_name)
                if allday:
                    return idate
                else:
                    return tz.localize(idate)
            return False

        try:
            import vobject
        except ImportError:
            _logger.warning("The `vobject` Python module is not installed, so iCal file generation is unavailable. Please install the `vobject` Python module")
            return result

        for meeting in meetings:
            cal = vobject.iCalendar()

            cal.add('method').value = 'REQUEST'
            
            event = cal.add('vevent')

            if not meeting.get("start") or not meeting.get("stop"):
                raise ValueError("First you have to specify the date of the invitation.")
            
            event.add('created').value = ics_datetime(datetime.now())
            event.add('dtstart').value = ics_datetime(meeting["start"], meeting.get("allday", False), tz_name='America/Mexico_City')
            event.add('dtend').value = ics_datetime(meeting["stop"], meeting.get("allday", False), tz_name='America/Mexico_City')
            event.add('summary').value = meeting["name"]
            if meeting.get("description"):
                event.add('description').value = meeting["description"]
            if meeting.get("location"):
                location_value = meeting["location"]
                if isinstance(location_value, list):
                    location_value = self.format_ubicaciones_to_google_pass(location_value)
                event.add('location').value = location_value
            if meeting.get("rrule"):
                event.add('rrule').value = meeting["rrule"]

            if meeting.get("alarm_ids"):
                for alarm in meeting["alarm_ids"]:
                    valarm = event.add('valarm')
                    interval = alarm["interval"]
                    duration = alarm["duration"]
                    trigger = valarm.add('TRIGGER')
                    trigger.params['related'] = ["START"]
                    if interval == 'days':
                        delta = timedelta(days=duration)
                    elif interval == 'hours':
                        delta = timedelta(hours=duration)
                    elif interval == 'minutes':
                        delta = timedelta(minutes=duration)
                    trigger.value = delta
                    valarm.add('DESCRIPTION').value = alarm.get("name", "Default Alarm")

            # Agregar organizador
            organizer = event.add('organizer')
            organizer.params['CN'] = [meeting['organizer_name']]
            organizer.value = f"MAILTO:{meeting['organizer_email']}"
            
            # Agregar los asistentes (attendees)
            for attendee_data in meeting.get("attendee_ids", []):
                attendee = event.add('attendee')
                attendee.value = "mailto:" + attendee_data.get("email", "")
                
                # Configuración de los parámetros de los asistentes
                attendee.params['CN'] = [attendee_data.get("name", "Unknown")]
                attendee.params['RS'] = ["OPT-PARTICIPANT"]
                attendee.params['CUTYPE'] = ["INDIVIDUAL"]
                attendee.params['ROLE'] = ["REQ-PARTICIPANT"]
                attendee.params['PARTSTAT'] = ["NEEDS-ACTION"]
                attendee.params['RSVP'] = ["TRUE"]
            
            result[meeting["id"]] = cal.serialize().encode('utf-8')

        return result
    
    def get_locations_address(self, list_locations=[]):
        match_query = {
            "deleted_at": {"$exists": False},
            "form_id": self.Location.UBICACIONES,
            # f"answers.{self.mf['ubicacion']}": {"$in": list_locations}
        }
        query = [                   
            {'$match': match_query},
            {'$project': {
                "_id": 0,
                "ubicacion": f"$answers.{self.mf['ubicacion']}",
                "direccion": f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_name']}",
                "geolocalizacion": f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.f['address_geolocation']}",
            }},
        ]
        print('query=', simplejson.dumps(query, indent=2))
        res = self.format_cr(self.cr.aggregate(query))
        print('res', res)
        format_res = {}
        for item in res:
            print('item', item)
            format_res[item.get('ubicacion','')] = {
                'address': item.get('direccion', ''),
                'geolocation': item.get('geolocalizacion') or []
            }
        return format_res

    def access_pass_vista_a(self, visita_a):
        """
        Crea grupo repetitivo de personas que son vistadas para pase de entrada

        args:
            visita_a (list): lista con NOMBRES de empleados a quien se vista

        return:
            lista con elementos para visitantes de pase de entrdada
        """
        res = []
        employee = {}
        if isinstance(visita_a, str):
            if visita_a == 'Usuario Actual':
                user_id = self.user['user_id']
                employee = self.Employee.get_employee_data(user_id=self.user['user_id'], get_one=True)
                self.employee = employee
                visita_a = employee.get('worker_name')
            visita_a = [visita_a,]

        if isinstance(visita_a, dict):
            if visita_a == 'Usuario Actual':
                user_id = self.user['user_id']
                employee = self.Employee.get_employee_data(user_id=self.user['user_id'], get_one=True)
                self.employee = employee
                visita_a = {'nombre': employee.get('worker_name')}
            name = visita_a.get('nombre')
            email = visita_a.get('email')
            phone = visita_a.get('telefono')
            visita_set = {}
            if not employee and self.valid_email(email):
                employee = self.Employee.get_employee_data(email=email, get_one=True)

            if not employee and name:
                employee = self.Employee.get_employee_data(name=name, get_one=True)

            if not employee and phone:
                employee = self.Employee.get_employee_data(phone=phone, get_one=True)

            if employee:
                visita_set = self.visita_a_set_format(employee)
            if visita_set:
                return [visita_set,]
            else:
                return []

        set_autorizado_por = False
        if not visita_a:
            #Si no trae dato utiliza el dato del usuario que esta creando el pase
            visita_a = [self.user.get('email'),]
            set_autorizado_por = True

        for visita in visita_a:
            visita_set = {}
            if visita == 'Usuario Actual':
                user_id = self.user['user_id']
                employee = self.Employee.get_employee_data(user_id=self.user['user_id'], get_one=True)
                self.employee = employee
                visita_set.update(self.visita_a_set_format(employee))
                if visita_set:
                    res.append(visita_set)
                continue
            if self.valid_email(visita):
                employee = self.Employee.get_employee_data(email=visita, get_one=True)
                self.employee = employee
                # TODO REVISAR ESTOOOOOO
                if set_autorizado_por:
                    self.autorizado_por = employee.get('worker_name')
            else:
                employee = self.Employee.get_employee_data(name = visita, get_one=True)
                self.employee = employee
            visita_set.update(self.visita_a_set_format(employee))
            if visita_set and self.employee:
                res.append(visita_set)
            else:
                visita_set = {self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID: {
                self.mf['nombre_empleado'] : visita}}
                res.append(visita_set)
        return res

    def visita_a_set_format(self, employee):
        """
        Crea formato de set para pase de acceso
        args:
            employee (json): objeto de self.get_employee_data
        return:
            res (json) : fromato de vista_a pase de acceso
        """
        res = {}
        nombre_visita_a = employee.get('worker_name')
        phone = self.unlist(employee.get('new_user_phone', employee.get('telefono2', employee.get('telefono1',""))))
        email = self.unlist(employee.get('new_user_email', employee.get('usuario_email', "")))
        user_id_id = self.unlist(employee.get('user_id_id',employee.get('usuario_id',"")))
        username = self.unlist(employee.get('new_user_username',""))
        departamento = self.unlist(employee.get('worker_department',""))
        puesto = self.unlist(employee.get('worker_position',""))
        #Lo seteamo en una lista porque es campo catlog detail
        res = {self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID: {
                self.mf['nombre_empleado'] : nombre_visita_a,
                self.mf['telefono_visita_a']: [phone, ],
                self.mf['email_visita_a']: [email, ],
                self.mf['id_usuario']: [user_id_id, ],
                self.mf['username']: [username, ],
                self.mf['departamento_empleado']: [departamento, ],
                self.mf['puesto_empleado']: [puesto, ],
                }
            }
        return res

    def access_pass_set_status(self, answers):
        """
        Evalua criterios del pase y regresa el status del pase
        Proceso
        Activo
        Vencido
        args:
            answers (json): Objeto de answers
        return:
            status (str): String con status
        """
        foto_ok = False
        id_vista = False
        fecha_ok = False
        vista_a_ok = False
        autorizado_ok = False
        status = 'proceso'
        foto = answers.get(self.pase_entrada_fields['walkin_fotografia'])
        if isinstance(foto, list) and len(foto) > 0:
            foto = foto[0]

        if isinstance(foto, dict):
            if 'file_url' in foto.keys() and foto['file_url']:
                foto_ok = self.valid_url(foto['file_url'])
        #TODO revisar configuracion
        id_vista  = answers[self.pase_entrada_fields['walkin_identificacion']]
        if isinstance(id_vista, list) and len(id_vista) > 0:
            id_vista = id_vista[0]

        if isinstance(id_vista, dict):
            if 'file_url' in id_vista.keys() and id_vista['file_url']:
                id_vista = self.valid_url(id_vista['file_url'])
        id_vista = True
        today = self.get_today_format()
        documentos_ok = foto_ok or id_vista
        if isinstance(today, datetime):
            today = today.strftime('%Y-%m-%d')
        elif today and isinstance(today, str) and len(today) > 10:
            today = today[:10]

        try:
            val_visita = answers[self.pase_entrada_fields['fecha_desde_visita']]
            if isinstance(val_visita, datetime):
                fecha_desde_visita = val_visita.strftime('%Y-%m-%d')
            else:
                fecha_desde_visita = self.valid_date(val_visita)
                if fecha_desde_visita:
                    if isinstance(fecha_desde_visita, datetime):
                        fecha_desde_visita = fecha_desde_visita.strftime('%Y-%m-%d')
                    elif isinstance(fecha_desde_visita, str) and len(fecha_desde_visita) > 10:
                        fecha_desde_visita = fecha_desde_visita[:10]
        except Exception as e:
            print(f"DEBUG DESDE ERROR: {e}")
            fecha_desde_visita = None

        try:
            val_hasta = answers[self.pase_entrada_fields['fecha_desde_hasta']]
            if isinstance(val_hasta, datetime):
                fecha_desde_hasta = val_hasta.strftime('%Y-%m-%d')
            else:
                fecha_desde_hasta = self.valid_date(val_hasta)
                if fecha_desde_hasta:
                    if isinstance(fecha_desde_hasta, datetime):
                        fecha_desde_hasta = fecha_desde_hasta.strftime('%Y-%m-%d')
                    elif isinstance(fecha_desde_hasta, str) and len(fecha_desde_hasta) > 10:
                        fecha_desde_hasta = fecha_desde_hasta[:10]
        except Exception as e:
            print(f"DEBUG HASTA ERROR: {e}")
            fecha_desde_hasta = None

        if fecha_desde_hasta and today <= fecha_desde_hasta:
            fecha_ok = True
        else:
            print(f"DEBUG FECHA_OK FALSE: today={today}, desde={fecha_desde_visita}, hasta={fecha_desde_hasta}")

        grupo_visitados = answers[self.mf['grupo_visitados']]
        for vista in grupo_visitados:
            if isinstance(vista, int):
                vista_a = grupo_visitados[vista]
            else:
                vista_a = vista
            if vista_a.get(self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID,{}).get(self.mf['nombre_empleado']):
                vista_a_ok = True

            if answers.get(self.pase_entrada_fields['catalago_autorizado_por'],{}).get(self.pase_entrada_fields['autorizado_por']):
                autorizado_ok = True

        if documentos_ok and fecha_ok and vista_a_ok and autorizado_ok:
            status = 'activo'
        elif documentos_ok and fecha_ok and vista_a_ok and not autorizado_ok:
            status = 'por_autorizar'
        elif not fecha_ok:
            status = 'vencido'
        return status

    def create_multiple_pass_threads(self, answers, acompanantes_grupo, parent_id):
        """
        Creates individual passes for each member of acompanantes_grupo in parallel threads.
        Pops acompanantes_grupo from child answers to avoid recursion.
        Links each child to the parent via url_padre, then updates the parent with all url_hijo.
        """
        parent_url = f"{self.settings.config.get('WEB_PROTOCOL','https')}://{self.settings.config.get('WEB_HOST','app.linkaform.com')}/#/records/detail/{parent_id}"
        def create_single_pass(acompanante, parent_id):
            record_id = self.object_id()
            pass_answers = deepcopy(answers)
            pass_answers.pop(self.pase_entrada_fields['acompanantes_grupo'], None)
            pass_answers.pop(self.pase_entrada_fields['acompanantes'], None)
            pass_answers.pop(self.pase_entrada_fields['qr_pase'], None)
            pass_answers.pop(self.mf['codigo_qr'], None)
            pass_answers[self.mf['nombre_pase']] = acompanante.get('nombre', '')
            pass_answers[self.pase_entrada_fields['link']] = pass_answers[self.pase_entrada_fields['link']].replace(str(parent_id), str(record_id))
            pass_answers[self.pase_entrada_fields['email']] = acompanante.get('email', '')
            pass_answers[self.mf['telefono_pase']] = acompanante.get('telefono', '')
            pass_answers[self.pase_entrada_fields['url_padre']] = parent_url

            metadata = self.lkf_api.get_metadata(form_id=self.PASE_ENTRADA)
            metadata.update({
                "id": record_id,
                "properties": {
                    "device_properties": {
                        "System": "Script",
                        "Module": "Accesos",
                        "Process": "Creación de pase grupo",
                        "Action": "create_multiple_pass_threads",
                        "File": "accesos/app.py"
                    }
                },
            })
            metadata.update({'answers': pass_answers})
            return self.lkf_api.post_forms_answers(metadata)

        url_by_email = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(create_single_pass, acompanante, parent_id): acompanante
                for acompanante in acompanantes_grupo
            }
            for future in as_completed(futures):
                acompanante = futures[future]
                try:
                    result = future.result()
                    child_id = result.get('json', {}).get('id')
                    if child_id:
                        child_url = f"{self.settings.config.get('WEB_PROTOCOL','https')}://{self.settings.config.get('WEB_HOST','app.linkaform.com')}/#/records/detail/{child_id}"
                        url_by_email[acompanante.get('email', '')] = child_url
                except Exception as e:
                    print(f"Error creating pass for {acompanante.get('nombre')}: {e}")

        child_group = [
            {
                self.pase_entrada_fields['nombre_acompanante']: acompanante.get('nombre', ''),
                self.pase_entrada_fields['email_acompanante']: acompanante.get('email', ''),
                self.pase_entrada_fields['telefono_acompanante']: acompanante.get('telefono', ''),
                self.pase_entrada_fields['url_hijo']: url_by_email.get(acompanante.get('email', ''), ''),
            }
            for acompanante in acompanantes_grupo
        ]

        if child_group:
            self.cr.update_one(
                {'_id': ObjectId(parent_id)},
                {'$set': {f"answers.{self.pase_entrada_fields['acompanantes_grupo']}": child_group}}
            )
        return child_group

    def get_booth_config(self, location):
        """
        Se obtiene la configuracion de la ubicacion de la forma Configuracion Modulo Seguridad
        Opciones actuales: impresion_de_pase, auto_acceso
        Args:
            location  (str): Ubicacion de la caseta.
        Returns:
            Lista de configuraciones
        """
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.CONF_MODULO_SEGURIDAD,
            }},
            {'$sort': {'updated_at': -1}},
            {'$limit': 1},
            {'$project': {
                "answers": 1,
            }},
            {'$unwind': f"$answers.{self.conf_modulo_seguridad['grupo_requisitos']}"},
            {'$match': {
                f"answers.{self.conf_modulo_seguridad['grupo_requisitos']}.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}": location
            }}
        ]
        data = self.format_cr(self.cr.aggregate(query))
        format_data = []
        if data:
            data = self.unlist(data)
            configuracion_de_accesos = data.get('configuracion_de_accesos', [])
            format_data = list(set(configuracion_de_accesos))
        return format_data

    def get_tipos_de_pase(self, ubicaciones=[]):
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.CONF_PERFILES,
                f"answers.{self.PERFILES_OBJ_ID}.{self.mf['walkin']}": "Si"
            }},
            {'$project': {
                "ubicacion": f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}",
                "tipo": f"$answers.{self.PERFILES_OBJ_ID}.{self.mf['nombre_perfil']}",
            }},
            {'$group': {
                "_id": {"$ifNull": ["$ubicacion", "General"]},
                "tipos": {"$addToSet": "$tipo"}
            }},
            {'$project': {
                "_id": 0,
                "ubicacion": "$_id",
                "tipos": 1
            }}
        ]
        if isinstance(ubicaciones, str):
            ubicaciones = [ubicaciones,]
        data = self.format_cr(self.cr.aggregate(query))
        if not data:
            return []
        mapped = {
            item.get("ubicacion", "General"): set(item.get("tipos", []))
            for item in data
        }

        tipos_generales = mapped.get("General", set())

        if not ubicaciones:
            return sorted(tipos_generales)

        tipos_por_ubicacion = []

        for u in ubicaciones:
            tipos_especificos = mapped.get(u, set())
            tipos_reales = tipos_especificos | tipos_generales
            tipos_por_ubicacion.append(tipos_reales)

        tipos_comunes = tipos_por_ubicacion[0].copy()

        for t in tipos_por_ubicacion[1:]:
            tipos_comunes &= t
        return sorted(tipos_comunes)

    def _hidratar_acompanantes(self, records_con_grupo):
        """
        records_con_grupo: lista de dicts, cada uno con la key 'acompanantes_grupo' cruda.
        Modifica cada record in-place, normalizando y agregando el estatus real de cada acompañante.
        """
        pase_fields_inv = {v: k for k, v in self.pase_entrada_fields.items()}
        all_qr_codes = set()

        for x in records_con_grupo:
            grupo_visita = x.get('acompanantes_grupo') or []
            acompanantes = []
            for acompanante in grupo_visita:
                item = {pase_fields_inv.get(k, k): v for k, v in acompanante.items()}
                url = item.get('url_hijo', '')
                if url:
                    item['qr_code'] = url.rstrip('/').rsplit('/', 1)[-1]
                    if ObjectId.is_valid(item['qr_code']):
                        all_qr_codes.add(item['qr_code'])
                acompanantes.append(item)
            x['acompanantes_grupo'] = acompanantes

        if not all_qr_codes:
            return

        extra_fields = ['status_pase', 'walkin_fotografia', 'walkin_identificacion', 'link']
        field_aliases = {
            'status_pase': 'estatus',
            'walkin_fotografia': 'foto',
            'walkin_identificacion': 'identificacion',
            'link': 'link',
        }
        projection = {f"answers.{self.pase_entrada_fields[f]}": 1 for f in extra_fields}
        pases_info = {
            str(p['_id']): {
                field_aliases[field]: p.get('answers', {}).get(self.pase_entrada_fields[field], '')
                for field in extra_fields
            }
            for p in self.cr.find(
                {'_id': {'$in': [ObjectId(qr) for qr in all_qr_codes]}, 'deleted_at': {'$exists': False}},
                projection,
            )
        }

        for x in records_con_grupo:
            for acompanante in x.get('acompanantes_grupo', []):
                qr = acompanante.get('qr_code', '')
                if qr in pases_info:
                    acompanante.update(pases_info[qr])

    def get_pdf_seg(self, qr_code, template_id=None, name_pdf=None):
        return self.lkf_api.get_pdf_record(qr_code, template_id = template_id, name_pdf =name_pdf, send_url=True)

    def autorizar_pase_acceso(self, answers):
        autorizado_por = {}
        #TODO FLUJO DE AUTORIZACION
        if not self.use_api or True:
            first_name = self.user.get('first_name')
            if not first_name:
                first_name = self.settings.config['USER']['name']
            autorizado_por = {self.pase_entrada_fields['autorizado_por']:first_name}
        return autorizado_por

    def access_pass_create_ics(self, access_pass, answers, ics_invitation=False):
        """
        Crea archivo para envio de invitacion a google calenar
        args:
            acces_pass (json): objeto con datos de pase enviados por front
            answers (json): objeto con el pase a crear
        return:
            res (json): reponse, con archivo de ics
        """
        res = {}
        print('creating acces pass ICS')
        if ics_invitation:
            id_forma = self.PASE_ENTRADA
            id_campo = self.pase_entrada_fields['archivo_invitacion']

            fecha_desde_visita = access_pass.get("fecha_desde_visita")
            descripcion = access_pass.get("descripcion", "")
            ubicacion = self.unlist(access_pass.get("ubicaciones"))
            visita_a = access_pass.get("visita_a")
            tema_cita = access_pass.get("tema_cita", f"Cita en {ubicacion}")
            if "Usuario Actual" in visita_a:
                visita_a = self.employee.get('worker_name')
            creado_por_email = access_pass.get("link", {}).get("creado_por_email")
            nombre = access_pass.get("nombre")
            email = access_pass.get("email")
            attendee_ids = [{"email": email, "nombre": nombre}, {"email": creado_por_email, "nombre": visita_a}]
            address = access_pass.get("address",{})
            geolocation = address.get('geolocation', [])
            if geolocation:
                geolocation = self.unlist(address.get('geolocation', [])).get('search_txt', '')
            else:
                geolocation = ubicacion
            fecha_desde_hasta = access_pass.get("fecha_desde_hasta")
            start_datetime = datetime.strptime(fecha_desde_visita, "%Y-%m-%d %H:%M:%S")
            stop_datetime = start_datetime + timedelta(hours=1)

            meeting = [
                {
                    "id": 1,
                    "start": start_datetime,
                    "stop": stop_datetime,
                    "name": tema_cita,
                    "description": descripcion,
                    "location": geolocation,
                    "allday": False,
                    "rrule": None,
                    "alarm_ids": [{"interval": "minutes", "duration": 10, "name": "Reminder"}],
                    'organizer_name': visita_a,
                    'organizer_email': creado_por_email,
                    "attendee_ids": attendee_ids,
                }
            ]

            try:
                respuesta_ics = self.upload_ics(id_forma, id_campo, meetings=meeting)
            except Exception as e:
                print(f"Error al generar o subir el archivo ICS: {e}")
                respuesta_ics = {}

            if respuesta_ics:
                res = {
                    self.pase_entrada_fields['archivo_invitacion'] : [
                            {
                                "file_name":respuesta_ics.get('file_name',''),
                                "file_url": respuesta_ics.get('file_url','')
                            }
                        ]}

        return res

    def create_access_pass(self, access_pass):
        """
        Crea pase de acceso

        args:
        location (str): Ubicacion de donde se crea el paso
        access_pass (json): json con datos completos para generar el pase

        return:

        """
        #---Define Metadata
        print('-----------------------')
        metadata = self.lkf_api.get_metadata(form_id=self.PASE_ENTRADA)
        self.autorizado_por = ""
        metadata.update({
            "id":self.object_id(),
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de pase",
                    "Action": "create_access_pass",
                    "File": "accesos/app.py"
                }
            },
        })
        answers = {}
        ics_invitation = False

        record_id = metadata['id']

        link_info = access_pass.get('link', "")
        docs=""

        if link_info:
            for index, d in enumerate(link_info["docs"]):
                if(d == "agregarIdentificacion"):
                    docs+="iden"
                elif(d == "agregarFoto"):
                    docs+="foto"
                if index==0 :
                    docs+="-"
            link_pass= f"{link_info['link']}?id={record_id}&user={self.user.get('parent_id')}&docs={docs}"
            answers[self.pase_entrada_fields['link']] = link_pass
        lkf_qr = generar_qr.LKF_QR(self.settings)

        qr_generado = lkf_qr.procesa_qr(
            record_id,
            f"qr_{record_id}",
            self.PASE_ENTRADA,
            img_field_id=self.pase_entrada_fields['qr_pase'] )

        answers[self.pase_entrada_fields['qr_pase']] = qr_generado
        #
        #---Define Answers
        perfil_pase = access_pass.get('perfil_pase', 'Visita General')
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id', self.user.get('id')))

        #TODO el timezone debiera de ser de quien crea el registro o de a quien se vista.
        #creo que se debe de poner una opcion advanzada para ajustar el tiemzone
        timezone = user_data.get('timezone','America/Monterrey')
        now_datetime =self.today_str(timezone, date_format='datetime')
        now_datetime_out = self.get_date_str(self.date_operation(now_datetime, '+', 8, 'hours'))
        # Setea personas vistadas
        answers[self.mf['grupo_visitados']] = []
        answers[self.mf['grupo_visitados']] = self.access_pass_vista_a(access_pass.get('visita_a',[]))

        ubicaciones = access_pass.get('ubicaciones')
        location = ubicaciones[0] if isinstance(ubicaciones, list) and ubicaciones else None

        answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {}

        ### Setting defaults
        access_pass['tipo_visita_pase'] = access_pass.get('tipo_visita_pase', 'fecha_fija')

        if not  access_pass.get('fecha_desde_visita') or access_pass['fecha_desde_visita'] == "":
            access_pass['fecha_desde_visita'] =  now_datetime

        if not access_pass.get('fecha_desde_hasta') or access_pass['fecha_desde_hasta'] == "":
            if access_pass.get('tipo_visita_pase') == 'fecha_fija':
                fecha_limite = access_pass.get('fecha_desde_visita', now_datetime)
                if isinstance(fecha_limite, datetime):
                    fecha_limite = fecha_limite.strftime('%Y-%m-%d')

                access_pass['fecha_desde_hasta'] = f"{fecha_limite[:10]} 23:59:59"
            else:
                ics_invitation = True
                access_pass['fecha_desde_hasta'] = now_datetime_out

        if not  access_pass.get('config_limitar_acceso') or access_pass['config_dia_de_acceso'] == "":
            access_pass['config_limitar_acceso'] =  1

        answers[self.pase_entrada_fields['acompanantes']]= access_pass.get('acompanantes', 0)
        answers[self.pase_entrada_fields['acompanantes_grupo']]= access_pass.get('acompanantes_grupo', 0)
        answers[self.pase_entrada_fields['config_dia_de_acceso']] = access_pass.get('config_dia_de_acceso',"")
        answers[self.pase_entrada_fields['config_dias_acceso']] = access_pass.get('config_dias_acceso',"")
        answers[self.pase_entrada_fields['config_limitar_acceso']] = access_pass.get('config_limitar_acceso',1)
        answers[self.pase_entrada_fields['descripcion']] = access_pass.get('descripcion',"")
        answers[self.pase_entrada_fields['empresa_pase']] = access_pass.get('empresa',"")
        answers[self.pase_entrada_fields['enviar_correo_pre_registro']] = access_pass.get("enviar_correo_pre_registro",[])
        answers[self.pase_entrada_fields['fecha_desde_visita']] = access_pass.get('fecha_desde_visita',now_datetime)
        answers[self.pase_entrada_fields['fecha_desde_hasta']] = access_pass.get('fecha_desde_hasta',now_datetime_out)
        answers[self.pase_entrada_fields['habilitar_vehiculo']]= access_pass.get('habilitar_vehiculo', 'no')
        answers[self.pase_entrada_fields['tipo_visita_pase']] = access_pass.get('tipo_visita_pase','fecha_fija')
        # answers[self.pase_entrada_fields['fecha_fija']] = access_pass.get('fechaFija',now_datetime)
        answers[self.pase_entrada_fields['status_pase']] = access_pass.get('status_pase',"").lower()
        answers[self.pase_entrada_fields['tema_cita']] = access_pass.get('tema_cita',access_pass.get('motivo',"") )
        answers[self.pase_entrada_fields['tipo_visita']] = 'alta_de_nuevo_visitante'
        answers[self.pase_entrada_fields['walkin_nombre']] = access_pass.get('nombre')
        answers[self.pase_entrada_fields['walkin_email']] = access_pass.get('email', '')
        answers[self.pase_entrada_fields['walkin_empresa']] = access_pass.get('empresa')
        answers[self.pase_entrada_fields['walkin_fotografia']] = access_pass.get('foto')
        answers[self.pase_entrada_fields['walkin_identificacion']] = access_pass.get('identificacion')
        answers[self.pase_entrada_fields['walkin_telefono']] = access_pass.get('telefono', '')

        created_from = access_pass.get('created_from')
        if created_from == 'app':
            created_from = 'pase_de_entrada_app'
        elif created_from == 'web':
            created_from = 'pase_de_entrada_web'
        elif created_from == 'nueva_visita':
            created_from = 'nueva_visita'
        elif created_from == 'auto_registro':
            created_from = 'auto_registro'
        else:
            created_from = 'nueva_visita'

        if created_from:
            answers[self.pase_entrada_fields['creado_desde']] = created_from

        if access_pass.get('ubicaciones'):
            ubicaciones = access_pass.get('ubicaciones',[])
            if isinstance(ubicaciones, str):
                ubicaciones = [ubicaciones, ]
            address_list = self.get_locations_address(list_locations=ubicaciones)
            if ubicaciones:
                ubicaciones_list = []
                for ubi in ubicaciones:
                    ubicaciones_list.append(
                        {
                            self.pase_entrada_fields['ubicacion_cat']: {
                                self.mf["ubicacion"]: ubi,
                                self.mf["direccion"]: [address_list.get(ubi, {}).get('address', '')],
                                self.f["address_geolocation"]: address_list.get(ubi, {}).get('geolocation', [])
                            }
                        }
                    )
                    if not access_pass.get('address'):
                        access_pass['address'] = address_list.get(ubi, {})
                answers.update({self.pase_entrada_fields['ubicaciones']:ubicaciones_list})

        if access_pass.get('comentarios'):
            comm = access_pass.get('comentarios',[])
            if comm:
                comm_list = []
                for c in comm:
                    comm_list.append(
                        {
                            self.pase_entrada_fields['comentario_pase']:c.get('comentario_pase'),
                            self.pase_entrada_fields['tipo_comentario'] :c.get('tipo_comentario').lower()
                        }
                    )
                answers.update({self.pase_entrada_fields['grupo_instrucciones_pase']:comm_list})

        if access_pass.get('todas_las_areas'):
            answers[self.pase_entrada_fields['todas_las_areas']]='sí'
            todas_areas = []
            for location in access_pass.get('ubicaciones', []):
                areas = self.Location.get_areas_by_location(location)
                if isinstance(areas, list):
                    for area in areas:
                        todas_areas.append({
                            "nombre_area": area,
                            "commentario_area": ""
                        })
            access_pass["areas"] = todas_areas

        if access_pass.get('areas'):
            areas = access_pass.get('areas',[])
            if areas:
                areas_list = []
                for c in areas:
                    areas_list.append(
                        {
                            self.pase_entrada_fields['commentario_area']:c.get('commentario_area'),
                            self.pase_entrada_fields['area_catalog_normal'] :{self.mf['nombre_area']: c.get('nombre_area')}
                        }
                    )
                answers.update({self.pase_entrada_fields['grupo_areas_acceso']:areas_list})

        # Perfil de Pase
        answers[self.CONFIG_PERFILES_OBJ_ID] = {
            self.mf['nombre_perfil'] : perfil_pase
        }
        if answers[self.CONFIG_PERFILES_OBJ_ID].get(self.mf['nombre_permiso']) and \
           type(answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']]) == str:
            answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']] = [answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']],]

        # Revisa si el pase contiene un grupo o forma parte de un grupo.

        #---Valor
        # Crea invitacion de calendario
        if created_from in ('pase_de_entrada_app', 'pase_de_entrada_web') or True:
            #TODO FLUJO DE AUTORIZACION DE PASES
            answers.update(self.access_pass_create_ics(access_pass, answers, ics_invitation))
            answers[self.pase_entrada_fields['catalago_autorizado_por']] = self.autorizar_pase_acceso(answers)


        answers[self.pase_entrada_fields['status_pase']] = self.access_pass_set_status(answers)

        acompanantes = answers.get(self.pase_entrada_fields['acompanantes'], 0)
        acompanantes_grupo = answers.get(self.pase_entrada_fields['acompanantes_grupo'], [])
        if acompanantes_grupo and len(acompanantes_grupo) > int(acompanantes or 0):
            self.LKFException({
                'msg': (
                    f"El número de acompañantes en la lista ({len(acompanantes_grupo)}) "
                    f"excede el permitido para este pase ({acompanantes}). "
                    f"Por favor ajusta la lista o incrementa el número de acompañantes."
                ),
                'status_code': 400,
            })

        metadata.update({'answers':answers})
        res = self.lkf_api.post_forms_answers(metadata)
        print('res=',res)
        if res.get('status_code') in (200, 201):
            parent_id = res.get('json', {}).get('id')
            if acompanantes_grupo and len(acompanantes_grupo) > 0 and parent_id:
                self.create_multiple_pass_threads(answers, acompanantes_grupo, parent_id)
        return res
   
    def create_visita_autorizada(self, visita_autorizada_obj, pase_obj={}):
        pase_info = pase_obj
        #---Define Metadata
        metadata = self.lkf_api.get_metadata(form_id=self.VISITA_AUTORIZADA)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de visita autorizada",
                    "Action": "create_visita_autorizada",
                    "File": "accesos/app.py"
                }
            },
        })

        #---Define Answers
        answers = {}
        nombre_completo = visita_autorizada_obj.get('nombre_completo', '')
        curp = visita_autorizada_obj.get('curp', '')
        direccion = visita_autorizada_obj.get('direccion', '')
        nss = visita_autorizada_obj.get('nss', '')

        email = pase_info.get('email', '')
        telefono = pase_info.get('telefono', '')
        fotografia = pase_info.get('fotografia',[])
        identificacion = pase_info.get('identificacion',[])
        
        answers[self.mf['nombre_visita']] = nombre_completo
        answers[self.mf['curp']] = curp
        answers[self.mf['email_vista']] = email
        answers[self.mf['telefono_visita']] = telefono
        answers[self.mf['foto']] = fotografia
        answers[self.mf['identificacion']] = identificacion
        answers[self.mf['direccion_visita']] = direccion
        answers[self.mf['nss']] = nss

        metadata.update({'answers':answers})
        res = self.lkf_api.post_forms_answers(metadata)
        if res.get("status_code") ==200 or res.get("status_code")==201:
            print(res)
        else:
            print("Error al ejecutar el post_forms_answers en create_visita_autorizada")
        return res

    def format_seguimiento_fallas(self, data):
        res = []
        for r in data:
            row = {}
            row['falla_fecha_seguimiento'] = r.get(self.fallas_fields['falla_fecha_seguimiento'],'')
            row['falla_tiempo_transcurrido'] = r.get(self.fallas_fields['falla_tiempo_transcurrido'],'')
            row['falla_accion_realizada'] = r.get(self.fallas_fields['falla_accion_realizada'],'')
            row['falla_personas_involucradas'] = r.get(self.fallas_fields['falla_personas_involucradas'],'')
            row['falla_documento_solucion'] = r.get(self.fallas_fields['falla_documento_solucion'],'')
            row['falla_evidencia_solucion'] = r.get(self.fallas_fields['falla_evidencia_solucion'],'')
            res.append(row)
        return res

    def format_seguimiento_incidencias(self, data):
        res = []
        for r in data:
            row = {}
            row['accion_correctiva_incidencia'] = r.get(self.incidence_fields['accion_correctiva_incidencia'],'')
            row['incidencia_personas_involucradas'] = r.get(self.incidence_fields['incidencia_personas_involucradas'],'')
            row['fecha_inicio_seg'] = r.get(self.incidence_fields['fecha_inicio_seg'],'')
            row['tiempo_transcurrido'] = r.get(self.incidence_fields['tiempo_transcurrido'],'')
            row['incidencia_documento_solucion'] = r.get(self.incidence_fields['incidencia_documento_solucion'],'')
            row['incidencia_evidencia_solucion'] = r.get(self.incidence_fields['incidencia_evidencia_solucion'],'')
            res.append(row)
        return res
    
    def format_tags_incidencias(self, data):
        res = []
        for r in data:
            tag = r.get(self.incidence_fields['tag'], '')
            if tag:
                res.append(tag)
        return res

    def format_personas_involucradas(self, data):
        res = []
        for r in data:
            row = {}
            print("row", row)
            row['nombre_completo'] = r.get(self.incidence_fields['nombre_completo'],'')
            row['puesto'] = r.get(self.incidence_fields['puesto'],'')
            row['rol'] = (r.get(self.incidence_fields['rol']) or '').capitalize().replace("_", " ")
            row['sexo'] = (r.get(self.incidence_fields['sexo']) or '').capitalize().replace("_"," ")
            row['grupo_etario'] = (r.get(self.incidence_fields['grupo_etario'])or '').capitalize().replace("_"," ")
            row['atencion_medica'] = r.get(self.incidence_fields['atencion_medica'],'')
            row['retenido'] = r.get(self.incidence_fields['retenido'],'')
            row['comentarios'] = r.get(self.incidence_fields['comentarios'],'')
            res.append(row)
        return res

    def format_datos_deposito(self, data):
        res = []
        for r in data:
            row = {}
            row['tipo_deposito'] = r.get(self.incidence_fields['tipo_deposito'],'').title().replace('_', ' ')
            row['cantidad'] = r.get(self.incidence_fields['cantidad'],'')
            row['origen'] = r.get(self.incidence_fields['origen'],'')
            res.append(row)
        return res

    def format_acciones(self, data):
        res = []
        for r in data:
            row = {}
            row['acciones_tomadas'] = r.get(self.incidence_fields['acciones_tomadas'],'')
            row['llamo_a_policia'] = r.get(self.incidence_fields['llamo_a_policia'],'')
            row['autoridad'] = r.get(self.incidence_fields['autoridad'],'').capitalize().replace("_"," ")
            row['numero_folio_referencia'] = r.get(self.incidence_fields['numero_folio_referencia'],'')
            row['responsable'] = r.get(self.incidence_fields['responsable'],'')
            res.append(row)
        return res
 
    def format_afectacion_patrimonial(self, data):
        res = []
        for r in data:
            row = {}
            print("que tenemos", r)
            row['tipo_afectacion'] = r.get(self.incidence_fields['tipo_afectacion'],'').capitalize().replace("_"," ")
            row['descripcion_afectacion'] = r.get(self.incidence_fields['descripcion_afectacion'],'')
            row['monto_estimado'] = r.get(self.incidence_fields['monto_estimado'],'')
            row['estatus_afectacion'] = r.get(self.incidence_fields['estatus_afectacion'],'').capitalize().replace("_"," ")
            row['duracion_estimada'] = r.get(self.incidence_fields['duracion_estimada'],'')
            row['evidencia'] = r.get(self.incidence_fields['evidencia'],[])
            row['documento'] = r.get(self.incidence_fields['documento'],[])
            res.append(row)
        return res

    def format_comentarios(self, data):
        res = []
        for r in data:
            row = {}
            row['comentario'] = r.get(self.bitacora_fields['comentario'],'')
            row['tipo_comentario'] = r.get(self.bitacora_fields['tipo_comentario'],'').title()
            res.append(row)
        return res

    def format_equipos(self, data):
        res = []
        for r in data:
            row = {}
            row['modelo_articulo'] = r.get(self.mf['modelo_articulo'],'')
            row['marca_articulo'] = r.get(self.mf['marca_articulo'],'')
            row['numero_serie'] = r.get(self.mf['numero_serie'],'')
            row['nombre_articulo'] = r.get(self.mf['nombre_articulo'],'')
            row['tipo_equipo'] = r.get(self.mf['tipo_equipo'],'Computo').title()
            row['color_articulo'] = r.get(self.mf['color_articulo'],'').title()
            res.append(row)
        return res

    def format_gafete(self, data):
        res = []
        for r in data:
            row = {}
            row['_id'] = r.get('_id')
            row['ubicacion'] = r.get(self.f['location'])
            row['gafete_id'] = r.get(self.gafetes_fields['gafete_id'])
            row['status'] = r.get(self.mf['status_gafete'])
            row['area'] = r.get(self.f['area'])
            res.append(row)
        return res

    def format_lockers(self, data):
        res = []
        for r in data:
            row = {}
            row['_id'] = r.get('_id')
            row['ubicacion'] = r.get(self.f['location'])
            row['locker_id'] = r.get(self.mf['locker_id'])
            row['status'] = r.get(self.mf['status_locker'])
            row['tipo_locker'] = r.get(self.mf['tipo_locker'])
            row['area'] = r.get(self.f['area'])
            res.append(row)
        return res

    def format_perfil_pase(self, perfil_pase, id_user=None, empresa=None):
        certificaciones = []
        if not perfil_pase.get('nombre_permiso') :
            return {}
        for idx, name in enumerate(perfil_pase.get('nombre_permiso',[])):
            cert = {}
            cert['nombre_certificacion'] = name
            vigencia = perfil_pase.get('vigencia_certificado',[])
            if len(vigencia) >= (idx+1):
                cert.update({'vigencia':vigencia[idx]})
            tipo_vigencia = perfil_pase.get('vigencia_certificado_en',[])
            if len(tipo_vigencia) >= (idx+1):
                cert.update({'tipo_vigencia':tipo_vigencia[idx]})
            if id_user:
                z = self.get_valiaciones_certificado(name, id_user, empresa)
                cert['status'] = z
            certificaciones.append(cert)
        return certificaciones

    def format_vehiculos(self, data):
        res = []
        for v in data:
            row = {}
            row['color'] = v.get(self.mf['color_vehiculo'],'').title()
            row['placas'] = v.get(self.mf['placas_vehiculo'],'')
            row['tipo'] = v.get('tipo_vehiculo','')
            row['marca_vehiculo'] = v.get(self.mf['marca_vehiculo'],'')
            row['modelo_vehiculo'] = v.get(self.mf['modelo_vehiculo'],'')
            row['nombre_estado'] = v.get('state','')
            res.append(row)
        return res

    def format_vehiculos_simple(self, data):
        res = []
        for v in data:
            row = {}
            row['color'] = v.get('color_vehiculo','') or v.get('color','') or  v.get(self.mf['color_vehiculo'],'')or ''
            row['placas'] = v.get('placas_vehiculo','') or v.get('placas','')  or v.get(self.mf['placas_vehiculo'],'')or  ''
            row['tipo'] = v.get('tipo_vehiculo','') or v.get('tipo','') or v.get(self.mf['tipo_vehiculo'],'') or ''
            row['marca'] = v.get('marca_vehiculo','') or v.get(self.mf['marca_vehiculo'],'') or ''
            row['modelo'] = v.get('modelo_vehiculo','') or v.get(self.mf['modelo_vehiculo'],'') or ''
            row['estado'] = v.get('nombre_estado','')or v.get('state','') or v.get(self.mf['nombre_estado'],'') or ''
            res.append(row)
        return res

    def format_equipos_simple(self, data):
        res = []
        for r in data:
            row = {}
            row['modelo'] = r.get('modelo_articulo','')  or r.get(self.mf['marca_articulo'],'') or ''
            row['marca'] = r.get('marca_articulo','') or r.get(self.mf['marca_articulo'],'') or ''
            row['serie'] = r.get('numero_serie','') or r.get(self.mf['numero_serie'],'') or''
            row['nombre'] = r.get('nombre_articulo','') or r.get(self.mf['nombre_articulo'],'') or ''
            row['tipo'] = r.get('tipo_equipo','').title() or r.get(self.mf['tipo_equipo'],'') or ''
            row['color'] = r.get('color_articulo','').title() or r.get(self.mf['color_articulo'],'') or ''
            res.append(row)
        return res

    def format_vehiculos_last_move(self, data):
        res = []
        for v in data:
            row = {}
            row['color_vehiculo'] = v.get('color','').title()
            row['placas_vehiculo'] = v.get('placas','')
            row['tipo_vehiculo'] = v.get('tipo','')
            row['marca_vehiculo'] = v.get('marca_vehiculo','')
            row['modelo_vehiculo'] = v.get('modelo_vehiculo','')
            row['nombre_estado'] = v.get('nombre_estado','')
            res.append(row)
        return res

    def format_visita(self, data):
        res = []
        for r in data:
            row = {}
            row['user_id']=self.unlist(r.get('user_id',[])) or ""
            row['nombre']=self.unlist(r.get('note_guard',[])) or ""
            row['departamento']=self.unlist(r.get('worker_department',[])) or ""
            row['posicion']=self.unlist(r.get('worker_position',[])) or ""
            row['email']=self.unlist(r.get('email',[])) or ""
            res.append(row)
        return res

    def get_access_pass(self, qr_code):
        # Obtiene el pase de acceso con el código QR.

        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CHECKIN_CASETAS,
            }
        if _id:
            match_query.update({"_id":ObjectId(_id)})

    def get_access_notes(self, location_name, area_name):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.ACCESOS_NOTAS,
            f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['location']}":location_name,
            f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['area']}":area_name
            }
        query = [
            {'$match': match_query },
            {'$project': self.project_format(self.notes_project_fields)},
            {'$sort':{self.f['note_open_date']:1}}
            ]
        return self.format_cr_result(self.cr.aggregate(query))

    def get_booths_guards(self, location=None, area=None, solo_disponibles=False, **kwargs):
        res = {}
        if not area:
            default_booth , user_booths = self.Employee.get_user_booth(search_default=False)
            location = default_booth.get('location')
            area = default_booth.get('area')
        guards_positions = self.config_get_guards_positions()
        if not guards_positions:
            self.LKFException({"status_code":400, "msg":'No Existen puestos de guardias configurados.'})
        for guard_type in guards_positions:
            puesto = guard_type['tipo_de_guardia']
            if kwargs.get('position') and kwargs['position'] != puesto:
                continue
            res[puesto] = res.get(puesto,
                self.Employee.get_users_by_location_area(location, area, **{'position': guard_type['puestos']})
                )
        uids = []
        for pos, user in res.items():
            uids += [x['user_id'] for x in user]

        pics = self.Employee.get_employee_pic(uids)
        for pos, user in res.items():
            for x in user:
                if x['user_id'] in list(pics.keys()):
                    x['picture'] = pics[x['user_id']]
        if solo_disponibles:
            uids = []
            disponibles = []
            for pos, user in res.items():
                for x in user:
                    if x['user_id'] not in uids:
                        uids.append(x['user_id'])
            active_employees = self.get_employee_checkin_status(uids)
            uids = []
            for uid, user_st in active_employees.items():
                uids.append(uid)
                user_status = user_st.get('status')
                if user_st.get('status') == 'out':
                    disponibles.append(uid)
            res_disp = {}
            for pos, user in res.items():
                for x in user:
                    if x['user_id'] in disponibles:
                        res_disp[pos] = res_disp.get(pos,[])
                        res_disp[pos].append(x)
                    elif x['user_id'] not in uids:
                        res_disp[pos] = res_disp.get(pos,[])
                        res_disp[pos].append(x)
            res = res_disp
        return res

    def get_booth_status(self, booth_area, location):
        last_chekin = self.get_last_checkin(location, booth_area)
        booth_status = {
            "status":'Cerrada',
            "guard_on_dutty":'',
            "user_id":'',
            "stated_at":'',
            "fotografia_inicio_turno":[],
            "fotografia_cierre_turno":[],
            }
        if last_chekin.get('checkin_type') in ['entrada','apertura','disponible', 'abierta']:
            #todo
            #user_id
            booth_status['status'] = 'Abierta'
            booth_status['guard_on_dutty'] = last_chekin.get('employee')
            booth_status['stated_at'] = last_chekin.get('boot_checkin_date')
            booth_status['checkin_id'] = last_chekin.get('_id', last_chekin.get('id', ''))
            booth_status['fotografia_inicio_turno'] = last_chekin.get('fotografia_inicio_turno',[])
            booth_status['fotografia_cierre_turno'] = last_chekin.get('fotografia_cierre_turno',[])
        return booth_status

    def get_booth_stats(self, booth_area, location):
        res ={
                "in_invitees":11,
                "articulos_concesionados":12,
                "incidentes_pendites": 13,
                "vehiculos_estacionados": 14,
                "gefetes_pendientes": 15,
            }
        return res
    
    def get_page_stats(self, booth_area, location, page=''):
        timezone = pytz.timezone('America/Mexico_City')
        today = datetime.now(timezone).strftime("%Y-%m-%d")        
        res={}

        if page == 'Turnos':
            #Visitas dentro, Gafetes pendientes y Vehiculos estacionados
            query_visitas = [
                {'$match': {
                    "deleted_at": {"$exists": False},
                    "form_id": self.BITACORA_ACCESOS,
                    f"answers.{self.bitacora_fields['status_visita']}": "entrada",
                    f"answers.{self.PASE_ENTRADA_OBJ_ID}.{self.pase_entrada_fields['status_pase']}": {"$in": ["Activo"]},
                    f"answers.{self.bitacora_fields['caseta_entrada']}": booth_area,
                    f"answers.{self.bitacora_fields['ubicacion']}": location,
                    # f"answers.{self.mf['fecha_entrada']}": {"$gte": f"{today} 00:00:00", "$lte": f"{today} 23:59:59"}
                }},
                {'$project': {
                    '_id': 1,
                    'vehiculos': {"$ifNull": [f"$answers.{self.mf['grupo_vehiculos']}", []]},
                    'equipos': {"$ifNull": [f"$answers.{self.mf['grupo_equipos']}", []]},
                    'status_visita': f"$answers.{self.bitacora_fields['status_visita']}",
                    'id_gafete': f"$answers.{self.GAFETES_CAT_OBJ_ID}.{self.gafetes_fields['gafete_id']}",
                    'status_gafete': f"$answers.{self.mf['status_gafete']}"
                }},
                {'$group': {
                    '_id': None,
                    'total_visitas_dentro': {'$sum': 1},
                    'total_equipos_dentro': {
                        '$sum': {
                            '$cond': {
                                'if': {'$eq': ['$status_visita', 'entrada']},
                                'then': {'$size': '$equipos'},
                                'else': 0
                            }
                        }
                    },
                    'total_vehiculos_dentro': {'$sum': {'$size': '$vehiculos'}},
                    'gafetes_info': {
                        '$push': {
                            'id_gafete':'$id_gafete',
                            'status_gafete':'$status_gafete'
                        }
                    }
                }}
            ]

            resultado = self.format_cr(self.cr.aggregate(query_visitas))
            total_vehiculos_dentro = resultado[0]['total_vehiculos_dentro'] if resultado else 0
            total_visitas_dentro = resultado[0]['total_visitas_dentro'] if resultado else 0
            total_equipos_dentro = resultado[0]['total_equipos_dentro'] if resultado else 0
            gafetes_info = resultado[0]['gafetes_info'] if resultado else []
            gafetes_pendientes = sum(1
                for gafete in gafetes_info
                    if gafete.get('id_gafete') and gafete.get('status_gafete', '').lower() != 'entregado'
            )

            res['total_vehiculos_dentro'] = total_vehiculos_dentro
            res['in_invitees'] = total_visitas_dentro
            res['total_equipos_dentro'] = total_equipos_dentro
            res['gafetes_pendientes'] = gafetes_pendientes

            #Articulos concesionados
            query_concesionados = [
                {'$match': {
                    "deleted_at": {"$exists": False},
                    "form_id": self.CONCESSIONED_ARTICULOS,
                    f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}": location,
                }},
                {'$project': {
                    '_id': 1,
                }},
                {'$group': {
                    '_id': None,
                    'articulos_concesionados': {'$sum': 1}
                }}
            ]

            resultado = self.format_cr(self.cr.aggregate(query_concesionados))
            articulos_concesionados = resultado[0]['articulos_concesionados'] if resultado else 0
            
            res['articulos_concesionados'] = articulos_concesionados

            #Incidentes pendientes
            query_incidentes = [
                {'$match': {
                    "deleted_at": {"$exists": False},
                    "form_id": self.BITACORA_INCIDENCIAS,
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.incidence_fields['area_incidencia']}": booth_area,
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.incidence_fields['ubicacion_incidencia']}": location,
                    f"answers.{self.incidence_fields['estatus']}": 'abierto'
                }},
                {'$project': {
                    '_id': 1,
                }},
                {'$group': {
                    '_id': None,
                    'incidentes_pendientes': {'$sum': 1}
                }}
            ]

            resultado = self.format_cr(self.cr.aggregate(query_incidentes))
            incidentes_pendientes = resultado[0]['incidentes_pendientes'] if resultado else 0
            
            res['incidentes_pendites'] = incidentes_pendientes

            #Fallas pendientes
            query_fallas = [
                {'$match': {
                    "deleted_at": {"$exists": False},
                    "form_id": self.BITACORA_FALLAS,
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.fallas_fields['falla_caseta']}": booth_area,
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.fallas_fields['falla_ubicacion']}": location,
                    f"answers.{self.fallas_fields['falla_estatus']}": 'abierto',
                    # f"answers.{self.incidence_fields['fecha_hora_incidencia']}": {"$gte": today,"$lt": f"{today}T23:59:59"}
                }},
                {'$project': {
                    '_id': 1,
                }},
                {'$group': {
                    '_id': None,
                    'fallas_pendientes': {'$sum': 1}
                }}
            ]

            resultado = self.format_cr(self.cr.aggregate(query_fallas))
            fallas_pendientes = resultado[0]['fallas_pendientes'] if resultado else 0

            res['fallas_pendientes'] = fallas_pendientes

        elif page == 'Accesos' or page == 'Bitacoras':
            #Visitas en el dia, personal dentro, vehiculos dentro, salidas registradas y personas dentro
            match_query_one = {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_ACCESOS,
                f"answers.{self.PASE_ENTRADA_OBJ_ID}.{self.pase_entrada_fields['status_pase']}": {"$in": ["Activo"]},
                f"answers.{self.bitacora_fields['ubicacion']}": location,
            }

            match_query_two = {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_ACCESOS,
                f"answers.{self.PASE_ENTRADA_OBJ_ID}.{self.pase_entrada_fields['status_pase']}": {"$in": ["Activo"]},
                f"answers.{self.bitacora_fields['ubicacion']}": location,
                f"answers.{self.mf['fecha_entrada']}": {"$gte": f"{today} 00:00:00", "$lte": f"{today} 23:59:59"}
            }

            if not booth_area == 'todas' and booth_area:
                match_query_one.update({
                    f"answers.{self.bitacora_fields['caseta_entrada']}": booth_area,
                })
                match_query_two.update({
                    f"answers.{self.bitacora_fields['caseta_entrada']}": booth_area,
                })

            query_visitas = [
                {'$match': match_query_one},
                {'$project': {
                    '_id': 1,
                    'vehiculos': {"$ifNull": [f"$answers.{self.mf['grupo_vehiculos']}", []]},
                    'equipos': {"$ifNull": [f"$answers.{self.mf['grupo_equipos']}", []]},
                    'perfil': f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['nombre_perfil']}",
                    'status_visita': f"$answers.{self.bitacora_fields['status_visita']}",
                    'fecha_salida': f"$answers.{self.mf['fecha_salida']}"
                }},
                {'$group': {
                    '_id': None,
                    'visitas_en_dia': {'$sum': 1},
                    'total_vehiculos_dentro': {
                        '$sum': {
                            '$cond': {
                                'if': {'$eq': ['$status_visita', 'entrada']},
                                'then': {'$size': '$vehiculos'},
                                'else': 0
                            }
                        }
                    },
                    'total_equipos_dentro': {
                        '$sum': {
                            '$cond': {
                                'if': {'$eq': ['$status_visita', 'entrada']},
                                'then': {'$size': '$equipos'},
                                'else': 0
                            }
                        }
                    },
                    'detalle_visitas': {
                        '$push': {
                            'perfil': '$perfil',
                            'status_visita': '$status_visita',
                            'fecha_salida': '$fecha_salida'
                        }
                    }
                }}
            ]

            query_visitas_dia = [
                {'$match': match_query_two},
                {'$project': {
                    '_id': 1,
                    'vehiculos': {"$ifNull": [f"$answers.{self.mf['grupo_vehiculos']}", []]},
                    'equipos': {"$ifNull": [f"$answers.{self.mf['grupo_equipos']}", []]},
                    'perfil': f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['nombre_perfil']}",
                    'status_visita': f"$answers.{self.bitacora_fields['status_visita']}"
                }},
                {'$group': {
                    '_id': None,
                    'visitas_en_dia': {'$sum': 1},
                    'total_vehiculos_dentro': {
                        '$sum': {
                            '$cond': {
                                'if': {'$eq': ['$status_visita', 'entrada']},
                                'then': {'$size': '$vehiculos'},
                                'else': 0
                            }
                        }
                    },
                    'total_equipos_dentro': {
                        '$sum': {
                            '$cond': {
                                'if': {'$eq': ['$status_visita', 'entrada']},
                                'then': {'$size': '$equipos'},
                                'else': 0
                            }
                        }
                    },
                    'detalle_visitas': {
                        '$push': {
                            'perfil': '$perfil',
                            'status_visita': '$status_visita'
                        }
                    }
                }}
            ]

            resultado = self.format_cr(self.cr.aggregate(query_visitas))
            today_salida = f"{today} 00:00:00"
            resultado_dia = self.format_cr(self.cr.aggregate(query_visitas_dia))

            total_vehiculos_dentro = resultado[0]['total_vehiculos_dentro'] if resultado else 0
            total_equipos_dentro = resultado[0]['total_equipos_dentro'] if resultado else 0
            detalle_visitas_todas = resultado[0]['detalle_visitas'] if resultado else []
            visitas_en_dia = resultado_dia[0]['visitas_en_dia'] if resultado_dia else 0

            personal_dentro = 0
            salidas = 0
            personas_dentro = 0

            for visita in detalle_visitas_todas:
                status_visita = visita['status_visita'].lower()

                if status_visita == "entrada":
                    personas_dentro += 1
                    
                if visita.get('fecha_salida') and visita.get('fecha_salida') >= today_salida:
                    salidas += 1

            res['total_vehiculos_dentro'] = total_vehiculos_dentro
            res['total_equipos_dentro'] = total_equipos_dentro
            res['visitas_en_dia'] = visitas_en_dia
            res['personal_dentro'] = personal_dentro
            res['salidas_registradas'] = salidas
            res['personas_dentro'] = personas_dentro

            query_paqueteria = [
                {'$match': {
                    "deleted_at": {"$exists": False},
                    "form_id": self.PAQUETERIA,
                    f"answers.{self.paquetes_fields['estatus_paqueteria']}": "guardado",
                    f"answers.{self.paquetes_fields['fecha_recibido_paqueteria']}": {"$gte": f"{today} 00:00:00", "$lte": f"{today} 23:59:59"}
                }},
                {'$project': {
                    '_id': 1,
                }},
                {'$group': {
                    '_id': None,
                    'paquetes_recibidos': {'$sum': 1},
                }}
            ]

            resultado_paquetes = self.format_cr(self.cr.aggregate(query_paqueteria))
            paquetes_recibidos = resultado_paquetes[0]['paquetes_recibidos'] if resultado_paquetes else 0

            res['paquetes_recibidos'] = paquetes_recibidos

        elif page == 'Incidencias':
            #Incidentes por dia, por semana y por mes
            now = datetime.now(pytz.timezone("America/Mexico_City"))
            today_date = now.date()
            user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
            zona = user_data.get('timezone','America/Monterrey')
            dateFromWeek, dateToWeek = self.get_range_dates('this_week', zona)

            match_query_incidentes = {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_INCIDENCIAS,
            }

            if location:
                match_query_incidentes.update({
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.incidence_fields['ubicacion_incidencia']}": location,
                })
            if booth_area:
                match_query_incidentes.update({
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.incidence_fields['area_incidencia']}": booth_area,
                })

            query_incidentes = [
                {'$match': match_query_incidentes},
                {'$addFields': {
                    'fecha_incidencia': {
                        '$dateFromString': {
                            'dateString': f"$answers.{self.incidence_fields['fecha_hora_incidencia']}",
                            'format': "%Y-%m-%d %H:%M:%S"
                        }
                    }
                }},
                {'$facet': {
                    'por_dia': [
                        {'$match': {
                            'fecha_incidencia': {
                                '$gte': datetime.combine(today_date, time.min),
                                '$lte': datetime.combine(today_date, time.max)
                            }
                        }},
                        {'$count': 'incidentes_x_dia'}
                    ],
                    'por_semana': [
                        {'$match': {
                            'fecha_incidencia': {
                                '$gte': dateFromWeek,
                                '$lte': dateToWeek
                            }
                        }},
                        {'$group': {
                            '_id': {
                                'year': {'$isoWeekYear': '$fecha_incidencia'},
                                'week': {'$isoWeek': '$fecha_incidencia'}
                            },
                            'incidentes_x_semana': {'$sum': 1}
                        }}
                    ],
                    'por_mes': [
                        {'$match': {
                            'fecha_incidencia': {
                                '$gte': datetime.combine(today_date.replace(day=1), time.min),
                                '$lte': datetime.combine(today_date, time.max)
                            }
                        }},
                        {'$group': {
                            '_id': {
                                'year': {'$year': '$fecha_incidencia'},
                                'month': {'$month': '$fecha_incidencia'}
                            },
                            'incidentes_x_mes': {'$sum': 1}
                        }}
                    ]
                }}
            ]

            resultado = self.format_cr(self.cr.aggregate(query_incidentes))[0]

            res['incidentes_x_dia'] = resultado['por_dia'][0]['incidentes_x_dia'] if resultado['por_dia'] else 0
            res['incidentes_x_semana'] = resultado['por_semana'][0]['incidentes_x_semana'] if resultado['por_semana'] else 0
            res['incidentes_x_mes'] = resultado['por_mes'][0]['incidentes_x_mes'] if resultado['por_mes'] else 0

            match_query_fallas = {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_FALLAS,
                f"answers.{self.fallas_fields['falla_estatus']}": 'abierto',
            }

            if location:
                match_query_fallas.update({
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.fallas_fields['falla_ubicacion']}": location,
                })
            if booth_area:
                match_query_fallas.update({
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.fallas_fields['falla_caseta']}": booth_area,
                })

            #Fallas pendientes
            query_fallas = [
                {'$match': match_query_fallas},
                {'$project': {
                    '_id': 1,
                }},
                {'$group': {
                    '_id': None,
                    'fallas_pendientes': {'$sum': 1}
                }}
            ]

            resultado = self.format_cr(self.cr.aggregate(query_fallas))
            fallas_pendientes = resultado[0]['fallas_pendientes'] if resultado else 0

            res['fallas_pendientes'] = fallas_pendientes
        elif page == 'Articulos':
            #Articulos concesionados pendientes
            query_concesionados = [
                {'$match': {
                    "deleted_at": {"$exists": False},
                    "form_id": self.CONCESSIONED_ARTICULOS,
                    f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}": location,
                    f"answers.{self.cons_f['status_concesion']}": "abierto",
                }},
                {'$project': {
                    '_id': 1,
                }},
                {'$group': {
                    '_id': None,
                    'articulos_concesionados_pendientes': {'$sum': 1}
                }}
            ]

            resultado = self.format_cr(self.cr.aggregate(query_concesionados))
            articulos_concesionados_pendientes = resultado[0]['articulos_concesionados_pendientes'] if resultado else 0
            
            res['articulos_concesionados_pendientes'] = articulos_concesionados_pendientes

            #Articulos perdidos
            query_perdidos = [
                {'$match': {
                    "deleted_at": {"$exists": False},
                    "form_id": self.BITACORA_OBJETOS_PERDIDOS,
                    f"answers.{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.perdidos_fields['ubicacion_perdido']}": location,
                    f"answers.{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.perdidos_fields['area_perdido']}": booth_area,
                }},
                {'$project': {
                    '_id': 1,
                    'status_perdido': f"$answers.{self.perdidos_fields['estatus_perdido']}",
                }},
                {'$group': {
                    '_id': None,
                    'perdidos_info': {
                        '$push': {
                            'status_perdido':'$status_perdido'
                        }
                    }
                }}
            ]

            resultado = self.format_cr(self.cr.aggregate(query_perdidos))
            perdidos_info = resultado[0]['perdidos_info'] if resultado else []

            articulos_perdidos = 0
            for perdido in perdidos_info:
                status_perdido = perdido.get('status_perdido', '').lower()
                if status_perdido not in ['entregado', 'donado']:
                    articulos_perdidos += 1

            res['articulos_perdidos'] = articulos_perdidos

            match_query_paqueteria = {
                "deleted_at": {"$exists": False},
                "form_id": self.PAQUETERIA,
                f"answers.{self.paquetes_fields['estatus_paqueteria']}": "guardado",
            }

            if location:
                match_query_paqueteria.update({
                    f"answers.{self.paquetes_fields['ubicacion_paqueteria']}": location,
                })
            if booth_area and not booth_area == "todas" and not booth_area == "":
                match_query_paqueteria.update({
                    f"answers.{self.paquetes_fields['area_paqueteria']}": booth_area,
                })

            query_paqueteria = [
                {'$match': match_query_paqueteria },
                {'$project': {
                    '_id': 1,
                }},
                {'$group': {
                    '_id': None,
                    'paquetes_recibidos': {'$sum': 1},
                }}
            ]

            resultado_paquetes = self.format_cr(self.cr.aggregate(query_paqueteria))
            paquetes_recibidos = resultado_paquetes[0]['paquetes_recibidos'] if resultado_paquetes else 0

            res['paquetes_recibidos'] = paquetes_recibidos

        elif page == 'Notas':
            #Notas
            match_query = {
                "deleted_at": {"$exists": False},
                "form_id": self.ACCESOS_NOTAS,
                f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}": location,
            }

            if booth_area and not booth_area == "todas" and not booth_area == "":
                match_query.update({
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}": booth_area,
                })
                
            query_notas = [
                {'$match': match_query},
                {'$project': {
                    '_id': 1,
                    'nota_status': f"$answers.{self.notes_fields['note_status']}",
                    'fecha_apertura': f"$answers.{self.notes_fields['note_open_date']}",
                    'fecha_cierre': f"$answers.{self.notes_fields['note_close_date']}"
                }},
            ]

            notas = self.format_cr(self.cr.aggregate(query_notas))
            notas_del_dia = 0
            notas_abiertas = 0
            notas_cerradas = 0

            for nota in notas:
                if(nota.get('nota_status') == 'abierto'):
                    notas_abiertas += 1
                if(nota.get('fecha_apertura') >= f"{today} 00:00:00" and nota.get('fecha_apertura') <= f"{today} 23:59:59"):
                    notas_del_dia += 1
                if(nota.get('fecha_cierre') and nota.get('nota_status') == 'cerrado'):
                   notas_cerradas += 1

            res['notas_abiertas'] = notas_abiertas
            res['notas_del_dia'] = notas_del_dia
            res['notas_cerradas'] = notas_cerradas

        return res

    def get_certificacion(self, certificacion, id_user, empresa=None):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CARGA_PERMISOS_VISITANTES,
            f"answers.{self.DEFINICION_PERMISOS_OBJ_ID}.{self.mf['nombre_permiso']}":certificacion,
            f"answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['curp']}":id_user,
        }
        if empresa:
            match_query.update(
                {f"answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['empresa']}":empresa}
            )
        result  =self.format_cr(self.cr.find(match_query,{'answers':1}), get_one=True)
        result  = self._labels(result, self.mf)
        return result

    def get_config_accesos(self):
        response = []
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CONF_ACCESOS,
            f"answers.{self.Employee.EMPLOYEE_OBJ_ID}.{self.Employee.employee_fields['user_id_id']}":self.user['user_id'],
        }
        query = [
            {'$match': match_query },
            {"$sort": {"created_at": -1}},
            {'$limit':1},
            {'$project': {
                "usuario":f"$answers.{self.conf_accesos_fields['usuario_cat']}",
                "grupos":f"$answers.{self.conf_accesos_fields['grupos']}",
                "menus": f"$answers.{self.conf_accesos_fields['menus']}",
            }},
            {'$lookup': {
                'from': 'form_answer',
                'pipeline': [
                    {'$match': {
                        'deleted_at': {'$exists': False},
                        'form_id': self.CONF_MODULO_SEGURIDAD,
                    }},
                    {'$project': {
                        "_id": 0,
                        "excluir": f"$answers.{self.f['personalizacion_pases']}",
                        "incluir": f"$answers.{self.f['grupo_incluir']}",
                        "alertas": f"$answers.{self.f['grupo_alertas']}",
                        "requisitos": f"$answers.{self.conf_modulo_seguridad['grupo_requisitos']}",
                    }}
                ],
                'as': 'personalizaciones'
            }},
            {'$unwind': '$personalizaciones'},
            {'$project': {
                "usuario":1,
                "grupos":1,
                "menus":1,
                "exclude_inputs": "$personalizaciones.excluir",
                "include_inputs": "$personalizaciones.incluir",
                "alertas": "$personalizaciones.alertas",
                "requisitos": "$personalizaciones.requisitos",
            }}
        ]
        print('self.cr', self.cr)
        data = self.format_cr_result(self.cr.aggregate(query),  get_one=True)
        format_data = {}
        if data:
            exclude_inputs = data.get('exclude_inputs', [])
            format_exclude_inputs = self.unlist([i for i in exclude_inputs])

            include_inputs = data.get('include_inputs', [])
            format_include_inputs = self.unlist([i for i in include_inputs])

            alertas = data.get('alertas', [])
            format_alerts = []
            for i in alertas:
                new_item = {}
                new_item[i.get('nombre_alerta')] = {
                    'accion': i.get('accion_alerta', '') if len(i.get('accion_alerta', [])) > 1 else self.unlist(i.get('accion_alerta', [])),
                }
                if 'llamar' in i.get('accion_alerta') or 'sms' in i.get('accion_alerta'):
                    new_item[i.get('nombre_alerta')]['number'] = i.get('llamar_num_alerta', 0000000000)
                if 'email' in i.get('accion_alerta'):
                    new_item[i.get('nombre_alerta')]['email'] = i.get('email_alerta', '')
                format_alerts.append(new_item)

            grupo_requisitos = data.get('requisitos', [])

            format_grupo_requisitos = []
            for req in grupo_requisitos:
                format_grupo_requisitos.append({
                    'envio_por': req.get('envio_por',[]) ,
                    'datos_requeridos': req.get('datos_requeridos',[]) ,
                    'ubicacion': self.unlist(req.get('incidente_location') or []),
                    'prefijo_telefonico': req.get('prefijo_telefonico'),
                    'tolerancia_de_entrada_previa': req.get('tolerancia_de_entrada_previa'),
                    'tolerancia_de_entrada_posterior': req.get('tolerancia_de_entrada_posterior')
                })
            data.update({
                'exclude_inputs': format_exclude_inputs,
                'include_inputs': format_include_inputs,
                'alertas': format_alerts,
                'requisitos': format_grupo_requisitos,
            })
        # print(simplejson.dumps(data, indent=4))
        return data

    def get_config_modulo_seguridad(self, ubicaciones=[]):
        #TODO Verificar por que se envia asi la lista
        if isinstance(ubicaciones, list) and ubicaciones and isinstance(ubicaciones[0], dict):
            ubicaciones = [u.get('name') or u.get('id') for u in ubicaciones]
        requerimientos = set()
        envios = set()
        match_query = {
            "deleted_at": {"$exists": False},
            "form_id": self.CONF_MODULO_SEGURIDAD,
        }
        query = [
            {'$match': match_query},
            {'$sort': {'updated_at': -1}},
            {'$limit': 1},
            {'$project': {
                "grupo_requisitos": f"$answers.{self.conf_modulo_seguridad['grupo_requisitos']}",
            }},
        ]
    
        raw_result = self.format_cr(self.cr.aggregate(query))
        for raw in raw_result:
            for grupo in raw.get('grupo_requisitos', []):
                #TODO Verficiar el cambio de key
                ubicacion = grupo.get('incidente_location', grupo.get('ubicacion_recorrido', ''))
                if ubicacion in ubicaciones:
                    clave_conf = self.conf_modulo_seguridad.get('datos_requeridos')
                    reqs = grupo.get('datos_requeridos') or grupo.get(clave_conf, [])
                    if isinstance(reqs, list):
                        requerimientos.update(reqs)
                    envios = set()
                    envio_por_list = self.conf_modulo_seguridad.get('envio_por', [])
                    for item in envio_por_list if isinstance(envio_por_list, list) else [envio_por_list]:
                        envs = grupo.get(item) or grupo.get('envio_por', [])
                        if envs:
                            if isinstance(envs, list):
                                envios.update(envs)
                            else:
                                envios.add(envs)

        tipos = self.get_tipos_de_pase(ubicaciones)
        return {
            "ubicaciones": ubicaciones,
            "requerimientos": list(requerimientos),
            "envios": list(envios),
            "tipos": tipos
        }

    def get_count_ingresos(self, qr_code):
        total_entradas=""
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_ACCESOS,
            f"answers.{self.mf['codigo_qr']}":qr_code
        }
        query = [
            {'$match': match_query },
            {'$project': {
                'folio':'$folio',
                }
            },
            {'$count': 'total_records'}
        ]
        total_entradas = self.format_cr_result(self.cr.aggregate(query))
        if total_entradas:
            total_entradas = total_entradas.pop()
        return total_entradas

    def get_detail_access_pass(self, qr_code, get_answers=False):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.PASE_ENTRADA,
            "_id":ObjectId(qr_code),
        }
        print("QR", qr_code)
        query = [
            {'$match': match_query },
            {'$project':
                {'_id':1,
                'folio': f"$folio",
                'answers':'$answers',
                'ubicacion': f"$answers.{self.mf['grupo_ubicaciones_pase']}.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}",
                'nombre': {"$ifNull":[
                    f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['nombre_visita']}",
                    f"$answers.{self.mf['nombre_pase']}"]},
                'estatus': f"$answers.{self.pase_entrada_fields['status_pase']}",
                'empresa': {"$ifNull":[
                     f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['empresa']}",
                     f"$answers.{self.mf['empresa_pase']}"]},
                'email':  {"$ifNull":[
                    f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['email_vista']}",
                    f"$answers.{self.mf['email_pase']}"]},
                'telefono': {"$ifNull":[
                    f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['telefono']}",
                    f"$answers.{self.mf['telefono_pase']}"]},
                'curp': f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['curp']}",
                'fecha_de_expedicion': f"$answers.{self.mf['fecha_desde_visita']}",
                'fecha_de_caducidad':{'$ifNull':[
                    f"$answers.{self.mf['fecha_desde_hasta']}",
                    f"$answers.{self.mf['fecha_desde_visita']}",
                    ]
                    },
                'foto': {'$ifNull':[
                    f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['foto']}",
                    f"$answers.{self.pase_entrada_fields['walkin_fotografia']}"]},
                'limite_de_acceso': f"$answers.{self.mf['config_limitar_acceso']}",
                'config_dia_de_acceso': f"$answers.{self.mf['config_dia_de_acceso']}",
                'identificacion': {'$ifNull':[
                    f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['identificacion']}",
                    f"$answers.{self.pase_entrada_fields['walkin_identificacion']}"]},
                'limitado_a_dias':f"$answers.{self.mf['config_dias_acceso']}",
                'motivo_visita':f"$answers.{self.CONFIG_PERFILES_OBJ_ID}.{self.mf['motivo']}",
                'perfil_pase':f"$answers.{self.CONFIG_PERFILES_OBJ_ID}",
                'tipo_de_pase':f"$answers.{self.pase_entrada_fields['perfil_pase']}",
                'tipo_de_comentario': f"$answers.{self.mf['tipo_de_comentario']}",
                'visita_a_nombre':
                     f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}",
                'visita_a_puesto': 
                    f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['puesto_empleado']}",
                'visita_a_departamento':
                    f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['departamento_empleado']}",
                'visita_a_user_id':
                    f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['user_id_empleado']}",
                'visita_a_email':
                    f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['email_visita_a']}",
                'visita_a_telefono':
                    f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['telefono_visita_a']}",
                'grupo_areas_acceso': f"$answers.{self.mf['grupo_areas_acceso']}",
                # 'grupo_commentario_area': f"$answers.{self.mf['grupo_commentario_area']}",
                'grupo_equipos': f"$answers.{self.mf['grupo_equipos']}",
                'grupo_vehiculos': f"$answers.{self.mf['grupo_vehiculos']}",
                'grupo_instrucciones_pase': f"$answers.{self.mf['grupo_instrucciones_pase']}",
                'comentario': f"$answers.{self.mf['grupo_instrucciones_pase']}",
                'codigo_qr': f"$answers.{self.mf['codigo_qr']}",
                'qr_pase': f"$answers.{self.mf['qr_pase']}",
                'tema_cita': f"$answers.{self.pase_entrada_fields['tema_cita']}",
                'descripcion': f"$answers.{self.pase_entrada_fields['descripcion']}",
                'link': f"$answers.{self.pase_entrada_fields['link']}",
                'google_wallet_pass_url': f"$answers.{self.pase_entrada_fields['google_wallet_pass_url']}",
                'apple_wallet_pass': f"$answers.{self.pase_entrada_fields['apple_wallet_pass']}",
                'pdf_to_img': f"$answers.{self.pase_entrada_fields['pdf_to_img']}",
                'acepto_aviso_privacidad': f"$answers.{self.pase_entrada_fields['acepto_aviso_privacidad']}",
                'acepto_aviso_datos_personales': f"$answers.{self.pase_entrada_fields['acepto_aviso_datos_personales']}",
                'conservar_datos_por': f"$answers.{self.pase_entrada_fields['conservar_datos_por']}",
                'ubicaciones': f"$answers.{self.pase_entrada_fields['ubicaciones']}",
                'habilitar_vehiculo': {"$ifNull": [f"$answers.{self.pase_entrada_fields['habilitar_vehiculo']}", True]},
                'tipo_visita_pase': f"$answers.{self.mf['tipo_visita_pase']}",
                'acompanantes': f"$answers.{self.pase_entrada_fields['acompanantes']}",
                'acompanantes_grupo': f"$answers.{self.pase_entrada_fields['acompanantes_grupo']}",
                'url_padre': f"$answers.{self.pase_entrada_fields['url_padre']}",
                },
            },
            {'$sort':{'folio':-1}},
        ]
        res = self.cr.aggregate(query)
        x = {}
        for x in res:
            visita_a =[]
            x['_id'] = str(x.pop('_id'))
            v = x.pop('visita_a_nombre') if x.get('visita_a_nombre') else []
            d = x.get('visita_a_departamento',[])
            p = x.get('visita_a_puesto',[])
            e =  x.get('visita_a_user_id',[])
            u =  x.get('visita_a_email',[])
            f =  x.get('visita_a_telefono',[])
            x['empresa'] = self.unlist(x.get('empresa',''))
            x['email'] =self.unlist(x.get('email',''))
            x['telefono'] = self.unlist(x.get('telefono',''))
            x['curp'] = self.unlist(x.get('curp',''))
            x['motivo_visita'] = self.unlist(x.get('motivo_visita',''))
            for idx, nombre in enumerate(v):
                emp = {'nombre':nombre}
                if d:
                    emp.update({'departamento':d[idx].pop(0) if d[idx] else ""})
                if p:
                    emp.update({'puesto':p[idx].pop(0) if p[idx] else ""})
                if e:
                    emp.update({'user_id':e[idx].pop(0) if e[idx] else ""})
                if u:
                    emp.update({'email': u[idx].pop(0) if u[idx] else ""})
                if f:
                    emp.update({'telefono': f[idx].pop(0) if f[idx] else ""})
                visita_a.append(emp)
            x['visita_a'] = visita_a
            perfil_pase = x.pop('perfil_pase') if x.get('perfil_pase') else []
            perfil_pase = self._labels(perfil_pase, self.mf)
            if x.get('fecha_de_caducidad') == "":
                x['fecha_de_caducidad'] = x.get('fecha_de_expedicion')
            if perfil_pase:
                x['tipo_de_pase'] = perfil_pase.pop('nombre_perfil')
                empresa = x.get('empresa')
                x['certificaciones'] = self.format_perfil_pase(perfil_pase, x['curp'], empresa)
            x['grupo_areas_acceso'] = self._labels_list(x.pop('grupo_areas_acceso',[]), self.mf)
            x['grupo_instrucciones_pase'] = self._labels_list(x.pop('grupo_instrucciones_pase',[]), self.mf)
            x['grupo_equipos'] = self._labels_list(x.pop('grupo_equipos',[]), self.mf)
            x['grupo_vehiculos'] = self._labels_list(x.pop('grupo_vehiculos',[]), self.mf)
            x['ubicacion'] = x.get('ubicacion', [])
            ubicaciones = x.get('ubicaciones', [])
            ubicaciones_format = []
            for ubicacion in ubicaciones:
                ubicaciones_format.append(ubicacion.get(self.Location.UBICACIONES_CAT_OBJ_ID, {}).get(self.mf['ubicacion'], ''))
            x['ubicaciones'] = ubicaciones_format
        if not x:
            self.LKFException({'title':'Advertencia', 'msg':'Este pase fue eliminado o no pertenece a esta organizacion.'})
        return x

    def get_ids_labels(self, data):
        return data

    def get_employee_checkin_status(self, user_ids, as_shift=False,  **kwargs):
        query = []
        if kwargs.get('user_id'):
            user_id = kwargs['user_id']
        else:
            user_id = self.user.get('user_id')
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CHECKIN_CASETAS,
            }
        unwind = {'$unwind': f"$answers.{self.f['guard_group']}"}
        query = [{'$match': match_query }, unwind ]

        unwind_query = {f"answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['user_id_jefes']}": {"$exists":True}}
        if as_shift:
            match_query.update({'created_by_id':user_id})
            query = [
                {'$match': match_query },
                {'$sort':{'created_at':-1}},
                {'$limit':1},
                unwind
                ]
        else:
            if type(user_ids) == list:
                unwind_query.update({f"answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['user_id_jefes']}": {"$in": user_ids}})
            else:
                unwind_query.update({f"answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['user_id_jefes']}": user_ids })
        query += [ {'$match': unwind_query }]
        query += [
            {'$addFields': {
                'priority': {
                    '$cond': [{'$eq': [f"$answers.{self.f['guard_group']}.{self.f['checkin_status']}", 'entrada']}, 1, 0]
                }
            }},
            {'$project':
                {'_id': 1,
                    'folio': "$folio",
                    'created_at': "$created_at",
                    'name': f"$answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['worker_name_jefes']}",
                    'user_id': {"$first":f"$answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['user_id_jefes']}"},
                    'location': f"$answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['ubicacion']}",
                    'area': f"$answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_area']}",
                    'checkin_date': f"$answers.{self.f['guard_group']}.{self.f['checkin_date']}",
                    'checkout_date': f"$answers.{self.f['guard_group']}.{self.f['checkout_date']}",
                    'checkin_status': f"$answers.{self.f['guard_group']}.{self.f['checkin_status']}",
                    'checkin_position': f"$answers.{self.f['guard_group']}.{self.f['checkin_position']}",
                    'nombre_suplente': f"$answers.{self.f['guard_group']}.{self.checkin_fields['nombre_suplente']}",
                    'priority': '$priority',
                    }
            },
            {'$sort':{'priority':-1, 'created_at':-1}},
            {'$group':{
                '_id':{
                    'user_id':'$user_id',
                    },
                'name':{'$first':'$name'},
                'location':{'$first':'$location'},
                'area':{'$first':'$area'},
                'checkin_date':{'$first':'$checkin_date'},
                'checkout_date':{'$first':'$checkout_date'},
                'checkin_status':{'$first':'$checkin_status'},
                'checkin_position':{'$first':'$checkin_position'},
                'folio':{'$first':'$folio'},
                'id_register':{'$first':'$_id'},
                'nombre_suplente':{'$first':'$nombre_suplente'},

            }},
            {'$project':{
                '_id':0,
                'user_id':'$_id.user_id',
                'name':'$name',
                'location':'$location',
                'area':'$area',
                'checkin_date':'$checkin_date',
                'checkout_date':'$checkout_date',
                'checkin_status': {'$cond': [ {'$eq':['$checkin_status','entrada']},'in','out']},
                'checkin_position':'$checkin_position',
                'folio':'$folio',
                'id_register':'$id_register',
                'nombre_suplente':'$nombre_suplente',

            }}
            ]
        data = self.format_cr(self.cr.aggregate(query))
        res = {}
        for rec in data:
            status = 'in' if rec.get('checkin_status') in ['in','entrada'] else 'out'
            user_id = rec.get('user_id') or 0
            res[int(user_id)] = {
                'status':status,
                'name': rec.get('name'),
                'folio': rec.get('folio'),
                '_id': str(rec.get('id_register')),
                'user_id': rec.get('user_id'),
                'location':rec.get('location'),
                'area':rec.get('area'),
                'checkin_date':rec.get('checkin_date'),
                'checkout_date':rec.get('checkout_date'),
                'checkin_position':rec.get('checkin_position'),
                'nombre_suplente':rec.get('nombre_suplente',"")
                }
        return res

    def get_employee_checkin_status_by_id(self, user_id, location, area):
        """
        Obtiene el estado de checkin de un empleado
        Args:
            user_id (int): ID del usuario

        Returns:
            dict: Estado de checkin del usuario
        """
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CHECKIN_CASETAS,
        }
        query = [
            {'$match': match_query},
            {'$unwind': f"$answers.{self.f['guard_group']}"},
            {'$match': {
                f"answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.mf['id_usuario']}": {"$exists":True},
                f"answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.mf['id_usuario']}": {"$in": [user_id]},
            }},
            {'$addFields': {
                'priority': {
                    '$cond': [{'$eq': [f"$answers.{self.f['guard_group']}.{self.f['checkin_status']}", 'entrada']}, 1, 0]
                }
            }},
            {'$sort': {'priority': -1, 'created_at': -1}},
            {'$limit': 1},
            {'$project': {
                '_id': 1,
                'folio': "$folio",
                'created_at': "$created_at",
                'name': f"$answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['worker_name_jefes']}",
                'user_id': {"$first":f"$answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.mf['id_usuario']}"},
                'location': f"$answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['ubicacion']}",
                'area': f"$answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_area']}",
                'checkin_date': f"$answers.{self.f['guard_group']}.{self.f['checkin_date']}",
                'checkout_date': f"$answers.{self.f['guard_group']}.{self.f['checkout_date']}",
                'checkin_status': f"$answers.{self.f['guard_group']}.{self.f['checkin_status']}",
                'checkin_position': f"$answers.{self.f['guard_group']}.{self.f['checkin_position']}",
                'nombre_suplente': f"$answers.{self.f['guard_group']}.{self.checkin_fields['nombre_suplente']}",
            }},
            {'$group':{
                '_id': {
                    'user_id':'$user_id',
                },
                'name': {'$last':'$name'},
                'location': {'$last':'$location'},
                'area': {'$last':'$area'},
                'checkin_date': {'$last':'$checkin_date'},
                'checkout_date': {'$last':'$checkout_date'},
                'checkin_status': {'$last':'$checkin_status'},
                'checkin_position': {'$last':'$checkin_position'},
                'folio': {'$last':'$folio'},
                'id_register': {'$last':'$_id'},
                'nombre_suplente': {'$last':'$nombre_suplente'}
            }},
            {'$project':{
                '_id': 0,
                'user_id': '$_id.user_id',
                'name': '$name',
                'location': '$location',
                'area': '$area',
                'checkin_date': '$checkin_date',
                'checkout_date': '$checkout_date',
                'checkin_status': {'$cond': [ {'$eq':['$checkin_status','entrada']},'in','out']},
                'checkin_position': '$checkin_position',
                'folio': '$folio',
                'id_register': '$id_register',
                'nombre_suplente': '$nombre_suplente'
            }}
        ]
        data = self.format_cr(self.cr.aggregate(query))
        format_data = {}
        if data:
            record = self.unlist(data)
            status = 'in' if record.get('checkin_status') in ['in', 'entrada'] else 'out'
            format_data = {
                'status':status,
                'name': record.get('name'),
                'folio': record.get('folio'),
                '_id': str(record.get('id_register')),
                'user_id': record.get('user_id'),
                'location':record.get('location'),
                'area':record.get('area'),
                'checkin_date':record.get('checkin_date'),
                'checkout_date':record.get('checkout_date'),
                'checkin_position':record.get('checkin_position'),
                'nombre_suplente':record.get('nombre_suplente',"")
            }
        return format_data

    def get_checkin_by_id(self, _id=None, folio=None):
        # Obtiene el registro de check-in por ID o folio.

        if not _id or not folio:
            msg = "An _id or a folio is required to get the record"
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CHECKIN_CASETAS,
            }
        if _id:
            match_query.update({"_id":ObjectId(_id)})
        elif folio:
            match_query.update({"folio":folio})
        query = [
            {'$match': match_query },
            {'$project': self.proyect_format(self.checkin_fields)},
            {'$sort':{'updated_at':-1}},
            {'$limit':1}
            ]
        return self.format_cr_result(self.cr.aggregate(query), get_one=True)
 
    def get_last_checkin(self, location, area):
        # Obtiene el último registro de check-in por ubicación y área.

        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CHECKIN_CASETAS,
            f"answers.{self.checkin_fields['cat_location']}":location,
            f"answers.{self.checkin_fields['cat_area']}":area,
            }
        query = [
            {'$match': match_query },
            {'$project': self.project_format(self.checkin_fields)},
            {'$sort':{'created_at':-1}},
            {'$limit':1}
            ]
        return self.format_cr_result(self.cr.aggregate(query), get_one=True)

    def get_open_checkin(self, location, area):
        """Busca explícitamente un registro de checkin con estado abierto para una caseta.
        A diferencia de get_last_checkin, filtra por checkin_type abierto antes de ordenar,
        evitando falsos negativos cuando el registro más reciente ya fue cerrado."""
        open_statuses = ['entrada', 'apertura', 'disponible', 'abierta']
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.CHECKIN_CASETAS,
                f"answers.{self.checkin_fields['cat_location']}": location,
                f"answers.{self.checkin_fields['cat_area']}": area,
                f"answers.{self.checkin_fields['checkin_type']}": {"$in": open_statuses},
            }},
            {'$project': self.project_format(self.checkin_fields)},
            {'$sort': {'created_at': -1}},
            {'$limit': 1},
        ]
        return self.format_cr_result(self.cr.aggregate(query), get_one=True)

    def extends_date_of_pass(self, qr_code, update_obj):
        if not qr_code:
            return self.LKFException({'title': 'Error', 'msg': 'No se proporciono el QR code'})
        if not update_obj.get('fecha_desde'):
            return self.LKFException({'title': 'Error', 'msg': 'No se proporciono una fecha valida'})

        answers = {}
        answers[self.mf['fecha_desde_visita']] = update_obj.get('fecha_desde')
        answers[self.mf['fecha_desde_hasta']] = update_obj.get('fecha_hasta', None)

        if answers:
            res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.PASE_ENTRADA, record_id=[qr_code,])
            return res
        return False

    def close_orphaned_checkin(self, orphaned_record, closed_record):
        """Cierra un registro de checkin huérfano usando la hora de cierre
        del registro más reciente ya cerrado. Actualiza tanto el estatus
        general de la caseta como el checkin_status individual de cada guardia."""
        record_id = orphaned_record.get('_id', orphaned_record.get('id'))
        checkout_time = closed_record.get('boot_checkout_date', self.today_str(date_format='datetime'))
        data = self.lkf_api.get_metadata(self.CHECKIN_CASETAS)
        record = self.get_record_by_id(record_id)
        answers = record['answers']
        answers[self.checkin_fields['checkin_type']] = 'cerrada'
        answers[self.checkin_fields['boot_checkout_date']] = checkout_time
        answers[self.checkin_fields['forzar_cierre']] = 'forzar'
        for guard in answers.get(self.f['guard_group'], []):
            if guard.get(self.checkin_fields['checkin_status']) != 'salida':
                guard[self.checkin_fields['checkin_status']] = 'salida'
                guard[self.checkin_fields['checkout_date']] = checkout_time
        data['answers'] = answers
        return self.lkf_api.patch_record(data=data, record_id=record_id)

    def get_guard_last_checkin(self, user_ids):
        '''
            Se realiza busqued del ulisto registro de checkin de un usuario
        '''
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CHECKIN_CASETAS,
            }
        unwind_query = {}
        if user_ids and type(user_ids) == list:
            if len(user_ids) == 1:
                #hace la busqueda por directa, para optimizar recuros
                user_ids = user_ids[0]
            else:
                #hace busqueda en lista de opciones
                match_query.update({
                    f"answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['user_id_jefes']}":{'$in':user_ids}
                    })
        if user_ids and type(user_ids) == int:
            unwind_query.update({
                f"answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['user_id_jefes']}":user_ids
                })
        if not unwind_query:
            return self.LKFException({"msg":f"Algo salio mal al intentar buscar el checkin del los ids: {user_id}"})
        query = [
            {'$match': match_query },
            {'$unwind': f"$answers.{self.f['guard_group']}"},
            {'$match':unwind_query},
            {'$project': self.project_format(self.checkin_fields)},
            {'$sort':{'created_at':-1}},
            {'$limit':1}
            ]
        return self.format_cr_result(self.cr.aggregate(query), get_one=True)

    def get_last_user_move(self, qr, location, record_id=None):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_ACCESOS,
            f"answers.{self.mf['codigo_qr']}":qr,
        }
        if record_id:
            match_query["_id"] = ObjectId(record_id)
        res = self.cr.find(
            match_query, 
            {
                'folio':'$folio', 
                'status_visita': f"$answers.{self.bitacora_fields['status_visita']}",
                'checkin_date': f"$answers.{self.bitacora_fields['fecha_entrada']}",
                'checkout_date': f"$answers.{self.bitacora_fields['fecha_salida']}",
                'gafete_id': f"$answers.{self.GAFETES_CAT_OBJ_ID}.{self.gafetes_fields['gafete_id']}",
                'gafete_id': f"$answers.{self.GAFETES_CAT_OBJ_ID}.{self.gafetes_fields['gafete_id']}",
                'locker_id': f"$answers.{self.LOCKERS_CAT_OBJ_ID}.{self.mf['locker_id']}",
                'ubicacion_entrada': f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
                'status_gafete':f"$answers.{self.bitacora_fields['status_gafete']}"
                }
            ).sort('updated_at', -1).limit(1)
        return self.format_cr(res, get_one=True)
        # return self.format_cr_result(self.cr.aggregate(query), get_one=True)

    def procesar_devoluciones_item(self, item):
        equipos = item.get('grupo_equipos', [])
        devoluciones_totales = item.get('grupo_equipos_devolucion', [])
        for equipo in equipos:
            id_mov = equipo.get('id_movimiento')
            devoluciones_equipo = [
                dev for dev in devoluciones_totales
                if dev.get('id_movimiento_devolucion') == id_mov
            ]
            equipo['devoluciones'] = devoluciones_equipo
        return item

    def get_list_articulos_concesionados(self, location="", area="", status="", dateFrom="", dateTo="", filterDate=""):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CONCESSIONED_ARTICULOS,
        }
        if location:
             match_query[f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.perdidos_fields['ubicacion_perdido']}"] = location
        if area:
             match_query[f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area_salida']}"] = area
        if status:
             match_query[f"answers.{self.cons_f['status_concesion']}"] = status

        zona = self.user.get('timezone','America/Monterrey')

        if filterDate != "range":
            dateFrom, dateTo = self.get_range_dates(filterDate,zona)
            if dateFrom:
                dateFrom = str(dateFrom)
            if dateTo:
                dateTo = str(dateTo)
        if dateFrom and dateTo:
            match_query.update({
                f"answers.{self.cons_f['fecha_concesion']}": {"$gte": dateFrom,"$lte": dateTo},
            })
        elif dateFrom:
            match_query.update({
                f"answers.{self.cons_f['fecha_concesion']}": {"$gte": dateFrom}
            })
        elif dateTo:
            match_query.update({
                f"answers.{self.cons_f['fecha_concesion']}": {"$lte": dateTo}
            })

        query = [
            {'$match': match_query },
            {'$project': {
                "_id" : "$_id",
                "folio": "$folio",
                "created_at":"$created_at",
                "answers":"$answers",
            }},
            {'$sort':{'created_at':-1}},
        ]
        result = self.format_cr_result(self.cr.aggregate(query), ids_label_dct=self.cons_f)
        for item in result:
            item = self.procesar_devoluciones_item(item)
            item['firma'] = {}
            if item.get('file_url'):
                item['firma']['file_url'] = item.pop('file_url')
            if item.get('file_name'):
                item['firma']['file_name'] = item.pop('file_name')
        return result

    def get_list_article_lost(self, location, area, status=None, dateFrom="", dateTo="", filterDate=""):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_OBJETOS_PERDIDOS,
        }
        if location:
             match_query[f"answers.{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.mf['ubicacion']}"] = location
        if area:
             match_query[f"answers.{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.mf['nombre_area_salida']}"] = area
        if status:
             match_query[f"answers.{self.perdidos_fields['estatus_perdido']}"] = status

        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        zona = user_data.get('timezone','America/Monterrey')

        if filterDate != "range":
            dateFrom, dateTo = self.get_range_dates(filterDate,zona)

            if dateFrom:
                dateFrom = str(dateFrom)
            if dateTo:
                dateTo = str(dateTo)
        if dateFrom and dateTo:
            match_query.update({
                f"answers.{self.perdidos_fields['date_hallazgo_perdido']}": {"$gte": dateFrom,"$lte": dateTo},
            })
        elif dateFrom:
            match_query.update({
                f"answers.{self.perdidos_fields['date_hallazgo_perdido']}": {"$gte": dateFrom}
            })
        elif dateTo:
            match_query.update({
                f"answers.{self.perdidos_fields['date_hallazgo_perdido']}": {"$lte": dateTo}
            })

        query = [
            {'$match': match_query },
            #{'$project': self.proyect_format(self.perdidos_fields)},
            {'$project': {
                "folio":"$folio",
                'created_at':'$created_at',
                'estatus_perdido':f"$answers.{self.perdidos_fields['estatus_perdido']}",
                'date_hallazgo_perdido':f"$answers.{self.perdidos_fields['date_hallazgo_perdido']}",
                'ubicacion_perdido':f"$answers.{self.perdidos_fields['ubicacion_catalog']}.{self.perdidos_fields['ubicacion_perdido']}",
                'area_perdido': f"$answers.{self.perdidos_fields['area_catalog']}.{self.perdidos_fields['area_perdido']}",
                'color_perdido':f"$answers.{self.perdidos_fields['color_perdido']}",
                'articulo_perdido':f"$answers.{self.perdidos_fields['articulo_perdido']}",
                'tipo_articulo_perdido':f"$answers.{self.perdidos_fields['tipo_articulo_catalog']}.{self.perdidos_fields['tipo_articulo_perdido']}",
                'articulo_seleccion':f"$answers.{self.perdidos_fields['articulo_seleccion_catalog']}.{self.perdidos_fields['articulo_seleccion']}",
                'foto_perdido':f"$answers.{self.perdidos_fields['foto_perdido']}",
                'descripcion':f"$answers.{self.perdidos_fields['descripcion']}",
                'comentario_perdido':f"$answers.{self.perdidos_fields['comentario_perdido']}",
                'quien_entrega_interno':f"$answers.{self.perdidos_fields['quien_entrega_catalog']}.{self.perdidos_fields['quien_entrega_interno']}",
                'quien_entrega':f"$answers.{self.perdidos_fields['quien_entrega']}",
                'quien_entrega_externo':f"$answers.{self.perdidos_fields['quien_entrega_externo']}",
                'recibe_perdido':f"$answers.{self.perdidos_fields['recibe_perdido']}",
                'telefono_recibe_perdido':f"$answers.{self.perdidos_fields['telefono_recibe_perdido']}",
                'identificacion_recibe_perdido':f"$answers.{self.perdidos_fields['identificacion_recibe_perdido']}",
                'foto_recibe_perdido':f"$answers.{self.perdidos_fields['foto_recibe_perdido']}",
                'date_entrega_perdido':f"$answers.{self.perdidos_fields['date_entrega_perdido']}",
                'locker_perdido':f"$answers.{self.perdidos_fields['locker_catalog']}.{self.perdidos_fields['locker_perdido']}"
            }},
            {'$sort':{'created_at':-1}},
        ]
        if not filterDate:
            query.append(
                {"$limit":25}
            )
        pr= self.format_cr_result(self.cr.aggregate(query))
        return self.format_cr_result(self.cr.aggregate(query))

    def get_list_article_concessioned(self, location="", area="", status="", dateFrom="", dateTo="", filterDate=""):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CONCESSIONED_ARTICULOS,
        }
        if location:
             match_query[f"answers.{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.perdidos_fields['ubicacion_perdido']}"] = location
        if area:
             match_query[f"answers.{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.mf['nombre_area_salida']}"] = area
        if status:
             match_query[f"answers.{self.cons_f['status_concesion']}"] = status

        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        zona = user_data.get('timezone','America/Monterrey')

        if filterDate != "range":
            dateFrom, dateTo = self.get_range_dates(filterDate,zona)

            if dateFrom:
                dateFrom = str(dateFrom)
            if dateTo:
                dateTo = str(dateTo)
        if dateFrom and dateTo:
            match_query.update({
                f"answers.{self.cons_f['fecha_concesion']}": {"$gte": dateFrom,"$lte": dateTo},
            })
        elif dateFrom:
            match_query.update({
                f"answers.{self.cons_f['fecha_concesion']}": {"$gte": dateFrom}
            })
        elif dateTo:
            match_query.update({
                f"answers.{self.cons_f['fecha_concesion']}": {"$lte": dateTo}
            })

        query = [
            {'$match': match_query },
            {'$project': {
                "_id" : "$_id",
                "folio": "$folio",
                'status_concesion':f"$answers.{self.cons_f['status_concesion']}",
                'ubicacion_concesion':f"$answers.{self.cons_f['ubicacion_concesion']}",
                'solicita_concesion':f"$answers.{self.cons_f['solicita_concesion']}",
                'persona_nombre_concesion':f"$answers.{self.cons_f['persona_nombre_concesion']}",
                'caseta_concesion':f"$answers.{self.cons_f['caseta_concesion']}",
                'fecha_concesion':f"$answers.{self.cons_f['fecha_concesion']}",
                'equipo_imagen_concesion':f"$answers.{self.cons_f['equipo_imagen_concesion']}",
                'area_concesion':f"$answers.{self.cons_f['area_concesion']}",
                'equipo_concesion':f"$answers.{self.cons_f['equipo_concesion']}",
                'observacion_concesion':f"$answers.{self.cons_f['observacion_concesion']}",
                'fecha_devolucion_concesion':f"$answers.{self.cons_f['fecha_devolucion_concesion']}",
            }},
            {'$sort':{'folio':-1}},
        ]
        return self.format_cr_result(self.cr.aggregate(query))

    def get_gafetes(self, status='Disponible', location=None, area=None, gafete_id=None, limit=1000, skip=0):
        selector = {}
        if status:
            selector.update({f"answers.{self.mf['status_gafete']}":status})
        if location:
            selector.update({f"answers.{self.f['location']}":location})
        if area:
            selector.update({f"answers.{self.f['area']}":area})
        if gafete_id:
            selector.update({f"answers.{self.gafetes_fields['gafete_id']}":gafete_id})
        if not selector:
            selector = {"_id":{"$gt":None}}
        mango_query = {
            "selector": selector,
            "limit":limit,
            "skip":skip
        }
        return self.format_gafete(self.lkf_api.search_catalog( self.GAFETES_CAT_ID, mango_query))

    def get_lockers(self, status='Disponible', location=None, area=None, tipo_locker='Locker', locker_id=None, limit=1000, skip=0):
        selector = {}
        if status:
            selector.update({f"answers.{self.mf['status_locker']}":status})
        if location:
            selector.update({f"answers.{self.f['location']}":location})
        if area:
            selector.update({f"answers.{self.f['area']}":area})
        if tipo_locker:
            selector.update({f"answers.{self.mf['tipo_locker']}":tipo_locker})
        if locker_id:
            selector.update({f"answers.{self.mf['locker_id']}":locker_id})
        if not selector:
            selector = {"_id":{"$gt":None}}
        mango_query = {
            "selector": selector,
            "limit":limit,
            "skip":skip
        }
        return self.format_lockers(self.lkf_api.search_catalog( self.LOCKERS_CAT_ID, mango_query))

    def get_list_bitacora(self, location=None, area=None, prioridades=[], dateFrom='', dateTo='', filterDate="", dynamic_filters={}, limit=10, offset=0):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_ACCESOS
        }
        if location:
            if isinstance(location, list):
                match_query.update({f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}": {"$in": location}})
            else:
                match_query.update({f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}":location})
        if area:
            match_query.update({f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}":area})
        if prioridades:
            match_query[f"answers.{self.bitacora_fields['status_visita']}"] = {"$in": prioridades}
        if dynamic_filters:
            for item in dynamic_filters:
                if item.get('key') == 'status':
                    match_query[f"answers.{self.mf['tipo_registro']}"] = {"$in": item.get('value')}
                elif item.get('key') == 'perfil_visita':
                    match_query[f"answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['nombre_perfil']}"] = {"$in": item.get('value')}
                elif item.get('key') == 'visita_a':
                    match_query[f"answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}"] = {"$in": item.get('value')}
                elif item.get('key') == 'ubicacion':
                    match_query.update({f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}": {"$in": item.get('value')}})
                else:
                    continue

        zona = self.user.get('timezone','America/Monterrey')
        is_preset_range = bool(filterDate) and filterDate != "range"
        if is_preset_range:
            range_start, range_end = self.get_range_dates(filterDate, zona)
            if range_start:
                dateFrom = str(range_start)
            if range_end:
                dateTo = str(range_end)

        if dateFrom and dateTo:
            if not is_preset_range:
                dateFrom = f"{dateFrom} 00:00:00"
                dateTo = f"{dateTo} 23:59:59"
            match_query.update({
                f"answers.{self.mf['fecha_entrada']}": {"$gte": dateFrom, "$lte": dateTo},
            })
        elif dateFrom:
            if not is_preset_range:
                dateFrom = f"{dateFrom} 00:00:00"
            match_query.update({
                f"answers.{self.mf['fecha_entrada']}": {"$gte": dateFrom}
            })
        elif dateTo:
            if not is_preset_range:
                dateTo = f"{dateTo} 23:59:59"
            match_query.update({
                f"answers.{self.mf['fecha_entrada']}": {"$lte": dateTo}
            })

        proyect_fields ={
            '_id': 1,
            'folio': "$folio",
            'created_at': "$created_at",
            'updated_at': "$updated_at",
            'a_quien_visita':f"$answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}",
            'documento': f"$answers.{self.mf['documento']}",
            'caseta_entrada':f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}",
            'codigo_qr':f"$answers.{self.mf['codigo_qr']}",
            'comentarios':f"$answers.{self.bitacora_fields['grupo_comentario']}",
            'fecha_salida':f"$answers.{self.mf['fecha_salida']}",
            'fecha_entrada':f"$answers.{self.mf['fecha_entrada']}",
            'foto_url': {"$arrayElemAt": [f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['foto']}.file_url", 0]},
            'equipos':f"$answers.{self.mf['grupo_equipos']}",
            'grupo_areas_acceso': f"$answers.{self.mf['grupo_areas_acceso']}",
            'id_gafet': f"$answers.{self.GAFETES_CAT_OBJ_ID}.{self.gafetes_fields['gafete_id']}",
            'id_locker': f"$answers.{self.LOCKERS_CAT_OBJ_ID}.{self.lockers_fields['locker_id']}",
            'identificacion':  {"$first":f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['identificacion']}"},
            'pase_id':{"$toObjectId":f"$answers.{self.mf['codigo_qr']}"},
            'motivo_visita':f"$answers.{self.CONFIG_PERFILES_OBJ_ID}.{self.mf['motivo']}",
            'nombre_area_salida':f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.mf['nombre_area_salida']}",
            'nombre_visitante':f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['nombre_visita']}",
            'contratista':f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['empresa']}",
            'perfil_visita':{'$arrayElemAt': [f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['nombre_perfil']}",0]},
            'status_gafete':f"$answers.{self.mf['status_gafete']}",
            'status_visita':f"$answers.{self.mf['tipo_registro']}",
            'ubicacion':f"$answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
            'vehiculos':f"$answers.{self.mf['grupo_vehiculos']}",
            'visita_a': f"$answers.{self.mf['grupo_visitados']}"
            }
        lookup = {
         'from': 'form_answer',
         'localField': 'pase_id',
         'foreignField': '_id',
         "pipeline": [
                {'$match':{
                    "deleted_at":{"$exists":False},
                    "form_id": self.PASE_ENTRADA,
                    }
                },
                {'$project':{
                    "_id":0, 
                    'motivo_visita':f"$answers.{self.CONFIG_PERFILES_OBJ_ID}.{self.mf['motivo']}",
                    'grupo_areas_acceso': f"$answers.{self.mf['grupo_areas_acceso']}",                    
                    }
                },
                ],
         'as': 'pase',
        }
        query = [
            {'$match': match_query },
            {'$project': proyect_fields},
            {'$lookup': lookup},
        ]
        if dateFrom:
            query.append(
                {'$sort':{'folio':1}},
            )
        else:
            query.append(
                {'$sort':{'folio':-1}},
            )

        query.append({'$skip': offset})
        query.append({'$limit': limit})

        records = self.format_cr(self.cr.aggregate(query))
        count_query = [
            {'$match': match_query},
            {'$count': 'total'}
        ]

        count_result = self.format_cr(self.cr.aggregate(count_query))
        total_count = count_result[0]['total'] if count_result else 0
        total_pages = ceil(total_count / limit) if limit else 1
        current_page = (offset // limit) + 1 if limit else 1

        for r in records:
            pase = r.pop('pase')
            r.pop('pase_id')
            if len(pase) > 0 :
                pase = pase[0]
                r['motivo_visita'] = self.unlist(pase.get('motivo_visita',''))
                r['grupo_areas_acceso'] = self._labels_list(pase.get('grupo_areas_acceso',[]), self.mf)
            r['id_gafet'] = r.get('id_gafet','')
            r['status_visita'] = r.get('status_visita','').title().replace('_', ' ')
            r['contratista'] = self.unlist(r.get('contratista',[]))
            r['status_gafete'] = r.get('status_gafete','').title().replace('_', ' ')
            r['documento'] = r.get('documento','')
            r['grupo_areas_acceso'] = self._labels_list(r.pop('grupo_areas_acceso',[]), self.mf)
            r['comentarios'] = self.format_comentarios(r.get('comentarios',[]))
            r['vehiculos'] = self.format_vehiculos(r.get('vehiculos',[]))
            r['equipos'] = self.format_equipos(r.get('equipos',[]))
            r['visita_a'] = self.format_visita(r.get('visita_a',[]))
        bitacora = {
            'records': records,
            'total_records': total_count,
            'total_pages': total_pages,
            'actual_page': current_page
        }
        return bitacora

    def get_list_fallas(self, location=None, area=None,status=None, folio=None, dateFrom="", dateTo="", filterDate=""):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_FALLAS,
        }
        if location:
            match_query[f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.fallas_fields['falla_ubicacion']}"] = location
        if area:
            match_query[f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.fallas_fields['falla_caseta']}"] = area
        if status:
            match_query[f"answers.{self.fallas_fields['falla_estatus']}"] = status
        if folio:
            match_query.update({"folio":folio})

        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        zona = user_data.get('timezone','America/Monterrey')

        if filterDate != "range":
            dateFrom, dateTo = self.get_range_dates(filterDate,zona)

            if dateFrom:
                dateFrom = str(dateFrom)
            if dateTo:
                dateTo = str(dateTo)

        if dateFrom and dateTo:
            match_query.update({
                f"answers.{self.fallas_fields['falla_fecha_hora']}": {"$gte": dateFrom, "$lte": dateTo},
            })
        elif dateFrom:
            match_query.update({
                f"answers.{self.fallas_fields['falla_fecha_hora']}": {"$gte": dateFrom}
            })
        elif dateTo:
            match_query.update({
                f"answers.{self.fallas_fields['falla_fecha_hora']}": {"$lte": dateTo}
            })

        query = [
            {'$match': match_query },
            {'$project': {
                "folio": "$folio",
                'created_at':'$created_at',
                'falla_estatus': f"$answers.{self.fallas_fields['falla_estatus']}",
                'falla_fecha_hora': f"$answers.{self.fallas_fields['falla_fecha_hora']}",
                'falla_reporta_nombre': f"$answers.{self.fallas_fields['falla_reporta_catalog']}.{self.fallas_fields['falla_reporta_nombre']}",
                'falla_reporta_departamento': f"$answers.{self.fallas_fields['falla_reporta_catalog']}.{self.fallas_fields['falla_reporta_departamento']}",
                'falla_ubicacion': f"$answers.{self.fallas_fields['falla_ubicacion_catalog']}.{self.fallas_fields['falla_ubicacion']}",
                'falla_caseta':f"$answers.{self.fallas_fields['falla_ubicacion_catalog']}.{self.fallas_fields['falla_caseta']}",
                'falla':f"$answers.{self.fallas_fields['falla_catalog']}.{self.fallas_fields['falla']}",
                'falla_objeto_afectado':f"$answers.{self.LISTA_FALLAS_CAT_OBJ_ID}.{self.fallas_fields['falla_subconcepto']}",
                'falla_comentarios':f"$answers.{self.fallas_fields['falla_comentarios']}",
                'falla_evidencia': f"$answers.{self.fallas_fields['falla_evidencia']}",
                'falla_documento':f"$answers.{self.fallas_fields['falla_documento']}",
                'falla_responsable_solucionar_nombre':f"$answers.{self.fallas_fields['falla_responsable_solucionar_catalog']}.{self.fallas_fields['falla_responsable_solucionar_nombre']}",
                'falla_responsable_solucionar_documento':f"$answers.{self.fallas_fields['falla_responsable_solucionar_catalog']}.{self.fallas_fields['falla_responsable_solucionar_documento']}",
                'falla_comentario_solucion':f"$answers.{self.fallas_fields['falla_comentario_solucion']}",
                'falla_folio_accion_correctiva':f"$answers.{self.fallas_fields['falla_folio_accion_correctiva']}",
                'falla_evidencia_solucion':f"$answers.{self.fallas_fields['falla_evidencia_solucion']}",
                'falla_documento_solucion':f"$answers.{self.fallas_fields['falla_documento_solucion']}",
                # 'falla_fecha_hora_solucion':f"$answers.{self.fallas_fields['falla_fecha_hora_solucion']}",
                'falla_grupo_seguimiento':f"$answers.{self.fallas_fields['falla_grupo_seguimiento']}",
            }},
            {'$sort':{'created_at':-1}},
        ]
        result = self.format_cr_result(self.cr.aggregate(query))
        for r in result:
            if r:
                r['falla_grupo_seguimiento_formated'] = self.format_seguimiento_fallas(r.get('falla_grupo_seguimiento',[]))
                r.pop('falla_grupo_seguimiento', None)
        return result

    def get_list_incidences(self, location, area, prioridades=[], dateFrom="", dateTo="", filterDate="", folio=None):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_INCIDENCIAS,
        }
        if location:
             match_query[f"answers.{self.incidence_fields['ubicacion_incidencia_catalog']}.{self.incidence_fields['ubicacion_incidencia']}"] = location
        if area:
             match_query[f"answers.{self.incidence_fields['area_incidencia_catalog']}.{self.incidence_fields['area_incidencia']}"] = area
        if prioridades:
            match_query[f"answers.{self.incidence_fields['prioridad_incidencia']}"] = {"$in": prioridades}
        if folio:
            match_query.update({"folio":folio})
       
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        zona = user_data.get('timezone','America/Monterrey')

        if filterDate != "range":
            dateFrom, dateTo = self.get_range_dates(filterDate,zona)

            if dateFrom:
                dateFrom = str(dateFrom)
            if dateTo:
                dateTo = str(dateTo)

        if dateFrom and dateTo:
            match_query.update({
                f"answers.{self.incidence_fields['fecha_hora_incidencia']}": {"$gte": dateFrom,"$lte": dateTo},
            })
        elif dateFrom:
            match_query.update({
                f"answers.{self.incidence_fields['fecha_hora_incidencia']}": {"$gte": dateFrom}
            })
        elif dateTo:
            match_query.update({
                f"answers.{self.incidence_fields['fecha_hora_incidencia']}": {"$lte": dateTo}
            })

        query = [
            {'$match': match_query },
            {'$project': {
                'folio': '$folio',
                'reporta_incidencia': f"$answers.{self.incidence_fields['reporta_incidencia_catalog']}.{self.incidence_fields['reporta_incidencia']}",
                'fecha_hora_incidencia':f"$answers.{self.incidence_fields['fecha_hora_incidencia']}",
                'ubicacion_incidencia': f"$answers.{self.incidence_fields['ubicacion_incidencia_catalog']}.{self.incidence_fields['ubicacion_incidencia']}",
                'area_incidencia': f"$answers.{self.incidence_fields['area_incidencia_catalog']}.{self.incidence_fields['area_incidencia']}",
                'incidencia': f"$answers.{self.incidence_fields['incidencia_catalog']}.{self.incidence_fields['incidencia']}",
                'tipo_incidencia': f"$answers.{self.incidence_fields['tipo_incidencia']}",
                'comentario_incidencia': f"$answers.{self.incidence_fields['comentario_incidencia']}",
                'tipo_dano_incidencia': f"$answers.{self.incidence_fields['tipo_dano_incidencia']}",
                'dano_incidencia':f"$answers.{self.incidence_fields['dano_incidencia']}",

                'evidencia_incidencia':f"$answers.{self.incidence_fields['evidencia_incidencia']}",
                'documento_incidencia':f"$answers.{self.incidence_fields['documento_incidencia']}",
                'prioridad_incidencia':f"$answers.{self.incidence_fields['prioridad_incidencia']}",
                'notificacion_incidencia':f"$answers.{self.incidence_fields['notificacion_incidencia']}",
                'total_deposito_incidencia':f"$answers.{self.incidence_fields['total_deposito_incidencia']}",
                'datos_deposito_incidencia':f"$answers.{self.incidence_fields['datos_deposito_incidencia']}",
                
                'tags':f"$answers.{self.incidence_fields['tags']}",
                
                'estatus':f"$answers.{self.incidence_fields['estatus']}",

                'nombre_completo_persona_extraviada':f"$answers.{self.incidence_fields['nombre_completo_persona_extraviada']}",
                'edad':f"$answers.{self.incidence_fields['edad']}",
                'color_piel':f"$answers.{self.incidence_fields['color_piel']}",
                'color_cabello': f"$answers.{self.incidence_fields['color_cabello']}",
                'estatura_aproximada':f"$answers.{self.incidence_fields['estatura_aproximada']}",
                'descripcion_fisica_vestimenta':f"$answers.{self.incidence_fields['descripcion_fisica_vestimenta']}",
                'nombre_completo_responsable': f"$answers.{self.incidence_fields['nombre_completo_responsable']}",
                'parentesco': f"$answers.{self.incidence_fields['parentesco']}",
                'num_doc_identidad': f"$answers.{self.incidence_fields['num_doc_identidad']}",
                'telefono': f"$answers.{self.incidence_fields['telefono']}",
                'info_coincide_con_videos': f"$answers.{self.incidence_fields['info_coincide_con_videos']}",
                'responsable_que_entrega': f"$answers.{self.incidence_fields['responsable_que_entrega']}",
                #'responsable_que_recibe':f"$answers.{self.incidence_fields['responsable_que_recibe']}",

                #Robo de cableado
                'valor_estimado': f"$answers.{self.incidence_fields['valor_estimado']}",
                'pertenencias_sustraidas': f"$answers.{self.incidence_fields['pertenencias_sustraidas']}",
                #Robo de vehiculo
                'placas': f"$answers.{self.incidence_fields['placas']}",
                'tipo': f"$answers.{self.incidence_fields['tipo']}",
                'marca':f"$answers.{self.incidence_fields['marca']}",
                'modelo':f"$answers.{self.incidence_fields['modelo']}",
                'color': f"$answers.{self.incidence_fields['color']}",

                'categoria':f"$answers.{self.incidence_fields['incidencia_catalog']}.{self.incidence_fields['categoria']}",
                'sub_categoria':f"$answers.{self.incidence_fields['incidencia_catalog']}.{self.incidence_fields['sub_categoria']}",
                # NOTA: legacy tiene esta misma proyeccion duplicada bajo la llave 'incidencia'
                # (ver linea ~10176) — Python colapsa el duplicado y solo sobrevive esa, sin
                # generar una llave 'incidente' en el output real. Se omite aqui para igualar
                # byte a byte la respuesta de produccion.

                #Grupos repetitivos
                'personas_involucradas_incidencia':f"$answers.{self.incidence_fields['personas_involucradas_incidencia']}",
                'afectacion_patrimonial_incidencia':f"$answers.{self.incidence_fields['afectacion_patrimonial_incidencia']}",
                'acciones_tomadas_incidencia':f"$answers.{self.incidence_fields['acciones_tomadas_incidencia']}",
                'seguimientos_incidencia':f"$answers.{self.incidence_fields['seguimientos_incidencia']}",
                }
            },
            {'$sort':{'folio':-1}}
        ]
        result = self.format_cr_result(self.cr.aggregate(query))
        result = self.format_cr(result)
        for r in result:
            r['personas_involucradas_incidencia'] = self.format_personas_involucradas(r.get('personas_involucradas_incidencia',[]))
            r['acciones_tomadas_incidencia'] = self.format_acciones(r.get('acciones_tomadas_incidencia',[]))
            r['afectacion_patrimonial_incidencia'] = self.format_afectacion_patrimonial(r.get('afectacion_patrimonial_incidencia',[]))
            r['datos_deposito_incidencia'] = self.format_datos_deposito(r.get('datos_deposito_incidencia',[]))
            r['seguimientos_incidencia'] = self.format_seguimiento_incidencias(r.get('seguimientos_incidencia',[]))
            r['tags'] = self.format_tags_incidencias(r.get('tags',[]))
            r['prioridad_incidencia'] = r.get('prioridad_incidencia',[]).title()
            r['color_piel'] = r.get('color_piel',"").capitalize().replace("_", " ")
            r['estatus'] = r.get('estatus',"").capitalize()
        print("resultados", simplejson.dumps(result, indent=4))
        return result

    def get_list_notes(self, location, area, status=None, limit=10, offset=0, dateFrom="", dateTo=""):
        '''
        Función para obtener las notas, puedes pasarle un area, una ubicacion, un estatus, una fecha desde
        y una fecha hasta
        '''
        response = []
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.ACCESOS_NOTAS,
            f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['location']}":location
        }
        if area and not area == 'todas':
            match_query.update({
                f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['area']}":area
            })
        if status != 'dia':
            match_query.update({f"answers.{self.notes_fields['note_status']}":status})
        if dateFrom and dateTo:
            if dateFrom == dateTo:
                if "T" not in dateFrom:
                    dateFrom += " 00:00:00"
                    dateTo += " 23:59:59"
            else:
                if "T" not in dateFrom:
                    dateFrom += " 00:00:00"
                if "T" not in dateTo:
                    dateTo += " 23:59:59"

            match_query.update({
                f"answers.{self.notes_fields['note_open_date']}": {"$gte": dateFrom, "$lte": dateTo}
            })
        elif dateFrom:
            if "T" not in dateFrom:
                dateFrom += " 00:00:00"
            match_query.update({
                f"answers.{self.notes_fields['note_open_date']}": {"$gte": dateFrom}
            })
        elif dateTo:
            if "T" not in dateTo:
                dateTo += " 23:59:59"
            match_query.update({
                f"answers.{self.notes_fields['note_open_date']}": {"$lte": dateTo}
            })
        query = [
            {'$match': match_query },
            {'$project': {
                "folio":"$folio",
                "created_at": 1,
                "created_by_name": f"$created_by_name",
                "created_by_id": f"$created_by_id",
                "created_by_email": f"$created_by_email",
                "note_status": f"$answers.{self.notes_fields['note_status']}",
                "note_open_date": f"$answers.{self.notes_fields['note_open_date']}",
                "note_close_date": f"$answers.{self.notes_fields['note_close_date']}",
                "note_booth": f"$answers.{self.notes_fields['note_catalog_booth']}.{self.notes_fields['note_booth']}",
                "note_guard": f"$answers.{self.notes_fields['note_catalog_guard']}.{self.notes_fields['note_guard']}",
                "note_guard_close": f"$answers.{self.notes_fields['note_catalog_guard_close']}.{self.notes_fields['note_guard_close']}",
                "note": f"$answers.{self.notes_fields['note']}",
                "note_file": f"$answers.{self.notes_fields['note_file']}",
                "note_pic": f"$answers.{self.notes_fields['note_pic']}",
                "note_comments": f"$answers.{self.notes_fields['note_comments_group']}",
            }},
            {'$sort':{'created_at':-1}},
        ]
        
        query.append({'$skip': offset})
        query.append({'$limit': limit})
        
        records = self.format_cr(self.cr.aggregate(query))

        count_query = [
            {'$match': match_query},
            {'$count': 'total'}
        ]

        count_result = self.format_cr(self.cr.aggregate(count_query))
        total_count = count_result[0]['total'] if count_result else 0
        total_pages = ceil(total_count / limit) if limit else 1
        current_page = (offset // limit) + 1 if limit else 1

        notes = {
            'records': records,
            'total_records': total_count,
            'total_pages': total_pages,
            'actual_page': current_page
        }

        return notes

    def get_lista_pase(self, location, status='activo', inActive=""):
        status_value = self.pase_entrada_fields.get('status_pase', '')
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.PASE_ENTRADA,
        }


        if inActive =="true":
              match_query[f"answers.{self.pase_entrada_fields['status_pase']}"] =  {"$ne": "activo"}
        else:
             match_query[f"answers.{self.pase_entrada_fields['status_pase']}"] = status

        proyect_fields = {'_id':1,
            'folio': f"$folio",
            'ubicacion': f"$answers.{self.mf['grupo_ubicaciones_pase']}.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}",
            'nombre': {"$ifNull":[
                f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['nombre_visita']}",
                f"$answers.{self.mf['nombre_pase']}"]},
            'estatus':f"$answers.{self.pase_entrada_fields['status_pase']}",
            'empresa': {"$ifNull":[
                 f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['empresa']}",
                 f"$answers.{self.pase_entrada_fields['walkin_empresa']}"]},
            'foto': {"$ifNull":[
                f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['foto']}",
                f"$answers.{self.pase_entrada_fields['walkin_fotografia']}"]},
            }
        query = [
            {'$match': match_query },
            {'$unwind': f"$answers.{self.mf['grupo_ubicaciones_pase']}"},
            {'$match': {f"answers.{self.mf['grupo_ubicaciones_pase']}.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}":location}},
            {'$project': proyect_fields},
            {'$sort':{'_id':-1}},
        ]
        records = self.format_cr(self.cr.aggregate(query))
        for rec in records:
            rec['qr_code'] = rec['_id']
            rec['empresa'] = self.unlist(rec.get('empresa',[]))
        return  records

    def get_list_last_user_move(self, qr, limit=100, status=False):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_ACCESOS,
            f"answers.{self.mf['codigo_qr']}":qr,
        }

        if status == 'in':
            status = 'entrada'
        elif status == 'out':
            status = 'salida'
        elif status == 'deny':
            status = 'acceso_denegado'
        if status:
            match_query.update({
                f"answers.{self.bitacora_fields['status_visita']}": status
                })
        res = self.cr.find(
            match_query, 
            {
                'pase_status': f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.pase_entrada_fields['status_pase']}",
                'comentarios': f"$answers.{self.bitacora_fields['grupo_comentario']}",
                'checkin_date': f"$answers.{self.bitacora_fields['fecha_entrada']}",
                'checkout_date': f"$answers.{self.bitacora_fields['fecha_salida']}",
                'duration':f"$answers.{self.mf['duracion']}",
                'equipos':f"$answers.{self.mf['grupo_equipos']}",
                'equipos':f"$answers.{self.mf['grupo_equipos']}",
                'folio':'$folio', 
                'fecha':f"$answers.{self.mf['fecha_entrada']}",
                'status_visita': f"$answers.{self.bitacora_fields['status_visita']}",
                'gafete_id': f"$answers.{self.GAFETES_CAT_OBJ_ID}.{self.gafetes_fields['gafete_id']}",
                'locker_id': f"$answers.{self.LOCKERS_CAT_OBJ_ID}.{self.mf['locker_id']}",
                'visita_a':f"$answers.{self.bitacora_fields['visita_a']}",
                #Vehiculos
                'vehiculos':f"$answers.{self.mf['grupo_vehiculos']}",
            }
            ).sort('updated_at', -1).limit(limit)

        result = self.format_cr(res)
        for r in result:
            r['vehiculos'] = self.format_vehiculos(r.get('vehiculos',[]))
            # r['equipos'] = self.format_equipos(r.get('equipos',[]))
            r['comentarios'] = self.format_comentarios(r.get('comentarios',[]))
            r['visita_a']= self.format_visita(r.get('visita_a',[]))
            # r['status_pase'] = r.get(self.pase_entrada_fields['status_pase'],'')
            # if r.get('comentario'):
            #     coment=[]
            #     for c in r['comentario']:
            #         row = {
            #             'comentario':c.get(self.bitacora_fields['comentario']),
            #             'tipo_comentario':c.get(self.bitacora_fields['tipo_comentario'])
            #         }
            #     coment.append(row)
            #     r['comentario'] = coment
            equipos = r.get('equipos', [])
            if equipos:  # Verifica si la lista de equipos no está vacía
                r['equipos'] = self.format_equipos(equipos)
            else:
                r['equipos'] = []  # O alguna otra lógica que desees aplicar si está vacía
                match_query2 = {
                    "deleted_at":{"$exists":False},
                    "form_id": self.PASE_ENTRADA,
                    f"answers.{self.mf['codigo_qr']}":qr,
                }
                res2= self.cr.find(
                match_query2, 
                {
                    'equipos':f"$answers.{self.mf['grupo_equipos']}",
                }).sort('updated_at', -1).limit(limit)
                result2 = self.format_cr(res2)
                for r2 in result2:
                    r['equipos'] = self.format_equipos(r2.get('equipos',[]))
        return result

    def get_pefiles_walkin(self, location):
        query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CONF_PERFILES,
            f"answers.{self.PERFILES_OBJ_ID}.{self.mf['walkin']}":'Si'
        }
        format_filed = {
            'perfil': f"$answers.{self.PERFILES_OBJ_ID}.{self.mf['nombre_perfil']}",
            'ubicacion': f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}"
            } 
        res = []
        for r in self.cr.find(query,format_filed):
            if r.get('perfil'):
                if location:
                    if r.get('ubicacion'): 
                        if r['ubicacion'] == location:
                            if r['perfil'] not in res:
                                res.append(r['perfil'])
                    else:
                        if r['perfil'] not in res:
                            res.append(r['perfil'])
                else:
                    if r['perfil'] not in res:
                        res.append(r['perfil'])
        return res
    
    def get_my_pases(self, tab_status="", limit=10, skip=0, search_name=None, location=None, dynamic_filters=[], dateFrom="", dateTo="", filterDate="", locations=[]):
        employee = self.Employee.get_employee_data(user_id=self.user.get('user_id'), get_one=True)
        fecha_hoy = datetime.now(pytz.timezone(self.user['timezone'])).replace(microsecond=0).astimezone(pytz.utc).replace(tzinfo=None)
        fecha_local = datetime.now(pytz.timezone(self.user['timezone'])).replace(microsecond=0)
        fecha_utc = fecha_local.astimezone(pytz.utc).replace(tzinfo=None, microsecond=0)

        fecha_hoy_formateada = fecha_hoy.strftime('%Y-%m-%d %H:%M:%S')
        match_query = {
            'form_id':self.PASE_ENTRADA,
            'deleted_at':{'$exists':False},
                '$or': [
            {
                f"answers.{self.pase_entrada_fields['visita_a']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}": employee.get('worker_name')
            },
            {
                'created_by_id': self.user.get('user_id')
            }
        ]
        }
        if not tab_status:
            tab_status = ""
        if tab_status.strip().lower() == "favoritos":
            match_query.update({f"answers.{self.pase_entrada_fields['favoritos']}":'si'})
        elif tab_status.strip().lower() == "activos":
            match_query.update({f"answers.{self.pase_entrada_fields['status_pase']}":'activo'})
        elif tab_status.strip().lower() == "vencidos":
            match_query.update({f"answers.{self.pase_entrada_fields['status_pase']}":'vencido'})
        elif tab_status.strip().lower() == "por_autorizar":
            match_query.update({f"answers.{self.pase_entrada_fields['status_pase']}":'por_autorizar'})
        elif tab_status.strip().lower() == "en_proceso":
            match_query.update({f"answers.{self.pase_entrada_fields['status_pase']}":'proceso'})

        if search_name:
            match_query.update({
                f"$or": [
                    {f"answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['nombre_visita']}": {"$regex": search_name, "$options": "i"}},
                    {f"answers.{self.mf['nombre_pase']}": {"$regex": search_name, "$options": "i"}}
                ]
            })
        if location:
            match_query[f"answers.{self.mf['grupo_ubicaciones_pase']}.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}"] = location
        if locations:
            match_query[f"answers.{self.mf['grupo_ubicaciones_pase']}.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}"] = {"$in": locations}
        if dynamic_filters:
            for item in dynamic_filters:
                if item.get('key') == 'status':
                    match_query[f"answers.{self.pase_entrada_fields['status_pase']}"] = {"$in": item.get('value')}
                elif item.get('key') == 'perfil_visita':
                    match_query[f"answers.{self.CONFIG_PERFILES_OBJ_ID}.{self.mf['nombre_perfil']}"] = {"$in": item.get('value')}
                elif item.get('key') == 'visita_a':
                    match_query[f"answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}"] = {"$in": item.get('value')}
                else:
                    continue

        zona = self.user.get('timezone','America/Monterrey')
        if filterDate != "range":
            dateFrom, dateTo = self.get_range_dates(filterDate, zona)
            if dateFrom:
                dateFrom = str(dateFrom)
            if dateTo:
                dateTo = str(dateTo)

        if dateFrom and dateTo:
           match_query.update({
                f"answers.{self.mf['fecha_desde_visita']}": {"$gte": dateFrom, "$lte": dateTo},
            })
        elif dateFrom:
            match_query.update({
                f"answers.{self.mf['fecha_desde_visita']}": {"$gte": dateFrom}
            })
        elif dateTo:
            match_query.update({
                f"answers.{self.mf['fecha_desde_visita']}": {"$lte": dateTo}
            })

        # Conteo total de registros
        count_query = [
            {"$match": match_query},
            {"$count": "total"}
        ]
        count_result = self.format_cr(self.cr.aggregate(count_query))
        total_count = count_result[0]['total'] if count_result else 0
        current_page = (skip // limit) + 1
        total_pages = ceil(total_count / limit) if limit else 1

        query = [ 
            {"$match":match_query},
            {'$project':
                {
                    '_id': 1,
                    'folio': "$folio",
                    'favoritos':f"$answers.{self.pase_entrada_fields['favoritos']}",
                    'ubicacion': f"$answers.{self.mf['grupo_ubicaciones_pase']}.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}",
                    # 'ubicacion': f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
                    'nombre': {"$ifNull":[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['nombre_visita']}",
                        f"$answers.{self.mf['nombre_pase']}"]},
                    'estatus': f"$answers.{self.pase_entrada_fields['status_pase']}",
                    'empresa': {"$ifNull":[
                         f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['empresa']}",
                         f"$answers.{self.mf['empresa_pase']}"]},
                    'email':  {"$ifNull":[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['email_vista']}",
                        f"$answers.{self.mf['email_pase']}"]},
                    'telefono': {"$ifNull":[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['telefono']}",
                        f"$answers.{self.mf['telefono_pase']}"]},
                    'fecha_desde_visita': f"$answers.{self.mf['fecha_desde_visita']}",
                    'fecha_desde_hasta':{'$ifNull':[
                        f"$answers.{self.mf['fecha_desde_hasta']}",
                        f"$answers.{self.mf['fecha_desde_visita']}"]
                        },
                    'identificacion': {'$ifNull':[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['identificacion']}",
                        f"$answers.{self.pase_entrada_fields['walkin_identificacion']}"]},
                    'foto': {'$ifNull':[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['foto']}",
                        f"$answers.{self.pase_entrada_fields['walkin_fotografia']}"]},
                    'visita_a_nombre':
                        f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}",
                    'visita_a_puesto': 
                        f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['puesto_empleado']}",
                    'visita_a_departamento':
                        f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['departamento_empleado']}",
                    'visita_a_user_id':
                        f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['user_id_empleado']}",
                    'visita_a_email':
                        f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['email']}",
                    'motivo_visita':f"$answers.{self.CONFIG_PERFILES_OBJ_ID}.{self.mf['motivo']}",
                    'tipo_de_pase':f"$answers.{self.pase_entrada_fields['perfil_pase']}",
                    'tema_cita':f"$answers.{self.pase_entrada_fields['tema_cita']}",
                    'descripcion':f"$answers.{self.pase_entrada_fields['descripcion']}",
                    'tipo_visita': f"$answers.{self.pase_entrada_fields['tipo_visita']}",
                    'limite_de_acceso': f"$answers.{self.mf['config_limitar_acceso']}",
                    'config_dia_de_acceso': f"$answers.{self.mf['config_dia_de_acceso']}",
                    'identificacion': {'$ifNull':[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['identificacion']}",
                        f"$answers.{self.pase_entrada_fields['walkin_identificacion']}"]},
                    'limitado_a_dias':f"$answers.{self.mf['config_dias_acceso']}",
                    'perfil_pase':f"$answers.{self.CONFIG_PERFILES_OBJ_ID}",
                    'tipo_de_comentario': f"$answers.{self.mf['tipo_de_comentario']}",
                    'tipo_fechas_pase': f"$answers.{self.mf['tipo_visita_pase']}",
                    'enviar_correo_pre_registro': f"$answers.{self.pase_entrada_fields['enviar_correo_pre_registro']}",
                    'enviar_correo': f"$answers.{self.pase_entrada_fields['enviar_correo']}",
                    'grupo_areas_acceso': f"$answers.{self.mf['grupo_areas_acceso']}",
                    'grupo_equipos': f"$answers.{self.mf['grupo_equipos']}",
                    'grupo_vehiculos': f"$answers.{self.mf['grupo_vehiculos']}",
                    'grupo_instrucciones_pase': f"$answers.{self.mf['grupo_instrucciones_pase']}",
                    'comentario_area_pase':f"$answers.{self.mf['grupo_areas_acceso']}.{self.pase_entrada_fields['commentario_area']}",
                    'archivo_invitacion': f"$answers.{self.mf['archivo_invitacion']}",
                    'codigo_qr': f"$answers.{self.mf['codigo_qr']}",
                    'qr_pase': f"$answers.{self.mf['qr_pase']}",
                    'link':f"$answers.{self.pase_entrada_fields['link']}",
                    'perfil_pase': f"$answers.{self.mf['nombre_perfil']}",
                    'status_pase': f"$answers.{self.pase_entrada_fields['status_pase']}",
                    'pdf_to_img': f"$answers.{self.pase_entrada_fields['pdf_to_img']}",
                    'autorizado_por':f"$answers.{self.pase_entrada_fields['autorizado_por']}",
                    'acompanantes_grupo':f"$answers.{self.pase_entrada_fields['acompanantes_grupo']}",
                    'acompanantes':f"$answers.{self.pase_entrada_fields['acompanantes']}",
                    'habilitar_vehiculo':f"$answers.{self.pase_entrada_fields['habilitar_vehiculo']}"
                }
            },
            {'$sort':{'_id':-1}},
        ]
        query.append({'$skip': skip})
        query.append({'$limit': limit})
        records = self.format_cr(self.cr.aggregate(query))
        self._hidratar_acompanantes(records)
        for x in records:
            qr_code = x.get('_id')
            total_entradas = self.get_count_ingresos(qr_code)
            if total_entradas:
                x['total_entradas'] = total_entradas.get('total_records')
            else:
                x['total_entradas'] = 0
            visita_a =[]
            v = x.pop('visita_a_nombre') if x.get('visita_a_nombre') else []
            d = x.get('visita_a_departamento',[])
            p = x.get('visita_a_puesto',[])
            e =  x.get('visita_a_user_id',[])
            u =  x.get('visita_a_email',[])

            for idx, nombre in enumerate(v):
                emp = {'nombre':nombre}
                emp['departamento'] = d[idx] if idx < len(d) and d[idx] else [""]
                emp['puesto'] = p[idx] if idx < len(p) and p[idx] else [""]
                emp['user_id'] = e[idx] if idx < len(e) and e[idx] else [""]
                emp['email'] = u[idx] if idx < len(u) and u[idx] else [""]
                visita_a.append(emp)
            if x['tipo_de_pase'] == 'Visita General' or x['tipo_de_pase'] == 'visita general':
                x['visita_a'] = visita_a
                x['favoritos'] = x.get('favoritos', [""]) if x.get('favoritos') else ""
                x['motivo_visita'] = x.get('motivo_visita', [""]) if x.get('motivo_visita') else ""
                x['email'] = x.get('email', [""]) if x.get('email') else ""
                x['empresa'] = x.get('empresa', [""]) if x.get('empresa') else ""
                x['telefono'] = x.get('telefono', [""]) if x.get('telefono') else ""
                # x['pdf'] = self.lkf_api.get_pdf_record(x['_id'], template_id = 447, name_pdf='Pase de Entrada', send_url=True)
            else:
                
                x['visita_a'] = visita_a
                x['favoritos'] = x.get('favoritos') or ""
                x['motivo_visita'] =x.get('motivo_visita') or ""
                x['email']= x.get('email') or ""
                x['empresa']= x.get('empresa') or ""
                x['telefono']= x.get('telefono') or ""
                # x['pdf'] = self.lkf_api.get_pdf_record(x[' # for idx, dic in enumerate(x['grupo_areas_acceso']):
            # x['comentario_area_pase']=x.pop('comentario_area_pase',[])
           

                # for key in list(item.keys()):
                #     if key in id_to_name_mapping:
                #         # Reemplaza el id hexadecimal por su nombre en el diccionario
                #         item[self.pase_entrada_fields['commentario_area']] = item.pop(key)

            for visita in x.get('visita_a', []):
                visita['departamento'] = visita['departamento'][0] if isinstance(visita.get('departamento'), list) and visita.get('departamento') else visita.get('departamento', "")
                visita['puesto'] = visita['puesto'][0] if isinstance(visita.get('puesto'), list) and visita.get('puesto') else visita.get('puesto', "")
                visita['user_id'] = visita['user_id'][0] if isinstance(visita.get('user_id'), list) and visita.get('user_id') else visita.get('user_id', "")
                visita['email'] = visita['email'][0] if isinstance(visita.get('email'), list) and visita.get('email') else visita.get('email', "")

            visitas = x.get('visita_a', [])
            x['status_pase'] = x.get('estatus', "")
            x['autorizado_por'] = x.get('autorizado_por', "")
            x['grupo_areas_acceso'] = self._labels_list(x.pop('grupo_areas_acceso',[]), self.mf)
            x['grupo_instrucciones_pase'] = self._labels_list(x.pop('grupo_instrucciones_pase',[]), self.mf)
            x['habilitar_vehiculo'] = x.get('habilitar_vehiculo', "")

            x['grupo_vehiculos'] = self.format_vehiculos_simple(x.pop('grupo_vehiculos',[]))
            x['grupo_equipos'] = self.format_equipos_simple(x.pop('grupo_equipos',[]))
            x['comentarios'] = x['grupo_instrucciones_pase']

            comentarios = []
            for item in x.pop('comentarios', []):
                comentario_pase = item.get('comentario_pase', '') 
                tipo_comentario = item.get('tipo_de_comentario', '')
                comentarios.append({
                    'comentario_pase': comentario_pase,
                    'tipo_comentario': tipo_comentario
                })
            x['comentarios'] = comentarios

            x.pop('visita_a_nombre', None)
            x.pop('visita_a_departamento', None)
            x.pop('visita_a_puesto', None)
            x.pop('visita_a_user_id', None)
            x.pop('visita_a_email', None)
        # print("data", simplejson.dumps(records, indent=4))
        return  {
            "records": records,
            "total_records": total_count,
            "total_pages": total_pages,
            "actual_page": current_page,
            "records_on_page": len(records)
        }

    def get_pdf(self, qr_code, template_id=None, name_pdf=None):
        return self.lkf_api.get_pdf_record(qr_code, template_id = template_id, name_pdf =name_pdf, send_url=True)

    def get_pass_img(self, qr_code):
        answers = {}
        pdf_to_img = self.update_pass_img(qr_code)
        if pdf_to_img:
            answers.update({self.pase_entrada_fields['pdf_to_img']: pdf_to_img})
            response = self.lkf_api.patch_multi_record( answers = answers, form_id=self.PASE_ENTRADA, record_id=[qr_code])
            if response.get('status_code') in [200, 201, 202]:
                url = self.unlist(pdf_to_img).get('file_url') if len(pdf_to_img) > 0 else ''
                return url
            else:
                self.LKFException({'title': 'Error', 'msg': 'Hubo un error al actualizar los registros.'})
        return False

    def get_pass_custom(self,qr_code):
        pass_selected= self.get_detail_access_pass(qr_code=qr_code)
        answers={}
        for key, value in pass_selected.items():
            if key == 'nombre' or \
               key == 'email' or \
               key == 'telefono' or \
               key == 'visita_a' or \
               key == 'ubicacion' or \
               key == 'fecha_de_expedicion' or \
               key == 'fecha_de_caducidad' or \
               key == "qr_pase" or \
               key == "pdf_to_img" or \
               key == "_id" or \
               key == "estatus" or \
               key == "foto" or \
               key == "identificacion" or \
               key == "grupo_equipos" or \
               key == "grupo_vehiculos" or \
               key == "google_wallet_pass_url" or \
               key == "limite_de_acceso" or \
               key == "empresa" or \
               key == "ubicaciones_geolocation" or \
               key == "habilitar_vehiculo" or \
               key == "acompanantes" or \
               key == "acompanantes_grupo" or \
               key == "url_padre" or \
               key == "estatus_pase_padre" or \
               key == "link_padre" or \
               key == "google_wallet_pass_url":
                answers[key] = value
        answers['folio']= pass_selected.get("folio")
        return answers

    def get_paquetes(self, location= "", area="", status="", dateFrom="", dateTo="", filterDate=""):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.PAQUETERIA,
        }
        if location:
             match_query[f"answers.{self.paquetes_fields['ubicacion_paqueteria']}"] = location
        if area:
             match_query[f"answers.{self.paquetes_fields['area_paqueteria']}"] = area
        if status:
             match_query[f"answers.{self.paquetes_fields['estatus_paqueteria']}"] = status

        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        zona = user_data.get('timezone','America/Monterrey')

        if filterDate != "range":
            dateFrom, dateTo = self.get_range_dates(filterDate,zona)

            if dateFrom:
                dateFrom = str(dateFrom)
            if dateTo:
                dateTo = str(dateTo)
        if dateFrom and dateTo:
            match_query.update({
                f"answers.{self.paquetes_fields['fecha_recibido_paqueteria']}": {"$gte": dateFrom, "$lte": dateTo},
            })
        elif dateFrom:
            match_query.update({
                f"answers.{self.paquetes_fields['fecha_recibido_paqueteria']}": {"$gte": dateFrom}
            })
        elif dateTo:
           match_query.update({
                f"answers.{self.paquetes_fields['fecha_recibido_paqueteria']}": {"$lte": dateTo}
            })

        query = [
            {'$match': match_query },
            {'$project': {
                "folio":"$folio",
                "_id":"$_id",
                'created_at':'$created_at',
                'ubicacion_paqueteria':f"$answers.{self.paquetes_fields['ubicacion_paqueteria']}",
                'area_paqueteria': f"$answers.{self.paquetes_fields['area_paqueteria']}",
                'fotografia_paqueteria':f"$answers.{self.paquetes_fields['fotografia_paqueteria']}",
                'descripcion_paqueteria':f"$answers.{self.paquetes_fields['descripcion_paqueteria']}",
                'quien_recibe_paqueteria':f"$answers.{self.paquetes_fields['quien_recibe_cat']}.{self.paquetes_fields['quien_recibe_paqueteria']}",
                'guardado_en_paqueteria': f"$answers.{self.paquetes_fields['guardado_en_paqueteria']}",
                'fecha_recibido_paqueteria': f"$answers.{self.paquetes_fields['fecha_recibido_paqueteria']}",
                'fecha_entregado_paqueteria': f"$answers.{self.paquetes_fields['fecha_entregado_paqueteria']}",
                'estatus_paqueteria': f"$answers.{self.paquetes_fields['estatus_paqueteria']}",
                'entregado_a_paqueteria': f"$answers.{self.paquetes_fields['entregado_a_paqueteria']}",
                'proveedor': f"$answers.{self.paquetes_fields['proveedor_cat']}.{self.paquetes_fields['proveedor']}",
                'quien_recibe_otro': f"$answers.{self.paquetes_fields['quien_recibe_otro']}",
            }},
            {'$sort':{'created_at':-1}},
        ]
        if not filterDate:
            query.append(
                {"$limit":25}
            )
        pr= self.format_cr_result(self.cr.aggregate(query))
        for x in pr:
            status = x.get('estatus_paqueteria', [])
            x['estatus_paqueteria'] = status.pop() if status else ""
        return pr
    
    def get_range_dates(self, period, zona):
        now = arrow.now(zona) 
        start_date = None
        end_date = None

        if period == 'today':
            start_date = now.floor('day')
            end_date = now.floor('day').shift(days=+1).shift(seconds=-1)
        elif period == 'yesterday':
            now = now.shift(days=-1)
            start_date = now.floor('day')
            end_date = now.floor('day').shift(days=+1).shift(seconds=-1)
        elif period == 'this_week':
            start_date = now.floor('week')
            end_date = now.ceil('week').shift(days=+1).shift(seconds=-1)
        elif period == 'last_week':
            start_date = now.shift(weeks=-1).floor('week')
            end_date = start_date.ceil('week').shift(seconds=-1)
        elif period == 'last_fifteen_days':
            start_date = now.shift(days=-15).floor('day')
            end_date = now.shift(days=+1).floor('day').shift(seconds=-1)
        elif period == 'this_month':
            start_date = now.floor('month')  # El primer día del mes
            end_date = now.ceil('month').shift(days=+1).shift(seconds=-1)
        elif period == 'last_month':
            start_date = now.replace(day=1, month=now.month-1, year=now.year).floor('day')
            end_date = start_date.shift(months=+1).shift(seconds=-1)
        elif period == 'this_year':
            start_date = now.replace(month=1, day=1, year=now.year).floor('day')
            end_date = now.shift(days=+1).floor('day').shift(seconds=-1)
        elif period == 'last_year':
            start_date = now.replace(month=1, day=1, year=now.year-1).floor('day')
            end_date = now.replace(month=12, day=31, year=now.year-1).shift(seconds=-1)

        if isinstance(start_date, arrow.Arrow):
            start_date = start_date.datetime.replace(tzinfo=None)

        if isinstance(end_date, arrow.Arrow):
            end_date = end_date.datetime.replace(tzinfo=None)

        return start_date, end_date

    def get_user_booths_availability(self, turn_areas=True):
        '''
        Regresa las castas configurados por usuario y su stats
        TODO, se puede mejorar la parte de la obtencion de la direccion para hacerlo en 1 sola peticion
        '''
        default_booth , user_booths = self.Employee.get_user_booth(search_default=False, turn_areas=turn_areas)
        user_booths.insert(0, default_booth)
        user_booths_with_area = []
        for booth in user_booths:
            booth_area = booth.get('area')
            if booth_area:
                location = booth.get('location')
                booth_status = self.get_booth_status(booth_area, location)
                booth['status'] = booth_status.get('status', 'Disponible')
                booth_address = self.Location.get_area_address(location, booth_area)
                booth_address.pop('_id')
                booth_address.pop('folio')
                booth.update(booth_address)
                user_booths_with_area.append(booth)
        return user_booths_with_area


    def get_user_contacts(self):
        user_id = self.user['user_id']
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.PASE_ENTRADA,
            "created_by_id": user_id
            }

        query = [
            {'$match': match_query },
            {'$group':{
                '_id':{
                    'nombre':f"$answers.{self.pase_entrada_fields['walkin_nombre']}"
                    },
                'email': {'$last':f"$answers.{self.pase_entrada_fields['walkin_email']}"},
                'empresa': {'$last':f"$answers.{self.pase_entrada_fields['walkin_empresa']}"},
                'fotografia': {'$last':f"$answers.{self.pase_entrada_fields['walkin_fotografia']}"},
                'identificacion': {'$last':f"$answers.{self.pase_entrada_fields['walkin_identificacion']}"},
                'telefono': {'$last':f"$answers.{self.pase_entrada_fields['walkin_telefono']}"},
                }
            },
            {"$project":{
                "nombre":"$_id.nombre",
                "email":"$email",
                "empresa":"$empresa",
                "fotografia":"$fotografia",
                "identificacion":"$identificacion",
                "telefono":"$telefono",
            }},
            {'$sort':{'nombre':-1}},
            ]
        return self.format_cr(self.cr.aggregate(query))        
    
    def check_in_aux_guard(self):
        match_query = {
            "deleted_at": {"$exists": False},
            "form_id": self.CHECKIN_CASETAS,
        }
        query = [
            {'$match': match_query},
            {'$unwind': f"$answers.{self.f['guard_group']}"},
            {'$project': {
                '_id': 1,
                'folio': "$folio",
                'created_at': "$created_at",
                'name': f"$answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['worker_name_jefes']}",
                'user_id': {"$first": f"$answers.{self.f['guard_group']}.{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['user_id_jefes']}"},
                'location': f"$answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['ubicacion']}",
                'area': f"$answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_area']}",
                'checkin_date': f"$answers.{self.f['guard_group']}.{self.f['checkin_date']}",
                'checkout_date': f"$answers.{self.f['guard_group']}.{self.f['checkout_date']}",
                'checkin_status': f"$answers.{self.f['guard_group']}.{self.f['checkin_status']}",
                'checkin_position': f"$answers.{self.f['guard_group']}.{self.f['checkin_position']}",
            }},
            {'$match': {'user_id': {'$ne': None}}},
            {'$sort': {'updated_at': -1}},
            {'$group': {
                '_id': {'user_id': '$user_id'},
                'name': {'$last': '$name'},
                'location': {'$last': '$location'},
                'area': {'$last': '$area'},
                'checkin_date': {'$last': '$checkin_date'},
                'checkout_date': {'$last': '$checkout_date'},
                'checkin_status': {'$last': '$checkin_status'},
                'checkin_position': {'$last': '$checkin_position'},
            }},
            {'$project': {
                '_id': 0,
                'user_id': '$_id.user_id',
                'name': '$name',
                'location': '$location',
                'area': '$area',
                'checkin_date': '$checkin_date',
                'checkout_date': '$checkout_date',
                'checkin_status': {'$cond': [{'$eq': ['$checkin_status', 'entrada']}, 'in', 'out']},
                'checkin_position': '$checkin_position',
            }},
        ]
        data = self.format_cr(self.cr.aggregate(query))
        res = {}
        for rec in data:
            status = 'in' if rec.get('checkin_status') in ['in', 'entrada'] else 'out'
            user_id = rec.get('user_id') or 0
            res[int(user_id)] = {
                'status': status,
                'name': rec.get('name'),
                'user_id': rec.get('user_id'),
                'location': rec.get('location'),
                'area': rec.get('area'),
                'checkin_date': rec.get('checkin_date'),
                'checkout_date': rec.get('checkout_date'),
                'checkin_position': rec.get('checkin_position')
            }
        return res

    @reload_user
    def get_shift_data(self, booth_location=None, booth_area=None, search_default=True, headers=None):
        """
        Obtiene informacion del turno del usuario logeado
        """
        load_shift_json = { }
        guard = None
        username = self.user.get('username')
        user_id = self.user.get('user_id')

        #! Se obtiene la informacion del usuario, si esta dentro o fuera de turno.
        this_user = self.get_employee_checkin_status_by_id(user_id, booth_location, booth_area)
        if not this_user:
            this_user = self.Employee.get_employee_data(user_id=user_id, get_one=True)
            this_user['name'] = this_user.get('worker_name','')

        user_booths = []
        guards_positions = self.config_get_guards_positions()
        if not guards_positions:
            self.LKFException({"status_code":400, "msg":'No Existen puestos de guardias configurados.'})

        check_aux_guard = self.check_in_aux_guard()
        if this_user and this_user.get('status') == 'out':
            #! Si el usuario esta fuera de turno, se verifica si se encuentra como guardia de apoyo para obtener la informacion del usuario.
            for user_id_aux, each_user in check_aux_guard.items():
                if user_id_aux == user_id:
                    this_user = each_user
                    this_user['status'] = 'in' if each_user.get('status') == 'in' else 'out'
                    this_user['location'] = each_user.get('location')
                    this_user['area'] = each_user.get('area')
                    this_user['checkin_date'] = each_user.get('checkin_date')
                    this_user['checkout_date'] = each_user.get('checkout_date')
                    this_user['checkin_position'] = each_user.get('checkin_position')

        if this_user and this_user.get('status') == 'in':
            #! Si el usuario esta dentro de turno, se obtienen los guardias de apoyo registrados con el.
            location_employees = {self.chife_guard:{},self.support_guard:[]}
            booth_area = this_user['area']
            booth_location = this_user['location']
            for u_id, each_user in check_aux_guard.items():
                if u_id == user_id:
                    guard = each_user
                if each_user.get('status') == 'in' \
                    and each_user.get('location') == booth_location \
                    and each_user.get('area') == booth_area \
                    and each_user.get('user_id') != user_id:
                    location_employees[self.support_guard].append(each_user)
        else:
            #! Si el usuario esta fuera de turno, se obtienen los guardias disponibles.
            default_booth , user_booths = self.Employee.get_user_booth(search_default=False)
            if not booth_location:
                booth_area = default_booth.get('area')
            if not booth_location:
                booth_location = default_booth.get('location')
            if not default_booth:
                return self.LKFException({"status_code":400, "msg":'No booth found or configure for user'})
            location_employees = self.get_booths_guards(booth_location, booth_area, solo_disponibles=True)
            guard = self.get_user_guards(location_employees=location_employees)
            if not guard:
                #! Si el usuario no esta configurado como guardia se agrega su informacion general.
                common_user = {
                    "user_id": self.unlist(this_user.get('usuario_id')),
                    "name": this_user.get('name'),
                    "location": booth_location,
                    "area": booth_area,
                    "config_exception": {
                        "title": "Configuracion",
                        "msg": "El usuario no esta configurado correctamente, faltan configuraciones para Turnos."
                    }
                }
                load_shift_json["guard"] = common_user
                return load_shift_json
        location_employees = self.set_employee_pic(location_employees)
        support_guards = location_employees.get('guardia_de_apoyo', [])
        for idx, guard_item in enumerate(support_guards):
            if guard_item.get('user_id') == user_id:
                support_guards.pop(idx)
                break
        location_employees['guardia_de_apoyo'] = support_guards
        booth_address = self.Location.get_area_address(booth_location, booth_area)

        #! Si el último checkin está cerrado pero existe uno huérfano abierto,
        #! lo cerramos con la hora de cierre del registro más reciente.
        open_statuses = ['entrada', 'apertura', 'disponible', 'abierta']
        last_checkin = self.get_last_checkin(booth_location, booth_area)
        if last_checkin.get('checkin_type') not in open_statuses:
            orphaned = self.get_open_checkin(booth_location, booth_area)
            if orphaned:
                self.close_orphaned_checkin(orphaned, last_checkin)

        notes = self.get_list_notes(booth_location, booth_area, status='abierto')
        load_shift_json["location"] = {
            "name":  booth_location,
            "area": booth_area,
            "city": booth_address.get('city'),
            "state": booth_address.get('state'),
            "address": booth_address.get('address'),
            }
        load_shift_json["booth_stats"] = self.get_page_stats( booth_area, booth_location, "Turnos")
        load_shift_json["booth_status"] = self.get_booth_status(booth_area, booth_location)
        load_shift_json["support_guards"] = location_employees.get(self.support_guard, "")
        load_shift_json["guard"] = self.update_guard_status(guard, this_user)
        load_shift_json["notes"] = notes
        load_shift_json["user_booths"] = user_booths
        load_shift_json["booth_config"] = self.get_booth_config(booth_location)
        return load_shift_json

    def get_user_last_checkin(self, user_id=False):
        if not user_id:
            user_id = self.user.get('user_id')
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CHECKIN_CASETAS,
            "created_by_id": user_id
            }
        query = [
            {'$match': match_query },
            {'$project': self.proyect_format(self.checkin_fields)},
            {'$sort':{'updated_at':-1}},
            {'$limit':1}
            ]
        return self.format_cr_result(self.cr.aggregate(query), get_one=True)

    def get_user_guards(self, location_employees=[]):
        location_guards = []
        for clave in ["guardia_de_apoyo", "guardia_lider"]:
            if location_employees.get(clave):
                for usuario in location_employees[clave]:
                    if usuario.get("user_id") == self.user.get('user_id'):
                        location_guards = location_employees[clave]

        location_employees = location_guards

        for employee in location_employees:
            if employee.get('user_id', 0) == self.user.get('user_id'):
                    return employee
        self.LKFException(f"El usuario con id {self.user['id']}, no se ecuentra configurado como guardia")

    def get_guards_booths(self, location, area):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CHECKIN_CASETAS,
            f"answers.{self.mf['catalog_guard']}.{self.mf['ubicacion']}":location,
            f"answers.{self.mf['catalog_guard']}.{self.mf['nombre_area']}":area,
            f"answers.{self.checkin_fields['checkin_type']}":'apertura',
        }
        query = [
            {'$match': match_query },
            {'$project': {
                "_id": 1,
                "folio": "$folio",
                "name": f"$answers.{self.mf['guard_group']}.{self.mf['catalog_guard_close']}.{self.mf['nombre_guardia_apoyo']}",
            }},
            {'$sort':{'folio':-1}},
            {'$limit':1},
        ]
        #return self.format_cr_result(self.format_cr_result(self.cr.aggregate(query)))
        response = self.format_cr_result(self.format_cr_result(self.cr.aggregate(query)))
        if len(response) == 1:
            list_guards = response[0].get('name',[])
            return list_guards
        else:
            return []

    def get_valiaciones_certificado(self, certificacion, id_user, empresa=None, detail=False):
        cert = self.get_certificacion(certificacion, id_user, empresa=empresa)
        if cert:
            return self.do_validacion_certificado(cert, detail=detail)
        else:
            return 'No Encontrado'

    def user_in_facility(self, status_visita):
        """
        Si envias un registro con entrada quiere regresa Verdadero, si 
        """
        if not status_visita:
            return False
        elif status_visita in ('entrada'):
            return True
        else:
            return False

    def is_boot_available(self, location, area):
        # Verifica si el boot está disponible para check-in.

        self.last_check_in = self.get_last_checkin(location, area)
        last_status = self.last_check_in.get('checkin_type')
        if last_status in ['entrada','apertura']:
            return False
        else:
            return True

    def set_checkout_employees(self, checkin={}, employee_list=[], replace=True):
        # Establece los empleados para check-out.
        
        if not replace:
            checkin[self.f['guard_group']] = employee_list
        elif employee_list and replace:
            checkin[self.f['guard_group']] += [
                {self.f['employee_position']:'guardiad_de_apoyo',
                 self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID:
                   {self.f['worker_name_b']:guard.get('name'),
                   }} 
                    for guard in employee_list ]
        return checkin

    def search_pass(self, qr_code=None, location=None):
        # Busca el pase de acceso con el código QR o ubicación

        if not qr_code and not location:
            msg = "Debes de proveer qr_code o location"
            self.LKFException(msg)
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.PASE_ENTRADA,
            }
        if qr_code:
            match_query.update({"_id":ObjectId(qr_code)})
        if location:
            match_query.update({f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}":location})
        query = [
            {'$match': match_query },
            {'$project': self.proyect_format(self.mf)},
            {'$sort':{'updated_at':-1}},
            {'$limit':1}
            ]
        return self.format_cr_result(self.cr.aggregate(query), get_one=True)

    def search_access_pass(self, qr_code=None, location=None):
        """
        Busca pases de acceso
        Si se entega el puro qr_code, se entrega la info de QR code
        Si se entrega el qr_code con location y area, te valida si el qr es valido para dicha area
        Si NO entregas el qr_code, te regresa todos los qr de dicha area y ubicacion
        Si no entregas nada, te regrea un warning...
        """
        last_move = {}
        if self.validate_value_id(qr_code):
            last_moves = self.get_list_last_user_move(qr_code, limit=10)
            if len(last_moves) > 0:
                last_move = last_moves[0]
            # else:
            #     self.LKFException({"msg":"No se econtro ninguan entrada con pase "+ qr_code})
            # print('last_moves=',simplejson.dumps(last_moves, indent=3))
            #last_move = self.get_last_user_move(qr_code, location)
            gafete_info = {}
            access_pass = self.get_detail_access_pass(qr_code)
            if not last_move or last_move.get('status_visita') == 'salida':
                tipo_movimiento = 'Entrada'
                access_pass['grupo_vehiculos'] = self.format_vehiculos_simple(access_pass.get('grupo_vehiculos',[]))
                access_pass['grupo_equipos'] = self.format_equipos_simple(access_pass.get('grupo_equipos',[]))
                print("entrada",access_pass['grupo_vehiculos'])
            else:
                gafete_info['gafete_id'] = last_move.get('gafete_id')
                gafete_info['locker_id'] = last_move.get('locker_id')
                access_pass['grupo_vehiculos'] = self.format_vehiculos_simple(last_move.get('vehiculos',[]))
                access_pass['grupo_equipos'] = self.format_equipos_simple(last_move.get('equipos',[]))
                tipo_movimiento = 'Salida'
                print("salida", access_pass['grupo_vehiculos'],access_pass['grupo_equipos'])
                print("last_move", simplejson.dumps(last_move, indent=4))
            #---Last Access
            access_pass['ultimo_acceso'] = last_moves
            access_pass['tipo_movimiento'] = tipo_movimiento
            access_pass['gafete_id'] = gafete_info.get('gafete_id')
            access_pass['locker_id'] = gafete_info.get("locker_id")
            access_pass['status_pase']= self.unlist(access_pass.get('estatus',"")).title() or ""
            access_pass['limitado_a_dias']= access_pass.get('limitado_a_dias','')
            access_pass['limitado_a_acceso']= access_pass.get('limite_de_acceso','')
            access_pass['config_dia_de_acceso']=access_pass.get('config_dia_de_acceso',"").replace("_", " ")
            total_entradas = self.get_count_ingresos(qr_code)
            access_pass['total_entradas'] = total_entradas.get('total_records') if total_entradas else "0"
            access_pass['anfitrions_data'] = access_pass.get('visita_a_details', [])
            if access_pass.get('grupo_areas_acceso'):
                for area in access_pass['grupo_areas_acceso']:
                    area['status'] = self.Location.get_area_status(access_pass['ubicacion'], area['nombre_area'])
            return access_pass
        else:
            return self.LKFException({"status_code":400, "msg":'El parametro para QR, no es valido'})

    def search_pass_by_status(self, status, query_update=None):
        match_query = {
            'form_id':self.PASE_ENTRADA,
            'deleted_at':{'$exists':False},
            f"answers.{self.pase_entrada_fields['status_pase']}":status,
        }
        if query_update:
            match_query.update(query_update)

        query = [ 
            {"$match":match_query},
            {'$project':
                {
                    '_id': 1,
                    'folio': "$folio",
                    'favoritos':f"$answers.{self.pase_entrada_fields['favoritos']}",
                    'ubicacion': f"$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
                    'nombre': {"$ifNull":[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['nombre_visita']}",
                        f"$answers.{self.mf['nombre_pase']}"]},
                    'estatus': f"$answers.{self.pase_entrada_fields['status_pase']}",
                    'empresa': {"$ifNull":[
                         f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['empresa']}",
                         f"$answers.{self.mf['empresa_pase']}"]},
                    'email':  {"$ifNull":[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['email_vista']}",
                        f"$answers.{self.mf['email_pase']}"]},
                    'telefono': {"$ifNull":[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['telefono']}",
                        f"$answers.{self.mf['telefono_pase']}"]},
                    'fecha_desde_visita': f"$answers.{self.mf['fecha_desde_visita']}",
                    'fecha_desde_hasta':{'$ifNull':[
                        f"$answers.{self.mf['fecha_desde_hasta']}",
                        f"$answers.{self.mf['fecha_desde_visita']}"]
                        },
                    'identificacion': {'$ifNull':[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['identificacion']}",
                        f"$answers.{self.pase_entrada_fields['walkin_identificacion']}"]},
                    'foto': {'$ifNull':[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['foto']}",
                        f"$answers.{self.pase_entrada_fields['walkin_fotografia']}"]},
                    'visita_a_nombre':
                        f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}",
                    'visita_a_puesto': 
                        f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['puesto_empleado']}",
                    'visita_a_departamento':
                        f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['departamento_empleado']}",
                    'visita_a_user_id':
                        f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['user_id_empleado']}",
                    'visita_a_email':
                        f"$answers.{self.mf['grupo_visitados']}.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['email_empleado']}",
                    'motivo_visita':f"$answers.{self.CONFIG_PERFILES_OBJ_ID}.{self.mf['motivo']}",
                    'tipo_de_pase':f"$answers.{self.pase_entrada_fields['perfil_pase']}",
                    'tema_cita':f"$answers.{self.pase_entrada_fields['tema_cita']}",
                    'descripcion':f"$answers.{self.pase_entrada_fields['descripcion']}",
                    'tipo_visita': f"$answers.{self.pase_entrada_fields['tipo_visita']}",
                    'limite_de_acceso': f"$answers.{self.mf['config_limitar_acceso']}",
                    'config_dia_de_acceso': f"$answers.{self.mf['config_dia_de_acceso']}",
                    'identificacion': {'$ifNull':[
                        f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['identificacion']}",
                        f"$answers.{self.pase_entrada_fields['walkin_identificacion']}"]},
                    'limitado_a_dias':f"$answers.{self.mf['config_dias_acceso']}",
                    'perfil_pase':f"$answers.{self.CONFIG_PERFILES_OBJ_ID}",
                    'tipo_de_comentario': f"$answers.{self.mf['tipo_de_comentario']}",
                    'tipo_fechas_pase': f"$answers.{self.mf['tipo_visita_pase']}",
                    'enviar_correo_pre_registro': f"$answers.{self.pase_entrada_fields['enviar_correo_pre_registro']}",
                    'enviar_correo': f"$answers.{self.pase_entrada_fields['enviar_correo']}",
                    'grupo_areas_acceso': f"$answers.{self.mf['grupo_areas_acceso']}",
                    'grupo_equipos': f"$answers.{self.mf['grupo_equipos']}",
                    'grupo_vehiculos': f"$answers.{self.mf['grupo_vehiculos']}",
                    'grupo_instrucciones_pase': f"$answers.{self.mf['grupo_instrucciones_pase']}",
                    'comentario': f"$answers.{self.mf['grupo_instrucciones_pase']}",
                    'comentario_area_pase':f"$answers.{self.mf['commentario_area']}",
                }
            },
            {'$sort':{'_id':-1}},
            # {'$limit':10}
        ]
        return self.format_cr(self.cr.aggregate(query))

    def set_boot_status(self, checkin_type):
        if checkin_type == 'in':
            set_boot_status = 'apertura'
        elif checkin_type == 'out':
            set_boot_status = 'cierre'
        return set_boot_status

    def set_employee_pic(self, employees):
        employee_ids = []
        for a, x in employees.items():
            if type(x) == list:
                for y in x:
                    employee_ids.append(y['user_id'])
            else:
                if x:
                    employee_ids.append(x['user_id'])
        pics = self.Employee.get_employee_pic(employee_ids)
        for a, x in employees.items():
            if type(x) == list:
                for y in x:
                    u_id = y['user_id']
                    if pics.get(u_id):
                        y['picture'] = pics[u_id]
            else:
                if x:
                    u_id = int(x['user_id'])
                    if pics.get(u_id):
                        x['picture'] = pics[u_id]
                    employee_ids.append(x['user_id'])
        return employees

    def update_article_concessioned(self, data_articles, folio):
        answers = {}
        for key, value in data_articles.items():
            if  key == 'ubicacion_concesion' or key == 'area_concesion':
                if data_articles['ubicacion_concesion'] and not data_articles['area_concesion']:
                    answers[self.cons_f['ubicacion_catalog_concesion']] = {self.mf['ubicacion']:data_articles['ubicacion_concesion']}
                elif data_articles['area_concesion'] and not data_articles['ubicacion_concesion']:
                    answers[self.cons_f['ubicacion_catalog_concesion']] = {self.mf['nombre_area_salida']:data_articles['area_concesion']}
                elif data_articles['area_concesion'] and data_articles['ubicacion_concesion']: 
                    answers[self.cons_f['ubicacion_catalog_concesion']] = {self.mf['ubicacion']:data_articles['ubicacion_concesion'],
                    self.mf['nombre_area_salida']:data_articles['area_concesion']}
            elif  key == 'persona_nombre_concesion':
                answers[self.cons_f['persona_catalog_concesion']] = { self.mf['nombre_guardia_apoyo'] : value}
            elif  key == 'caseta_concesion':
                answers[self.cons_f['area_catalog_concesion']] = { self.mf['nombre_area_salida']: value}
            elif  key == 'area_concesion':
                dic_prev = answers.get(self.cons_f['equipo_catalog_concesion'],{})
                dic_prev[self.cons_f['area_concesion']] = value 
                answers[self.cons_f['equipo_catalog_concesion']] = dic_prev
            elif  key == 'equipo_concesion':
                dic_prev = answers.get(self.cons_f['equipo_catalog_concesion'],{})
                dic_prev[self.cons_f['equipo_concesion']] = value 
                answers[self.cons_f['equipo_catalog_concesion']] = dic_prev
            else:
                answers.update({f"{self.cons_f[key]}":value})
        if answers or folio:
            return self.lkf_api.patch_multi_record( answers = answers, form_id=self.CONCESSIONED_ARTICULOS, folios=[folio])
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_article_lost(self, data_articles, folio):
        answers = {}
        employee = self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
        #---Define Answers
        date_entrega_perdido=""
        answers = {}
        for key, value in data_articles.items():
            if key == 'list_comments' or key == 'note_comments':
                answers.update({self.notes_fields['note_comments_group']:{-1:{f"{self.notes_fields[key]}": value}}})
            elif  key == 'tipo_articulo_perdido' or key == 'articulo_seleccion':
                if data_articles['tipo_articulo_perdido'] and not data_articles['articulo_seleccion']:
                    answers[self.perdidos_fields['tipo_articulo_catalog']] = {
                        self.perdidos_fields['tipo_articulo_perdido']: data_articles['tipo_articulo_perdido']
                        }
                elif data_articles['articulo_seleccion'] and not data_articles['tipo_articulo_perdido']:
                    answers[self.perdidos_fields['tipo_articulo_catalog']] = {
                        self.perdidos_fields['articulo_seleccion']: data_articles['articulo_seleccion']
                        }
                elif data_articles['articulo_seleccion'] and data_articles['tipo_articulo_perdido']: 
                    answers[self.perdidos_fields['tipo_articulo_catalog']] = {
                    self.perdidos_fields['tipo_articulo_perdido']:data_articles['tipo_articulo_perdido'],
                    self.perdidos_fields['articulo_seleccion']:data_articles['articulo_seleccion']}
            elif  key == 'ubicacion_perdido' or key == 'area_perdido':
                if data_articles['ubicacion_perdido'] and not data_articles['area_perdido']:
                    answers[self.perdidos_fields['ubicacion_catalog']] = {self.perdidos_fields['ubicacion_perdido']:data_articles['ubicacion_perdido']}
                elif data_articles['area_perdido'] and not data_articles['ubicacion_perdido']:
                    answers[self.perdidos_fields['ubicacion_catalog']] = {self.perdidos_fields['area_perdido']:data_articles['area_perdido']}
                elif data_articles['area_perdido'] and data_articles['ubicacion_perdido']: 
                    answers[self.perdidos_fields['ubicacion_catalog']] = {self.perdidos_fields['ubicacion_perdido']:data_articles['ubicacion_perdido'],
                    self.perdidos_fields['area_perdido']:data_articles['area_perdido']}
            elif key == 'quien_entrega_interno':
                answers[self.perdidos_fields['quien_entrega_catalog']] = {self.perdidos_fields['quien_entrega_interno']:value}
            elif key == 'locker_perdido':
                answers[self.perdidos_fields['locker_catalog']] = {self.perdidos_fields['locker_perdido']:value}
            elif key == 'estatus_perdido' and (value == 'donado' or value == 'entregado'):
                timezone = employee.get('cat_timezone', employee.get('timezone', 'America/Monterrey'))
                date_entrega_perdido =self.today_str(timezone, date_format='datetime')
                answers.update({
                    f"{self.perdidos_fields['date_entrega_perdido']}":date_entrega_perdido})
                answers.update({
                    f"{self.perdidos_fields['estatus_perdido']}":value})
            else:
                answers.update({f"{self.perdidos_fields[key]}":value})
        if answers or folio:
            res= self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_OBJETOS_PERDIDOS, folios=[folio])
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                res['json'].update({'date_entrega_perdido':date_entrega_perdido})
                return res
            else: 
                return res
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_failure(self, data_failures, folio):
        employee = self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
        answers = {}
        falla_fecha_hora_solucion=""
        for key, value in data_failures.items():
            if key == 'falla_ubicacion' or key == 'falla_caseta':
                if data_failures['falla_ubicacion'] and not data_failures['falla_caseta']:
                    answers[self.fallas_fields['falla_ubicacion_catalog']] = {self.fallas_fields['falla_ubicacion']:data_failures['falla_ubicacion']}
                elif data_failures['falla_caseta'] and not data_failures['falla_ubicacion']:
                    answers[self.fallas_fields['falla_ubicacion_catalog']] = {self.fallas_fields['falla_caseta']:data_failures['falla_caseta']}
                elif data_failures['falla_caseta'] and data_failures['falla_ubicacion']: 
                    answers[self.fallas_fields['falla_ubicacion_catalog']] = {self.fallas_fields['falla_ubicacion']:data_failures['falla_ubicacion'],
                    self.fallas_fields['falla_caseta']:data_failures['falla_caseta']}
            elif key == 'falla' or key== 'falla_objeto_afectado':
                answers[self.fallas_fields['falla_catalog']] = {self.fallas_fields['falla']:data_failures['falla'],
                self.fallas_fields['falla_subconcepto']:data_failures['falla_objeto_afectado']}
            elif key == 'falla_reporta_nombre':
                answers[self.fallas_fields['falla_reporta_catalog']] = {self.fallas_fields['falla_reporta_nombre']:value}
            elif key == 'falla_responsable_solucionar_nombre':
                answers[self.fallas_fields['falla_responsable_solucionar_catalog']] = {self.fallas_fields['falla_responsable_solucionar_nombre']:value}
            elif key == 'falla_estatus' and  value == 'resuelto':
                timezone = employee.get('cat_timezone', employee.get('timezone', 'America/Monterrey'))
                falla_fecha_hora_solucion =self.today_str(timezone, date_format='datetime')
                answers.update({
                    f"{self.fallas_fields['falla_fecha_hora_solucion']}":falla_fecha_hora_solucion})
                answers.update({
                    f"{self.fallas_fields['falla_estatus']}":value})
            elif key == 'falla_grupo_seguimiento':
                seg = data_failures.get('falla_grupo_seguimiento',[])
                if seg:
                    seg_list = []
                    for item in seg:
                        seg_list.append(
                            {
                                self.fallas_fields['falla_accion_realizada']:item.get('accion_correctiva_incidencia',''),
                                self.fallas_fields['falla_personas_involucradas']: item.get('incidencia_personas_involucradas',''),
                                self.fallas_fields['falla_evidencia_solucion']:item.get('incidencia_evidencia_solucion',''),
                                self.fallas_fields['falla_documento_solucion']: item.get('incidencia_documento_solucion',''),
                                self.fallas_fields['falla_fecha_seguimiento']:item.get('fecha_inicio_seg',''),
                                self.fallas_fields['falla_tiempo_transcurrido']:item.get('tiempo_transcurrido', '')
                            }
                        )
                    answers.update({self.fallas_fields['falla_grupo_seguimiento']:seg_list})
            else:
                answers.update({f"{self.fallas_fields[key]}":value})
        if answers or folio:
            res = self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_FALLAS, folios=[folio])
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                res['json'].update({'falla_fecha_hora_solucion':falla_fecha_hora_solucion})
                return res
            else:
                return res
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_failure_seguimiento(self, location=None, area=None, status=None, folio=None, falla_grupo_seguimiento=None):
        employee = self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
        failure_selected = self.get_list_fallas(location, area, folio=folio)
        if failure_selected:
            failure_selected = failure_selected[0]
        else:
            self.LKFException('No hay una falla registrada.')
        qr_code = failure_selected.get('_id')
        falla_nuevo_grupo = failure_selected.get('falla_grupo_seguimiento_formated', [])
        falla_nuevo_grupo_con_ids = []
        for falla in falla_nuevo_grupo:
            falla = {
                self.fallas_fields['falla_comentario_solucion']: falla.get('comentario'),
                self.fallas_fields['falla_folio_accion_correctiva']: falla.get('accion_correctiva'),
                self.fallas_fields['falla_evidencia_solucion']: falla.get('evidencia'),
                self.fallas_fields['falla_documento_solucion']: falla.get('documento'),
                self.fallas_fields['falla_inicio_seguimiento']: falla.get('fecha_inicio'),
                self.fallas_fields['falla_fin_seguimiento']: falla.get('fecha_fin'),    
            }
            falla_nuevo_grupo_con_ids.append(falla)

        falla_seg = {
            "falla_estatus": status,
            "falla_fecha_hora": failure_selected.get('falla_fecha_hora', ''),
            "falla_reporta_nombre": failure_selected.get('falla_reporta_nombre', ''),
            "falla_ubicacion": failure_selected.get('falla_ubicacion', ''),
            "falla_caseta": failure_selected.get('falla_caseta', ''),
            "falla": failure_selected.get('falla', ''),
            "falla_objeto_afectado": failure_selected.get('falla_objeto_afectado', ''),
            "falla_comentarios": failure_selected.get('falla_comentarios', ''),
            "falla_evidencia": failure_selected.get('falla_evidencia', []),
            "falla_documento": failure_selected.get('falla_documento', []),
            "falla_responsable_solucionar_nombre": failure_selected.get('falla_responsable_solucionar_nombre', ''),
            "falla_grupo_seguimiento": falla_grupo_seguimiento,
        }

        answers = {}
        falla_fecha_hora_solucion = ''

        if status == 'resuelto':
            timezone = employee.get('cat_timezone', employee.get('timezone', 'America/Monterrey'))
            falla_fecha_hora_solucion =self.today_str(timezone, date_format='datetime')
            answers.update({
                f"{self.fallas_fields['falla_fecha_hora_solucion']}": falla_fecha_hora_solucion
            })

        for key, value in falla_seg.items():
            if key == 'falla_reporta_nombre':
                answers.update({
                    self.fallas_fields['falla_reporta_catalog']: {
                        self.fallas_fields['falla_reporta_nombre']: value
                    }
                })
            elif key == 'falla_ubicacion':
                answers.update({
                    self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                        self.fallas_fields['falla_ubicacion']: falla_seg.get('falla_ubicacion'),
                        self.fallas_fields['falla_caseta']: falla_seg.get('falla_caseta')
                    }
                })
            elif key == 'falla':
                answers.update({
                    self.LISTA_FALLAS_CAT_OBJ_ID: {
                        self.fallas_fields['falla']: falla_seg.get('falla'),
                        self.fallas_fields['falla_subconcepto']: falla_seg.get('falla_objeto_afectado')
                    }
                })
            elif key == 'falla_responsable_solucionar_nombre':
                answers.update({
                    self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID: {
                        self.fallas_fields['falla_responsable_solucionar_nombre']: value
                    }
                })
            elif key == 'falla_grupo_seguimiento':
                fallas_seguimiento = [falla_seg.get('falla_grupo_seguimiento',{})]
                if fallas_seguimiento:
                    list_fallas_seguimiento = []
                    for item in fallas_seguimiento:
                        falla_folio = item.get('falla_folio_accion_correctiva','')
                        falla_comentario = item.get('falla_comentario_solucion','')
                        falla_foto_evidencia = item.get('falla_evidencia_solucion','')
                        falla_documento = item.get('falla_documento_solucion','')
                        falla_inicio_incidencia = item.get('fechaInicioFallaCompleta','')
                        falla_fin_incidencia = item.get('fechaFinFallaCompleta','')
                        list_fallas_seguimiento.append({
                            self.fallas_fields['falla_folio_accion_correctiva']:falla_folio,
                            self.fallas_fields['falla_comentario_solucion']:falla_comentario,
                            self.fallas_fields['falla_evidencia_solucion']:falla_foto_evidencia,
                            self.fallas_fields['falla_documento_solucion']:falla_documento,
                            self.fallas_fields['falla_inicio_seguimiento']:falla_inicio_incidencia,
                            self.fallas_fields['falla_fin_seguimiento']:falla_fin_incidencia,
                        })
                    falla_nuevo_grupo_con_ids.append(list_fallas_seguimiento[0])
                    answers[self.fallas_fields['falla_grupo_seguimiento']] = falla_nuevo_grupo_con_ids
            else:
                answers.update({f"{self.fallas_fields[key]}":value})

        if answers or folio:
            metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_FALLAS)
            metadata.update(self.get_record_by_folio(folio, self.BITACORA_FALLAS, select_columns={'_id':1}, limit=1))

            metadata.update({
                    'properties': {
                        "device_properties":{
                            "system": "Addons",
                            "process":"Actualizacion de Falla", 
                            "accion":'update_failure_seguimiento', 
                            "folio": folio, 
                            "archive": "fallas.py"
                        }
                    },
                    'answers': answers,
                    '_id': qr_code
                })
            print(simplejson.dumps(metadata, indent=3))
            res= self.net.patch_forms_answers(metadata)
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                res['json'].update({'falla_fecha_hora_solucion':falla_fecha_hora_solucion})
                return res
            else:
                return res
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_incidence_seguimiento(self, folio, incidencia_grupo_seguimiento,estatus, location=None, area=None):
        """
        Actualiza el seguimiento de una incidencia existente.
        folio: Folio de la incidencia a actualizar.
        incidencia_grupo_seguimiento: Lista de diccionarios con los datos del seguimiento.
        """
        incidence_selected = self.get_list_incidences(location, area, folio=folio)
        if incidence_selected:
            incidence_selected = incidence_selected[0]
        else:
            self.LKFException('No hay una incidencia registrada.')
        qr_code = incidence_selected.get('_id')
        incidencia_nuevo_grupo = incidence_selected.get('seguimientos_incidencia', [])
        # incidencia_nuevo_grupo_con_ids = []
        # for incidencia in incidencia_nuevo_grupo:
        #     incidencia = {
        #         self.incidence_fields['accion_correctiva_incidencia']:incidencia.get('accion_correctiva_incidencia',""),
        #         self.incidence_fields['incidencia_personas_involucradas'] :incidencia.get('incidencia_personas_involucradas',""),
        #         self.incidence_fields['fecha_inicio_seg'] :incidencia.get('fecha_inicio_seg',""),
        #         self.incidence_fields['tiempo_transcurrido'] : incidencia.get('tiempo_transcurrido',""),
        #         self.incidence_fields['incidencia_documento_solucion'] :incidencia.get('incidencia_documento_solucion'),
        #         self.incidence_fields['incidencia_evidencia_solucion'] :incidencia.get('incidencia_evidencia_solucion')
        #         # self.incidence_fields['comentario_accion_correctiva_incidencia']: incidencia.get('comentario'),
        #         # self.incidence_fields['accion_correctiva_incidencia']: incidencia.get('accion_correctiva'),
        #         # self.incidence_fields['evidencia_accion_correctiva_incidencia']: incidencia.get('evidencia'),
        #         # self.incidence_fields['documento_accion_correctiva_incidencia']: incidencia.get('documento'),
        #         # self.incidence_fields['fecha_inicio_seg']: incidencia.get('fecha_inicio'),
        #         # self.incidence_fields['fecha_fin_accion_correctiva_incidencia']: incidencia.get('fecha_fin'),    
        #     }
        #     incidencia_nuevo_grupo_con_ids.append(incidencia)
        incidencia_seg = {
            "reporta_incidencia": incidence_selected.get('reporta_incidencia', {}),
            "fecha_hora_incidencia": incidence_selected.get('fecha_hora_incidencia', ''),
            "ubicacion_incidencia": incidence_selected.get('ubicacion_incidencia', ''),
            "area_incidencia": incidence_selected.get('area_incidencia', ''),
            "incidencia": incidence_selected.get('incidencia', ''),
            "tipo_incidencia": incidence_selected.get('tipo_incidencia', ''),
            "comentario_incidencia": incidence_selected.get('comentario_incidencia', ''),
            "tipo_dano_incidencia": incidence_selected.get('tipo_dano_incidencia', []),
            "dano_incidencia": incidence_selected.get('dano_incidencia', ''),
            "personas_involucradas_incidencia": incidence_selected.get('personas_involucradas_incidencia', []),
            "acciones_tomadas_incidencia": incidence_selected.get('acciones_tomadas_incidencia', []),
            "afectacion_patrimonial_incidencia" : incidence_selected.get('afectacion_patrimonial_incidencia', []),
            "evidencia_incidencia": incidence_selected.get('evidencia_incidencia', []),
            "documento_incidencia": incidence_selected.get('documento_incidencia', []),
            "prioridad_incidencia": incidence_selected.get('prioridad_incidencia', '').lower(),
            "notificacion_incidencia": incidence_selected.get('notificacion_incidencia', ''),
            "tags": incidence_selected.get('tags', []),
            "datos_deposito_incidencia": incidence_selected.get('datos_deposito_incidencia', []),
            "total_deposito_incidencia": incidence_selected.get('total_deposito_incidencia', []),
            "seguimientos_incidencia": incidencia_nuevo_grupo,
            "seguimientos_incidencia_nuevo": [incidencia_grupo_seguimiento],
            "categoria": incidence_selected.get("categoria", ''),
            "sub_categoria": incidence_selected.get("sub_categoria", ''),
            "incidente": incidence_selected.get("incidente", ''),
            "estatus": estatus or incidence_selected.get("estatus", '')
        }
        answers = {}
        for key, value in incidencia_seg.items():
            if key == 'categoria':
                answers[self.incidence_fields['incidencia_catalog']].update({
                    self.incidence_fields['categoria']: value
                })
            if key == 'sub_categoria':
                answers[self.incidence_fields['incidencia_catalog']].update({
                    self.incidence_fields['sub_categoria']: value
                })
            if key == 'incidente':
                answers[self.incidence_fields['incidencia_catalog']].update({
                    self.incidence_fields['incidente']: incidencia_seg['incidencia']
                })
            if  key == 'ubicacion_incidencia' or key == 'area_incidencia':
                if incidencia_seg['ubicacion_incidencia'] and not incidencia_seg['area_incidencia']:
                    answers[self.incidence_fields['ubicacion_incidencia_catalog']] = {self.incidence_fields['ubicacion_incidencia']:incidencia_seg['ubicacion_incidencia']}
                elif incidencia_seg['area_incidencia'] and not incidencia_seg['ubicacion_incidencia']:
                    answers[self.incidence_fields['ubicacion_incidencia_catalog']] = {self.incidence_fields['area_incidencia']:incidencia_seg['area_incidencia']}
                elif incidencia_seg['area_incidencia'] and incidencia_seg['ubicacion_incidencia']: 
                    answers[self.incidence_fields['ubicacion_incidencia_catalog']] = {self.incidence_fields['ubicacion_incidencia']:incidencia_seg['ubicacion_incidencia'],
                    self.incidence_fields['area_incidencia']:incidencia_seg['area_incidencia']}
            elif  key == 'reporta_incidencia':
                answers[self.incidence_fields['reporta_incidencia_catalog']] = {self.incidence_fields['reporta_incidencia']:value}
            elif  key == 'incidencia':
                answers[self.incidence_fields['incidencia_catalog']] = {self.incidence_fields['incidencia']:value}
            elif key == 'personas_involucradas_incidencia':
                personas = incidencia_seg.get('personas_involucradas_incidencia',[])
                if personas:
                    personas_list = []
                    for c in personas:
                        personas_list.append(
                            {
                                self.incidence_fields['nombre_completo']:c.get('nombre_completo',""),
                                self.incidence_fields['puesto']:c.get('puesto',""),
                                self.incidence_fields['rol'] :c.get('rol',"").lower().replace(" ","_"),
                                self.incidence_fields['sexo'] :c.get('sexo',"").lower(),
                                self.incidence_fields['grupo_etario'] :c.get('grupo_etario',"").lower().replace(" ","_"),
                                self.incidence_fields['atencion_medica'] :c.get('atencion_medica',""),
                                self.incidence_fields['retenido'] :c.get('retenido',""),
                                self.incidence_fields['comentarios'] :c.get('comentarios',"")
                            }
                        )
                    answers.update({self.incidence_fields['personas_involucradas_incidencia']:personas_list})
            elif key == 'acciones_tomadas_incidencia':
                acciones = incidencia_seg.get('acciones_tomadas_incidencia',[])
                if acciones:
                    acciones_list = []
                    for c in acciones:
                        acciones_list.append(
                            {
                                self.incidence_fields['acciones_tomadas']:c.get('acciones_tomadas', ''),
                                self.incidence_fields['llamo_a_policia'] :c.get('llamo_a_policia', ''),
                                self.incidence_fields['autoridad'] :c.get('autoridad', '').lower().replace(" ","_"),
                                self.incidence_fields['numero_folio_referencia'] :c.get('numero_folio_referencia', ''),
                                self.incidence_fields['responsable'] :c.get('responsable', '')
                            }
                        )
                    answers.update({self.incidence_fields['acciones_tomadas_incidencia']:acciones_list})
            elif key == 'seguimientos_incidencia' or key == 'seguimientos_incidencia_nuevo':
                seg = incidencia_seg.get(key,[])
                if seg:
                    seg_list = []
                    for c in seg:
                        seg_list.append(
                            {
                                self.incidence_fields['accion_correctiva_incidencia']:c.get('accion_correctiva_incidencia',""),
                                self.incidence_fields['incidencia_personas_involucradas'] :c.get('incidencia_personas_involucradas',""),
                                self.incidence_fields['fecha_inicio_seg'] : c.get('fecha_inicio_seg',""),
                                self.incidence_fields['tiempo_transcurrido'] : c.get('tiempo_transcurrido',""),
                                self.incidence_fields['incidencia_documento_solucion'] : c.get('incidencia_documento_solucion'),
                                self.incidence_fields['incidencia_evidencia_solucion'] : c.get('incidencia_evidencia_solucion')
                            }
                        )
                    if self.incidence_fields['seguimientos_incidencia'] in answers:
                        answers[self.incidence_fields['seguimientos_incidencia']].extend(seg_list)
                    else:
                        answers[self.incidence_fields['seguimientos_incidencia']] = seg_list
            elif key == 'afectacion_patrimonial_incidencia':
                ap = incidencia_seg.get('afectacion_patrimonial_incidencia',[])
                if ap:
                    ap_list = []
                    for c in ap:
                        ap_list.append(
                            {
                                self.incidence_fields['tipo_afectacion']:c.get('tipo_afectacion',"").lower().replace(" ","_"),
                                self.incidence_fields['monto_estimado'] :c.get('monto_estimado',""),
                                self.incidence_fields['descripcion_afectacion']:c.get('descripcion_afectacion',""),
                                self.incidence_fields['estatus_afectacion']:c.get('estatus_afectacion',"").lower().replace(" ", "_"),
                                self.incidence_fields['duracion_estimada'] :c.get('duracion_estimada',""),
                                self.incidence_fields['evidencia'] :c.get('evidencia'),
                                self.incidence_fields['documento'] :c.get('documento')
                            }
                        )
                    answers.update({self.incidence_fields['afectacion_patrimonial_incidencia']:ap_list})
            elif key == 'datos_deposito_incidencia':
                acciones = incidencia_seg.get('datos_deposito_incidencia',[])
                if acciones:
                    acciones_list = []
                    for c in acciones:
                        acciones_list.append(
                            {
                                self.incidence_fields['tipo_deposito']:c.get('tipo_deposito','').lower().replace(" ","_"),
                                self.incidence_fields['cantidad'] :c.get('cantidad',''),
                                self.incidence_fields['origen'] :c.get('origen','')
                            }
                        )
                    answers.update({self.incidence_fields['datos_deposito_incidencia']:acciones_list})
            elif key == 'tags':
                tags = incidencia_seg.get('tags',[])
                if tags:
                    tag_list = []
                    for c in tags:
                        tag_list.append(
                            {
                                self.incidence_fields['tag']:c,
                            }
                        )
                    answers.update({self.incidence_fields['tags']:tag_list})
            elif key == 'prioridad_incidencia':
                answers[self.incidence_fields['prioridad_incidencia']] = f"{value}".lower()
            elif key == 'color_piel':
                answers[self.incidence_fields['color_piel']] = f"{value}".lower().replace(" ", "_")
            elif key == 'estatus':
                answers[self.incidence_fields['estatus']] = f"{value}".lower().replace(" ", "_")
            else:
                answers.update({f"{self.incidence_fields[key]}":value})
        print("ANSWERS", simplejson.dumps(answers, indent=4))
        # print(err)
        if answers or folio:
            metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_INCIDENCIAS)
            metadata.update(self.get_record_by_folio(folio, self.BITACORA_INCIDENCIAS, select_columns={'_id':1}, limit=1))

            metadata.update({
                    'properties': {
                        "device_properties":{
                            "system": "Addons",
                            "process":"Actualizacion de Incidencia", 
                            "accion":'update_incidence_seguimiento', 
                            "folio": folio, 
                            "archive": "incidencias.py"
                        }
                    },
                    'answers': answers,
                    '_id': qr_code
                })
            print(simplejson.dumps(metadata, indent=3))
            res= self.net.patch_forms_answers(metadata)
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                return res
            else:
                return res
        else:
            self.LKFException('No se mandarón parametros para actualizar') 

    def update_seg(self, folio, seguimientos ):
        # incidence_selected = self.get_list_incidences(location, area, folio=folio)
        answers={}
        print("SEGUIMIENTOS", seguimientos, folio)
        if seguimientos:
            seg_list={}
            seg_list.update({
                    self.incidence_fields['accion_correctiva_incidencia']:seguimientos.get('accion_correctiva_incidencia',""),
                    self.incidence_fields['incidencia_personas_involucradas'] :seguimientos.get('incidencia_personas_involucradas',""),
                    self.incidence_fields['fecha_inicio_seg'] :seguimientos.get('fecha_inicio_seg',""),
                    self.incidence_fields['tiempo_transcurrido'] : seguimientos.get('tiempo_transcurrido',""),
                    self.incidence_fields['incidencia_documento_solucion'] :seguimientos.get('incidencia_documento_solucion'),
                    self.incidence_fields['incidencia_evidencia_solucion'] :seguimientos.get('incidencia_evidencia_solucion')
                })
            # answers.update({self.incidence_fields['seguimientos_incidencia']:seg_list})
            answers[self.incidence_fields['seguimientos_incidencia']][-1]=seg_list
        print("answers",simplejson.dumps(answers, indent=4))
        res = self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_INCIDENCIAS, record_id=['68ad4fe042ca0aff7cadfd0e'])
        print("response",res)
        return res

    def update_incidence(self, data_incidences, folio):
        '''
            Realiza una actualización sobre cualquier nota, actualizando imagenes, status etc
        '''
        answers = {}
        # answers[self.incidence_fields['estatus']]="abierto"
        for key, value in data_incidences.items():
            if key == 'categoria':
                answers[self.incidence_fields['incidencia_catalog']].update({
                    self.incidence_fields['categoria']:data_incidences['categoria']
                })
            if key == 'sub_categoria':
                answers[self.incidence_fields['incidencia_catalog']].update({
                    self.incidence_fields['sub_categoria']: data_incidences['sub_categoria']
                })
            if key == 'incidente':
                answers[self.incidence_fields['incidencia_catalog']].update({
                    self.incidence_fields['incidente']: data_incidences['incidente']
                })
            if  key == 'ubicacion_incidencia' or key == 'area_incidencia':
                if data_incidences['ubicacion_incidencia'] and not data_incidences['area_incidencia']:
                    answers[self.incidence_fields['ubicacion_incidencia_catalog']] = {self.incidence_fields['ubicacion_incidencia']:data_incidences['ubicacion_incidencia']}
                elif data_incidences['area_incidencia'] and not data_incidences['ubicacion_incidencia']:
                    answers[self.incidence_fields['ubicacion_incidencia_catalog']] = {self.incidence_fields['area_incidencia']:data_incidences['area_incidencia']}
                elif data_incidences['area_incidencia'] and data_incidences['ubicacion_incidencia']: 
                    answers[self.incidence_fields['ubicacion_incidencia_catalog']] = {self.incidence_fields['ubicacion_incidencia']:data_incidences['ubicacion_incidencia'],
                    self.incidence_fields['area_incidencia']:data_incidences['area_incidencia']}
            elif  key == 'reporta_incidencia':
                answers[self.incidence_fields['reporta_incidencia_catalog']] = {self.incidence_fields['reporta_incidencia']:value}
            elif  key == 'incidencia':
                answers[self.incidence_fields['incidencia_catalog']] = {self.incidence_fields['incidencia']:value}
            elif key == 'personas_involucradas_incidencia':
                personas = data_incidences.get('personas_involucradas_incidencia',[])
                if personas:
                    personas_list = []
                    for c in personas:
                        personas_list.append(
                            {
                                self.incidence_fields['nombre_completo']:c.get('nombre_completo',""),
                                self.incidence_fields['puesto']:c.get('puesto',""),
                                self.incidence_fields['rol'] :c.get('rol',"").lower().replace(" ","_"),
                                self.incidence_fields['sexo'] :c.get('sexo',"").lower(),
                                self.incidence_fields['grupo_etario'] :c.get('grupo_etario',"").lower().replace(" ","_"),
                                self.incidence_fields['atencion_medica'] :c.get('atencion_medica',""),
                                self.incidence_fields['retenido'] :c.get('retenido',""),
                                self.incidence_fields['comentarios'] :c.get('comentarios',"")
                            }
                        )
                    answers.update({self.incidence_fields['personas_involucradas_incidencia']:personas_list})
            elif key == 'acciones_tomadas_incidencia':
                acciones = data_incidences.get('acciones_tomadas_incidencia',[])
                if acciones:
                    acciones_list = []
                    for c in acciones:
                        acciones_list.append(
                            {
                                self.incidence_fields['acciones_tomadas']:c.get('acciones_tomadas', ''),
                                self.incidence_fields['llamo_a_policia'] :c.get('llamo_a_policia', ''),
                                self.incidence_fields['autoridad'] :c.get('autoridad', '').lower().replace(" ","_"),
                                self.incidence_fields['numero_folio_referencia'] :c.get('numero_folio_referencia', ''),
                                self.incidence_fields['responsable'] :c.get('responsable', '')
                            }
                        )
                    answers.update({self.incidence_fields['acciones_tomadas_incidencia']:acciones_list})
            elif key == 'seguimientos_incidencia':
                seg = data_incidences.get('seguimientos_incidencia',[])
                if seg:
                    seg_list = []
                    for c in seg:
                        seg_list.append(
                            {
                                self.incidence_fields['accion_correctiva_incidencia']:c.get('accion_correctiva_incidencia',""),
                                self.incidence_fields['incidencia_personas_involucradas'] :c.get('incidencia_personas_involucradas',""),
                                self.incidence_fields['fecha_inicio_seg'] :c.get('fecha_inicio_seg',""),
                                self.incidence_fields['tiempo_transcurrido'] : c.get('tiempo_transcurrido',""),
                                self.incidence_fields['incidencia_documento_solucion'] :c.get('incidencia_documento_solucion'),
                                self.incidence_fields['incidencia_evidencia_solucion'] :c.get('incidencia_evidencia_solucion')
                            }
                        )
                    answers.update({self.incidence_fields['seguimientos_incidencia']:seg_list})
            elif key == 'afectacion_patrimonial_incidencia':
                ap = data_incidences.get('afectacion_patrimonial_incidencia',[])
                if ap:
                    ap_list = []
                    for c in ap:
                        ap_list.append(
                            {
                                self.incidence_fields['tipo_afectacion']:c.get('tipo_afectacion',"").lower().replace(" ","_"),
                                self.incidence_fields['monto_estimado'] :c.get('monto_estimado',""),
                                self.incidence_fields['descripcion_afectacion']:c.get('descripcion_afectacion',""),
                                self.incidence_fields['estatus_afectacion']:c.get('estatus_afectacion',"").lower().replace(" ", "_"),
                                self.incidence_fields['duracion_estimada'] :c.get('duracion_estimada',""),
                                self.incidence_fields['evidencia'] :c.get('evidencia'),
                                self.incidence_fields['documento'] :c.get('documento')
                            }
                        )
                    answers.update({self.incidence_fields['afectacion_patrimonial_incidencia']:ap_list})

            elif key == 'datos_deposito_incidencia':
                acciones = data_incidences.get('datos_deposito_incidencia',[])
                if acciones:
                    acciones_list = []
                    for c in acciones:
                        acciones_list.append(
                            {
                                self.incidence_fields['tipo_deposito']:c.get('tipo_deposito','').lower().replace(" ","_"),
                                self.incidence_fields['cantidad'] :c.get('cantidad',''),
                                self.incidence_fields['origen'] :c.get('origen','')
                            }
                        )
                    answers.update({self.incidence_fields['datos_deposito_incidencia']:acciones_list})
            elif key == 'tags':
                tags = data_incidences.get('tags',[])
                if tags:
                    tag_list = []
                    for c in tags:
                        tag_list.append(
                            {
                                self.incidence_fields['tag']:c,
                            }
                        )
                    answers.update({self.incidence_fields['tags']:tag_list})
            elif key == 'prioridad_incidencia':
                answers[self.incidence_fields['prioridad_incidencia']] = f"{value}".lower()
            elif key == 'color_piel':
                answers[self.incidence_fields['color_piel']] = f"{value}".lower().replace(" ", "_")
            elif key == 'estatus':
                answers[self.incidence_fields['estatus']] = f"{value}".lower().replace(" ", "_")

            else:
                answers.update({f"{self.incidence_fields[key]}":value})
        # print("incidencias answers", simplejson.dumps(answers, indent=4) )
        if answers or folio:
            metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_INCIDENCIAS)
            metadata.update(self.get_record_by_folio(folio, self.BITACORA_INCIDENCIAS, select_columns={'_id':1}, limit=1))
            metadata.update({
                    'properties': {
                        "device_properties":{
                            "system": "Addons",
                            "process":"Actualizacion de Incidencias", 
                            "accion":'update_incidence', 
                            "folio": folio, 
                            "archive": "incidencias.py"
                        }
                    },
                    'answers': answers
                })
            return self.net.patch_forms_answers(metadata)
            # return self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_INCIDENCIAS, folios=[folio])
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_gafet_status(self, answers={}):
        if not answers:
            answers = self.answers

        status = None
        tipo_movimiento=None
        tipo_movimiento = answers.get(self.mf['tipo_registro'])
        res = {}
        location=""
        area=""
        if tipo_movimiento == "entrada":
            status = "En Uso"
        elif tipo_movimiento == 'salida':
            status = "Disponible"
        if status :
            gafete_id = answers[self.GAFETES_CAT_OBJ_ID][self.gafetes_fields['gafete_id']]
            locker_id = answers[self.LOCKERS_CAT_OBJ_ID][self.mf['locker_id']]
            if self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID in answers:
                if self.f['area'] in answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]:
                    area = answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID][self.f['area']]
                if self.f['location'] in answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]:
                    location = answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID][self.f['location']]
            
            gafete = self.get_gafetes(status=None, location=location, area=area, gafete_id=gafete_id)

            print("heloooo", gafete, gafete_id, status,tipo_movimiento)

            if len(gafete) > 0 :
                gafete = gafete[0]
                res = self.lkf_api.update_catalog_multi_record({self.mf['status_gafete']: status}, self.GAFETES_CAT_ID, record_id=[gafete['_id']])
            self.update_locker_status(tipo_movimiento, location, area, tipo_locker='Identificaciones', locker_id=locker_id)

        return res

    def get_attendance_images(self, user_id):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.REGISTRO_ASISTENCIA,
                "created_by_id": user_id,
            }},
            {"$sort": {"created_at": -1}},
            {"$limit": 1},
            {"$project": {
                "_id": 0,
                "start_turn_image": {"$ifNull": [f"$answers.{self.f['image_checkin']}", ""]},
                "end_turn_image": {"$ifNull": [f"$answers.{self.f['foto_cierre_turno']}", ""]},
            }}
        ]
        data = self.format_cr(self.cr.aggregate(query))
        format_data = {}
        if data:
            format_data = self.unlist(data)
        return format_data

    def update_guard_status(self, guard, this_user):
        # last_checkin = self.get_user_last_checkin(guard['user_id'])
        attendance_images = self.get_attendance_images(this_user.get('user_id', self.unlist(this_user.get('usuario_id', 0))))
        status_turn = 'Turno Cerrado'
        if this_user.get('status') == 'in':
            status_turn = 'Turno Abierto'

        this_user['turn_start_datetime'] = this_user.get('checkin_date')
        this_user['start_turn_image'] = attendance_images.get('start_turn_image', [])
        this_user['end_turn_image'] = attendance_images.get('end_turn_image', [])
        this_user['status_turn'] = status_turn
        return this_user

    def update_guards_checkin(self, data_guard, record_id, location, area, user_data=None, nombre_suplente="", foto_checkin=[]):
        if not user_data:
            user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))

        timezone = user_data.get('timezone','America/Monterrey')
        now_datetime =self.today_str(timezone, date_format='datetime')
        response = []
        checkin = self.check_in_out_employees('in', now_datetime, checkin={},
            employee_list=data_guard, **{'employee_type':self.support_guard})
        for idx, employee in enumerate(checkin.get(self.mf['guard_group'],[])):
            user_id = employee[self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID].get(self.f['user_id_jefes'])
            validate_status = self.get_employee_checkin_status(user_id)
            not_allowed = [uid for uid, u_data in validate_status.items() if u_data['status'] =='in']
            if not_allowed:
                msg = f"El usuario(s) con ids {not_allowed}. Se encuentran actualmente logeado en otra caseta."
                msg += f"Es necesario primero salirse de cualquier caseta antes de querer entrar a una casta"
                self.LKFException({'msg':msg,"title":'Accion Requerida!!!'})
            answers = {}
            answers[self.mf['guard_group']] = {'-1':employee}

            asistencia_answers = {
                self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID: {
                    self.Location.f['location']: location,
                    self.Location.f['area']: area
                },
                self.f['tipo_guardia']: 'guardia_regular',
                self.checkin_fields['checkin_type']: 'iniciar_turno',
                self.f['image_checkin']: foto_checkin
            }
            if nombre_suplente:
                asistencia_answers.update({
                    self.f['tipo_guardia']: 'guardia_suplente',
                    self.f['nombre_guardia_suplente']: nombre_suplente
                })
            self.do_attendance(asistencia_answers)

            data = self.lkf_api.patch_multi_record( answers = answers, form_id=self.CHECKIN_CASETAS, record_id=[record_id])
            data.update({'registro_de_asistencia': 'Correcto'})
            response.append(data)
        return response

    def update_locker_status(self, tipo_movimiento, location, area, tipo_locker, locker_id):
        res = {}
        if tipo_movimiento == "entrada":
            status = "En Uso"
        elif tipo_movimiento == 'salida':
            status = "Disponible"

        locker = self.get_lockers(status=None, location=location, area=area, tipo_locker=tipo_locker, locker_id=locker_id)
        if len(locker) > 0 :
            locker = locker[0]
            res = self.lkf_api.update_catalog_multi_record({self.mf['status_locker']: status}, self.LOCKERS_CAT_ID, record_id=[locker['_id']])
        return res

    def update_notes(self, data_notes, folio):
        '''
            Realiza una actualización sobre cualquier nota, actualizando imagenes, status etc
        '''
        answers = {}
        #----Assign Value
        for key, value in data_notes.items():
            if not value:
                continue
            if key == 'list_comments' or key == 'note_comments':
                answers.update({self.notes_fields['note_comments_group']:{-1:{f"{self.notes_fields[key]}": value}}})
            elif  key == 'note_booth':
                answers[self.notes_fields['note_catalog_booth']] = {self.notes_fields['note_booth']:value}
            elif  key == 'note_guard':
                answers[self.notes_fields['note_catalog_guard']] = {self.notes_fields['note_guard']:value}
            else:
                answers.update({f"{self.notes_fields[key]}":value})
        #----Assign Time
        if data_notes.get('note_status','') == 'cerrado':
            employee = self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
            timezone = employee.get('cat_timezone', employee.get('timezone', 'America/Monterrey'))
            fecha_hora_str =self.today_str(timezone, date_format='datetime')
            answers.update({
                f"{self.notes_fields['note_close_date']}":fecha_hora_str,
                self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID :{
                    self.Employee.employee_fields['worker_name_b']:employee['worker_name'],
                    }
                }
                )

        if answers or folio:
            return self.lkf_api.patch_multi_record( answers = answers, form_id=self.ACCESOS_NOTAS, folios=[folio])
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_bitacora_entrada(self, data, record_id=None, folio=None):
        '''
            Realiza una actualización sobre cualquier nota, actualizando imagenes, status etc
        '''
        answers = {}
        action = data.get('action', 'create')
        equipos = data.get('equipos', data.get('equipo'))
        if equipos:
            tipo = equipos.get('tipo','').lower().replace(' ', '_')
            nombre = equipos.get('nombre','')
            marca = equipos.get('marca','')
            modelo = equipos.get('modelo','')
            color = equipos.get('color','')
            serie = equipos.get('serie','')
            ans = {
                self.mf['tipo_equipo']:tipo,
                self.mf['nombre_articulo']:nombre,
                self.mf['marca_articulo']:marca,
                self.mf['modelo_articulo']:modelo,
                self.mf['color_articulo']:color,
                self.mf['numero_serie']:serie,
            }
            if action == 'create':
                answers[self.mf['grupo_equipos']]  = {-1: ans }
            elif action == 'edit':
                answers[self.mf['grupo_equipos']]  = {data.get('set_number',0): ans }

        vehiculos = data.get('vehiculo',[])
        if vehiculos:
            tipo = vehiculos.get('tipo', vehiculos.get('tipo',''))
            marca = vehiculos.get('marca','')
            modelo = vehiculos.get('modelo','')
            estado = vehiculos.get('estado','')
            placas = vehiculos.get('placas',vehiculos.get('placas_vehiculo',''))
            color = vehiculos.get('color',vehiculos.get('color_vehiculo',''))
            ans = {
                    self.AF.TIPO_DE_VEHICULO_OBJ_ID:{
                        self.mf['tipo_vehiculo']:tipo,
                        self.mf['marca_vehiculo']:marca,
                        self.mf['modelo_vehiculo']:modelo,
                    },
                    self.ESTADO_OBJ_ID:{
                        self.mf['nombre_estado']:estado,
                    },
                    self.mf['placas_vehiculo']:placas,
                    self.mf['color_vehiculo']:color,
                    }
            if action == 'create':
                answers[self.mf['grupo_vehiculos']]  = {-1: ans }
            elif action == 'edit':
                answers[self.mf['grupo_vehiculos']]  = {data.get('set_number',0): ans }
        #TODO UPDATE GAFET

        if not record_id and not folio:
            self.LKFException({'msg':'Se requiere el folio o el id del registro a editar'})
        if record_id:
            res =  self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_ACCESOS, record_id=[record_id,])
        elif folio:
             res = self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_ACCESOS, folios=[folio,])
        else:
            self.LKFException({'msg':'Faltan datos para acutalizar pase de entrada'})
        return res

    def update_bitacora_entrada_many(self, data, record_id=None, folio=None):
        answers = {}
        action = data.get('action', 'create')
        equipos = data.get('equipos', data.get('equipo'))
        if equipos:
            for i, equipo in enumerate(equipos):  # Iterar sobre cada equipo
                tipo = equipo.get('tipo_equipo', '').lower().replace(' ', '_')
                nombre = equipo.get('nombre_articulo', '')
                marca = equipo.get('marca_articulo', '')
                modelo = equipo.get('modelo_articulo', '')
                color = equipo.get('color_articulo', '')
                serie = equipo.get('numero_serie', '')
                ans = {
                    self.mf['tipo_equipo']: tipo,
                    self.mf['nombre_articulo']: nombre,
                    self.mf['marca_articulo']: marca,
                    self.mf['modelo_articulo']: modelo,
                    self.mf['color_articulo']: color,
                    self.mf['numero_serie']: serie,
                }
                
                if action == 'create':
                    # Usar -1 para nuevos registros en 'create'
                    answers[self.mf['grupo_equipos']] = answers.get(self.mf['grupo_equipos'], {})
                    answers[self.mf['grupo_equipos']][-1] = ans
                elif action == 'edit':
                    # Usar el número de conjunto especificado en 'edit'
                    set_number = data.get('set_number', 0)
                    answers[self.mf['grupo_equipos']] = answers.get(self.mf['grupo_equipos'], {})
                    answers[self.mf['grupo_equipos']][set_number] = ans

        # Procesar los vehículos
        vehiculos = data.get('vehiculo', [])
        if vehiculos:
            for i, vehiculo in enumerate(vehiculos):  # Iterar sobre cada vehículo
                tipo = vehiculo.get('tipo_vehiculo', vehiculo.get('tipo', ''))
                marca = vehiculo.get('marca_vehiculo', '')
                modelo = vehiculo.get('modelo_vehiculo', '')
                estado = vehiculo.get('nombre_estado', '')
                placas = vehiculo.get('placas', vehiculo.get('placas_vehiculo', ''))
                color = vehiculo.get('color', vehiculo.get('color_vehiculo', ''))
                
                ans = {
                    self.AF.TIPO_DE_VEHICULO_OBJ_ID: {
                        self.mf['tipo_vehiculo']: tipo,
                        self.mf['marca_vehiculo']: marca,
                        self.mf['modelo_vehiculo']: modelo,
                    },
                    self.ESTADO_OBJ_ID: {
                        self.mf['nombre_estado']: estado,
                    },
                    self.mf['placas_vehiculo']: placas,
                    self.mf['color_vehiculo']: color,
                }

                if action == 'create':
                    # Usar -1 para nuevos registros en 'create'
                    answers[self.mf['grupo_vehiculos']] = answers.get(self.mf['grupo_vehiculos'], {})
                    answers[self.mf['grupo_vehiculos']][-1] = ans
                elif action == 'edit':
                    # Usar el número de conjunto especificado en 'edit'
                    set_number = data.get('set_number', 0)
                    answers[self.mf['grupo_vehiculos']] = answers.get(self.mf['grupo_vehiculos'], {})
                    answers[self.mf['grupo_vehiculos']][set_number] = ans
                #TODO UPDATE GAFET

        if not record_id and not folio:
            self.LKFException({'msg':'Se requiere el folio o el id del registro a editar'})
        if record_id:
            res =  self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_ACCESOS, record_id=[record_id,])
        elif folio:
             res = self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_ACCESOS, folios=[folio,])
        else:
            self.LKFException({'msg':'Faltan datos para acutalizar pase de entrada'})
        return res

    def catalog_visita_a_pases(self, visita_a):
        if visita_a == 'Usuario Actual':
            user_id = self.user['user_id']
            employee = self.Employee.get_employee_data(user_id=self.user['user_id'], get_one=True)
            self.employee = employee
            visita_a = employee.get('worker_name')
        visita_set = {
            self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID:{
                self.mf['nombre_empleado'] : visita_a,
                }
            }
        options_vistia = {
              "group_level": 2,
              "startkey": [visita_a],
              "endkey": [f"{visita_a}\n",{}],
            }
        cat_visita = self.catalogo_view(self.Employee.CONF_AREA_EMPLEADOS_CAT_ID, self.PASE_ENTRADA, options_vistia)
        if len(cat_visita) > 0:
            cat_visita =  {key: [value,] for key, value in cat_visita[0].items() if value}
        visita_set[self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID].update(cat_visita)
        return visita_set

    def update_pass(self, access_pass,folio=None):
        pass_selected= self.get_detail_access_pass(qr_code=folio, get_answers=True)
        qr_code= folio
        _folio= pass_selected.get("folio")
        answers={}
        for key, value in access_pass.items():
            if not self.pase_entrada_fields.get(key):
                continue
            if key == 'grupo_vehiculos':
                answers[self.mf['grupo_vehiculos']]={}
                for index, item in enumerate(access_pass.get('grupo_vehiculos',[])):
                    tipo = item.get('tipo',item.get('tipo_vehiculo',''))
                    marca = item.get('marca',item.get('marca_vehiculo',''))
                    modelo = item.get('modelo',item.get('modelo_vehiculo',''))
                    estado = item.get('estado',item.get('nombre_estado',''))
                    placas = item.get('placas',item.get('placas_vehiculo',''))
                    color = item.get('color',item.get('color_vehiculo',''))
                    foto_vehiculo = item.get('foto_vehiculo','')
                    obj={
                        self.AF.TIPO_DE_VEHICULO_OBJ_ID:{
                            self.mf['tipo_vehiculo']:tipo,
                            self.mf['marca_vehiculo']:marca,
                            self.mf['modelo_vehiculo']:modelo,
                        },
                        self.ESTADO_OBJ_ID:{
                            self.mf['nombre_estado']:estado,
                        },
                        self.mf['placas_vehiculo']:placas,
                        self.mf['color_vehiculo']:color,
                        self.f['foto_vehiculo']:foto_vehiculo,
                    }
                    answers[self.mf['grupo_vehiculos']][(index+1)*-1]=obj
            elif key == 'grupo_equipos':
                answers[self.mf['grupo_equipos']]={}
                for index, item in enumerate(value):
                    nombre = item.get('nombre',item.get('nombre_articulo',''))
                    marca = item.get('marca',item.get('marca_articulo',''))
                    color = item.get('color',item.get('color_articulo',''))
                    tipo = item.get('tipo',item.get('tipo_equipo',''))
                    serie = item.get('serie',item.get('numero_serie',''))
                    modelo = item.get('modelo',item.get('modelo_articulo',''))
                    foto_equipo = item.get('foto_equipo','')
                    obj={
                        self.mf['tipo_equipo']:tipo.lower(),
                        self.mf['nombre_articulo']:nombre,
                        self.mf['marca_articulo']:marca,
                        self.mf['numero_serie']:serie,
                        self.mf['color_articulo']:color,
                        self.mf['modelo_articulo']:modelo,
                        self.f['foto_equipo']:foto_equipo,
                    }
                    answers[self.mf['grupo_equipos']][(index+1)*-1]=obj
            elif key == 'visita_a':
                for index, item in enumerate(access_pass.get('visita_a',[])):
                    answers[self.mf['grupo_visitados']] = answers.get(self.mf['grupo_visitados'],{})
                    answers[self.mf['grupo_visitados']][(index+1)*-1] =self.catalog_visita_a_pases(item)
            elif key == 'status_pase':
                answers.update({f"{self.pase_entrada_fields[key]}":value.lower()})
            elif key == 'archivo_invitacion':
                answers.update({f"{self.pase_entrada_fields[key]}": value})
            elif key == "google_wallet_pass_url":
                answers.update({f"{self.pase_entrada_fields[key]}": value})
            elif key == "apple_wallet_pass":
                answers.update({f"{self.pase_entrada_fields[key]}": value})
            elif key == "pdf_to_img":
                answers.update({f"{self.pase_entrada_fields[key]}": value})
            elif key == 'favoritos':
                answers.update({f"{self.pase_entrada_fields[key]}": [value]})
            elif key == 'conservar_datos_por':
                answers.update({f"{self.pase_entrada_fields[key]}": value.replace(" ", "_")})
            else:
                if value:
                    answers.update({f"{self.pase_entrada_fields[key]}":value})
        employee = getattr(self,'employee',self.Employee.get_employee_data(email=self.user.get('email'), get_one=True))
        if answers:
            new_answers = deepcopy(pass_selected['answers'])
            new_answers.update(answers)
            # Si viene con estatus cancelado se salta la funcion de asignar estatus
            status_field = self.pase_entrada_fields['status_pase']
            if answers.get(status_field) == 'cancelado':
                status = 'cancelado'
            else:
                status = self.access_pass_set_status(new_answers)
            answers[status_field] = status

            res= self.lkf_api.patch_multi_record( answers = answers, form_id=self.PASE_ENTRADA, record_id=[qr_code])
            if res.get('status_code') == 201 or res.get('status_code') == 202 and folio:
                pdf = getattr(self, 'pdf', self.lkf_api.get_pdf_record(qr_code, name_pdf='Pase de Entrada', send_url=True))
                res['json'].update({'qr_pase':pass_selected.get("qr_pase")})
                res['json'].update({'telefono':pass_selected.get("telefono")})
                res['json'].update({'enviar_a':pass_selected.get("nombre")})
                res['json'].update({'enviar_de':employee.get('worker_name')})
                res['json'].update({'enviar_de_correo':employee.get('email')})
                res['json'].update({'ubicacion':pass_selected.get('ubicacion')})
                res['json'].update({'fecha_desde':pass_selected.get('fecha_de_expedicion')})
                res['json'].update({'fecha_hasta':pass_selected.get('fecha_de_caducidad')})
                res['json'].update({'asunto':pass_selected.get('tema_cita')})
                res['json'].update({'descripcion':pass_selected.get('descripcion')})
                res['json'].update({'pdf': pdf})
                return res
            else:
                return res
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_pass_img(self, qr_code=None):
        self.pdf = getattr(self, 'pdf', self.lkf_api.get_pdf_record(qr_code, name_pdf='Pase de Entrada', send_url=True))
        pdf_url = self.pdf.get('json', {}).get('download_url')
        id_forma = self.PASE_ENTRADA
        id_campo_pdf_to_img = self.pase_entrada_fields['pdf_to_img']
        pass_img_url = self.upload_pdf_as_image(id_forma, id_campo_pdf_to_img, pdf_url)
        pass_img_file_name = pass_img_url.get('file_name')
        pass_img_file_url = pass_img_url.get('file_url')
        return [{'file_name': pass_img_file_name, 'file_url': pass_img_file_url}]

    def update_full_pass(self, access_pass,folio=None, qr_code=None, location=None):
        answers = {}
        perfil_pase = access_pass.get('perfil_pase', 'Visita General')
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        this_user = self.Employee.get_employee_data(user_id=self.user.get('user_id'), get_one=True)
        this_user_name = this_user.get('worker_name', '')
        timezone = user_data.get('timezone','America/Monterrey')
        now_datetime =self.today_str(timezone, date_format='datetime')
        answers[self.mf['grupo_visitados']] = []
        employee = self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
        nombre_visita_a = employee.get('worker_name')

        # answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {}
        # answers[self.Location.UBICACIONES_CAT_OBJ_ID][self.f['location']] = location
        answers[self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID] = {}
        answers[self.CONFIG_PERFILES_OBJ_ID] = {}
        answers[self.VISITA_AUTORIZADA_CAT_OBJ_ID] = {}
        # answers[self.pase_entrada_fields['qr_pase']] = []

        for key, value in access_pass.items():
            if key == 'grupo_vehiculos':
                vehiculos = access_pass.get('grupo_vehiculos',[])
                if vehiculos:
                    list_vehiculos = []
                    for item in vehiculos:
                        tipo = item.get('tipo_vehiculo', item.get('tipo', ''))
                        marca = item.get('marca_vehiculo', item.get('marca', ''))
                        modelo = item.get('modelo_vehiculo', item.get('modelo', ''))
                        estado = item.get('state', item.get('estado', ''))
                        placas = item.get('placas_vehiculo', item.get('placas', ''))
                        color = item.get('color_vehiculo', item.get('color', ''))
                        list_vehiculos.append({
                            self.AF.TIPO_DE_VEHICULO_OBJ_ID:{
                                self.mf['tipo_vehiculo']:tipo,
                                self.mf['marca_vehiculo']:marca,
                                self.mf['modelo_vehiculo']:modelo,
                            },
                            self.ESTADO_OBJ_ID:{
                                self.mf['nombre_estado']:estado,
                            },
                            self.mf['placas_vehiculo']:placas,
                            self.mf['color_vehiculo']:color,
                        })
                    answers[self.mf['grupo_vehiculos']] = list_vehiculos  
            elif key == 'grupo_equipos':
                equipos = access_pass.get('grupo_equipos',[])
                if equipos:
                    list_equipos = []
                    for item in equipos:
                        tipo = item.get('tipo_equipo', item.get('tipo', '')).lower().replace(' ', '_')
                        nombre = item.get('nombre_articulo', item.get('nombre', ''))
                        marca = item.get('marca_articulo', item.get('marca', ''))
                        modelo = item.get('modelo_articulo', item.get('modelo', ''))
                        color = item.get('color_articulo', item.get('color', ''))
                        serie = item.get('numero_serie', item.get('serie', ''))
                        list_equipos.append({
                            self.mf['tipo_equipo']:tipo,
                            self.mf['nombre_articulo']:nombre,
                            self.mf['marca_articulo']:marca,
                            self.mf['modelo_articulo']:modelo,
                            self.mf['color_articulo']:color,
                            self.mf['numero_serie']:serie,
                        })
                    answers[self.mf['grupo_equipos']] = list_equipos
            elif key == 'grupo_instrucciones_pase':
                acciones = access_pass.get('grupo_instrucciones_pase',[])
                if acciones:
                    acciones_list = []
                    for c in acciones:
                        acciones_list.append(
                            {
                                self.pase_entrada_fields['tipo_comentario']:c.get('tipo_comentario'),
                                self.pase_entrada_fields['comentario_pase'] :c.get('comentario_pase')
                            }
                        )
                    answers.update({self.pase_entrada_fields['grupo_instrucciones_pase']:acciones_list})
            elif key == 'grupo_areas_acceso':
                acciones = access_pass.get('grupo_areas_acceso',[])
                if acciones:
                    acciones_list = []
                    for c in acciones:
                        acciones_list.append(
                            {
                                self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID : {
                                    self.pase_entrada_fields['nombre_area']:c.get('nombre_area')
                                } ,
                                self.pase_entrada_fields['commentario_area'] :c.get('commentario_area')
                            }
                        )
                    answers.update({self.pase_entrada_fields['grupo_areas_acceso']:acciones_list})
            elif key == 'autorizado_por':
                answers[self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID] = {
                    self.mf['nombre_guardia_apoyo'] : this_user_name,
                }
            elif key == 'link':
                link_info=access_pass.get('link', '')
                if link_info:
                    docs=""
                    for index, d in enumerate(link_info["docs"]): 
                        if(d == "agregarIdentificacion"):
                            docs+="iden"
                        elif(d == "agregarFoto"):
                            docs+="foto"
                        if index==0 :
                            docs+="-"
                    link_pass= f"{link_info['link']}?id={link_info['qr_code']}&user={link_info['creado_por_id']}&docs={docs}"

                answers.update({f"{self.pase_entrada_fields[key]}":link_pass})
            elif key == 'ubicacion':
                # answers[self.pase_entrada_fields['ubicacion_cat']] = {self.mf['ubicacion']:access_pass['ubicacion']}
                ubicaciones = access_pass.get('ubicacion',[])
                if ubicaciones:
                    ubicaciones_list = []
                    for ubi in ubicaciones:
                        ubicaciones_list.append(
                            {
                                self.pase_entrada_fields['ubicacion_cat']:{ self.mf["ubicacion"] : ubi}
                            }
                        )
                    answers.update({self.pase_entrada_fields['ubicaciones']:ubicaciones_list})
            elif key == 'created_from':
                created_from = access_pass.get('created_from')
                if created_from == 'app':
                    created_from = 'pase_de_entrada_app'
                elif created_from == 'web':
                    created_from = 'pase_de_entrada_web'
                elif created_from == 'nueva_visita':
                    created_from = 'nueva_visita'
                elif created_from == 'auto_registro':
                    created_from = 'auto_registro'
                else:
                    created_from = 'nueva_visita'

                if created_from:
                    answers[self.pase_entrada_fields['creado_desde']] = created_from
            elif key == 'visita_a':
                answers[self.mf['grupo_visitados']] = self.access_pass_vista_a(access_pass.get('visita_a',[]))
            elif key == 'perfil_pase':
                # Perfil de Pase
                answers[self.CONFIG_PERFILES_OBJ_ID] = {}
                answers[self.CONFIG_PERFILES_OBJ_ID] = {
                    self.mf['nombre_perfil'] : perfil_pase,
                }
                options = {
                      "group_level": 2,
                      "startkey": [perfil_pase],
                      "endkey": [f"{perfil_pase}\n",{}],
                    }
                cat_perfil = self.catalogo_view(self.CONFIG_PERFILES_ID, self.PASE_ENTRADA, options)
                if len(cat_perfil) > 0:
                    cat_perfil[0][self.mf['motivo']]= [cat_perfil[0].get(self.mf['motivo'])]
                    cat_perfil = cat_perfil[0]
                answers[self.CONFIG_PERFILES_OBJ_ID].update(cat_perfil)
                if answers[self.CONFIG_PERFILES_OBJ_ID].get(self.mf['nombre_permiso']) and \
                   type(answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']]) == str:
                    answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']] = [answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']],]
            elif key == 'archivo_invitacion':
                # id_forma = 121736
                id_forma = self.PASE_ENTRADA
                # id_campo = '673773741b2adb2d05d99d63'
                id_campo = self.pase_entrada_fields['archivo_invitacion']
                tema_cita = access_pass.get("tema_cita")
                descripcion = access_pass.get("descripcion")
                fecha_desde_visita = access_pass.get("fecha_desde_visita")
                fecha_desde_hasta = access_pass.get("fecha_desde_hasta")
                creado_por_email = access_pass.get("link", {}).get("creado_por_email")
                ubicacion = access_pass.get("ubicacion",'')
                nombre = access_pass.get("nombre_pase",'')
                visita_a = access_pass.get("visita_a",'')
                email = access_pass.get("email_pase",'')

                start_datetime = datetime.strptime(fecha_desde_visita, "%Y-%m-%d %H:%M:%S")

                if not fecha_desde_hasta:
                    stop_datetime = start_datetime + timedelta(hours=1)
                else:
                    stop_datetime = datetime.strptime(fecha_desde_hasta, "%Y-%m-%d %H:%M:%S")

                meeting = [
                    {
                        "id": 1,
                        "start": start_datetime,
                        "stop": stop_datetime,
                        "name": tema_cita,
                        "description": descripcion,
                        "location": ubicacion,
                        "allday": False,
                        "rrule": None,
                        "alarm_ids": [{"interval": "minutes", "duration": 10, "name": "Reminder"}],
                        'organizer_name': visita_a,
                        'organizer_email': creado_por_email,
                        "attendee_ids": [{"email": email, "nombre": nombre}, {"email": creado_por_email, "nombre": visita_a}],
                    }
                ]
                respuesta_ics = self.upload_ics(id_forma, id_campo, meetings=meeting)
                file_name = respuesta_ics.get('file_name', '')
                file_url = respuesta_ics.get('file_url', '')

                archivo_invitacion= [
                    {
                        "file_name": f"{file_name}",
                        "file_url": f"{file_url}"
                    }
                ]
                answers.update({f"{self.pase_entrada_fields[key]}": archivo_invitacion})
            else:
                answers.update({f"{self.pase_entrada_fields[key]}":value})

        # --- Manejo de acompañantes nuevos ---
        acompanantes_nuevos = access_pass.get('acompanantes_grupo', []) or []
        acompanantes_total = len(acompanantes_nuevos)

        if acompanantes_nuevos:
            registro_actual = self.get_record_by_folio(
                folio, self.PASE_ENTRADA, select_columns={'_id': 1}, limit=1
            ) or {}
            parent_id = registro_actual.get('_id') or qr_code

            child_group_nuevo = self.create_multiple_pass_threads(answers, acompanantes_nuevos, parent_id) if parent_id else []

            answers[self.pase_entrada_fields['acompanantes_grupo']] = child_group_nuevo
            answers[self.pase_entrada_fields['acompanantes']] = acompanantes_total

        if answers or folio:
            metadata = self.lkf_api.get_metadata(form_id=self.PASE_ENTRADA)
            metadata.update(self.get_record_by_folio(folio, self.PASE_ENTRADA, select_columns={'_id':1}, limit=1))

            metadata.update({
                    'properties': {
                        "device_properties":{
                            "system": "Addons",
                            "process":"Actualizacion de Pase de Entrada",
                            "accion":'update_full_pass',
                            "folio": folio,
                            "archive": "pase_acceso.py"
                        }
                    },
                    'answers': answers,
                    '_id': qr_code
                })
            res= self.net.patch_forms_answers(metadata)
            return res
            # return self.lkf_api.patch_multi_record( answers = answers, form_id=self.BITACORA_INCIDENCIAS, folios=[folio,])
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_active_pass(self, folio=None, qr_code=None, update_obj={}):
        pass_selected= self.get_detail_access_pass(qr_code=qr_code)
        if not pass_selected.get('fecha_de_caducidad'):
            tipo_visita_pase = 'fecha_fija'
        else:
            tipo_visita_pase = 'rango_de_fechas'

        access_pass = {
            "autorizado_por": pass_selected.get('visita_a', '')[0].get('nombre'),
            "config_dias_acceso": pass_selected.get('limitado_a_dias', []),
            "config_limitar_acceso": pass_selected.get('limite_de_acceso'),
            "descripcion": pass_selected.get('descripcion', ''),
            "email_pase": pass_selected.get('email', ''),
            "enviar_correo": [],
            "enviar_correo_pre_registro": [],
            "fecha_desde_hasta": pass_selected.get('fecha_de_caducidad', ''),
            "fecha_desde_visita": pass_selected.get('fecha_de_expedicion', ''),
            "grupo_areas_acceso": pass_selected.get('grupo_areas_acceso', []),
            "grupo_equipos": update_obj.get('grupo_equipos'),
            "grupo_instrucciones_pase": pass_selected.get('grupo_instrucciones_pase', []),
            "grupo_vehiculos": update_obj.get('grupo_vehiculos'),
            "link": {
                "creado_por_email": update_obj.get('user_email', ''),
                "docs": [],
                "creado_por_id": pass_selected.get('visita_a', '')[0].get('creado_por_id', ''),
                "link": pass_selected.get('link', ''),
                "qr_code": pass_selected.get('_id', '')
            },
            "nombre_pase": pass_selected.get('nombre', ''),
            "perfil_pase": pass_selected.get('tipo_de_pase', ''),
            "qr_pase": pass_selected.get('qr_pase', []),
            "status_pase": pass_selected.get('estatus', ''),
            "telefono_pase": pass_selected.get('telefono', ''),
            "tema_cita": pass_selected.get('tema_cita', ''),
            "tipo_visita": 'alta_de_nuevo_visitante',
            "tipo_visita_pase": tipo_visita_pase,
            "ubicacion": pass_selected.get('ubicacion', ''),
            "visita_a": pass_selected.get('visita_a')[0].get('nombre'),
            "walkin_fotografia": update_obj.get('foto', []),
            "walkin_identificacion": update_obj.get('identificacion', []),
            "archivo_invitacion": [],
        }

        location = access_pass.get('ubicacion', '')

        answers = {}
        perfil_pase = access_pass.get('perfil_pase', 'Visita General')
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        timezone = user_data.get('timezone','America/Monterrey')
        now_datetime =self.today_str(timezone, date_format='datetime')
        answers[self.mf['grupo_visitados']] = []
        answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {}
        answers[self.Location.UBICACIONES_CAT_OBJ_ID][self.f['location']] = location
        answers[self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID] = {}
        answers[self.CONFIG_PERFILES_OBJ_ID] = {}
        answers[self.VISITA_AUTORIZADA_CAT_OBJ_ID] = {}

        cont = 0
        for key, value in access_pass.items():
            cont += 1
            if key == 'grupo_vehiculos':
                vehiculos = access_pass.get('grupo_vehiculos',[])
                if vehiculos:
                    list_vehiculos = []
                    for item in vehiculos:
                        tipo = item.get('tipo_vehiculo','')
                        marca = item.get('marca_vehiculo','')
                        modelo = item.get('modelo_vehiculo','')
                        estado = item.get('nombre_estado','')
                        placas = item.get('placas_vehiculo','')
                        color = item.get('color_vehiculo','')
                        list_vehiculos.append({
                            self.AF.TIPO_DE_VEHICULO_OBJ_ID:{
                                self.mf['tipo_vehiculo']:tipo,
                                self.mf['marca_vehiculo']:marca,
                                self.mf['modelo_vehiculo']:modelo,
                            },
                            self.ESTADO_OBJ_ID:{
                                self.mf['nombre_estado']:estado,
                            },
                            self.mf['placas_vehiculo']:placas,
                            self.mf['color_vehiculo']:color,
                        })
                    answers[self.mf['grupo_vehiculos']] = list_vehiculos  
            elif key == 'grupo_equipos':
                equipos = access_pass.get('grupo_equipos',[])
                if equipos:
                    list_equipos = []
                    for item in equipos:
                        tipo = item.get('tipo_equipo','').lower().replace(' ', '_')
                        nombre = item.get('nombre_articulo','')
                        marca = item.get('marca_articulo','')
                        modelo = item.get('modelo_articulo','')
                        color = item.get('color_articulo','')
                        serie = item.get('numero_serie','')
                        list_equipos.append({
                            self.mf['tipo_equipo']:tipo,
                            self.mf['nombre_articulo']:nombre,
                            self.mf['marca_articulo']:marca,
                            self.mf['modelo_articulo']:modelo,
                            self.mf['color_articulo']:color,
                            self.mf['numero_serie']:serie,
                        })
                    answers[self.mf['grupo_equipos']] = list_equipos
            elif key == 'grupo_instrucciones_pase':
                acciones = access_pass.get('grupo_instrucciones_pase',[])
                if acciones:
                    acciones_list = []
                    for c in acciones:
                        acciones_list.append(
                            {
                                self.pase_entrada_fields['tipo_comentario']:c.get('tipo_de_comentario').lower(),
                                self.pase_entrada_fields['comentario_pase'] :c.get('comentario_pase')
                            }
                        )
                    answers.update({self.pase_entrada_fields['grupo_instrucciones_pase']:acciones_list})
            elif key == 'grupo_areas_acceso':
                acciones = access_pass.get('grupo_areas_acceso',[])
                if acciones:
                    acciones_list = []
                    for c in acciones:
                        acciones_list.append(
                            {
                                self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID : {
                                    self.pase_entrada_fields['nombre_area']:c.get('nombre_area')
                                } ,
                                self.pase_entrada_fields['commentario_area'] :c.get('commentario_area')
                            }
                        )
                    answers.update({self.pase_entrada_fields['grupo_areas_acceso']:acciones_list})
            elif key == 'autorizado_por':
                answers[self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID] = {
                    self.mf['nombre_guardia_apoyo'] : access_pass.get('autorizado_por', ''),
                }
            elif key == 'link':
                link_info=access_pass.get('link', '')
                if link_info:
                    docs=""
                    for index, d in enumerate(link_info["docs"]): 
                        if(d == "agregarIdentificacion"):
                            docs+="iden"
                        elif(d == "agregarFoto"):
                            docs+="foto"
                        if index==0 :
                            docs+="-"
                    link_pass= f"{link_info['link']}"
                answers.update({f"{self.pase_entrada_fields[key]}":link_pass}) 
            elif key == 'ubicacion':
                answers[self.pase_entrada_fields['ubicacion_cat']] = {self.mf['ubicacion']:access_pass['ubicacion']}
            elif key == 'visita_a': 
                answers[self.mf['grupo_visitados']] = []
                visita_a = access_pass.get('visita_a')
                visita_set = {
                    self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID:{
                        self.mf['nombre_empleado'] : visita_a,
                        }
                    }
                options_vistia = {
                      "group_level": 3,
                      "startkey": [location, visita_a],
                      "endkey": [location, f"{visita_a}\n",{}],
                    }
                cat_visita = self.catalogo_view(self.Employee.CONF_AREA_EMPLEADOS_CAT_ID, self.PASE_ENTRADA, options_vistia)
                if len(cat_visita) > 0:
                    cat_visita =  {key: [value,] for key, value in cat_visita[0].items() if value}
                visita_set[self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID].update(cat_visita)
                answers[self.mf['grupo_visitados']].append(visita_set)
            elif key == 'perfil_pase':
                answers[self.CONFIG_PERFILES_OBJ_ID] = {}
                answers[self.CONFIG_PERFILES_OBJ_ID] = {
                    self.mf['nombre_perfil'] : perfil_pase,
                }
                options = {
                      "group_level": 2,
                      "startkey": [perfil_pase],
                      "endkey": [f"{perfil_pase}\n",{}],
                    }
                cat_perfil = self.catalogo_view(self.CONFIG_PERFILES_ID, self.PASE_ENTRADA, options)
                if len(cat_perfil) > 0:
                    cat_perfil[0][self.mf['motivo']]= [cat_perfil[0].get(self.mf['motivo'])]
                    cat_perfil = cat_perfil[0]
                answers[self.CONFIG_PERFILES_OBJ_ID].update(cat_perfil)
                if answers[self.CONFIG_PERFILES_OBJ_ID].get(self.mf['nombre_permiso']) and \
                   type(answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']]) == str:
                    answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']] = [answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']],]
            elif key == 'archivo_invitacion':
                # id_forma = 121736
                id_forma = self.PASE_ENTRADA
                # id_campo = '673773741b2adb2d05d99d63'
                id_campo = self.pase_entrada_fields['archivo_invitacion']
                tema_cita = access_pass.get("tema_cita")
                descripcion = access_pass.get("descripcion")
                fecha_desde_visita = access_pass.get("fecha_desde_visita")
                fecha_desde_hasta = access_pass.get("fecha_desde_hasta")
                creado_por_email = access_pass.get("link", {}).get("creado_por_email")
                ubicacion = access_pass.get("ubicacion",'')
                nombre = access_pass.get("nombre_pase",'')
                visita_a = access_pass.get("visita_a",'')
                email = access_pass.get("email_pase",'')

                start_datetime = datetime.strptime(fecha_desde_visita, "%Y-%m-%d %H:%M:%S")

                if not fecha_desde_hasta:
                    stop_datetime = start_datetime + timedelta(hours=1)
                else:
                    stop_datetime = datetime.strptime(fecha_desde_hasta, "%Y-%m-%d %H:%M:%S")

                meeting = [
                    {
                        "id": 1,
                        "start": start_datetime,
                        "stop": stop_datetime,
                        "name": tema_cita,
                        "description": descripcion,
                        "location": ubicacion,
                        "allday": False,
                        "rrule": None,
                        "alarm_ids": [{"interval": "minutes", "duration": 10, "name": "Reminder"}],
                        'organizer_name': visita_a,
                        'organizer_email': creado_por_email,
                        "attendee_ids": [{"email": email, "nombre": nombre}, {"email": creado_por_email, "nombre": visita_a}],
                    }
                ]
                respuesta_ics = self.upload_ics(id_forma, id_campo, meetings=meeting)
                file_name = respuesta_ics.get('file_name', '')
                file_url = respuesta_ics.get('file_url', '')

                archivo_invitacion= [
                    {
                        "file_name": f"{file_name}",
                        "file_url": f"{file_url}"
                    }
                ]
                answers.update({f"{self.pase_entrada_fields[key]}": archivo_invitacion})
            else:
                answers.update({f"{self.pase_entrada_fields[key]}":value})

        if answers or folio:
            metadata = self.lkf_api.get_metadata(form_id=self.PASE_ENTRADA)
            metadata.update(self.get_record_by_folio(folio, self.PASE_ENTRADA, select_columns={'_id':1}, limit=1))

            metadata.update({
                    'properties': {
                        "device_properties":{
                            "system": "Addons",
                            "process":"Actualizacion de Pase de Entrada", 
                            "accion":'update_full_pass', 
                            "folio": folio, 
                            "archive": "pase_acceso.py"
                        }
                    },
                    'answers': answers,
                    '_id': qr_code
                })
            res= self.net.patch_forms_answers(metadata)
            return res
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_pass_status(self):
        query_update = {}
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        timezone = user_data.get('timezone','America/Monterrey')
        today = self.today_str(tz_name=timezone, date_format="datetime")
        query_update = {
            "$and": [{
                "$or":[{
                    f"answers.{self.pase_entrada_fields['fecha_desde_visita']}":{
                        "$lte":today
                        }
                    },
                    {
                        f"answers.{self.pase_entrada_fields['fecha_desde_hasta']}":{
                            "$lte":today
                        },
                    }
                ]
                }]
            }
        records_ = self.search_pass_by_status('activo', query_update)
        records = [ObjectId(req["_id"]) for req in records_]
        update_query= {f"answers.{self.pase_entrada_fields['status_pase']}":"vencido"}
        # return self.cr.update_many({
        #         'form_id':self.PASE_ENTRADA,
        #         'deleted_at':{'$exists':False},
        #         '_id':{
        #             "$in":records
        #         }
        #     }, {"$set": update_query})
    
        res = self.cr.update_many({
                'form_id':self.PASE_ENTRADA,
                'deleted_at':{'$exists':False},
                '_id':{
                    "$in":records
                }
            }, {"$set": update_query})
        
        return res.matched_count
        # print("records=",stop)

    def update_paquete(self, data_paquete_actualizar, folio):
        answers = {}
        for key, value in data_paquete_actualizar.items():
            if  key == 'area_paqueteria':
                answers[self.paquetes_fields['area_paqueteria']] = value
            elif key == 'ubicacion_paqueteria':
                answers[self.paquetes_fields['ubicacion_paqueteria']] = value
            elif key == 'quien_recibe_paqueteria':
                answers[self.paquetes_fields['quien_recibe_catalogo']] = {self.paquetes_fields['quien_recibe_paqueteria']:value}
            else:
                answers.update({f"{self.paquetes_fields[key]}":value})
        if answers or folio:
            return self.lkf_api.patch_multi_record( answers = answers, form_id=self.PAQUETERIA, folios=[folio])
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def validate_access_pass_location(self, qr_code, location):
        #TODO
        last_move = self.get_last_user_move(qr_code, location)
        if self.user_in_facility(last_move.get('status_visita')):
            return True
        return False

    def validate_certificados(self, qr_code, location):
        # Valida los certificados del pase de acceso.
        return True

    def validate_pass_dates(self, access_pass):
        # Valida las fechas del pase de acceso
        return True

    def validate_value_id(self, qr_code):
        try:
            ObjectId(qr_code)
            return True
        except Exception as e:
            return False

    def vehiculo_tipo(self):
        return self.catalogo_vehiculos()
    
    def vehiculo_marca(self, tipo):
        options = {
            'startkey': [tipo,],
            'endkey': [f"{tipo}\n",{}],
            'group_level':2
        }
        return self.catalogo_vehiculos(options)

    def vehiculo_modelo(self, tipo, marca):
        options = {
            'startkey': [tipo,marca],
            'endkey': [f"{tipo}, {marca}\n",{}],
            'group_level':3
        }
        return self.catalogo_vehiculos(options)

    def visita_a(self, location):
        form_id = self.PASE_ENTRADA
        catalog_id = self.Employee.CONF_AREA_EMPLEADOS_CAT_ID
        options = {
            'startkey': [location],
            'endkey': [f"{location}\n",{}],
            'group_level':2
        }
        return self.catalogo_view(catalog_id, form_id, options)

    def visita_a_detail(self, location, visita_a):
        form_id = self.PASE_ENTRADA
        catalog_id = self.Employee.CONF_AREA_EMPLEADOS_CAT_ID
        options = {
            'startkey': [location, visita_a],
            'endkey': [location,f"{visita_a}\n",{}],
            'group_level':3
        }
        return self.catalogo_view(catalog_id, form_id, options, detail=True)
    
    def send_email_and_sms(self, data):
        answers = {}
        phone_to = data['phone_to']
        mensaje = data['mensaje']
        titulo = 'Aviso desde Soter - Accesos'

        metadata = self.lkf_api.get_metadata(form_id=self.ENVIO_DE_CORREOS)
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Addons",
                    "Process": "Creación de envio de correo",
                    "Action": "send_email_and_sms",
                }
            },
        })

        #---Define Answers
        answers.update({
            f"{self.envio_correo_fields['email_from']}": data['email_from'],
            f"{self.envio_correo_fields['titulo']}": titulo,
            f"{self.envio_correo_fields['nombre']}": data['nombre'],
            f"{self.envio_correo_fields['email_to']}": data['email_to'],
            f"{self.envio_correo_fields['msj']}": mensaje,
            f"{self.envio_correo_fields['enviado_desde']}": 'Accesos Aviso',
        })

        metadata.update({'answers': answers})

        email_status = 'Correo: No se realizo la peticion.'
        email_response = self.lkf_api.post_forms_answers(metadata)
        if email_response.get('status_code') == 201:
            email_status = 'Correo: Enviado correctamente'
        else:
            email_status = 'Correo: Hubo un error...'

        message_status = 'Mensaje: No se realizo la peticion.'
        if phone_to:
            #TODO: Cambiar a nuevo proveedor de envio de sms
            sms_response = self.lkf_api.send_sms(phone_to, mensaje, use_api_key=True)
            if hasattr(sms_response, "status") and sms_response.status in ["queued", "sent", "delivered"]:
                message_status = 'Mensaje: Enviado correctamente'
            else:
                message_status = 'Mensaje: Hubo un error...'
        
        return {
            "email_status": email_status,
            "message_status": message_status
        }

    def create_class_google_wallet(self, data, qr_code):
        ISSUER_ID = '3388000000022924601'
        CLASS_ID = f'{ISSUER_ID}.ProdPassClass'

        google_wallet_creds = self.lkf_api.get_user_google_wallet(use_api_key=True, jwt_settings_key=False)
        QR_CODE_VALUE = qr_code
        OBJECT_ID = f'{ISSUER_ID}.pase-entrada-{QR_CODE_VALUE}-{uuid.uuid4()}'

        credentials_data = google_wallet_creds.get('data', {})
        private_key = credentials_data.get('private_key')
        client_email = credentials_data.get('client_email')

        credentials = service_account.Credentials.from_service_account_info(
            credentials_data,
            scopes=['https://www.googleapis.com/auth/wallet_object.issuer']
        )

        auth_req = Request()
        credentials.refresh(auth_req)
        access_token = credentials.token

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        class_url = f'https://walletobjects.googleapis.com/walletobjects/v1/genericClass/{CLASS_ID}'
        class_check = requests.get(class_url, headers={'Authorization': f'Bearer {access_token}'})

        if class_check.status_code != 200:
            class_body = {
                "id": CLASS_ID,
            }
            response = requests.post(
                'https://walletobjects.googleapis.com/walletobjects/v1/genericClass',
                headers=headers,
                json=class_body
            )
            print("Status code:", response.status_code)
            print("Response text:", response.text)

        response = self.create_pass_google_wallet(OBJECT_ID, CLASS_ID, QR_CODE_VALUE, data, headers, client_email, private_key)
        return response

    def create_pass_google_wallet(self, object_id, class_id, qr_code, data, headers, client_email, private_key):
        ubicaciones_list = data.get('ubicaciones', [])
        format_ubicacion = self.format_ubicaciones_to_google_pass(ubicaciones_list)
        visita_a_list = data.get('visita_a', [])
        format_visita_a = self.format_ubicaciones_to_google_pass(visita_a_list)
        empresa = data.get('empresa', 'Sin especificar')
        num_accesos = data.get('num_accesos', 1)
        fecha_desde = data.get('fecha_desde', '')
        fecha_hasta = data.get('fecha_hasta', '')
        geolocations = data.get('geolocations', [])
        if not fecha_hasta:
            fecha_hasta = fecha_desde

        object_body = {
            "id": object_id,
            "classId": class_id,
            "state": "ACTIVE",
            "genericType": "GENERIC_TYPE_UNSPECIFIED",
            "cardTitle": {
                "defaultValue": {
                    "language": "es-MX",
                    "value": empresa
                }
            },
            "subheader": {
                "defaultValue": {
                    "language": "es-MX",
                    "value": 'Pase de Entrada'
                }
            },
            "header": {
                "defaultValue": {
                    "language": "es-MX",
                    "value": f'Visita a: {format_visita_a}'
                }
            },
            'logo': {
                'sourceUri': {
                    'uri':
                        'https://f001.backblazeb2.com/file/app-linkaform/public-client-126/71202/60b81349bde5588acca320e1/698b8b36e216075bd8f4597a.png'
                },
                'contentDescription': {
                    'defaultValue': {
                        'language': 'en-US',
                        'value': 'Generic card logo'
                    }
                }
            },
            "hexBackgroundColor": "#FFFFFF",
            "groupingInfo": {
                "sortIndex": 1,
                "groupingId": "pase_de_entrada",
            },
            "textModulesData": [
                {
                    "id": "ubicacion",
                    "header": "UBICACION",
                    "body": format_ubicacion
                },
                {
                    "id": "fecha_entrada",
                    "header": "FECHA DESDE",
                    "body": fecha_desde
                },
                {
                    "id": "fecha_salida",
                    "header": "FECHA HASTA",
                    "body": fecha_hasta
                },
                {
                    "id": "accesos",
                    "header": "ACCESOS",
                    "body": num_accesos
                },
                {
                    "id": "vehiculos",
                    "header": "",
                    "body": ""
                },
                {
                    "id": "equipos",
                    "header": "",
                    "body": ""
                }
            ],
            "barcode": {
                "type": "QR_CODE",
                "value": qr_code,
                "alternateText": "Muestra tu QR para ingresar"
            },
        }

        if geolocations:
            object_body['linksModuleData'] = {
                "uris": [
                    {
                        "kind": "walletobjects#uri",
                        "uri": f"https://www.google.com/maps/dir/?api=1&destination={value['latitude']},{value['longitude']}",
                        "description": f"Cómo llegar a {key}",
                        "id": f"direcciones_{key}"
                    }
                    for key, value in geolocations.items()
                ]
            }

        requests.post(
            'https://walletobjects.googleapis.com/walletobjects/v1/genericObject',
            headers=headers,
            json=object_body
        )

        jwt_payload = {
            "iss": client_email,
            "aud": "google",
            "origins": [],
            "typ": "savetowallet",
            "payload": {
                "genericObjects": [
                    {"id": object_id}
                ]
            }
        }
        signed_jwt = jwt.encode(jwt_payload, private_key, algorithm='RS256')
        save_url = f'https://pay.google.com/gp/v/save/{signed_jwt}'
        print('Agrega tu pase con este link:', save_url)
        return save_url

    def assign_google_pass_url(self, qr_code, google_wallet_pass_url):
        answers = {}
        answers[self.pase_entrada_fields['google_wallet_pass_url']] = google_wallet_pass_url
        response = self.lkf_api.patch_multi_record(answers=answers, form_id=self.PASE_ENTRADA, record_id=[qr_code,])
        return response

    def format_ubicaciones_to_google_pass(self, ubicaciones_list):
        if not ubicaciones_list:
            return ''
        if len(ubicaciones_list) == 1:
            return self.unlist(ubicaciones_list)
        if len(ubicaciones_list) == 2:
            return f"{ubicaciones_list[0]} y {ubicaciones_list[1]}"
        return ', '.join(ubicaciones_list[:-1]) + ' y ' + ubicaciones_list[-1]

    def crear_pass_json(self, data):
        visita_a = data.get('visita_a')
        nombre = data.get('nombre')
        fecha = data.get('fecha')
        hora = data.get('hora')
        ubicaciones_list = data.get('ubicacion')
        format_ubicacion = self.format_ubicaciones_to_google_pass(ubicaciones_list)
        area = data.get('area')

        pass_data = {
            "generic": {
                "headerFields": [
                    {
                        "key": "welcome",
                        "label": "Folio:",
                        "value": "PE/2505/1272"
                    }
                ],
                "primaryFields": [
                    {
                        "key": "name",
                        "label": "",
                        "value": nombre
                    }
                ],
                "secondaryFields": [
                    {
                        "key": "date2",
                        "label": "Visita a:",
                        "value": visita_a
                    },
                    {
                        "key": "date3",
                        "label": "",
                        "value": ""
                    },
                    {
                        "key": "date",
                        "label": "Fecha",
                        "value": fecha
                    }
                ],
                "auxiliaryFields": [
                    {
                        "key": "ubication",
                        "label": f"Ubicación",
                        "value": format_ubicacion
                    },
                    {
                        "key": "area",
                        "label": "Área",
                        "value": area
                    },
                    {
                        "key": "hour",
                        "label": "Hora",
                        "value": hora
                    }
                ]
            }
        }

        temp = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.json')
        json.dump(pass_data, temp, ensure_ascii=False, indent=4)
        temp.seek(0)

        return temp.name

    def get_image_file(self, url):
        response = requests.get(url)
        response.raise_for_status()
        return io.BytesIO(response.content)

    def upload_zip(self, id_forma_seleccionada, id_field, zip_bytes, filename="archivo.zip"):
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, filename)

        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(zip_bytes)

        rb_file = open(temp_file_path, 'rb')
        dir_file = {'File': rb_file}

        try:
            upload_data = {'form_id': id_forma_seleccionada, 'field_id': id_field}
            upload_url = self.lkf_api.post_upload_file(data=upload_data, up_file=dir_file)
            rb_file.close()
        except Exception as e:
            rb_file.close()
            os.remove(temp_file_path)
            return {"error": "Fallo al subir el archivo"}

        try:
            file_url = upload_url['data']['file']
            update_file = {'file_name': filename, 'file_url': file_url}
        except KeyError:
            update_file = {"error": "Fallo al obtener la URL del archivo"}
        finally:
            os.remove(temp_file_path)

        return update_file

    def create_pass_apple_wallet(self, record_id):
        if not record_id:
            self.LKFException({'title': 'Error', 'msg': 'record_id es requerido'})

        access_pass = self.get_detail_access_pass(qr_code=record_id)
        file_url = ''
        if access_pass.get('apple_wallet_pass', []):
            for apple_pass in access_pass.get('apple_wallet_pass', []):
                file_url = apple_pass.get('file_url')
        else:
            fecha_completa = access_pass.get('fecha_de_caducidad', '')
            fecha, hora = fecha_completa.split(' ')
            hora_sin_segundos = hora[:5]
            foto_url = access_pass.get('foto', [])[0].get('file_url', '')

            data = {
                "qr_code": record_id,
                "nombre": access_pass.get('nombre'),
                "visita_a": access_pass.get('visita_a', [])[0].get('nombre', ''),
                "fecha": fecha,
                "hora": hora_sin_segundos,
                "ubicacion": access_pass.get('ubicaciones', []),
                "area": access_pass.get('area', 'Caseta Principal'),
            }

            pass_json_path = self.crear_pass_json(data)

            with open(pass_json_path, "r", encoding="utf-8") as f:
                pass_data = json.load(f)

            card_info = Generic()
            card_info.headerFields = [Field(**f) for f in pass_data.get("generic", {}).get("headerFields", [])]
            card_info.primaryFields = [Field(**f) for f in pass_data.get("generic", {}).get("primaryFields", [])]
            card_info.secondaryFields = [Field(**f) for f in pass_data.get("generic", {}).get("secondaryFields", [])]
            card_info.auxiliaryFields = [Field(**f) for f in pass_data.get("generic", {}).get("auxiliaryFields", [])]

            my_pass = MyPass(
                pass_information=card_info,
                pass_type_identifier="pass.com.soter.mx",
                organization_name="Soter",
                team_identifier="ME623A8A63",
            )

            my_pass.barcode = Barcode(message=record_id, format='qr', encoding='iso-8859-1', alt_text='')
            my_pass.serialNumber = str(uuid.uuid4())
            my_pass.description = "Pase de acceso"

            icon_url = "https://f001.backblazeb2.com/file/app-linkaform/public-client-126/68600/6076166dfd84fa7ea446b917/2025-05-08T08:28:17_1.png"
            logo_url = "https://f001.backblazeb2.com/file/app-linkaform/public-client-126/68600/6076166dfd84fa7ea446b917/2025-05-22T17:02:16_1.png"
            thumbnail_url = foto_url

            my_pass.add_file(name="icon.png", file_handle=self.get_image_file(icon_url))
            my_pass.add_file(name="logo.png", file_handle=self.get_image_file(logo_url))
            if thumbnail_url:
                my_pass.add_file(name="thumbnail.png", file_handle=self.get_image_file(thumbnail_url))

            # Material de certificado especifico de la cuenta (Apple Developer):
            # se lee de settings/config en vez de estar hardcodeado, ya que cada
            # cliente puede tener su propio certificado/appId de Apple Wallet.
            apple_wallet_config = self.settings.config.get('APPLE_WALLET', {})
            cert_string = apple_wallet_config.get('CERT', '')
            wwdr_string = apple_wallet_config.get('WWDR', '')
            soter_pass_string = apple_wallet_config.get('PRIVATE_KEY', '')
            key_pem_password = apple_wallet_config.get('PRIVATE_KEY_PASSWORD', '')

            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.pem') as cert_temp:
                cert_temp.write(cert_string)
                cert_temp_path = cert_temp.name

            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.pem') as wwdr_temp:
                wwdr_temp.write(wwdr_string)
                wwdr_temp_path = wwdr_temp.name

            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.pem') as soter_pass_key_temp:
                soter_pass_key_temp.write(soter_pass_string)
                soter_pass_key_temp_path = soter_pass_key_temp.name

            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_pkpass:
                pkpass_path = temp_pkpass.name

            my_pass.create(cert_temp_path, soter_pass_key_temp_path, wwdr_temp_path, key_pem_password, pkpass_path)

            with open(pkpass_path, "rb") as f:
                zip_bytes = f.read()

            id_forma_seleccionada = self.PASE_ENTRADA
            id_field = self.pase_entrada_fields['apple_wallet_pass']
            upload_result = self.upload_zip(id_forma_seleccionada, id_field, zip_bytes, filename="SoterApplePass.zip")
            file_url = upload_result.get('file_url')

            data = {
                'apple_wallet_pass': [
                    {
                        'file_name': upload_result.get('file_name'),
                        'file_url': file_url
                    }
                ]
            }

            self.update_pass(access_pass=data, folio=record_id)
        return file_url

    def upload_pdf_as_image(self, id_forma_seleccionada, id_field, pdf_url, convert_all=False):
        # 1. Descargar PDF desde la URL
        try:
            response = requests.get(pdf_url)
            response.raise_for_status()
        except Exception as e:
            print("Error al descargar el PDF:", e)
            return {"error": "Fallo al descargar el PDF"}

        # 2. Convertir PDF a imágenes
        try:
            images = convert_from_bytes(response.content, dpi=150)
        except Exception as e:
            print("Error al convertir el PDF:", e)
            return {"error": "Fallo al convertir el PDF"}

        temp_dir = tempfile.gettempdir()

        if convert_all and len(images) > 1:
            # 3a. Guardar todas las imágenes en un archivo ZIP
            zip_path = os.path.join(temp_dir, "converted_images.zip")
            with ZipFile(zip_path, 'w') as zipf:
                for i, img in enumerate(images):
                    img_path = os.path.join(temp_dir, f"page_{i+1}.png")
                    img.save(img_path, "PNG")
                    zipf.write(img_path, arcname=f"page_{i+1}.png")
                    os.remove(img_path)
            file_to_upload_path = zip_path
            filename = "converted_images.zip"
        else:
            # 3b. Guardar solo la primera imagen como PNG
            img_path = os.path.join(temp_dir, "converted_image.png")
            images[0].save(img_path, "PNG")
            file_to_upload_path = img_path
            filename = "converted_image.png"

        rb_file = open(file_to_upload_path, 'rb')
        dir_file = {'File': rb_file}

        try:
            upload_data = {'form_id': id_forma_seleccionada, 'field_id': id_field}
            upload_url = self.lkf_api.post_upload_file(data=upload_data, up_file=dir_file)
            rb_file.close()
        except Exception as e:
            rb_file.close()
            os.remove(file_to_upload_path)
            print("Error al subir el archivo:", e)
            return {"error": "Fallo al subir el archivo"}

        try:
            file_url = upload_url['data']['file']
            update_file = {'file_name': filename, 'file_url': file_url}
        except KeyError:
            print('No se pudo obtener la URL del archivo')
            update_file = {"error": "Fallo al obtener la URL del archivo"}
        finally:
            os.remove(file_to_upload_path)

        return update_file

    # ──────────────────────────────────────────────────────────
    # HELPERS DE OCR (usados por OcrMixin.ocr_paquete)
    # ──────────────────────────────────────────────────────────

    def get_employees_names(self):
        """
        Lista de nombres de empleados, usada por ocr_paquete para matchear el
        remitente leído en la etiqueta contra empleados existentes.
        """
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.Employee.EMPLEADOS,
            }},
            {"$project": {"_id": 0, "value": f"$answers.{self.f['nombre_empleado']}"}},
        ]
        data = self.format_cr(self.cr.aggregate(query))
        return list({item.get('value') for item in data if item.get('value')})

    def get_proveedores_paqueteria(self):
        """
        Obtiene los proveedores de paquetería de la FORMA de PROVEEDORES.
        """
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.PROVEEDORES_FORM,
                f"answers.{self.f['tipo_de_proveedor']}": "paqueteria"
            }},
            {"$project": {
                "_id": 0,
                "nombre_proveedor": f"$answers.{self.f['nombre_comercial']}"
            }}
        ]
        data = self.format_cr(self.cr.aggregate(query))
        format_data = []
        if data:
            format_data = {i.get('nombre_proveedor') for i in data}
            format_data = list(format_data)
        return format_data

    def create_proveedor_de_paqueteria(self, proveedor):
        metadata = self.lkf_api.get_metadata(form_id=self.PROVEEDORES_FORM)
        metadata.update({
            'properties': {
                'device_properties': {
                    'System': 'Sanic App',
                    'Module': 'Accesos',
                    'Process': 'OCR Paqueteria',
                    'Action': 'create_proveedor_de_paqueteria',
                    'File': 'lkf_addons/accesos/service.py',
                }
            },
            'answers': {
                self.f['nombre_comercial']: proveedor,
                self.f['razon_social']: proveedor,
                self.f['tipo_de_proveedor']: 'paqueteria',
            }
        })
        res = self.lkf_api.post_forms_answers(metadata)
        if res.get('status_code') not in [200, 201, 202]:
            self.LKFException({"title": "Error en crear proveedor de paqueteria", "msg": "No se pudo crear correctamente el registro."})
        return res

    # ──────────────────────────────────────────────────────────
    # OCR — equipo / persona / vehículo / camión / artículo concesionado
    # (migrado de lkf-addons: modules/accesos/items/scripts/Accesos/ocr_docs.py)
    # ──────────────────────────────────────────────────────────

    def ocr_equipo(self, image_source,
                   extra_instructions: str = None,
                   model: str = 'google/gemini-2.5-flash-lite') -> dict:
        """
        Extrae los datos de una foto de un equipo/herramienta:
        tipo, marca, modelo, número de serie y color.

        Args:
            image_source: URL remota, ruta local, o lista de imágenes.
            model:        Modelo OpenRouter a usar.

        Returns:
            dict con:
                - status_code : 200 OK / 206 advertencias / 400 config / 500 error
                - data        : campos extraídos
                - msg         : mensaje de resultado
        """
        if not self.ai:
            return {'status_code': 400, 'msg': 'OpenRouter no configurado'}

        system = (
            "You are an asset identification specialist trained to analyze images "
            "of equipment, tools, computers, tablets, and electronic devices. "
            "You extract identifying information such as brand, model, serial number, "
            "and color from photographs. "
            "Always respond with a single valid JSON object and nothing else — "
            "no markdown, no backticks, no explanation, no preamble."
        )

        prompt = (
            "Analyze the provided image and extract all visible identifying information "
            "about the equipment or device shown. "
            "If a field cannot be determined from the image, use null. "
            "\n\n"
            "Return ONLY a JSON object with this exact structure:\n"
            "{\n"
            '  "tipo": "string — MUST be exactly one of: herramienta, computadora, equipo de limpieza, escalera, impresora, monitor, tablet, otro. No other values allowed.",\n'
            '  "marca": "string — brand name visible on the device (Apple, Dell, HP, Lenovo, Samsung, Makita, Dewalt, etc.), or null",\n'
            '  "modelo": "string — model name or number if visible (e.g. MacBook Pro, ThinkPad X1, iPad Pro, etc.), or null",\n'
            '  "num_serie": "string — serial number exactly as visible on label or sticker, or null",\n'
            '  "color": "string — MUST be exactly one of: Amarillo, Azul, Beige, Blanco, Cafe, Crema, Dorado, Gris, Morado, Naranja, Negro, Plateado, Rojo, Rosa, Verde, Violeta, Otro. Pick the closest match.",\n'
            '  "observaciones": "string — any notable features, damage, stickers, or distinguishing marks, or null",\n'
            '  "confianza": "string — alto / medio / bajo — overall confidence based on image clarity"\n'
            "}"
        )

        if extra_instructions:
            prompt += f"\n\nAdditional instructions: {extra_instructions}"

        # Sanitizar image_source
        if isinstance(image_source, str):
            image_source = [image_source]
        elif isinstance(image_source, list):
            image_source = [
                img['file_url'] if isinstance(img, dict) else img
                for img in image_source
            ]

        raw_text = self.ai.ocr_general(image_source, system, prompt, model=model, max_tokens=1000)

        datos = {}
        if raw_text.get('choices'):
            choices = raw_text['choices']
            if isinstance(choices, list) and len(choices) > 0:
                content = choices[0].get('message', {}).get('content')
                if content:
                    datos = content

        datos = self._ocr_normalizar(datos)

        errores = self._ocr_validar_id(datos)
        if errores:
            return {
                'status_code': 206,
                'msg': 'Extracción con advertencias',
                'data': datos,
                'warnings': errores,
            }

        return {'status_code': datos.get('status_code', 200), 'msg': 'OK', 'data': datos}

    def ocr_persona(self, image_source,
                    extra_instructions: str = None,
                    model: str = 'google/gemini-2.5-flash-lite') -> dict:
        """
        Analiza una foto para detectar si hay una persona visible
        y extrae sus características físicas descriptivas.

        Args:
            image_source: URL remota, ruta local, o lista de imágenes.
            model:        Modelo OpenRouter a usar.

        Returns:
            dict con:
                - status_code : 200 OK / 206 advertencias / 400 config / 500 error
                - data        : campos extraídos
                - msg         : mensaje de resultado
        """
        if not self.ai:
            return {'status_code': 400, 'msg': 'OpenRouter no configurado'}

        system = (
            "You are a security system specialist trained to analyze images "
            "and determine whether a person is present, and describe their "
            "visible physical characteristics for identification purposes. "
            "You are objective and descriptive. Never make assumptions about "
            "identity, ethnicity, or personal data beyond what is visually evident. "
            "Always respond with a single valid JSON object and nothing else — "
            "no markdown, no backticks, no explanation, no preamble."
        )

        prompt = (
            "Analyze the provided image and determine if a person is visible. "
            "If a person is present, extract all visible physical characteristics. "
            "If no person is detected, return es_persona: false and all other fields as null. "
            "\n\n"
            "Return ONLY a JSON object with this exact structure:\n"
            "{\n"
            '  "es_persona": true,\n'
            '  "cantidad_personas": "integer — number of people visible in the image",\n'
            '  "rostro_visible": "boolean — true if face is clearly visible",\n'
            '  "genero_aparente": "string — masculino / femenino / no determinado",\n'
            '  "edad_estimada": "string — estimated age range e.g. 20-30",\n'
            '  "complexion": "string — delgado / normal / robusto / corpulento",\n'
            '  "estatura_estimada": "string — bajo / mediano / alto based on context clues",\n'
            '  "color_piel": "string — descriptive skin tone in Spanish",\n'
            '  "color_cabello": "string — hair color in Spanish, or null if not visible",\n'
            '  "tipo_cabello": "string — corto / mediano / largo / calvo, or null",\n'
            '  "color_ojos": "string — eye color if visible, else null",\n'
            '  "rasgos_faciales": "string — notable facial features: beard, glasses, mustache, etc., or null",\n'
            '  "ropa_superior": "string — describe upper garment color and type, or null",\n'
            '  "ropa_inferior": "string — describe lower garment color and type, or null",\n'
            '  "accesorios": "string — hat, backpack, bag, jewelry, or null",\n'
            '  "postura": "string — de pie / sentado / en movimiento / acostado, or null",\n'
            '  "calidad_imagen": "string — buena / regular / mala",\n'
            '  "observaciones": "string — anything unusual, suspicious behavior, or notable context",\n'
            '  "confianza": "string — alto / medio / bajo"\n'
            "}"
        )

        if extra_instructions:
            prompt += f"\n\nAdditional instructions: {extra_instructions}"

        # Sanitizar image_source
        if isinstance(image_source, str):
            image_source = [image_source]
        elif isinstance(image_source, list):
            image_source = [
                img['file_url'] if isinstance(img, dict) else img
                for img in image_source
            ]

        raw_text = self.ai.ocr_general(image_source, system, prompt, model=model, max_tokens=1000)

        datos = {}
        if raw_text.get('choices'):
            choices = raw_text['choices']
            if isinstance(choices, list) and len(choices) > 0:
                content = choices[0].get('message', {}).get('content')
                if content:
                    datos = content

        datos = self._ocr_normalizar(datos)

        errores = self._ocr_validar_id(datos)
        if errores:
            return {
                'status_code': 206,
                'msg': 'Extracción con advertencias',
                'data': datos,
                'warnings': errores,
            }

        return {'status_code': datos.get('status_code', 200), 'msg': 'OK', 'data': datos}

    def ocr_vehiculo(self, image_source, fields: dict = {},
                     extra_instructions: str = None,
                     model: str = 'google/gemini-2.5-flash-lite') -> dict:
        """
        Extrae los datos de una foto de un vehículo:
        tipo, marca, modelo, año estimado, color, placas,
        número económico, condición y observaciones.

        Args:
            image_source:        URL remota, ruta local, o lista de imágenes del vehículo.
            fields:              Campos adicionales a extraer (opcional).
            extra_instructions:  Instrucciones extra al modelo (opcional).
            model:               Modelo OpenRouter a usar.

        Returns:
            dict con:
                - status_code : 200 OK / 206 advertencias / 400 config / 500 error
                - data        : campos extraídos
                - msg         : mensaje de resultado
        """
        if not self.ai:
            return {'status_code': 400, 'msg': 'OpenRouter no configurado'}

        system = (
            "You are a vehicle identification specialist with expertise in "
            "reading license plates, identifying car makes and models, and "
            "assessing vehicle condition from photographs. "
            "You analyze images of cars, trucks, motorcycles, and commercial vehicles. "
            "Always respond with a single valid JSON object and nothing else — "
            "no markdown, no backticks, no explanation, no preamble."
        )

        prompt = (
            "Analyze all provided vehicle images as a single combined inspection. "
            "Images may show: front, sides, rear, license plate close-ups, or interior. "
            "All inputs refer to ONE vehicle. Extract every available field. "
            "If a field cannot be determined from the provided material, use null. "
            "\n\n"
            "Return ONLY a JSON object with this exact structure:\n"
            "{\n"
            '  "tipo_vehiculo": "string — MUST be exactly one of: pick up, camión, bicicleta, remolque, moto, van, autobús, trailer, automóvil. No other values allowed.",\n'
            '  "marca": "string — vehicle brand (Toyota, Ford, Nissan, Chevrolet, Honda, Kia, etc.)",\n'
            '  "modelo": "string — vehicle model name (Corolla, F-150, Sentra, Aveo, etc.)",\n'
            '  "color_principal": "string — MUST be exactly one of: Amarillo, Azul, Beige, Blanco, Cafe, Crema, Dorado, Gris, Morado, Naranja, Negro, Plateado, Rojo, Rosa, Verde, Violeta, Otro. No other values allowed. Pick the closest match.",\n'
            '  "placa": "string — license plate number exactly as visible, preserving spacing/hyphens",\n'
            '  "estado_placa": "string — Mexican state or country of the plate if identifiable",\n'
            '  "num_serie_vin": "string — VIN or chassis number if visible (e.g. on windshield sticker), else null",\n'
            '  "condicion": "string — bueno / regular / malo — overall visible condition of the vehicle",\n'
            '  "danios_visibles": "string — describe any dents, scratches, broken parts, or damage, else null",\n'
            '  "observaciones": "string — small description, any notable features, modifications, stickers, cargo, or distinguishing marks",\n'
            '  "confianza": "string — alto / medio / bajo — overall confidence based on image clarity and angle"\n'
            "}"
        )

        if extra_instructions:
            prompt += f"\n\nAdditional instructions: {extra_instructions}"
        # 1. Sanitizar image_source — asegurar que sea lista de strings
        if isinstance(image_source, str):
            image_source = [image_source]
        elif isinstance(image_source, list):
            image_source = [
                img['file_url'] if isinstance(img, dict) else img
                for img in image_source
            ]
        # 1. Llamar al LLM
        raw_text = self.ai.ocr_general(image_source, system, prompt, model=model, max_tokens=1000)

        # 2. Extraer el contenido de texto
        datos = {}
        if raw_text.get('choices'):
            choices = raw_text['choices']
            if isinstance(choices, list) and len(choices) > 0:
                content = choices[0].get('message', {}).get('content')
                if content:
                    datos = content

        # 3. Normalizar (limpia markdown fences, parsea JSON, etc.)
        datos = self._ocr_normalizar(datos)

        # 4. Validar campos básicos
        errores = self._ocr_validar_id(datos)
        if errores:
            return {
                'status_code': 206,
                'msg': 'Extracción con advertencias',
                'data': datos,
                'warnings': errores,
            }

        return {'status_code': datos.get('status_code', 200), 'msg': 'OK', 'data': datos}

    def ocr_truck(self, image_source: list, fields: dict = {},
                           extra_instructions: str = None,
                           model: str = 'google/gemini-2.5-flash-lite') -> dict:
        """
        Extrae los datos de una foto de un camión/transporte en caseta:
        vehículo, remolques/contenedores, inspección de 17 puntos (tractor)
        e inspección de 7 puntos (contenedor).

        Args:
            image_source: URL remota, ruta local, o lista de imágenes/PDFs.
            model:        Modelo OpenRouter a usar (opcional).

        Returns:
            dict con:
                - status_code: 200/206/400/500
                - data: campos extraídos por el OCR
                - msg: mensaje de resultado
        """
        system = (
            "You are a certified security guard and heavy transport specialist at a manufacturing plant. "
            "Your role is to process inbound and outbound truck check-ins following CTPAT compliance standards. "
            "You specialize in identifying all types of commercial vehicles, reading transport documents, "
            "driver IDs, bills of lading, and cargo manifests. "
            "Always respond with a single valid JSON object and nothing else — no markdown, no explanation, no preamble."
        )

        prompt = (
            "Analyze all provided images and/or PDF documents as a single combined inspection. "
            "Images may include: truck exterior (front, sides, rear, undercarriage), driver ID/license, "
            "cargo documents, invoices, manifests, or trailer/container photos. "
            "All inputs refer to ONE transport event. Extract every available field. "
            "If a field cannot be determined from the provided material, use null. "
            "For boolean inspection fields: true = no findings (OK), false = findings detected, null = not visible/not applicable. "
            "\n\n"
            "Return ONLY a JSON object with this exact structure:\n"
            "{\n"

            # ── TAB 1: VEHÍCULO ──────────────────────────────────────────
            '  "vehiculo": {\n'
            '    "transportista": "string — carrier company name",\n'
            '    "tipo_accion": "string — Entrega or Recoleccion",\n'
            '    "procedencia": "string — origin state/city",\n'
            '    "tipo_vehiculo": "string — torton, doble remolque, plataforma, caja seca, caja refrigerada, volteo, pipa, low-boy, dolly, etc.",\n'
            '    "marca": "string — truck brand (Kenworth, Freightliner, International, Volvo, etc.)",\n'
            '    "modelo": "string — truck model (T680, Cascadia, etc.)",\n'
            '    "anio": "string — model year if visible",\n'
            '    "color": "string — truck cab color",\n'
            '    "placa_vehiculo": "string — tractor/cab license plate",\n'
            '    "no_economico": "string — carrier-assigned unit number (numero economico / rotulo)",\n'
            '    "material": "string — cargo description",\n'
            '    "conductor": "string — driver full name",\n'
            '    "no_licencia": "string — driver license number"\n'
            '  },\n'

            # ── TAB 2: REMOLQUES / CONTENEDORES ──────────────────────────
            '  "remolques": [\n'
            '    {\n'
            '      "tipo_remolque": "string — caja seca, caja refrigerada, plataforma, contenedor, tanque, etc.",\n'
            '      "no_sello": "string — seal number",\n'
            '      "no_caja_contenedor": "string — box/container unit number",\n'
            '      "placas_caja": "string — trailer license plate",\n'
            '      "comentarios": "string — any comments about this trailer"\n'
            '    }\n'
            '  ],\n'

            # ── TAB 3A: INSPECCIÓN 17 PUNTOS (TRACTOR) ───────────────────
            '  "inspeccion_17_puntos": {\n'
            '    "1_defensa": true,\n'
            '    "2_motor_bateria_filtros": true,\n'
            '    "3_llantas_rines": true,\n'
            '    "4_piso_tractor": true,\n'
            '    "5_tanque_combustible": true,\n'
            '    "6_cabina_dormitorio_puertas_herramientas": true,\n'
            '    "7_tanque_aire": true,\n'
            '    "8_ejes_transmision": true,\n'
            '    "9_quinta_rueda": true,\n'
            '    "10_chasis": true,\n'
            '    "11_puertas_externa": true,\n'
            '    "12_piso_externo_trailer": true,\n'
            '    "13_paredes_externas": true,\n'
            '    "14_pared_frontal_externa": true,\n'
            '    "15_techo_externo": true,\n'
            '    "16_unidad_refrigeracion": true,\n'
            '    "17_escape_mofles": true\n'
            '  },\n'
            "  // Note: inspection booleans — true = OK/no findings, false = issue detected, null = not visible\n"

            # ── TAB 3B: INSPECCIÓN 7 PUNTOS CONTENEDOR ───────────────────
            '  "inspeccion_contenedor": {\n'
            '    "altura_interior": "string — e.g. 2.5m",\n'
            '    "ancho_interior": "string — e.g. 2.4m",\n'
            '    "longitud_interior": "string — e.g. 16.1m",\n'
            '    "puntos": {\n'
            '      "1_exterior_parte_inferior": {"suciedad": null, "plagas": null, "fauna": null},\n'
            '      "2_puertas_interiores_exteriores": {"suciedad": null, "plagas": null, "fauna": null},\n'
            '      "3_pared_interior_derecha": {"suciedad": null, "plagas": null, "fauna": null},\n'
            '      "4_pared_interior_izquierda": {"suciedad": null, "plagas": null, "fauna": null},\n'
            '      "5_pared_interior_frontal": {"suciedad": null, "plagas": null, "fauna": null},\n'
            '      "6_techo_cubierta_superior": {"suciedad": null, "plagas": null, "fauna": null},\n'
            '      "7_piso_interior": {"suciedad": null, "plagas": null, "fauna": null}\n'
            '    }\n'
            '  },\n'

            # ── METADATA ─────────────────────────────────────────────────
            '  "observaciones_generales": "string — CTPAT flags, anomalies, damage, or anything unusual",\n'
            '  "confianza": "string — high / medium / low — your confidence in the extracted data based on image quality"\n'
            "}"
        )
        if not self.ai:
            return {'status_code': 400, 'msg': 'OpenRouter no configurado'}

        # 1. Extraer datos con el LLM
        raw_text = self.ai.ocr_general(image_source, system, prompt, model=model, max_tokens=2000)

        # 2. Normalizar — esto es código, no LLM
        datos = {}
        if raw_text.get('choices'):
            if isinstance(raw_text['choices'], list) and len(raw_text['choices']) >0:
                if raw_text['choices'][0].get('message',{}).get('content'):
                    datos = raw_text['choices'][0]['message']['content']

        datos = self._ocr_normalizar(datos)

        # 3. Validar
        errores = self._ocr_validar_id(datos)
        if errores:
            return {
                'status_code': 206,  # partial content — extrajo pero hay campos inválidos
                'msg': 'Extracción con advertencias',
                'data': datos,
                'warnings': errores,
            }
        return {'status_code': datos.get('status_code', 200), 'msg': 'OK', 'data': datos}

    def ocr_articulo_concesionado(self, image_source,
                                   extra_instructions: str = None,
                                   model: str = 'google/gemini-2.5-flash-lite') -> dict:
        """
        Identifica un artículo concesionado a partir de su foto. Puede tratarse de:
          - Un artículo genérico identificable a simple vista (guantes, casco, chaleco,
            lentes de seguridad, herramienta, etc.), donde lo importante es reconocer
            QUÉ artículo es.
          - Un artículo con un llavero/etiqueta con un número o ID impreso (ej. "ID-360"
            o "360"), usado sobre todo en camiones/vehículos (ej. "ID-360 SPRINTER
            CORTA"). En ese caso el número tiene prioridad para la búsqueda.

        Con lo detectado busca el activo correspondiente en self.AF.ACTIVOS_FIJOS
        (formulario "activos_fijos") y regresa su categoría, nombre de equipo y demás
        datos del registro encontrado.

        Args:
            image_source: URL remota, ruta local, o lista de imágenes del artículo.
            model:        Modelo OpenRouter a usar.

        Returns:
            dict con:
                - status_code : 200 OK / 206 advertencias (no se encontró match) / 400 config
                - data        : campos leídos de la foto + 'activo_fijo' con el registro
                                encontrado en activos fijos (o None si no hubo match)
                - msg         : mensaje de resultado
        """
        if not self.ai:
            return {'status_code': 400, 'msg': 'OpenRouter no configurado'}

        t_inicio = time_module.time()

        system = (
            "You are an asset identification specialist at an industrial plant, trained "
            "to recognize conceded/loaned articles (articulos concesionados). "
            "These can be generic items identifiable on sight — safety gloves, helmets, "
            "vests, goggles, harnesses, tools, etc. — or vehicles/equipment identified by "
            "a physical key tag or label with a printed number/ID (e.g. '360' or "
            "'ID-360 SPRINTER CORTA'). "
            "Your priority is to determine WHICH article this is: if a number or ID tag "
            "is visible, read it as accurately as possible; otherwise identify the article "
            "by what it visually is. "
            "Always respond with a single valid JSON object and nothing else — "
            "no markdown, no backticks, no explanation, no preamble."
        )

        prompt = (
            "Analyze the provided image and identify the conceded article shown. "
            "First check if there is a key tag or label with a printed number/ID visible "
            "(e.g. '360', 'ID-360', 'ID-360 SPRINTER CORTA') — if so, that identifier takes "
            "priority. If there is no number/ID visible, identify the article itself from "
            "what is visually shown (e.g. guantes, casco, chaleco de seguridad, lentes de "
            "seguridad, arnés, herramienta, camión, van, etc.). "
            "If a field cannot be determined from the image, use null. "
            "\n\n"
            "Return ONLY a JSON object with this exact structure:\n"
            "{\n"
            '  "numero_identificador": "string — number/ID read from a key tag or label, e.g. 360 or ID-360, or null",\n'
            '  "nombre_articulo": "string — full text read from the tag/label if any, e.g. ID-360 SPRINTER CORTA, or null",\n'
            '  "tipo_articulo": "string — what the article physically is, in Spanish (e.g. guantes, casco, chaleco de seguridad, lentes de seguridad, arnés, herramienta, camión, van, etc.). This should always be filled based on what is visible.",\n'
            '  "marca": "string — visible brand of the article/vehicle/equipment, or null",\n'
            '  "modelo": "string — visible model, or null",\n'
            '  "color": "string — main visible color, or null",\n'
            '  "observaciones": "string — any relevant detail, damage, or distinguishing marks, or null",\n'
            '  "confianza": "string — alto / medio / bajo — overall confidence based on image clarity"\n'
            "}"
        )

        if extra_instructions:
            prompt += f"\n\nAdditional instructions: {extra_instructions}"

        # Sanitizar image_source
        if isinstance(image_source, str):
            image_source = [image_source]
        elif isinstance(image_source, list):
            image_source = [
                img['file_url'] if isinstance(img, dict) else img
                for img in image_source
            ]
        print('model', model)
        print('image_source', image_source)
        t_ai_inicio = time_module.time()
        raw_text = self.ai.ocr_general(image_source, system, prompt, model=model, max_tokens=1000)
        t_ai_fin = time_module.time()
        print(f'>>> TIEMPO self.ai.ocr_general: {t_ai_fin - t_ai_inicio:.3f}s')
        print('2222', raw_text)
        datos = {}
        if raw_text.get('choices'):
            choices = raw_text['choices']
            if isinstance(choices, list) and len(choices) > 0:
                content = choices[0].get('message', {}).get('content')
                if content:
                    datos = content

        datos = self._ocr_normalizar(datos)

        t_match_inicio = time_module.time()
        activo = self._buscar_activo_fijo(
            numero=datos.get('numero_identificador'),
            nombre=datos.get('nombre_articulo'),
            tipo=datos.get('tipo_articulo'),
        )
        t_match_fin = time_module.time()
        print(f'>>> TIEMPO _buscar_activo_fijo: {t_match_fin - t_match_inicio:.3f}s')
        datos['activo_fijo'] = activo or None

        errores = self._ocr_validar_id(datos)
        if not activo:
            errores.append('No se encontró el artículo en activos fijos')

        t_total = time_module.time() - t_inicio
        print(f'>>> TIEMPO TOTAL ocr_articulo_concesionado: {t_total:.3f}s '
              f'(ai={t_ai_fin - t_ai_inicio:.3f}s, match={t_match_fin - t_match_inicio:.3f}s, '
              f'resto={t_total - (t_ai_fin - t_ai_inicio) - (t_match_fin - t_match_inicio):.3f}s)')

        if errores:
            return {
                'status_code': 206,
                'msg': 'Extracción con advertencias',
                'data': datos,
                'warnings': errores,
            }

        return {'status_code': 200, 'msg': 'OK', 'data': datos}

    def _buscar_activo_fijo(self, numero: str = None, nombre: str = None, tipo: str = None) -> dict:
        """
        Busca en self.AF.ACTIVOS_FIJOS el activo que corresponde a lo detectado en la
        foto del artículo concesionado. Prioriza el match por número/ID (ej. "360" contra
        nombre_equipo "ID-360 SPRINTER CORTA"), y si no hay número usa el nombre leído en
        la etiqueta o, en su defecto, el tipo de artículo identificado visualmente
        (ej. "guantes", "casco") contra nombre_equipo, categoria y tipo_equipo.
        Regresa el registro con categoria, nombre_equipo, marca, modelo, tipo de
        equipo/vehiculo, numero de serie, placas y estatus.
        """
        import re

        # ID de subcampo "categoria" dentro del catalog-select de equipos concesionados
        # (mismo valor que lkf-addons cons_f['categoria_equipo_concesion']).
        categoria_equipo_concesion = f"{self.AF.ACTIVOS_FIJOS_CAT_OBJ_ID}.66ce23efc5c4d148311adf86"

        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.AF.ACTIVOS_FIJOS,
            }},
            {"$project": {
                "_id": 0,
                "folio": {"$ifNull": ["$folio", None]},
                "categoria": {"$ifNull": [f"$answers.{categoria_equipo_concesion}", None]},
                "nombre_equipo": {"$ifNull": [f"$answers.{self.f['nombre_equipo']}", None]},
                "marca": {"$ifNull": [f"$answers.{self.AF.TIPO_DE_VEHICULO_OBJ_ID}.{self.mf['marca_vehiculo']}", None]},
                "modelo": {"$ifNull": [f"$answers.{self.AF.TIPO_DE_VEHICULO_OBJ_ID}.{self.mf['modelo_vehiculo']}", None]},
                "tipo_vehiculo": {"$ifNull": [f"$answers.{self.AF.TIPO_DE_VEHICULO_OBJ_ID}.{self.mf['tipo_vehiculo']}", None]},
                "tipo_equipo": {"$ifNull": [f"$answers.{self.f['tipo_equipo']}", None]},
                "numero_de_serie_chasis": {"$ifNull": [f"$answers.{self.f['numero_de_serie_chasis']}", None]},
                "placas": {"$ifNull": [f"$answers.{self.f['placas']}", None]},
                "estado": {"$ifNull": [f"$answers.{self.f['estado']}", None]},
                "estatus": {"$ifNull": [
                    f"$answers.{self.f['estatus_vehiculo']}",
                    f"$answers.{self.f['estatus']}",
                    None]},
            }},
        ]
        t_query_inicio = time_module.time()
        activos = self.format_cr(self.cr.aggregate(query))
        print(f'>>> TIEMPO query activos_fijos: {time_module.time() - t_query_inicio:.3f}s '
              f'({len(activos)} registros)')

        # 1. Match por número/ID — se le da prioridad (ej. llaveros de camiones/vehículos)
        digitos = re.sub(r'\D', '', numero) if numero else ''
        if digitos:
            for activo in activos:
                digitos_nombre = re.sub(r'\D', '', activo.get('nombre_equipo') or '')
                if digitos_nombre and digitos_nombre == digitos:
                    return activo

        # 2. Match por nombre/tipo de artículo leído o identificado visualmente
        nombres = [a['nombre_equipo'] for a in activos if a.get('nombre_equipo')]
        for texto in (nombre, tipo):
            if not texto:
                continue
            match = next((a for a in activos if a.get('nombre_equipo') == texto), None)
            if not match:
                mejor = self._match_label(texto, nombres, umbral=60)
                if mejor.get('label'):
                    match = next((a for a in activos if a.get('nombre_equipo') == mejor['label']), None)
            if not match:
                categorias = [a['categoria'] for a in activos if a.get('categoria')]
                mejor_cat = self._match_label(texto, categorias, umbral=60)
                if mejor_cat.get('label'):
                    match = next((a for a in activos if a.get('categoria') == mejor_cat['label']), None)
            if not match:
                tipos = [a['tipo_equipo'] for a in activos if a.get('tipo_equipo')]
                mejor_tipo = self._match_label(texto, tipos, umbral=60)
                if mejor_tipo.get('label'):
                    match = next((a for a in activos if a.get('tipo_equipo') == mejor_tipo['label']), None)
            if match:
                return match
        return {}

    # ============================================
    # Menus (migrado de menus.py)
    # ============================================

    def format_menus(self, data):
        """
        Formatea los datos de los registros obtenidos en el catalogo de ELEMENTOS MENU
        para obtener los menus.
        """
        if not data:
            return []

        f = self.menu_catalog_fields
        format_data = []
        for item in data:
            format_data.append({
                # Módulo
                "menu_key":           item.get(f['catalog_menu_key']),
                "menu":               item.get(f['catalog_menu']),
                "menu_order":         item.get(f['catalog_menu_order']),
                "menu_icon":          item.get(f['catalog_menu_icon']),
                "menu_columns":       item.get(f['catalog_menu_columns']),
                # Sección
                "seccion_key":        item.get(f['catalog_seccion_key']),
                "seccion":            item.get(f['catalog_seccion']),
                "seccion_order":      item.get(f['catalog_seccion_order']),
                "seccion_column":     item.get(f['catalog_seccion_column']),
                "seccion_href":       item.get(f['catalog_seccion_href']),
                "seccion_icon":       item.get(f['catalog_seccion_icon']),
                "seccion_icon_color": item.get(f['catalog_seccion_icon_color']),
                # Item
                "elemento":           item.get(f['catalog_elemento']),
                "key":                item.get(f['catalog_key']),
                "type":               item.get(f['catalog_type']),
                "item_order":         item.get(f['catalog_item_order']),
                "href_web":           item.get(f['catalog_href_web']),
                "route_mobile":       item.get(f['catalog_route_mobile']),
                "plataforms":         item.get(f['catalog_plataforms']),
            })
        return format_data

    def get_format_user_menus(self, filter_keys=None):
        """
        Obtiene los menus por default del catalogo de ELEMENTOS MENU.
        """
        selector = {}
        if filter_keys:
            selector = {f"answers.{self.menu_catalog_fields['catalog_key']}": {"$in": filter_keys}}

        mango_query = {
            "selector": selector,
            "limit": 10000,
        }
        data = self.format_menus(self.lkf_api.search_catalog( self.MENUS_CATALOG_ID, mango_query))
        return data

    def get_structured_mobile_menu(self, data):
        """
        Agrupa una lista plana de items de menú en la estructura
        jerárquica para móvil: módulo > submodulos > items.
        """
        modules_dict = {}

        for item in data:
            if item.get('plataforms') == 'web':
                continue

            menu_key    = item.get('menu_key') or self.slugify(item.get('menu', ''), '_')
            seccion_key = item.get('seccion_key') or self.slugify(item.get('seccion', ''), '_')

            if menu_key not in modules_dict:
                modules_dict[menu_key] = {
                    'id':         menu_key.replace('_', '-'),
                    'key':        menu_key,
                    'label':      item.get('menu', ''),
                    'icon':       item.get('menu_icon'),
                    'order':      item.get('menu_order') or len(modules_dict) + 1,
                    'submodules': {}
                }

            submodules = modules_dict[menu_key]['submodules']

            if seccion_key not in submodules:
                submodules[seccion_key] = {
                    'id':         seccion_key.replace('_', '-'),
                    'key':        seccion_key,
                    'label':      item.get('seccion', ''),
                    'order':      item.get('seccion_order') or len(submodules) + 1,
                    'icon':       item.get('seccion_icon'),
                    'iconBgColor': item.get('seccion_icon_color'),
                    'items':      {}
                }

            item_key = item.get('key') or self.slugify(item.get('elemento', ''), '_')
            if item_key not in submodules[seccion_key]['items']:
                item_data = {
                    'key':   item_key,
                    'label': item.get('elemento', ''),
                    'type':  item.get('type', 'link'),
                    'order': item.get('item_order') or len(submodules[seccion_key]['items']) + 1,
                }
                item_route = item.get('route_mobile')
                if item_route:
                    item_data['route'] = item_route
                submodules[seccion_key]['items'][item_key] = item_data

        modules = []
        for module in modules_dict.values():
            submodules = sorted(module['submodules'].values(), key=lambda s: s['order'])
            for s in submodules:
                s['items'] = sorted(s['items'].values(), key=lambda i: i['order'])
            modules.append({**module, 'submodules': submodules})

        return {'menu': sorted(modules, key=lambda m: m['order'])}

    def get_structured_web_menu(self, data):
        """
        Agrupa una lista plana de items de menú en la estructura
        jerárquica módulo > sección > items.
        """
        modules_dict = {}

        for item in data:
            if item.get('plataforms') in ['Mobile', 'mobile']:
                continue

            menu_key    = item.get('menu_key') or self.slugify(item.get('menu', ''), '_')
            seccion_key = item.get('seccion_key') or self.slugify(item.get('seccion', ''), '_')

            if menu_key not in modules_dict:
                modules_dict[menu_key] = {
                    'id':       menu_key.replace('_', '-'),
                    'key':      menu_key,
                    'label':    item.get('menu', ''),
                    'icon':     item.get('menu_icon'),
                    'order':    item.get('menu_order') or len(modules_dict) + 1,
                    'columns':  item.get('menu_columns'),
                    'sections': {}
                }

            sections = modules_dict[menu_key]['sections']

            if seccion_key not in sections:
                seccion_href = item.get('seccion_href')
                seccion_data = {
                    'id':     seccion_key.replace('_', '-'),
                    'key':    seccion_key,
                    'label':  item.get('seccion', ''),
                    'order':  item.get('seccion_order') or len(sections) + 1,
                    'column': item.get('seccion_column') or len(sections) + 1,
                    'items':  {}
                }
                if seccion_href:
                    seccion_data['href'] = seccion_href
                sections[seccion_key] = seccion_data

            item_href = item.get('href_web')
            item_key = item.get('key') or self.slugify(item.get('elemento', ''), '_')
            if item_key not in sections[seccion_key]['items']:
                item_data = {
                    'key':   item_key,
                    'label': item.get('elemento', ''),
                    'type':  item.get('type', 'link'),
                    'order': item.get('item_order') or len(sections[seccion_key]['items']) + 1,
                }
                if item_href:
                    item_data['href'] = item_href
                sections[seccion_key]['items'][item_key] = item_data

        modules = []
        for module in modules_dict.values():
            sections = sorted(module['sections'].values(), key=lambda s: s['order'])
            for s in sections:
                s['items'] = sorted(s['items'].values(), key=lambda i: i['order'])
            modules.append({**module, 'sections': sections})

        return {'modules': sorted(modules, key=lambda m: m['order'])}

    def get_user_menus(self, platform=''):
        """
        Obtiene los menus personalizados para el usuario
        actual desde los registros de la forma de CONFIGURACION MENUS.
        """
        print('user get_menus...... en service...')
        query = [
            {"$match": {
                "form_id": self.MENUS_FORM,
                "deleted_at": {"$exists": False},
                f"answers.{self.USUARIOS_OBJ_ID}.{self.menu_form_fields['usuario_id']}": self.user.get('user_id')
            }},
            {"$project": {
                "_id": 0,
                "elementos": f"$answers.{self.menu_form_fields['elementos']}"
            }},
            {"$unwind": "$elementos"},
            {"$project": {
                "menu_key": f"$elementos.{self.MENUS_CATALOG_OBJ_ID}.{self.menu_form_fields['key']}",
            }}
        ]
        print('self.cr=', self.cr)
        data = self.format_cr(self.cr.aggregate(query), ids_label_dct=self.menu_form_fields)
        if data:
            menu_keys = [self.unlist(item['menu_key']) for item in data if item.get('menu_key')]
            data = self.get_format_user_menus(filter_keys=menu_keys)
        else:
            data = self.get_format_user_menus()

        if platform == 'mobile':
            return self.get_structured_mobile_menu(data)

        modules = self.get_structured_web_menu(data)
        return modules

    def set_item_permits(self, user_id, item_needed, item_type):
        """
        Comparte los items necesarios para el usuario
        """
        permissions = 'can_read_item'
        share_data = {
            "owner": f"/api/infosync/user/{user_id}/",
            "perm": permissions
        }
        if item_type == 'form':
            user_item = self.lkf_api.get_user_forms(user_id)
        elif item_type == 'catalog':
            user_item = self.lkf_api.get_user_catalog(user_id)
        elif item_type == 'script':
            user_item = self.lkf_api.get_user_scripts(user_id)
        else:
            self.LKFException('Item type not found: ', item_type)
        res = {}
        user_item = user_item.get('data',[])
        if isinstance(user_item, dict):
            user_item = []
        user_item = [item for item in user_item ]
        unshare_items = []
        for item in user_item:
            if item['id'] not in item_needed:
                unshare_items.append(item)

        if unshare_items:
            unshare_items_data = []
            for item in unshare_items:
                unshare_data = {'group_id':None, 'filter_name':None}
                unshare_data['uri'] = f"/api/infosync/file_shared/{item['shared_id']}/"
                unshare_data['item_id'] = item['id']
                unshare_items_data.append(unshare_data)
            if unshare_items_data:
                res = self.lkf_api.share_form(unshare_items_data, unshare=True)

        user_item_ids = {item['id'] for item in user_item}
        items_to_share = item_needed - user_item_ids
        for item_id in items_to_share:
            share_data["file_shared"]=  f"/api/infosync/item/{item_id}/"
            res = self.lkf_api.share_form(share_data)
            if res['status_code'] != 201:
                self.LKFException(f'Error al compartir scritp: {share_data}')
        return res

    def set_user_permissions(self, answers, user_id=None):
        """
        Comparte las Formas, Catalogos y Scripts necesarios para el usuario tomando en cuenta
        sus menus asignados.

        args:
            answers (json): answers del registro de CONFIGURACION MENUS que disparó el cambio
            user_id (str): opcional, si no viene se toma de answers (usuario_id del registro)
        """
        data = self._labels(answers, ids_label_dct=self.menu_form_fields)
        if not user_id:
            user_id = data.get('usuario_id')
        if user_id and isinstance(user_id, list):
            user_id = user_id[0]
        forms_needed = set()
        catalogs_needed = set()
        scripts_needed = set()
        menus = {i.get('menu', '').lower().replace(' ', '_') for i in data.get('elementos', [])}
        menus = ['always'] + list(menus)
        for menu in menus:
            config = self.module_permits.get(menu, {})
            if not config:
                continue
            forms_needed.update([x for x in config.get('forms',[]) if x])
            catalogs_needed.update([x for x in config.get('catalogs') if x])
            scripts_needed.update([x for x in config.get('scripts') if x])

        response_forms = self.set_item_permits(user_id, forms_needed, item_type='form')
        response_catalog = self.set_item_permits(user_id, catalogs_needed, item_type='catalog')
        response_scripts = self.set_item_permits(user_id, scripts_needed,  item_type='script')

        return True

    def slugify(self, text, sep='-'):
        """
        Convierte un texto en un slug,
        reemplazando espacios y caracteres especiales.
        """
        text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')
        text = re.sub(r'[^\w\s-]', '', text.lower().strip())
        return re.sub(r'[\s_-]+', sep, text)

    def set_config(self, answers):
        """
        Comparte Formas, Catalogos y Scripts segun el esquema legacy de
        permisos de config_access.py (distinto de set_user_permissions/menus.py).
        """
        data = self._labels(answers)
        user_id = data.get('id_usuario')
        if user_id and isinstance(user_id, list):
            user_id = user_id[0]
        forms_needed = set()
        catalogs_needed = set()
        scripts_needed = set()
        menus = ['always'] + data.get('menus', [])
        for menu in menus:
            config = self.config_access_module_permits.get(menu, {})
            if not config:
                continue
            forms_needed.update([x for x in config.get('forms', []) if x])
            catalogs_needed.update([x for x in config.get('catalogs') if x])
            scripts_needed.update([x for x in config.get('scripts') if x])

        self.set_item_permits(user_id, forms_needed, item_type='form')
        self.set_item_permits(user_id, catalogs_needed, item_type='catalog')
        self.set_item_permits(user_id, scripts_needed, item_type='script')

        return True

    #! ============================================
    #! Transportistas: pases, bitacora de recepcion e inspecciones CTPAT
    #! (migrado de transportistas.py / transportistas_bitacoras.py / accesos_utils.py)
    #! ============================================

    def get_andenes(self):
        query = [
            {'$match': {
                'form_id': self.Location.AREAS_DE_LAS_UBICACIONES,
                'deleted_at': {'$exists': False},
                f'answers.{self.Location.TIPO_AREA_OBJ_ID}.{self.f["tipo_de_area"]}': 'Andén',
            }},
            {'$project': {
                '_id': 0,
                'area': f'$answers.{self.f["area"]}',
            }},
            {'$sort': {'area': 1}},
        ]
        resultado = self.format_cr(self.cr.aggregate(query))
        return [r['area'] for r in resultado if r.get('area')]

    def get_bitac_transportista_record(self, record_id):
        f = self.bitacora_transportista_fields
        query = [
            {'$match': {
                'form_id': self.BITACORA_TRANSPORTISTAS,
                'deleted_at': {'$exists': False},
                '_id': ObjectId(record_id),
            }},
            {'$project': {
                '_id': 1,
                'folio': 1,
                'created_at': 1,
                'estatus':               f'$answers.{f["estatus"]}',
                'fecha_hora_ingreso':    f'$answers.{f["fecha_hora_ingreso"]}',
                'fecha_hora_descarga':   f'$answers.{f["fecha_hora_descarga"]}',
                'num_de_pase':           f'$answers.{f["num_de_pase"]}',
                'empresa_transportista': f'$answers.{f["empresa_transportista"]}',
                'tipo_de_operacion':     f'$answers.{f["tipo_de_operacion"]}',
                'procedencia':           f'$answers.{f["procedencia"]}',
                'tipo_de_vehiculo':      f'$answers.{f["tipo_de_vehiculo"]}',
                'placas_de_vehiculo':    f'$answers.{f["placas_de_vehiculo"]}',
                'num_eco_num_rotulo':    f'$answers.{f["num_eco_num_rotulo"]}',
                'marca_vehiculo':        f'$answers.{f["marca_vehiculo"]}',
                'year_vehiculo':         f'$answers.{f["year_vehiculo"]}',
                'color_vehiculo':        f'$answers.{f["color_vehiculo"]}',
                'conductor':             f'$answers.{f["conductor"]}',
                'ayudante':              f'$answers.{f["ayudante"]}',
                'num_licencia':          f'$answers.{f["num_licencia"]}',
                'firma_conductor':       f'$answers.{f["firma_conductor"]}',
                'anden_asignado':        f'$answers.{f["anden_asignado"]}',
                'proveedor_cliente':     f'$answers.{f["proveedor_cliente"]}',
                'orden_de_compra':       f'$answers.{f["orden_de_compra"]}',
                'documentos': {'$map': {
                    'input': {'$ifNull': [f'$answers.{f["grupo_fotos_y_documentos"]}', []]},
                    'as': 'doc',
                    'in': {
                        'tipo':      f'$$doc.{f["tipo_de_documento"]}',
                        'documento': f'$$doc.{f["documento"]}',
                    },
                }},
                'materiales': {'$map': {
                    'input': {'$ifNull': [f'$answers.{f["grupo_materiales"]}', []]},
                    'as': 'm',
                    'in': {
                        'lugar':             f'$$m.{f["lugar_material"]}',
                        'no_referencia':     f'$$m.{f["no_referencia_material"]}',
                        'producto':          f'$$m.{f["producto_material"]}',
                        'lote':              f'$$m.{f["lote_material"]}',
                        'cantidad':          f'$$m.{f["cantidad_material"]}',
                        'cantidad_fisica':   f'$$m.{f["cantidad_fisica_material"]}',
                        'peso':              f'$$m.{f["peso_material"]}',
                        'volumen':           f'$$m.{f["volumen_material"]}',
                    },
                }},
                'remolques': {'$map': {
                    'input': {'$ifNull': [f'$answers.{f["grupo_remolques"]}', []]},
                    'as': 'r',
                    'in': {
                        'tipo_remolque': f'$$r.{f["tipo_remolque"]}',
                        'no_referencia_remolque': f'$$r.{f["no_referencia_remolque"]}',
                        'no_sello':      f'$$r.{f["num_sello"]}',
                        'no_caja':       f'$$r.{f["num_caja_contenedor"]}',
                        'placas_caja':   f'$$r.{f["placas_de_caja"]}',
                        'color':         f'$$r.{f["color_remolque_contenedor"]}',
                        'comentarios':   f'$$r.{f["comentarios"]}',
                    },
                }},
                'inspecciones': {'$map': {
                    'input': {'$ifNull': [f'$answers.{f["grupo_inspecciones"]}', []]},
                    'as': 'i',
                    'in': {
                        'tipo': f'$$i.{f["tipo_inspeccion"]}',
                        'url':  f'$$i.{f["url_inspeccion"]}',
                    },
                }},
            }},
        ]
        return self.format_cr(self.cr.aggregate(query), get_one=True)

    def get_bitac_transportista_records(self):
        f = self.bitacora_transportista_fields
        query = [
            {'$match': {
                'form_id': self.BITACORA_TRANSPORTISTAS,
                'deleted_at': {'$exists': False},
            }},
            {'$project': {
                '_id': 1,
                'folio':              1,
                'placas':             f'$answers.{f["placas_de_vehiculo"]}',
                'proveedor_cliente':  f'$answers.{f["proveedor_cliente"]}',
                'conductor':          f'$answers.{f["conductor"]}',
                'tipo_de_operacion':  f'$answers.{f["tipo_de_operacion"]}',
                'estatus':            f'$answers.{f["estatus"]}',
                'num_de_pase':        f'$answers.{f["num_de_pase"]}',
                'fecha_hora_ingreso': f'$answers.{f["fecha_hora_ingreso"]}',
                'material': {
                    '$let': {
                        'vars': {'primer': {'$arrayElemAt': [f'$answers.{f["grupo_materiales"]}', 0]}},
                        'in': f'$$primer.{f["producto_material"]}',
                    }
                },
            }},
            {'$sort': {'_id': -1}},
        ]
        return self.format_cr(self.cr.aggregate(query))

    def get_horarios_data(self, dia=None):
        """
        Devuelve la concurrencia por hora del día para graficar horarios de mayor
        afluencia, similar al gráfico de Google Maps.

        Args:
            dia: 0=lunes … 6=domingo. None = todos los días acumulados.

        Nota: cada pase cuenta en todas las horas que abarca su rango
        hora_inicial→hora_final (excluyendo la hora de salida).
        """
        f = self.pass_fields_transportista

        hoy = date.today()
        cuatrimestre = (hoy.month - 1) // 4
        mes_inicio = cuatrimestre * 4 + 1
        mes_fin = mes_inicio + 3
        fecha_inicio = f'{hoy.year}-{mes_inicio:02d}-01'
        fecha_fin = f'{hoy.year}-{mes_fin:02d}-31'

        match_query = {
            'form_id': self.PASE_ENTRADA_TRANSPORTISTA,
            'deleted_at': {'$exists': False},
            f'answers.{f["fecha_pase_transportista_desde"]}': {'$lte': fecha_fin},
            '$or': [
                {f'answers.{f["fecha_pase_transportista_hasta"]}': {'$gte': fecha_inicio}},
                {f'answers.{f["fecha_pase_transportista_hasta"]}': {'$exists': False}},
                {f'answers.{f["fecha_pase_transportista_hasta"]}': ''},
            ],
        }

        res = self.cr.find(match_query, {
            'hora_inicial': f'$answers.{f["hora_inicial"]}',
            'hora_final':   f'$answers.{f["hora_final"]}',
            'fecha_desde':  f'$answers.{f["fecha_pase_transportista_desde"]}',
            'fecha_hasta':  f'$answers.{f["fecha_pase_transportista_hasta"]}',
        })

        DIAS_SEMANA = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        conteo = {h: 0 for h in range(24)}

        for record in self.format_cr(res):
            if dia is not None:
                fecha_desde_str = record.get('fecha_desde', '')
                fecha_hasta_str = record.get('fecha_hasta', '') or fecha_desde_str
                try:
                    d_ini = datetime.strptime(fecha_desde_str[:10], '%Y-%m-%d').date()
                    d_fin = datetime.strptime(fecha_hasta_str[:10], '%Y-%m-%d').date()
                    dias_rango = (d_fin - d_ini).days + 1
                    dia_en_rango = any(
                        (d_ini + timedelta(days=i)).weekday() == dia
                        for i in range(min(dias_rango, 7))
                    )
                    if not dia_en_rango:
                        continue
                except (ValueError, AttributeError):
                    continue

            hora_ini_str = record.get('hora_inicial', '')
            hora_fin_str = record.get('hora_final', '')
            if not hora_ini_str or not hora_fin_str:
                continue

            try:
                h_ini = int(hora_ini_str.split(':')[0])
                h_fin = int(hora_fin_str.split(':')[0])
                for h in range(h_ini, h_fin):
                    conteo[h] += 1
            except (ValueError, AttributeError):
                continue

        resultado = [
            {'hora': f'{h:02d}:00', 'count': conteo[h]}
            for h in range(0, 24)
        ]

        max_count = max((h['count'] for h in resultado), default=1) or 1
        for h in resultado:
            nivel = round(h['count'] / max_count * 100)
            if nivel == 0:
                h['nivel'] = 'sin_concurrencia'
            elif nivel <= 33:
                h['nivel'] = 'poco_concurrido'
            elif nivel <= 66:
                h['nivel'] = 'concurrido'
            else:
                h['nivel'] = 'muy_concurrido'

        dia_label = DIAS_SEMANA[dia] if dia is not None else 'todos'
        return {'dia': dia_label, 'horarios': resultado}

    def get_pass_transportista(self, record_id=None, token=None):
        f = self.pass_fields_transportista
        match = {
            'form_id': self.PASE_ENTRADA_TRANSPORTISTA,
            'deleted_at': {'$exists': False},
        }
        if record_id:
            match['_id'] = ObjectId(record_id)
        elif token:
            match[f'answers.{f["token_transportista"]}'] = token
        else:
            self.LKFException({'title': 'Se requiere record_id o token', 'status_code': 400})
        query = [
            {'$match': match},
            {'$project': {
                '_id': 1,
                'created_at': 1,
                'folio':          '$folio',
                'creado_desde':   f'$answers.{self.pase_entrada_fields["creado_desde"]}',
                'tipo_de_operacion': f'$answers.{f["tipo_de_operacion"]}',

                # quien crea el pase
                'nombre_crea_el_pase':   f'$answers.{f["nombre_crea_el_pase"]}',
                'email_crea_el_pase':    f'$answers.{f["email_crea_el_pase"]}',
                'telefono_crea_el_pase': f'$answers.{f["telefono_crea_el_pase"]}',

                # transportista que recibe
                'proveedor':          f'$answers.{f["proveedor"]}',
                'proveedor_email':    f'$answers.{f["proveedor_email"]}',
                'proveedor_telefono': f'$answers.{f["proveedor_telefono"]}',

                # material
                'proveedor_cliente_material': f'$answers.{f["proveedor_cliente_material"]}',
                'orden_de_compra':            f'$answers.{f["orden_de_compra"]}',
                'documentos': {'$map': {
                    'input': f'$answers.{f["grupo_documentos_para_ocr"]}',
                    'as':    'doc',
                    'in': {
                        'tipo':      f'$$doc.{f["tipo_de_documento"]}',
                        'no_doc':    f'$$doc.{f["no_de_documento"]}',
                        'archivo':   f'$$doc.{f["documento_para_ocr"]}',
                    },
                }},
                'materiales': {'$map': {
                    'input': f'$answers.{f["grupo_materiales"]}',
                    'as':    'item',
                    'in': {
                        'tipo':       f'$$item.{f["tipo"]}',
                        'cantidad':   f'$$item.{f["cantidad"]}',
                        'volumen':    f'$$item.{f["volumen"]}',
                        'peso':       f'$$item.{f["peso"]}',
                        'sello':      f'$$item.{f["sello"]}',
                        'contenedor': f'$$item.{f["contenedor"]}',
                    },
                }},

                # lugar entrega / recepción
                'ubicacion':    f'$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.mf["ubicacion"]}',
                'direccion':    {'$first': f'$answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f["address_name"]}'},
                'anden':        f'$answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf["nombre_area"]}',
                'fecha_desde':  f'$answers.{f["fecha_pase_transportista_desde"]}',
                'fecha_hasta':  f'$answers.{f["fecha_pase_transportista_hasta"]}',
                'hora_inicial': f'$answers.{f["hora_inicial"]}',
                'hora_final':   f'$answers.{f["hora_final"]}',

                # lugar recolección (tipos 2 y 3)
                'lugar_recoleccion':         f'$answers.{f["lugar_de_recoleccion"]}',
                'direccion_recoleccion':     f'$answers.{f["direccion_lugar_de_recoleccion"]}',
                'fecha_recoleccion':         f'$answers.{f["fecha_de_recoleccion"]}',
                'hora_inicial_recoleccion':  f'$answers.{f["hora_inicial_recoleccion"]}',
                'hora_final_recoleccion':    f'$answers.{f["hora_final_recoleccion"]}',
                'anden_recoleccion':         f'$answers.{f["anden_recoleccion"]}',
                'responsable':               f'$answers.{f["responsable"]}',
                'responsable_email':         f'$answers.{f["responsable_email"]}',
                'responsable_telefono':      f'$answers.{f["responsable_telefono"]}',
                'metodo_de_embarque':        f'$answers.{f["metodo_de_embarque"]}',
                'incoterm':                  f'$answers.{f["incoterm"]}',

                # conductor
                'conductor_nombre':           f'$answers.{f["conductor_nombre"]}',
                'conductor_no_licencia':      f'$answers.{f["conductor_no_licencia"]}',
                'conductor_lugar_expedicion': f'$answers.{f["conductor_lugar_expedicion"]}',
                'conductor_vigencia':         f'$answers.{f["conductor_vigencia"]}',
                'conductor_foto_licencia':    f'$answers.{f["conductor_foto_licencia"]}',

                # ayudante
                'ayudante_nombre':            f'$answers.{f["ayudante_nombre"]}',
                'ayudante_no_licencia':       f'$answers.{f["ayudante_no_licencia"]}',
                'ayudante_lugar_expedicion':  f'$answers.{f["ayudante_lugar_expedicion"]}',
                'ayudante_vigencia':          f'$answers.{f["ayudante_vigencia"]}',
                'ayudante_foto_licencia':     f'$answers.{f["ayudante_foto_licencia"]}',

                # vehículo
                'vehiculo_linea':               f'$answers.{f["vehiculo_linea"]}',
                'vehiculo_tipo_unidad':         f'$answers.{f["vehiculo_tipo_unidad"]}',
                'vehiculo_marca':               f'$answers.{f["vehiculo_marca"]}',
                'vehiculo_modelo':              f'$answers.{f["vehiculo_modelo"]}',
                'vehiculo_year':                f'$answers.{f["vehiculo_year"]}',
                'vehiculo_placas':              f'$answers.{f["vehiculo_placas"]}',
                'vehiculo_no_economico':        f'$answers.{f["vehiculo_no_economico"]}',
                'vehiculo_niv':                 f'$answers.{f["vehiculo_niv"]}',
                'vehiculo_tarjeta_circulacion': f'$answers.{f["vehiculo_tarjeta_circulacion"]}',

                # contenedores
                'foto_contenedores': f'$answers.{f["foto_contenedores"]}',
                'contenedores': {'$map': {
                    'input': {'$ifNull': [f'$answers.{f["grupo_contenedores"]}', []]},
                    'as':    'row',
                    'in': {
                        'numero': f'$$row.{f["contenedor_numero"]}',
                        'sello':  f'$$row.{f["contenedor_sello"]}',
                        'tipo':   f'$$row.{f["contenedor_tipo"]}',
                    },
                }},

                # control
                'estado_transportista': f'$answers.{f["estado_transportista"]}',
                'url_del_pase':         f'$answers.{f["url_del_pase_transportista"]}',
                'qr':                   f'$answers.{f["qr_del_pase_transportista"]}',
                'token':                f'$answers.{f["token_transportista"]}',
            }},
        ]
        return self.format_cr(self.cr.aggregate(query), get_one=True)

    def generate_submit_token_transportista(self, record_id):
        f = self.pass_fields_transportista
        token = str(ObjectId())
        answers = {f['token_transportista']: token}
        res = self.lkf_api.patch_multi_record(
            answers=answers,
            form_id=self.PASE_ENTRADA_TRANSPORTISTA,
            record_id=[record_id],
        )
        if res.get('status_code') not in [201, 202]:
            self.LKFException({'title': 'Error al generar token transportista', 'msg': res})
        return {'token': token, 'record_id': record_id}

    def get_users_data(self, locations=None):
        match = {
            'form_id': self.Employee.CONF_AREA_EMPLEADOS,
            'deleted_at': {'$exists': False},
        }
        if locations:
            if isinstance(locations, str):
                locations = [locations]
            match[f'answers.{self.mf["areas_grupo"]}'] = {
                '$elemMatch': {
                    f'{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f["location"]}': {'$in': locations}
                }
            }
        query = [
            {'$match': match},
            {'$project': {
                'nombre':   f'$answers.{self.Employee.EMPLOYEE_OBJ_ID}.{self.mf["nombre_empleado"]}',
                'email':    {'$first': f'$answers.{self.Employee.EMPLOYEE_OBJ_ID}.{self.f["new_user_email"]}'},
                'telefono': {'$first': f'$answers.{self.Employee.EMPLOYEE_OBJ_ID}.{self.mf["telefono_visita_a"]}'},
            }},
            {'$group': {
                '_id': '$nombre',
                'email':    {'$first': '$email'},
                'telefono': {'$first': '$telefono'},
            }},
            {'$project': {
                '_id': 0,
                'nombre':   '$_id',
                'email':    1,
                'telefono': 1,
            }},
            {'$sort': {'nombre': 1}},
        ]
        return self.format_cr(self.cr.aggregate(query))

    def get_location_data(self, location):
        areas_query = [
            {'$match': {
                'form_id': self.Location.AREAS_DE_LAS_UBICACIONES,
                'deleted_at': {'$exists': False},
                f'answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f["location"]}': location,
            }},
            {'$project': {
                '_id': 0,
                'area': f'$answers.{self.mf["nombre_area"]}',
            }},
            {'$sort': {'area': 1}},
        ]
        areas = [r['area'] for r in self.format_cr(self.cr.aggregate(areas_query)) if r.get('area')]

        ubicacion_query = [
            {'$match': {
                'form_id': self.Location.UBICACIONES,
                'deleted_at': {'$exists': False},
                f'answers.{self.f["location"]}': location,
            }},
            {'$project': {
                '_id': 0,
                'direccion': {'$first': f'$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.mf["direccion"]}'},
            }},
            {'$limit': 1},
        ]
        ubicacion = self.format_cr(self.cr.aggregate(ubicacion_query), get_one=True)

        return {
            'ubicacion': location,
            'direccion': ubicacion.get('direccion', '') if ubicacion else '',
            'areas': areas,
        }

    def get_proveedores_transportista(self):
        query = [
            {'$match': {
                'form_id': self.PROVEEDORES_FORM,
                'deleted_at': {'$exists': False},
                'answers.6a18e4086423e82150aa527c': 'recoleccion',
            }},
            {'$project': {
                '_id': 0,
                'nombre':    '$answers.667468e3e577b8b98c852aaa',
                'direccion': {'$first': f'$answers.{self.CONTACTO_CAT_OBJ_ID}.663a7e0fe48382c5b1230902'},
            }},
            {'$sort': {'nombre': 1}},
        ]
        return self.format_cr(self.cr.aggregate(query))

    def validate_token(self, record_id=None, token=None):
        f = self.pass_fields_transportista
        match = {
            'form_id': self.PASE_ENTRADA_TRANSPORTISTA,
            'deleted_at': {'$exists': False},
        }
        if record_id and token:
            match['_id'] = ObjectId(record_id)
            match[f'answers.{f["token_transportista"]}'] = token
        else:
            self.LKFException({'title': 'Se requiere record_id y token para validar el pase', 'status_code': 400})
        query = [
            {'$match': match},
            {'$project': {
                '_id': 1,
            }},
        ]
        data = self.format_cr(self.cr.aggregate(query), get_one=True)
        if data:
            return True
        return False

    def update_information_transportista(self, data):
        f = self.pass_fields_transportista
        record_id  = data.get('record_id')
        conductor  = data.get('conductor')
        ayudante   = data.get('ayudante')
        vehiculo   = data.get('vehiculo')
        foto_cont  = data.get('foto_contenedores')
        contenedores = data.get('contenedores')

        answers = {}

        if conductor:
            foto = conductor.get('foto') or {}
            answers.update({
                f['conductor_nombre']:           conductor.get('nombre', ''),
                f['conductor_no_licencia']:      conductor.get('licencia', ''),
                f['conductor_lugar_expedicion']: conductor.get('lugar_expedicion', ''),
                f['conductor_vigencia']:         conductor.get('vigencia', ''),
                f['conductor_foto_licencia']:    [{'file_name': foto.get('file_name', ''), 'file_url': foto['file_url']}] if foto.get('file_url') else [],
            })

        if ayudante:
            foto = ayudante.get('foto') or {}
            answers.update({
                f['ayudante_nombre']:            ayudante.get('nombre', ''),
                f['ayudante_no_licencia']:       ayudante.get('licencia', ''),
                f['ayudante_lugar_expedicion']:  ayudante.get('lugar_expedicion', ''),
                f['ayudante_vigencia']:          ayudante.get('vigencia', ''),
                f['ayudante_foto_licencia']:     [{'file_name': foto.get('file_name', ''), 'file_url': foto['file_url']}] if foto.get('file_url') else [],
            })

        if vehiculo:
            foto = vehiculo.get('foto') or {}
            answers.update({
                f['vehiculo_linea']:               vehiculo.get('linea', ''),
                f['vehiculo_tipo_unidad']:         vehiculo.get('tipo', ''),
                f['vehiculo_marca']:               vehiculo.get('marca', ''),
                f['vehiculo_modelo']:              vehiculo.get('modelo', ''),
                f['vehiculo_year']:                vehiculo.get('año', ''),
                f['vehiculo_placas']:              vehiculo.get('placas', ''),
                f['vehiculo_no_economico']:        vehiculo.get('economico', ''),
                f['vehiculo_niv']:                 vehiculo.get('niv', ''),
                f['vehiculo_tarjeta_circulacion']: [{'file_name': foto.get('file_name', ''), 'file_url': foto['file_url']}] if foto.get('file_url') else [],
            })

        if foto_cont:
            answers[f['foto_contenedores']] = [{'file_name': foto_cont.get('file_name', ''), 'file_url': foto_cont['file_url']}] if foto_cont.get('file_url') else []

        if contenedores:
            answers[f['grupo_contenedores']] = {
                -(i + 1): {
                    f['contenedor_numero']: c.get('numero', ''),
                    f['contenedor_sello']:  c.get('sello', ''),
                    f['contenedor_tipo']:   c.get('tipo', ''),
                }
                for i, c in enumerate(contenedores)
            }

        res = self.lkf_api.patch_multi_record(
            answers=answers,
            form_id=self.PASE_ENTRADA_TRANSPORTISTA,
            record_id=[record_id],
        )
        if res.get('status_code') not in [201, 202]:
            self.LKFException({'title': 'Error al actualizar información del transportista', 'msg': res})
        return res

    def save_bitac_transportista_record(self, record_id, data):
        f = self.bitacora_transportista_fields
        answers = {}

        vehiculo = data.get('vehiculo') or {}
        if vehiculo:
            answers.update({
                f['placas_de_vehiculo']: vehiculo.get('placas_de_vehiculo', ''),
                f['num_eco_num_rotulo']: vehiculo.get('num_eco_num_rotulo', ''),
                f['tipo_de_vehiculo']:   vehiculo.get('tipo_de_vehiculo', ''),
                f['marca_vehiculo']:     vehiculo.get('marca', ''),
                f['year_vehiculo']:      vehiculo.get('modelo', ''),
                f['color_vehiculo']:     vehiculo.get('color', ''),
            })

        embarque = data.get('embarque') or {}
        if embarque:
            answers.update({
                f['empresa_transportista']: embarque.get('procedencia', ''),
                f['proveedor_cliente']:     embarque.get('proveedor_cliente', ''),
                f['orden_de_compra']:       embarque.get('no_orden_compra', ''),
            })

        # contenedores y remolques van al mismo grupo
        remolques    = data.get('remolques', []) or []
        contenedores = data.get('contenedores', []) or []
        grupo = remolques + contenedores
        if grupo:
            answers[f['grupo_remolques']] = {
                (item['index'] if item.get('index') is not None else -(i + 1)): {
                    f['tipo_remolque']:            item.get('tipo', ''),
                    f['num_caja_contenedor']:      item.get('no_caja', ''),
                    f['num_sello']:                item.get('no_sello', ''),
                    f['placas_de_caja']:           item.get('placas', ''),
                    f['color_remolque_contenedor']: item.get('color', ''),
                    f['no_referencia_remolque']:   item.get('ref_remolque', ''),
                    f['comentarios']:              item.get('comentarios', ''),
                }
                for i, item in enumerate(grupo)
            }

        materiales = data.get('materiales', []) or []
        if materiales:
            answers[f['grupo_materiales']] = {
                (m['index'] if m.get('index') is not None else -(i + 1)): {
                    f['producto_material']:        m.get('producto', ''),
                    f['lote_material']:            m.get('lote', ''),
                    f['cantidad_material']:        m.get('cant_esperada', ''),
                    f['cantidad_fisica_material']: m.get('cant_fisica', ''),
                    f['peso_material']:            m.get('peso', ''),
                    f['volumen_material']:         m.get('volumen', ''),
                    f['no_referencia_material']:   m.get('ref', ''),
                    f['lugar_material']:           'contenedor' if str(m.get('ref', '')).startswith('contenedor') else 'remolque' if str(m.get('ref', '')).startswith('remolque') else 'vehiculo',
                }
                for i, m in enumerate(materiales)
            }

        documento = data.get('documentos_adicionales') or {}
        if documento:
            idx = documento.get('index')
            key = idx if idx is not None else -1
            answers[f['grupo_fotos_y_documentos']] = {
                key: {
                    f['tipo_de_documento']: documento.get('tipo', '').lower().replace(' ', '_'),
                    f['documento']: [{'file_name': documento['file_name'], 'file_url': documento['file_url']}],
                }
            }

        if data.get('delete_remolques') or data.get('delete_contenedores') or data.get('delete_materiales') or data.get('delete_documentos'):
            self.delete_bitac_transportista_items(record_id, data)

        if answers:
            res = self.lkf_api.patch_multi_record(
                answers=answers,
                form_id=self.BITACORA_TRANSPORTISTAS,
                record_id=[record_id],
            )
            if res.get('status_code') not in [201, 202, 203]:
                self.LKFException({'title': 'Error al guardar registro de bitácora', 'msg': res})
            return res

        return {'status_code': 200, 'msg': 'OK'}

    def delete_bitac_transportista_items(self, record_id, data):
        f = self.bitacora_transportista_fields
        current = None

        delete_remolques    = data.get('delete_remolques', []) or []
        delete_contenedores = data.get('delete_contenedores', []) or []
        delete_materiales   = data.get('delete_materiales', []) or []
        delete_documentos   = data.get('delete_documentos', []) or []

        if delete_remolques or delete_contenedores:
            current = self.get_bitac_transportista_record(record_id)
            indexes_borrar = set(delete_remolques + delete_contenedores)
            nuevo_grupo = [
                {
                    f['tipo_remolque']:             r.get('tipo_remolque', ''),
                    f['num_caja_contenedor']:       r.get('no_caja', ''),
                    f['num_sello']:                 r.get('no_sello', ''),
                    f['placas_de_caja']:            r.get('placas_caja', ''),
                    f['color_remolque_contenedor']: r.get('color', ''),
                    f['no_referencia_remolque']:    r.get('no_referencia_remolque', ''),
                    f['comentarios']:               r.get('comentarios', ''),
                }
                for i, r in enumerate(current.get('remolques', []))
                if i not in indexes_borrar
            ]
            self.cr.update_one(
                {'_id': ObjectId(record_id), 'form_id': self.BITACORA_TRANSPORTISTAS, 'deleted_at': {'$exists': False}},
                {'$set': {f'answers.{f["grupo_remolques"]}': nuevo_grupo}}
            )

        if delete_materiales:
            if current is None:
                current = self.get_bitac_transportista_record(record_id)
            indexes_borrar = set(delete_materiales)
            nuevo_grupo = [
                {
                    f['lugar_material']:           m.get('lugar', ''),
                    f['no_referencia_material']:   m.get('no_referencia', ''),
                    f['producto_material']:        m.get('producto', ''),
                    f['lote_material']:            m.get('lote', ''),
                    f['cantidad_material']:        m.get('cantidad', ''),
                    f['cantidad_fisica_material']: m.get('cantidad_fisica', ''),
                    f['peso_material']:            m.get('peso', ''),
                    f['volumen_material']:         m.get('volumen', ''),
                }
                for i, m in enumerate(current.get('materiales', []))
                if i not in indexes_borrar
            ]
            self.cr.update_one(
                {'_id': ObjectId(record_id), 'form_id': self.BITACORA_TRANSPORTISTAS, 'deleted_at': {'$exists': False}},
                {'$set': {f'answers.{f["grupo_materiales"]}': nuevo_grupo}}
            )

        if delete_documentos:
            if current is None:
                current = self.get_bitac_transportista_record(record_id)
            indexes_borrar = set(delete_documentos)
            nuevo_grupo = [
                {
                    f['tipo_de_documento']: d.get('tipo', ''),
                    f['documento']:         d.get('documento', []),
                }
                for i, d in enumerate(current.get('documentos', []))
                if i not in indexes_borrar
            ]
            self.cr.update_one(
                {'_id': ObjectId(record_id), 'form_id': self.BITACORA_TRANSPORTISTAS, 'deleted_at': {'$exists': False}},
                {'$set': {f'answers.{f["grupo_fotos_y_documentos"]}': nuevo_grupo}}
            )

        return {'status_code': 200, 'msg': 'OK'}

    def save_inspecciones(self, record_id, data):
        f_bit = self.bitacora_transportista_fields

        TRACTOR_CAMPOS = [
            'defensa',
            'motor_caja_de_la_bateria_caja_y_filtros_de_aire',
            'llantas_y_rines_tractor_y_remolque',
            'piso_tractor',
            'tanque_de_combustible',
            'cabina_dormitorio_puertas_y_compartimientos_de_herramientas_seccion_de_pasajero_y_techo',
            'tanque_de_aire',
            'ejes_de_transmision',
            'quinta_rueda',
            'chasis',
            'puertas_externa',
            'piso_externo_trailer_contenedor_caja',
            'paredes_externa',
            'pared_frontal_externa',
            'techo_externo',
            'unidad_de_refrigeracion',
            'escape_mofles',
        ]

        REMOLQUE_CAMPOS = [
            'tanque_de_aire',
            'ejes_de_transmision',
            'quinta_rueda',
            'chasis',
            'puertas_externa',
            'piso_externo_trailer_contenedor_caja',
            'paredes_externa',
            'pared_frontal_externa',
            'techo_externo',
            'unidad_de_refrigeracion',
            'escape_mofles',
        ]

        CONTENEDOR_PUNTO_MAP = {
            'Exterior / parte inferior del contenedor (bastidor o chasis)': 'exterior_parte_inferior_del_contenedor_bastidor_o_chasis',
            'Puertas interiores / exteriores':  'puertas_interiores_exteriores',
            'Pared interior lado derecho':       'pared_interior_lado_derecho',
            'Pared interior lado izquierdo':     'pared_interior_lado_izquierdo',
            'Pared interior frontal':            'pared_interior_frontal',
            'Techo / cubierta superior':         'techo_cubierta_superior',
            'Piso (interior)':                   'piso_interior',
        }

        inspecciones_creadas = []

        for inspeccion in data:
            tipo   = inspeccion.get('tipo', '')
            unidad = inspeccion.get('unidad')
            tipo_label = f'{tipo}_{unidad}' if unidad else tipo

            if tipo == 'tractor':
                puntos = inspeccion.get('puntos', [])
                if not any(p.get('resultado') for p in puntos):
                    continue
                form_id = self.INSPECCION_ENTRADA_CTPAT_TRACTOR
                f_ins   = self.inspeccion_entrada_tractor_fields
                answers = {}
                for punto in puntos:
                    num = punto.get('numero', 0) - 1
                    if 0 <= num < len(TRACTOR_CAMPOS):
                        campo = TRACTOR_CAMPOS[num]
                        resultado = (punto.get('resultado') or '').lower()
                        if resultado:
                            answers[f_ins[campo]] = resultado
                        if punto.get('comentario'):
                            answers[f_ins[f'{campo}_comentarios']] = punto['comentario']
                        if punto.get('fotos'):
                            answers[f_ins[f'{campo}_evidencia']] = punto['fotos']

            elif tipo == 'remolque':
                puntos = inspeccion.get('puntos', [])
                if not any(p.get('resultado') for p in puntos):
                    continue
                form_id = self.INSPECCION_ENTRADA_CTPAT_REMOLQUE
                f_ins   = self.inspeccion_entrada_ctpat_remolque_fields
                answers = {}
                medidas = inspeccion.get('medidas', {}) or {}
                if medidas.get('longitud'):
                    answers[f_ins['longitud_interior']] = medidas['longitud']
                if medidas.get('ancho'):
                    answers[f_ins['ancho_interior']] = medidas['ancho']
                if medidas.get('altura'):
                    answers[f_ins['altura_interior']] = medidas['altura']
                for punto in puntos:
                    num = punto.get('numero', 0) - 1
                    if 0 <= num < len(REMOLQUE_CAMPOS):
                        campo = REMOLQUE_CAMPOS[num]
                        resultado = (punto.get('resultado') or '').lower().replace('í', 'i')
                        if resultado:
                            answers[f_ins[campo]] = resultado
                        if punto.get('comentario'):
                            answers[f_ins[f'{campo}_comentarios']] = punto['comentario']
                        if punto.get('fotos'):
                            answers[f_ins[f'{campo}_evidencia']] = punto['fotos']

            elif tipo == 'contenedor':
                filas   = inspeccion.get('filas', [])
                medidas = inspeccion.get('medidas', {}) or {}
                has_data = (
                    any(fila.get('valores') for fila in filas)
                    or any(medidas.get(k) for k in ['longitud', 'ancho', 'altura'])
                )
                if not has_data:
                    continue
                form_id = self.INSPECCION_ENTRADA_CTPAT_CONTENEDOR
                f_ins   = self.inspeccion_entrada_ctpat_contenedor_fields
                answers = {}
                if medidas.get('longitud'):
                    answers[f_ins['longitud_interior']] = medidas['longitud']
                if medidas.get('ancho'):
                    answers[f_ins['ancho_interior']] = medidas['ancho']
                if medidas.get('altura'):
                    answers[f_ins['altura_interior']] = medidas['altura']
                for fila in filas:
                    campo = CONTENEDOR_PUNTO_MAP.get(fila.get('punto', ''))
                    if not campo:
                        continue
                    valores = fila.get('valores') or []
                    if valores:
                        answers[f_ins[campo]] = [v.lower() for v in valores]
            else:
                continue

            metadata = self.lkf_api.get_metadata(form_id=form_id)
            inspeccion_id = self.object_id()
            metadata.update({
                'id': inspeccion_id,
                'properties': {
                    'device_properties': {
                        'System':  'Script',
                        'Module':  'Accesos',
                        'Process': 'Inspección CTPAT',
                        'Action':  'save_inspecciones',
                        'File':    'accesos/service.py',
                    }
                },
                'answers': answers,
            })
            res = self.lkf_api.post_forms_answers(metadata)
            if res.get('status_code') not in [200, 201, 202]:
                self.LKFException({'title': f'Error al crear inspección {tipo_label}', 'msg': res})
            inspecciones_creadas.append((tipo_label, inspeccion_id))

        if inspecciones_creadas:
            answers_bitacora = {
                f_bit['estatus']: 'inspeccion_entrada',
                f_bit['grupo_inspecciones']: {
                    -(i + 1): {
                        f_bit['tipo_inspeccion']: tipo_label,
                        f_bit['url_inspeccion']:  f'https://app.linkaform.com/#/records/detail/{inspeccion_id}',
                    }
                    for i, (tipo_label, inspeccion_id) in enumerate(inspecciones_creadas)
                }
            }
            res_bit = self.lkf_api.patch_multi_record(
                answers=answers_bitacora,
                form_id=self.BITACORA_TRANSPORTISTAS,
                record_id=[record_id],
            )
            if res_bit.get('status_code') not in [201, 202, 203]:
                self.LKFException({'title': 'Error al actualizar inspecciones en bitácora', 'msg': res_bit})

        return {'status_code': 200, 'msg': 'OK', 'inspecciones_creadas': [t for t, _ in inspecciones_creadas]}

    def save_inspecciones_sello(self, record_id, data):
        f_bit = self.bitacora_transportista_fields
        f     = self.inspeccion_de_sello_fields

        SLOT_MAP = {
            'foto_sello':              f['1_foto_del_sello'],
            'sello_puertas':           f['2_sello_colocado_en_las_puertas'],
            'puertas_completas':       f['3_puertas_completas_del_remolque'],
            'placas_economico':        f['4_placas_o_economico'],
            'identificacion_operador': f['5_identificacion_del_operador'],
        }

        ISO_MAP = {
            'I':  'indicative',
            'S':  'security',
            'H':  'high_security',
            'HS': 'high_security',
        }

        inspecciones_creadas = []

        for inspeccion in data:
            if inspeccion.get('tipo') != 'sello':
                continue

            answers = {}

            if inspeccion.get('no_sello_revisado'):
                answers[f['numero_de_sello_fisico']] = inspeccion['no_sello_revisado']
            if inspeccion.get('no_sello_sistema'):
                answers[f['numero_de_sello_esperado_revisado']] = inspeccion['no_sello_sistema']
            if inspeccion.get('clasificacion_iso'):
                iso_raw = inspeccion['clasificacion_iso']
                answers[f['tipo_de_sello_clasificacion_iso_17712']] = ISO_MAP.get(iso_raw, iso_raw.lower())
            if inspeccion.get('comentario'):
                answers[f['comentarios']] = inspeccion['comentario']

            vvtt = inspeccion.get('vvtt', []) or []
            acciones_verificadas = [v['punto'].lower() for v in vvtt if v.get('verificado')]
            if acciones_verificadas:
                answers[f['matriz_vttt_marca_cada_accion_verificada']] = acciones_verificadas

            for evidencia in inspeccion.get('evidencias', []) or []:
                field_id = SLOT_MAP.get(evidencia.get('slot', ''))
                if field_id and evidencia.get('file_url'):
                    answers[field_id] = [{'file_name': evidencia['file_name'], 'file_url': evidencia['file_url']}]

            metadata = self.lkf_api.get_metadata(form_id=self.INSPECCION_SELLO)
            inspeccion_id = self.object_id()
            metadata.update({
                'id': inspeccion_id,
                'properties': {
                    'device_properties': {
                        'System':  'Script',
                        'Module':  'Accesos',
                        'Process': 'Inspección de Sello',
                        'Action':  'save_inspecciones_sello',
                        'File':    'accesos/service.py',
                    }
                },
                'answers': answers,
            })
            res = self.lkf_api.post_forms_answers(metadata)
            if res.get('status_code') not in [200, 201, 202]:
                self.LKFException({'title': f'Error al crear inspección de sello unidad {inspeccion.get("unidad")}', 'msg': res})

            tipo_label = f'sello_{inspeccion.get("unidad", "")}'
            inspecciones_creadas.append((tipo_label, inspeccion_id))

        if inspecciones_creadas:
            answers_bitacora = {
                f_bit['grupo_inspecciones']: {
                    -(i + 1): {
                        f_bit['tipo_inspeccion']: tipo_label,
                        f_bit['url_inspeccion']:  f'https://app.linkaform.com/#/records/detail/{inspeccion_id}',
                    }
                    for i, (tipo_label, inspeccion_id) in enumerate(inspecciones_creadas)
                }
            }
            res_bit = self.lkf_api.patch_multi_record(
                answers=answers_bitacora,
                form_id=self.BITACORA_TRANSPORTISTAS,
                record_id=[record_id],
            )
            if res_bit.get('status_code') not in [201, 202, 203]:
                self.LKFException({'title': 'Error al actualizar inspecciones de sello en bitácora', 'msg': res_bit})

        return {'status_code': 200, 'msg': 'OK', 'inspecciones_creadas': [t for t, _ in inspecciones_creadas]}

    def create_custom_qr(self, url_for_qr, name_qr, form_id, img_field_id):
        lkf_qr = generar_qr.LKF_QR(self.settings)
        qr_generado = lkf_qr.procesa_qr(url_for_qr, name_qr, form_id, img_field_id)
        return qr_generado

    def create_pass_transportista(self, data):
        f = self.pass_fields_transportista
        metadata = self.lkf_api.get_metadata(form_id=self.PASE_ENTRADA_TRANSPORTISTA)
        metadata.update({
            'id': self.object_id(),
            'properties': {
                'device_properties': {
                    'System': 'Script',
                    'Module': 'Accesos',
                    'Process': 'Pase Transportista',
                    'Action': 'create_pass_transportista',
                    'File': 'accesos/service.py',
                }
            }
        })
        pass_id = metadata['id']

        crea  = data.get('crea_el_pase', {})
        recibe = data.get('recibe_el_pase', {})
        mat   = data.get('material', {})
        lugar = data.get('lugar_entrega_recepcion', {})

        horario = lugar.get('horario_disponible', '') or ''
        hora_inicio, hora_fin = '', ''
        if '-' in horario:
            partes = horario.split('-')
            hora_inicio = partes[0].strip()
            hora_fin    = partes[1].strip()

        dominio = data.get('dominio', 'http://localhost:3000')
        parent_id = self.user.get('parent_id')
        url_pase_transportista = f"{dominio}/transportistas/preview/transportista/{pass_id}?p_id={parent_id}"
        qr_pase_transportista = self.create_custom_qr(
            url_pase_transportista,
            f"qr_code_pase_transportista_{pass_id}",
            self.PASE_ENTRADA_TRANSPORTISTA,
            f['qr_del_pase_transportista'])

        answers = {
            self.pase_entrada_fields['creado_desde']: data.get('creado_desde', 'pase_de_entrada_web'),
            f['tipo_de_operacion']:              data.get('tipo_de_operacion', ''),
            f['nombre_crea_el_pase']:            crea.get('nombre', ''),
            f['email_crea_el_pase']:             crea.get('email', ''),
            f['telefono_crea_el_pase']:          crea.get('telefono', ''),
            f['proveedor']:                      recibe.get('nombre', ''),
            f['proveedor_email']:                recibe.get('email', ''),
            f['proveedor_telefono']:             recibe.get('telefono', ''),
            f['proveedor_cliente_material']:     mat.get('proveedor_cliente', ''),
            f['orden_de_compra']:                mat.get('orden_compra', ''),
            f['grupo_documentos_para_ocr']:       [
                {
                    f['tipo_de_documento']:  doc.get('tipo', ''),
                    f['no_de_documento']:    doc.get('no_doc', ''),
                    f['documento_para_ocr']: [{'file_name': doc.get('file_name', ''), 'file_url': doc.get('file_url', '')}] if doc.get('file_url') else [],
                }
                for doc in mat.get('documentos', [])
            ],
            f['grupo_materiales']:               [
                {
                    f['tipo']:       item.get('tipo', ''),
                    f['cantidad']:   item.get('cantidad', ''),
                    f['volumen']:    item.get('volumen', ''),
                    f['peso']:       item.get('peso', ''),
                    f['sello']:      item.get('sello', ''),
                    f['contenedor']: item.get('contenedor', ''),
                }
                for item in mat.get('items', [])
            ],
            self.Location.UBICACIONES_CAT_OBJ_ID: {
                self.mf['ubicacion']:            lugar.get('ubicacion', ''),
                self.f['address_name']:          [lugar.get('direccion', '')],
            },
            self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID: {
                self.mf['nombre_area_salida']:   lugar.get('area', '')
            },
            f['fecha_pase_transportista_desde']: lugar.get('fecha_pase_transportista_desde', ''),
            f['fecha_pase_transportista_hasta']: lugar.get('fecha_pase_transportista_hasta', ''),
            f['hora_inicial']:                   hora_inicio + ':00' if hora_inicio else '',
            f['hora_final']:                     hora_fin    + ':00' if hora_fin    else '',
            self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                self.mf['nombre_area']: lugar.get('anden', ''),
            },
            f['url_del_pase_transportista']: url_pase_transportista,
            f['qr_del_pase_transportista']: qr_pase_transportista,
            f['estado_transportista']: "pendiente"
        }

        # lugar_recoleccion — solo tipos 2 y 3
        recoleccion = data.get('lugar_recoleccion', {})
        if recoleccion:
            transporte   = recoleccion.get('transporte', {})
            horario_rec  = recoleccion.get('horario', '') or ''
            hora_ini_rec, hora_fin_rec = '', ''
            if '-' in horario_rec:
                partes       = horario_rec.split('-')
                hora_ini_rec = partes[0].strip()
                hora_fin_rec = partes[1].strip()
            answers.update({
                f['lugar_de_recoleccion']:          recoleccion.get('lugar', ''),
                f['direccion_lugar_de_recoleccion']: recoleccion.get('direccion', ''),
                f['fecha_de_recoleccion']:          recoleccion.get('fecha', ''),
                f['hora_inicial_recoleccion']:      hora_ini_rec + ':00' if hora_ini_rec else '',
                f['hora_final_recoleccion']:        hora_fin_rec + ':00' if hora_fin_rec else '',
                f['anden_recoleccion']:             recoleccion.get('anden', ''),
                f['responsable']:                   transporte.get('responsable', ''),
                f['responsable_email']:             transporte.get('email', ''),
                f['responsable_telefono']:          transporte.get('telefono', ''),
            })

        metadata.update({'answers': answers})
        res = self.lkf_api.post_forms_answers(metadata)
        if res.get('status_code') not in [200, 201, 202]:
            self.LKFException({'title': 'Error al crear pase transportista', 'msg': res})
        res['qr_pase_transportista'] = qr_pase_transportista
        return res

    def create_visit_transportista(self, data):
        f = self.bitacora_transportista_fields
        metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_TRANSPORTISTAS)
        metadata.update({
            'properties': {
                'device_properties': {
                    'System': 'Script',
                    'Module': 'Accesos',
                    'Process': 'Bitácora Transportista',
                    'Action': 'create_visit_transportista',
                    'File': 'accesos/service.py',
                }
            }
        })

        vehiculo  = data.get('vehiculo', {}) or {}
        conductor = data.get('conductor', {}) or {}
        embarque  = data.get('embarque', {}) or {}
        firma     = conductor.get('firma') or {}

        tz_name = self.user.get('timezone', 'America/Mexico_City')
        tz = pytz.timezone(tz_name)
        fecha_ingreso = datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

        answers = {
            f['estatus']:               'arribo',
            f['fecha_hora_ingreso']:    fecha_ingreso,
            f['tipo_de_operacion']:     data.get('tipo_operacion', '').lower().replace(' ', '_'),
            f['empresa_transportista']: vehiculo.get('transportista', ''),
            f['procedencia']:           vehiculo.get('procedencia', ''),
            f['tipo_de_vehiculo']:      vehiculo.get('tipo_vehiculo', ''),
            f['placas_de_vehiculo']:    vehiculo.get('placa', ''),
            f['num_eco_num_rotulo']:    vehiculo.get('no_economico', ''),
            f['marca_vehiculo']:        vehiculo.get('marca', ''),
            f['year_vehiculo']:         vehiculo.get('modelo', ''),
            f['color_vehiculo']:        vehiculo.get('color', ''),
            f['conductor']:             conductor.get('nombre', ''),
            f['ayudante']:              conductor.get('acompanante', ''),
            f['num_licencia']:          conductor.get('no_licencia', ''),
            f['vigencia_licencia']:     conductor.get('vigencia_licencia', ''),
            f['rfc_conductor']:         conductor.get('rfc', ''),
            f['firma_conductor']:       firma,
            f['proveedor_cliente']:     embarque.get('proveedor_cliente', ''),
            f['orden_de_compra']:       embarque.get('no_orden_compra', ''),
        }

        remolques    = data.get('remolques', []) or []
        contenedores = data.get('contenedores', []) or []
        grupo = remolques + contenedores
        if grupo:
            answers[f['grupo_remolques']] = [
                {
                    f['tipo_remolque']:             item.get('tipo', ''),
                    f['num_caja_contenedor']:        item.get('no_caja', ''),
                    f['num_sello']:                  item.get('no_sello', ''),
                    f['placas_de_caja']:             item.get('placas', ''),
                    f['color_remolque_contenedor']:  item.get('color', ''),
                    f['no_referencia_remolque']:     item.get('ref_remolque', ''),
                    f['comentarios']:                item.get('comentarios', ''),
                }
                for item in grupo
            ]

        docs = data.get('documentos_adicionales', []) or []
        if docs:
            answers[f['grupo_fotos_y_documentos']] = [
                {
                    f['tipo_de_documento']: doc.get('tipo', ''),
                    f['documento']:         [{'file_name': doc.get('file_name', ''), 'file_url': doc['file_url']}] if doc.get('file_url') else [],
                }
                for doc in docs
            ]

        materiales = data.get('materiales', []) or []
        if materiales:
            answers[f['grupo_materiales']] = [
                {
                    f['producto_material']:        m.get('producto', ''),
                    f['lote_material']:            m.get('lote', ''),
                    f['cantidad_material']:        m.get('cant_esperada', ''),
                    f['cantidad_fisica_material']: m.get('cant_fisica', ''),
                    f['peso_material']:            m.get('peso', ''),
                    f['volumen_material']:         m.get('volumen', ''),
                    f['no_referencia_material']:   m.get('ref', ''),
                    f['lugar_material']:           'contenedor' if str(m.get('ref', '')).startswith('contenedor') else 'remolque' if str(m.get('ref', '')).startswith('remolque') else 'vehiculo',
                }
                for m in materiales
            ]

        metadata.update({'answers': answers})
        res = self.lkf_api.post_forms_answers(metadata)
        if res.get('status_code') not in [200, 201, 202]:
            self.LKFException({'title': 'Error al crear visita de transportista', 'msg': res})
        return res

    def ocr_acceso_transportista(self, image_source,
                                  extra_instructions: str = None,
                                  model: str = 'google/gemini-2.5-flash') -> dict:
        """
        Analiza uno o varios archivos de un acceso de transportista (fotos de
        vehiculo/conductor, licencia, tarjeta de circulacion, BL, pedimento,
        orden de compra, o fotos del contenedor).
        """
        if not self.ai:
            return {'status_code': 400, 'msg': 'OpenRouter no configurado'}

        system = (
            "You are a certified security supervisor and CTPAT compliance specialist at an industrial facility. "
            "You process transport access events by analyzing any combination of: vehicle photos, license plates, "
            "driver photos, driver licenses, vehicle registration cards (tarjeta de circulación), "
            "Bills of Lading, temporary import permits (pedimentos), port release documents, "
            "purchase orders, cargo manifests, and container photos. "
            "All inputs refer to ONE transport access event. "
            "You ONLY extract information that is clearly visible or printed in the provided files. "
            "You NEVER invent, estimate, or hallucinate data. "
            "If a field is not present in any document, return null — never guess. "
            "Always respond with a single valid JSON object and nothing else — "
            "no markdown, no backticks, no explanation, no preamble."
        )

        prompt = (
            "Analyze all provided files (images and/or documents) as a single transport access event. "
            "The files are provided in order: the first is imagen_1, the second is imagen_2, and so on. "
            "Files may include vehicle photos, driver photos, driver licenses, vehicle registration cards, "
            "Bills of Lading, pedimentos, port documents, purchase orders, or container photos. "
            "Extract every field you can find. If a field is absent from all provided files, use null. "
            "IMPORTANT: remolques are trailers/flatbeds pulled by the truck. "
            "contenedores are ISO shipping containers (they have an alphanumeric container number like ECMU7740351). "
            "A remolque may carry a contenedor — if so, list the trailer in remolques and the container in contenedores. "
            "\n\n"
            "Return ONLY a JSON object with this exact structure:\n"
            "{\n"
            '  "vehiculo": {\n'
            '    "transportista": "string — carrier company name, or null",\n'
            '    "procedencia": "string — city or state of origin of the vehicle/shipment if visible on any document, or null",\n'
            '    "tipo_vehiculo": "string — one of: torton, trailer, caja_seca, caja_refrigerada, plataforma, volteo, van, pick_up, camion, pipa, or null",\n'
            '    "marca": "string — truck/tractor brand, or null",\n'
            '    "modelo": "string — truck model year if visible, or null",\n'
            '    "color": "string — main cab color in Spanish, or null",\n'
            '    "placa": "string — tractor/cab license plate exactly as printed, or null",\n'
            '    "no_economico": "string — carrier economic number / rótulo on the vehicle, or null"\n'
            '  },\n'
            '  "conductor": {\n'
            '    "nombre": "string — driver full name from license or permit document, or null",\n'
            '    "no_licencia": "string — driver license number exactly as printed, or null",\n'
            '    "vigencia_licencia": "string — license expiration date in YYYY-MM-DD format, or null",\n'
            '    "rfc": "string — RFC if shown on any document, or null",\n'
            '    "acompanante": "string — co-driver or helper full name if visible on any document, or null"\n'
            '  },\n'
            '  "remolques": [\n'
            '    {\n'
            '      "tipo": "string — trailer type: caja_seca, caja_refrigerada, plataforma, tanque, volteo, or null",\n'
            '      "no_caja": "string — trailer box/unit number, or null",\n'
            '      "no_sello": "string — seal number on the trailer, or null",\n'
            '      "placas": "string — trailer license plate exactly as printed, or null",\n'
            '      "color": "string — trailer color in Spanish, or null",\n'
            '      "comentarios": "string — any relevant note about this trailer, or null"\n'
            '    }\n'
            '  ],\n'
            '  "contenedores": [\n'
            '    {\n'
            '      "tipo": "string — ISO container type: 20GP, 40GP, 40HC, 20RF, 40RF, tanque, or null",\n'
            '      "no_caja": "string — container number exactly as printed, or null",\n'
            '      "no_sello": "string — seal number on the container, or null",\n'
            '      "placas": "string — chassis plate if visible, or null",\n'
            '      "color": "string — container color in Spanish, or null",\n'
            '      "comentarios": "string — any relevant note about this container, or null"\n'
            '    }\n'
            '  ],\n'
            '  "materiales": [\n'
            '    {\n'
            '      "producto": "string — cargo/product description, or null",\n'
            '      "lote": "string — lot or batch number if stated, or null",\n'
            '      "cant_esperada": "string — expected quantity with unit if stated, or null",\n'
            '      "peso": "string — gross weight with unit, or null",\n'
            '      "volumen": "string — volume with unit if stated, or null"\n'
            '    }\n'
            '  ],\n'
            '  "embarque": {\n'
            '    "proveedor_cliente": "string — shipper, supplier or consignee company name, or null",\n'
            '    "no_orden_compra": "string — purchase order / OC number, or null",\n'
            '    "no_bl": "string — Bill of Lading number, or null",\n'
            '    "no_pedimento": "string — pedimento or customs document number, or null",\n'
            '    "no_autorizacion_puerto": "string — port release authorization number, or null",\n'
            '    "origen": "string — place/port of loading or origin, or null",\n'
            '    "destino": "string — place/port of discharge or delivery, or null",\n'
            '    "naviera": "string — shipping line name, or null",\n'
            '    "fecha_embarque": "string — on-board or shipment date (YYYY-MM-DD if possible), or null"\n'
            '  },\n'
            '  "documentos_detectados": [\n'
            '    {\n'
            '      "fuente": "string — imagen_1 / imagen_2 / imagen_3 ... (position of the file in the input list)",\n'
            '      "tipo": "string — one of: identificacion_chofer, foto_conductor, tarjeta_circulacion_vehiculo, carta_porte, factura_orden_compra, foto_placa_vehiculo, evidencia_carga, conocimiento_embarque_bl, otro."\n'
            '    }\n'
            '  ],\n'
            '  "observaciones": "string — CTPAT flags, anomalies, damage, incomplete docs, or anything security-relevant, or null",\n'
            '  "confianza": "string — alto / medio / bajo — overall confidence based on document/image quality"\n'
            "}"
        )

        if extra_instructions:
            prompt += f"\n\nAdditional instructions: {extra_instructions}"

        if isinstance(image_source, str):
            image_source = [image_source]
        elif isinstance(image_source, list):
            image_source = [
                img['file_url'] if isinstance(img, dict) else img
                for img in image_source
            ]

        sources = []
        for src in image_source:
            if isinstance(src, str) and src.lower().endswith('.pdf') and src.startswith('http'):
                r = requests.get(src, timeout=30)
                r.raise_for_status()
                b64 = base64.b64encode(r.content).decode('utf-8')
                sources.append(f'data:application/pdf;base64,{b64}')
            else:
                sources.append(src)

        source_index = {f'imagen_{i+1}': src for i, src in enumerate(image_source)}

        raw_text = self.ai.ocr_general(sources, system, prompt, model=model, max_tokens=2000)

        datos = {}
        if raw_text.get('choices'):
            choices = raw_text['choices']
            if isinstance(choices, list) and len(choices) > 0:
                content = choices[0].get('message', {}).get('content')
                if content:
                    datos = content

        datos = self._ocr_normalizar(datos)

        if isinstance(datos, dict) and isinstance(datos.get('documentos_detectados'), list):
            for doc in datos['documentos_detectados']:
                fuente = doc.get('fuente', '')
                if fuente in source_index:
                    doc['url'] = source_index[fuente]

        errores = self._ocr_validar_id(datos)
        if errores:
            return {
                'status_code': 206,
                'msg': 'Extracción con advertencias',
                'data': datos,
                'warnings': errores,
            }

        return {'status_code': datos.get('status_code', 200), 'msg': 'OK', 'data': datos}

    #! ============================================
    #! Offline services: sincronizacion CouchDB <-> LinkaForm
    #! (migrado de offline_services.py / lkf_addons.addons.accesos.app)
    #!
    #! cr_db (la conexion CouchDB del usuario) se recibe como parametro explicito
    #! en cada metodo en vez de vivir en self.cr_db, ya que "service" es un
    #! singleton compartido entre requests concurrentes. Lo mismo aplica para
    #! `results`/`results_lock`, que en el script original eran self.results/
    #! self.results_lock creados una vez por invocacion del CLI (proceso nuevo
    #! por request); aqui se crean localmente en sync_records() y se pasan
    #! explicitamente para evitar que dos syncs concurrentes compartan el
    #! mismo contador de resultados.
    #!
    #! No se portaron (confirmado codigo muerto/roto en el legacy, nunca
    #! invocado desde ninguna opcion real): process_checks (usa
    #! self.check_area_filter, nunca definido), _process_single_check_record y
    #! create_checks_in_lkf (marcados "revisar si esto no esta repetido",
    #! superados por process_check_area_stage), _process_attachment_upload
    #! singular (superado por _process_attachment_upload_universal), y
    #! _handle_result (utilidad sin ningun llamador).
    #! ============================================

    def clean_db(self, cr_db, status='received', batch_size=300):
        """
        Borra todos los registros con status 'received' en batches
        """
        total_deleted = 0

        while True:
            mango_query = {
                "selector": {
                    "status": status
                },
                "limit": batch_size,
                "fields": ["_id", "_rev"]
            }
            if status == 'all':
                mango_query = {
                    "selector": {
                        "_id": {"$gt": None}
                    },
                    "limit": batch_size,
                    "fields": ["_id", "_rev"]
                }
            result = cr_db.find(mango_query)
            docs = list(result)

            if not docs:
                break

            to_delete = [
                {
                    "_id": doc["_id"],
                    "_rev": doc["_rev"],
                    "_deleted": True
                }
                for doc in docs
            ]

            cr_db.update(to_delete)
            total_deleted += len(to_delete)

        return total_deleted

    def complete_rondines(self, cr_db, records):
        status = {}
        answers = {}
        bad_items = []
        good_items = []

        if not records:
            return {'status_code': 400, 'type': 'error', 'msg': 'No records provided', 'data': {}}

        for item in records:
            _id = item.get('_id', None)
            _rev = item.get('_rev', None)

            if not _id or not _rev:
                bad_items.append(item)
                continue

            record = self.get_couch_record(cr_db, _id=_id, _rev=_rev)

            if record.get('status_code') in [400, 404, 461, 462]:
                bad_items.append(item)
                continue

            if record.get('status_user') == 'completed':
                good_items.append(_id)
                record['inbox'] = False
                record['status'] = 'received'
                record['updated_at'] = self.today_str(date_format='datetime')
                cr_db.save(record)

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

    def get_user_catalogs(self):
        dbs = {}
        try:
            fields_invertido = {v: k for k, v in self.f.items()}
            for catalog_id in self.clave10_catalogs:
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

    def get_couch_record(self, cr_db, _id=None, _rev=None):
        if not _id:
            return {'status_code': 400, 'type': 'error', 'msg': 'ID is required', 'data': {}}

        max_retries = 3
        wait_time = 2

        for attempt in range(max_retries):
            record = cr_db.get(_id, revs_info=True)
            if not record:
                return {'status_code': 404, 'type': 'error', 'msg': 'Record not found', 'data': {}}

            current_rev = record.rev
            all_revs = [r['rev'] for r in record['_revs_info'] if r['status'] == 'available']

            if _rev == current_rev:
                return record
            elif _rev in all_revs:
                return {'status_code': 461, 'type': 'error', 'msg': 'Old revision found', 'data': {}}
            else:
                if attempt < max_retries - 1:
                    time_module.sleep(wait_time)
                else:
                    return {'status_code': 462, 'type': 'error', 'msg': 'Revision not yet propagated', 'data': {}}

    def upload_file_from_couchdb(self, image_data, attachment_name, id_forma_seleccionada, id_field):
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
            return {"error": "Fallo al subir el archivo"}

        try:
            file_url = upload_url['data']['file']
            update_file = {'file_name': attachment_name, 'file_url': file_url}
        except KeyError:
            update_file = {"error": "Fallo al obtener la URL del archivo"}
        finally:
            os.remove(temp_file_path)
        return update_file

    def build_area_inspection_map(self, data):
        """
        Construye:
        {
            'areas': {'nombre area': form_id},
            'inspection_ids': {
                form_id: [schema_preguntas]
            }
        }
        """
        result = {
            'areas': {},
            'inspection_ids': {}
        }
        for item in data:
            area_name = item.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.f['nombre_area'])
            for _, value in item.items():
                form_id = self.unlist(value.get(self.f['form_id']))
                if form_id:
                    result['areas'][area_name] = form_id
                if form_id not in result['inspection_ids']:
                    result['inspection_ids'][form_id] = self.get_form_question_schema(form_id)
        return result

    def get_form_question_schema(self, form_id):
        """
        Obtiene las preguntas del formulario. Solo regresa las preguntas
        aceptadas por el rondin.
        """
        res = self.lkf_api.get_form_id_fields(form_id)
        if not res:
            return []

        form_info = res[0] if isinstance(res, list) else res
        fields = form_info.get('fields', [])

        questions = []
        for field in fields:
            field_type = field.get('field_type')
            if field_type not in self.INSPECTION_ACCEPTED_TYPES:
                continue

            question_schema = {}
            options = field.get('options', [])
            if field_type == 'integer':
                field_properties = field.get('properties', {})
                field_min = field_properties.get('min')
                field_max = field_properties.get('max')
                if field_min or field_max:
                    field_type = 'slider'
                    question_schema['min'] = field_min or 0
                    question_schema['max'] = field_max or field_min + 100

            question_schema.update({
                'pregunta': field.get('label', ''),
                'field_id': field.get('field_id', ''),
                'tipo': field_type,
                'opciones': [opt.get('label') for opt in options if opt.get('label')],
                'required': field.get('required', False),
            })
            questions.append(question_schema)

        return questions

    def assign_user_inbox(self, cr_db, data, record_id, geolocation=None, folio=None):
        """
        Asigna registro a usuario
        """
        geolocation = geolocation or []
        user_id_to_assign = self.unlist(data.get(self.USUARIOS_OBJ_ID, {}).get(self.mf['id_usuario'], ''))
        if not user_id_to_assign:
            self.LKFException({'msg': 'No se encontro id de usuario en el registro a asignar', 'status_code': 400})

        record = cr_db.get(str(record_id))
        user_name_to_assign = data.get(self.USUARIOS_OBJ_ID, {}).get(self.mf['nombre_usuario'], '')
        nombre_recorrido = data.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.mf['nombre_del_recorrido'], '')
        ubicacion_recorrido = data.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.Location.f['location'], '')

        recorrido_info = self.get_info_recorrido(nombre_recorrido, ubicacion_recorrido)

        status = {}
        lat = 0.0
        long = 0.0
        if len(geolocation) > 1:
            lat = geolocation[0]
            long = geolocation[1]
        epoc_today = int(time_module.time())
        format_check_areas = self.get_area_images(data.get(self.f['areas_del_rondin'], []), location=ubicacion_recorrido)
        inpections_by_area = self.build_area_inspection_map(data.get(self.f['areas_del_rondin'], []))

        for i in format_check_areas:
            form_id = inpections_by_area['areas'].get(i['area'])
            i['inspeccion'] = inpections_by_area['inspection_ids'].get(form_id, {})
            i['inspeccion_form_id'] = form_id
            i['checked'] = False
            i['checked_at'] = ''
            i['check_area_id'] = ''

        inbox_record = {
            "_id": record_id,
            "type": "rondin",
            "inbox": True,
            "status": "synced",
            "folio": folio,
            "status_user": "new",
            "created_at": epoc_today,
            "updated_at": self.today_str(date_format='datetime'),
            "created_by_id": user_id_to_assign,
            "created_by_name": user_name_to_assign,
            "geolocation": {
                "lat": lat,
                "long": long
            },
            "record": {
                "user_name": user_name_to_assign,
                "nombre_rondin": nombre_recorrido,
                "ubicacion_rondin": ubicacion_recorrido,
                "tipo_rondin": data.get(self.f['tipo_rondin'], 'qr'),
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
            result = cr_db.save(inbox_record)
            if result:
                status = {'status_code': 200, 'type': 'success', 'msg': 'Inbox assigned successfully', 'data': {
                    'assigned_user_id': user_id_to_assign,
                    'assigned_user': user_name_to_assign,
                    'bitacora_record_id': record_id,
                    'bitacora_ubicacion': ubicacion_recorrido,
                    'bitacora_nombre_rondin': nombre_recorrido,
                    'bitacora_fecha_programada': data.get(self.f['fecha_programacion'], ''),
                }}
        except Exception as e:
            status = {'status_code': 400, 'type': 'error', 'msg': str(e), 'data': {}}
        return status

    def get_info_recorrido(self, nombre_recorrido, ubicacion_recorrido):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.CONFIGURACION_DE_RECORRIDOS_FORM,
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
            if res:
                format_res = self.unlist(res)
        return format_res

    def sync_check_area_to_lkf(self, cr_db, complete_record):
        """
        Sincroniza un registro de couchdb a linkaform
        """
        status = {}
        record_id = complete_record.get('_id', None)
        record = complete_record.get('record', {})
        attachments_result = self.do_attachments(cr_db, complete_record)
        complete_record = attachments_result['updated_record']
        if isinstance(record, dict) and 'status_code' in record:
            return record
        inspeccion = record.get('inspeccion', {})
        inspeccion_form_id = record.get('inspeccion_form_id', '')
        if inspeccion_form_id and inspeccion:
            response_inspeccion = self.create_inspeccion(complete_record, inspeccion_form_id)
            inspeccion_id = response_inspeccion.get('json', {}).get('id', '')
            complete_record['record']['inspeccion_record_id'] = inspeccion_id
            self.insert_images_and_comments_into_inspeccion(complete_record, inspeccion_form_id, inspeccion_id)
        response = self.create_check_area(complete_record)
        if response.get('status_code') in [200, 201, 202, 208]:
            complete_record['status'] = 'received'
            complete_record['folio'] = response.get('json', {}).get('folio', '')
            status = {'status_code': 200, 'type': 'success', 'msg': 'Record received successfully', 'data': {}}
        else:
            if response.get('status_code') == 400:
                last_error = response.get('json', {})
            else:
                last_error = response.get('json', {}).get('error', 'sync_check_area_to_lkf: Error creating record.')

            if response.get('status_code') == 400 and response.get('json', {}).get('code', 0) == 8:
                complete_record['status'] = 'received'
                complete_record['last_error'] = last_error
                status = {'status_code': 208, 'type': 'success', 'msg': 'El id del registro no es único', 'data': {}}
            else:
                status = {'status_code': response.get('status_code', 400), 'type': 'error', 'msg': last_error, 'data': {}}
                complete_record['status'] = 'error'
                complete_record['last_error'] = last_error
        cr_db.save(complete_record)
        return status

    def find_check_area_in_rondines(self, cr_db, check_area_id):
        rondines = cr_db.find({
            "selector": {
                "type": "rondin",
                "record.check_areas": {}
            },
            "limit": 1
        })

        rondin = next(iter(rondines), None)
        if not rondin:
            return None

        check_areas = rondin.get('record', {}).get('check_areas', [])
        for item in check_areas:
            if item.get('check_area_id') == check_area_id:
                return {
                    'rondin_id': rondin.get('_id'),
                    'rondin': rondin,
                    'check_area': item
                }

        return None

    def process_single_check_for_rondin(self, cr_db, rec, results, results_lock):
        """
        Procesa un check_area y regresa info util para agruparla por rondin_id.
        """
        _id = rec.get('_id')
        rondin_id = rec.get('rondin_id') or rec.get('record', {}).get('rondin_id', '')

        res = self.sync_check_area_to_lkf(cr_db, complete_record=rec)

        check_info = {
            "check_id": _id,
            "status_code": res.get('status_code'),
            "ok": res.get('status_code') in [200, 201, 202, 208],
            "record": rec.get('record', {}),
            "folio": rec.get('folio', ''),
            "type": rec.get('type'),
        }

        if not rondin_id:
            check_data = self.find_check_area_in_rondines(cr_db, _id)
            rondin_id = check_data.get('rondin_id') if check_data else None
        return {
            "rondin_id": rondin_id,
            "check": check_info,
            "raw_result": res
        }

    def process_check_area_stage(self, cr_db, check_records, results, results_lock):
        """
        Procesa todos los checks en paralelo.
        Cuando terminan, los agrupa por rondin_id.
        """
        checks_by_rondin = {}
        if not check_records:
            return checks_by_rondin

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {
                executor.submit(self.process_single_check_for_rondin, cr_db, rec, results, results_lock): rec
                for rec in check_records
            }

            for future in as_completed(futures):
                rec = futures[future]
                try:
                    result = future.result()
                    rondin_id = result.get('rondin_id') or 'unknown'

                    checks_by_rondin.setdefault(rondin_id, []).append(result['check'])

                    with results_lock:
                        results["result"].append(result["raw_result"])
                        if result["check"]["ok"]:
                            results["success"] += 1
                        else:
                            results["failed"] += 1
                            results["errors"].append({
                                "id": rec.get('_id'),
                                "error": result["raw_result"].get("msg")
                            })

                except Exception as e:
                    with results_lock:
                        results["failed"] += 1
                        results["errors"].append({
                            "id": rec.get('_id'),
                            "error": str(e)
                        })

        return checks_by_rondin

    def fix_rondines(self):
        fecha_inicio = datetime(2026, 4, 24, 0, 0, 0)
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                "version": {"$gte": 3},
                "created_at": {"$gte": fecha_inicio},
            }},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "answers": 1,
                "other_versions": 1
            }}
        ]
        response = self.cr.aggregate(query)
        for r in response:
            self.fix_rondin(r)

    def fix_rondin(self, record):
        merge_areas = {}
        record_id = record['_id']

        def extract_objectid(uri):
            return uri.strip('/').split('/')[-1]

        def merge_area_into(merge_areas, area):
            """Merge un dict de área al acumulador, sin sobreescribir con vacíos."""
            key = area.get('incidente_area', '').strip()
            if not key:
                return
            if key not in merge_areas:
                merge_areas[key] = {}
            for field, value in area.items():
                if value not in (None, '', [], {}):
                    merge_areas[key][field] = value

        def process_version_record(ver_record, version_label):
            areas = ver_record.get('areas_del_rondin', [])
            if not areas:
                return
            for area in areas:
                merge_area_into(merge_areas, area)

        for v in record.get('other_versions', []):
            ver_id = extract_objectid(v['uri'])
            ver_record = self.get_version_rec(ver_id)
            if not ver_record:
                continue
            process_version_record(ver_record, f"v{v['version']} id={ver_id}")

        process_version_record(record, "actual (form_answers)")
        areas_list = []
        for area in merge_areas.values():
            areas_list.append({
                self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                    self.f['nombre_area']: area.get('incidente_area', '').strip(),
                },
                self.f['fecha_hora_inspeccion_area']: area.get('fecha_hora_inspeccion_area', ''),
                self.f['foto_evidencia_area_rondin']: area.get('foto_evidencia_area_rondin', []),
                self.f['comentario_area_rondin']: area.get('comentario_area_rondin', ''),
                self.f['url_registro_rondin']: area.get('url_registro_rondin', ''),
                self.f['duracion_traslado_area']: area.get('duracion_traslado_area', ''),
            })

        # NOTA: en el legacy esta variable se referenciaba sin haberse calculado
        # nunca (bug — hubiera lanzado NameError). Se ordena aqui igual que en
        # create_bitacora/update_bitacora (por fecha_hora_inspeccion_area).
        all_areas_sorted = sorted(
            areas_list,
            key=lambda x: self.parse_date_for_sorting(x.get(self.f['fecha_hora_inspeccion_area'], ''))
        )

        update_query = {"_id": ObjectId(record_id)}
        update_payload = {
            "$set": {
                f"answers.{self.f['areas_del_rondin']}": all_areas_sorted
            }
        }
        result = self.cr.update_one(update_query, update_payload)
        return result

    def get_version_rec(self, record_id):
        cr_versions = self.net.get_collections(collection='answer_version')
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                "_id": ObjectId(record_id)
            }},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "answers": 1,
                "other_versions": 1
            }}
        ]
        response = self.format_cr(cr_versions.aggregate(query))
        format_response = self.unlist(response)
        return format_response

    def get_checks_by_rondin_id(self, rondin_id):
        """
        Busca en mongodb todos los checks de area que pertenezcan a un rondin.
        """
        rondin_url = f"{self.settings.config.get('WEB_PROTOCOL','https')}://{self.settings.config.get('WEB_HOST','app.linkaform.com')}/#/records/detail/{rondin_id}"
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.CHECK_UBICACIONES,
                f"answers.{self.f['bitacora_rondin_url']}": rondin_url
            }},
            {"$sort": {"created_at": 1}},
            {"$project": {
                "_id": 1,
                "folio": 1,
                "answers": 1,
                "created_at": 1,
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        return {self.unlist(x.get('incidente_area', '')): x for x in response}

    def get_incidencias_from_checks(self, checks_for_rondin):
        """
        Extrae y normaliza las incidencias de una lista de checks de área.
        """
        incidencias = []

        for area_name, check in checks_for_rondin.items():
            fecha_check = check.get('created_at', '')
            grupo_incidencias = check.get('grupo_incidencias_check', [])

            if not grupo_incidencias:
                continue

            for incidencia in grupo_incidencias:
                incidencia.update({
                    'area':             area_name,
                    'fecha_incidencia': fecha_check,
                })
            incidencias += grupo_incidencias
        return incidencias

    def sync_rondin_to_lkf(self, cr_db, rondin_id, rondin_record={}):
        """
        Sincroniza la bitácora del rondín hacia Linkaform usando checks ya
        procesados, o actualiza/cierra el rondin en linkaform.
        """
        status = {}
        bitacora_in_lkf = self.get_bitacora_by_id_safe(rondin_id)
        if not bitacora_in_lkf:
            rondin_record['status'] = 'not_found'
            rondin_record['last_error'] = 'Rondin record not found on users database.'
            cr_db.save(rondin_record)
            return {
                'status_code': 404,
                'type': 'error',
                'msg': f'No se encontró bitácora en LKF para rondin_id={rondin_id}',
                'data': {}
            }

        checks_for_rondin = self.get_checks_by_rondin_id(rondin_id)

        couch_dates = {
            ca.get('area'): ca.get('checked_at')
            for ca in (rondin_record or {}).get('record', {}).get('check_areas', [])
            if ca.get('checked_at')
        }
        for area_name, check in checks_for_rondin.items():
            if couch_dates.get(area_name) and not (check.get('fecha_hora_inspeccion_area') or check.get('fecha_inspeccion_area')):
                check['fecha_hora_inspeccion_area'] = couch_dates[area_name]

        incidencia_for_rondin = self.get_incidencias_from_checks(checks_for_rondin)
        data = rondin_record or {
            '_id': rondin_id,
            'record': {},
            'status_user': ''
        }
        bitacora_response = self.update_bitacora_with_retry(
            cr_db,
            bitacora_in_lkf,
            data,
            incidencia_for_rondin,
            checks_for_rondin
        )
        if rondin_record and bitacora_response.get('status_code') in [200, 201, 202]:
            try:
                rondin_record['status'] = 'received'
                rondin_record['inbox'] = False
            except Exception as e:
                return {
                    'status_code': 409,
                    'type': 'error',
                    'msg': f'Bitácora actualizada pero no se pudo marcar rondín como received: {e}',
                    'data': {'bitacora_response': bitacora_response}
                }

        if bitacora_response.get('status_code') in [200, 201, 202]:
            status = {'status_code': 200, 'type': 'success', 'msg': 'Rondín actualizado correctamente', 'data': {}}
        else:
            status = {'status_code': 400, 'type': 'error', 'msg': bitacora_response, 'data': {}}

        return status

    def process_rondin_stage(self, cr_db, rondin_records, results, results_lock, test=False):
        rondin_results = []

        if not rondin_records:
            return rondin_results

        if test:
            for rec in rondin_records:
                rondin_id = rec.get('_id')
                rondin_results.append(self.sync_rondin_to_lkf(cr_db, rondin_id, rec))
        else:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {}
                for rec in rondin_records:
                    rondin_id = rec.get('_id')
                    futures[executor.submit(self.sync_rondin_to_lkf, cr_db, rondin_id, rec)] = rec

                for future in as_completed(futures):
                    rec = futures[future]
                    try:
                        result = future.result()
                        rondin_results.append(result)

                        with results_lock:
                            results["result"].append(result)
                            if result.get("status_code") in [200, 201, 202, 208]:
                                results["success"] += 1
                            else:
                                results["failed"] += 1
                                results["errors"].append({
                                    "id": rec.get('_id'),
                                    "error": result.get("msg")
                                })

                    except Exception as e:
                        with results_lock:
                            results["failed"] += 1
                            results["errors"].append({
                                "id": rec.get('_id'),
                                "error": str(e)
                            })

        return rondin_results

    def update_rondines_from_checks(self, cr_db, checks_by_rondin, results, results_lock, test=False):
        """
        Actualiza el Rondin, segun los checks que se estan sincronizando. Aplica
        cuando un rondin esta pausado o en progreso pero ya cuenta con checks de
        ubicacion, y se va auto rellenando.
        """
        results_out = []

        if not checks_by_rondin:
            return results_out

        if test:
            for rondin_id in checks_by_rondin:
                results_out.append(self.sync_rondin_to_lkf(cr_db, rondin_id))
        else:
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {
                    executor.submit(self.sync_rondin_to_lkf, cr_db, rondin_id): rondin_id
                    for rondin_id in checks_by_rondin
                }

                for future in as_completed(futures):
                    rondin_id = futures[future]
                    try:
                        result = future.result()
                        results_out.append({
                            'rondin_id': rondin_id,
                            'result': result
                        })

                        with results_lock:
                            results["result"].append(result)
                            if result.get("status_code") in [200, 201, 202, 208]:
                                results["success"] += 1
                            else:
                                results["failed"] += 1
                                results["errors"].append({
                                    "id": rondin_id,
                                    "error": result.get("msg")
                                })

                    except Exception as e:
                        with results_lock:
                            results["failed"] += 1
                            results["errors"].append({
                                "id": rondin_id,
                                "error": str(e)
                            })

        return results_out

    def get_bitacora_by_id_safe(self, record_id):
        try:
            query = [
                {"$match": {
                    "deleted_at": {"$exists": False},
                    "form_id": self.BITACORA_RONDINES,
                    "_id": ObjectId(record_id)
                }},
                {"$project": {
                    "_id": 1,
                    "folio": 1,
                    "answers": 1,
                }}
            ]
            response = self.format_cr(self.cr.aggregate(query))
            format_response = self.unlist(response)
        except Exception:
            format_response = []

        return format_response

    def _format_fecha(self, fecha):
        fecha_str = ""
        if fecha:
            try:
                s = fecha.replace("Z", "+00:00")
                dt = datetime.fromisoformat(s)
                fecha_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                fecha_str = ""
        return fecha_str

    def format_ids_incidencias_to_bitacora(self, data):
        fecha_str = self._format_fecha(data.get('fecha_incidencia'))
        res = {
            self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID: {
                self.f['nombre_area_salida']: data.get('area'),
            },
            self.f['fecha_hora_incidente_bitacora']: data.get('fecha_incidencia', fecha_str),
            self.LISTA_INCIDENCIAS_CAT_OBJ_ID: {
                self.f['categoria']: data.get('categoria', ''),
                self.f['sub_categoria']: data.get('sub_categoria', ''),
                self.f['incidencia']: data.get('incidencia', ''),
            },
            self.f['incidente_open']: data.get('incidente_open', ''),
            self.f['comentario_incidente_bitacora']: data.get('comentario_incidente_bitacora', ''),
            self.f['incidente_accion']: data.get('incidente_accion', ''),
            self.f['incidente_evidencia']: [i for i in data.get('incidente_evidencia', []) if i.get('file_url', '')],
            self.f['incidente_documento']: [i for i in data.get('incidente_documento', []) if i.get('file_url', '')],
        }
        return res

    def format_incidencias_to_bitacora(self, bitacora_in_lkf, new_incidencias):
        """
        Formatea las incidencias para inyectarlas al registro de bitacora de
        rondines, tomando en cuenta las incidencias existentes.
        """
        incidencias_list = []
        incidencias_existentes = bitacora_in_lkf.get('bitacora_rondin_incidencias', [])
        for incidencia in new_incidencias:
            fecha_str = self._format_fecha(incidencia.get('fecha_incidencia'))
            ya_existe = False
            for inc_existente in incidencias_existentes:
                if (inc_existente.get('incidencia') == incidencia.get('incidencia') and
                    inc_existente.get('categoria') == incidencia.get('categoria') and
                    inc_existente.get('nombre_area_salida') == incidencia.get('area') and
                    inc_existente.get('fecha_hora_incidente_bitacora') == fecha_str):
                        ya_existe = True
                        break

            if not ya_existe:
                new_item = self.format_ids_incidencias_to_bitacora(incidencia)
                incidencias_list.append(new_item)

        for incidencia in incidencias_existentes:
            new_item = self.format_ids_incidencias_to_bitacora(incidencia)
            incidencias_list.append(new_item)
        return incidencias_list

    def bitacora_set_area_format(self, bitacora, check):
        """
        Formatea un registro con leyendas al formato que ocupa el grupo
        repetitivo de la bitacora de rondines.
        """
        area_name = self.unlist(check.get('incidente_area', '?'))
        timezone_str = check.get('timezone') or self.user.get('timezone')
        fecha = (check.get('fecha_hora_inspeccion_area')
                 or check.get('fecha_inspeccion_area'))
        if not fecha:
            raw_ts = check.get('created_at')
            if raw_ts:
                try:
                    target_tz = pytz.timezone(timezone_str)
                    dt_utc = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
                    fecha = dt_utc.astimezone(target_tz).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    fecha = raw_ts
        res = {
            self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID: {
                self.mf['nombre_area']: self.unlist(check.get('incidente_area', '')),
            },
            self.f['fecha_inspeccion_area']: fecha,
            self.f['foto_evidencia_area_rondin']: check.get('foto_evidencia_area', []),
            self.f['comentario_area_rondin']: check.get('comentario_check_area', check.get('comentario_area_rondin', '')),
            self.f['url_registro_rondin']: f"{self.settings.config.get('WEB_PROTOCOL','https')}://{self.settings.config.get('WEB_HOST','app.linkaform.com')}/#/records/detail/{check.get('_id')}",
            self.f['duracion_traslado_area']: 0,
        }
        return res

    def create_check_area(self, data):
        """
        Registra Area, realiza check de area
        """
        record = data.get('record', {})
        answers = {}
        metadata = self.lkf_api.get_metadata(form_id=self.CHECK_UBICACIONES)
        metadata.update({
            "properties": {
                "device_properties": {
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de check area",
                    "Action": "create_check_area",
                    "File": "accesos/service.py",
                }
            },
        })
        metadata.update({"id": data.id})
        if isinstance(data.get('geolocation'), dict):
            metadata.update({'geolocation': [data.get('geolocation').get('long'), data.get('geolocation').get('lat')]})

        metadata['start_date'] = record.get('checked_at', data.get('created_at', metadata['start_timestamp']))
        metadata['start_timestamp'] = self.get_epoch(metadata['start_date'])
        metadata['end_timestamp'] = self.get_epoch(data.get('updated_at', metadata['end_timestamp']))
        metadata['timezone'] = data.get('timezone') or metadata.get('timezone') or self.user.get('timezone')
        if data.get('rondin_id'):
            rondin_id = data.get('rondin_id')
            answers[self.f['bitacora_rondin_url']] = f"{self.settings.config.get('WEB_PROTOCOL','https')}://{self.settings.config.get('WEB_HOST','app.linkaform.com')}/#/records/detail/{rondin_id}"

        if record.get('inspeccion_record_id'):
            answers[self.f['url_inspeccion']] = f"{self.settings.config.get('WEB_PROTOCOL','https')}://{self.settings.config.get('WEB_HOST','app.linkaform.com')}/#/records/detail/{record.get('inspeccion_record_id', '')}"

        if data.get('rondin_name'):
            rondin_name = data.get('rondin_name')
            answers[self.CONFIGURACION_RECORRIDOS_OBJ_ID] = {
                self.mf['nombre_del_recorrido']: rondin_name
            }
        answers[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID] = {}
        answers[self.f['check_status']] = "continuar_siguiente_punto_de_inspección"
        answers[self.f['fecha_inspeccion_area']] = record.get('checked_at', data.get('created_at', metadata['start_timestamp']))
        for key, value in record.items():
            if key == 'tag_id':
                answers[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID].update({
                    self.f['area_tag_id']: value,
                    self.Location.f['location']: [record.get('ubicacion', '')],
                    self.Location.f['area']: [record.get('area', '')],
                    self.f['tipo_de_area']: [record.get('tipo_de_area', '')],
                    self.f['area_foto']: [record.get('foto_del_area', '')],
                })
            elif key == 'evidencia_incidencia':
                answers[self.f['foto_evidencia_area']] = value
            elif key == 'documento_incidencia':
                answers[self.f['documento_check']] = value
            elif key == 'incidencias':
                incidencias = record.get('incidencias', [])
                if incidencias:
                    incidencias_list = []
                    for incidencia in incidencias:
                        item = {}
                        if incidencia.get('categoria'):
                            item = {self.LISTA_INCIDENCIAS_CAT_OBJ_ID: {
                                self.f['categoria']: incidencia.get('categoria', ''),
                                self.f['sub_categoria']: incidencia.get('sub_categoria', ''),
                                self.f['incidencia']: incidencia.get('incidencia', ''),
                            }}
                        item.update({
                            self.f['incidente_open']: incidencia.get('incidente_open', ''),
                            self.f['comentario_incidente_bitacora']: incidencia.get('comentario', ''),
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

        metadata.update({'answers': answers})
        res = self.lkf_api.post_forms_answers(metadata)
        return res

    def create_inspeccion(self, data, form_id):
        record = data.get('record', {})
        answers = {}
        metadata = self.lkf_api.get_metadata(form_id=form_id)
        metadata.update({
            "properties": {
                "device_properties": {
                    "System": "Script",
                    "Module": "Accesos",
                    "Process": "Creación de Inspeccion",
                    "Action": "create_inspeccion",
                    "File": "accesos/service.py",
                }
            },
        })
        if isinstance(data.get('geolocation'), dict):
            metadata.update({'geolocation': [data.get('geolocation').get('long'), data.get('geolocation').get('lat')]})

        metadata['start_date'] = record.get('checked_at', data.get('created_at', metadata['start_timestamp']))
        metadata['start_timestamp'] = self.get_epoch(metadata['start_date'])
        metadata['end_timestamp'] = self.get_epoch(data.get('updated_at', metadata['end_timestamp']))
        metadata['timezone'] = data.get('timezone') or metadata.get('timezone') or self.user.get('timezone')

        ubicacion = record.get('ubicacion', '')
        area = record.get('area', '')
        inspeccion = record.get('inspeccion', '')

        answers[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID] = {
            self.mf['ubicacion']: ubicacion,
            self.mf['nombre_area']: area
        }

        for item in inspeccion:
            field_id = item.get('field_id')
            value = item.get('valor', '')
            field_type = item.get('tipo', '')
            if field_type == 'checkbox':
                for idx, item in enumerate(value) if isinstance(value, list) else []:
                    value[idx] = item.lower().replace(' ', '_')
            elif field_type == 'radio':
                value = value.lower().replace(' ', '_')
            answers[field_id] = value

        metadata.update({'answers': answers})
        res = self.lkf_api.post_forms_answers(metadata)
        return res

    def insert_images_and_comments_into_inspeccion(self, record, form_id, record_id):
        images = {}
        comments = {}
        data = record.get('record', {})
        inspection = data.get('inspeccion', [])
        for question in inspection:
            if question.get('field_id'):
                if question.get('foto'):
                    images.update({question.get('field_id'): question.get('foto')})
                if question.get('comentario'):
                    comments.update({question.get('field_id'): question.get('comentario')})

        if not images and not comments:
            return False

        update_fields = {
            "images": images,
            "comments": comments
        }
        update_db = self.cr.update_one({
            '_id': ObjectId(record_id),
            'form_id': form_id,
            'deleted_at': {'$exists': False}
        }, {'$set': update_fields})

        db_res = update_db.raw_result
        return bool(db_res.get('updatedExisting'))

    def delete_rondines(self, cr_db, records):
        status = {}
        answers = {}
        bad_items = []
        good_items = []

        if not records:
            return {'status_code': 400, 'type': 'error', 'msg': 'No records provided', 'data': {}}

        for item in records:
            _id = item.get('_id', None)
            _rev = item.get('_rev', None)

            if not _id or not _rev:
                bad_items.append(item)
                continue

            record = self.get_couch_record(cr_db, _id=_id, _rev=_rev)

            if record.get('status_code') in [400, 404, 461, 462]:
                bad_items.append(item)
                continue

            good_items.append(_id)
            cr_db.delete(record)

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

    def get_user_data(self, user_id):
        query = [{"$match": {
            "deleted_at": {"$exists": False},
            "form_id": 129958,
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

    def reasignar_rondines(self, cr_db, records, user_to_assign):
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

        for item in records:
            _id = item.get('_id', None)
            _rev = item.get('_rev', None)

            if not _id or not _rev:
                bad_items.append(item)
                continue

            record = self.get_couch_record(cr_db, _id=_id, _rev=_rev)

            if record.get('status_code') in [400, 404, 461, 462]:
                bad_items.append(item)
                continue

            if record:
                good_items.append(_id)
                record['inbox'] = False
                record['status_user'] = 'deleted'
                record['status'] = 'received'
                cr_db.save(record)

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
                format_response.append({
                    'guard_id': item.get('created_by_id', 0),
                    'guard_name': item.get('created_by_name', ''),
                    'guard_email': item.get('created_by_email', ''),
                })
        return {'status_code': 200, 'type': 'success', 'msg': 'Active guards retrieved successfully', 'data': format_response}

    def validate_areas_completadas(self, cr_db, areas_completadas, areas_formateadas, data):
        """
        Actualiza data['record']['check_areas'] con el status correspondiente,
        validando lo que el movil reporta como completado contra LKF.
        """
        nombres_en_lkf = set()
        for area in areas_formateadas:
            nombre = area.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.mf['nombre_area'])
            nombre = self.unlist(nombre)
            was_checked = area.get(self.f['fecha_inspeccion_area'])
            if nombre and was_checked:
                nombres_en_lkf.add(nombre)

        check_area_ids = [x['check_area_id'] for x in data['record'].get('check_areas', []) if x['check_area_id']]
        check_areas_status = self.get_check_status(cr_db, check_area_ids)
        for check_area in data['record'].get('check_areas', []):
            status_user = check_area.get('status_user', check_area.get('status_check'))
            check_area_id = check_area.get('check_area_id')

            if status_user == 'completed' and check_area_id not in check_area_ids:
                check_area['status'] = 'not_found'
            elif check_area_id in list(check_areas_status.keys()):
                check_area['status'] = check_areas_status[check_area_id]

        return data

    def get_check_status(self, cr_db, check_id_list):
        records_rondin = cr_db.find({
            "selector": {"_id": {"$in": check_id_list}},
            "fields": ["_id", "status"]
        })
        return {x['_id']: x.get('status') for x in records_rondin}

    def _ensure_date_str(self, value):
        """Convierte un valor a string de fecha 'YYYY-MM-DD HH:MM:SS'.
        Acepta: string ya formateado, epoch int/float, o None/vacío."""
        if not value:
            return ''
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                return ''
        return str(value)

    def update_bitacora_from_sync(self, cr_db, bitacora_in_lkf, data, incidencia_for_rondin, checks_for_rondin):
        """
        Actualiza la bitacora de Rondines a partir de checks/incidencias
        sincronizados desde CouchDB.
        """
        answers = {}
        res = {}
        conf_recorrido = {}
        estatus_bitacora_in_couch = data.get('status_user', '')
        incidencias_list = self.format_incidencias_to_bitacora(bitacora_in_lkf, incidencia_for_rondin)
        answers[self.f['bitacora_rondin_incidencias']] = incidencias_list

        bitacora_in_lkf['areas_del_rondin'] = bitacora_in_lkf.get('areas_del_rondin', [])

        for item in bitacora_in_lkf['areas_del_rondin']:
            nombre_area = item.get('incidente_area')
            if checks_for_rondin.get(nombre_area):
                item.update(checks_for_rondin.pop(nombre_area))

        areas_completadas = [
            area for area in data['record'].get('check_areas', [])
            if area.get('status_check') == 'completed'
        ]
        for nombre_area, new_item in checks_for_rondin.items():
            bitacora_in_lkf['areas_del_rondin'].append(new_item)

        bitacora_in_lkf['areas_del_rondin'] = sorted(
            bitacora_in_lkf['areas_del_rondin'],
            key=lambda x: x.get('fecha_hora_inspeccion_area') or 'zzzz'
        )

        for key, value in bitacora_in_lkf.items():
            if key == 'new_user_complete_name':
                answers[self.USUARIOS_OBJ_ID] = {
                    self.f['new_user_complete_name']: value,
                    self.f['new_user_id']: [self.user['user_id']],
                    self.f['new_user_email']: [self.user['email']]
                }
            elif key == 'fecha_programacion':
                answers[self.f['fecha_programacion']] = self._ensure_date_str(value)
            elif key == 'fecha_inicio_rondin':
                answers[self.f['fecha_inicio_rondin']] = self._ensure_date_str(value)
            elif key == 'fecha_fin_rondin':
                answers[self.f['fecha_fin_rondin']] = self._ensure_date_str(value)
            elif key == 'estatus_del_recorrido' and value:
                answers[self.f['estatus_del_recorrido']] = value
            elif key == 'incidente_location':
                conf_recorrido.update({self.f['ubicacion_recorrido']: value})
            elif key == 'nombre_del_recorrido':
                conf_recorrido.update({self.f['nombre_del_recorrido']: value})
            elif key == 'estatus_del_recorrido':
                answers[self.f['estatus_del_recorrido']] = value
            elif key == 'areas_del_rondin':
                answers[self.f['areas_del_rondin']] = [self.bitacora_set_area_format(bitacora_in_lkf, check) for check in value]

        data = self.validate_areas_completadas(
            cr_db,
            areas_completadas=areas_completadas,
            areas_formateadas=answers[self.f['areas_del_rondin']],
            data=data
        )
        if estatus_bitacora_in_couch == 'in_progress':
            answers[self.f['estatus_del_recorrido']] = 'en_proceso'
        elif estatus_bitacora_in_couch == 'completed':
            answers[self.f['estatus_del_recorrido']] = 'realizado'
        elif estatus_bitacora_in_couch == 'cancel':
            answers[self.f['estatus_del_recorrido']] = 'cancelado'
        else:
            answers[self.f['estatus_del_recorrido']] = 'realizado'

        answers[self.CONFIGURACION_RECORRIDOS_OBJ_ID] = conf_recorrido
        if not answers.get(self.f['fecha_inicio_rondin']):
            answers[self.f['fecha_inicio_rondin']] = data.get('record', {}).get('fecha_inicio', '')

        comentarios_in_couch = data.get('record', {}).get('comentarios_rondin', [])
        comentarios_in_lkf = bitacora_in_lkf.get('grupo_comentarios_generales', [])
        comentarios_existentes = set()
        comentarios_finales = []

        for comentario in comentarios_in_lkf:
            fecha = comentario.get('grupo_comentarios_generales_fecha', '')
            texto = comentario.get('grupo_comentarios_generales_texto', '')
            comentarios_existentes.add((fecha, texto))

        for comentario in comentarios_in_lkf:
            comentarios_finales.append({
                self.f['grupo_comentarios_generales_fecha']: comentario.get('grupo_comentarios_generales_fecha', ''),
                self.f['grupo_comentarios_generales_texto']: comentario.get('grupo_comentarios_generales_texto', '')
            })

        for comentario in comentarios_in_couch:
            fecha = comentario.get('fecha', '')
            texto = comentario.get('texto', '')
            if (fecha, texto) not in comentarios_existentes:
                comentarios_finales.append({
                    self.f['grupo_comentarios_generales_fecha']: fecha,
                    self.f['grupo_comentarios_generales_texto']: texto
                })

        answers[self.f['grupo_comentarios_generales']] = comentarios_finales
        if answers:
            metadata = self.lkf_api.get_metadata(form_id=self.BITACORA_RONDINES)
            metadata.update(self.get_record_by_folio(bitacora_in_lkf.get('folio'), self.BITACORA_RONDINES, select_columns={'_id': 1}, limit=1))

            metadata.update({
                'properties': {
                    "device_properties": {
                        "system": "Addons",
                        "process": "Actualizacion de Bitacora",
                        "accion": 'offline_services_sync',
                        "folio": bitacora_in_lkf.get('folio'),
                        "archive": "accesos/service.py"
                    }
                },
                'answers': answers,
                '_id': bitacora_in_lkf.get('_id')
            })
            res = self.net.patch_forms_answers(metadata)
            if res.get('status_code') == 202:
                data['status'] = 'received'
                data['inbox'] = False
                cr_db.save(data)
        return res

    def update_bitacora_with_retry(self, cr_db, bitacora_in_lkf, data, incidencia_for_rondin, checks_for_rondin, max_retries=5, base_wait=2):
        """
        Reintenta update_bitacora_from_sync en caso de error 208 (registro
        ocupado), con backoff exponencial + jitter.
        """
        for attempt in range(max_retries):
            wait = base_wait * (2 ** attempt) + random.uniform(0, 1)
            wait = .1
            time_module.sleep(wait)

            response = self.update_bitacora_from_sync(cr_db, bitacora_in_lkf, data, incidencia_for_rondin, checks_for_rondin)

            if response.get('status_code') == 208:
                continue

            return response

        return {'status_code': 408, 'type': 'error', 'msg': 'Max retries exceeded after 208 conflicts', 'data': {}}

    def sync_incidence_to_lkf(self, cr_db, record):
        status = {}
        record_id = record.pop('_id', None)
        record_data = record.get('record', {})
        folio = self.get_folio_incidencia(record_id)
        payload = {k: record_data[k] for k in self.incidence_filter.keys() if k in record_data}

        if isinstance(record_data, dict) and 'status_code' in record_data:
            return record_data
        elif folio:
            folio = folio.get('folio', '')
            response = self.update_incidence(payload, folio)
        else:
            payload.update({'record_id': record_id})
            response = self.create_incidence(payload)

        record = cr_db.get(record_id)
        if response.get('status_code') in [200, 201, 202]:
            record['status'] = 'synced'
            record['updated_at'] = self.today_str(date_format='datetime')
            cr_db.save(record)
            status = {'status_code': 200, 'type': 'success', 'msg': 'Record synced successfully', 'data': {}}
        else:
            record['last_error'] = record.get('json', {}).get('error', 'Error al sincronizar incidencia')
            record['status'] = 'error'
            record['updated_at'] = self.today_str(date_format='datetime')
            cr_db.save(record)
            status = {'status_code': 400, 'type': 'error', 'msg': response, 'data': {}}
        return status

    def is_valid_url(self, value):
        return isinstance(value, str) and value.startswith('http')

    def get_extension(self, filename):
        return os.path.splitext(filename or '')[1].lower()

    def infer_field_id(self, filename):
        ext = self.get_extension(filename)
        if ext in self.IMAGE_EXTENSIONS:
            return self.f['foto_evidencia_area']
        return self.f['documento_check']

    def find_pending_media_nodes(self, node, found=None, path='record'):
        """
        Recorre recursivamente dicts/lists y encuentra diccionarios que tengan
        file_path pero no un file_url valido.
        """
        if found is None:
            found = []

        if isinstance(node, dict):
            has_file_path = bool(node.get('file_path'))
            has_valid_url = self.is_valid_url(node.get('file_url', ''))

            if has_file_path and not has_valid_url:
                found.append({'node': node, 'path': path})

            for key, value in node.items():
                self.find_pending_media_nodes(value, found, f'{path}.{key}')

        elif isinstance(node, list):
            for idx, item in enumerate(node):
                self.find_pending_media_nodes(item, found, f'{path}[{idx}]')
        return found

    def _process_attachment_upload_universal(self, cr_db, doc_id, media_node):
        """
        media_node es el diccionario original dentro de record. Si encuentra
        attachment en CouchDB, lo sube a LKF y actualiza el mismo dict.
        """
        attachment_name = media_node.get('name') or media_node.get('file_name')
        file_url = media_node.get('file_url', '')
        file_path = media_node.get('file_path', '')

        if not attachment_name:
            return {'success': False, 'error': 'No se encontró name ni file_name', 'node': media_node}

        if self.is_valid_url(file_url):
            return {'success': True, 'skipped': True, 'reason': 'Ya tenía file_url', 'node': media_node}

        attachment = cr_db.get_attachment(doc_id, attachment_name)
        if not attachment:
            return {'success': False, 'error': f'No se encontró attachment en CouchDB: {attachment_name}', 'node': media_node}

        data = attachment.read()
        field_id = self.infer_field_id(attachment_name)

        upload_result = self.upload_file_from_couchdb(data, attachment_name, self.CHECK_UBICACIONES, field_id)

        if upload_result.get('error'):
            return {'success': False, 'error': upload_result['error'], 'node': media_node}

        media_node['file_name'] = upload_result.get('file_name', attachment_name)
        media_node['file_url'] = upload_result.get('file_url', '')
        return {
            'success': True,
            'file_name': media_node['file_name'],
            'file_url': media_node['file_url'],
            'file_path': file_path,
            'node': media_node
        }

    def do_attachments(self, cr_db, record):
        """
        Sube todos los attachments que se le pasen a Linkaform utilizando hilos
        """
        pending_nodes = self.find_pending_media_nodes(record.get('record'))
        if not pending_nodes:
            return {'updated_record': record, 'uploaded': [], 'errors': [], 'total_found': 0}
        uploaded = []
        errors = []

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [
                executor.submit(self._process_attachment_upload_universal, cr_db, record['_id'], item['node'])
                for item in pending_nodes
            ]

            for future in as_completed(futures):
                result = future.result()
                if result.get('success'):
                    if not result.get('skipped'):
                        uploaded.append(result)
                else:
                    errors.append(result)

        return {
            'updated_record': record,
            'uploaded': uploaded,
            'errors': errors,
            'total_found': len(pending_nodes)
        }

    def get_area_model(self, cr_db, record):
        """
        Traduce un record de CouchDB al formato answers de LKF. record['record']
        contiene los datos del área capturada en la app.
        """
        attachments_result = self.do_attachments(cr_db, record)
        if attachments_result.get('updated_record'):
            record = attachments_result['updated_record']

        data = record.get('record', {})

        nombre_area = data.get('incidente_area')
        area_catalogo = data.get('area_catalogo')
        if not nombre_area and not area_catalogo:
            return {"error": "Nombre de Area Requerido"}

        answers = {}
        answers[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID] = {
            self.f['location']: data.get('incidente_location', ''),
        }
        if area_catalogo:
            answers[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID].update({self.f['nombre_area']: area_catalogo})

        answers[self.configuracion_area['nombre_nueva_area']] = nombre_area

        answers[self.Location.TIPO_AREA_OBJ_ID] = {
            self.f['tipo_de_area']: data.get('tipo_area', ''),
        }

        answers[self.configuracion_area['foto_area']] = data.get('area_foto', [])
        answers[self.configuracion_area['tag_id']] = data.get('area_tag_id', '')
        answers[self.configuracion_area['comentarios']] = data.get('comentario', '')

        return answers

    def config_area(self, cr_db, record):
        if not record:
            return {'status_code': 400, 'type': 'error', 'msg': 'No record provided', 'data': {}}

        _id = record.id
        _rev = record.rev

        if not _id or not _rev:
            return {'status_code': 400, 'type': 'error', 'msg': 'Missing _id or _rev', 'data': {}}

        answers = self.get_area_model(cr_db, record)
        metadata = self.lkf_api.get_metadata(form_id=self.CONFIGURACION_AREA_FORM)
        if record.get('geolocation'):
            metadata['geolocation'] = [record['geolocation']['long'], record['geolocation']['lat']]
        metadata.update({'answers': answers})
        res = self.lkf_api.post_forms_answers(metadata)
        if res.get('status_code') in (200, 201, 202):
            record['status'] = 'received'
            record.pop('last_error', None)
            cr_db.save(record)
            res = {'status_code': 200, 'type': 'success', 'msg': 'Area synced', 'data': {}}
        else:
            record['status'] = 'error'
            if res['status_code'] == 400:
                last_error = res.get('json', {})
            else:
                last_error = res.get('json', {}).get('error', 'Error al crear la configuracon del area')
            if isinstance(last_error, dict):
                last_error = last_error.get('exception', last_error)

            res = {'status_code': 400, 'type': 'error', 'msg': last_error, 'data': {}}
            record['updated_at'] = self.today_str(date_format='datetime')
            record['last_error'] = last_error
            cr_db.save(record)
        return res

    def delete_old_synced_areas(self, cr_db, days=3):
        cutoff = time_module.time() - (days * 86400)
        deleted = 0
        for record in cr_db:
            if record.get('status') != 'synced':
                continue
            if record.get('created_at', 0) < cutoff:
                cr_db.delete(record)
                deleted += 1
        return deleted

    def group_records_by_type(self, records):
        """
        Regresa un diccionario con los registros agrupados por type.
        """
        grouped = {}
        for rec in records:
            r_type = rec.get('type') or 'unknown'
            grouped.setdefault(r_type, []).append(rec)
        return grouped

    def process_stage_in_parallel(self, records, handler, results, results_lock, max_workers=10):
        """
        Procesa en paralelo los registros de una etapa (handler ya trae cr_db
        cerrado sobre si mismo via closure).
        """
        stage_results = []

        if not records:
            return stage_results

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(handler, rec): rec for rec in records}

            for future in as_completed(futures):
                rec = futures[future]
                try:
                    result = future.result()
                    stage_results.append(result)

                    with results_lock:
                        results["result"].append(result)
                        if result.get("status_code") in [200, 201, 202, 208]:
                            results["success"] += 1
                        else:
                            results["failed"] += 1
                            results["errors"].append({"id": rec.get('_id'), "error": result.get("msg")})

                except Exception as e:
                    with results_lock:
                        results["failed"] += 1
                        results["errors"].append({"id": rec.get('_id'), "error": str(e)})

        return stage_results

    def process_area_record(self, cr_db, rec):
        return self.config_area(cr_db, rec)

    def sync_records(self, cr_db, app_records=[], test=False):
        """
        Obtiene todos los registros de couchdb que esten con
        "status_user": "completed" y los procesa segun sea el tipo.
        """
        record_list = []
        records = cr_db.find({
            "selector": {"status_user": "completed", "status": "synced"},
            "limit": 1000
        })
        record_list += list(records)

        # backward compatibility: checks viejos (sin campo "status" o
        # marcados como "synced" via status_check)
        records_check = cr_db.find({
            "selector": {"$and": [
                {"status_check": "completed"},
                {"$or": [{"status": {"$exists": False}}, {"status": "synced"}]}
            ]},
            "limit": 1000
        })
        record_list += list(records_check)

        unique_records = {}
        for rec in record_list:
            unique_records[rec.get('_id')] = rec
        record_list = list(unique_records.values())
        if not record_list:
            return {"results": {"success": 0, "failed": 0, "errors": [], "result": []}, "rondin_results": [], "missing_rondin_results": []}

        results = {"success": 0, "failed": 0, "errors": [], "result": []}
        results_lock = threading.Lock()

        grouped_records = self.group_records_by_type(record_list)

        self.process_stage_in_parallel(
            grouped_records.get('area', []),
            lambda rec: self.process_area_record(cr_db, rec),
            results, results_lock,
            max_workers=10
        )

        # NOTA: en el legacy esta rama referenciaba `acceso_obj`/`record` sin
        # definir (bug — nunca iteraba la lista, hubiera lanzado NameError si
        # alguna vez llegaba un registro tipo "incidencia"). Se corrige
        # iterando cada registro igual que las demas etapas.
        for incidencia_record in grouped_records.get('incidencia', []):
            res = self.sync_incidence_to_lkf(cr_db, incidencia_record)
            with results_lock:
                results["result"].append(res)
                if res.get('status_code') in [200, 201, 202, 208]:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({"id": incidencia_record.get('_id'), "error": res.get('msg')})

        # 1. primero checks
        check_records = grouped_records.get('check_area', [])
        checks_by_rondin = self.process_check_area_stage(cr_db, check_records, results, results_lock)

        # 2. luego rondines explícitos
        rondin_records = grouped_records.get('rondin', [])
        rondin_results = self.process_rondin_stage(cr_db, rondin_records, results, results_lock, test=test)

        # 3. rondines derivados de checks que NO tenían registro rondin explícito en Stage 2
        already_synced = {r.get('_id') for r in rondin_records}
        pending_checks_by_rondin = {rid: cks for rid, cks in checks_by_rondin.items() if rid not in already_synced}
        missing_rondin_results = self.update_rondines_from_checks(cr_db, pending_checks_by_rondin, results, results_lock, test=test)

        return {
            "results": results,
            "rondin_results": rondin_results,
            "missing_rondin_results": missing_rondin_results,
        }
