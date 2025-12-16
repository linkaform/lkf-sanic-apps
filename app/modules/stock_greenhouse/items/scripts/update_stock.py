# -*- coding: utf-8 -*-
import sys, simplejson

from lkf_addons.stock_greenhouse.stock_utils import Stock
from account_settings import *


if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    current_record = stock_obj.current_record
    current_answers = current_record.get('answers',{})
    plant_info = current_answers.get(stock_obj.CATALOG_INVENTORY_OBJ_ID,{})
    folio_inventory = plant_info.get(stock_obj.f['cat_stock_folio'])
    product_code = plant_info.get(stock_obj.f['product_code'])
    warehouse = plant_info.get(stock_obj.f['warehouse'])
    product_lot = plant_info.get(stock_obj.f['product_lot'])
    move_dest_folio = current_answers.get(stock_obj.f['move_dest_folio'])
    stock_obj.update_calc_fields(product_code, warehouse, product_lot, folio=folio_inventory)
    if move_dest_folio:
        move_new_location = current_answers.get(stock_obj.f['move_new_location'])
        dest_warehouse = move_new_location.replace('_',' ').title()
        stock_obj.update_calc_fields(product_code, dest_warehouse, product_lot, folio=move_dest_folio)

    #print(sto)
    #a = stock_obj.lkf_api.patch_multi_record({stock_obj.f['inventory_status']:'active'}, stock_obj.FORM_INVENTORY_ID, folios=[folio_inventory])
