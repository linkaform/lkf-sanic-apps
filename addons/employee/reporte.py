# -*- coding: utf-8 -*-
"""Reporte de asistencias.

Tres lecturas sobre el modelo nuevo:
- Hoy: por persona, el turno que le toca según su horario, a qué hora llegó
  (su jornada), su estado y dónde está (su Check In abierto).
- Periodo: por persona, el estado de cada día, retardos, faltas y horas
  trabajadas contra horas programadas.
- Día: la jornada de una persona con sus Check In (lugares, rol, fotos).

El "deber" sale del horario asignado en Empleados; el "fue" de la jornada
(`registro_de_asistencia`) y de los Check In (`checkin_checkout_casetas`),
ligados por el folio de la jornada.
"""

from collections import defaultdict
from datetime import datetime, timedelta

from .checkin import Presencia

SIN_UBICACION = 'Sin ubicación'
FALTAS = ('falta', 'falta_por_retardo')


class ReporteAsistencia(Presencia):

    def __init__(self, settings, **kwargs):
        super().__init__(settings, **kwargs)
        self.FORMATO_VACACIONES = self.lkm.form_id('formato_vacaciones_aviso', 'id')
        self.vacaciones_fields = {
            'inicio': '55887b7e01a4de2ea71c5ab4',
            'fin': '55887b7e01a4de2ea71c5ab5',
            'tipo': '55887b7e01a4de2ea71c5ab2',
            'autorizacion': '55887b7e01a4de2ea71c5ab8',
        }

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def get_hoy(self, locations=None):
        tz = self._tz()
        now = self._now(tz)
        hoy = now.date()
        empleados = self._empleados_filtrados(locations)
        ids = [e['employee_id'] for e in empleados]
        horarios = self._horarios_por_nombre([e.get('horario') for e in empleados])
        jornadas = self._jornadas(hoy, hoy, ids)
        abiertos = self._checkins_abiertos(ids)
        vacaciones = self._vacaciones(hoy, hoy)

        rows = []
        for e in empleados:
            uid = e['employee_id']
            horario = horarios.get(e.get('horario'))
            turno = next(iter(self._turnos_del_dia(horario, hoy, tz)), None)
            jornada = jornadas.get((uid, hoy))
            checkin = abiertos.get(uid)
            row = {
                'user_id': uid,
                'nombre': e['nombre'],
                'horario': e.get('horario'),
                'turno': self._turno_fmt(turno),
                'llegada': (jornada or {}).get('inicio'),
                'retraso_min': None,
                'estado': self._estado(horario, turno, jornada, vacaciones.get(uid, {}).get(hoy), now),
                'lugar': self._lugar(checkin),
                'rol': (checkin or {}).get('rol'),
                'jornada_abierta': bool(jornada and not jornada.get('cierre')),
            }
            if jornada and turno:
                llegada = self._parse(jornada.get('inicio'), tz)
                if llegada:
                    row['retraso_min'] = max(int((llegada - turno['entrada_dt']).total_seconds() // 60), 0)
            rows.append(row)

        resumen = {
            'programados': sum(1 for r in rows if r['turno']),
            'a_tiempo': sum(1 for r in rows if r['estado'] == 'presente' and r['turno']),
            'retardo': sum(1 for r in rows if r['estado'] in ('retardo', 'falta_por_retardo')),
            'no_ha_llegado': sum(1 for r in rows if r['estado'] == 'no_ha_llegado'),
            'fuera_de_horario': sum(1 for r in rows if r['estado'] == 'fuera_de_horario'),
            'dentro': sum(1 for r in rows if r['lugar']),
        }
        orden = ['no_ha_llegado', 'falta_por_retardo', 'retardo', 'fuera_de_horario', 'presente', 'asistio',
                 'por_llegar', 'sin_horario', 'descanso']
        rows.sort(key=lambda r: (orden.index(r['estado']) if r['estado'] in orden else len(orden), r['nombre']))
        return {'fecha': hoy.isoformat(), 'hora': now.strftime('%H:%M'), 'resumen': resumen, 'empleados': rows}

    def get_periodo(self, desde=None, hasta=None, locations=None):
        tz = self._tz()
        now = self._now(tz)
        hoy = now.date()
        desde, hasta = self._rango(desde, hasta, hoy)
        empleados = self._empleados_filtrados(locations)
        ids = [e['employee_id'] for e in empleados]
        horarios = self._horarios_por_nombre([e.get('horario') for e in empleados])
        jornadas = self._jornadas(desde, hasta, ids)
        vacaciones = self._vacaciones(desde, hasta)

        result = []
        for e in empleados:
            uid = e['employee_id']
            horario = horarios.get(e.get('horario'))
            resumen = {'asistencias': 0, 'retardos': 0, 'faltas': 0, 'descansos': 0,
                       'horas_trabajadas': 0.0, 'horas_programadas': 0.0}
            dias = []
            fecha = desde
            while fecha <= hasta:
                turno = next(iter(self._turnos_del_dia(horario, fecha, tz)), None)
                jornada = jornadas.get((uid, fecha))
                if e.get('alta') and fecha < e['alta'] and not jornada:
                    estado = 'sin_registro'
                else:
                    estado = self._estado(horario, turno, jornada, vacaciones.get(uid, {}).get(fecha), now)
                    if estado in ('no_ha_llegado', 'por_llegar'):
                        estado = 'falta' if estado == 'no_ha_llegado' else 'sin_registro'
                    if turno and fecha <= hoy and estado not in ('sin_registro',) and not vacaciones.get(uid, {}).get(fecha):
                        resumen['horas_programadas'] += (turno['salida_dt'] - turno['entrada_dt']).total_seconds() / 3600
                if estado in ('presente', 'asistio', 'fuera_de_horario'):
                    resumen['asistencias'] += 1
                elif estado == 'retardo':
                    resumen['asistencias'] += 1
                    resumen['retardos'] += 1
                elif estado in FALTAS:
                    resumen['faltas'] += 1
                elif estado == 'descanso':
                    resumen['descansos'] += 1
                if jornada:
                    resumen['horas_trabajadas'] += self._horas(jornada, tz, now)
                dias.append({'fecha': fecha.isoformat(), 'estado': estado})
                fecha += timedelta(days=1)
            resumen['horas_trabajadas'] = round(resumen['horas_trabajadas'], 1)
            resumen['horas_programadas'] = round(resumen['horas_programadas'], 1)
            result.append({'user_id': uid, 'nombre': e['nombre'], 'horario': e.get('horario'),
                           'dias': dias, 'resumen': resumen})
        return {'desde': desde.isoformat(), 'hasta': hasta.isoformat(), 'empleados': result}

    def get_dia(self, user_id, fecha=None):
        tz = self._tz()
        now = self._now(tz)
        fecha = self._fecha(fecha) or now.date()
        user_id = int(user_id)
        empleado = next((e for e in self._empleados() if e['employee_id'] == user_id), {})
        horario = self._horarios_por_nombre([empleado.get('horario')]).get(empleado.get('horario'))
        turno = next(iter(self._turnos_del_dia(horario, fecha, tz)), None)
        jornada = self._jornadas(fecha, fecha, [user_id]).get((user_id, fecha))
        checkins = self._checkins_del_dia(user_id, fecha, jornada)
        vacaciones = self._vacaciones(fecha, fecha).get(user_id, {}).get(fecha)
        return {
            'user_id': user_id,
            'nombre': empleado.get('nombre', ''),
            'fecha': fecha.isoformat(),
            'horario': empleado.get('horario'),
            'turno': self._turno_fmt(turno),
            'estado': self._estado(horario, turno, jornada, vacaciones, now),
            'jornada': {
                'folio': jornada.get('folio'),
                'inicio': jornada.get('inicio'),
                'cierre': jornada.get('cierre'),
                'tipo_cierre': jornada.get('tipo_cierre'),
                'horas': round(self._horas(jornada, tz, now), 2),
                'ubicacion': jornada.get('ubicacion_horario'),
            } if jornada else None,
            'checkins': checkins,
        }

    def get_locations(self):
        rows = self.lkf_api.search_catalog(self.Location.UBICACIONES_CAT_ID, {
            'selector': {}, 'fields': ['_id', f"answers.{self.Location.f['location']}"], 'limit': 200}) or []
        return sorted({r.get(self.Location.f['location']) for r in rows if r.get(self.Location.f['location'])})

    # ------------------------------------------------------------------
    # Estado de un día
    # ------------------------------------------------------------------

    def _estado(self, horario, turno, jornada, vacaciones, now):
        if jornada:
            if jornada.get('status'):
                return jornada['status']
            # Registró asistencia sin turno que le correspondiera; sin horario no hay puntualidad que medir.
            return 'fuera_de_horario' if horario else 'asistio'
        if vacaciones:
            return vacaciones
        if not horario or (horario.get('tipo') or 'semanal') != 'semanal':
            return 'sin_horario'
        if not turno:
            return 'descanso'
        limite = turno['entrada_dt'] + timedelta(minutes=int(horario.get('retardo_maximo') or 0))
        return 'no_ha_llegado' if now > limite else 'por_llegar'

    # ------------------------------------------------------------------
    # Lecturas
    # ------------------------------------------------------------------

    def _empleados(self):
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.EMPLEADOS,
                **self._get_match_q(self.employee_fields['estatus_dentro_empresa'], 'activo'),
            }},
            {'$project': {
                '_id': 0,
                'created_at': 1,
                'employee_id': f"$answers.{self.USUARIOS_OBJ_ID}.{self.employee_fields['user_id_id']}",
                'nombre': f"$answers.{self.f['worker_name']}",
                'horario': f"$answers.{self.HORARIOS_CAT_OBJ_ID}.{self.asistencia_fields['nombre_horario']}",
            }},
        ]
        res = []
        for e in self.cr.aggregate(query):
            emp_id = self.unlist(e.get('employee_id'))
            if emp_id:
                alta = e.get('created_at')
                res.append({'employee_id': int(emp_id), 'nombre': e.get('nombre') or '',
                            'alta': alta.date() if hasattr(alta, 'date') else None,
                            'horario': self.unlist(e.get('horario'))})
        return sorted(res, key=lambda e: e['nombre'])

    def _empleados_filtrados(self, locations):
        empleados = self._empleados()
        if not locations:
            return empleados
        ubicaciones = self._ubicaciones_por_usuario([e['employee_id'] for e in empleados])
        return [e for e in empleados if ubicaciones.get(e['employee_id'], set()) & set(locations)]

    def _ubicaciones_por_usuario(self, user_ids):
        user_path = f'answers.{self.EMPLOYEE_OBJ_ID}.{self.employee_fields["user_id_id"]}'
        query = [
            {'$match': {'deleted_at': {'$exists': False}, 'form_id': self.CONF_AREA_EMPLEADOS, user_path: {'$in': user_ids}}},
            {'$unwind': f'${user_path}'},
            {'$unwind': f'$answers.{self.f["areas_group"]}'},
            {'$project': {
                '_id': 0,
                'user_id': f'${user_path}',
                'ubicacion': f'$answers.{self.f["areas_group"]}.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.Location.f["location"]}',
            }},
        ]
        res = defaultdict(set)
        for r in self.cr.aggregate(query):
            if r.get('ubicacion'):
                res[int(r['user_id'])].add(r['ubicacion'])
        return res

    def _jornadas(self, desde, hasta, user_ids):
        """{(user_id, fecha): jornada} con la última jornada de cada persona por día."""
        f = self.asistencia_fields
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.REGISTRO_ASISTENCIA,
                'user_id': {'$in': user_ids},
                f'answers.{f["inicio"]}': {'$gte': f'{desde.isoformat()} 00:00:00', '$lte': f'{hasta.isoformat()} 23:59:59'},
            }},
            {'$sort': {f'answers.{f["inicio"]}': -1}},
            {'$project': {
                '_id': 0,
                'folio': 1,
                'user_id': 1,
                'inicio': f'$answers.{f["inicio"]}',
                'cierre': f'$answers.{f["cierre"]}',
                'status': f'$answers.{f["status"]}',
                'horas_trabajadas': f'$answers.{f["horas_trabajadas"]}',
                'nombre_horario': f'$answers.{f["nombre_horario"]}',
                'ubicacion_horario': f'$answers.{f["ubicacion_horario"]}',
                'tipo_cierre': f'$answers.{f["tipo_cierre"]}',
            }},
        ]
        res = {}
        for j in self.cr.aggregate(query):
            fecha = self._fecha((j.get('inicio') or '')[:10])
            if fecha:
                res.setdefault((j['user_id'], fecha), j)
        return res

    def _checkin_project(self):
        f = self.checkin_fields
        return {
            '_id': 0,
            'folio': 1,
            'user_id': 1,
            'folio_jornada': f'$answers.{f["folio_jornada"]}',
            'ubicacion': f'$answers.{f["lugar"]}.{f["ubicacion"]}',
            'caseta': f'$answers.{f["lugar"]}.{f["caseta"]}',
            'estatus': f'$answers.{f["estatus"]}',
            'desde': f'$answers.{f["fecha_in"]}',
            'hasta': f'$answers.{f["fecha_out"]}',
            'rol': f'$answers.{self.ROL_CATALOG_OBJ_ID}.{f["rol"]}',
            'suplente': f'$answers.{f["suplente"]}',
            'tipo_out': f'$answers.{f["tipo_out"]}',
            'comentario': f'$answers.{f["comentario"]}',
            'horas': f'$answers.{f["horas_lugar"]}',
            'foto_in': f'$answers.{f["foto_in"]}',
            'foto_out': f'$answers.{f["foto_out"]}',
        }

    def _checkins_abiertos(self, user_ids):
        res = {}
        for c in self.cr.aggregate(self._checkin_query({'user_id': {'$in': user_ids}})):
            res.setdefault(c.get('user_id'), {k: self.unlist(c.get(k)) for k in ('ubicacion', 'caseta', 'rol')})
        return res

    def _checkins_del_dia(self, user_id, fecha, jornada):
        """Los Check In de la jornada; los anteriores al folio de jornada, por fecha."""
        f = self.checkin_fields
        match = {'deleted_at': {'$exists': False}, 'form_id': self.CHECKIN}
        if jornada and jornada.get('folio'):
            # Los Check In de antes del folio de jornada se ligan por caer dentro de ella.
            dentro = {'$gte': jornada.get('inicio'), '$lte': jornada.get('cierre') or f'{fecha.isoformat()} 23:59:59'}
            match['$or'] = [
                {f'answers.{f["folio_jornada"]}': jornada['folio']},
                {'user_id': user_id, f'answers.{f["folio_jornada"]}': {'$exists': False},
                 f'answers.{f["fecha_in"]}': dentro},
            ]
        else:
            match.update({'user_id': user_id, f'answers.{f["fecha_in"]}': {'$regex': f'^{fecha.isoformat()}'}})
        rows = []
        for c in self.cr.aggregate([{'$match': match}, {'$sort': {f'answers.{f["fecha_in"]}': 1}},
                                    {'$project': self._checkin_project()}]):
            for k in ('ubicacion', 'caseta', 'rol'):
                c[k] = self.unlist(c.get(k))
            c['foto_in'] = c.get('foto_in') or []
            c['foto_out'] = c.get('foto_out') or []
            rows.append(c)
        return rows

    def _vacaciones(self, desde, hasta):
        """{user_id: {fecha: tipo}} de los permisos autorizados que caen en el rango."""
        if not self.FORMATO_VACACIONES:
            return {}
        v = self.vacaciones_fields
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.FORMATO_VACACIONES,
                f'answers.{v["autorizacion"]}': 'autorizado',
            }},
            {'$project': {
                '_id': 0,
                'inicio': f'$answers.{v["inicio"]}',
                'fin': f'$answers.{v["fin"]}',
                'tipo': f'$answers.{v["tipo"]}',
                'user_id': f'$answers.{self.EMPLOYEE_OBJ_ID}.{self.employee_fields["user_id_id"]}',
            }},
        ]
        res = defaultdict(dict)
        for r in self.cr.aggregate(query):
            ini, fin = self._fecha((r.get('inicio') or '')[:10]), self._fecha((r.get('fin') or '')[:10])
            try:
                uid = int(self.unlist(r.get('user_id')))
            except (TypeError, ValueError):
                continue
            if not ini or not fin:
                continue
            d = max(ini, desde)
            while d <= min(fin, hasta):
                res[uid][d] = r.get('tipo') or 'vacaciones'
                d += timedelta(days=1)
        return res

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _horas(self, jornada, tz, now):
        if jornada.get('horas_trabajadas') is not None and jornada.get('cierre'):
            return float(jornada['horas_trabajadas'] or 0)
        inicio = self._parse(jornada.get('inicio'), tz)
        return max((now - inicio).total_seconds(), 0) / 3600 if inicio else 0.0

    def _turno_fmt(self, turno):
        if not turno:
            return None
        return {'entrada': (turno['hora_entrada'] or '')[:5], 'salida': (turno['hora_salida'] or '')[:5]}

    def _lugar(self, checkin):
        if not checkin:
            return None
        return ' · '.join(x for x in (checkin.get('ubicacion'), checkin.get('caseta')) if x) or None

    def _rango(self, desde, hasta, hoy):
        desde = self._fecha(desde) or hoy.replace(day=1)
        hasta = self._fecha(hasta) or hoy
        if hasta < desde:
            desde, hasta = hasta, desde
        # Tope de 93 días para que el reporte no se vuelva pesado.
        return desde, min(hasta, desde + timedelta(days=92))

    def _fecha(self, value):
        if not value:
            return None
        if hasattr(value, 'year') and not isinstance(value, str):
            return value
        try:
            return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()
        except ValueError:
            return None

    def _tz(self):
        return self._user_tz(self.user.get('user_id'))
