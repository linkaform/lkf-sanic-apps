# -*- coding: utf-8 -*-
import sys, simplejson

from lab_stock_utils import Stock

from account_settings import *

if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    stock_obj.console_run()
    record_catalog = stock_obj.get_record_catalog_del()
    print('catalog record to delete', record_catalog)
    stock_obj.del_catalog_record(record_catalog, stock_obj.form_id)
    #doing cleanup
    #for done records that for some reason are not deleted
    # record_catalog = get_record_catalog(form_id)
    # del_catalog_record(record_catalog)

