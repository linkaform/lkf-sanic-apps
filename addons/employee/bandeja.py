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

from .app import Employee

# Tipos de documento de la bandeja y si se resuelven en web.
TIPOS = {
    'rondin': {'label': 'Rondín', 'solo_app': True},
    'autorizacion_acceso': {'label': 'Autorización de acceso', 'solo_app': False},
}
ORDEN_ESTADO = {'in_progress': 0, 'paused': 1, 'new': 2}


class Bandeja(Employee):

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
        return item

    def _epoch(self, value):
        try:
            return datetime.fromtimestamp(float(value)).strftime('%Y-%m-%d %H:%M:%S')
        except (TypeError, ValueError):
            return None
