# -*- coding: utf-8 -*-
import sys, simplejson, threading, concurrent.futures, time

from linkaform_api import settings
from lab_stock_utils import Stock

from account_settings import *


class Stock(Stock):


    def thread_function(self, rec, answers):
        folios = [rec['folio'],]
        print('folios',folios)
        res = stock_obj.update_stock(answers=answers, form_id=inv_query['form_id'], folios=folios )
        print('res',res)


    def update_adjustment(self):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.ADJUIST_FORM_ID,
            f"answers.{self.f['grading_date']}":{"$gte":"2024-03-07"}
            }
        metadata = self.lkf_api.get_metadata(form_id=self.ADJUIST_FORM_ID, user_id=9908 )

        records  = self.cr.find(match_query, {'folio':1, 'answers':1})
        for rec in records:
            print('rec', rec)

            rec["answers"][self.f['inv_adjust_status']] = "todo"
            group = rec["answers"][self.f['grading_group']]
            for product in group:
                product[self.f['inv_adjust_grp_in']] = 0
                product[self.f['inv_adjust_grp_out']] = 0

            print('answers', rec["answers"])
            print('folio', rec['folio'])

            metadata['answers'] = rec["answers"]
            res = self.lkf_api.patch_record(metadata, record_id=rec['_id'])
            print('folio', res)
        # folios = [rec['folio'] for rec in records]
        # print('folios',folios)
        # print('len folios',len(folios))
        # print('hola.....',len(folios))
        # # folios = ['135695-9908',]
        # answers = rec["answers"]


    def update_new_lot(self):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.MOVE_NEW_PRODUCTION_ID,
            # "folio":'39955397-9908'
            }
        metadata = self.lkf_api.get_metadata(form_id=self.MOVE_NEW_PRODUCTION_ID, user_id=9908 )
        records  = self.cr.find(match_query, {'folio':1, 'answers':1})
        for rec in records:
            rec["answers"][self.f['move_status']] = "to_do"
            metadata['answers'] = rec["answers"]
            res = self.lkf_api.patch_record(metadata, record_id=rec['_id'])


    def get_all_inventory_records(self):
        inv_query = self.get_stock_query({})
        records  = self.cr.find(inv_query, {'folio':1})
        answers = {"644c36f1d20db114694a495a":"grading_pending"}
        for rec in records:
            folios = [rec['folio'],]
            print('folios',folios)
            res = stock_obj.update_stock(answers=answers, form_id=inv_query['form_id'], folios=folios )
        # with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        #     executor.map(lambda rec: self.thread_function(rec, answers), records)
            

if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    start_time = time.time()
    data = stock_obj.data
    print('data=',data)
    update_type = data.get('update_type', 'stock')
    print('update_type', update_type)
    form_id = None
    answers = None
    if data.get('form_id'):
        stock_obj.form_id = data['form_id']
    if data.get('answers'):
        stock_obj.answers = data['answers']
    if data.get('update_type'):
        update_type  = data['update_type']
    if update_type == 'stock':
        stock_obj.get_all_inventory_records()
    elif update_type == 'adjustment':
        stock_obj.update_adjustment()
    elif update_type == 'prod':
        stock_obj.update_new_lot()
    end_time = time.time()
    duration = end_time - start_time
    print(f'se tardo {duration} sengundos ')
    print(f'se tardo {duration/60} minutos ')