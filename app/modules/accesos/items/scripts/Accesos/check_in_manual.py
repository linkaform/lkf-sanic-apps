# coding: utf-8
from bson import ObjectId
import sys, simplejson, json
from linkaform_api import settings
from account_settings import *

from accesos_utils import Accesos
from datetime import datetime, timedelta
import pytz

class Accesos(Accesos):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)
        self.CHECKIN_MANUAL = self.lkm.form_id('checkin_manual','id')
        self.REGISTRO_ASISTENCIA = self.lkm.form_id('registro_de_asistencia','id')
        self.HORARIOS = self.lkm.form_id('horarios','id')
        
        self.f.update({
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
            'status_turn': '68d5bbb57691dec5a7640358'
        })
        
        self.default_shifts = {
            "T1": {"start": "06:00:00", "end": "14:00:00", "tolerance": 15, "max_delay": 120},
            "T2": {"start": "14:00:00", "end": "22:00:00", "tolerance": 15, "max_delay": 120},
            "T3": {"start": "22:00:00", "end": "06:00:00", "tolerance": 15, "max_delay": 120},
        }
        
    def do_checkin(self, location, area, employee_list=[], check_in_manual={}):
        if not self.is_boot_available(location, area):
            msg = f"No se puede hacer check in en la caseta en la ubicación {location} y área {area}."
            msg += f"Porque '{self.last_check_in.get('employee')}' ya está registrado en la caseta."
            raise Exception(msg)
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
        user_data = self.lkf_api.get_user_by_id(self.user.get('user_id'))
        employee['timezone'] = user_data.get('timezone','America/Monterrey')
        employee['name'] = employee['worker_name']
        employee['position'] = self.chife_guard
        if not employee:
            msg = f"Ningun empleado encontrado con email: {self.user.get('email')}"
            self.LKFException(msg)
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
        resp_create = self.lkf_api.post_forms_answers(data)
        if resp_create.get('status_code') == 201:
            resp_create['json'].update({'boot_status':{'guard_on_duty':user_data['name']}})
        return resp_create

    def verify_guard_status(self):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.REGISTRO_ASISTENCIA,
                f"answers.{self.f['start_shift']}": {"$exists": True},
                f"answers.{self.f['end_shift']}": {"$exists": False},
                "user_id": self.user_id,
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
            self.automatic_close_turn(records=response)
        return True

    def automatic_close_turn(self, records=[]):
        fecha_inicio = ''
        for record in records:
            fecha_inicio = record.get('fecha_inicio', '')
            if fecha_inicio:
                fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d %H:%M:%S')
                
            if fecha_inicio:
                tz = pytz.timezone(self.timezone if self.timezone else 'America/Monterrey')
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
                update_fields = {f"answers.{k}": v for k, v in answers.items()}
                res = self.cr.update_one({
                    'form_id': self.REGISTRO_ASISTENCIA,
                    'deleted_at': {'$exists': False},
                    '_id': ObjectId(record['_id']),
                }, {"$set": update_fields})
                print('======log:', res.modified_count, ' registros cerrados automaticamente.')

    def get_guard_data(self, guard_id, location, hora_inicio):
        dt_inicio = datetime.strptime(hora_inicio, "%Y-%m-%d %H:%M:%S")
        hora_minuto_segundo_minus10 = (dt_inicio - timedelta(minutes=10)).strftime("%H:%M:%S")
        hora_minuto_segundo_plus10 = (dt_inicio + timedelta(minutes=10)).strftime("%H:%M:%S")
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.EMPLEADOS,
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
                        "$expr": {
                            "$and": [
                                {"$lte": [f"$answers.{self.f['hora_entrada']}", hora_minuto_segundo_plus10]},
                                {"$gt":  [f"$answers.{self.f['hora_salida']}", hora_minuto_segundo_minus10]}
                            ]
                        }
                    }},
                    {"$unwind": f"$answers.{self.f['grupo_turnos']}"},
                    {"$match": {
                        "$expr": {
                            "$eq": [f"$answers.{self.f['grupo_turnos']}.{self.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}", location]
                        }
                    }},
                    {"$project": {
                        "_id": 0,
                        "hora_inicio": f"$answers.{self.f['hora_entrada']}",
                        "hora_fin": f"$answers.{self.f['hora_salida']}",
                        "nombre_horario": f"$answers.{self.f['nombre_horario']}",
                        "tolerancia_retardo": f"$answers.{self.f['tolerancia_retardo']}",
                        "retardo_maximo": f"$answers.{self.f['retardo_maximo']}",
                        "areas": f"$answers.{self.f['grupo_turnos']}",
                    }}
                ],
                "as": "turno"
            }},
            {"$project": {
                "dias_libres": 1,
                "turno": {
                    "$ifNull": [
                        {"$arrayElemAt": ["$turno", 0]},
                        "sin_registro"
                    ]
                }
            }}
        ]
        response = self.format_cr(self.cr.aggregate(query))
        response = self.unlist(response)
        if response.get('turno') == 'sin_registro':
            dt_inicio = datetime.strptime(hora_inicio, "%Y-%m-%d %H:%M:%S")
            hora_inicio_time = dt_inicio.time()

            turno_seleccionado = None
            min_diff = None

            for nombre_turno, datos_turno in self.default_shifts.items():
                h_start = datetime.strptime(datos_turno["start"], "%H:%M:%S").time()
                # Calcula diferencia en minutos (puede ser negativa si el turno es después de la hora actual)
                diff = (
                    (datetime.combine(datetime.today(), hora_inicio_time) -
                    datetime.combine(datetime.today(), h_start)).total_seconds() / 60
                )
                # Si la hora de inicio del turno es antes o igual a la hora actual y la diferencia es la menor (más reciente)
                if diff >= 0:
                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        turno_seleccionado = {**datos_turno, "nombre_horario": nombre_turno}

            # Si no encontró ninguno (por ejemplo, turno nocturno), toma el primero cuyo inicio sea después de la hora actual
            if turno_seleccionado is None:
                for nombre_turno, datos_turno in self.default_shifts.items():
                    h_start = datetime.strptime(datos_turno["start"], "%H:%M:%S").time()
                    diff = (
                        (datetime.combine(datetime.today(), h_start) -
                        datetime.combine(datetime.today(), hora_inicio_time)).total_seconds() / 60
                    )
                    if diff > 0:
                        turno_seleccionado = {**datos_turno, "nombre_horario": nombre_turno}
                        break

            if turno_seleccionado:
                response.update({
                    'hora_inicio': turno_seleccionado['start'],
                    'hora_fin': turno_seleccionado['end'],
                    'nombre_horario': turno_seleccionado['nombre_horario'],
                    'turno': turno_seleccionado['nombre_horario'],
                    'tolerancia_retardo': turno_seleccionado['tolerance'],
                    'retardo_maximo': turno_seleccionado['max_delay'],
                })
        return response

    def calculate_status(self, hora_inicio, guard_data):
        dt_inicio = datetime.strptime(hora_inicio, "%Y-%m-%d %H:%M:%S")
        minutos_inicio = dt_inicio.hour * 60 + dt_inicio.minute
        turno_inicio = guard_data.get('hora_inicio', '00:00:00')
        dt_turno_inicio = datetime.strptime(turno_inicio, "%H:%M:%S")
        minutos_turno_inicio = dt_turno_inicio.hour * 60 + dt_turno_inicio.minute

        tolerancia = int(guard_data.get('tolerancia_retardo', 0))
        retardo_maximo = int(guard_data.get('retardo_maximo', 0))

        minutos_retraso = minutos_inicio - minutos_turno_inicio

        if -10 <= minutos_retraso <= 10:
            return "presente"
        elif tolerancia < minutos_retraso <= retardo_maximo:
            return "retardo"
        elif minutos_retraso > retardo_maximo:
            return "falta_por_retardo"
        else:
            return ""

    def check_in_manual(self):
        #! Se cierra cualquier turno anterior que este abierto
        self.verify_guard_status()
        
        if self.answers.get(self.f['start_shift']):
            fecha_actual = self.answers.get(self.f['start_shift'])
            # self.LKFException({'msg': msg, 'title': 'Turno ya iniciado'})
        else:
            tz = pytz.timezone(self.timezone)
            now = datetime.now(tz)
            fecha_actual = now.strftime('%Y-%m-%d %H:%M:%S')
        
        self.answers.update({
            self.f['start_shift']: fecha_actual,
            self.f['option_checkin']: 'cerrar_turno',
        })
        
        #! Se obtiene la informacion del guardia como Horario y Turno en el que esta haciendo su check in
        location = self.answers.get(self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID, {}).get(self.f['location'], '')
        hora_inicio = self.answers.get(self.f['start_shift'], '')
        employee_data = self.get_guard_data(self.user_id, location, hora_inicio)
        self.answers.update({
            self.f['dias_libres']: employee_data.get('dias_libres', []),
            self.f['nombre_horario']: employee_data.get('nombre_horario', ''),
            self.f['hora_entrada']: employee_data.get('hora_inicio', ''),
            self.f['hora_salida']: employee_data.get('hora_fin', ''),
            self.f['tolerancia_retardo']: employee_data.get('tolerancia_retardo', 0),
            self.f['retardo_maximo']: employee_data.get('retardo_maximo', 0),
        })
        
        #! Se calcula status de la llegada del guardia
        status = self.calculate_status(hora_inicio, employee_data)
        self.answers.update({
            self.f['status_turn']: status,
        })
        
    def get_last_check_in(self, guard_id):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.REGISTRO_ASISTENCIA,
                "user_id": guard_id,
                f"answers.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.Location.f['location']}": self.location,
                f"answers.{self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.Location.f['area']}": self.area,
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
        
    def delete_record(self, folio: str):
        """Elimina un registro por su folio.
        Args:
            folio (str): El folio del registro a eliminar.
        Returns:
            bool: True si el registro fue eliminado, False en caso contrario.
        Raises:
            Exception: Si el folio no es proporcionado.
        """
        if not folio:
            raise Exception("Folio is required to delete a registro.")
        
        response = self.cr.delete_one({
            'form_id': self.REGISTRO_ASISTENCIA,
            'folio': folio
        })
        
        if response.deleted_count > 0:
            response = True
        else:
            response = False
        return response
        
    def check_out_manual(self):
        last_check_in = self.get_last_check_in(self.user_id)
        print('===log: last_check_in', simplejson.dumps(last_check_in, indent=3))
        if last_check_in and self.record_id != str(last_check_in.get('_id', '')):
            self.answers.update({
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
            response = self.delete_record(last_check_in.get('folio', ''))
            if response:
                print(f"Registro con folio {last_check_in.get('folio', '')} eliminado exitosamente.")
        
        if self.answers.get(self.f['end_shift']):
            fecha_actual = self.answers.get(self.f['end_shift'])
        else:
            tz = pytz.timezone(self.timezone)
            now = datetime.now(tz)
            fecha_actual = now.strftime('%Y-%m-%d %H:%M:%S')
        
        self.answers.update({
            self.f['end_shift']: fecha_actual,
        })

    def set_work_hours(self, start_time, end_time):
        dt_inicio = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        dt_cierre = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        delta = dt_cierre - dt_inicio
        horas = delta.total_seconds() / 3600
        self.answers.update({
            self.f['horas_trabajadas']: round(horas, 2),
        })

if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv, use_api=False)
    acceso_obj.console_run()
    option = acceso_obj.answers.get(acceso_obj.f['option_checkin'], '')
    data_rondin = json.loads(sys.argv[1])
    acceso_obj.user_id = data_rondin.get('user_id', acceso_obj.user.get('user_id'))
    acceso_obj.timezone = data_rondin.get('timezone', 'America/Mexico_City')
    acceso_obj.location = acceso_obj.answers.get(acceso_obj.CONF_AREA_EMPLEADOS_CAT_OBJ_ID, {}).get(acceso_obj.f['location'], '')
    acceso_obj.area = acceso_obj.answers.get(acceso_obj.CONF_AREA_EMPLEADOS_CAT_OBJ_ID, {}).get(acceso_obj.f['area'], '')
    
    response = {}
    if option == 'iniciar_turno':
        acceso_obj.check_in_manual()
    elif option == 'cerrar_turno':
        acceso_obj.check_out_manual()

    if acceso_obj.answers.get(acceso_obj.f['start_shift']) and acceso_obj.answers.get(acceso_obj.f['end_shift']) \
            and not acceso_obj.answers.get(acceso_obj.f['horas_trabajadas']):
        acceso_obj.set_work_hours(acceso_obj.answers.get(acceso_obj.f['start_shift']), acceso_obj.answers.get(acceso_obj.f['end_shift']))

    print('===log: answers', simplejson.dumps(acceso_obj.answers, indent=3))
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': acceso_obj.answers
    }))