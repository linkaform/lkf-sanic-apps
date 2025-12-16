#   dependencies
import sys
from account_settings import *
from linkaform_api import settings
from lkf_addons.jit.app import JIT
from lkf_addons.stock.app import Stock


def get_first_element(warehouse, data):
    
    stock_obj = Stock(settings, sys_argv=sys.argv)
    match_query = {
        "form_id": stock_obj.ADJUIST_FORM_ID,
        "deleted_at":{"$exists":False},
        "warehouse_name": "test"
    }
    
    if wharehouse!='':
        wh = match_query.get({'answers.66dfc4de6b95c11a3b58720f.6442e4831198daf81456f274'})
        print(wh)
    # data = [x for x in data]
    
    # for item in data:
    #     warehouse = item.get('warehouse_name', '')
        #print(warehouse)



if __name__ == "__main__":
    jit_obj = JIT(settings, sys_argv=sys.argv)
    
    jit_obj.console_run()
    data = jit_obj.data
    wharehouse = data.get('wharehouse', '')
    #print('data = ', data)
    get_first_element(wharehouse, data)