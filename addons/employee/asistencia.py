# -*- coding: utf-8 -*-
"""Asistencia (Disponible / Ausente) de cualquier usuario.

Un registro de `registro_de_asistencia` por jornada: ponerse Disponible lo abre
(fecha de inicio), ponerse Ausente lo cierra (fecha de cierre y horas trabajadas).
No tiene lugar: el Check In en una ubicación/caseta es un flujo aparte.
"""

from datetime import datetime, timedelta

import pytz

from .app import Employee

DATE_FMT = '%Y-%m-%d %H:%M:%S'

# Un registro abierto más viejo que esto se considera olvidado y se cierra solo.
MAX_JORNADA_HORAS = 16
# Sin horario, una jornada olvidada se cierra a estas horas de su inicio.
CIERRE_SIN_HORARIO_HORAS = 12


class Asistencia(Employee):

    def __init__(self, settings, **kwargs):
        super().__init__(settings, **kwargs)
        self.REGISTRO_ASISTENCIA = self.lkm.form_id('registro_de_asistencia', 'id')
        self.HORARIOS = self.lkm.form_id('horarios', 'id')

        self.asistencia_fields = {
            'inicio': '6879828d0234f02649cad390',
            'cierre': '6879828d0234f02649cad391',
            'comentario_cierre': '68798dd1205f333d8f53a1c7',
            'dias_libres': '68bb20095035e61c5745de05',
            'nombre_horario': '68b6427cc8f94827ebfed695',
            'hora_entrada': '68b6427cc8f94827ebfed696',
            'hora_salida': '68b6427cc8f94827ebfed697',
            'tolerancia_retardo': '68b6427cc8f94827ebfed698',
            'retardo_maximo': '68b642e2bc17e2713cabe019',
            'horas_trabajadas': '68d6b0d5f7865907a86c37d7',
            'status': '68d5bbb57691dec5a7640358',
            'ubicacion_horario': '6ad90e4757d6829358977bd8',
            'tipo_cierre': '6ad90e477d254b629e023075',
        }
        self.horario_fields = {
            'ingreso_maximo': '69824e4bfdead27b0009739e',
            'ubicaciones': '68b6427cc8f94827ebfed699',
        }

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get_estado(self):
        user_id = self.user.get('user_id')
        tz = self._user_tz(user_id)
        abierto = self._registro_abierto(user_id, tz)
        return self._format_estado(abierto, user_id)

    def set_estatus(self, estatus):
        if estatus not in ('disponible', 'ausente'):
            self.LKFException({'title': 'Estatus inválido', 'msg': 'El estatus debe ser "disponible" o "ausente".'})
        user_id = self.user.get('user_id')
        tz = self._user_tz(user_id)
        abierto = self._registro_abierto(user_id, tz)

        if estatus == 'disponible' and not abierto:
            self._abrir(user_id, tz)
        elif estatus == 'ausente' and abierto:
            self._cerrar(abierto, self._now(tz), tz)

        return self._format_estado(self._registro_abierto(user_id, tz), user_id)

    # ------------------------------------------------------------------
    # Registros
    # ------------------------------------------------------------------

    def _registro_abierto(self, user_id, tz):
        """El registro abierto del usuario. Si quedó olvidado de otra jornada, lo cierra."""
        f = self.asistencia_fields
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.REGISTRO_ASISTENCIA,
                'user_id': user_id,
                f'answers.{f["inicio"]}': {'$exists': True},
                f'answers.{f["cierre"]}': {'$exists': False},
            }},
            {'$sort': {'created_at': -1}},
            {'$project': {
                '_id': 1,
                'folio': 1,
                'inicio': f'$answers.{f["inicio"]}',
                'nombre_horario': f'$answers.{f["nombre_horario"]}',
                'hora_entrada': f'$answers.{f["hora_entrada"]}',
                'hora_salida': f'$answers.{f["hora_salida"]}',
                'status': f'$answers.{f["status"]}',
            }},
        ]
        abiertos = self.format_cr(self.cr.aggregate(query))
        now = self._now(tz)
        vigente = None
        for reg in abiertos:
            inicio = self._parse(reg.get('inicio'), tz)
            if vigente is None and inicio and now - inicio < timedelta(hours=MAX_JORNADA_HORAS):
                vigente = reg
            else:
                self._cerrar(reg, self._cierre_olvidado(reg, tz, now), tz, automatico=True)
        return vigente

    def _abrir(self, user_id, tz):
        f = self.asistencia_fields
        now = self._now(tz)
        answers = {f['inicio']: now.strftime(DATE_FMT)}

        horario = self._horario_para(user_id, now, tz)
        # Sin horario, si el empleado tiene una sola ubicación, esa es la de su jornada.
        ubicaciones = self._ubicaciones_configuradas(user_id)
        ubicacion = (horario or {}).get('ubicacion') or (ubicaciones[0] if len(ubicaciones) == 1 else None)
        if ubicacion:
            answers[f['ubicacion_horario']] = ubicacion
        if horario:
            answers.update({
                f['nombre_horario']: horario['nombre_horario'],
                f['hora_entrada']: horario['hora_entrada'],
                f['hora_salida']: horario['hora_salida'],
                f['tolerancia_retardo']: horario['tolerancia_retardo'],
                f['retardo_maximo']: horario['retardo_maximo'],
                f['status']: self._status_llegada(now, horario),
            })
        dias_libres = self._dias_libres(user_id)
        if dias_libres:
            answers[f['dias_libres']] = dias_libres

        metadata = self.lkf_api.get_metadata(form_id=self.REGISTRO_ASISTENCIA)
        metadata.update({
            'properties': {
                'device_properties': {
                    'System': 'Sanic',
                    'Module': 'Employee',
                    'Process': 'Asistencia',
                    'Action': 'disponible',
                    'File': 'employee/asistencia.py',
                }
            },
            'answers': answers,
        })
        res = self._crear_registro(metadata)
        if res.get('status_code') not in (200, 201, 202):
            self.LKFException({'title': 'Error al registrar asistencia', 'msg': res.get('json', res)})
        return res

    def _crear_registro(self, metadata):
        """Crea el registro con el JWT del usuario del request.

        post_forms_answers lo manda desde un hilo que no hereda el contexto del
        request y termina usando el JWT de la cuenta: el registro quedaba a nombre
        del dueño y no del usuario. Aquí se manda en el mismo hilo.
        """
        url = self.lkf_api.api_url.form['set_form_answer']
        return self.lkf_api.network.dispatch(url, data=metadata)

    def _cerrar(self, registro, cierre_dt, tz, automatico=False):
        f = self.asistencia_fields
        inicio = self._parse(registro.get('inicio'), tz)
        answers = {
            f['cierre']: cierre_dt.strftime(DATE_FMT),
            f['tipo_cierre']: 'automatico' if automatico else 'manual',
        }
        if inicio:
            horas = max((cierre_dt - inicio).total_seconds(), 0) / 3600
            answers[f['horas_trabajadas']] = round(horas, 2)
        if automatico:
            answers[f['comentario_cierre']] = 'Cierre automático: la jornada no se cerró al pasar a Ausente.'
        res = self.lkf_api.patch_multi_record(
            answers=answers, form_id=self.REGISTRO_ASISTENCIA, record_id=[str(registro['_id'])])
        if res.get('status_code') not in (200, 201, 202):
            self.LKFException({'title': 'Error al cerrar asistencia', 'msg': res.get('json', res)})
        return res

    def _cierre_olvidado(self, registro, tz, now):
        """Hora de cierre para una jornada olvidada: su hora de salida, o inicio + 12 h."""
        inicio = self._parse(registro.get('inicio'), tz) or now
        salida = registro.get('hora_salida')
        cierre = None
        if salida:
            t_salida = datetime.strptime(self._hhmmss(salida), '%H:%M:%S').time()
            cierre = tz.localize(datetime.combine(inicio.date(), t_salida))
            if cierre <= inicio:
                cierre += timedelta(days=1)
        if not cierre:
            cierre = inicio + timedelta(hours=CIERRE_SIN_HORARIO_HORAS)
        return min(cierre, now)

    def _ultimo_cierre(self, user_id):
        f = self.asistencia_fields
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.REGISTRO_ASISTENCIA,
                'user_id': user_id,
                f'answers.{f["cierre"]}': {'$exists': True},
            }},
            {'$sort': {f'answers.{f["cierre"]}': -1}},
            {'$limit': 1},
            {'$project': {'_id': 0, 'cierre': f'$answers.{f["cierre"]}'}},
        ]
        res = self.format_cr(self.cr.aggregate(query), get_one=True)
        return (res or {}).get('cierre')

    def _format_estado(self, abierto, user_id):
        if abierto:
            horario = None
            if abierto.get('nombre_horario'):
                horario = {
                    'nombre': abierto.get('nombre_horario'),
                    'entrada': abierto.get('hora_entrada'),
                    'salida': abierto.get('hora_salida'),
                }
            return {
                'estatus': 'disponible',
                'desde': abierto.get('inicio'),
                'status_llegada': abierto.get('status'),
                'horario': horario,
                'folio': abierto.get('folio'),
            }
        return {
            'estatus': 'ausente',
            'ultimo_cierre': self._ultimo_cierre(user_id),
        }

    # ------------------------------------------------------------------
    # Horario
    # ------------------------------------------------------------------

    def _ubicaciones_configuradas(self, user_id):
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.CONF_AREA_EMPLEADOS,
                f'answers.{self.EMPLOYEE_OBJ_ID}.{self.employee_fields["user_id_id"]}': user_id,
            }},
            {'$unwind': f'$answers.{self.f["areas_group"]}'},
            {'$group': {
                '_id': f'$answers.{self.f["areas_group"]}.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.Location.f["location"]}',
            }},
        ]
        return [x['_id'] for x in self.cr.aggregate(query) if x.get('_id')]

    def _horario_para(self, user_id, now, tz):
        """El horario de las ubicaciones del empleado cuya entrada queda más cerca de `now`."""
        ubicaciones = self._ubicaciones_configuradas(user_id)
        if not ubicaciones:
            return None
        f, hf = self.asistencia_fields, self.horario_fields
        loc_path = f'{hf["ubicaciones"]}.{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.Location.f["location"]}'
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.HORARIOS,
                f'answers.{loc_path}': {'$in': ubicaciones},
            }},
            {'$project': {
                '_id': 0,
                'nombre_horario': f'$answers.{f["nombre_horario"]}',
                'hora_entrada': f'$answers.{f["hora_entrada"]}',
                'hora_salida': f'$answers.{f["hora_salida"]}',
                'tolerancia_retardo': f'$answers.{f["tolerancia_retardo"]}',
                'retardo_maximo': f'$answers.{f["retardo_maximo"]}',
                'ingreso_maximo': f'$answers.{hf["ingreso_maximo"]}',
                'ubicaciones': f'$answers.{loc_path}',
            }},
        ]
        mejor, mejor_diff = None, None
        for h in self.cr.aggregate(query):
            if not h.get('hora_entrada'):
                continue
            t_entrada = datetime.strptime(self._hhmmss(h['hora_entrada']), '%H:%M:%S').time()
            antes_permitido = int(h.get('ingreso_maximo') or 0) * 60
            for dias in (-1, 0, 1):
                entrada = tz.localize(datetime.combine(now.date() + timedelta(days=dias), t_entrada))
                delta = (now - entrada).total_seconds()
                # Puede llegar hasta `ingreso_maximo` min antes, o hasta 12 h después.
                if -antes_permitido <= delta <= 12 * 3600:
                    if mejor_diff is None or abs(delta) < mejor_diff:
                        mejor, mejor_diff = {**h, 'entrada_dt': entrada}, abs(delta)
        if not mejor:
            return None
        # El horario puede aplicar a varias ubicaciones: la suya es la que también tiene el empleado.
        del_horario = mejor.get('ubicaciones') or []
        ubicacion = next((u for u in del_horario if u in ubicaciones), None)
        return {
            'ubicacion': ubicacion,
            'nombre_horario': mejor.get('nombre_horario', ''),
            'hora_entrada': mejor.get('hora_entrada', ''),
            'hora_salida': mejor.get('hora_salida', ''),
            'tolerancia_retardo': int(mejor.get('tolerancia_retardo') or 0),
            'retardo_maximo': int(mejor.get('retardo_maximo') or 0),
            'entrada_dt': mejor['entrada_dt'],
        }

    def _status_llegada(self, now, horario):
        retraso_min = (now - horario['entrada_dt']).total_seconds() / 60
        if retraso_min <= horario['tolerancia_retardo']:
            return 'presente'
        if retraso_min <= horario['retardo_maximo']:
            return 'retardo'
        return 'falta_por_retardo'

    def _dias_libres(self, user_id):
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.EMPLEADOS,
                f'answers.{self.USUARIOS_OBJ_ID}.{self.employee_fields["user_id_id"]}': user_id,
            }},
            {'$limit': 1},
            {'$project': {'_id': 0, 'dias_libres': f'$answers.{self.asistencia_fields["dias_libres"]}'}},
        ]
        res = self.format_cr(self.cr.aggregate(query), get_one=True)
        return (res or {}).get('dias_libres') or []

    # ------------------------------------------------------------------
    # Fechas
    # ------------------------------------------------------------------

    def _user_tz(self, user_id):
        user = self.lkf_api.get_user_by_id(user_id) or {}
        return pytz.timezone(user.get('timezone') or 'America/Monterrey')

    def _now(self, tz):
        return datetime.now(tz).replace(microsecond=0)

    def _parse(self, value, tz):
        if not value:
            return None
        try:
            return tz.localize(datetime.strptime(value, DATE_FMT))
        except (ValueError, TypeError):
            return None

    def _hhmmss(self, value):
        return value if len(value.split(':')) == 3 else f'{value}:00'
