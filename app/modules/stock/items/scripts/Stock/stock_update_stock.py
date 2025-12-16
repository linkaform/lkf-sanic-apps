# -*- coding: utf-8 -*-
import sys, simplejson

from stock_utils import Stock

from account_settings import *


if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    product_info = stock_obj.answers.get(stock_obj.CATALOG_INVENTORY_OBJ_ID,{})
    folio_inventory = product_info.get(stock_obj.f['cat_stock_folio'])
    print('folio_inventory', folio_inventory)
    print('DEPRICATEDD')
    print('TODO BORRAR')
    #stock_obj.update_stock(answers={}, form_id=stock_obj.FORM_INVENTORY_ID, folios=folio_inventory)
