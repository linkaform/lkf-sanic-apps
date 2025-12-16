# -*- coding: utf-8 -*-
import sys, simplejson, math
from datetime import timedelta, datetime

from linkaform_api import settings
from account_settings import *

from stock_report import Reports

    
print('whcih', Reports)

def arrage_by_prodcut(data):
    res = []
    for product, info  in data.items():
        qty = info.get('actuals')
        row = {
            'product_code': product,
            'scrap_flats': info.get('scrap'),
            'total_flats': qty,
            'scrap_pct': round(info.get('scrap_per')*100,4),
            '_children':get_reason_as_children(info.get('reason'), qty )
            }
        res.append(row)
    return sort_by_key(res, 'scrap_flats')
    # return res

def arrage_by_reason(data):
    res = []
    total = 0
    for reason, info  in data.items():
        total += info.get('scrap',0)
    for reason, info  in data.items():
        qty = info.get('actuals')
        row = {
            'reason': reason,
            'scrap_flats': info.get('scrap'),
            'scrap_pct': round(info.get('scrap')/total*100,4),
            '_children':from_reson_products_as_children(info.get('product',{}), info.get('scrap')  )
            }
        res.append(row)
    return sort_by_key(res, 'scrap_flats')

def from_reson_products_as_children(data, total):
    res = []
    for key, val in data.items():
        row = {
            'reason':key, 
            'scrap_flats':val, 
            'scrap_pct': round(val/total *100,2)}
        res.append(row)
    return sort_by_key(res, 'scrap_flats')

def arrage_by_warehouse(data):
    res = []
    total = 0
    for warehouse, info  in data.items():
        qty = info.get('actuals')
        row = {
            'warehouse': warehouse,
            'scrap_flats': info.get('scrap'),
            'total_flats': qty,
            'scrap_pct': round(info.get('scrap')/qty*100,4),
            '_children':get_products_as_children(info.get('products',{}), qty)
            }
        res.append(row)
    return res

def arrage_graph_by_product(data):
    """
      labels: ['20-11-23','20-11-23','20-11-24','20-11-25'],
  datasets: [
    {
      label: 'LNAS',
      data: [10,15,5,20,40],
      backgroundColor: '#bad3c6',
      fill: true,
    },
    """
    res = {"labels":[], "datasets":[]}
    res['labels'] = list(data.keys())
    products = {}
    for yearweek, info in data.items():
        for pcode, values in info['products'].items():
           products[pcode] = products.get(pcode, {} )
           products[pcode].update({yearweek:values.get('scrap',0)})
    for pcode, values in products.items():
        print('pcoce', pcode)
        row = {'label':pcode, 'data':[], 'fill':True, 'backgroundColor':''}
        for yearweek in res['labels']:
            if values.get(yearweek):
                row['data'].append(values[yearweek])
            else:
                row['data'].append(0)
        print('row', row)
        res['datasets'].append(row)

    return res

def get_reason_as_children(data, total):
    res = []
    for r, q in data.items():
        row = {
            'product_code':r, 
            'scrap_flats':q, 
            'scrap_pct': round(q/total *100,2)}
        res.append(row)
    return sort_by_key(res, 'scrap_flats')

def get_products_as_children(data, total):
    res = []
    for product, info in data.items():
        q = info.get('scrap')
        row = {
            'warehouse':product, 
            'scrap_flats':q, 
            'scrap_pct': round(q/total *100,2)}
        res.append(row)
    return sort_by_key(res, 'scrap_flats')

def sort_by_key(data, key):
    tmp = {}
    res = []
    for r in data:
        val = r.get(key)
        tmp[val] = tmp.get(val, [])
        tmp[val].append(r)
    tmp_keys = list(tmp.keys())
    tmp_keys.sort()
    tmp_keys.reverse()
    for k in tmp_keys:
        res += tmp[k]
    return res  


if __name__ == '__main__':
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    #getFilters
    option = report_obj.data.get('data').get("option",0)
    product_code = report_obj.data.get('data').get("product_code")
    print('data',report_obj.data.get('data'))
    print('option',option)
    print('product_code',product_code)
    if option == 'getFilters': 
        filters = ['products','warehouse']
        filter_data = report_obj.get_report_filters(filters)
    elif option =='getLotNumber':
        filters = ['inventory',]
        filter_data = report_obj.get_report_filters(filters, product_code=product_code)
    else:
        report_obj.get_scrap_report()
        report_obj.json['firstElement'] = {'data': arrage_by_prodcut(report_obj.scrap_by_product)}
        report_obj.json['secondElement'] = {'data': arrage_graph_by_product(report_obj.scrap_by_week)}
        report_obj.json['thirdElement'] = {'data': []}
        report_obj.json['fourthElement'] = {'data': arrage_by_warehouse(report_obj.scrap_by_warehouse)}
        report_obj.json['sixthElement'] = {'data': arrage_by_reason(report_obj.scrap_by_reason)}
        # report_obj.json['secondElement'] = {'data':data}

    sys.stdout.write(simplejson.dumps(report_obj.report_print()))

