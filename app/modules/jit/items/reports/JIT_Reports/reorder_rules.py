# -*- coding: utf-8 -*-
import sys, simplejson, math
import json
import math
from datetime import timedelta, datetime

from linkaform_api import settings, base
from account_settings import *

print('inicia....')
from jit_report import Reports
from lkf_addons.product.app import Product
from lkf_addons.product.app import Warehouse
from lkf_addons.jit.app import JIT
from lkf_addons.stock.app import Stock
from itertools import zip_longest

def gett_product_by_type(product_type, product_line=""):
    product_field = None
    # Base query with both product_type and product_line (if not empty)
    mango_query = {
        "selector": {
            "$and": [
                {"answers." + prod_obj.f['product_type']: {"$eq": product_type}},
                # Only add the product_line filter if it's not empty
                {"answers." + prod_obj.f['product_category']: {"$eq": product_line}} if product_line else {}
            ]
        },
        "limit": 10000,
        "skip": 0
    }
    
    # Clean up any empty $and conditions if product_line was empty
    mango_query["selector"]["$and"] = [clause for clause in mango_query["selector"]["$and"] if clause]

    # Execute query and return records
    record = prod_obj._labels_list(prod_obj.lkf_api.search_catalog(prod_obj.PRODUCT_ID, mango_query), prod_obj.f)
    return record

def gett_products_inventory(product_code, warehouse, location=None, status='active'):

        match_query ={ 
         'form_id': 123133,  
         'deleted_at' : {'$exists':False},
         } 

        if product_code:
            if type(product_code) == list:
                match_query.update({f"answers.{prod_obj.SKU_OBJ_ID}.{prod_obj.f['product_code']}":{"$in":product_code}})
            else:
                match_query.update({f"answers.{prod_obj.SKU_OBJ_ID}.{prod_obj.f['product_code']}":product_code})
                
        if warehouse:
            if type(warehouse) == list:                
                match_query.update({f"answers.{warehouse_obj.WAREHOUSE_LOCATION_OBJ_ID}.{warehouse_obj.f['warehouse']}":{"$in":warehouse}})
            else:
                match_query.update({f"answers.{warehouse_obj.WAREHOUSE_LOCATION_OBJ_ID}.{warehouse_obj.f['warehouse']}":warehouse})
        if location:
            if type(location) == list:                
                match_query.update({f"answers.{warehouse_obj.WAREHOUSE_LOCATION_OBJ_ID}.{warehouse_obj.f['warehouse_location']}":{"$in":location}})
            else:
                match_query.update({f"answers.{warehouse_obj.WAREHOUSE_LOCATION_OBJ_ID}.{warehouse_obj.f['warehouse_location']}":location})
        query = [
            {'$match': match_query},
            {'$project':{
                '_id':0,
                'product_code':f"$answers.{prod_obj.SKU_OBJ_ID}.{prod_obj.f['product_code']}",
                'warehouse':f"$answers.{warehouse_obj.WAREHOUSE_LOCATION_OBJ_ID}.{warehouse_obj.f['warehouse']}",
                'actuals':f"$answers.{stock_obj.f['actual_eaches_on_hand']}",
            }},
            {'$group':{
                '_id':{
                    'product_code':'$product_code',
                    'warehouse':'$warehouse'
                },
                'actuals':{'$sum':'$actuals'}
            }},
            {"$project":{
                "_id":0,
                "product_code":"$_id.product_code",
                "warehouse":"$_id.warehouse",
                "actuals": "$actuals",
            }},
        ]
        
        #print('query=',simplejson.dumps(query, indent=5))
        res = script_obj.format_cr(script_obj.cr.aggregate(query))
        return res


def get_report_filters(filters=[], product_code_aux=None):
    mango_query = {
        "selector": {
            "_id": {"$gt": None}
        },
        "limit": 10000,
        "skip": 0
    }

    if 'inventory' in filters:
        if product_code_aux:
            mango_query['selector'] = {f"answers.{prod_obj.f['product_type']}": product_code_aux}

        res = prod_obj.lkf_api.search_catalog(123105, mango_query)

        product_categories = []

        for item in res:
            category = item.get(prod_obj.f['product_category'])
            if category and category not in product_categories:
                product_categories.append(category)

    return product_categories

def get_procurments(warehouse=None, location=None, product_code=None, sku=None, status='programmed', group_by=False):
    match_query ={ 
            'form_id': procurment_obj.PROCURMENT,  
            'deleted_at' : {'$exists':False},
            f'answers.{procurment_obj.mf["procurment_status"]}': status,
        }
    if product_code:
        match_query.update({
            f"answers.{procurment_obj.SKU_OBJ_ID}.{procurment_obj.f['product_code']}": {'$in': product_code}
            })
    if sku:
        match_query.update({
            f"answers.{procurment_obj.SKU_OBJ_ID}.{procurment_obj.f['sku']}":sku
            })
    if warehouse:
        match_query.update({
            f"answers.{procurment_obj.WH.WAREHOUSE_LOCATION_OBJ_ID}.{procurment_obj.WH.f['warehouse']}":warehouse
            })
    if location:
        match_query.update({
            f"answers.{procurment_obj.WH.WAREHOUSE_LOCATION_OBJ_ID}.{procurment_obj.WH.f['warehouse_location']}":location
            })
    query = [
        {'$match': match_query},
        {'$project':{
                '_id':0,
                'date':f'$answers.{procurment_obj.mf["procurment_date"]}',
                'date_schedule':f'$answers.{procurment_obj.mf["procurment_schedule_date"]}',
                'procurment_method':f'$answers.{procurment_obj.mf["procurment_method"]}',
                'procurment_qty':f'$answers.{procurment_obj.mf["procurment_qty"]}',
                'product_code':f'$answers.{procurment_obj.SKU_OBJ_ID}.{procurment_obj.f["product_code"]}',
                'sku':f'$answers.{procurment_obj.SKU_OBJ_ID}.{procurment_obj.f["sku"]}',
                'uom':f'$answers.{procurment_obj.UOM_OBJ_ID}.{procurment_obj.f["uom"]}',
                'warehouse':f'$answers.{procurment_obj.WH.WAREHOUSE_LOCATION_OBJ_ID}.{procurment_obj.WH.f["warehouse"]}',
                'warehouse_location':f'$answers.{procurment_obj.WH.WAREHOUSE_LOCATION_OBJ_ID}.{procurment_obj.WH.f["warehouse_location"]}',
        }}]
    return procurment_obj.format_cr(procurment_obj.cr.aggregate(query))

def get_product(product_code):
    return get_product_field(product_code, pfield='*')

def get_product_field(product_code, pfield='product_family'):
    product_field = None
    mango_query = {
        "selector": {
            "answers": {
                '61ef32bcdf0ec2ba73dec33d': {"$eq": product_code},
                } ,
            },
        "limit": 1,
        "skip": 0
            }
    record = prod_obj.lkf_api.search_catalog(prod_obj.PRODUCT_ID, mango_query)
    if record and len(record) > 0:
        rec = record[0]
        if pfield == '*':
            return rec
        product_field = rec.get(prod_obj.f[pfield])
    return product_field

def format_catalog_product(data_query, id_field):
    list_response = []
    for item in data_query:
        wharehouse = item.get(id_field,'')
        if wharehouse not in list_response and wharehouse !='':
            list_response.append(wharehouse)

    list_response.sort()
    return list_response
        
def get_catalog_product_field(id_field):
    match_query = { 
        'deleted_at':{"$exists":False},
    }

    mango_query = {"selector":
        {"answers":
            {"$and":[match_query]}
        },
        "limit":10000,
        "skip":0
    }
    res = script_obj.lkf_api.search_catalog( 123105, mango_query)
    res_format = format_catalog_product(res, id_field)
    return res_format


if __name__ == "__main__":
    script_obj = base.LKF_Base(settings, sys_argv=sys.argv, use_api=True)
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    prod_obj = Product(settings, sys_argv=sys.argv, use_api=True)
    stock_obj = Stock(settings, sys_argv=sys.argv, use_api=True)
    procurment_obj = JIT(settings, sys_argv=sys.argv, use_api=True)
    warehouse_obj = Warehouse(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()

    data = report_obj.data
    data = data.get('data',[])
    option = data.get('option','get_report')
    status = 'active'

    warehouse = data.get('warehouse', '')
    product_family = data.get('product_family', 'TUBOS')
<<<<<<< HEAD
    product_line = data.get('product_line', '')
=======
    product_line = data.get('product_line', '304')
    # familia = data.get('familia', '')
>>>>>>> fb96d052a2b7ca05e37923fe0fbea7380960a9b9
    
    warehouse_cedis = 'CEDIS GUADALAJARA'
    warehouse_cedis = 'ALM GUADALAJARA'
    
    if option == 'get_report':
        products = gett_product_by_type(product_type=product_family, product_line=product_line)
        product_dict = {x['product_code']:x for x in products}
<<<<<<< HEAD
        product_code = ['750200301040']
        #product_code = list(product_dict.keys())
=======
        #print('///////////product dict', product_dict)
        product_code = list(product_dict.keys())
        #product_code = ['750200301040']
        #print('///////PRODUCT CODES', product_code)
>>>>>>> fb96d052a2b7ca05e37923fe0fbea7380960a9b9
        procurment = get_procurments(product_code=product_code)
        
        #print('///////PROCURMENT', procurment)
        product_stock = gett_products_inventory(product_code=product_code, warehouse=warehouse)
        stock_cedis = gett_products_inventory(product_code=product_code, warehouse=warehouse_cedis)
        stock_cedis_dict = {x['product_code']:x['actuals'] for x in stock_cedis}
                
        res_first = report_obj.reorder_rules_warehouse(product_code=product_code)
        stock_dict = {}
        product_code = []
        
        for item in procurment:
            code = item['product_code']
            warehouse = item['warehouse'].lower().replace(' ','_')
            actuals = stock_cedis_dict.get(code, 0)
            product_name = product_dict[code]['product_name']
            product_category = product_dict[code]['product_category']
            product_type = product_dict[code]['product_type']

            stock_dict[code] = stock_dict.get(code,
                {
                    'sku': item['sku'],
                    'desc_producto': product_name,
                    'line': product_category,
                    'familia': product_type,
                    'stock_mty': 0,
                    'stock_gdl': 0,
                    'stock_max': 0,
                    'stock_merida': 0,
                    'actuals': actuals, #   proviene de stock_cedis_dict
                    'percentage_stock_max': 0,
                    'stock_final': actuals,
                }
            )
    
            stock_dict[code].update({f'stock_to_move_{warehouse}': item['procurment_qty']})
            stock_dict[code]['stock_final'] -= item['procurment_qty']
            
        for x in product_stock:
            code = x['product_code']
            warehouse = x['warehouse'].lower().replace(' ','_')
            if stock_dict.get(code):
                stock_dict[code][f'actuals_{warehouse}'] = x['actuals']
        
        for x in res_first:
            code = x['product_code']
            warehouse = x['warehouse'].lower().replace(' ','_')
            if stock_dict.get(code):
                stock_dict[code][f'stock_max_{warehouse}'] = x['stock_maximum']
                stock_dict[code][f'p_stock_max_{warehouse}'] = round((stock_dict[code][f'actuals_{warehouse}'] / x[f'stock_maximum']) * 100, 2)
                    
        stock_list = list(stock_dict.values())
        
        percentage_values = [40, 30, 70]

        for items in stock_list:
            maximum_stock_mty = 435
            stock_max_alm_gdl = 170
            #stock_max_alm_merida = items['stock_max_alm_merida']
            initial_stock_cedis = 150
            
            for value in items:
                if value.startswith('p_stock_max_') and items[value] < 100:
                    pass
                    # percentage_values.append(round(items[value]))
            
            sorted_values = sorted(percentage_values)
            
            # Calcular diferencias de porcentaje
            percentage_differences = []
            for i in range(1, len(sorted_values)):
                difference = sorted_values[i] - sorted_values[i - 1]
                percentage_differences.append(difference)
            
            #   Crear un diccionario para almacenar los resultados
            if len(percentage_differences) >= 2:
                first_diference = percentage_differences[0]
                second_diference = percentage_differences[1]
                                
                # Calculos para primer almacen
                percentage_of_pieces_warehouse_one = math.floor((maximum_stock_mty * first_diference) / 100)
                total_stock_cedis = initial_stock_cedis - percentage_of_pieces_warehouse_one
                
                # Calculos para segundo almacen
                second_warehouse = math.floor((stock_max_alm_gdl * second_diference) / 100)
                first_warehouse = math.floor((maximum_stock_mty * second_diference) / 100)
                
                total_relation = first_warehouse + second_warehouse
                
                stock_for_warehouse_two = round(second_warehouse * total_stock_cedis / total_relation)
                stock_for_warehouse_one = math.ceil(stock_for_warehouse_two * first_warehouse / second_warehouse)
                
                print('almacen 1', stock_for_warehouse_one)
                print('almacen 2', stock_for_warehouse_two)



        # script_obj.HttpResponse({
        #     "stockInfo": stock_list,
        # })

    elif option == 'get_catalog':
        warehouse_types_catalog = warehouse_obj.get_all_stock_warehouse()
        product_type = get_catalog_product_field(id_field='61ef32bcdf0ec2ba73dec343')
        
        script_obj.HttpResponse({
            "dataCatalogWarehouse": warehouse_types_catalog,
            "dataCatalogProductFamily": product_type,
        })

    elif option == 'get_product_line':
        filters = ['inventory',]
        product_code_aux = data.get("product_code")
        products_categorys = get_report_filters(filters, product_code_aux=product_code_aux)

        script_obj.HttpResponse({
            "product_line": products_categorys,
        })