import sys,json, simplejson, re
from account_settings import *
from linkaform_api import  base
from pytz import timezone
from datetime import datetime, timedelta, date

#---Get Catalog
def get_catalog_record():
    dic_res = []
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
    res = script_obj.lkf_api.search_catalog(124692, mango_query)

    for item_catalog in res:
        cliente = item_catalog.get('670f20ba3b523deaa0b496b6', '')

        dic_item = {'cliente':cliente,}
        dic_res.append(dic_item)

    dic_res_sort = sorted(dic_res, key=lambda x: x["cliente"])

    if dic_res_sort :
        return dic_res_sort  
    return None

#----Format
def format_report_first(data, type_record):
    dic_res = []
    for item_record in data:
        folio = item_record.get('folio','')
        client = item_record.get('client','')
        instrument = item_record.get('instrument','')
        model = item_record.get('model','')
        brand = item_record.get('brand','')
        serie = item_record.get('serie','')
        last_maitenance = item_record.get('last_maitenance','')
        next_maitenance = item_record.get('next_maitenance','')

        if len(type_record) == 0:
            dic_res.append({
                'title': client,
                'color': "#e74c3c",
                'start': last_maitenance,
                'description': instrument,
                'eventBackgroundColor':"#e74c3c",
                'allDay': True, 
                'extendedProps': {
                    'folio':folio,
                    'client':client,
                    'instrument':instrument,
                    'model':model,
                    'serie':serie,
                    'brand':brand,
                }
            })
            dic_res.append({
                'title': client,
                'color': "#58d68d",
                'start': next_maitenance,
                'description': instrument,
                'eventBackgroundColor':"#58d68d",
                'allDay': True, 
                'extendedProps': {
                    'folio':folio,
                    'client':client,
                    'instrument':instrument,
                    'model':model,
                    'serie':serie,
                    'brand':brand,
                }
            })
        if 'last' in type_record :
            dic_res.append({
                'title': client,
                'color': "#e74c3c",
                'start': last_maitenance,
                'description': instrument,
                'eventBackgroundColor':"#e74c3c",
                'allDay': True, 
                'extendedProps': {
                    'folio':folio,
                    'client':client,
                    'instrument':instrument,
                    'model':model,
                    'serie':serie,
                    'brand':brand,
                }
            })
        if 'next' in type_record :
            dic_res.append({
                'title': client,
                'color': "#58d68d",
                'start': next_maitenance,
                'description': instrument,
                'eventBackgroundColor':"#58d68d",
                'allDay': True, 
                'extendedProps': {
                    'folio':folio,
                    'client':client,
                    'instrument':instrument,
                    'model':model,
                    'serie':serie,
                    'brand':brand,
                }
            })

    return dic_res

#----Query
def query_report_first(client, types):
    match_query = { 
        "form_id": 124696,
        "deleted_at":{"$exists":False},
    }

    if client:
        match_query.update({'answers.670f20ba3b523deaa0b496b3.670f20ba3b523deaa0b496b6':client})
    
    query = [
        {"$match": match_query},
        {"$project": {
            "_id":0,
            "folio":"$folio",
            "client":"$answers.670f20ba3b523deaa0b496b3.670f20ba3b523deaa0b496b6",
            "instrument":"$answers.6748b4da70017a0dc61603cb.6748b4da70017a0dc61603cc",
            "model":"$answers.a00000000000000000000002",
            "brand":"$answers.a00000000000000000000003",
            "serie":"$answers.a00000000000000000000004",
            "last_maitenance":"$answers.a00000000000000000000011",
            "next_maitenance":"$answers.a00000000000000000000012",
        }},
    ]

    result = script_obj.cr.aggregate(query)
    result_format = format_report_first(result, types)
    return result_format

if __name__ == "__main__":
    #-CONFIGURACIONES
    script_obj = base.LKF_Base(settings, sys_argv=sys.argv, use_api=True)
    script_obj.console_run()
    #-FILTROS
    data = script_obj.data
    data = data.get('data',[])
    client = data.get('cliente',[])
    types = data.get('types',[])
    option = data.get('option','report')
    #-DATA
    if option == 'get_catalog':
        response_catalog = get_catalog_record()
        sys.stdout.write(simplejson.dumps({'data':response_catalog}))
    elif option == 'report':
        response_first = query_report_first(client, types)
        sys.stdout.write(simplejson.dumps({'data':{
            'response_first': response_first,
        }}))
