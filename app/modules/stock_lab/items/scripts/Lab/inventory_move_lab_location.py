# -*- coding: utf-8 -*-
import sys, simplejson

from lab_stock_utils import Stock

from account_settings import *


if __name__ == '__main__':
    # print('enra invmove=', sys.argv)
    # print(f"python { sys.argv[0].split('/')[-1]} '{ sys.argv[1]}' '{ sys.argv[2]}'")
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    if not stock_obj.record_id:
        stock_obj.record_id = stock_obj.object_id()
        print('NOOOOT ,....stock_obj record_id', stock_obj.record_id)
    current_record = stock_obj.current_record
    folio = stock_obj.folio
    # print('current_record',current_record)
    #kwargs = current_record.get('kwargs', current_record.get('properties',{}).get('kwargs', {}))

    dest_folio = stock_obj.move_location()
    stock_obj.answers[stock_obj.f['inv_adjust_status']] =  'done'
    print('grupo', stock_obj.answers[stock_obj.f['move_group']])
    for idx, gset in enumerate(stock_obj.answers[stock_obj.f['move_group']]):
        print('idx', idx)
        print('gset', gset)
        gset[stock_obj.f['move_dest_folio']] =  dest_folio[idx]
    # sys.stdout.write(simplejson.dumps({
    #     'status': 206,
    #     'metadata':{'editable':False},
    #     'replace_ans': current_record['answers'],
    #     }))
    # sys.stdout.write(simplejson.dumps({
    #     'status': 206,
    #     # 'metadata':{'editable':False},
    #     'merge': {
    #         'answers': current_record['answers']},
    #     }))
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans':  stock_obj.answers,
        'metadata':{"id":stock_obj.record_id}

    }))
