# coding: utf-8
import datetime

import sys, simplejson
from linkaform_api import settings
from account_settings import *

from accesos_utils import Accesos


class Accesos(Accesos):
    
    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)
        self.f.update({
            'porcentaje_obtenido_bitacora': '689a7ecfbf2b4be31039388e',
            'cantidad_areas_inspeccionadas': '68a7b68a22ac030a67b7f8f8'
        })

    def calcluta_tiempo_traslados(self):
        fecha_inicio = self.answers.get(self.f['fecha_inicio_rondin'], None)
        fecha_inicio = self.date_2_epoch(fecha_inicio)
        areas_visitadas = self.answers.get(self.f['grupo_areas_visitadas'], [])
        fecha_inspeccion = 0
        duracion_total = 0
        cantidad_de_inspecciones = 0
        areas_procesadas = False
        fecha_final = None
        for area in areas_visitadas:
            fecha_inspeccion = area.get(self.f['fecha_inspeccion_area'])
            fecha_inspeccion = self.date_2_epoch(fecha_inspeccion)
            if not fecha_inspeccion:
                continue
            fecha_final = fecha_inspeccion
            cantidad_de_inspecciones += 1
            areas_procesadas = True
            duracion = fecha_inspeccion - fecha_inicio
            area[self.f['duracion_traslado_area']] = round(duracion / 60,2)
            duracion_total = duracion
        if areas_procesadas:
            self.answers[self.f['duracion_rondin']] = round(duracion_total / 60,2)
            self.answers[self.f['porcentaje_obtenido_bitacora']] = str(round((cantidad_de_inspecciones / len(areas_visitadas)) * 100, 2)) + '%'
            self.answers[self.f['cantidad_areas_inspeccionadas']] = str(cantidad_de_inspecciones) + '/' + str(len(areas_visitadas))
        fecha_final_str = datetime.datetime.fromtimestamp(fecha_final).strftime('%Y-%m-%d %H:%M:%S') if fecha_final else ''
        if self.answers.get(self.f['estatus_del_recorrido']) in ['realizado', 'cerrado'] and fecha_final_str:
            self.answers[self.f['fecha_fin_rondin']] = fecha_final_str
        return True
    
    def get_and_set_areas_recorrido(self):
        location = self.answers.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.Location.f['location'], '')
        name_rondin = self.answers.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.mf['nombre_del_recorrido'], '')
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": 121742, #self.CONFIGURACION_RECORRIDOS_ID,
                f"answers.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": location,
                f"answers.{self.mf['nombre_del_recorrido']}": name_rondin
            }},
            {"$project": {
                "_id": 0,
                "rondin_areas": f"$answers.{self.f['grupo_de_areas_recorrido']}"
            }}
        ]
        res = self.cr.aggregate(query)
        format_res = list(res)
        if format_res:
            areas_recorrido = self.unlist(format_res)
            self.answers[self.f['grupo_areas_visitadas']] = areas_recorrido.get('rondin_areas', [])
            return True
        return False
    
    def get_active_guards_in_location(self, location):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.REGISTRO_ASISTENCIA,
                f"answers.{self.f['start_shift']}": {"$exists": True},
                f"answers.{self.f['end_shift']}": {"$exists": False},
                f"answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['ubicacion']}": location,
            }},
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
    
    def get_and_set_user(self):
        location = self.answers.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID, {}).get(self.Location.f['location'], '')
        user_info = self.get_active_guards_in_location(location)

        if not user_info:
            return False
        
        self.answers[self.USUARIOS_OBJ_ID] = {
            self.mf['nombre_usuario']: user_info.get('created_by_name', ''),
            self.mf['id_usuario']: [user_info.get('created_by_id', '')],
            self.mf['email_visita_a']: [user_info.get('created_by_email', '')],
        }
        return True

if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv)
    acceso_obj.console_run()
    
    #! Validacion para answers vacio
    if not acceso_obj.answers:
        acceso_obj.answers = acceso_obj.current_record.get('answers', {})
    
    #-FILTROS
    acceso_obj.calcluta_tiempo_traslados()

    if acceso_obj.answers.get(acceso_obj.mf['estatus_del_recorrido']) == 'programado':
        if not acceso_obj.answers.get(acceso_obj.f['grupo_areas_visitadas']):
            acceso_obj.get_and_set_areas_recorrido()
        if not acceso_obj.answers.get(acceso_obj.USUARIOS_OBJ_ID):
            acceso_obj.get_and_set_user()
    
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': acceso_obj.answers
    }))

