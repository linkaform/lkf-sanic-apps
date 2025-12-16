# -*- coding: utf-8 -*-
import sys, simplejson
from datetime import datetime, timedelta


from linkaform_api import settings, network, utils

from account_settings import *

from stock_utils import Stock

class Stock(Stock):

    def set_product_catalog(self):
        plant =  self.answers.get(self.SKU_OBJ_ID, {})
        # self.answers[self.SKU_OBJ_ID ] = plant
        # soil_type = self.unlist(plant.get(self.f['reicpe_soil_type'],""))
        # self.answers[self.SKU_OBJ_ID ][self.f['reicpe_soil_type']] = soil_type
        # self.answers[self.SKU_OBJ_ID ][self.f['reicpe_container']] = self.unlist(
        #     self.answers.get(self.SKU_OBJ_ID,{}).get(self.f['reicpe_container'],"")
        #     )
        # self.answers[self.SKU_OBJ_ID ][self.f['product_name']] = self.unlist(
        #     self.answers.get(self.SKU_OBJ_ID,{}).get(self.f['product_name'],"")
        #     )
        # self.answers[self.SKU_OBJ_ID ][self.f['prod_qty_per_container']] = \
        #     [self.answers.get(self.SKU_OBJ_ID,{}).get(self.f['prod_qty_per_container'],""),  ]
        # self.answers[self.SKU_OBJ_ID ][self.f['recipe_type']] = \
        #     [ self.answers.get(self.SKU_OBJ_ID,{}).get(self.f['recipe_type'],""), ]
        # res[self.SKU_OBJ_ID ][self.f['reicpe_soil_type']] = \
        #     self.answers.get(self.SKU_OBJ_ID,{}).get(self.f['reicpe_soil_type'],"")

        created_week = self.answers[self.f['production_cut_week']]
        print('create', created_week)
        cut_year = self.answers[self.f['plant_cut_year']]
        cut_day = self.answers[self.f['production_cut_day']]
        year = str( self.answers.get(self.f['plant_cut_year'], '') ).zfill(2)
        week = str( self.answers.get(self.f['production_cut_week'], '') ).zfill(2)
        plant_group = self.answers[self.f['plant_group']]
        plant_group = self.answers[self.f['plant_group']]

        self.answers[self.f['plant_cut_yearweek']] = f"{cut_year}{week}"
        
        plant_date = datetime.strptime('%04d-%02d-1' % (int(year), int(week)), '%Y-%W-%w')
        if plant.get(self.f['reicpe_growth_weeks']):
            grow_weeks = plant.get(self.f['reicpe_growth_weeks'])
            ready_date = plant_date + timedelta(weeks=grow_weeks)
            self.answers[self.f['product_growth_week']] = grow_weeks
            self.answers[self.f['plant_next_cutweek']] = int(ready_date.strftime('%Y%W'))
        return True


if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    stock_obj.set_product_catalog()
    print('si tiene folio', stock_obj.folio)
    if stock_obj.folio:
        res = stock_obj.make_inventory_flow()
        print('ultimo res', res)
        status_code = res[0].get('status_code')
        update_ok = res[0].get('updatedExisting')
        print('si tiene status_code', status_code)
        #TODO, hace este pedazo atomico, ya que si se crea uno y se actualiza otro es distinto
        if status_code == 201 or update_ok:
            #todo poner sttatus en cada linea
            sys.stdout.write(simplejson.dumps({
                'status': 101,
                'replace_ans': False,
                'metadata':{'editable':False},
                'merge':{
                    'primary': False,
                    'replace': False,
                    'answers': {stock_obj.f['move_status']: 'done'}
                },
            }))
        else:
            try:
                for r in res:
                    if r.get('status_code') not in (200,201):
                        msg_error_app = r.get('json', 'Unkown error on creation, contact support')
            except:
                msg_error_app =  'Unkown error on creation, contact support'
            raise Exception( simplejson.dumps( msg_error_app ) )


# def get_form_fields(lkf_api, form_id=81503):
#     fields_inventory_flow = lkf_api.get_form_id_fields( 81503, jwt_settings_key='USER_JWT_KEY' )
#     if not fields_inventory_flow:
#         return {}
#     else:
#         fields = fields_inventory_flow[0]['fields']

#         # Obtengo solo los índices que necesito de cada campo
#         info_fields = [{k:n[k] for k in ('label','field_type','field_id','groups_fields','group','options','catalog_fields','catalog') if k in n} for n in fields]

#         fields_to_new_record = {}
#         for field in info_fields:
#             if field['field_type'] == 'catalog':
#                 fields_to_new_record[ field['field_id'] ] = field['field_type']
#             if not field.get('catalog'):
#                 fields_to_new_record[ field['field_id'] ] = field['field_type']
#         #print('fields_to_new_record = ',fields_to_new_record)
#     return fields_to_new_record

# def set_up_containers_math(answers, record_qty , new_location, production=False):
#     #Relocate Containers 620ad6247a217dbcb888d17e
#     #qty cont produced 6271dc35e84e2577579eafeb
#     per_container = int(answers['620ad6247a217dbcb888d170'])
#     container_type = answers['620ad6247a217dbcb888d16f']
#     container_on_racks = int(new_location.get('c24000000000000000000001',0)) * container_per_rack[container_type]
#     print('--------------------------')
#     print('container_on_racks',container_on_racks)
#     print('container_on_racks',int(answers.get('c24000000000000000000001',0)))
#     move_qty = new_location['6319404d1b3cefa880fefcc8'] + container_on_racks
#     print('containers alone',new_location['6319404d1b3cefa880fefcc8'])
#     answers.update(new_location)
#     print('per_container',per_container)
#     print('move_qty',move_qty)
#     answers['620ad6247a217dbcb888d171'] = move_qty
#     answers['620ad6247a217dbcb888d172'] = move_qty * per_container
#     print('asi quedan eaches',answers['620ad6247a217dbcb888d172'] )
#     print('-++++++++++++++++++++++++++-',)
#     if production:
#         answers['6271dc35e84e2577579eafeb'] = record_qty # qty produced
#         answers['620ad6247a217dbcb888d17e'] = record_qty - move_qty # Relocated
#     return answers


# def make_inventory_flow(lkf_api, data):
#     ####
#     #### Si la nueva ubicacion de almacen esta dentro de un grupo la saca y llama a la funcion nuevamente
#     ####
#     new_records_data = []
#     fields_to_new_record = get_form_fields(lkf_api)
#     if data['answers'].get('63193fc51b3cefa880fefcc7'):
#         move_group = data['answers'].pop('63193fc51b3cefa880fefcc7')
#         container_type = data['answers'].get('620ad6247a217dbcb888d16f')
#         container_on_racks = sum([int(x['c24000000000000000000001']) for x in move_group]) * container_per_rack[container_type]
#         move_qty = sum([int(x['6319404d1b3cefa880fefcc8']) for x in move_group]) + container_on_racks
#         record_qty =  int(data['answers'].get('620ad6247a217dbcb888d171',0))
#         if record_qty != move_qty:
#             msg_error_app = {
#                 "620ad6247a217dbcb888d171":
#                     {"msg": ["There are {} Containers on the record, but you are trying to alocate {}".format(record_qty, move_qty)],
#                     "label": "Containers on Hand", "error": []}
#             }
#             raise Exception( simplejson.dumps( msg_error_app ) )
#         for location in move_group:
#             if data.get('form_id') == 87499:
#                 production = True
#             else:
#                 production = False
#             print('location........')
#             data['answers'].update(set_up_containers_math(data['answers'], record_qty, location, production=production ))
#             print('data answers', data['answers'])
#             new_records_data.append(create_inventory_flow(lkf_api, data, fields_to_new_record))

#     else:
#         new_records_data = create_inventory_flow(lkf_api, data, fields_to_new_record)
#     print('new_records_data',new_records_data)
#     if new_records_data:
#         res_create = lkf_api.post_forms_answers_list(new_records_data, jwt_settings_key='USER_JWT_KEY')
#         return res_create
#     return False


# def create_inventory_flow(lkf_api, data, fields_to_new_record):
#     #data es un json con answers y folio. Que puede ser el current record
#     if not fields_to_new_record:
#         print('No se pudo obtener los campos de la forma')
#         return False
#     answers_to_new_record = {}
#     for field_id in fields_to_new_record:

#         if data['answers'].get(field_id):
#             answers_to_new_record[ field_id ] = data['answers'][field_id]
#     if answers_to_new_record:
#         answers_to_new_record['620ad6247a217dbcb888d176'] = 'todo' # Post Status
#         answers_to_new_record['62fa97d0c111b295935db5ac'] = answers_to_new_record.get('62fa97d0c111b295935db5ac','growing')
#         metadata = lkf_api.get_metadata(81503)
#         metadata.update({
#             'properties': {
#                 "device_properties":{
#                     "system": "Script",
#                     "process": data.get('process', 'Inventory Move - New Production'),
#                     "action":data.get('action', 'Create record Inventory Flow'),
#                     "from_folio":data.get('folio',''),
#                     "archive":"make_inventory_flow.py"
#                 }
#             },
#             'answers': answers_to_new_record
#         })
#         return metadata
#         # res_create = lkf_api.post_forms_answers(metadata, jwt_settings_key='USER_JWT_KEY')
#         # print('res_create = ',res_create)
#         # status_code =  res_create.get('status_code')
#         # if status_code > 300:
#         #     msg_error_app = res_create.get('json')
#         #     raise Exception( simplejson.dumps( msg_error_app ) )

# if __name__ == '__main__':
#     # print(sys.argv)
#     current_record = simplejson.loads( sys.argv[1] )
#     jwt_complete = simplejson.loads( sys.argv[2] )
#     config['USER_JWT_KEY'] = jwt_complete['jwt'].split(' ')[1]
#     settings.config.update(config)
#     lkf_api = utils.Cache(settings)
#     folio = current_record.get('folio')
#     if folio:
#         res = make_inventory_flow(lkf_api, current_record)
#         print('res=',res)

#         if res:
#             status_code = res[0].get('status_code')
#             if status_code == 201:
#                 #todo poner sttatus en cada linea
#                 sys.stdout.write(simplejson.dumps({
#                     'status': 101,
#                     'replace_ans': False,
#                     'metadata':{'editable':False},
#                     'merge':{
#                         'primary': False,
#                         'replace': False,
#                         'answers': {'62e9d296cf8d5b373b24e028': 'done'}
#                     },
#                 }))
#             else:
#                 try:
#                     for r in res:
#                         if r.get('status_code') not in (200,201):
#                             msg_error_app = r.get('json', 'Unkown error on creation, contact support')
#                 except:
#                     msg_error_app =  'Unkown error on creation, contact support'
#                 raise Exception( simplejson.dumps( msg_error_app ) )
