# -*- coding: utf-8 -*-
"""Autorización de horas extra según la política de la cuenta.

La forma "Política de horas extra" dice si la extra requiere autorización,
quién autoriza (su jefe directo o usuarios específicos), si el motivo es
obligatorio, los motivos y los topes. Cuando requiere autorización, la
solicitud se manda a la bandeja (CouchDB `clave_{user_id}`) de quien autoriza,
que la resuelve desde web.
"""

import time

from couchdb.http import ResourceNotFound

POLITICA_FIELDS = {
    'requiere': '6ad94f6d2c30b34c8bfaf315',
    'momentos': '6ad94f6d92f74af995dc1431',
    'quien': '6ad94f6d4fc03bf55bd0bfed',
    'usuarios': '6ad94f6dd5e448b78ef12310',
    'motivo_obligatorio': '6ad94f6dea66b2054973bdb1',
    'motivos': '6ad94f6d1bd0371a03b15ecc',
    'motivo': '6ad94f6dc84f1982a145abc0',
    'tope_dia': '6ad94f6d6c46ff09afac7dc3',
    'tope_semana': '6ad94f6d7b1084c3c2894c2c',
    'al_tope': '6ad94f6d4ba6a6c6fedee950',
    'sin_autorizar': '6ad94f6de1dbd3c83d608525',
}
JEFE_DIRECTO_OBJ_ID = '6a7f820cd5f8174ffccac65b'
JEFE_NOMBRE_FIELD = '663bd36eb19b7fb7d9e97ccb'
USER_ID_FIELD = '638a9a99616398d2e392a9f5'


class HorasExtra:

    def _politica(self):
        """La política vigente (el último registro). Sin política: no requiere autorización."""
        p = POLITICA_FIELDS
        forma = self.lkm.form_id('politica_horas_extra', 'id')
        reg = next(iter(self.cr.aggregate([
            {'$match': {'deleted_at': {'$exists': False}, 'form_id': forma}},
            {'$sort': {'created_at': -1}},
            {'$limit': 1},
            {'$project': {'_id': 0, 'answers': 1}},
        ]))) if forma else None
        a = (reg or {}).get('answers') or {}
        usuarios = []
        for renglon in a.get(p['usuarios']) or []:
            for valor in renglon.values():
                if isinstance(valor, dict) and valor.get(USER_ID_FIELD):
                    usuarios.append(int(self.unlist(valor[USER_ID_FIELD])))
        return {
            'requiere': a.get(p['requiere']) == 'si',
            'momentos': a.get(p['momentos']) or [],
            'quien': a.get(p['quien']) or 'jefe_directo',
            'usuarios': usuarios,
            'motivo_obligatorio': a.get(p['motivo_obligatorio']) == 'si',
            'motivos': [r.get(p['motivo']) for r in a.get(p['motivos']) or [] if r.get(p['motivo'])],
            'tope_dia': a.get(p['tope_dia']),
            'tope_semana': a.get(p['tope_semana']),
            'al_tope': a.get(p['al_tope']) or 'avisar',
            'sin_autorizar': a.get(p['sin_autorizar']) or 'por_autorizar',
        }

    def _aprobadores(self, user_id, politica):
        """A quién se le pide la autorización: su jefe directo o los usuarios de la política."""
        if politica['quien'] == 'jefe_directo':
            emp = next(iter(self.cr.aggregate([
                {'$match': {
                    'deleted_at': {'$exists': False},
                    'form_id': self.EMPLEADOS,
                    f'answers.{self.USUARIOS_OBJ_ID}.{self.employee_fields["user_id_id"]}': user_id,
                }},
                {'$limit': 1},
                {'$project': {'_id': 0, 'jefe': f'$answers.{JEFE_DIRECTO_OBJ_ID}.{JEFE_NOMBRE_FIELD}'}},
            ])), {})
            # La forma solo guarda el nombre del jefe: su usuario sale de su registro en Empleados.
            jefe = self.get_employee_data(name=self.unlist(emp.get('jefe')), get_one=True) if emp.get('jefe') else None
            jefe_id = self.unlist((jefe or {}).get('usuario_id') or (jefe or {}).get('user_id_id'))
            if jefe_id:
                return [int(jefe_id)]
        # Sin jefe directo (o si la política lo dice), los usuarios específicos.
        return [u for u in politica['usuarios'] if u != user_id]

    def _bandeja_db(self, user_id, crear=False):
        nombre = f'clave_{user_id}'
        try:
            return self.lkf_api.couch.set_db(nombre)
        except ResourceNotFound:
            if not crear:
                return None
            self.lkf_api.create_user_couch_db(user_id, nombre)
            return self.lkf_api.couch.set_db(nombre)

    def _solicitar_autorizacion(self, registro, motivo, horas=None, salida=None):
        """Deja (o actualiza) la solicitud en la bandeja de cada quien puede autorizar."""
        usuario = int(self.unlist(registro.get('usuario')))
        politica = self._politica()
        aprobadores = self._aprobadores(usuario, politica)
        empleado = self.get_employee_data(user_id=usuario, get_one=True) or {}
        doc_id = f"extra_{registro.get('folio')}"
        for aprobador in aprobadores:
            db = self._bandeja_db(aprobador, crear=True)
            doc = db.get(doc_id) or {'_id': doc_id}
            doc.update({
                'type': 'autorizacion_extra',
                'inbox': True,
                'status': 'synced',
                'status_user': 'new',
                'autorizacion_status': 'pendiente',
                'created_at': doc.get('created_at') or int(time.time()),
                'record': {
                    'empleado': empleado.get('worker_name') or '',
                    'user_id': usuario,
                    'jornada_folio': registro.get('folio'),
                    'jornada_id': str(registro.get('_id')),
                    'inicio': registro.get('inicio'),
                    'salida_turno': salida.strftime('%H:%M') if salida else None,
                    'motivo': motivo or (doc.get('record') or {}).get('motivo') or '',
                    'horas': horas if horas is not None else (doc.get('record') or {}).get('horas'),
                    'aprobadores': aprobadores,
                },
            })
            db.save(doc)
        return aprobadores
