# -*- coding: utf-8 -*-
import sys, simplejson, math
from datetime import timedelta, datetime

from linkaform_api import settings, network, utils

#from account_utils import get_plant_recipe, select_S4_recipe, get_record_greenhouse_inventory
from account_settings import *

from lab_stock_utils import Stock



class Stock(Stock):

    def set_product_catalog(self):
        self.answers[self.PRODUCT_RECIPE_OBJ_ID ] = self.answers.get(self.PRODUCT_RECIPE_OBJ_ID, {})
        # soil_type = self.unlist(self.answers.get(self.PRODUCT_RECIPE_OBJ_ID,{}).get(self.f['reicpe_soil_type'],""))
        # self.answers[self.PRODUCT_RECIPE_OBJ_ID ][self.f['reicpe_soil_type']] = soil_type

        # self.answers[self.PRODUCT_RECIPE_OBJ_ID ][self.f['prod_qty_per_container']] = \
        #     [self.answers.get(self.PRODUCT_RECIPE_OBJ_ID,{}).get(self.f['prod_qty_per_container'],""),  ]
        # self.answers[self.PRODUCT_RECIPE_OBJ_ID ][self.f['reicpe_container']] = \
        #     [ self.answers.get(self.PRODUCT_RECIPE_OBJ_ID,{}).get(self.f['reicpe_container'],""), ]
        # self.answers[self.PRODUCT_RECIPE_OBJ_ID ][self.f['recipe_type']] = \
        #     [ self.answers.get(self.PRODUCT_RECIPE_OBJ_ID,{}).get(self.f['recipe_type'],""), ]
        # res[self.PRODUCT_RECIPE_OBJ_ID ][self.f['reicpe_soil_type']] = \
        #     self.answers.get(self.PRODUCT_RECIPE_OBJ_ID,{}).get(self.f['reicpe_soil_type'],"")
        return True

if __name__ == '__main__':
    stock_obj = Stock(settings, sys_argv=sys.argv)
    #stock_obj.set_product_catalog()
    stock_obj.console_run()
    prod_status = stock_obj.answers.get(stock_obj.f['production_left_overs'],'')
    # ------------------------------------------------------------------------------
    stock_obj.calculates_production_warehouse()



    print('prod_status', prod_status)
    print('asi regresan...', stock_obj.answers)
    if prod_status == 'finished':
        #adjust_inventory_flow(worked_containers)
        #create_move_line(current_record, move_inventory)
        stock_obj.answers[stock_obj.f['production_order_status']] = 'done'
        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans': stock_obj.answers,
        }))
    else:
        stock_obj.answers[stock_obj.f['production_order_status']] = 'in_progress'
        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans': stock_obj.answers
        }))
