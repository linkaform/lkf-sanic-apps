import sys,json, simplejson, re
from linkaform_api import  base
from account_settings import *
from datetime import datetime

#---Formatear
def format_firts_element(data_query):
    data = [x for x in data_query]
    response = []
    #--Format
    for item in data:
        _children = []

        total_stock = 0
        total_adjustmen_in = 0
        total_adjustmen_out = 0
        wharehouse = item.get('wharehouse_name','')
        _children_data = item.get('list_record','')

        for record in _children_data:
            folio = record.get('folio','')
            location = record.get('wharehouse_location','')
            inventory = record.get('inventory',[])
            product = record.get('product','')
            stock = record.get('stock',0)
            adjust_in = record.get('adjust_in',0)
            adjust_out = record.get('adjust_out',0)
            status_item = record.get('status_item','')


            total_stock += stock
            total_adjustmen_in += adjust_in
            total_adjustmen_out += adjust_out
            _children.append({
                'folio': folio,
                'location': location,
                'inventory': inventory,
                'product': product,
                'stock': stock,
                'adjust_in': adjust_in,
                'adjust_out': adjust_out,
                'status_item': status_item.title(),
            })

        response.append({
            'wharehouse':wharehouse,
            'stock': total_stock,
            'adjust_in': total_adjustmen_in,
            'adjust_out': total_adjustmen_out,
            '_children':_children,
        })

    return response

def format_catalog_wharehouse(data_query):
    list_response = []
    for item in data_query:
        wharehouse = item.get('6442e4831198daf81456f274','')
        if wharehouse not in list_response and wharehouse !='':
            list_response.append(wharehouse)

    list_response.sort()           
    return list_response

#---Consultar
def get_first_element(date_to, date_from, wharehouse, status):
    match_query = {
        "form_id": 123136,
        "deleted_at":{"$exists":False},
    }

    #--Filter 
    if date_to:
        date_to = datetime.strptime(date_to, "%Y-%m-%d")

    if date_from:
        date_from = datetime.strptime(date_from, "%Y-%m-%d")

    match_query.update(script_obj.get_date_query(date_to, date_from))

    if wharehouse!='':
        match_query.update({'answers.66dfc4de6b95c11a3b58720f.6442e4831198daf81456f274': wharehouse})

    if status!='':
        match_query.update({'answers.644bf7ccfa9830903f087867.ad00000000000000000ad999': status})

    query = [
        {"$unwind": "$answers.644bf7ccfa9830903f087867"},
        {"$match": match_query}, 
        {"$project": {
            "_id":1,
            "wharehouse_name":"$answers.66dfc4de6b95c11a3b58720f.6442e4831198daf81456f274",
            "folio":"$folio",
            "date":"$answers.000000000000000000000111",
            "wharehouse_location":"$answers.66dfc4de6b95c11a3b58720f.65ac6fbc070b93e656bd7fbe",
            "product":"$answers.644bf7ccfa9830903f087867.66dfc4d9a306e1ac7f6cd02c.61ef32bcdf0ec2ba73dec33d",
            "stock":"$answers.644bf7ccfa9830903f087867.ad00000000000000000ad000",
            "adjust_in":"$answers.644bf7ccfa9830903f087867.ad00000000000000000ad100",
            "adjust_out":"$answers.644bf7ccfa9830903f087867.ad00000000000000000ad200",
            "status_item":"$answers.644bf7ccfa9830903f087867.ad00000000000000000ad999",
            "comment":"$answers.64d05792c373f9b62f539d00",
        }},
        {"$group":{
            "_id":{
                "wharehouse_name":"$wharehouse_name",
            },
            "list_record":{
                "$push":{
                    "folio":"$folio",
                    "date":"$date",
                    "wharehouse_name":"$wharehouse_name",
                    "wharehouse_location":"$wharehouse_location",
                    "product":"$product",
                    "stock":"$stock",
                    "adjust_in":"$adjust_in",
                    "adjust_out":"$adjust_out",
                    "status_item":"$status_item",
                    "comment":"$comment",
                    "status":"$status",
                }
            }
        }},
        {"$project":{
            "_id":0,
            "wharehouse_name":"$_id.wharehouse_name",
            "list_record": "$list_record"
        }},
    ]
    result = script_obj.cr.aggregate(query)
    res_format = format_firts_element(result)
    return res_format


def get_catalog_wharehouse():
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
    res = script_obj.lkf_api.search_catalog( 123110, mango_query)
    res_format = format_catalog_wharehouse(res)
    return res_format


if __name__ == "__main__":
    script_obj = base.LKF_Base(settings, sys_argv=sys.argv, use_api=True)
    script_obj.console_run()

    #-FILTROS
    data = script_obj.data
    data = data.get('data',[])

    option = data.get('option','')
    date_to = data.get('date_to','')
    date_from = data.get('date_from', '')
    wharehouse = data.get('wharehouse', '')
    status = data.get('status', '')

    if option == 'get_report':
        res_first = get_first_element(date_to, date_from, wharehouse, status)
        script_obj.HttpResponse({
            "firstElement":res_first,
        })
    elif option == 'get_catalog':
        res_catalog = get_catalog_wharehouse()
        script_obj.HttpResponse({
            "dataCatalog":res_catalog,
        })
