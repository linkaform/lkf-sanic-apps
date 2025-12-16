# -*- coding: utf-8 -*-
import sys, simplejson
from linkaform_api import settings, network, utils
from magnolia_settings import *
from account_utils import unlist, get_inventory_flow

def get_answer_catalog_field( answer_field ):
    if type(answer_field) == list and answer_field:
        return answer_field[0]
    return answer_field


def move_location(current_record):
    current_answers = current_record['answers']
    form_id =  current_record.get('form_id')
    if form_id == 96071:
        move_type = 'pull'
        move_lines = current_answers['63f8e128694361f17f7b59d5']
    else:
        move_lines = current_answers['6310c609bbb3788e5f7ffa46']
        move_type = current_answers['62e9cecfa7d81a71e4b4e6da']

    # Información original del Inventory Flow
    status_code = 0
    for moves in move_lines:
        print('move........')
        info_plant = moves.get('61ef419c91bb38dcfedec3cb', {})
        plant_code = get_answer_catalog_field( info_plant.get('61ef32bcdf0ec2ba73dec33d', 0) )
        per_container = get_answer_catalog_field( info_plant.get('620ad6247a217dbcb888d170', 0) )
        folio_plant = get_answer_catalog_field( info_plant.get('62c44f96dae331e750428732') )
        if not folio_plant:
            continue
        # Información que modifica el usuario
        containers_out = moves.get('62e9cc6b36cb6821c274eb9c', 0)
        print('containers_out=', containers_out)
        record_inventory_flow = get_inventory_flow(folio_plant)
        # Consulto el Inventory Flow del registro
        # print('folio_plant',folio_plant)
        # print('folio_plant',record_inventory_flow)
        answers = record_inventory_flow.get('answers')
        qty_produced = abs(answers.get('6271dc35e84e2577579eafeb', 0))
        relocated_containers = abs(answers.get('620ad6247a217dbcb888d17e', 0))
        discard_containers = abs(answers.get('620ad6247a217dbcb888d16d', 0))
        shipped_containers = abs(answers.get('620ad6247a217dbcb888d16e', 0))
        actual_containers_on_hand = int(  answers.get('620ad6247a217dbcb888d171', 0))
        new_actual_containers_on_hand = actual_containers_on_hand - containers_out
        # print('plant_code', plant_code)
        # print('per_container', per_container)
        # print('folio_plant', folio_plant)
        # print('containers_out', containers_out)
        # print('discard_containers', discard_containers)
        # print('shipped_containers', shipped_containers)
        # print('actual_containers_on_hand', actual_containers_on_hand)
        # print('new_actual_containers_on_hand', new_actual_containers_on_hand)

        if move_type =='scrap':
            discard_containers = discard_containers + containers_out
        elif move_type == 'pull':
            shipped_containers = shipped_containers + containers_out
        elif move_type == 'sell':
            shipped_containers = shipped_containers + containers_out

        if not per_container:
            per_container = answers.get('620ad6247a217dbcb888d170', 0)

        record_inventory_flow['answers'].update({
            '620ad6247a217dbcb888d17e' : relocated_containers,
            '620ad6247a217dbcb888d16d' : discard_containers,
            '620ad6247a217dbcb888d16e' : shipped_containers,
            '620ad6247a217dbcb888d171': new_actual_containers_on_hand, # Actual Containers on hand
            '620ad6247a217dbcb888d172': int(per_container) * int(new_actual_containers_on_hand) # Actual Eaches on Hand
        })

        if new_actual_containers_on_hand <= 0:
            record_inventory_flow['answers'].update({
                '620ad6247a217dbcb888d175': 'done'
            })

        record_inventory_flow.update({
            'properties': {
                "device_properties":{
                    "system": "SCRIPT",
                    "process":"Inventory Move - Out",
                    "accion":'Update record Inventory Flow',
                    "archive":"inventory_move_scrap.py"
                }
            }
        })
        print('record_inventory_flow',record_inventory_flow['answers'])
        # Se actualiza el Inventory Flow que está seleccionado en el campo del current record
        res_update_inventory = lkf_api.patch_record( record_inventory_flow, jwt_settings_key='USER_JWT_KEY' )
        print('res_update_inventory =',res_update_inventory)
        if res_update_inventory.get('status_code',0) > status_code:
            status_code = res_update_inventory['status_code']
    return status_code

if __name__ == '__main__':
    print(sys.argv)
    current_record = simplejson.loads( sys.argv[1] )
    jwt_complete = simplejson.loads( sys.argv[2] )
    config['USER_JWT_KEY'] = jwt_complete['jwt'].split(' ')[1]
    settings.config.update(config)
    lkf_api = utils.Cache(settings)
    net = network.Network(settings)
    cr = net.get_collections()
    status_code = move_location(current_record)
    current_record['answers']['62e9d296cf8d5b373b24e028'] =  'done'
    if status_code == 202:
        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans': current_record['answers'],
            }))
    else:
        msg = "One or more of the moves were not executed correctly"
        msg_error_app = {
                "63f8e128694361f17f7b59d5": {
                    "msg": [msg],
                    "label": "Please check stock moves",
                    "error":[]

                }
            }
        raise Exception( simplejson.dumps( msg_error_app ) )
