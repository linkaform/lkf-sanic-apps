# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from linkaform_api import base
from lkf_addons.accesos.app import Accesos
import pytz, simplejson





from sanic import Blueprint
from sanic.request import Request
from sanic.response import json



class Accesos( Accesos):
    print('Entra a acceos utils')

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.f.update({
            'duracion_rondin':'6639b47565d8e5c06fe97cf3',
            'duracion_traslado_area':'6760a9581e31b10a38a22f1f',
            'fecha_inspeccion_area':'6760a908a43b1b0e41abad6b',
            'fecha_inicio_rondin':'6760a8e68cef14ecd7f8b6fe',
            'status_rondin':'6639b2744bb44059fc59eb62',
            'grupo_areas_visitadas':'66462aa5d4a4af2eea07e0d1',
            'nombre_recorrido':'6644fb97e14dcb705407e0ef',
            
            'option_checkin': '663bffc28d00553254f274e0',
            'image_checkin': '6855e761adab5d93274da7d7',
            'comment_checkin': '66a5b9bed0c44910177eb724',
            'comment_checkout': '68798dd1205f333d8f53a1c7',
            'start_shift': '6879828d0234f02649cad390',
            'end_shift': '6879828d0234f02649cad391',
            'foto_end': '6879823d856f580aa0e05a3b',
            
            'dias_libres': '68bb20095035e61c5745de05',
            'nombre_horario': '68b6427cc8f94827ebfed695',
            'hora_entrada': '68b6427cc8f94827ebfed696',
            'hora_salida': '68b6427cc8f94827ebfed697',
            'tolerancia_retardo': '68b6427cc8f94827ebfed698',
            'retardo_maximo': '68b642e2bc17e2713cabe019',
            'grupo_turnos': '68b6427cc8f94827ebfed699',
            'horas_trabajadas': '68d6b0d5f7865907a86c37d7',
            'status_turn': '68d5bbb57691dec5a7640358',
            
            'tipo_guardia': '68acee270f2af5e173b7f92e',
            'nombre_guardia_suplente': '68acb67685a044b5fdd869b2',
            'estatus_guardia': '663bffc28d00553254f274e0',
            'foto_inicio_turno': '6855e761adab5d93274da7d7',
            'foto_cierre_turno': '6879823d856f580aa0e05a3b',
            'fecha_inicio_turno': '6879828d0234f02649cad390',
            'fecha_cierre_turno': '6879828d0234f02649cad391',
            'comentario_inicio_turno': '66a5b9bed0c44910177eb724',
            'comentario_cierre_turno': '68798dd1205f333d8f53a1c7',
            'nombre_horario': '68b6427cc8f94827ebfed695',
            'hora_entrada': '68b6427cc8f94827ebfed696',
            'hora_salida': '68b6427cc8f94827ebfed697',
            'dias_de_la_semana': '68b861ba34290efdd49ab24f',
            'tolerancia_retardo': '68b6427cc8f94827ebfed698',
            'retardo_maximo': '68b642e2bc17e2713cabe019',
            'grupo_ubicaciones_horario': '68b6427cc8f94827ebfed699',
            'dias_libres_empleado': '68bb20095035e61c5745de05',
            'duracion_estimada': '6854459836ea891d9d2be7d9',
        })

        #BORRAR
        self.CONFIGURACION_RECORRIDOS = self.lkm.catalog_id('configuracion_de_recorridos')
        self.CONFIGURACION_RECORRIDOS_ID = self.CONFIGURACION_RECORRIDOS.get('id')
        self.CONFIGURACION_RECORRIDOS_OBJ_ID = self.CONFIGURACION_RECORRIDOS.get('obj_id')
        self.REGISTRO_ASISTENCIA = self.lkm.form_id('registro_de_asistencia','id')

        # self.bitacora_fields.update({
        #     "catalogo_pase_entrada": "66a83ad652d2643c97489d31",
        #     "gafete_catalog": "66a83ace56d1e741159ce114"
        # })

        # self.consecionados_fields.update({
        #     "catalogo_ubicacion_concesion": "66a83a74de752e12018fbc3c",
        # })

        self.CONFIGURACION_DE_RECORRIDOS_FORM = self.lkm.form_id('configuracion_de_recorridos','id')

        self.f.update({
            'areas_del_rondin': '66462aa5d4a4af2eea07e0d1',
            'comentario_area_rondin': '66462b9d7124d1540f962088',
            'comentario_check_area': '681144fb0d423e25b42818d4',
            'estatus_del_recorrido': '6639b2744bb44059fc59eb62',
            'fecha_hora_inspeccion_area': '6760a908a43b1b0e41abad6b',
            'fecha_programacion':'6760a8e68cef14ecd7f8b6fe',
            'foto_evidencia_area': '681144fb0d423e25b42818d2',
            'foto_evidencia_area_rondin': '66462b9d7124d1540f962087',
            'grupo_de_areas_recorrido': '6645052ef8bc829a5ccafaf5',
            'nombre_area':'663e5d44f5b8a7ce8211ed0f',
            'nombre_del_recorrido': '6645050d873fc2d733961eba',
            'nombre_del_recorrido_en_catalog': '6644fb97e14dcb705407e0ef',
            'ubicacion_recorrido': '663e5c57f5b8a7ce8211ed0b',
            'fecha_inicio_rondin': '6818ea068a7f3446f1bae3b3',
            'fecha_fin_rondin': '6760a8e68cef14ecd7f8b6ff',
            'check_status': '681fa6a8d916c74b691e174b',
            'grupo_incidencias_check': '681144fb0d423e25b42818d3',
            'incidente_open': '6811455664dc22ecae83f75b',
            'incidente_comentario': '681145323d9b5fa2e16e35cc',
            'incidente_area': '663e5d44f5b8a7ce8211ed0f',
            'incidente_location': '663e5c57f5b8a7ce8211ed0b',
            'incidente_evidencia': '681145323d9b5fa2e16e35cd',
            'incidente_documento': '685063ba36910b2da9952697',
            'url_registro_rondin': '6750adb2936622aecd075607',
            'bitacora_rondin_incidencias': '686468a637d014b9e0ab5090',
            'tipo_de_incidencia': '663973809fa65cafa759eb97'
        })

    def get_config_accesos(self):
        response = []
        print('AAAAA === HERDACION....')
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
        # print('cr', self.cr)
        # print('query><<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<', simplejson.dumps(query, indent=2))
        return self.format_cr_result(self.cr.aggregate(query),  get_one=True)

    def get_cantidades_de_pases(self, x_empresa=False):
        print('entra a get_cantidades_de_pases')
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.PASE_ENTRADA,
        }

        proyect_fields = {
            '_id':1,
            'folio': f"$folio",
            'estatus':f"$answers.{self.pase_entrada_fields['status_pase']}",
            'empresa': { "$first" : f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['empresa']}"},
            'nombre': f"$answers.{self.mf['nombre_pase']}",
            'nombre_perfil': f"$answers.{self.pase_entrada_fields['nombre_perfil']}",
            'fecha_hasta_pase': f"$answers.{self.pase_entrada_fields['fecha_hasta_pase']}",
            'created_at': 1
        }

        match_query.update({f"answers.{self.pase_entrada_fields['status_pase']}":{'$exists': True}})

        post_project_match = {}

        group_by = {
                '_id':{
                    'estatus': '$estatus',
                    },
                'cantidad': {'$sum': 1},
                }
        
        if x_empresa:
            post_project_match = {
                "$and": [
                    {'empresa': {"$ne": None}},
                    {'empresa': {"$ne": ""}}
                ]
            }

            group_by = {
                '_id':{
                    'empresa':'$empresa',
                    'estatus': '$estatus',
                    },
                'cantidad': {'$sum': 1},
            }

        query = [
            {'$match': match_query },
            {'$project': proyect_fields},
            {'$match': post_project_match},
            {'$group': group_by}
        ]

        records = self.format_cr(self.cr.aggregate(query))
        print('/////////records', records)
        return  records
    
    def get_cantidades_de_pases_x_persona(self, contratista=None):
        print('entra a get_cantidades_de_pases_x_persona')
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.PASE_ENTRADA,
        }

        if contratista:
            match_query.update({f"answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['empresa']}":contratista})

        proyect_fields = {
            '_id':1,
            'folio': f"$folio",
            'estatus':f"$answers.{self.pase_entrada_fields['status_pase']}",
            'empresa': { "$first" : f"$answers.{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['empresa']}"},
            'nombre': f"$answers.{self.mf['nombre_pase']}",
            'nombre_perfil': f"$answers.{self.pase_entrada_fields['nombre_perfil']}",
            'fecha_hasta_pase': f"$answers.{self.pase_entrada_fields['fecha_hasta_pase']}",
            'created_at': 1
        }

        match_query.update({f"answers.{self.pase_entrada_fields['status_pase']}":{'$exists': True}})

        group_by = {
                '_id':{
                    'folio':'$folio',
                    'nombre': '$nombre',
                    'empresa': '$empresa',
                    'nombre_perfil': '$nombre_perfil',
                    'fecha_hasta_pase': '$fecha_hasta_pase',
                    }
                }
        

        query = [
            {'$match': match_query },
            {'$project': proyect_fields},
            {'$group': group_by}
        ]

        records = self.format_cr(self.cr.aggregate(query))
        print('/////////records', records)
        return  records
    
    def get_catalogo_paquetes(self):
        catalog_id = self.PROVEEDORES_CAT_ID
        form_id= self.PAQUETERIA
        return self.lkf_api.catalog_view(catalog_id, form_id) 

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
                answers[self.UBICACIONES_CAT_OBJ_ID] = { self.mf['ubicacion']: value}
            elif  key == 'area_paqueteria':
                 answers[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID] = { self.mf['nombre_area']: value}
            elif  key == 'guardado_en_paqueteria':
                answers[self.LOCKERS_CAT_OBJ_ID] ={self.mf['locker_id']:value} 
            elif key == 'proveedor':
                answers[self.PROVEEDORES_CAT_OBJ_ID] = {self.paquetes_fields['proveedor']:value}
            elif key == 'quien_recibe_paqueteria':
                answers[self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID] = {self.mf['nombre_empleado']:value}
            else:
                answers.update({f"{self.paquetes_fields[key]}":value})
        metadata.update({'answers':answers})
        res=self.lkf_api.post_forms_answers(metadata)
        return res

    def update_paquete(self, data_paquete, folio):
        #---Define Answers
        answers = {}
        for key, value in data_paquete.items():
            if  key == 'ubicacion_perdido':
                answers[self.consecionados_fields['ubicacion_catalog_concesion']] = { self.mf['ubicacion']: value}
            elif  key == 'area_paqueteria':
                 answers[self.consecionados_fields['area_catalog_concesion']] = { self.mf['nombre_area_salida']: value}
            elif  key == 'guardado_en_paqueteria':
                answers[self.LOCKERS_CAT_OBJ_ID] ={self.mf['locker_id']:value} 
            elif key == 'proveedor':
                answers[self.PROVEEDORES_CAT_OBJ_ID] = {self.paquetes_fields['proveedor']:value}
            elif key == 'quien_recibe_paqueteria':
                answers[self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID] = {self.mf['nombre_empleado']:value}
            else:
                answers.update({f"{self.paquetes_fields[key]}":value})
        if answers or folio:
            return self.lkf_api.patch_multi_record( answers = answers, form_id=self.PAQUETERIA, folios=[folio])
        else:
            self.LKFException('No se mandarón parametros para actualizar')

    def get_list_bitacora2(self, location=None, area=None, prioridades=[], dateFrom='', dateTo='', filterDate=""):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_ACCESOS
        }
        if location:
            match_query.update({f"answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}":location})
        if area:
            match_query.update({f"answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}":area})
        if prioridades:
            match_query[f"answers.{self.bitacora_fields['status_visita']}"] = {"$in": prioridades}
  
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
                f"answers.{self.mf['fecha_entrada']}": {"$gte": dateFrom, "$lte": dateTo},
            })
        elif dateFrom:
            match_query.update({
                f"answers.{self.mf['fecha_entrada']}": {"$gte": dateFrom}
            })
        elif dateTo:
            match_query.update({
                f"answers.{self.mf['fecha_entrada']}": {"$lte": dateTo}
            })
        
        proyect_fields ={
            '_id': 1,
            'folio': "$folio",
            'created_at': "$created_at",
            'updated_at': "$updated_at",
            'a_quien_visita':f"$answers.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}",
            'documento': f"$answers.{self.mf['documento']}",
            'caseta_entrada':f"$answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}",
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
            'nombre_area_salida':f"$answers.{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.mf['nombre_area_salida']}",
            'nombre_visitante':f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['nombre_visita']}",
            'contratista':f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['empresa']}",
            'perfil_visita':{'$arrayElemAt': [f"$answers.{self.PASE_ENTRADA_OBJ_ID}.{self.mf['nombre_perfil']}",0]},
            'status_gafete':f"$answers.{self.mf['status_gafete']}",
            'status_visita':f"$answers.{self.mf['tipo_registro']}",
            'ubicacion':f"$answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
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
        # if not filterDate:
        #     query.append(
        #         {"$limit":1}
        #     )
        if dateFrom:
            query.append(
                {'$sort':{'folio':-1}},
            )
        else:
            query.append(
                {'$sort':{'folio':-1}},
            )
           
        records = self.format_cr(self.cr.aggregate(query))
        # print( simplejson.dumps(records, indent=4))
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
        return  records

    def get_pdf_seg(self, qr_code, template_id=491, name_pdf='Pase de Entrada'):
        return self.lkf_api.get_pdf_record(qr_code, template_id = template_id, name_pdf =name_pdf, send_url=True)

    def get_list_rondines(self, prioridades=[], dateFrom='', dateTo='', filterDate=""):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.BITACORA_RONDINES
        }
        # if location:
        #     match_query.update({f"answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}":location})
        # if area:
        #     match_query.update({f"answers.{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}":area})
        # if prioridades:
        #     match_query[f"answers.{self.bitacora_fields['status_visita']}"] = {"$in": prioridades}
  
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
                f"answers.{self.f['fecha_inicio_rondin']}": {"$gte": dateFrom, "$lte": dateTo},
            })
        elif dateFrom:
            match_query.update({
                f"answers.{self.f['fecha_inicio_rondin']}": {"$gte": dateFrom}
            })
        elif dateTo:
            match_query.update({
                f"answers.{self.f['fecha_inicio_rondin']}": {"$lte": dateTo}
            })
        
        proyect_fields ={
            '_id': 1,
            'folio': "$folio",
            'duracion_rondin': f"$answers.{self.f['duracion_rondin']}",
            'duracion_traslado_area':f"$answers.{self.f['duracion_traslado_area']}",
            'fecha_inspeccion_area':f"$answers.{self.f['fecha_inspeccion_area']}",
            'fecha_programacion':f"$answers.{self.f['fecha_programacion']}",
            'fecha_inicio_rondin':f"$answers.{self.f['fecha_inicio_rondin']}",
            'grupo_areas_visitadas':f"$answers.{self.f['grupo_areas_visitadas']}",
            
            # 'areas_del_rondin': '66462aa5d4a4af2eea07e0d1',
            # 'comentario_area_rondin': '66462b9d7124d1540f962088',
            # 'comentario_check_area': '681144fb0d423e25b42818d4',
            # 'estatus_del_recorrido': '6639b2744bb44059fc59eb62',
            # 'fecha_hora_inspeccion_area': '6760a908a43b1b0e41abad6b',
            # 'fecha_programacion':'6760a8e68cef14ecd7f8b6fe',
            # 'foto_evidencia_area': '681144fb0d423e25b42818d2',
            # 'foto_evidencia_area_rondin': '66462b9d7124d1540f962087',
            # 'grupo_de_areas_recorrido': '6645052ef8bc829a5ccafaf5',
            # 'nombre_area':'663e5d44f5b8a7ce8211ed0f',
            # 'nombre_del_recorrido': '6645050d873fc2d733961eba',
            # 'nombre_del_recorrido_en_catalog': '6644fb97e14dcb705407e0ef',
            # 'ubicacion_recorrido': '663e5c57f5b8a7ce8211ed0b',
            # 'fecha_inicio_rondin': '6818ea068a7f3446f1bae3b3',
            # 'fecha_fin_rondin': '6760a8e68cef14ecd7f8b6ff',
            # 'check_status': '681fa6a8d916c74b691e174b',
            # 'grupo_incidencias_check': '681144fb0d423e25b42818d3',
            # 'incidente_open': '6811455664dc22ecae83f75b',
            # 'incidente_comentario': '681145323d9b5fa2e16e35cc',
            # 'incidente_area': '663e5d44f5b8a7ce8211ed0f',
            # 'incidente_location': '663e5c57f5b8a7ce8211ed0b',
            # 'incidente_evidencia': '681145323d9b5fa2e16e35cd',
            # 'incidente_documento': '685063ba36910b2da9952697',
            # 'url_registro_rondin': '6750adb2936622aecd075607',
            # 'bitacora_rondin_incidencias': '686468a637d014b9e0ab5090',
            # 'tipo_de_incidencia': '663973809fa65cafa759eb97'
            }
        # lookup = {
        #  'from': 'form_answer',
        #  'localField': 'pase_id',
        #  'foreignField': '_id',
        #  "pipeline": [
        #         {'$match':{
        #             "deleted_at":{"$exists":False},
        #             "form_id": self.PASE_ENTRADA,
        #             }
        #         },
        #         {'$project':{
        #             "_id":0, 
        #             'motivo_visita':f"$answers.{self.CONFIG_PERFILES_OBJ_ID}.{self.mf['motivo']}",
        #             'grupo_areas_acceso': f"$answers.{self.mf['grupo_areas_acceso']}",                    
        #             }
        #         },
        #         ],
        #  'as': 'pase',
        # }
       
        query = [
            {'$match': match_query },
            {'$project': proyect_fields},
            # {'$lookup': lookup},
        ]
        # if not filterDate:
        #     query.append(
        #         {"$limit":1}
        #     )
        if dateFrom:
            query.append(
                {'$sort':{'folio':-1}},
            )
        else:
            query.append(
                {'$sort':{'folio':-1}},
            )
           
        records = self.format_cr(self.cr.aggregate(query))
        # print( simplejson.dumps(records, indent=4))
        # for r in records:
        #     pase = r.pop('pase')
        #     r.pop('pase_id')
        #     if len(pase) > 0 :
        #         pase = pase[0]
        #         r['motivo_visita'] = self.unlist(pase.get('motivo_visita',''))
        #         r['grupo_areas_acceso'] = self._labels_list(pase.get('grupo_areas_acceso',[]), self.mf)
        #     r['id_gafet'] = r.get('id_gafet','')
        #     r['status_visita'] = r.get('status_visita','').title().replace('_', ' ')
        #     r['contratista'] = self.unlist(r.get('contratista',[]))
        #     r['status_gafete'] = r.get('status_gafete','').title().replace('_', ' ')
        #     r['documento'] = r.get('documento','')
        #     r['grupo_areas_acceso'] = self._labels_list(r.pop('grupo_areas_acceso',[]), self.mf)
        #     r['comentarios'] = self.format_comentarios(r.get('comentarios',[]))
        #     r['vehiculos'] = self.format_vehiculos(r.get('vehiculos',[]))
        #     r['equipos'] = self.format_equipos(r.get('equipos',[]))
        #     r['visita_a'] = self.format_visita(r.get('visita_a',[]))
        print("rondines", simplejson.dumps( records,indent=4))
        return  records

    # def get_page_stats(self, booth_area, location, page=''):
    #     print('entra a get_booth_stats')
    #     print('booth_area', booth_area)
    #     print('location', location)
    #     today = datetime.today().strftime("%Y-%m-%d")
    #     res={}

    #     if page == 'Turnos':
    #         #Visitas dentro, Gafetes pendientes y Vehiculos estacionados
    #         match_query_visitas = {
    #             "deleted_at": {"$exists": False},
    #             "form_id": self.BITACORA_ACCESOS,
    #             f"answers.{self.bitacora_fields['status_visita']}": "entrada",
    #             f"answers.{self.bitacora_fields['catalogo_pase_entrada']}.{self.pase_entrada_fields['status_pase']}": {"$in": ["Activo"]},
    #             f"answers.{self.bitacora_fields['caseta_entrada']}": booth_area,
    #             f"answers.{self.bitacora_fields['ubicacion']}": location,
    #         }

    #         proyect_fields_visitas = {
    #             '_id': 1,
    #             'vehiculos': {"$ifNull": [f"$answers.{self.mf['grupo_vehiculos']}", []]},
    #             'id_gafete': f"$answers.{self.bitacora_fields['gafete_catalog']}.{self.gafetes_fields['gafete_id']}",
    #             'status_gafete': f"$answers.{self.mf['status_gafete']}"
    #         }

    #         group_by_visitas = {
    #             '_id': None,
    #             'total_visitas_dentro': {'$sum': 1},
    #             'total_vehiculos_dentro': {'$sum': {'$size': '$vehiculos'}},
    #             'gafetes_info': {
    #                 '$push': {
    #                     'id_gafete':'$id_gafete',
    #                     'status_gafete':'$status_gafete'
    #                 }
    #             }
    #         }

    #         query_visitas = [
    #             {'$match': match_query_visitas},
    #             {'$project': proyect_fields_visitas},
    #             {'$group': group_by_visitas}
    #         ]

    #         resultado = self.format_cr(self.cr.aggregate(query_visitas))
    #         total_vehiculos_dentro = resultado[0]['total_vehiculos_dentro'] if resultado else 0
    #         total_visitas_dentro = resultado[0]['total_visitas_dentro'] if resultado else 0
    #         gafetes_info = resultado[0]['gafetes_info'] if resultado else []
    #         gafetes_pendientes = sum(1
    #             for gafete in gafetes_info
    #                 if gafete.get('id_gafete') and gafete.get('status_gafete', '').lower() != 'entregado'
    #         )
            
    #         res['total_vehiculos_dentro'] = total_vehiculos_dentro
    #         res['in_invitees'] = total_visitas_dentro
    #         res['gafetes_pendientes'] = gafetes_pendientes

    #         #Articulos concesionados
    #         match_query_concesionados = {
    #             "deleted_at": {"$exists": False},
    #             "form_id": self.CONCESSIONED_ARTICULOS,
    #             f"answers.{self.consecionados_fields['catalogo_ubicacion_concesion']}.{self.mf['ubicacion']}": location,
    #         }

    #         proyect_fields_concesionados = {
    #             '_id': 1,
    #         }

    #         group_by_concesionados = {
    #             '_id': None,
    #             'articulos_concesionados': {'$sum': 1}
    #         }

    #         query_concesionados = [
    #             {'$match': match_query_concesionados},
    #             {'$project': proyect_fields_concesionados},
    #             {'$group': group_by_concesionados}
    #         ]

    #         resultado = self.format_cr(self.cr.aggregate(query_concesionados))
    #         articulos_concesionados = resultado[0]['articulos_concesionados'] if resultado else 0
            
    #         res['articulos_concesionados'] = articulos_concesionados

    #         #Incidentes pendientes
    #         match_query_incidentes = {
    #             "deleted_at": {"$exists": False},
    #             "form_id": self.BITACORA_INCIDENCIAS,
    #             f"answers.{self.incidence_fields['area_incidencia_catalog']}.{self.incidence_fields['area_incidencia']}": booth_area,
    #             f"answers.{self.incidence_fields['ubicacion_incidencia_catalog']}.{self.incidence_fields['ubicacion_incidencia']}": location
    #         }

    #         proyect_fields_incidentes = {
    #             '_id': 1,
    #             'acciones_tomadas_incidencia': f"$answers.{self.incidence_fields['acciones_tomadas_incidencia']}",
    #         }

    #         group_by_incidentes = {
    #             '_id': None,
    #             'incidentes_pendientes': {'$sum': {'$cond': [{'$or': [{'$eq': [{'$size': {'$ifNull': ['$acciones_tomadas_incidencia', []]}}, 0]},{'$eq': ['$acciones_tomadas_incidencia', None]}]}, 1, 0]}}
    #         }

    #         query_incidentes = [
    #             {'$match': match_query_incidentes},
    #             {'$project': proyect_fields_incidentes},
    #             {'$group': group_by_incidentes}
    #         ]

    #         resultado = self.format_cr(self.cr.aggregate(query_incidentes))
    #         incidentes_pendientes = resultado[0]['incidentes_pendientes'] if resultado else 0
            
    #         res['incidentes_pendites'] = incidentes_pendientes
    #     elif page == 'Accesos' or page == 'Bitacoras':
    #         #Visitas en el dia, personal dentro, vehiculos dentro y salidas registradas
    #         match_query_visitas = {
    #             "deleted_at": {"$exists": False},
    #             "form_id": self.BITACORA_ACCESOS,
    #             # f"answers.{self.bitacora_fields['status_visita']}": "entrada",
    #             f"answers.{self.bitacora_fields['catalogo_pase_entrada']}.{self.pase_entrada_fields['status_pase']}": {"$in": ["Activo"]},
    #             f"answers.{self.bitacora_fields['caseta_entrada']}": booth_area,
    #             f"answers.{self.bitacora_fields['ubicacion']}": location,
    #             f"answers.{self.mf['fecha_entrada']}": {"$gte": today,"$lt": f"{today}T23:59:59"}
    #         }

    #         proyect_fields_visitas = {
    #             '_id': 1,
    #             'vehiculos': {"$ifNull": [f"$answers.{self.mf['grupo_vehiculos']}", []]},
    #             'perfil': f"$answers.{self.bitacora_fields['catalogo_pase_entrada']}.{self.mf['nombre_perfil']}",
    #             'status_visita': f"$answers.{self.bitacora_fields['status_visita']}"
    #         }

    #         group_by_visitas = {
    #             '_id': None,
    #             'visitas_en_dia': {'$sum': 1},
    #             'total_vehiculos_dentro': {'$sum': {'$size': '$vehiculos'}},
    #             'detalle_visitas': {
    #                 '$push': {
    #                     'perfil': '$perfil',
    #                     'status_visita': '$status_visita'
    #                 }
    #             }
    #         }

    #         query_visitas = [
    #             {'$match': match_query_visitas},
    #             {'$project': proyect_fields_visitas},
    #             {'$group': group_by_visitas}
    #         ]

    #         resultado = self.format_cr(self.cr.aggregate(query_visitas))
    #         # print('resultadooooooooooooooooo',resultado)
    #         total_vehiculos_dentro = resultado[0]['total_vehiculos_dentro'] if resultado else 0
    #         visitas_en_dia = resultado[0]['visitas_en_dia'] if resultado else 0
    #         detalle_visitas = resultado[0]['detalle_visitas'] if resultado else []
    #         personal_dentro = sum(1 for visita in detalle_visitas if visita['perfil'][0].lower() != "visita general")
    #         salidas = sum(1 for visita in detalle_visitas if visita['status_visita'].lower() == "salida")

    #         res['total_vehiculos_dentro'] = total_vehiculos_dentro
    #         res['visitas_en_dia'] = visitas_en_dia
    #         res['personal_dentro'] = personal_dentro
    #         res['salidas_registradas'] = salidas
    #     elif page == 'Incidencias':
    #         #Incidentes por dia
    #         match_query_incidentes = {
    #             "deleted_at": {"$exists": False},
    #             "form_id": self.BITACORA_INCIDENCIAS,
    #             f"answers.{self.incidence_fields['area_incidencia_catalog']}.{self.incidence_fields['area_incidencia']}": booth_area,
    #             f"answers.{self.incidence_fields['area_incidencia_catalog']}.{self.incidence_fields['area_incidencia']}": booth_area,
    #             f"answers.{self.incidence_fields['ubicacion_incidencia_catalog']}.{self.incidence_fields['ubicacion_incidencia']}": location,
    #             f"answers.{self.incidence_fields['fecha_hora_incidencia']}": {"$gte": today,"$lt": f"{today}T23:59:59"}
    #         }

    #         proyect_fields_incidentes = {
    #             '_id': 1,
    #         }

    #         group_by_incidentes = {
    #             '_id': None,
    #             'incidentes_x_dia': {'$sum': 1}
    #         }

    #         query_incidentes = [
    #             {'$match': match_query_incidentes},
    #             {'$project': proyect_fields_incidentes},
    #             {'$group': group_by_incidentes}
    #         ]

    #         resultado = self.format_cr(self.cr.aggregate(query_incidentes))
    #         incidentes_x_dia = resultado[0]['incidentes_x_dia'] if resultado else 0

    #         res['incidentes_x_dia'] = incidentes_x_dia

    #         #Fallas pendientes
    #         match_query_fallas = {
    #             "deleted_at": {"$exists": False},
    #             "form_id": self.BITACORA_FALLAS,
    #             f"answers.{self.fallas_fields['falla_ubicacion_catalog']}.{self.fallas_fields['falla_caseta']}": booth_area,
    #             f"answers.{self.fallas_fields['falla_ubicacion_catalog']}.{self.fallas_fields['falla_ubicacion']}": location,
    #             f"answers.{self.fallas_fields['falla_estatus']}": 'abierto',
    #             # f"answers.{self.incidence_fields['fecha_hora_incidencia']}": {"$gte": today,"$lt": f"{today}T23:59:59"}
    #         }

    #         proyect_fields_fallas = {
    #             '_id': 1,
    #         }

    #         group_by_fallas = {
    #             '_id': None,
    #             'fallas_pendientes': {'$sum': 1}
    #         }

    #         query_fallas = [
    #             {'$match': match_query_fallas},
    #             {'$project': proyect_fields_fallas},
    #             {'$group': group_by_fallas}
    #         ]

    #         resultado = self.format_cr(self.cr.aggregate(query_fallas))
    #         fallas_pendientes = resultado[0]['fallas_pendientes'] if resultado else 0

    #         res['fallas_pendientes'] = fallas_pendientes
    #     elif page == 'Articulos':
    #         #Articulos concesionados pendientes
    #         match_query_concesionados = {
    #             "deleted_at": {"$exists": False},
    #             "form_id": self.CONCESSIONED_ARTICULOS,
    #             f"answers.{self.consecionados_fields['catalogo_ubicacion_concesion']}.{self.mf['ubicacion']}": location,
    #             f"answers.{self.consecionados_fields['status_concesion']}": "abierto",
    #         }

    #         proyect_fields_concesionados = {
    #             '_id': 1,
    #         }

    #         group_by_concesionados = {
    #             '_id': None,
    #             'articulos_concesionados_pendientes': {'$sum': 1}
    #         }

    #         query_concesionados = [
    #             {'$match': match_query_concesionados},
    #             {'$project': proyect_fields_concesionados},
    #             {'$group': group_by_concesionados}
    #         ]

    #         resultado = self.format_cr(self.cr.aggregate(query_concesionados))
    #         articulos_concesionados_pendientes = resultado[0]['articulos_concesionados_pendientes'] if resultado else 0
            
    #         res['articulos_concesionados_pendientes'] = articulos_concesionados_pendientes

    #         #Articulos perdidos
    #         match_query_perdidos = {
    #             "deleted_at": {"$exists": False},
    #             "form_id": self.BITACORA_OBJETOS_PERDIDOS,
    #             f"answers.{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.perdidos_fields['ubicacion_perdido']}": location,
    #             f"answers.{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.perdidos_fields['area_perdido']}": booth_area,
    #         }

    #         proyect_fields_perdidos = {
    #             '_id': 1,
    #             'status_perdido': f"$answers.{self.perdidos_fields['estatus_perdido']}",
    #         }

    #         group_by_perdidos = {
    #             '_id': None,
    #             'perdidos_info': {
    #                 '$push': {
    #                     'status_perdido':'$status_perdido'
    #                 }
    #             }
    #         }

    #         query_perdidos = [
    #             {'$match': match_query_perdidos},
    #             {'$project': proyect_fields_perdidos},
    #             {'$group': group_by_perdidos}
    #         ]

    #         resultado = self.format_cr(self.cr.aggregate(query_perdidos))
    #         perdidos_info = resultado[0]['perdidos_info'] if resultado else []

    #         articulos_perdidos = 0
    #         for perdido in perdidos_info:
    #             status_perdido = perdido.get('status_perdido', '').lower()
    #             if status_perdido not in ['entregado', 'donado']:
    #                 articulos_perdidos += 1

    #         res['articulos_perdidos'] = articulos_perdidos

    #     # res ={
    #     #         "in_invitees":0,
    #     #         "articulos_concesionados":0,
    #     #         "incidentes_pendites": incidentes_pendientes,
    #     #         "vehiculos_estacionados": total_vehiculos,
    #     #         "gefetes_pendientes": 0,
    #     #     }
    #     return res
    
    def get_rondines_by_status(self, status_list=['programado', 'en_proceso']):
        query = [
            {'$match': {
                "deleted_at": {"$exists": False},
                "form_id": self.BITACORA_RONDINES,
                f"answers.{self.f['estatus_del_recorrido']}": {"$in": status_list},
            }},
            {'$project': {
                '_id': 1,
                'timezone': 1,
                'fecha_programacion': f"$answers.{self.f['fecha_programacion']}",
                'rondinero_id': f"$answers.{self.USUARIOS_OBJ_ID}.{self.mf['id_usuario']}",
                'answers': f"$answers"
            }},
        ]

        rondines = self.format_cr(self.cr.aggregate(query))
        return rondines

    def close_rondines(self, list_of_rondines, timezone='America/Mexico_City'):
        #- Expirados son lo que esta en status programados y que tienen mas de 24 de programdos
        # - en progreso son lo que estan con status progreso y tienen mas de 1 hr de su ultimo check.
        answers = {}
        tiz = pytz.timezone(timezone)
        ahora_cierre = datetime.now(tiz)

        rondines_expirados = []
        rondines_en_proceso_vencidos = []

        for rondin in list_of_rondines:
            estatus = rondin.get('estatus_del_recorrido')
            fecha_programacion_str = rondin.get('fecha_programacion')
            user_id = self.unlist(rondin.get('rondinero_id', 0))
            user_data = self.lkf_api.get_user_by_id(user_id)
            user_timezone = user_data.get('timezone', 'America/Mexico_City')
            tz = pytz.timezone(user_timezone)
            ahora = datetime.now(tz)

            if estatus == 'programado' and fecha_programacion_str:
                fecha_programacion = tz.localize(datetime.strptime(fecha_programacion_str, '%Y-%m-%d %H:%M:%S'))
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

        rondines_ids = []
        rondines_expirados = rondines_expirados + rondines_en_proceso_vencidos
        for rondin in rondines_expirados:
            rondines_ids.append(rondin.get('_id'))

        answers[self.f['estatus_del_recorrido']] = 'cerrado'
        answers[self.f['fecha_fin_rondin']] = ahora_cierre.strftime('%Y-%m-%d %H:%M:%S')

        # print(stop)
        if answers:
            res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.BITACORA_RONDINES, record_id=rondines_ids)
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                return res
            else: 
                return res