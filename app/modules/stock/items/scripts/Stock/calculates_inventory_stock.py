# -*- coding: utf-8 -*-
import sys, simplejson, math
from datetime import timedelta, datetime
from bson import ObjectId

from stock_utils import Stock

from account_settings import *


class Stock(Stock):

    def get_product_info(self, **kwargs):
        #REVISAR SI ESTO NO SE DEBE DE BORRAR DE MASTER
        try:
            product_code, sku, lot_number, warehouse, location = self.get_product_lot_location()
            # warehouse = self.answers[self.WAREHOUSE_LOCATION_OBJ_ID][self.f['warehouse']]
            # location = self.answers[self.WAREHOUSE_LOCATION_OBJ_ID][self.f['warehouse_location']]
            # product_code = self.answers.get(self.f['product_recipe'], {}).get(self.f['product_code'], '')
        except Exception as e:
            print('**********************************************')
            self.LKFException('Warehosue and product code are requierd', e)
        a = f'{product_code}_{sku}_{lot_number}_{warehouse}_{location}'
        values = {
                '_id': a
                }
        ccache = self.cache_read(values)
        product_stock = self.get_product_stock(product_code, sku=sku, lot_number=lot_number, warehouse=warehouse, location=location, kwargs=kwargs.get('kwargs',{}) )
        per_container = self.answers.get(self.f['per_container'],1)
        self.answers[self.f['product_lot_produced']] = product_stock['production']
        self.answers[self.f['product_lot_move_in']] = product_stock['move_in']
        self.answers[self.f['product_lot_scrapped']] = product_stock['scrapped']
        self.answers[self.f['product_lot_move_out']] = product_stock['move_out']
        self.answers[self.f['product_lot_sales']] = product_stock['sales']
        self.answers[self.f['product_lot_cuarentin']] = product_stock['cuarentin']
        self.answers[self.f['product_lot_actuals']] = product_stock['actuals'] 
        self.answers[self.f['actual_eaches_on_hand']] = product_stock['actuals'] * per_container
        self.answers[self.f['product_lot_adjustments']] = product_stock['adjustments']

        if self.answers[self.f['product_lot_actuals']] <= 0:
            self.answers[self.f['inventory_status']] = 'done'
        else:
            self.answers[self.f['inventory_status']] = 'active'

        wh_type = self.WH.warehouse_type(warehouse)
        if wh_type.lower() not in  ('stock'):
            self.answers[self.f['inventory_status']] = 'done'
        # self.answers.update({self.f['inv_group']:self.get_grading()})
        return self.answers

if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    #stock_obj.merge_stock_records()

    # if folio:
    #     #si ya existe el registro, no cambio el numero de lote
    #     kwargs['force_lote'] = True
    # print('answers = ', stock_obj.answers)
    stock_obj.get_product_info()
    query = None
    if stock_obj.record_id:
        query = {'_id':ObjectId(stock_obj.record_id)}
    if not query and stock_obj.folio:
        query = {'folio':stock_obj.folio, 'form_id':stock_obj.form_id }
    if query:
        print('no sera aqui..?????')
        stock_obj.cr.update_one(query, {'$set': {'answers':stock_obj.answers}})
    print('print va a hacer el update con...', stock_obj.answers)
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': stock_obj.answers
    }))
