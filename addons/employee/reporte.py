# -*- coding: utf-8 -*-
"""Reporte de asistencias sobre el modelo nuevo.

La jornada (`registro_de_asistencia`) da el status del día, las horas y la
ubicación del horario; los Check In (`checkin_checkout_casetas`) dan dónde
estuvo, con qué rol y sus fotos. Se ligan por el folio de la jornada.

Regresa las mismas formas que el reporte viejo (`asistencia_report.py`) para
que el front no cambie de estructura.
"""

from calendar import monthrange
from collections import defaultdict
from datetime import datetime, timedelta
from math import ceil

from .checkin import Presencia

DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
SIN_UBICACION = 'Sin ubicación'
STATUS_LABEL = {'presente': 'Asistencia', 'retardo': 'Retardo', 'falta_por_retardo': 'Falta por retardo'}


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

    def get_report(self, group_by='employees', locations=None, month=None, year=None):
        month, year = self._mes(month, year)
        empleados = self._empleados()
        jornadas = self._jornadas_del_mes(month, year, [e['employee_id'] for e in empleados])
        checkins = self._checkins_por_jornada([j['folio'] for j in jornadas])
        for j in jornadas:
            j['checkins'] = checkins.get(j['folio'], [])
            j['ubicacion'] = j.get('ubicacion_horario') or next(
                (c['ubicacion'] for c in j['checkins'] if c.get('ubicacion')), None) or SIN_UBICACION
        if locations:
            jornadas = [j for j in jornadas if self._ubicaciones_de(j) & set(locations)]
        if group_by == 'locations':
            return self._por_ubicacion(jornadas, empleados, month, year)
        return self._por_empleado(jornadas, empleados, month, year, bool(locations))

    def get_locations(self):
        rows = self.lkf_api.search_catalog(self.Location.UBICACIONES_CAT_ID, {
            'selector': {}, 'fields': ['_id', f"answers.{self.Location.f['location']}"], 'limit': 200}) or []
        return sorted({r.get(self.Location.f['location']) for r in rows if r.get(self.Location.f['location'])})

    def get_detail(self, user_ids=None, selected_day=1, location=None, month=None, year=None):
        month, year = self._mes(month, year)
        user_ids = [int(u) for u in (user_ids or []) if u]
        jornadas = self._jornadas_del_mes(month, year, user_ids)
        checkins = self._checkins_por_jornada([j['folio'] for j in jornadas])
        for j in jornadas:
            j['checkins'] = checkins.get(j['folio'], [])
        if location and location != SIN_UBICACION:
            jornadas = [j for j in jornadas if location in self._ubicaciones_de(j)]

        hoy = self._hoy()
        alta = next((e.get('alta') for e in self._empleados() if e['employee_id'] in user_ids), None)
        dias_libres = self._dias_descanso(next(iter(user_ids), None))
        por_dia = {j['dia']: j for j in jornadas}
        indicadores = {'cantidad_asistencias': 0, 'retardos': 0, 'faltas': 0}
        horas = 0.0
        asistencia_mes = []
        for dia in range(1, monthrange(year, month)[1] + 1):
            status = self._status_dia(datetime(year, month, dia).date(), hoy, por_dia.get(dia), dias_libres, {}, alta)
            self._sumar(indicadores, status, keys=('cantidad_asistencias', 'retardos', 'faltas'))
            asistencia_mes.append({'dia': dia, 'status': status})
        for j in jornadas:
            horas += float(j.get('horas_trabajadas') or 0)

        jornada = por_dia.get(int(selected_day or 0))
        return {
            'guardia_generales': self._generales(jornada) if jornada else {},
            'asistencia_mes': asistencia_mes,
            'indicadores_generales': {**indicadores, 'horas_trabajadas': f'{round(horas, 1)} h'},
        }

    def get_records(self, locations=None, month=None, year=None, limit=100, offset=0):
        """Un renglón por Check In del mes (fotos de entrada y salida), el más reciente primero."""
        month, year = self._mes(month, year)
        desde, hasta = self._rango(month, year)
        f = self.checkin_fields
        match = {
            'deleted_at': {'$exists': False},
            'form_id': self.CHECKIN,
            f'answers.{f["fecha_in"]}': {'$gte': desde, '$lte': hasta},
        }
        if locations:
            match[f'answers.{f["lugar"]}.{f["ubicacion"]}'] = {'$in': locations}
        total = next(iter(self.cr.aggregate([{'$match': match}, {'$count': 'n'}])), {}).get('n', 0)
        query = [
            {'$match': match},
            {'$sort': {f'answers.{f["fecha_in"]}': -1}},
            {'$skip': int(offset)},
            {'$limit': int(limit)},
            {'$project': self._checkin_project()},
        ]
        rows = list(self.cr.aggregate(query))
        jornadas = {j['folio']: j for j in self._jornadas_por_folio([r.get('folio_jornada') for r in rows])}
        records = []
        for r in rows:
            j = jornadas.get(r.get('folio_jornada')) or {}
            records.append({
                '_id': str(r['_id']),
                'folio': r.get('folio'),
                'attendance_status': STATUS_LABEL.get(j.get('status') or 'presente', '') if j else '',
                'attendance_start_pic': self._primera(r.get('foto_in')),
                'attendance_end_pic': self._primera(r.get('foto_out')),
                'attendance_name': self.unlist(r.get('nombre')) or '',
                'attendance_sup_name': r.get('suplente') or '',
                'attendance_horario': j.get('nombre_horario') or '',
                'attendance_position': self.unlist(r.get('rol')) or '',
                'attendance_location': self.unlist(r.get('ubicacion')) or '',
                'attendance_area': self.unlist(r.get('caseta')) or '',
                'attendance_start_time': r.get('desde'),
                'attendance_end_time': r.get('hasta'),
                'attendance_start_comment': '',
                'attendance_end_comment': r.get('comentario') or '',
                'attendance_work_hours': r.get('horas'),
            })
        return {
            'records': records,
            'total_records': total,
            'total_pages': ceil(total / limit) if limit else 1,
            'actual_page': (int(offset) // int(limit)) + 1 if limit else 1,
            'records_on_page': len(records),
        }

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

    def _jornada_project(self):
        f = self.asistencia_fields
        return {
            '_id': 0,
            'folio': 1,
            'user_id': 1,
            'inicio': f'$answers.{f["inicio"]}',
            'cierre': f'$answers.{f["cierre"]}',
            'status': f'$answers.{f["status"]}',
            'horas_trabajadas': f'$answers.{f["horas_trabajadas"]}',
            'nombre_horario': f'$answers.{f["nombre_horario"]}',
            'hora_entrada': f'$answers.{f["hora_entrada"]}',
            'hora_salida': f'$answers.{f["hora_salida"]}',
            'ubicacion_horario': f'$answers.{f["ubicacion_horario"]}',
            'tipo_cierre': f'$answers.{f["tipo_cierre"]}',
        }

    def _jornadas_del_mes(self, month, year, user_ids):
        """La última jornada de cada empleado por día del mes."""
        desde, hasta = self._rango(month, year)
        f = self.asistencia_fields
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.REGISTRO_ASISTENCIA,
                'user_id': {'$in': user_ids},
                f'answers.{f["inicio"]}': {'$gte': desde, '$lte': hasta},
            }},
            {'$sort': {f'answers.{f["inicio"]}': -1}},
            {'$project': self._jornada_project()},
        ]
        vistas, jornadas = set(), []
        for j in self.cr.aggregate(query):
            inicio = j.get('inicio') or ''
            clave = (j.get('user_id'), inicio[:10])
            if clave in vistas:
                continue
            vistas.add(clave)
            j['dia'] = int(inicio[8:10])
            jornadas.append(j)
        return jornadas

    def _jornadas_por_folio(self, folios):
        folios = [x for x in folios if x]
        if not folios:
            return []
        return list(self.cr.aggregate([
            {'$match': {'deleted_at': {'$exists': False}, 'form_id': self.REGISTRO_ASISTENCIA, 'folio': {'$in': folios}}},
            {'$project': self._jornada_project()},
        ]))

    def _checkin_project(self):
        f = self.checkin_fields
        return {
            '_id': 1,
            'folio': 1,
            'user_id': 1,
            'folio_jornada': f'$answers.{f["folio_jornada"]}',
            'nombre': f'$answers.{f["lugar"]}.{f["nombre"]}',
            'ubicacion': f'$answers.{f["lugar"]}.{f["ubicacion"]}',
            'caseta': f'$answers.{f["lugar"]}.{f["caseta"]}',
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

    def _checkins_por_jornada(self, folios):
        folios = [x for x in folios if x]
        if not folios:
            return {}
        f = self.checkin_fields
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.CHECKIN,
                f'answers.{f["folio_jornada"]}': {'$in': folios},
            }},
            {'$sort': {f'answers.{f["fecha_in"]}': 1}},
            {'$project': self._checkin_project()},
        ]
        res = defaultdict(list)
        for c in self.cr.aggregate(query):
            c['_id'] = str(c['_id'])
            for k in ('nombre', 'ubicacion', 'caseta', 'rol'):
                c[k] = self.unlist(c.get(k))
            res[c['folio_jornada']].append(c)
        return res

    def _vacaciones(self, month, year):
        """{user_id: {dia: tipo}} de los permisos autorizados que caen en el mes."""
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
            try:
                ini = datetime.strptime(r['inicio'][:10], '%Y-%m-%d').date()
                fin = datetime.strptime(r['fin'][:10], '%Y-%m-%d').date()
                uid = int(self.unlist(r.get('user_id')))
            except (KeyError, TypeError, ValueError):
                continue
            d = ini
            while d <= fin:
                if d.year == year and d.month == month:
                    res[uid][d.day] = r.get('tipo')
                d += timedelta(days=1)
        return res

    # ------------------------------------------------------------------
    # Formatos
    # ------------------------------------------------------------------

    def _por_empleado(self, jornadas, empleados, month, year, filtrado):
        hoy = self._hoy()
        vacaciones = self._vacaciones(month, year)
        nombres = {e['employee_id']: e['nombre'] for e in empleados}
        altas = {e['employee_id']: e.get('alta') for e in empleados}
        descansos = self._descansos(empleados)
        grupos = defaultdict(list)
        for j in jornadas:
            grupos[(j['user_id'], j['ubicacion'])].append(j)
        # Sin filtro de ubicación, los empleados sin jornadas también salen (todo falta).
        if not filtrado:
            con_jornada = {uid for uid, _ in grupos}
            for e in empleados:
                if e['employee_id'] not in con_jornada:
                    grupos[(e['employee_id'], SIN_UBICACION)] = []

        result = []
        for (uid, ubicacion), js in grupos.items():
            por_dia = {j['dia']: j for j in js}
            dias_libres = descansos.get(uid, [])
            resumen = {'asistencias': 0, 'retardos': 0, 'faltas': 0}
            asistencia_mes = []
            for dia in range(1, monthrange(year, month)[1] + 1):
                j = por_dia.get(dia)
                status = self._status_dia(datetime(year, month, dia).date(), hoy, j, dias_libres,
                                          vacaciones.get(uid, {}), altas.get(uid))
                self._sumar(resumen, status)
                item = {'dia': dia, 'status': status}
                if j and status == (j.get('status') or 'presente'):
                    item['fecha_inicio'] = j.get('inicio')
                    if j.get('cierre'):
                        item['fecha_cierre'] = j['cierre']
                        item['closed'] = True
                asistencia_mes.append(item)
            result.append({
                'employee_id': uid,
                'nombre': nombres.get(uid, str(uid)),
                'ubicacion': ubicacion,
                'asistencia_mes': asistencia_mes,
                'resumen': resumen,
            })
        return sorted(result, key=lambda r: (r['nombre'], r['ubicacion']))

    def _por_ubicacion(self, jornadas, empleados, month, year):
        nombres = {e['employee_id']: e['nombre'] for e in empleados}
        descansos = self._descansos(empleados)
        dias_mes = monthrange(year, month)[1]
        grupos = {}
        for j in jornadas:
            turno = f"{j.get('nombre_horario') or 'Sin horario'} {j.get('hora_entrada') or ''}-{j.get('hora_salida') or ''}".strip(' -')
            g = grupos.setdefault((j['ubicacion'], turno), {
                'ubicacion': j['ubicacion'],
                'turno_ref': turno,
                'asistencia_mes': [{'dia': d, 'empleados': []} for d in range(1, dias_mes + 1)],
                'resumen': {'asistencias': 0, 'retardos': 0, 'faltas': 0},
            })
            dia_semana = DIAS[datetime(year, month, j['dia']).weekday()]
            status = 'dia_libre' if dia_semana in descansos.get(j['user_id'], []) else (j.get('status') or 'presente')
            # El front separa "nombre-status-id" por guiones: el nombre no puede llevar guion.
            nombre = (nombres.get(j['user_id']) or str(j['user_id'])).replace('-', '–')
            g['asistencia_mes'][j['dia'] - 1]['empleados'].append(f"{nombre}-{status}-{j['user_id']}")
            self._sumar(g['resumen'], status)
        for g in grupos.values():
            for d in g['asistencia_mes']:
                if not d['empleados']:
                    d['empleados'] = ['sin_registro-sin_registro']
        return sorted(grupos.values(), key=lambda g: (g['ubicacion'], g['turno_ref']))

    def _generales(self, j):
        """Detalle del día con las llaves que lee el modal del reporte, más sus Check In."""
        checkins = j.get('checkins') or []
        primero = checkins[0] if checkins else {}
        ultimo = checkins[-1] if checkins else {}
        return {
            'fecha_inicio_turno': j.get('inicio'),
            'end_shift': j.get('cierre'),
            'status_turn': j.get('status') or 'presente',
            'nombre_horario': j.get('nombre_horario'),
            'hora_entrada': j.get('hora_entrada'),
            'hora_salida': j.get('hora_salida'),
            'horas_trabajadas': j.get('horas_trabajadas'),
            'tipo_cierre': j.get('tipo_cierre'),
            'comentario_inicio_turno': '',
            'comentario_cierre_turno': ultimo.get('comentario') or '',
            'incidente_location': primero.get('ubicacion') or j.get('ubicacion_horario'),
            'incidente_area': primero.get('caseta'),
            'tipo_guardia': primero.get('rol'),
            'foto_inicio_turno': primero.get('foto_in') or [],
            'foto_end': ultimo.get('foto_out') or [],
            'checkins': checkins,
        }

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def _descansos(self, empleados):
        """{user_id: [días de la semana sin turno]} según el horario semanal de cada empleado."""
        horarios = self._horarios_por_nombre([e.get('horario') for e in empleados])
        res = {}
        for e in empleados:
            dias = self._dias_sin_turno(horarios.get(e.get('horario')))
            if dias:
                res[e['employee_id']] = dias
        return res

    def _dias_descanso(self, user_id):
        return self._dias_sin_turno(self._horario_de(user_id)) if user_id else []

    def _dias_sin_turno(self, horario):
        # Sin horario (o con uno de ciclo, que aún no se calcula) no se sabe qué días descansa.
        if not horario or (horario.get('tipo') or 'semanal') != 'semanal':
            return []
        con_turno = set()
        for renglon in horario.get('dias') or []:
            con_turno.update(renglon.get(self.horario_fields['dias_semana']) or [])
        return [d for d in DIAS if d not in con_turno]

    def _ubicaciones_de(self, j):
        ubicaciones = {c.get('ubicacion') for c in j.get('checkins') or []}
        ubicaciones.update({j.get('ubicacion_horario'), j.get('ubicacion')})
        return {u for u in ubicaciones if u}

    def _status_dia(self, fecha, hoy, jornada, dias_libres, vacaciones, alta=None):
        if not jornada and alta and fecha < alta:
            return 'sin_registro'
        if fecha.day in vacaciones:
            return vacaciones[fecha.day]
        if DIAS[fecha.weekday()] in (dias_libres or []):
            return 'dia_libre'
        if jornada:
            return jornada.get('status') or 'presente'
        return 'falta' if fecha < hoy else 'sin_registro'

    def _sumar(self, resumen, status, keys=('asistencias', 'retardos', 'faltas')):
        asistencias, retardos, faltas = keys
        if status == 'presente':
            resumen[asistencias] += 1
        elif status == 'retardo':
            resumen[retardos] += 1
        elif status in ('falta', 'falta_por_retardo'):
            resumen[faltas] += 1

    def _primera(self, fotos):
        if isinstance(fotos, list):
            return fotos[0] if fotos else []
        return fotos or []

    def _mes(self, month, year):
        hoy = self._hoy()
        return int(month or hoy.month), int(year or hoy.year)

    def _rango(self, month, year):
        ultimo = monthrange(year, month)[1]
        return f'{year:04d}-{month:02d}-01 00:00:00', f'{year:04d}-{month:02d}-{ultimo:02d} 23:59:59'

    def _hoy(self):
        return self._now(self._user_tz(self.user.get('user_id'))).date()
