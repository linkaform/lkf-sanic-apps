#-*- coding: utf-8 -*-

import simplejson, sys
from copy import deepcopy
from linkaform_api import settings, network, utils
from bson import ObjectId
import time
from datetime import datetime, timedelta
from math import floor

from stock_report import Reports

from account_settings import *


columns_data = []
colweeks = []
table_data = []
existin_cols = []
chart_data = {"labels":[]}
chart_cat_dict = {
    'reqS2':"Required S2",
    'reqS3':"Required S3",
    'forcastS2':"Forcast S2",
    'hoursS2':"Hours S2",
    'hoursS3':"Hours S3",
    'hoursT':"Hours Total",
    }
elem_color = {
    'reqS2':"#D6EAF8",
    'reqS3':"#E8DAEF",
    'forcastS2':"#EDBB99 ",
    'hoursS2':"#82E0AA",
    'hoursS3':"#F0B27A",
    'hoursT':"#F5B7B1",
    }

columns_data.append({"title":"Plant Code", "hozAlign":"left", "field":"plant_code", "with":150, "frozen":False, "headerFilter":"input"})
columns_data.append({"title":"Botanical Name", "hozAlign":"left", "field":"plant_name", "with":150, "frozen":False, "headerFilter":"input"})
columns_data.append({"title":"Container Type", "hozAlign":"left", "field":"container_type", "with":150, "frozen":False, "headerFilter":"input"})
columns_data.append({"title":"Container Qty", "hozAlign":"right", "field":"container_qty", "with":150, "frozen":False, "headerFilter":"input"})
columns_data.append({"title":"Assignd", "hozAlign":"left", "field":"asigned", "with":150, "frozen":False, "headerFilter":"input"})
columns_data.append({"title":"Surplus", "hozAlign":"left", "field":"surplus", "with":150, "frozen":False, "headerFilter":"input"})

actuals_col = {"title":"Actuals", "field":"actuals", "hozAlign":"right", "with":150, "frozen":False, "headerFilter":"input",
    "formatter":"money", "formatterParams":{
            "decimal":".",
            "thousand":",",
            "symbol":"",
            "symbolAfter":"",
            "precision":0,
        }}
actuals_col_prev = {"title":"Actuals Previews Weeks", "field":"actuals_previews", "hozAlign":"right", "with":150, "frozen":False, "headerFilter":"input",
    "formatter":"money", "formatterParams":{
            "decimal":".",
            "thousand":",",
            "symbol":"",
            "symbolAfter":"",
            "precision":0,
        }}
forcast_s2 =  {"title":"A. Forecast S2", "field":"forcastS2", "hozAlign":"right", "with":150, "widthGrow":4, "headerFilter":"input",
        "formatter":"money", "formatterParams":{
        "decimal":".",
        "thousand":",",
        "symbol":"",
        "symbolAfter":"",
        "precision":0,
        }}
forcast_s3 =  {"title":"A. Forecast S3"  ,"field":"forcastS3","hozAlign":"right","headerFilter":"input",
        "formatter":"money", "formatterParams":{
        "decimal":".",
        "thousand":",",
        "symbol":"",
        "symbolAfter":"",
        "precision":0,
        }}
adjusted_fs2 =  {"title":"Adjusted FS2"  ,"field":"adjusted_fs2","hozAlign":"right","headerFilter":"input",
        "formatter":"money", "formatterParams":{
        "decimal":".",
        "thousand":",",
        "symbol":"",
        "symbolAfter":"",
        "precision":0,
        }}
adjusted_fs3 =  {"title":"Adjusted FS3"  ,"field":"adjusted_fs3","hozAlign":"right","headerFilter":"input",
        "formatter":"money", "formatterParams":{
        "decimal":".",
        "thousand":",",
        "symbol":"",
        "symbolAfter":"",
        "precision":0,
        }}
columns_data.append(actuals_col_prev)
columns_data.append(actuals_col)

week_columns = [
    {"title":"Stage S2 Req",  "field":"req", "hozAlign":"right","with":150, "headerFilter":"input",
        "formatter":"money", "formatterParams":{
            "decimal":".",
            "thousand":",",
            "symbol":"",
            "symbolAfter":"",
            "precision":0,
            }},
    {"title":"Stage S2 Forecast Actuals",  "field":"actuals_forcast", "hozAlign":"right","with":150, "headerFilter":"input",
        "formatter":"money", "formatterParams":{
            "decimal":".",
            "thousand":",",
            "symbol":"",
            "symbolAfter":"",
            "precision":0,
            }},
    {"title":"Stage S3 Req", "field":"req","hozAlign":"right", "with":150, "headerFilter":"input",
            "formatter":"money", "formatterParams":{
            "decimal":".",
            "thousand":",",
            "symbol":"",
            "symbolAfter":"",
            "precision":0,
            }},
    {"title":"Stage S2 Assign", "field":"reqAsigne","hozAlign":"right", "with":150,
        "editor":"number", "editorParams":{"step":10} ,"validator":["numeric"],
        "formatter":"money", "formatterParams":{
                "decimal":".",
                "thousand":",",
                "symbol":"",
                "symbolAfter":"",
                "precision":0,
                        }},
    {"title":"Stage S3 Assign", "field":"reqAsigne", "hozAlign":"right", "with":150,
        "editor":"number", "editorParams":{"step":10} ,"validator":["numeric"],
        "formatter":"money", "formatterParams":{
                "decimal":".",
                "thousand":",",
                "symbol":"",
                "symbolAfter":"",
                "precision":0,
                        }},
    {"title":"Stage S2 Hours Req",  "field":"hours", "hozAlign":"right","with":150, "headerFilter":"input",
        "formatter":"money", "formatterParams":{
            "decimal":".",
            "thousand":",",
            "symbol":"",
            "symbolAfter":"",
            "precision":0,
            }},
    {"title":"Stage S3 Hours Req",  "field":"hours", "hozAlign":"right","with":150, "headerFilter":"input",
        "formatter":"money", "formatterParams":{
            "decimal":".",
            "thousand":",",
            "symbol":"",
            "symbolAfter":"",
            "precision":0,
            }},
    {"title":"Week Hours Req",  "field":"hours", "hozAlign":"right","with":150, "headerFilter":"input",
        "formatter":"money", "formatterParams":{
            "decimal":".",
            "thousand":",",
            "symbol":"",
            "symbolAfter":"",
            "precision":0,
            }},
    ]

def get_week_query(serach_key, week_from, week_to=None, current=True):
    qry = {}
    if not week_to:
        week_to = week_from
    if current:
        qry.update({
        serach_key: {
        '$gte':week_from,
        '$lte':week_to,
        }
        })
    else:
        qry.update({
        serach_key: {
        '$lt':week_from
        }
        })

    return qry


def get_plant(all_codes):
    mango_query = {
        "selector": {
            "answers": {
                "61ef32bcdf0ec2ba73dec33d": {"$in": all_codes},
                } ,
        "limit": 1,
        "skip": 0
                }
            }
    plant = lkf_api.search_catalog(self.catalog_plant_catalog, mango_query, jwt_settings_key='USER_JWT_KEY')
    return plant


def set_cut_hours(requierd, recipe, recipeS3):
    hours = {}
    for req, qty in requierd.items():
        stage = req[3:][:2]
        yearweek = 'hours{}'.format(req[5:])
        yearweek_S2 = 'hours{}{}'.format('S2',req[5:])
        yearweek_S3 = 'hours{}{}'.format('S3',req[5:])
        if not hours.get(yearweek):
            hours[yearweek] = 0
            hours[yearweek_S2] = 0
            hours[yearweek_S3] = 0
        if stage == 'S2':
            cut_prod = recipe.get('cut_productivity',168)
            try:
                cut_prod = float(cut_prod)
            except:
                cut_prod = 168
            hours[yearweek_S2] += round(qty / cut_prod,2)
        if stage == 'S3':
            cut_prod = recipeS3.get('cut_productivity',120)
            try:
                cut_prod = float(cut_prod)
            except:
                cut_prod = 120
            hours[yearweek_S3] += round(qty / cut_prod,2)

        hours[yearweek] += round(qty / cut_prod,2)
    set_chart_req(hours , row_type='hours')
    return hours

def forcast_actualas(actuals, plant_recipe):
    forcast = {}
    if plant_recipe.get('S2_mult_rate'):
        # forcast_week = get_forcast_week(year_week, plant_recipe.get('S2_growth_weeks'))
        forcast["forcastS2"] = floor(actuals * plant_recipe.get('S2_mult_rate'))
    if plant_recipe.get('S3_mult_rate'):
        # forcast_week = get_forcast_week(year_week, plant_recipe.get('S3_growth_weeks'))
        forcast["forcastS3"] = floor(actuals * plant_recipe.get('S3_mult_rate'))
    return forcast

def set_chart_req(row, row_type='req'):
    global chart_data
    for key, value in row.items():
        if row_type == 'actuals':
            if not 'actuals_forcast' in key:
                continue
            stage = key[15:-6]
        else:
            stage = key[len(row_type):-6]

        yearweek = key[-6:]

        if yearweek not in chart_data["labels"]:
            chart_data["labels"].append(yearweek)

        if not stage or row_type == 'actuals':
            if row_type == 'actuals':
                key_type = 'forcastS2'
            else:
                key_type = 'hoursT'
        if row_type =='req':
            key_type = '{}{}'.format(key[:len(row_type)], stage)
        else:
            if row_type == 'hours' and stage:
                key_type = '{}{}'.format(key[:len(row_type)], stage)
        if not chart_data.get(key_type):
            chart_data[key_type]={
                "label":chart_cat_dict[key_type],
                "data":{}
            }
            if row_type =='hours':
                chart_data[key_type].update({
                    "type":"line",
                    "borderColor":elem_color[key_type],
                    "yAxisID":"ay",
                })
            if row_type == 'req' or row_type == 'actuals':
                chart_data[key_type].update({
                    "type":"bar",
                    "backgroundColor":elem_color[key_type],
                    "yAxisID":"ay1",
                })
        if yearweek not in chart_data[key_type]["data"]:
            chart_data[key_type]["data"][yearweek] = 0

        chart_data[key_type]["data"][yearweek] += value
        # if not chart_data.get(yearweek):
        #     chart_data[yearweek] = {
        #         "Categories":{"reqS2":0,"reqS3":0, "forcastS2":0},
        #         "LineCategory":{"hoursS3":0, "hoursS2":0,"hoursT":0}
        #         }
        # if row_type == 'req' or row_type == 'actuals':
        #     chart_data[yearweek]["Categories"][key_type] +=  float(value)
        # if row_type == 'hours':
        #     chart_data[yearweek]["LineCategory"][key_type] +=  float(value)
    return True

def set_rows(requierd, actuals, recipes, recipesS3):
    global chart_data
    res = []
    for x, code in enumerate(actuals):
        row = {}
        row['id'] = x + 1
        row['plant_code'] = code
        row['hours'] = 0
        if requierd.get(code):
            set_chart_req(requierd[code], 'req')
            row.update(requierd[code])
            row.update(set_cut_hours(requierd[code], recipes[code], recipesS3[code]))
            set_chart_req(actuals[code],'actuals')
        row.update(actuals[code])
        res.append(row)
    return res

def set_week_columns_field(stage, year_week):
    global week_columns, existin_cols
    res = []
    week_cols = deepcopy(week_columns)
    for col in week_cols:
        field_name = col.get('field')
        if stage in col.get('title'):
            col["field"] = "{}{}{}".format(field_name, stage, year_week)
            if col["field"] not in existin_cols:
                existin_cols.append(col["field"])
                res.append(col)
        elif col["field"] == "hours" and 'Stage' not in col.get('title'):
            col["field"] = "{}{}".format(field_name, year_week)
            if col["field"] not in existin_cols:
                existin_cols.append(col["field"])
                res.append(col)
    return res

def update_stage_2week(stage, year_week):
    global columns_data, colweeks, existin_cols
    new_col_data = []
    for idx, col in enumerate(columns_data):
        new_cols = []
        existin_cols += [ x.get('field') for x in  col.get('columns',[])]
        if col.get('title') == str(year_week):
            new_cols = set_week_columns_field(stage, year_week)
        if col.get('columns'):
            col['columns'] = new_cols + col.get('columns')
        new_col_data.append(col)
    columns_data = new_col_data

def update_requierd(requierd, stage_req, stage):
    global columns_data, colweeks, existin_cols
    # colweeks = []
    for x in stage_req:
        plant_code = x.get('plant_code')
        year_week = x.get('year_week')

        if not requierd.get(plant_code):
            requierd[plant_code] = {}
        # if not requierd[plant_code].get(year_week):
        #     requierd[plant_code][year_week] = {}
        if year_week not in colweeks:
            colweeks.append(year_week)
            columns_data.append({"title": str(year_week), "columns": set_week_columns_field(stage, year_week)})
        else:
            update_stage_2week(stage, year_week)
        field_name = "req{}{}".format(stage, year_week)
        requierd[plant_code].update({field_name:x.get('requierds')})

    return requierd

def set_dataset_order(res):
    data = res.get('datasets')
    bars = []
    lines = []
    for x in data:
        if x.get('type') == 'bar':
            bars.append(x)
        if x.get('type') == 'line':
            lines.append(x)
    return res

def format_chart():
    global chart_data
    chart_data['labels'].sort()
    yearweeks = chart_data['labels']
    res = {"labels":[], "datasets":[]}
    for key, value in chart_data.items():
        if key == 'labels':
            res['labels'] = value
            continue
        dataset = {"data":[]}
        for week in yearweeks:
            dataset['data'].append(int(value['data'].get(week,0)))
        value.pop('data')
        dataset.update(value)
        res['datasets'].append(dataset)
    res = set_dataset_order(res)
    return res




class Reports(Reports):


    def query_report(self, year_week_from, year_week_to ,current=True):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.FORM_INVENTORY_ID,
            f"answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}":'S2',
            f"answers.{self.f['inventory_status']}":"active",
            }
        match_query.update(get_week_query(f"answers.{self.f['new_cutweek']}", year_week_from, year_week_to, current))
        query = [
            {"$match": match_query },
            {"$project":{
                "_id":1,
                "plant_code":f"$answers.{self.SKU_OBJ_ID}.{self.f['product_code']}",
                "plant_name":{ "$arrayElemAt": [ f"$answers.{self.SKU_OBJ_ID}.{self.f['product_name']}", 0 ] },
                "actuals":f"$answers.{self.f['actual_eaches_on_hand']}",
                "year_week":{"$toInt":f"$answers.{self.f['new_cutweek']}"},
            }},
            {"$group":{
                "_id":{
                    "plant_code":"$plant_code",
                    "plant_name":"$plant_name",
                    "year_week":"$year_week",
                    },
                "actuals":{"$sum":"$actuals"}
            }},
            {"$project":{
                "plant_code":"$_id.plant_code",
                "plant_name":"$_id.plant_name",
                "year_week":"$_id.year_week",
                "actuals":"$actuals",
            }},
            {"$sort": {"plant_code": 1}}
        ]
        # print('query=', simplejson.dumps(query, indent=3))
        result = self.cr.aggregate(query)
        return result

    def query_report_previwes(self, year_week_from, year_week_to ,current=True):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.FORM_INVENTORY_ID,
            f"answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}":'S2',
            f"answers.{self.f['inventory_status']}":"active",
            }
        match_query.update(get_week_query(f"answers.{self.f['new_cutweek']}", year_week_from, year_week_to, current))
        query = [
            {"$match": match_query },
            {"$project":{
                "_id":1,
                "plant_code":f"$answers.{self.SKU_OBJ_ID}.{self.f['product_code']}",
                "plant_name":{ "$arrayElemAt": [ f"$answers.{self.SKU_OBJ_ID}.{self.f['product_name']}", 0 ] },
                "actuals":f"$answers.{self.f['actual_eaches_on_hand']}",
            }},
            {"$group":{
                "_id":{
                    "plant_code":"$plant_code",
                    "plant_name":"$plant_name",
                    },
                "actuals":{"$sum":"$actuals"}
            }},
            {"$project":{
                "plant_code":"$_id.plant_code",
                "plant_name":"$_id.plant_name",
                "actuals":"$actuals",
            }},
            {"$sort": {"plant_code": 1}}
        ]
        result = self.cr.aggregate(query)
        return result

    def get_s2_requierds(self, plant_codes, year_week_from, year_week_to=None):
        if not year_week_to:
            year_week_to = year_week_from
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":81420,
            }
        if plant_codes:
            match_query.update({f"answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}":plant_code,})
        query = [
            {"$match": match_query },
            {"$unwind":f"$answers.{self.f['prod_plan_development_group']}"},
            {"$match": get_week_query(f"answers.{self.f['prod_plan_development_group']}.{self.f['prod_plan_S2_requier_yearweek']}", year_week_from, year_week_to) },
            {"$project":{
                "_id":1,
                "plant_code":f"$answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}",
                "requierds":f"$answers.{self.f['prod_plan_development_group']}.{self.f['prod_plan_require_S2']}",
                "year_week":{"$toInt":f"$answers.{self.f['prod_plan_development_group']}.{self.f['prod_plan_S2_requier_yearweek']}"},
            }},
            {"$group":{
                "_id":{
                    "plant_code":"$plant_code",
                    "year_week":"$year_week",
                    },
                "requierds":{"$sum":"$requierds"}
            }},
            {"$project":{
                "plant_code":"$_id.plant_code",
                "year_week":"$_id.year_week",
                "requierds":"$requierds",
            }},
            {"$sort": {"plant_code": 1, "year_week":1}}
        ]
        # print('query=', query)
        result = self.cr.aggregate(query)
        return [r for r in result]

    def get_s3_requierds(self, plant_codes, year_week_from, year_week_to=None):
        if not year_week_to:
            year_week_to = year_week_from
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.PRODUCTION_PLAN,
            }
        if plant_codes:
            match_query.update({f"answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}":plant_code,})
        match_query.update(get_week_query(f"answers.{self.f['prod_plan_S3_requier_yearweek']}", year_week_from, year_week_to) )
        query = [
            {"$match": match_query },
            {"$project":{
                "_id":1,
                "plant_code":f"$answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}",
                "requierds":f"$answers.{self.f['prod_plan_require_S3']}",
                "year_week":{"$toInt":f"$answers.{self.f['prod_plan_S3_requier_yearweek']}"},
            }},
            {"$group":{
                "_id":{
                    "plant_code":"$plant_code",
                    "year_week":"$year_week",
                    },
                "requierds":{"$sum":"$requierds"}
            }},
            {"$project":{
                "plant_code":"$_id.plant_code",
                "year_week":"$_id.year_week",
                "requierds":"$requierds",
            }},
            {"$sort": {"plant_code": 1, "year_week":1}}
        ]
        # print('query=', query)
        result = self.cr.aggregate(query)
        return [r for r in result]


def get_week_report(year_week_from, year_week_to):
    global report_obj, columns_data
    plant_codes = []
    inventory_flow = report_obj.query_report(year_week_from, year_week_to)
    inventory_previos_weeks = report_obj.query_report_previwes(year_week_from, year_week_to ,current=False)
    requierd_s2 = report_obj.get_s2_requierds(plant_codes, year_week_from, year_week_to)
    requierd_s3 = report_obj.get_s3_requierds(plant_codes, year_week_from, year_week_to)
    # print('requierd_s3', requierd_s3)
    # print('requierd_s2', requierd_s2)
    plant_actuals = {}
    requierd = {}
    plant_codes = [ x['plant_code'] for x in requierd_s2]
    for x in requierd_s3:
        code = x['plant_code']
        if code not in plant_codes:
            plant_codes.append(x['plant_code'])
    if not plant_codes:
        return {}
    recipes = report_obj.get_plant_recipe(plant_codes, stage=[2,])
    # print('recipes', recipes)
    recipesS3 = report_obj.get_plant_recipe(plant_codes, stage=[3,])
    for rec in inventory_flow:
        if not plant_actuals.get(rec.get('plant_code')):
            plant_actuals[rec.get('plant_code')] = {}
        actuals = rec.get('actuals')
        actuals_forcast = floor(actuals * recipes.get(rec.get('plant_code'),{}).get('S2_mult_rate',1))
        plant_actuals[rec.get('plant_code')].update( {
            "plant_name":rec.get('plant_name'),
            "actuals{}".format(rec.get('year_week')):actuals,
            "actuals_forcast{}{}".format("S2",rec.get('year_week')):actuals_forcast,
            })
    for rec in inventory_previos_weeks:
        if not plant_actuals.get(rec.get('plant_code')):
            plant_actuals[rec.get('plant_code')] = {}
        actuals = rec.get('actuals')
        plant_actuals[rec.get('plant_code')].update( {
            "plant_name":rec.get('plant_name'),
            "actuals_previews":actuals,
            })
    accutals_weeks = []
    # plant_codes = [ x for x in plant_actuals]
    # plant_codes = ['LNAFP','LNAGS']
    ####
    #Calculates all actuals stuff#
    ####
    for x in plant_actuals:
        total = 0
        for t in plant_actuals[x]:
            if t in ('plant_name', 'actuals_previews'):
                continue
            tyear_week = t.strip('actuals')
            if len(plant_actuals[x]) > 1:
                if t not in accutals_weeks and 'previews' not in tyear_week:
                    if t.find('actuals_forcast') < 0:
                        accutals_weeks.append(t)
            if t.find('actuals_forcast') < 0:
                total += plant_actuals[x][t]
        plant_actuals[x].update({'actuals':total})
        media_tray = recipes.get(x,{}).get('media_tray')
        per_container = recipes.get(x,{}).get('per_container')
        plant_actuals[x].update({'container_type':'{}'.format(media_tray)})
        plant_actuals[x].update({'container_qty':'{}'.format(per_container)})
        plant_actuals[x].update({'cut_productivity':recipes.get(x,{}).get('cut_productivity')})
        plant_actuals_sum = plant_actuals[x].get('actuals_previews',0) + total

        plant_actuals[x].update(forcast_actualas(plant_actuals_sum, recipes.get(x,{})))
    accutals_weeks.sort()
    for t in accutals_weeks:
        this_col = deepcopy(actuals_col)
        tyear_week = t.strip('actuals')
        this_col['field'] = t
        this_col['title'] = 'Actuals {}'.format(tyear_week)
        columns_data.append(this_col)
    columns_data.append(forcast_s2)
    columns_data.append(forcast_s3)
    columns_data.append(adjusted_fs2)
    columns_data.append(adjusted_fs3)

    # req_year_week_from = 0
    # req_year_week_to = 0
    # for code in plant_codes:
    #     _req_year_week_from = year_week_from #+ recipes.get(code,{}).get('S3_growth_weeks',8)
    #     _req_year_week_to = year_week_to #+ recipes.get(code,{}).get('S2_growth_weeks',8)
    #     #borrar
    #     # if x == 1:
    #     #     _req_year_week_from = year_week_from + 9
    #     # if x == 2:
    #     #     _req_year_week_to = year_week_to + 11
    #     # end borrar
    #     if not req_year_week_from:
    #         req_year_week_from = _req_year_week_from
    #     if _req_year_week_from and _req_year_week_from < req_year_week_from:
    #         req_year_week_from = _req_year_week_from
    #
    #     if not req_year_week_to:
    #         req_year_week_to = _req_year_week_to
    #     if _req_year_week_to and _req_year_week_to > req_year_week_to:
    #         req_year_week_to = _req_year_week_to
    #
    # print('req_year_week_from', req_year_week_from)
    # print('req_year_week_to', req_year_week_to)
    print('\n\n')
    requierd.update(update_requierd(requierd, requierd_s3, "S3"))
    requierd.update(update_requierd(requierd, requierd_s2, "S2"))
    #todo get actuals Forcast
    # print('columns_data', columns_data)
    print('\n\n')
    # return {'colsData':columns_data, 'tabledata': requierd}
    return {
        'colsData':columns_data,
        'tabledata': set_rows(requierd, plant_actuals, recipes, recipesS3),
        'chartData':chart_data}


if __name__ == "__main__":
    # print(sys.argv)
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    all_data = report_obj.data
    data = all_data.get("data", {})
    year_week_from = int(data.get("year_week_from"))
    year_week_to = int(data.get("year_week_to"))
    test = data.get("test")
    print('data', data)
    if not year_week_to:
        year_week_to = year_week_from
    print('week_from', year_week_from)
    print('week_to', year_week_to)
    print('test', test)
    if year_week_from or year_week_to:
        response = get_week_report(year_week_from, year_week_to)
        if not test:
            sys.stdout.write(simplejson.dumps({"firstElement":response,"secondElement":format_chart()}))
    else:
        sys.stdout.write(simplejson.dumps({"firstElement": {"error":"At least one parameter is needed"}}))
