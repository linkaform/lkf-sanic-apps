# coding: utf-8
import sys, simplejson
from datetime import datetime, timedelta
import pytz

from accesos_utils import Accesos

from account_settings import *

class Accesos(Accesos):

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
            msg += f"Fecha actual: {ahora.strftime('%Y-%m-%d %H:%M')}  /" #formato: 2025-10-10 12:15
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
                    self.notificacion_rondin_no_arrancado(rondin, ahora, fecha_programacion)
                
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
        print('Rondines a cerrar')
        print("======log: ", rondines_ids)

        db_name = f'clave_{self.user.get("user_id")}'
        self.cr_db = self.lkf_api.couch.set_db(db_name)

        records = list(self.cr_db.find({
            "selector": {"_id": {"$in": rondines_ids}}
        }))

        for record in records:
            record['inbox'] = False
            record['status_rondin'] = 'deleted'
        self.cr_db.update(records)

        answers[self.f['estatus_del_recorrido']] = 'cerrado'
        answers[self.f['fecha_fin_rondin']] = ahora.strftime('%Y-%m-%d %H:%M:%S')

        # print(stop)
        if answers:
            res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.BITACORA_RONDINES, record_id=rondines_ids)
            if res.get('status_code') == 201 or res.get('status_code') == 202:
                return res
            else: 
                return res


if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv, use_api=True)
    acceso_obj.console_run()
    


    rondines = acceso_obj.get_rondines_by_status()

    if rondines:
        response = acceso_obj.close_rondines(rondines)
        print("response", response)
    else:
        print("No hay rondines para evaluar")