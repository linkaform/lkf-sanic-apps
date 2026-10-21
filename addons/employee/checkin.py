# -*- coding: utf-8 -*-
"""Check In / Check Out: presencia de una persona en un lugar (ubicación → caseta).

Un registro de `checkin_checkout_casetas` por persona y Check In. Lo usa cualquier
perfil (guardia, promotor, contratista...). Requiere estar Disponible
(asistencia); pasar a Ausente hace Check Out automático de lo abierto.
"""

from collections import defaultdict

from .asistencia import Asistencia, DATE_FMT


class Presencia(Asistencia):

    def __init__(self, settings, **kwargs):
        super().__init__(settings, **kwargs)
        self.CHECKIN = self.lkm.form_id('checkin_checkout_casetas', 'id')
        rol = self.lkm.catalog_id('rol') or {}
        self.ROL_CATALOG_ID = rol.get('id')
        self.ROL_CATALOG_OBJ_ID = rol.get('obj_id')

        self.checkin_fields = {
            'lugar': self.CONF_AREA_EMPLEADOS_CAT_OBJ_ID,
            'nombre': '62c5ff407febce07043024dd',
            'ubicacion': '663e5c57f5b8a7ce8211ed0b',
            'caseta': '663e5d44f5b8a7ce8211ed0f',
            'estatus': '663bffc28d00553254f274e0',
            'fecha_in': '663bffc28d00553254f274e1',
            'fecha_out': '663bffc28d00553254f274e2',
            'rol': '6a46f2730fc4d03a90da2209',
            'suplente': 'da9efe457ebcfb07c4ccf23d',
            'motivo': '26ee3d91370f51e2411bf2ae',
            'tipo_out': '66a5b9bed0c44910177eb723',
            'comentario': '66a5b9bed0c44910177eb724',
            'foto_in': '68d384ef55840a75f2cb7e28',
            'foto_out': '68d384ef55840a75f2cb7e29',
            'folio_jornada': '6ad90e470d23e745a45bfc6d',
            'horas_lugar': '6ad90e471e2847655984f5f0',
            'usuario': '6ad946c981c0e38093dbc8e5',
        }

    # ------------------------------------------------------------------
    # Lecturas
    # ------------------------------------------------------------------

    def get_estado_checkin(self):
        user_id = self.user.get('user_id')
        return {'checkin': self._format_checkin(self._checkin_abierto(user_id))}

    def get_lugares(self):
        """Ubicaciones y casetas donde el usuario puede hacer Check In, con quién está en cada una."""
        user_id = self.user.get('user_id')
        lugares = self._lugares_configurados(user_id)
        ocupantes = self._ocupantes(list(lugares.keys()))
        return [
            {
                'ubicacion': ubicacion,
                'casetas': [
                    {'caseta': caseta, 'ocupantes': ocupantes.get((ubicacion, caseta), [])}
                    for caseta in casetas
                ],
            }
            for ubicacion, casetas in sorted(lugares.items())
        ]

    def get_roles(self):
        if not self.ROL_CATALOG_ID:
            return []
        rows = self.lkf_api.search_catalog(self.ROL_CATALOG_ID, {'selector': {}, 'limit': 1000}) or []
        return sorted({r.get(self.checkin_fields['rol']) for r in rows if r.get(self.checkin_fields['rol'])})

    # ------------------------------------------------------------------
    # Check In / Check Out
    # ------------------------------------------------------------------

    def do_checkin(self, ubicacion, caseta, rol=None, suplente=None, motivo=None, foto=None):
        user_id = self.user.get('user_id')
        tz = self._user_tz(user_id)
        jornada = self._registro_abierto(user_id, tz)
        if not jornada:
            self.LKFException({'title': 'Registra tu asistencia',
                               'msg': 'Para hacer Check In primero cámbiate a Disponible.'})
        abierto = self._checkin_abierto(user_id)
        if abierto:
            self.LKFException({'title': 'Ya tienes un Check In',
                               'msg': f'Haz Check Out de {abierto["ubicacion"]} · {abierto["caseta"]} antes de entrar a otro lugar.'})
        lugares = self._lugares_configurados(user_id)
        if caseta not in lugares.get(ubicacion, []):
            self.LKFException({'title': 'Lugar no permitido',
                               'msg': f'No tienes configurada la caseta {caseta} de {ubicacion}.'})

        f = self.checkin_fields
        empleado = self.get_employee_data(user_id=user_id, get_one=True) or {}
        answers = {
            f['lugar']: {
                f['nombre']: empleado.get('worker_name') or self.user.get('name', ''),
                f['ubicacion']: ubicacion,
                f['caseta']: caseta,
            },
            f['estatus']: 'abierto',
            f['fecha_in']: self._now(tz).strftime(DATE_FMT),
            f['folio_jornada']: jornada.get('folio', ''),
            f['usuario']: user_id,
        }
        if rol and self.ROL_CATALOG_OBJ_ID:
            answers[self.ROL_CATALOG_OBJ_ID] = {f['rol']: rol}
        # Suplente: la cuenta es del titular y quien cubre escribe su propio nombre.
        if suplente:
            answers[f['suplente']] = suplente
            answers[f['motivo']] = motivo or 'otro'
        if foto:
            answers[f['foto_in']] = foto

        metadata = self.lkf_api.get_metadata(form_id=self.CHECKIN)
        metadata.update({
            'properties': {
                'device_properties': {
                    'System': 'Sanic',
                    'Module': 'Employee',
                    'Process': 'Presencia',
                    'Action': 'checkin',
                    'File': 'employee/checkin.py',
                }
            },
            'answers': answers,
        })
        res = self._crear_registro(metadata)
        if res.get('status_code') not in (200, 201, 202):
            self.LKFException({'title': 'Error al hacer Check In', 'msg': res.get('json', res)})
        return self.get_estado_checkin()

    def do_checkout(self, comentario=None, foto=None):
        user_id = self.user.get('user_id')
        abierto = self._checkin_abierto(user_id)
        if not abierto:
            self.LKFException({'title': 'Sin Check In', 'msg': 'No tienes un Check In abierto.'})
        self._cerrar_checkin(abierto, self._now(self._user_tz(user_id)), 'manual', comentario, foto)
        return self.get_estado_checkin()

    def set_estatus(self, estatus):
        # Pasar a Ausente cierra también el Check In abierto.
        if estatus == 'ausente':
            user_id = self.user.get('user_id')
            abierto = self._checkin_abierto(user_id)
            if abierto:
                self._cerrar_checkin(abierto, self._now(self._user_tz(user_id)), 'automatico',
                                     'Check Out automático al pasar a Ausente.')
        return super().set_estatus(estatus)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _cerrar(self, registro, cierre_dt, tz, automatico=False):
        """Si la jornada se cierra sola (olvidada), sus Check In abiertos también."""
        res = super()._cerrar(registro, cierre_dt, tz, automatico=automatico)
        if automatico:
            usuario = registro.get('usuario') or self.user.get('user_id')
            query = self._checkin_query({f'answers.{self.checkin_fields["usuario"]}': usuario})
            for abierto in self.format_cr(self.cr.aggregate(query)) or []:
                inicio = self._parse(abierto.get('desde'), tz)
                cierre = max(cierre_dt, inicio) if inicio else cierre_dt
                self._cerrar_checkin(abierto, cierre, 'automatico',
                                     'Check Out automático: la jornada se cerró sola.')
        return res

    def _cerrar_checkin(self, registro, cierre_dt, tipo, comentario=None, foto=None):
        f = self.checkin_fields
        answers = {
            f['estatus']: 'cerrado',
            f['fecha_out']: cierre_dt.strftime(DATE_FMT),
            f['tipo_out']: tipo,
        }
        inicio = self._parse(registro.get('desde'), self._user_tz(self.user.get('user_id')))
        if inicio:
            answers[f['horas_lugar']] = round(max((cierre_dt - inicio).total_seconds(), 0) / 3600, 2)
        if comentario:
            answers[f['comentario']] = comentario
        if foto:
            answers[f['foto_out']] = foto
        res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.CHECKIN, record_id=[str(registro['_id'])])
        if res.get('status_code') not in (200, 201, 202):
            self.LKFException({'title': 'Error al hacer Check Out', 'msg': res.get('json', res)})
        return res

    def _checkin_query(self, match):
        f = self.checkin_fields
        lugar = f['lugar']
        return [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.CHECKIN,
                f'answers.{f["estatus"]}': 'abierto',
                **match,
            }},
            {'$sort': {'created_at': -1}},
            {'$project': {
                '_id': 1,
                'folio': 1,
                'user_id': f'$answers.{f["usuario"]}',
                'nombre': f'$answers.{lugar}.{f["nombre"]}',
                'ubicacion': f'$answers.{lugar}.{f["ubicacion"]}',
                'caseta': f'$answers.{lugar}.{f["caseta"]}',
                'desde': f'$answers.{f["fecha_in"]}',
                'rol': f'$answers.{self.ROL_CATALOG_OBJ_ID}.{f["rol"]}',
                'suplente': f'$answers.{f["suplente"]}',
            }},
        ]

    def _checkin_abierto(self, user_id):
        query = self._checkin_query({f'answers.{self.checkin_fields["usuario"]}': user_id})
        return self.format_cr(self.cr.aggregate(query), get_one=True) or None

    def _ocupantes(self, ubicaciones):
        if not ubicaciones:
            return {}
        lugar = self.checkin_fields['lugar']
        query = self._checkin_query({f'answers.{lugar}.{self.checkin_fields["ubicacion"]}': {'$in': ubicaciones}})
        res = defaultdict(list)
        for r in self.format_cr(self.cr.aggregate(query)):
            res[(r.get('ubicacion'), r.get('caseta'))].append({
                'user_id': r.get('user_id'),
                'nombre': r.get('nombre'),
                'desde': r.get('desde'),
                'rol': r.get('rol'),
            })
        return res

    def _lugares_configurados(self, user_id):
        """{ubicacion: [casetas]} según la config de áreas y empleados; ubicación sin caseta = todas sus casetas."""
        query = [
            {'$match': {
                'deleted_at': {'$exists': False},
                'form_id': self.CONF_AREA_EMPLEADOS,
                f'answers.{self.EMPLOYEE_OBJ_ID}.{self.employee_fields["user_id_id"]}': user_id,
            }},
            {'$unwind': f'$answers.{self.f["areas_group"]}'},
            {'$project': {
                '_id': 0,
                'ubicacion': f'$answers.{self.f["areas_group"]}.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.Location.f["location"]}',
                'caseta': f'$answers.{self.f["areas_group"]}.{self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.Location.f["area"]}',
            }},
        ]
        lugares = defaultdict(set)
        sin_caseta = set()
        for r in self.cr.aggregate(query):
            ubicacion = r.get('ubicacion')
            if not ubicacion:
                continue
            if r.get('caseta'):
                lugares[ubicacion].add(r['caseta'])
            else:
                sin_caseta.add(ubicacion)
        for ubicacion in sin_caseta:
            lugares[ubicacion].update(self.Location.get_areas_by_location(ubicacion) or [])
        return {u: sorted(c) for u, c in lugares.items()}

    def _format_checkin(self, r):
        if not r:
            return None
        return {
            'folio': r.get('folio'),
            'ubicacion': r.get('ubicacion'),
            'caseta': r.get('caseta'),
            'desde': r.get('desde'),
            'rol': r.get('rol'),
            'suplente': r.get('suplente'),
        }
