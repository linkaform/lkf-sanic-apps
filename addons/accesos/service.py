# -*- coding: utf-8 -*-
### Linkaform Modules / Archivo de Módulo ###

import pytz
import logging
import tempfile
import os
import uuid
import simplejson, time
from bson import ObjectId
from datetime import datetime, timedelta, time, date
import time as time_module
from copy import deepcopy
from math import ceil
import urllib.parse
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests
import jwt
import arrow

from pdf2image import convert_from_bytes
from zipfile import ZipFile

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
        employee =  self.get_employee_data(email=self.user.get('email'), get_one=True)
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
            f"{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}":{
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
                        self.TIPO_DE_VEHICULO_OBJ_ID:{
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
        if comment:
            comment_list = []
            for c in comment:
                comment_list.append(
                    {
                        self.bitacora_fields['comentario']:c.get('comentario_pase'),
                        self.bitacora_fields['tipo_comentario'] :c.get('tipo_de_comentario').lower().replace(' ', '_')
                    }
                )
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
        ### Areas
        catalog_id = self.Location.AREAS_DE_LAS_UBICACIONES_CAT_ID
        form_id = self.PASE_ENTRADA
        group_level = 2
        options = {
              "group_level": group_level,
              "startkey": [
                location
              ],
              "endkey": [
                f"{location}\n",
                {}
              ]
            }
        areas = self.lkf_api.catalog_view(catalog_id, form_id, options) 
        ### Aquien Visita
        catalog_id = self.Employee.CONF_AREA_EMPLEADOS_CAT_ID
        visita_a = self.lkf_api.catalog_view(catalog_id, form_id, options) 
        # visita_a = [r.get('key')[group_level-1] for r in visita_a]
        ### Pases de accesos
        res = {
            'Areas': areas,
            'Visita_a': visita_a,
            'Perfiles': self.get_pefiles_walkin(location),
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
                    answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]={self.f['location']:data_gafete.get('ubicacion')}
                    # answers_return[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]={self.f['location']:data_gafete.get('ubicacion')}
                elif data_gafete['area'] and not data_gafete['ubicacion']:
                    answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]={self.f['area']:data_gafete.get('area', "")}
                    # answers_return[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID]={self.f['area']:data_gafete.get('area', "")}
                elif data_gafete['area'] and data_gafete['ubicacion']: 
                    answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID] = {self.f['location']:data_gafete.get('ubicacion'),self.f['area']:data_gafete.get('area', "")}
                    # answers_return[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID] = {self.f['location']:data_gafete.get('ubicacion'),self.f['area']:data_gafete.get('area', "")}
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

        if access_pass.get('estatus',"") == 'vencido':
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
        
        timezone = pytz.timezone('America/Mexico_City')
        fecha_actual = datetime.now(timezone).replace(microsecond=0)
        fecha_caducidad = access_pass.get('fecha_de_caducidad')
        fecha_obj_caducidad = datetime.strptime(fecha_caducidad, "%Y-%m-%d %H:%M:%S")
        fecha_caducidad = timezone.localize(fecha_obj_caducidad)

        # Se agregan 15 minutos como margen de tolerancia
        fecha_caducidad_con_margen = fecha_caducidad + timedelta(minutes=15)

        if fecha_caducidad_con_margen < fecha_actual:
            self.LKFException({'msg':"El pase esta vencido, ya paso su fecha de vigencia.","title":'Advertencia'})
        
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

    def do_checkin(self, location, area, employee_list=[], fotografia=[], check_in_manual={}):
        # Realiza el check-in en una ubicación y área específica.

        if not self.is_boot_available(location, area):
            msg = f"Can not login in to boot on location {location} at the area {area}."
            msg += f"Because '{self.last_check_in.get('employee')}' is logged in."
            self.LKFException(msg)
        if employee_list:
            user_id = [self.user.get('user_id'),] + [x['user_id'] for x in employee_list]
        else:
            user_id = self.user.get('user_id')
        boot_config = self.get_users_by_location_area(
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

        employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
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
                self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID: {
                    self.Location.f['location']: location,
                    self.Location.f['area']: area
                },
                self.f['tipo_guardia']: 'guardia_regular',
                self.checkin_fields['checkin_type']: 'iniciar_turno',
                self.f['image_checkin']: fotografia
            }
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
                resp_create.update({'registro_de_asistencia': 'Correcto'})
            else:
                resp_create.update({'registro_de_asistencia': 'Error'})
        return resp_create

    def do_checkout_aux_guard(self, checkin_id=None, location=None, area=None, guards=[], forzar=False, comments=False):
        """
        Realiza el checkout de los guardias auxiliares especificados en guards.
        """
        employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
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

    def do_checkout(self, checkin_id=None, location=None, area=None, guards=[], forzar=False, comments=False, fotografia=[]):
        # self.get_answer(keys)
        employee =  self.get_employee_data(email=self.user.get('email'), get_one=True)
        timezone = employee.get('cat_timezone', employee.get('timezone', 'America/Monterrey'))
        now_datetime =self.today_str(timezone, date_format='datetime')
        last_chekin = {}
        if not checkin_id:
            if guards:
                last_chekin = self.get_guard_last_checkin(guards)
            elif location or area:
                last_chekin = self.get_last_checkin(location, area)
            checkin_id = last_chekin.get('_id')
        if not checkin_id:
            self.LKFException({
                "msg":"No encontramos un checking valido del cual podemos hacer checkout...", 
                "title":"Una Disculpa!!!"})
        record = self.get_record_by_id(checkin_id)
        checkin_answers = record['answers']
        folio = record['folio']
        area = checkin_answers.get(self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID,{}).get(self.f['area'])
        location = checkin_answers.get(self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID,{}).get(self.f['location'])
        rec_guards = checkin_answers.get(self.checkin_fields['guard_group'])
        if not guards:
            checkin_answers[self.checkin_fields['commentario_checkin_caseta']] = \
                checkin_answers.get(self.checkin_fields['commentario_checkin_caseta'],'')
            # Si no especifica guardas va a cerrar toda la casta
            checkin_answers[self.checkin_fields['checkin_type']] = 'cierre'
            checkin_answers[self.checkin_fields['boot_checkout_date']] = now_datetime
            checkin_answers[self.checkin_fields['forzar_cierre']] = 'regular'
            if comments:
                checkin_answers[self.checkin_fields['commentario_checkin_caseta']] += comments + ' '
            if forzar:
                checkin_answers[self.checkin_fields['commentario_checkin_caseta']] += f"Cerrado por: {employee.get('worker_name')}"
                checkin_answers[self.checkin_fields['forzar_cierre']] = 'forzar'
        if self.is_boot_available(location, area):
            msg = f"Can not make a CHEKOUT on a boot that hasn't checkin. Location: {location} at the area {area}."
            msg += f"You need to checkin first."
            self.LKFException(msg)
        if not checkin_id:
            msg = f"No checking found for this  Location: {location} at the area {area}."
            msg += f"You need to checkin first."
            self.LKFException(msg)

        data = self.lkf_api.get_metadata(self.CHECKIN_CASETAS)
        checkin_answers = self.check_in_out_employees('out', now_datetime, checkin=checkin_answers, employee_list=guards)
        # response = self.lkf_api.patch_multi_record( answers=checkin, form_id=self.CHECKIN_CASETAS, folios=[folio,])
        data['answers'] = checkin_answers

        if fotografia:
            checkin_answers.update({
                self.checkin_fields['fotografia_cierre_turno']: fotografia
            })

        #Verificar si el guardia es un guardia de apoyo para hacer su checkout correctamente
        check_aux_guard = self.check_in_aux_guard()
        if check_aux_guard:
            for user_id_aux, each_user in check_aux_guard.items():
                if user_id_aux == self.unlist(employee.get('usuario_id')) and each_user.get('checkin_position') == 'guardia_de_apoyo':
                    resp = self.do_checkout_aux_guard(guards=[self.unlist(employee.get('usuario_id'))], location=location, area=area)
                    return resp

        response = self.lkf_api.patch_record( data=data, record_id=checkin_id)
        if response.get('status_code') in [200, 201, 202]:
            if employee:
                record_id = self.search_guard_asistance(location, area, self.unlist(employee.get('usuario_id')))
                asistencia_answers = {
                    self.f['foto_cierre_turno']: fotografia,
                    self.checkin_fields['checkin_type']: 'cerrar_turno',
                }
                res = self.lkf_api.patch_multi_record(answers=asistencia_answers, form_id=self.REGISTRO_ASISTENCIA, record_id=record_id)
                if res.get('status_code') in [200, 201, 202]:
                    response.update({'registro_de_asistencia': 'Correcto'})
                else:
                    response.update({'registro_de_asistencia': 'Error'})
        elif response.get('status_code') == 401:
            return self.LKFException({
                "title":"Error de Configuracion",
                "msg":"El guardia NO tiene permisos sobre el formulario de cierre de casetas"})
        return response

    def search_guard_asistance(self, location, area, guard):
        query = [
            {"$match": {
                "deleted_at":{"$exists":False},
                "form_id": self.REGISTRO_ASISTENCIA,
                f"answers.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['location']}": location,
                f"answers.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['area']}": area,
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

    def do_out(self, qr, location, area, gafete_id=None):
        '''
            Realiza el cambio de estatus de la forma de bitacora, relacionada a la salida, como parametro
            es necesesario enviar el nombre del visitante que es el unico dato qu se encuentra en la forma
        '''
        response = False
        last_check_out = self.get_last_user_move(qr, location)
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

    def calcula_total_depositos(self):
        depositos = self.answers.get(self.incidence_fields['datos_deposito_incidencia'],[])
        return sum([x[self.incidence_fields['cantidad']] for x in depositos])

    def catalogos_pase_area(self, location_name):
        user_id= self.user.get("user_id")
        res={
            "areas_by_location" : self.get_areas_by_location(location_name)
        }
        return res

    def catalogos_pase_location(self):
        user_id= self.user.get("user_id")
        res = {}
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CONF_AREA_EMPLEADOS,
        }
        if user_id:
            match_query[f"answers.{self.EMPLOYEE_OBJ_ID}.{self.employee_fields['user_id_id']}"] = user_id

        query = [
            {'$match': match_query },
            {'$unwind': f"$answers.{self.mf['areas_grupo']}"},
            {'$project': {
                'area':f"$answers.{self.mf['areas_grupo']}.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
                'set_as':f"$answers.{self.mf['areas_grupo']}.{self.Employee.f['area_default']}",
            }},
            {'$group': {
                '_id': {
                    'set_as': '$set_as',
                    'area': '$area',
                },
            }},
            {'$project': {
                '_id':0,
                'area':'$_id.area',
                'set_as':'$_id.set_as',
            }}
        ]
        response = self.cr.aggregate(query)
        res = {'ubicaciones_user':[],'ubicaciones_default':[]}
        for x in response:
            if x.get('area') not in res['ubicaciones_user']:
                res['ubicaciones_user'].append(x.get('area'))
            if x.get('set_as')  == 'default':
                if x.get('area') not in res['ubicaciones_default']:
                    res['ubicaciones_default'].append(x.get('area'))
        return res

    def catalagos_pase_no_jwt(self, qr_code):
        cat_vehiculos= self.catalogo_vehiculos({})
        cat_estados= self.catalogo_estados({})
        pass_selected= self.get_pass_custom(qr_code)
        res={"cat_vehiculos":cat_vehiculos, "cat_estados":cat_estados, "pass_selected":pass_selected}
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
        catalog_id = self.TIPO_DE_VEHICULO_ID
        form_id = self.PASE_ENTRADA
        res= self.catalogo_view(catalog_id, form_id, options=options)
        return res

    def catalogo_view(self, catalog_id, form_id, options={}, detail=False):
        catalog_id = catalog_id
        form_id = form_id
        res = self.lkf_api.catalog_view(catalog_id, form_id, options)
        if detail:
            if res and len(res) > 0:
                res = self._labels(res[0])
                res = {k:v[0] for k,v in res.items() if len(v)>0}
        return res

    def catalogo_config_area_empleado(self, bitacora, location=''):
        #TODO Verificar si objetos perdidos tambien necesita solo los empleados de una location
        #TODO Mejorar funcion, de momento funcional
        catalog_id = self.CONF_AREA_EMPLEADOS_CAT_ID
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
        catalog_id = self.CONF_AREA_EMPLEADOS_AP_CAT_ID
        form_id= self.BITACORA_FALLAS
        return self.lkf_api.catalog_view(catalog_id, form_id) 

    def catalogo_tipo_concesion(self,location="", tipo=""):
        catalog_id = self.ACTIVOS_FIJOS_CAT_ID
        form_id= self.CONCESSIONED_ARTICULOS
        options={}
        if location and tipo:
            options = {
                "group_level": 3,
                "startkey": [location,tipo],
                "endkey": [location, f"{tipo}\n"]
            }
        else:
            if location and not tipo:
                options = {
                    "group_level": 2,
                    "startkey": [location],
                    "endkey": [f"{location}\n"]
                }
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
                user_id = int(self.unlist(guard.get(self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID,{})\
                    .get(self.employee_fields['user_id_jefes'],0)))
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
                        self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID : empl_cat,
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
            self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID : {
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
                answers[self.consecionados_fields['status_concesion']] = value
            if  key == 'solicita_concesion':
                answers[self.consecionados_fields['solicita_concesion']] = value
            elif  key == 'persona_nombre_concesion':
                answers[self.consecionados_fields['persona_catalog_concesion']] = { self.mf['nombre_guardia_apoyo'] : value}
            elif  key == 'caseta_concesion':
                answers[self.consecionados_fields['area_catalog_concesion']] = { self.mf['nombre_area_salida']: value}
            elif  key == 'ubicacion_concesion':
                answers[self.consecionados_fields['ubicacion_catalog_concesion']] = { self.mf['ubicacion']: value}
            elif  key == 'area_concesion':
                answers[self.consecionados_fields['equipo_catalog_concesion']] =   { self.consecionados_fields['area_concesion']: value}
            elif  key == 'equipo_concesion':
                answers[self.consecionados_fields['equipo_catalog_concesion']] =   { self.consecionados_fields['equipo_concesion']: value}
            else:
                answers.update({f"{self.consecionados_fields[key]}":value})

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
        employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
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
        employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
        answers = {
            f"{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}":{
                self.f['location']:location,
                self.f['area']:area
            },
            f"{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}":{
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
            "form_id": self.UBICACIONES,
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

    def create_access_pass(self, location, access_pass):
        #---Define Metadata
        metadata = self.lkf_api.get_metadata(form_id=self.PASE_ENTRADA)
        metadata.update({
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

        #---Define Answers
        answers = {}
        perfil_pase = access_pass.get('perfil_pase')
        location_name = access_pass.get('ubicacion')
        if not location:
            location = location_name
        address = self.get_location_address(location_name=location_name)
        access_pass['direccion'] = [address.get('address', '')]
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        timezone = user_data.get('timezone','America/Monterrey')
        now_datetime =self.today_str(timezone, date_format='datetime')
        employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
        company = employee.get('company', 'Soter')
        nombre_visita_a = employee.get('worker_name')

        if(access_pass.get('site', '') == 'accesos'):
            nombre_visita_a = access_pass.get('visita_a')
            access_pass['ubicaciones'] = [location]

        answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {}
        # answers[self.Location.UBICACIONES_CAT_OBJ_ID][self.f['location']] = location
        if access_pass.get('custom') == True :
            answers[self.pase_entrada_fields['tipo_visita_pase']] = access_pass.get('tipo_visita_pase',"")
            answers[self.pase_entrada_fields['fecha_desde_visita']] = access_pass.get('fecha_desde_visita',"")
            answers[self.pase_entrada_fields['fecha_desde_hasta']] = access_pass.get('fecha_desde_hasta',"")
            answers[self.pase_entrada_fields['config_dia_de_acceso']] = access_pass.get('config_dia_de_acceso',"")
            answers[self.pase_entrada_fields['config_dias_acceso']] = access_pass.get('config_dias_acceso',"")
            answers[self.pase_entrada_fields['catalago_autorizado_por']] =  {self.pase_entrada_fields['autorizado_por']:nombre_visita_a}
            answers[self.pase_entrada_fields['status_pase']] = access_pass.get('status_pase',"").lower()
            answers[self.pase_entrada_fields['empresa_pase']] = access_pass.get('empresa',"")
            # answers[self.pase_entrada_fields['ubicacion_cat']] = {self.mf['ubicacion']:access_pass['ubicacion'], self.mf['direccion']:access_pass.get('direccion',"")}
            answers[self.pase_entrada_fields['tema_cita']] = access_pass.get('tema_cita',"") 
            answers[self.pase_entrada_fields['descripcion']] = access_pass.get('descripcion',"") 
            answers[self.pase_entrada_fields['config_limitar_acceso']] = access_pass.get('config_limitar_acceso',"") 

        else:
            answers[self.mf['fecha_desde_visita']] = now_datetime
            answers[self.mf['tipo_visita_pase']] = 'fecha_fija'
        answers[self.pase_entrada_fields['tipo_visita']] = 'alta_de_nuevo_visitante'
        answers[self.pase_entrada_fields['walkin_nombre']] = access_pass.get('nombre')
        answers[self.pase_entrada_fields['walkin_email']] = access_pass.get('email', '')
        answers[self.pase_entrada_fields['walkin_empresa']] = access_pass.get('empresa')
        answers[self.pase_entrada_fields['walkin_fotografia']] = access_pass.get('foto')
        answers[self.pase_entrada_fields['walkin_identificacion']] = access_pass.get('identificacion')
        answers[self.pase_entrada_fields['walkin_telefono']] = access_pass.get('telefono', '')
        answers[self.pase_entrada_fields['status_pase']] = access_pass.get('status_pase',"").lower()
        
        if access_pass.get('ubicaciones'):
            ubicaciones = access_pass.get('ubicaciones',[])
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
                areas = self.get_areas_by_location(location)
                if isinstance(areas, list):
                    for area in areas:
                        todas_areas.append({
                            "nombre_area": area,
                            "commentario_area": "" 
                        })
            print(f"Todas las áreas hasta ahora: {todas_areas}")
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

        print(access_pass.get('areas'))

        #Visita A
        answers[self.mf['grupo_visitados']] = []
        nombre_visita_a = access_pass.get('visita_a') if not nombre_visita_a else nombre_visita_a
        visita_set = {
            self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID:{
                self.mf['nombre_empleado'] : nombre_visita_a,
                }
            }
        options_vistia = {
              "group_level": 3,
              "startkey": [location, nombre_visita_a],
              "endkey": [location, f"{nombre_visita_a}\n",{}],
            }
        cat_visita = self.catalogo_view(self.CONF_AREA_EMPLEADOS_CAT_ID, self.PASE_ENTRADA, options_vistia)
        if len(cat_visita) > 0:
            cat_visita =  {key: [value,] for key, value in cat_visita[0].items() if value}
        else:
            selector = {}
            selector.update({f"answers.{self.mf['nombre_empleado']}": nombre_visita_a})
            fields = ["_id", f"answers.{self.mf['nombre_empleado']}", f"answers.{self.mf['email_visita_a']}", f"answers.{self.mf['id_usuario']}"]

            mango_query = {
                "selector": selector,
                "fields": fields,
                "limit": 1
            }

            row_catalog = self.lkf_api.search_catalog(self.CONF_AREA_EMPLEADOS_CAT_ID, mango_query)
            if row_catalog:
                visita_set[self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID].update({
                    self.mf['nombre_empleado']: nombre_visita_a,
                    self.mf['email_visita_a']: [row_catalog[0].get(self.mf['email_visita_a'], "")],
                    self.mf['id_usuario']: [row_catalog[0].get(self.mf['id_usuario'], "")],
                })

        visita_set[self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID].update(cat_visita)
        answers[self.mf['grupo_visitados']].append(visita_set)

        # Perfil de Pase
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
            # SE AGREGO ESTA PARTE DEL IF PARA CUANDO SE CREAN PASES DE ENTRADA DESDE SOTER, ya que se ocupa que motivo sea un array
            # CUSTOM == TRUE significa que el pase fue creado desde soter en la pantalla pase.html
            if access_pass.get('custom') == True :
                cat_perfil[0][self.mf['motivo']]= [cat_perfil[0].get(self.mf['motivo'])]
            else:
                cat_perfil[0][self.mf['motivo']]= ["Reunión"]
            cat_perfil = cat_perfil[0]
        answers[self.CONFIG_PERFILES_OBJ_ID].update(cat_perfil)
        if answers[self.CONFIG_PERFILES_OBJ_ID].get(self.mf['nombre_permiso']) and \
           type(answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']]) == str:
            answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']] = [answers[self.CONFIG_PERFILES_OBJ_ID][self.mf['nombre_permiso']],]

        #---Valor
        metadata.update({'answers':answers})
        res = self.lkf_api.post_forms_answers(metadata)
        qrcode_to_google_pass = ''
        id_forma = ''
        if res.get("status_code") ==200 or res.get("status_code")==201:
            qrcode_to_google_pass = res.get('json', {}).get('id', '')
            link_info=access_pass.get('link', "")
            docs=""
            
            if link_info:
                for index, d in enumerate(link_info["docs"]): 
                    if(d == "agregarIdentificacion"):
                        docs+="iden"
                    elif(d == "agregarFoto"):
                        docs+="foto"
                    if index==0 :
                        docs+="-"
                link_pass= f"{link_info['link']}?id={res.get('json')['id']}&user={link_info['creado_por_id']}&docs={docs}"
                id_forma = self.PASE_ENTRADA
                id_campo = self.pase_entrada_fields['archivo_invitacion']

                tema_cita = access_pass.get("tema_cita")
                descripcion = access_pass.get("descripcion")
                fecha_desde_visita = access_pass.get("fecha_desde_visita")
                fecha_desde_hasta = access_pass.get("fecha_desde_hasta")
                creado_por_email = access_pass.get("link", {}).get("creado_por_email")
                ubicacion = access_pass.get("ubicacion")
                nombre = access_pass.get("nombre")
                visita_a = access_pass.get("visita_a")
                email = access_pass.get("email")

                start_datetime = datetime.strptime(fecha_desde_visita, "%Y-%m-%d %H:%M:%S")

                if not fecha_desde_hasta:
                    stop_datetime = start_datetime + timedelta(hours=1)
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

                    try:
                        respuesta_ics = self.upload_ics(id_forma, id_campo, meetings=meeting)
                    except Exception as e:
                        print(f"Error al generar o subir el archivo ICS: {e}")
                        respuesta_ics = {}

                    file_name = respuesta_ics.get('file_name', '')
                    file_url = respuesta_ics.get('file_url', '')

                    access_pass_custom={
                        "link":link_pass,
                        "enviar_correo_pre_registro": access_pass.get("enviar_correo_pre_registro",[]),
                        "archivo_invitacion": [
                            {
                                "file_name": f"{file_name}",
                                "file_url": f"{file_url}"
                            }
                        ]
                    }
                else:
                    access_pass_custom={
                        "link":link_pass,
                        "enviar_correo_pre_registro": access_pass.get("enviar_correo_pre_registro",[])
                    }

                data_to_google_pass = {
                    "nombre": access_pass.get("nombre"),
                    "visita_a": access_pass.get("visita_a"),
                    "ubicacion": access_pass.get("ubicaciones"),
                    "address": address.get('address'),
                    "empresa": company,
                    "all_data": access_pass
                }

                google_wallet_pass_url = self.create_class_google_wallet(data=data_to_google_pass, qr_code=qrcode_to_google_pass)
                access_pass_custom.update({
                    "google_wallet_pass_url": google_wallet_pass_url,
                })
                
                self.update_pass(access_pass=access_pass_custom, folio=res.get("json")["id"])
            
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
            "status":'Disponible',
            "guard_on_dutty":'',
            "user_id":'',
            "stated_at":'',
            "fotografia_inicio_turno":[],
            "fotografia_cierre_turno":[]
            }
     
        if last_chekin.get('checkin_type') in ['entrada','apertura']:
            #todo
            #user_id 
            booth_status['status'] = 'No Disponible'
            booth_status['guard_on_dutty'] = last_chekin.get('employee') 
            booth_status['stated_at'] = last_chekin.get('boot_checkin_date')
            booth_status['checkin_id'] = last_chekin['_id']
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
                    f"answers.{self.mf['fecha_entrada']}": {"$gte": f"{today} 00:00:00", "$lte": f"{today} 23:59:59"}
                }},
                {'$project': {
                    '_id': 1,
                    'vehiculos': {"$ifNull": [f"$answers.{self.mf['grupo_vehiculos']}", []]},
                    'id_gafete': f"$answers.{self.GAFETES_CAT_OBJ_ID}.{self.gafetes_fields['gafete_id']}",
                    'status_gafete': f"$answers.{self.mf['status_gafete']}"
                }},
                {'$group': {
                    '_id': None,
                    'total_visitas_dentro': {'$sum': 1},
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
            gafetes_info = resultado[0]['gafetes_info'] if resultado else []
            gafetes_pendientes = sum(1
                for gafete in gafetes_info
                    if gafete.get('id_gafete') and gafete.get('status_gafete', '').lower() != 'entregado'
            )
            
            res['total_vehiculos_dentro'] = total_vehiculos_dentro
            res['in_invitees'] = total_visitas_dentro
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
                    f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.incidence_fields['ubicacion_incidencia']}": location
                }},
                {'$project': {
                    '_id': 1,
                    'acciones_tomadas_incidencia': f"$answers.{self.incidence_fields['acciones_tomadas_incidencia']}",
                }},
                {'$group': {
                    '_id': None,
                    'incidentes_pendientes': {'$sum': {'$cond': [{'$or': [{'$eq': [{'$size': {'$ifNull': ['$acciones_tomadas_incidencia', []]}}, 0]},{'$eq': ['$acciones_tomadas_incidencia', None]}]}, 1, 0]}}
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
                    f"answers.{self.consecionados_fields['status_concesion']}": "abierto",
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
        print('MMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMMM2')
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.CONF_ACCESOS,
            f"answers.{self.Employee.EMPLOYEE_OBJ_ID}.{self.Employee.employee_fields['user_id_id']}":self.user['id'],
            #"answers.677ffe8711c99ee27489d564.638a9a99616398d2e392a9f5":self.user['id'],
        }
        query = [
            {'$match': match_query },
            {'$project': {
                "usuario":f"$answers.{self.conf_accesos_fields['usuario_cat']}",
                "grupos":f"$answers.{self.conf_accesos_fields['grupos']}",
                "menus": f"$answers.{self.conf_accesos_fields['menus']}",
            }},
            {'$limit':1},
        ]
        return self.format_cr_result(self.cr.aggregate(query),  get_one=True)

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
    
        raw_result = self.format_cr_result(self.cr.aggregate(query))
        for raw in raw_result:
            for grupo in raw.get('grupo_requisitos', []):
                #TODO Verficiar el cambio de key
                ubicacion = grupo.get('incidente_location', grupo.get('ubicacion_recorrido', ''))
                if ubicacion in ubicaciones:
                    reqs = grupo.get(self.conf_modulo_seguridad['datos_requeridos'], [])
                    if isinstance(reqs, list):
                        requerimientos.update(reqs)
                    envs = grupo.get(self.conf_modulo_seguridad['envio_por'], [])
                    if isinstance(envs, list):
                        envios.update(envs)
                    if requerimientos == {"identificacion", "fotografia"} and envios == {"correo", "sms"}:
                        break
            if requerimientos == {"identificacion", "fotografia"} and envios == {"correo", "sms"}:
                break
    
        return {
            "ubicaciones": ubicaciones,
            "requerimientos": list(requerimientos),
            "envios": list(envios)
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

    def get_detail_access_pass(self, qr_code):
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
                     f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}",
                'visita_a_puesto': 
                    f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['puesto_empleado']}",
                'visita_a_departamento':
                    f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['departamento_empleado']}",
                'visita_a_user_id':
                    f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['user_id_empleado']}",
                'visita_a_email':
                    f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['email_visita_a']}",
                'visita_a_telefono':
                    f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['telefono_visita_a']}",
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
                'ubicaciones': f"$answers.{self.pase_entrada_fields['ubicaciones']}"                
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
            user_id = self.user.get('id')
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
                    }
            },
            {'$sort':{'updated_at':-1}},
            {'$group':{
                '_id':{
                    'user_id':'$user_id',
                    },
                'name':{'$last':'$name'},
                'location':{'$last':'$location'},
                'area':{'$last':'$area'},
                'checkin_date':{'$last':'$checkin_date'},
                'checkout_date':{'$last':'$checkout_date'},
                'checkin_status':{'$last':'$checkin_status'},
                'checkin_position':{'$last':'$checkin_position'},

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

            }}
            ]
        data = self.format_cr(self.cr.aggregate(query))
        res = {}
        for rec in data:
            status = 'in' if rec.get('checkin_status') in ['in','entrada'] else 'out'
            res[int(rec.get('user_id',0))] = {
                'status':status, 
                'name': rec.get('name'), 
                'user_id': rec.get('user_id'), 
                'location':rec.get('location'),
                'area':rec.get('area'),
                'checkin_date':rec.get('checkin_date'),
                'checkout_date':rec.get('checkout_date'),
                'checkin_position':rec.get('checkin_position')
                }
        return res

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
                    f"answers.{self.f['guard_group']}.{self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['user_id_jefes']}":{'$in':user_ids}
                    })
        if user_ids and type(user_ids) == int:
            unwind_query.update({
                f"answers.{self.f['guard_group']}.{self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['user_id_jefes']}":user_ids
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

    def get_last_user_move(self, qr, location):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_ACCESOS,
            f"answers.{self.mf['codigo_qr']}":qr,
        }
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
            {'$sort':{'folio':-1}},
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
             match_query[f"answers.{self.consecionados_fields['status_concesion']}"] = status

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
                f"answers.{self.consecionados_fields['fecha_concesion']}": {"$gte": dateFrom,"$lte": dateTo},
            })
        elif dateFrom:
            match_query.update({
                f"answers.{self.consecionados_fields['fecha_concesion']}": {"$gte": dateFrom}
            })
        elif dateTo:
            match_query.update({
                f"answers.{self.consecionados_fields['fecha_concesion']}": {"$lte": dateTo}
            })

        query = [
            {'$match': match_query },
            {'$project': {
                "_id" : "$_id",
                "folio": "$folio",
                'status_concesion':f"$answers.{self.consecionados_fields['status_concesion']}",
                'ubicacion_concesion':f"$answers.{self.consecionados_fields['ubicacion_concesion']}",
                'solicita_concesion':f"$answers.{self.consecionados_fields['solicita_concesion']}",
                'persona_nombre_concesion':f"$answers.{self.consecionados_fields['persona_nombre_concesion']}",
                'caseta_concesion':f"$answers.{self.consecionados_fields['caseta_concesion']}",
                'fecha_concesion':f"$answers.{self.consecionados_fields['fecha_concesion']}",
                'equipo_imagen_concesion':f"$answers.{self.consecionados_fields['equipo_imagen_concesion']}",
                'area_concesion':f"$answers.{self.consecionados_fields['area_concesion']}",
                'equipo_concesion':f"$answers.{self.consecionados_fields['equipo_concesion']}",
                'observacion_concesion':f"$answers.{self.consecionados_fields['observacion_concesion']}",
                'fecha_devolucion_concesion':f"$answers.{self.consecionados_fields['fecha_devolucion_concesion']}",
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

    def get_list_bitacora(self, location=None, area=None, prioridades=[], dateFrom='', dateTo='', limit=10, offset=0):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_ACCESOS
        }
        if location:
            match_query.update({f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}":location})
        if area:
            match_query.update({f"answers.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}":area})
        if prioridades:
            match_query[f"answers.{self.bitacora_fields['status_visita']}"] = {"$in": prioridades}

        if dateFrom and dateTo:
            dateFrom = f"{dateFrom} 00:00:00"
            dateTo = f"{dateTo} 23:59:59"
            match_query.update({
                f"answers.{self.mf['fecha_entrada']}": {"$gte": dateFrom, "$lte": dateTo},
            })
        elif dateFrom:
            dateFrom = f"{dateFrom} 00:00:00"
            match_query.update({
                f"answers.{self.mf['fecha_entrada']}": {"$gte": dateFrom}
            })
        elif dateTo:
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
            {'$sort':{'folio':-1}},
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
                'incidente':f"$answers.{self.incidence_fields['incidencia_catalog']}.{self.incidence_fields['incidente']}",

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
            {'$sort':{'folio':-1}},
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

    def get_lista_pase(self, location, status='activo', inActive="true"):
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
        print('query', simplejson.dumps(query, indent=4))
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
    
    def get_my_pases(self, tab_status, limit=10, skip=0, search_name=None):
        employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        employee['timezone'] = user_data.get('timezone','America/Monterrey')
        fecha_hoy = datetime.now(pytz.timezone(employee.get('timezone'))).replace(microsecond=0).astimezone(pytz.utc).replace(tzinfo=None)
        fecha_hoy_formateada = fecha_hoy.strftime('%Y-%m-%d %H:%M:%S')
        match_query = {
            'form_id':self.PASE_ENTRADA,
            'deleted_at':{'$exists':False},
            f"answers.{self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.pase_entrada_fields['autorizado_por']}":employee.get('worker_name') or '',
        }
        if tab_status == "Favoritos":
            match_query.update({f"answers.{self.pase_entrada_fields['favoritos']}":'si'})
        elif tab_status == "Activos":
            match_query.update({f"answers.{self.pase_entrada_fields['status_pase']}":'activo'})
        elif tab_status == "Vencidos":
            match_query.update({f"answers.{self.pase_entrada_fields['status_pase']}":'vencido'})

        if search_name:
            match_query.update({
                f"$or": [
                    {f"answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['nombre_visita']}": {"$regex": search_name, "$options": "i"}},
                    {f"answers.{self.mf['nombre_pase']}": {"$regex": search_name, "$options": "i"}}
                ]
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
                        f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}",
                    'visita_a_puesto': 
                        f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['puesto_empleado']}",
                    'visita_a_departamento':
                        f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['departamento_empleado']}",
                    'visita_a_user_id':
                        f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['user_id_empleado']}",
                    'visita_a_email':
                        f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['email']}",
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
                    'autorizado_por':f"$answers.{self.pase_entrada_fields['autorizado_por']}"
                }
            },
            {'$sort':{'_id':-1}},
        ]
        query.append({'$skip': skip})
        query.append({'$limit': limit})
        records = self.format_cr(self.cr.aggregate(query))
        # print("RECORDS",  simplejson.dumps(records, indent=4))
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
                if d:
                    emp.update({'departamento':d[idx].pop(0) if d[idx] else ""})
                if p:
                    emp.update({'puesto':p[idx].pop(0) if p[idx] else ""})
                if e:
                    emp.update({'user_id':e[idx].pop(0) if e[idx] else ""})
                if u:
                    emp.update({'email': u[idx].pop(0) if u[idx] else ""})
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
        print("data", simplejson.dumps(records, indent=4))
        return  {
            "records": records,
            "total_records": total_count,
            "total_pages": total_pages,
            "actual_page": current_page,
            "records_on_page": len(records)
        }

    def get_pdf(self, qr_code, template_id=584, name_pdf='Pase de Entrada'):
        return self.lkf_api.get_pdf_record(qr_code, template_id = template_id, name_pdf =name_pdf, send_url=True)

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
            }},
            {'$sort':{'folio':-1}},
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
            res[int(rec.get('user_id', 0))] = {
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
        username = self.user.get('username')
        user_id = self.user.get('id')
        config_accesos_user="" #get_config_accesos(user_id)
        user_status = self.get_employee_checkin_status(user_id, as_shift=True,  available=False)
        this_user = user_status.get(user_id)
        if not this_user:
            this_user =  self.Employee.get_employee_data(email=self.user.get('email'), get_one=True)
            this_user['name'] = this_user.get('worker_name','')
        user_booths = []
        guards_positions = self.config_get_guards_positions()
        if not guards_positions:
            self.LKFException({"status_code":400, "msg":'No Existen puestos de guardias configurados.'})
        if this_user and this_user.get('status') == 'out':
            check_aux_guard = self.check_in_aux_guard()

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
            location_employees = {self.chife_guard:{},self.support_guard:[]}
            booth_area = this_user['area']
            booth_location = this_user['location']
            for u_id, each_user in user_status.items():
                if u_id == user_id:
                    location_employees[self.support_guard].append(each_user)
                    guard = each_user
                else:
                    if each_user.get('status') == 'in':
                        location_employees[self.support_guard].append(each_user)
        else:
            # location_employees = {}
            default_booth , user_booths = self.Employee.get_user_booth(search_default=False)
            # location = default_booth.get('location')
            if not booth_location:
                booth_area = default_booth.get('area')
            if not booth_location:
                booth_location = default_booth.get('location')
            if not default_booth:
                return self.LKFException({"status_code":400, "msg":'No booth found or configure for user'})
            location_employees = self.get_booths_guards(booth_location, booth_area, solo_disponibles=True)
            guard = self.get_user_guards(location_employees=location_employees)
            if not guard:
                return self.LKFException({
                    "status_code":400, 
                    "msg":f"Usuario {self.user['user_id']} no confgurado como guardia, favor de revisar su configuracion."}) 
        location_employees = self.set_employee_pic(location_employees)
        support_guards = location_employees.get('guardia_de_apoyo', [])
        user_id = self.user.get('user_id')
        for idx, guard in enumerate(support_guards):
            if guard.get('user_id') == user_id:
                support_guards.pop(idx)
                break
        location_employees['guardia_de_apoyo'] = support_guards
        booth_address = self.Location.get_area_address(booth_location, booth_area)
        notes = self.get_list_notes(booth_location, booth_area, status='abierto')
        load_shift_json["location"] = {
            "name":  booth_location,
            "area": booth_area,
            "city": booth_address.get('city'),
            "state": booth_address.get('state'),
            "address": booth_address.get('address'),
            }
        # guards_online = self.get_guards_booths(booth_location, booth_area)
        load_shift_json["booth_stats"] = self.get_page_stats( booth_area, booth_location, "Turnos")
        load_shift_json["booth_status"] = self.get_booth_status(booth_area, booth_location)
        # load_shift_json["support_guards"] = location_employees[self.support_guard]
        load_shift_json["support_guards"] = location_employees.get(self.support_guard, "")
        load_shift_json["guard"] = self.update_guard_status(guard, this_user)
        load_shift_json["notes"] = notes
        load_shift_json["user_booths"] = user_booths
        load_shift_json['config_accesos_user']=config_accesos_user
        # load_shift_json["guards_online"] = guards_online
        print(simplejson.dumps(load_shift_json, indent=4))
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
                    if usuario.get("user_id") == self.user.get('id'):
                        location_guards = location_employees[clave]
                
        location_employees = location_guards

        for employee in location_employees:
            if employee.get('user_id', 0) == self.user.get('id'):
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
                 self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID:
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
            if access_pass.get('grupo_areas_acceso'):
                for area in access_pass['grupo_areas_acceso']:
                    area['status'] = self.get_area_status(access_pass['ubicacion'], area['nombre_area'])
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
                        f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}",
                    'visita_a_puesto': 
                        f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['puesto_empleado']}",
                    'visita_a_departamento':
                        f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['departamento_empleado']}",
                    'visita_a_user_id':
                        f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['user_id_empleado']}",
                    'visita_a_email':
                        f"$answers.{self.mf['grupo_visitados']}.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['email_empleado']}",
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
                    answers[self.consecionados_fields['ubicacion_catalog_concesion']] = {self.mf['ubicacion']:data_articles['ubicacion_concesion']}
                elif data_articles['area_concesion'] and not data_articles['ubicacion_concesion']:
                    answers[self.consecionados_fields['ubicacion_catalog_concesion']] = {self.mf['nombre_area_salida']:data_articles['area_concesion']}
                elif data_articles['area_concesion'] and data_articles['ubicacion_concesion']: 
                    answers[self.consecionados_fields['ubicacion_catalog_concesion']] = {self.mf['ubicacion']:data_articles['ubicacion_concesion'],
                    self.mf['nombre_area_salida']:data_articles['area_concesion']}
            elif  key == 'persona_nombre_concesion':
                answers[self.consecionados_fields['persona_catalog_concesion']] = { self.mf['nombre_guardia_apoyo'] : value}
            elif  key == 'caseta_concesion':
                answers[self.consecionados_fields['area_catalog_concesion']] = { self.mf['nombre_area_salida']: value}
            elif  key == 'area_concesion':
                dic_prev = answers.get(self.consecionados_fields['equipo_catalog_concesion'],{})
                dic_prev[self.consecionados_fields['area_concesion']] = value 
                answers[self.consecionados_fields['equipo_catalog_concesion']] = dic_prev
            elif  key == 'equipo_concesion':
                dic_prev = answers.get(self.consecionados_fields['equipo_catalog_concesion'],{})
                dic_prev[self.consecionados_fields['equipo_concesion']] = value 
                answers[self.consecionados_fields['equipo_catalog_concesion']] = dic_prev
            else:
                answers.update({f"{self.consecionados_fields[key]}":value})
        if answers or folio:
            return self.lkf_api.patch_multi_record( answers = answers, form_id=self.CONCESSIONED_ARTICULOS, folios=[folio])
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_article_lost(self, data_articles, folio):
        answers = {}
        employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
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
        employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
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
        employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
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
                    self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID: {
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

    def update_guard_status(self, guard, this_user):
        # last_checkin = self.get_user_last_checkin(guard['user_id'])
        status_turn = 'Turno Cerrado'
        if this_user.get('status') == 'in':
            status_turn = 'Turno Abierto'

        guard['turn_start_datetime'] =  this_user.get('checkin_date')
        guard['status_turn'] =  status_turn
        return guard

    def update_guards_checkin(self, data_guard, record_id, location, area):
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))

        timezone = user_data.get('timezone','America/Monterrey')
        now_datetime =self.today_str(timezone, date_format='datetime')
        response = []
        checkin = self.check_in_out_employees('in', now_datetime, checkin={}, 
            employee_list=data_guard, **{'employee_type':self.support_guard})
        for idx, employee in enumerate(checkin.get(self.mf['guard_group'],[])):
            user_id = employee[self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID].get(self.f['user_id_jefes'])
            validate_status = self.get_employee_checkin_status(user_id)
            not_allowed = [uid for uid, u_data in validate_status.items() if u_data['status'] =='in']
            if not_allowed:
                msg = f"El usuario(s) con ids {not_allowed}. Se encuentran actualmente logeado en otra caseta."
                msg += f"Es necesario primero salirse de cualquier caseta antes de querer entrar a una casta"
                self.LKFException({'msg':msg,"title":'Accion Requerida!!!'})
            # checkin = self.checkin_data(employee, location, area, 'in', now_datetime)
            answers = {}
            answers[self.mf['guard_group']] = {'-1':employee}
            response.append(self.lkf_api.patch_multi_record( answers = answers, form_id=self.CHECKIN_CASETAS, record_id=[record_id]))
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
            employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
            timezone = employee.get('cat_timezone', employee.get('timezone', 'America/Monterrey'))
            fecha_hora_str =self.today_str(timezone, date_format='datetime')
            answers.update({
                f"{self.notes_fields['note_close_date']}":fecha_hora_str,
                self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID :{
                    self.employee_fields['worker_name_b']:employee['worker_name'],
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
                    self.TIPO_DE_VEHICULO_OBJ_ID:{
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
                    self.TIPO_DE_VEHICULO_OBJ_ID: {
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

    def update_pass(self, access_pass,folio=None):
        pass_selected= self.get_detail_access_pass(qr_code=folio)
        qr_code= folio
        _folio= pass_selected.get("folio")
        answers={}
        for key, value in access_pass.items():
            if key == 'grupo_vehiculos':
                answers[self.mf['grupo_vehiculos']]={}
                for index, item in enumerate(access_pass.get('grupo_vehiculos',[])):
                    tipo = item.get('tipo',item.get('tipo_vehiculo',''))
                    marca = item.get('marca',item.get('marca_vehiculo',''))
                    modelo = item.get('modelo',item.get('modelo_vehiculo',''))
                    estado = item.get('estado',item.get('nombre_estado',''))
                    placas = item.get('placas',item.get('placas_vehiculo',''))
                    color = item.get('color',item.get('color_vehiculo',''))
                    obj={
                        self.TIPO_DE_VEHICULO_OBJ_ID:{
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
                    obj={
                        self.mf['tipo_equipo']:tipo.lower(),
                        self.mf['nombre_articulo']:nombre,
                        self.mf['marca_articulo']:marca,
                        self.mf['numero_serie']:serie,
                        self.mf['color_articulo']:color,
                        self.mf['modelo_articulo']:modelo,
                    }
                    answers[self.mf['grupo_equipos']][(index+1)*-1]=obj
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
                answers.update({f"{self.pase_entrada_fields[key]}":value})

        print("1ans", simplejson.dumps(answers, indent=4))
        # print(ans)
        employee = self.get_employee_data(email=self.user.get('email'), get_one=True)
        print("empleado", employee)
        if answers:
            res= self.lkf_api.patch_multi_record( answers = answers, form_id=self.PASE_ENTRADA, record_id=[qr_code])
            pdf_to_img = None
            if answers.get(self.pase_entrada_fields['status_pase'], '') == 'activo':
                pdf_to_img = self.update_pass_img(qr_code)
            if res.get('status_code') == 201 or res.get('status_code') == 202 and folio:
                if self.user.get('parent_id') == 7742:
                    pdf = self.lkf_api.get_pdf_record(qr_code, template_id = 553, name_pdf='Pase de Entrada', send_url=True)
                else:
                    pdf = self.lkf_api.get_pdf_record(qr_code, template_id = 584, name_pdf='Pase de Entrada', send_url=True)
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
                res['json'].update({'pdf_to_img': pdf_to_img if pdf_to_img else pass_selected.get('pdf_to_img')})
                res['json'].update({'pdf': pdf})
                return res
            else: 
                return res
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def update_pass_img(self, qr_code=None):
        pdf = self.lkf_api.get_pdf_record(qr_code, template_id = 584, name_pdf='Pase de Entrada', send_url=True)
        pdf_url = pdf.get('json', {}).get('download_url')
        id_forma = self.PASE_ENTRADA
        id_campo_pdf_to_img = self.pase_entrada_fields['pdf_to_img']
        pass_img_url = self.upload_pdf_as_image(id_forma, id_campo_pdf_to_img, pdf_url)
        pass_img_file_name = pass_img_url.get('file_name')
        pass_img_file_url = pass_img_url.get('file_url')
        answers = {
            self.pase_entrada_fields['pdf_to_img']: [{
                'file_name': pass_img_file_name,
                'file_url': pass_img_file_url
            }]
        }
        res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.PASE_ENTRADA, record_id=[qr_code])
        print('pass_img_response', res)
        return [{'file_name': pass_img_file_name, 'file_url': pass_img_file_url}]

    def update_full_pass(self, access_pass,folio=None, qr_code=None, location=None):
        answers = {}
        perfil_pase = access_pass.get('perfil_pase', 'Visita General')
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        timezone = user_data.get('timezone','America/Monterrey')
        now_datetime =self.today_str(timezone, date_format='datetime')
        answers[self.mf['grupo_visitados']] = []
        # answers[self.Location.UBICACIONES_CAT_OBJ_ID] = {}
        # answers[self.Location.UBICACIONES_CAT_OBJ_ID][self.f['location']] = location
        answers[self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID] = {}
        answers[self.CONFIG_PERFILES_OBJ_ID] = {}
        answers[self.VISITA_AUTORIZADA_CAT_OBJ_ID] = {}
        # answers[self.pase_entrada_fields['qr_pase']] = []

        for key, value in access_pass.items():
            if key == 'grupo_vehiculos':
                vehiculos = access_pass.get('grupo_vehiculos',[])
                if vehiculos:
                    list_vehiculos = []
                    for item in vehiculos:
                        tipo = item.get('tipo_vehiculo','')
                        marca = item.get('marca_vehiculo','')
                        modelo = item.get('modelo_vehiculo','')
                        estado = item.get('state','')
                        placas = item.get('placas_vehiculo','')
                        color = item.get('color_vehiculo','')
                        list_vehiculos.append({
                            self.TIPO_DE_VEHICULO_OBJ_ID:{
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
                answers[self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID] = {
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
            elif key == 'visita_a': 
                #Visita A
                answers[self.mf['grupo_visitados']] = []
                visita_a = access_pass.get('visita_a')
                visita_set = {
                    self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID:{
                        self.mf['nombre_empleado'] : visita_a,
                        }
                    }
                options_vistia = {
                      "group_level": 3,
                      "startkey": [location, visita_a],
                      "endkey": [location, f"{visita_a}\n",{}],
                    }
                cat_visita = self.catalogo_view(self.CONF_AREA_EMPLEADOS_CAT_ID, self.PASE_ENTRADA, options_vistia)
                if len(cat_visita) > 0:
                    cat_visita =  {key: [value,] for key, value in cat_visita[0].items() if value}
                visita_set[self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID].update(cat_visita)
                answers[self.mf['grupo_visitados']].append(visita_set)
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
        answers[self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID] = {}
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
                            self.TIPO_DE_VEHICULO_OBJ_ID:{
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
                answers[self.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID] = {
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
                    self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID:{
                        self.mf['nombre_empleado'] : visita_a,
                        }
                    }
                options_vistia = {
                      "group_level": 3,
                      "startkey": [location, visita_a],
                      "endkey": [location, f"{visita_a}\n",{}],
                    }
                cat_visita = self.catalogo_view(self.CONF_AREA_EMPLEADOS_CAT_ID, self.PASE_ENTRADA, options_vistia)
                if len(cat_visita) > 0:
                    cat_visita =  {key: [value,] for key, value in cat_visita[0].items() if value}
                visita_set[self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID].update(cat_visita)
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
                answers[self.consecionados_fields['area_paqueteria']] = value
            elif key == 'ubicacion_paqueteria':
                answers[self.consecionados_fields['ubicacion_paqueteria']] = value
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
        catalog_id = self.CONF_AREA_EMPLEADOS_CAT_ID
        options = {
            'startkey': [location],
            'endkey': [f"{location}\n",{}],
            'group_level':2
        }
        return self.catalogo_view(catalog_id, form_id, options)

    def visita_a_detail(self, location, visita_a):
        form_id = self.PASE_ENTRADA
        catalog_id = self.CONF_AREA_EMPLEADOS_CAT_ID
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
        nombre = data.get('nombre', '')
        ubicaciones_list = data.get('ubicacion', '')
        format_ubicacion = self.format_ubicaciones_to_google_pass(ubicaciones_list)
        address = data.get('address', '')
        visita_a = data.get('visita_a', '')
        empresa = data.get('all_data', {}).get('empresa', '')
        num_accesos = data.get('all_data', {}).get('config_limitar_acceso', 1)
        fecha_desde = data.get('all_data', {}).get('fecha_desde_visita', '')
        fecha_hasta = data.get('all_data', {}).get('fecha_hasta_visita', '')
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
                    "value": f'Visita a: {visita_a}'
                }
            },
            "logo": {
                "sourceUri": {
                    "uri": "https://f001.backblazeb2.com/file/app-linkaform/public-client-126/68600/6076166dfd84fa7ea446b917/2025-04-28T11:11:42.png"
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
    
    def format_ubicaciones_to_google_pass(self, ubicaciones_list):
        if not ubicaciones_list:
            return ''
        if len(ubicaciones_list) == 1:
            return self.unlist(ubicaciones_list)
        if len(ubicaciones_list) == 2:
            return f"{ubicaciones_list[0]} y {ubicaciones_list[1]}"
        return ', '.join(ubicaciones_list[:-1]) + ' y ' + ubicaciones_list[-1]

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
        # breakpoint()

        datos = {}
        if raw_text.get('choices'):
            choices = raw_text['choices']
            if isinstance(choices, list) and len(choices) > 0:
                content = choices[0].get('message', {}).get('content')
                if content:
                    datos = content

        # breakpoint()
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