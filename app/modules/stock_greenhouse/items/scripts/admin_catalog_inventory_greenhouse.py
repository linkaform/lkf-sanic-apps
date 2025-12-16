# -*- coding: utf-8 -*-
"""
# Administra el catálogo Inventory, tanto el catálogo como la forma tienen los mismos campos y ids
# Con ello al crear o editar registro en la forma se verá reflejado en el catálogo
"""
import sys, simplejson
from linkaform_api import settings, utils
from account_settings import *

from lkf_addons.stock_greenhouse.stock_utils import Stock


fdict ={
    'folio':'62c44f96dae331e750428732',
    'product_catalog':'61ef32bcdf0ec2ba73dec33c',
    'product_name':'61ef32bcdf0ec2ba73dec33e',
    'warehouse_catalog':'6442e4831198daf81456f273',
    'stock_actuals':'6441d33a153b3521f5b2afc9',

}


# def get_record_catalog( folio ):
#     print('Buscando registro en el catalogo ',folio)
#     mango_query = {"selector":
#         {"answers":
#             {"$and":[
#                 {fdict['folio']: {'$eq': folio}}
#             ]}},
#         "limit":1,
#         "skip":0}
#     res = lkf_api.search_catalog( CATALOG_ID, mango_query, jwt_settings_key='USER_JWT_KEY')
#     return res

# def process_record_to_catalog( current_record ):
#     answers = current_record['answers']
#     # Obtengo los campos de la forma
#     form_fields = lkf_api.get_form_id_fields(current_record['form_id'], jwt_settings_key='USER_JWT_KEY')
#     fields = form_fields[0]['fields']
#     # Obtengo solo los índices que necesito de cada campo
#     info_fields = [{k:n[k] for k in ('label','field_type','field_id','groups_fields','group','options','catalog_fields','catalog') if k in n} for n in fields]
#     for field in info_fields:
#         field_id = field.get('field_id', '')
#         if field.get('field_type', '') == 'catalog-select':
#             catalog_field_id = field.get('catalog', {}).get('catalog_field_id', '')
#             answers[ field_id ] = answers.get(catalog_field_id, {}).get(field_id)

#         elif field.get('field_type', '') == 'catalog-detail':
#             catalog_field_id = field.get('catalog', {}).get('catalog_field_id', '')
#             val_catalog_answers = answers.get(catalog_field_id, {}).get(field_id, [])
#             if val_catalog_answers:
#                 answers[ field_id ] = val_catalog_answers

#     # Obtengo los campos del catalogo
#     catalog_fields = lkf_api.get_catalog_id_fields( CATALOG_ID, jwt_settings_key='USER_JWT_KEY' )
#     info_catalog = catalog_fields.get('catalog', {})
#     fields = info_catalog['fields']
#     #print('fields=',fields)
#     dict_idfield_typefield = { \
#         f.get('field_id'): {\
#             'field_type': f.get('field_type'), \
#             'options': { o.get('value'): o.get('label') for o in f.get('options',[]) }\
#         } for f in fields }

#     #print('dict_idfield_typefield=',dict_idfield_typefield)
#     dict_answers_to_catalog = {}
#     for id_field in dict_idfield_typefield:
#         if id_field in (fdict['product_catalog'], fdict['warehouse_catalog']):
#             continue
#         val_in_record = answers.get( id_field, False )
#         val_in_record_org = val_in_record
#         if val_in_record or val_in_record == 0:
#             info_field_cat = dict_idfield_typefield[ id_field ]
#             if info_field_cat.get('options', False):
#                 val_in_record = info_field_cat['options'].get( val_in_record, None )
#                 if not val_in_record:
#                     if type(val_in_record) != str:
#                         continue
#                     val_in_record_org.replace('_', ' ')
#                     val_in_record_org = val_in_record_org.title()
#                     val_in_record = info_field_cat['options'].get( val_in_record_org, None )
#             elif info_field_cat.get('field_type') == 'catalog-select':
#                 print('si es una lista sacalo de la lista',val_in_record )
#                 if isinstance(val_in_record, list) and val_in_record:
#                     val_in_record = val_in_record[0]
#             dict_answers_to_catalog.update({ id_field: val_in_record })

#     dict_answers_to_catalog.update({
#         '62c44f96dae331e750428732': current_record['folio']
#     })
#     record_catalog = get_record_catalog( current_record['folio'] )
#     catalogo_metadata = lkf_api.get_catalog_metadata(catalog_id=CATALOG_ID)

#     if record_catalog:
#         info_record_catalog = record_catalog[0]

#         if answers.get(fdict['stock_actuals'], 1) <= 0:
#             # Se elimina el registro del catalogo
#             response_delete_catalog = lkf_api.delete_catalog_record(CATALOG_ID, info_record_catalog.pop('_id'), info_record_catalog.pop('_rev'), jwt_settings_key='USER_JWT_KEY')
#             return True

#         info_record_catalog.update(dict_answers_to_catalog)


#         catalogo_metadata.update({'record_id': info_record_catalog.pop('_id'), '_rev': info_record_catalog.pop('_rev'), 'answers': info_record_catalog})
#         response_update_catalog = lkf_api.bulk_patch_catalog([catalogo_metadata,], CATALOG_ID, jwt_settings_key='USER_JWT_KEY')
#     else:
#         catalogo_metadata.update({'answers': dict_answers_to_catalog})
#         res_crea_cat = lkf_api.post_catalog_answers(catalogo_metadata, jwt_settings_key='USER_JWT_KEY')

if __name__ == "__main__":
    # print(sys.argv)
    stock_obj = Stock(settings, sys_argv=sys.argv)
    current_record = stock_obj.current_record
    stock_obj = stock_obj.process_record_to_catalog( current_record )
