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


if __name__ == "__main__":
    print(sys.argv)
    stock_obj = Stock(settings, sys_argv=sys.argv)
    current_record = stock_obj.current_record
    stock_obj = stock_obj.process_record_to_catalog( current_record )
