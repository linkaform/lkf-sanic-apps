# -*- coding: utf-8 -*-

"""
python test_run_script.py '{}' '{"jwt": "jwt ", "account_id": 1868, "docker_image": "linkaform/addons:latest", "name": "test_run_script.py"}'
"""

import sys, simplejson
from produccion_pci_utils import Produccion_PCI

from account_settings import *

class ParticularAction( Produccion_PCI ):
    """docstring for ParticularAction"""
    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

    def review_os_no_liberadas(self):
        print('... ... Revisando Ordenes de Servicio actualizadas pero no liberadas FTTH - METRO ... ...')
        query_pendientes = {
            'answers.f1054000a030000000000012': 'paco',
            'answers.f1054000a030000000000013': 'en_proceso',
            'answers.5f40131c9bca6a32f518d9a9': {'$exists': False}
        }
        records = self.get_records(self.ORDEN_SERVICIO_FIBRA, query_answers=query_pendientes, select_columns=[
            'folio', 
            'answers.f1054000a010000000000005',
            'updated_at',
            'connection_id'
        ])

        c = 0
        group_conexions = {}
        for r in records:
            folio_lib = f"{r['folio']}{r['answers']['f1054000a010000000000005']}"
            record_lib = self.cr.find_one({
                'form_id': self.FORMA_LIBERACION_FIBRA,
                'deleted_at': {'$exists': False},
                'folio': folio_lib
            })
            if not record_lib:
                c += 1
                print(f"---- {c} :: {r['folio']} NO se creo registro de liberacion")
                conexion = r['connection_id']
                group_conexions.setdefault(conexion, []).append(r['folio'])
        print(' ==== ==== ====')
        print(simplejson.dumps(group_conexions, indent=4))

if __name__ == '__main__':
    lkf_obj = ParticularAction(settings, sys_argv=sys.argv)
    lkf_obj.review_os_no_liberadas()