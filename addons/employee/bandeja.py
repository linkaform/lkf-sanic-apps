# -*- coding: utf-8 -*-
"""Bandeja (inbox) del usuario para web.

Es la misma bandeja que usa la app: la base de CouchDB `clave_{user_id}`, con
los documentos que tienen `inbox: true`. La lee el servidor (con sus
credenciales de Couch) para no poner en el navegador cómo entrar a Couch.

Lo que solo se puede hacer en la app (un rondín) se muestra de solo lectura,
para que la persona sepa que lo tiene pendiente.
"""

from datetime import datetime

from couchdb.http import ResourceNotFound

from .checkin import Presencia

DATE_FMT = '%Y-%m-%d %H:%M:%S'

# Tipos de documento de la bandeja y si se resuelven en web.
TIPOS = {
    'rondin': {'label': 'Rondín', 'solo_app': True},
    'autorizacion_acceso': {'label': 'Autorización de acceso', 'solo_app': False},
    'autorizacion_extra': {'label': 'Horas extra por autorizar', 'solo_app': False},
}
ORDEN_ESTADO = {'in_progress': 0, 'paused': 1, 'new': 2}


class Bandeja(Presencia):

    def get_bandeja(self):
        user_id = self.user.get('user_id')
        try:
            db = self.lkf_api.couch.set_db(f'clave_{user_id}')
        except ResourceNotFound:
            # Todavía no se le ha asignado nada: no hay base.
            return {'items': [], 'total': 0, 'pendientes': 0}
        docs = db.find({'selector': {'inbox': True}, 'limit': 500})
        items = [self._item(d) for d in docs if d.get('type') in TIPOS]
        items.sort(key=lambda i: (ORDEN_ESTADO.get(i['estado'], 9), i['fecha'] or ''))
        pendientes = sum(1 for i in items if i['estado'] in ORDEN_ESTADO)
        return {'items': items, 'total': len(items), 'pendientes': pendientes}

    def _item(self, doc):
        tipo = doc.get('type')
        record = doc.get('record') or {}
        item = {
            'id': doc.get('_id'),
            'tipo': tipo,
            'tipo_label': TIPOS[tipo]['label'],
            'solo_app': TIPOS[tipo]['solo_app'],
            'folio': doc.get('folio'),
            'estado': doc.get('status_user') or 'new',
            'fecha': None,
            'titulo': '',
            'detalle': '',
        }
        if tipo == 'rondin':
            checks = record.get('check_areas') or []
            item.update({
                'titulo': record.get('nombre_rondin') or 'Rondín',
                'detalle': record.get('ubicacion_rondin') or '',
                'fecha': record.get('fecha_programada') or self._epoch(doc.get('created_at')),
                'progreso': {'hechos': sum(1 for c in checks if c.get('checked')), 'total': len(checks)},
                'duracion_estimada': record.get('duracion_estimada'),
            })
        elif tipo == 'autorizacion_acceso':
            item.update({
                'titulo': record.get('visitante_nombre') or 'Autorización de acceso',
                'detalle': record.get('ubicacion') or record.get('visitante_motivo') or '',
                'fecha': self._epoch(doc.get('created_at')) or doc.get('updated_at'),
                'autorizacion_status': doc.get('autorizacion_status') or record.get('autorizacion_status'),
            })
        elif tipo == 'autorizacion_extra':
            horas = record.get('horas')
            item.update({
                'titulo': record.get('empleado') or 'Horas extra',
                'detalle': ' · '.join(x for x in (
                    record.get('motivo'),
                    f"salida {record['salida_turno']}" if record.get('salida_turno') else None,
                    f'{horas} h' if horas is not None else 'en curso',
                ) if x),
                'fecha': record.get('inicio') or self._epoch(doc.get('created_at')),
                'autorizacion_status': doc.get('autorizacion_status'),
                'horas': horas,
                'motivo': record.get('motivo'),
                'jornada_folio': record.get('jornada_folio'),
            })
        return item

    def resolver(self, id, decision, comentario=None):
        """Aprueba o rechaza una solicitud de su propia bandeja."""
        if decision not in ('aprobada', 'rechazada'):
            self.LKFException({'title': 'Decisión inválida', 'msg': 'La decisión debe ser aprobada o rechazada.'})
        user_id = self.user.get('user_id')
        db = self._bandeja_db(user_id)
        doc = db.get(id) if db else None
        if not doc or doc.get('type') != 'autorizacion_extra':
            self.LKFException({'title': 'No encontrada', 'msg': 'Esa solicitud no está en tu bandeja.'})
        if doc.get('autorizacion_status') in ('aprobada', 'rechazada'):
            self.LKFException({'title': 'Ya resuelta', 'msg': 'Esta solicitud ya se resolvió.'})
        record = doc.get('record') or {}
        tz = self._user_tz(user_id)
        ahora = self._now(tz).strftime(DATE_FMT)
        nombre = (self.get_employee_data(user_id=user_id, get_one=True) or {}).get('worker_name') or self.user.get('name', '')
        f = self.asistencia_fields
        answers = {
            f['autorizacion_extra']: decision,
            f['autorizo_extra']: nombre,
            f['fecha_autorizacion']: ahora,
        }
        if comentario:
            answers[f['comentario_autorizacion']] = comentario
        res = self.lkf_api.patch_multi_record(answers=answers, form_id=self.REGISTRO_ASISTENCIA,
                                              record_id=[record.get('jornada_id')])
        if res.get('status_code') not in (200, 201, 202):
            self.LKFException({'title': 'Error al resolver', 'msg': res.get('json', res)})
        # Sale de la bandeja de todos los que podían autorizarla.
        for aprobador in record.get('aprobadores') or [user_id]:
            otra = self._bandeja_db(aprobador)
            copia = otra.get(id) if otra else None
            if not copia:
                continue
            copia.update({'inbox': False, 'status_user': 'completed', 'autorizacion_status': decision,
                          'resuelto_por': nombre, 'fecha_resolucion': ahora, 'comentario': comentario or ''})
            otra.save(copia)
        return {'id': id, 'autorizacion_status': decision}

    def _epoch(self, value):
        try:
            return datetime.fromtimestamp(float(value)).strftime('%Y-%m-%d %H:%M:%S')
        except (TypeError, ValueError):
            return None
