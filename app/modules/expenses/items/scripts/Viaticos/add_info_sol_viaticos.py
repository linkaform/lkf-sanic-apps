# -*- coding: utf-8 -*-
import sys, simplejson
from expense_utils import Expenses
from account_settings import *

def add_info_catalog_sol_gts():
    mango_query = {
        'selector': {
            'answers': {
                '$and': [
                    {expense_obj.f['cat_folio']: {'$eq': current_record['folio']}}
                ]
            }
        },
        'limit': 1,
        'skip': 0
    }
    print('... catalog id solicitudes de gasto =',expense_obj.CATALOG_SOL_VIAJE_ID)
    print('... catalog field id solicitudes de gasto =',expense_obj.CATALOG_SOL_VIAJE_OBJ_ID)
    print('... ... mango_query =',mango_query)
    record_solicitud = expense_obj.lkf_api.search_catalog(expense_obj.CATALOG_SOL_VIAJE_ID, mango_query)
    print('++++++ record_solicitud =',record_solicitud)
    print('expense_obj =',expense_obj)
    dict_sol_gts = {}
    for r in record_solicitud:
        dict_sol_gts[ expense_obj.f['cat_destinos'] ] = r[ expense_obj.f['cat_destinos'] ]
        dict_sol_gts[ expense_obj.f['cat_folio'] ] = r[ expense_obj.f['cat_folio'] ]
        dict_sol_gts[ expense_obj.f['fecha_salida'] ] = [r[ expense_obj.f['fecha_salida'] ],]
        dict_sol_gts[ expense_obj.f['fecha_regreso'] ] = [r[ expense_obj.f['fecha_regreso'] ],]
        dict_sol_gts[ expense_obj.f['cat_monto_total_aprobado'] ] = [r[ expense_obj.f['cat_monto_total_aprobado'] ],]
    if dict_sol_gts:
        current_record['answers'][ expense_obj.CATALOG_SOL_VIAJE_OBJ_ID ] = dict_sol_gts # No se debe hard codear!!!
        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans': current_record['answers']
        }))

if __name__ == '__main__':
    expense_obj = Expenses(settings, sys_argv=sys.argv, use_api=True)
    # expense_obj.console_run()
    current_record = expense_obj.current_record
    #print('+++++ current_record =',current_record)
    if current_record.get('folio'):
        add_info_catalog_sol_gts()