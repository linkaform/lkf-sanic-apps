import sys,json, re
from linkaform_api import  base
from account_settings import *
from datetime import datetime
from reporte_stock import format_firts_element

def get_first_element(wharehouse, familia):
    match_query = {
        "form_id": 123136,
        "deleted_at":{"$exists":False},
    }

    #--Filter 
    if wharehouse!='':
        match_query.update({'answers.66dfc4de6b95c11a3b58720f.6442e4831198daf81456f274': {'$in': wharehouse}})

    # if status!='':
    #     match_query.update({'answers.644bf7ccfa9830903f087867.ad00000000000000000ad999': status})

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
    print("//////////////", wharehouse)
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
    #res_format = format_catalog_wharehouse(res)
    return 




if __name__ == "__main__":
    script_obj = base.LKF_Base(settings, sys_argv=sys.argv, use_api=True)
    script_obj.console_run()

    #-FILTROS
    data = script_obj.data
    data = data.get('data',[])

    option = data.get('option','get_report')
    wharehouse = data.get('wharehouse', '')
    familia = data.get('familia', '')

    if option == 'get_report':
        res_first = get_first_element(wharehouse, familia)
        print('Hola reporteee', res_first)
        '''
        script_obj.HttpResponse({
            "firstElement":res_first,
        })
        '''
    elif option == 'get_catalog':
        #res_catalog = get_catalog_wharehouse()
        print('Hola catalogo')
        '''
        script_obj.HttpResponse({
            "dataCatalog":res_catalog,
        })
        '''