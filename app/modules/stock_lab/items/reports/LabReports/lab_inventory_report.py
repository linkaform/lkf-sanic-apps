#-*- coding: utf-8 -*-

import simplejson, sys, string
from copy import deepcopy
from linkaform_api import settings, network, utils
from bson import ObjectId
import time, pytz, math
from datetime import datetime, timedelta
from stock_report import Reports

from account_settings import *

def get_format_first(data_query):
    sort_keys = list(data_query.keys())
    sort_keys.sort()
    res = []
    for key in sort_keys:
        for x in data_query[key]:
            x['_id'] = str(x.get('_id', ""))
            res.append(x)
            x['qty'] = x.get('qty_in',0) if x.get('qty_in',0) != 0 else x.get('qty_out',0)
    return res

def get_format_first_old(data_query):
    global report_model
    data_query = [x for x in data_query]
    for x in data_query:
        plant_code = x.get('plant_code','')
        ready_week = x.get('ready_week','')
        option_out = x.get('out','')
        option_in = x.get('in', '')
        move_date = str(x.get('move_date', ''))[0:10]
        created_date = str(x.get('created_date', ''))[0:10]
        qty = x.get('qty', '')

        if type(option_out) == list and option_out:
            option_out = option_out[0].replace('_',' ').title()
        elif type(option_out) != list and option_out:
            option_out = option_out.replace('_',' ').title()

        if type(option_in) == list and option_in:
            option_in = option_in[0].replace('_',' ').title()
        elif type(option_in) != list and option_in:
            option_in = option_in.replace('_',' ').title()


        report_model.json['firstElement']['data'].append({
            "plant_code":plant_code,
            "ready_week":ready_week,
            "out":option_out,
            "in":option_in,
            "move_date":move_date,
            "created_date":created_date,
            "qty":qty,
        }) 

def get_format_second(data_query):
    global report_model
    data_query = [x for x in data_query]
    for x in data_query:
        plant_code = x.get('plant_code','')
        ready_week = x.get('ready_week','')
        option_out = x.get('out','')
        option_in = x.get('in', '')
        qty = x.get('qty', '')

        if type(option_out) == list and option_out:
            option_out = option_out[0].replace('_',' ').title()
        elif type(option_out) != list and option_out:
            option_out = option_out.replace('_',' ').title()

        if type(option_in) == list and option_in:
            option_in = option_in[0].replace('_',' ').title()
        elif type(option_in) != list and option_in:
            option_in = option_in.replace('_',' ').title()


        report_model.json['secondElement']['data'].append({
            "plant_code":plant_code,
            "ready_week":ready_week,
            "out":option_out,
            "in":option_in,
            "qtyTotal":qty,
        }) 

# --- QUERY
def query_report_first(date_from, date_to, plant, option_in, option_out, check):
    global report_model

    match_query = { 
        "form_id":{"$in":[98233,100515]},
        "deleted_at":{"$exists":False},
    }

    #---option
    if check == 'on' and date_from or date_to:
        match_query.update(report_obj.get_date_query(date_from, date_to, date_field_id='000000000000000000000111'))
    elif check == 'off' and date_from or date_to:
        match_query.update(report_obj.get_date_query(date_from, date_to, field_type=None ))

    if plant and '--' not in plant:
        match_query.update({"answers.6442cbafb1b1234eb68ec178.61ef32bcdf0ec2ba73dec33d":  plant})

    if option_in and '--' not in option_in:
        match_query.update({"answers.644897497a16141f4e5ee0c3": option_in})

    if option_out and '--' not in option_out:
        match_query.update({"answers.6442cbafb1b1234eb68ec178.6442e4831198daf81456f274": option_out})

    query = [
        {"$match": match_query},
        {"$project": {
            "_id":0,
            "plant_code": "$answers.6442cbafb1b1234eb68ec178.61ef32bcdf0ec2ba73dec33d",
            "ready_week": "$answers.6442cbafb1b1234eb68ec178.620a9ee0a449b98114f61d77",
            "folio": "$answers.6442cbafb1b1234eb68ec178.62c44f96dae331e750428732",
            "in": {"$cond":[ 
                {"$eq":["$form_id",98233]},
                "$answers.644897497a16141f4e5ee0c3",
                "$answers.64d52fd23c48fc6e08d47507"]
            },
            "out":"$answers.6442cbafb1b1234eb68ec178.6442e4831198daf81456f274",
            "move_date": "$answers.000000000000000000000111",
            "created_date": "$created_at",
            "qty": {"$cond" :[
                {"$eq":["$form_id",98233]},
                "$answers.6442e4537775ce64ef72dd68",
                "$answers.644bf9a04b1761305b080099"]
            },
        }},
        {"$group":{
            "_id":{
                "plant_code":"$plant_code",
                "ready_week":"$ready_week",
                "out":"$out",
                "in":"$in",
                "move_date":"$move_date",
                "created_date":"$created_date",
            },
            "qty":{"$sum":"$qty"}
        }},
        {"$project":{
            "_id":0,
            "plant_code":"$_id.plant_code",
            "ready_week":"$_id.ready_week",
            "out":"$_id.out",
            "in":"$_id.in",
            "move_date":"$_id.move_date",
            "created_date":"$_id.created_date",
            "qty":"$qty",
        }},
        {"$sort":{"plant_code":1}}
    ]
    result = cr.aggregate(query)
    get_format_first(result)

def query_report_second(date_from, date_to, plant, option_in, option_out, check):
    global report_model

    match_query = { 
        "form_id":{"$in":[98233,100515]},
        "deleted_at":{"$exists":False},
    }

    #---option
    if check == 'on' and date_from or date_to:
        match_query.update(report_obj.get_date_query(date_from, date_to, date_field_id='000000000000000000000111'))
    elif check == 'off' and date_from or date_to:
        match_query.update(report_obj.get_date_query(date_from, date_to, field_type=None ))

    if plant and '--' not in plant:
        match_query.update({"answers.6442cbafb1b1234eb68ec178.61ef32bcdf0ec2ba73dec33d":  plant})

    if option_in and '--' not in option_in:
        match_query.update({"answers.644897497a16141f4e5ee0c3": option_in})

    if option_out and '--' not in option_out:
        match_query.update({"answers.6442cbafb1b1234eb68ec178.6442e4831198daf81456f274": option_out})

    query = [
        {"$match": match_query},
        {"$project": {
            "_id":0,
            "plant_code": "$answers.6442cbafb1b1234eb68ec178.61ef32bcdf0ec2ba73dec33d",
            "ready_week": "$answers.6442cbafb1b1234eb68ec178.620a9ee0a449b98114f61d77",
            "folio": "$answers.6442cbafb1b1234eb68ec178.62c44f96dae331e750428732",
            "in": {"$cond":[ 
                {"$eq":["$form_id",98233]},
                "$answers.644897497a16141f4e5ee0c3",
                "$answers.64d52fd23c48fc6e08d47507"]
            },
            "out":"$answers.6442cbafb1b1234eb68ec178.6442e4831198daf81456f274",
            "move_date": "$answers.000000000000000000000111",
            "created_date": "$created_at",
            "qty": {"$cond" :[
                {"$eq":["$form_id",98233]},
                "$answers.6442e4537775ce64ef72dd68",
                "$answers.644bf9a04b1761305b080099"]
            },
        }},
        {"$group":{
            "_id":{
                "plant_code":"$plant_code",
                "ready_week":"$ready_week",
                "out":"$out",
                "in":"$in",
            },
            "qty":{"$sum":"$qty"}
        }},
        {"$project":{
            "_id":0,
            "plant_code":"$_id.plant_code",
            "ready_week":"$_id.ready_week",
            "out":"$_id.out",
            "in":"$_id.in",
            "qty":"$qty",
        }},
        {"$sort":{"plant_code":1}}
    ]
    result = cr.aggregate(query)
    get_format_second(result)


if __name__ == "__main__":
    # print(sys.argv)
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    # report_model = ReportModel(settings, sys_argv=sys.argv)
    all_data = report_obj.data

    #---FILTROS
    data = all_data.get("data", {})
    print('data', data)
    date_to = data.get("date_to",'')
    date_from = data.get("date_from",'')
    product_code = data.get("plant",'')
    warehouse_to = data.get("option_in",'')
    warehouse_from = data.get("option_out",'')
    check = data.get("check",'')
    option = data.get("option",0)
    print('option', option)
    cr = report_obj.cr
    if option == 2:
        report_obj.json['catalogtwo'] = report_obj.get_warehouse()
        sys.stdout.write(simplejson.dumps(report_obj.report_print()))
    elif option == 1:
        res = report_obj.lkf_api.search_catalog( report_obj.CATALOG_INVENTORY_ID)
        print('res=', res)
        report_obj.json['catalog'] = res
        sys.stdout.write(simplejson.dumps(report_obj.report_print()))
    elif option == 0:
        moves = report_obj.get_inventory_moves()
        #todo merge dict
        moves.update(moves)
        data = get_format_first(moves)
        report_obj.json['firstElement'] = {'data': data}
        #query_report_first(date_from, date_to, plant, option_in, option_out, check)
        #sys.stdout.write(simplejson.dumps(report_obj.report_print()))
        #query_report_second(date_from, date_to, plant, option_in, option_out, check)
        sys.stdout.write(simplejson.dumps(report_obj.report_print()))
    else:
        sys.stdout.write(simplejson.dumps({"json": {}}))