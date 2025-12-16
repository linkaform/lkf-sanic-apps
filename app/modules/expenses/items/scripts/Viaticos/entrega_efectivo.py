# -*- coding: utf-8 -*-
import sys, simplejson
from datetime import datetime
from copy import deepcopy

from expense_utils import Expenses

from account_settings import *


if __name__ == '__main__':
    expense_obj = Expenses(settings, sys_argv=sys.argv)
    expense_obj.console_run()
    current_record = expense_obj.current_record
    info_catalog = current_record['answers'].get(expense_obj.CATALOG_SOL_VIAJE_OBJ_ID, {})
    folio = info_catalog.get(expense_obj.f['cat_folio'], '')
    print('folio=', folio)
    update_ok = expense_obj.update_solicitud(folio, current_record['answers'])

    if not update_ok:
        msg_error_app = {
            "610419b5d28657c73e36fcd3":{"msg": ["Error al actualizar la solicitud"], "label": "Numero de Solicitud", "error":[]},
        }
        raise Exception(simplejson.dumps(msg_error_app))