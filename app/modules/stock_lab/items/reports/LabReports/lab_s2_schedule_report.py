#-*- coding: utf-8 -*-

import simplejson, sys
from copy import deepcopy
from linkaform_api import settings, network, utils
from bson import ObjectId
import time, math
from datetime import datetime, timedelta, date

from stock_report import Reports

from account_settings import *

catalog_plant_recipe = 80754

columns_data = []


added_columns = []

columns_data.append({"title":"Plant Code", "hozAlign":"left", "field":"plant_code", "with":150, "frozen":False, "headerFilter":"input"})
columns_data.append({"title":"Botanical Name", "hozAlign":"left", "field":"plant_name", "with":150, "frozen":False, "headerFilter":"input"})
columns_data.append({"title":"Row Type", "hozAlign":"left", "field":"row_type", "with":150, "frozen":False, "headerFilter":"input"})
columns_data.append({"title":"Total", "hozAlign":"right", "field":"total", "with":150, "frozen":False, "formatter":"money",
    "formatterParams":{
        "decimal":".",
        "thousand":",",
        "symbol":"",
        "symbolAfter":"",
        "precision":0,
    }})


max_cycle = 0
stage_1_min = 10
# colweeks = []from datetime import datetime, timedelta, date

# table_data = []
tabledata = []
req_by_week = {}
cycles = {}
today = date.today()
year_week = int(today.strftime('%Y%W'))
OLDEST_WEEK = year_week
all_due_actuals = {}

# def get_S2_requiers(plant_code):
#     print(st)
#     global req_by_week, cycles
#     match_query = {
#         "deleted_at":{"$exists":False},
#         "form_id":81420,
#         }
#     if plant_code:
#         match_query.update({"answers.6205f7690e752ce25bb30102.61ef32bcdf0ec2ba73dec33d":plant_code,})
#     query = [
#         {"$match": match_query },
#         {"$unwind": "$answers.6226ac11de14768c8527bb3e"},
#         {"$match": {"answers.6226ac11de14768c8527bb3e.6227b17400e5c73fc923b4bd": {"$gte":year_week  }}},
#         {"$project":{
#             "_id":1,
#             'folio':"$folio",
#             "demand":"$answers.620675be271e4456af93b6fb",
#             "demand_plan":"$answers.620675d2496f2e2ba0fca41f",
#             "demand_client":"$answers.62a174dbdcfd3dab21ba50e5",
#             "plant_code":"$answers.6205f7690e752ce25bb30102.61ef32bcdf0ec2ba73dec33d",
#             "plant_name":{ "$arrayElemAt": [ "$answers.6205f7690e752ce25bb30102.61ef32bcdf0ec2ba73dec33e", 0 ] },
#             "year_week":"$answers.6226ac11de14768c8527bb3e.6227b17400e5c73fc923b4bd",
#             "req":"$answers.6226ac11de14768c8527bb3e.6226acece895584f7d0b830c",
#             "starter":"$answers.6226ac11de14768c8527bb3e.6227fd449ac6cd48d296e187",
#         }},
#         {"$project":{
#             "_id":0,
#             'folio':"$folio",
#             'demand':"$demand",
#             'demand_plan':"$demand_plan",
#             'demand_client':"$demand_client",
#             "plant_code":"$plant_code",
#             "plant_name": "$plant_name",
#             "year_week":"$year_week",
#             "req":"$req",
#             # "starter":{"$cond": [{"$and":[{"$lte":["$req",stage_1_min]}, {"$eq":["$starter","yes"]}]},'yes','no']}
#         }},
#         {"$sort": {"year_week": 1}},
#         {"$group":{
#             "_id":{
#                 'folio':"$folio",
#                 'demand':"$demand",
#                 'demand_plan':"$demand_plan",
#                 'demand_client':"$demand_client",
#                 "plant_code":"$plant_code",
#                 # "cycle":"$cycle",
#                 # "starter":"$starter"
#                 },
#             "year_week":{"$min":"$year_week"},
#             "req":{"$min":"$req"}
#         }},
#         {"$project":{
#             "_id":0,
#             "folio":"$_id.folio",
#             "demand":"$_id.demand",
#             "demand_plan":"$_id.demand_plan",
#             "demand_client":"$_id.demand_client",
#             "plant_code":"$_id.plant_code",
#             "year_week":"$year_week",
#             # "starter":"$_id.starter",
#             "req":"$req",
#         }},
#         # {"$project":{
#         #     "_id":0,
#         #     "plant_code":"$plant_code",
#         #     "plant_name": "$plant_name",
#         #     "year_week":"$year_week",
#         #     "req":"$req",
#         #     "starter":{"$cond": [{"$and":[{"$lte":["$req",stage_1_min]}, {"$eq":["$starter","yes"]}]},'yes','no']}
#         # }},
#         # {"$group":{
#         #     "_id":{
#         #         "plant_code":"$plant_code",
#         #         # "cycle":"$cycle",
#         #         "year_week":"$year_week",
#         #         "starter":"$starter"
#         #         },
#         #     "req":{"$sum":"$req"}
#         # }},
#         # {"$project":{
#         #     "_id":0,
#         #     "plant_code":"$_id.plant_code",
#         #     "year_week":"$_id.year_week",
#         #     "starter":"$_id.starter",
#         #     "req":"$req",
#         # }},
#         {"$sort": {"plant_code":1,"year_week": 1}}
#     ]
#     ## TODO:
#     # 1.- acomodar por ciclos, obtener el cylco dependiendo de la semana de cultivo o la semana de arranque
#     cr_result = cr.aggregate(query)
#     result = get_starters(cr_result)
#     setup_plants(result, 'stage2', 'req')
#     return result

def start_plant_code(plant_code):
    global req_by_week
    this_week = deepcopy(int(year_week))
    if plant_code not in req_by_week:
        req_by_week[plant_code] = {
            'recipe':recipes.get(plant_code),
            'oldest_week':this_week,
            'stage1':{'total':0},
            'stage2':{'total':0},
            'stage2_actuals':{'total':0},
            'stage2_forcast':{'total':0},
            'stage2_asigne':{'total':0},
            'stage2_fufilment':{'total':0},
            'stage2_hours':{'total':0},
            'stage3':{'total':0},
            'stage3_asigne':{'total':0},
            'stage3_forcast_all':{'total':0},
            'stage3_forcast_availabe':{'total':0},
            'stage3_fufilment':{'total':0},
            'stage3_hours':{'total':0},
            'stage4_entering':{},
            'stage4_forcast':{'total':0},
            'stage4_harvest':{},
            'stage4_req':{'total':0},
            'stage4_fuf':{'total':0},
            'stage4_hours':{'total':0},
            }

def set_oldest_week(growth_time):
    global  today, OLDEST_WEEK
    until_week = today + timedelta(weeks=growth_time)
    until_week = int(until_week.strftime('%Y%W'))
    if until_week > OLDEST_WEEK:
        OLDEST_WEEK = until_week
    return True

def setup_demand(record, stage):
    res = {}
    if stage == 'stage2':
        res = {
            'demand':record['demand'],
            'demand_plan':record['demand_plan'],
        }
    return res

def setup_plants(result, stage='stage2', req_key='rec', year_key='year_week'):
    global req_by_week, recipesS3, year_week
    total = 0
    for rec in result:
        plant_code = rec['plant_code']
        S2_growth_weeks = recipes[plant_code]['S2_growth_weeks']
        init_week = datetime(today.year, today.month, today.day)
        max_plant_week = init_week + timedelta(weeks=S2_growth_weeks-1)

        yearweek = str(int(rec[year_key]))
        max_plant_week = max_plant_week.strftime('%Y%W')
        if int(yearweek) > int(max_plant_week) and stage != 'stage1':
            continue
        if stage == 'stage3':
            S3_growth_weeks = recipesS3[plant_code]['S3_growth_weeks']
            until_week = init_week + timedelta(weeks=S3_growth_weeks-1)
            # until_week = until_week.strftime('%Y%W')
            init_week = init_week.strftime('%Y%W')
            until_week = OLDEST_WEEK
            if int(yearweek) > int(until_week):
                continue

        if rec.get(req_key,0) <= 10:
            if not req_by_week[plant_code]['stage1'].get(yearweek):
                req_by_week[plant_code]['stage1'][yearweek] = {'demand':[], 'req':0}
                # req_by_week[plant_code]['stage1']['total'] = 0
            req_by_week[plant_code]['stage1'][yearweek]['req'] += rec[req_key]
            req_by_week[plant_code]['stage1'][yearweek]['demand'].append(setup_demand(rec, stage))
            req_by_week[plant_code]['stage1']['total'] += rec[req_key]
            continue
    # for rec in result:
    #     plant_code = rec['plant_code']
    #     week = str(rec[year_key])
    #     if int(week) > req_by_week[plant_code]['oldest_week']:
    #         continue
    #     if rec.get('starter') == 'yes':
    #         continue
    #     if req_by_week[plant_code]['stage1'].get(week):
    #         continue
        if not req_by_week[plant_code][stage].get(yearweek):
            req_by_week[plant_code][stage][yearweek] = {'demand':[], 'req':0}
            # if stage == 'stage3':
            #     print('plant_code', plant_code)
            #     print('stage', stage)
            #     print('yearweek', yearweek)
            # req_by_week[plant_code][stage]['total'] = 0
        req_by_week[plant_code][stage][yearweek]['req'] += rec[req_key]
        req_by_week[plant_code][stage][yearweek]['demand'].append(setup_demand(rec, stage))
        req_by_week[plant_code][stage]['total'] += rec[req_key]
    return True

def setup_plant_actuals(stage, actuals):
    global req_by_week, recipes, recipesS3
    total = {}
    for rec in actuals:
        plant_code = rec.get('plant_code')
        if not total.get(plant_code):
            total[plant_code] = 0
        total[plant_code] += rec.get('actuals',0)
        multi_rate_s2 = recipes.get(plant_code,{}).get('S2_mult_rate',1)
        multi_rate_s3 = recipesS3.get(plant_code,{}).get('S3_mult_rate',1)
        if not plant_code:
            continue
        start_plant_code(plant_code)
        week = rec.get('next_cut')

        if req_by_week[plant_code]['stage2_actuals'].get(str(week),{}).get('req'):
            req_by_week[plant_code]['stage2_actuals'][str(week)]['req'] += rec.get('actuals')
        else:
            req_by_week[plant_code]['stage2_actuals'][str(week)] = {'req': rec.get('actuals'), 'rem':rec.get('actuals')}

        if req_by_week[plant_code]['stage2_forcast'].get(str(week)):
            req_by_week[plant_code]['stage2_forcast'][str(week)] +=  rec.get('actuals') * multi_rate_s2
        else:
            req_by_week[plant_code]['stage2_forcast'][str(week)] =  rec.get('actuals') * multi_rate_s2

        if req_by_week[plant_code]['stage3_forcast_all'].get(str(week)) :
            req_by_week[plant_code]['stage3_forcast_all'][str(week)] += rec.get('actuals') * multi_rate_s3
        else:
            req_by_week[plant_code]['stage3_forcast_all'][str(week)] = rec.get('actuals') * multi_rate_s3

        req_by_week[plant_code]['stage2_forcast']['total'] +=  rec.get('actuals') * multi_rate_s2
        req_by_week[plant_code]['stage3_forcast_all']['total'] += rec.get('actuals') * multi_rate_s3
        req_by_week[plant_code]['stage2_actuals']['total'] = total[plant_code]
        # if plant_code == 'LAGBF':
        #     print('week',week)
        #     print('rem',rec.get('actuals'))
        #     print('req',rec.get('actuals'))
        #     print('req_by_week[plant_code]=',req_by_week[plant_code])
    return True

def add_column(col):
    global added_columns, columns_data
    if col not in added_columns:
        added_columns.append(col)

def insert_cols():
    added_columns.sort()
    for col in added_columns:
        columns_data.append({"title":col, "hozAlign":"right", "field":col, "with":150, "frozen":False, 
            "formatter":"money",
            "formatterParams":{
                "decimal":".",
                "thousand":",",
                "symbol":"",
                "symbolAfter":"",
                "precision":0,
            }
            })

def format_stage(plant_code, stage, row_name):
    global recipes
    plant_name = recipes.get(plant_code,{}).get('plant_name',"N/A")
    res = {'plant_code':plant_code, 'row_type': row_name, 'plant_name':plant_name}
    for col, data in stage.items():
        if col == 'total':
            res[col] = data
        else:
            try:
                res[col] = data.get('req',0)
                add_column(col)
            except AttributeError:
                res[col] = data
                add_column(col)
    return res

def assing_s2(plant_code, requierd, actuals, forcast):
    global req_by_week
    req_weeks = []
    for a in requierd:
        try:
            req_weeks.append(int(a))
        except:
            continue
    req_weeks.sort()
    req_weeks.reverse()
    for tweek in req_weeks:
        req = requierd[str(tweek)].get('req',0)
        act = actuals.get(str(tweek),{}).get('req',0)
        # act = get_stage_original_value('stage2', forcast.get(str(tweek),0))
        # act = forcast.get(str(tweek),0)
        forc = forcast.get(str(tweek),0)
        fufilment = forc - req
        req_ov = get_stage_original_value('stage2', req, plant_code)
        if fufilment > 0:
            req_by_week[plant_code]['stage2_asigne'][str(tweek)] = req
            req_by_week[plant_code]['stage2_asigne']['total'] += req
            # req_by_week[plant_code]['stage2_actuals'][str(tweek)]['rem'] -= req
            req_by_week[plant_code]['stage2_actuals'][str(tweek)]['rem'] -= req_ov
        else:
            req_by_week[plant_code]['stage2_asigne'][str(tweek)] = forc
            req_by_week[plant_code]['stage2_asigne']['total'] += forc
            if not req_by_week[plant_code]['stage2_actuals'].get(str(tweek)):
                req_by_week[plant_code]['stage2_actuals'][str(tweek)] = {'rem': forc *-1}
            req_by_week[plant_code]['stage2_actuals'][str(tweek)]['rem'] -= req_ov
        req_by_week[plant_code]['stage2_fufilment'][str(tweek)] = fufilment
        req_by_week[plant_code]['stage2_fufilment']['total'] += fufilment
    return True

def assing_s3(plant_code, requierd, actuals, forcast):
    global report_obj, req_by_week, recipesS3
    # print('actuals=', actuals)
    req_weeks = []
    for a in requierd:
        try:
            req_weeks.append(int(a))
        except:
            continue
    req_weeks.sort()
    req_weeks.reverse()
    multi_rate = recipesS3.get(plant_code,{}).get('S3_mult_rate',1)
    growth_weeks = recipesS3.get(plant_code,{}).get('S3_growth_weeks',1)
    # plant = Plant(plant_code)
    for tweek in req_weeks:
        req_by_week[plant_code]['stage4_entering'][str(tweek)] = 'w: ' + str(growth_weeks + tweek)
        if not req_by_week[plant_code]['stage2_actuals'].get(str(tweek)):
            req_by_week[plant_code]['stage2_actuals'][str(tweek)] = {'rem':0}
        act_rem = req_by_week[plant_code]['stage2_actuals'][str(tweek)]['rem']
        req = requierd[str(tweek)].get('req',0)
        # act = actuals.get(str(tweek),{}).get('rem',0)
        act = req_by_week[plant_code]['stage2_actuals'][str(tweek)]['rem']
        #act = get_stage_original_value('stage3', forcast.get(str(tweek),0))
        forc = forcast.get(str(tweek),0)
        if act_rem > 0:
            fufilment = (act_rem * multi_rate) - req
        else:
            fufilment = -1 * req

        if fufilment > 0:
            req_by_week[plant_code]['stage3_asigne'][str(tweek)] = req
            req_by_week[plant_code]['stage3_asigne']['total'] += req

            req_by_week[plant_code]['stage3_fufilment'][str(tweek)] =  (act_rem * multi_rate) - req
            req_by_week[plant_code]['stage3_fufilment']['total'] +=  (act_rem * multi_rate) - req

            req = get_stage_original_value('stage3', req, plant_code)
            req_by_week[plant_code]['stage2_actuals'][str(tweek)]['rem'] -= req

            req_by_week[plant_code]['stage3_forcast_availabe'][str(tweek)] = act_rem * multi_rate
            req_by_week[plant_code]['stage3_forcast_availabe']['total'] += act_rem * multi_rate
                # get_stage_present_value(stage='stage2', req_by_week, req, tweek)
            # req_by_week[plant_code]['stage2_forcast'][str(tweek)]['rem'] -= req
        else:
            # req_by_week[plant_code]['stage3_asigne'][str(tweek)] = get_stage_original_value('stage3', req)
            req_by_week[plant_code]['stage3_asigne'][str(tweek)] = 0
            if not req_by_week[plant_code]['stage2_actuals'].get(str(tweek)):
                req_by_week[plant_code]['stage2_actuals'][str(tweek)] = {'rem': act *-1}
            req_by_week[plant_code]['stage2_actuals'][str(tweek)]['rem'] -= act
            req_by_week[plant_code]['stage3_forcast_availabe'][str(tweek)] = 0
            req_by_week[plant_code]['stage3_fufilment'][str(tweek)] = fufilment
            req_by_week[plant_code]['stage3_fufilment']['total'] += fufilment

        #stage4
        s4_plant_week = report_obj.yearweek_int_2_date(tweek) + timedelta(weeks=growth_weeks)
        s4_tweek = s4_plant_week.strftime("%W")


        req_by_week[plant_code]['stage4_entering'][str(tweek)] = s4_plant_week.strftime('%W')
        qty_S4 = req_by_week[plant_code]['stage3_asigne'][str(tweek)]
        s4_recipe = report_obj.select_S4_recipe(recipesS4[plant_code], s4_plant_week.strftime('%W'))
        overage = s4_recipe.get('S4_overage',1)
        multi_rate_S4 = s4_recipe.get('S4_mult_rate',1)
        S4_growth_weeks = s4_recipe.get('S4_growth_weeks',1)
        s4_haverst_week = s4_plant_week + timedelta(weeks=S4_growth_weeks)
        req_by_week[plant_code]['stage4_harvest'][str(tweek)] = s4_haverst_week.strftime('%W')

        req_s4 = report_obj.get_multiplication_inverse(req, multi_rate_S4, overage)
        forcast_s4 = report_obj.get_multiplication_inverse(qty_S4, multi_rate_S4, overage)
        fufill_s4 = forcast_s4 - req_s4

        req_by_week[plant_code]['stage4_req'][str(tweek)] = req_s4
        req_by_week[plant_code]['stage4_req']['total'] += req_s4

        req_by_week[plant_code]['stage4_forcast'][str(tweek)] = forcast_s4
        req_by_week[plant_code]['stage4_forcast']['total'] += forcast_s4

        req_by_week[plant_code]['stage4_fuf'][str(tweek)] =  fufill_s4
        req_by_week[plant_code]['stage4_fuf']['total'] +=  fufill_s4

        # new_date = plant.yearweek_int_2_date(s4_plant_week)
        # plant_recipe = plant.get_week_recipe('Ln72', "S4", new_date)
    return True

def get_stage_original_value(stage, req, plant_code):
    global recipes, recipesS3
    multi_rate = 1
    res = 0
    # act = req_by_week[plant_code]['stage2_actuals'][str(tweek)]['rem']
    if stage == 'stage2':
        multi_rate = recipes.get(plant_code,{}).get('S2_mult_rate',1)
    if stage == 'stage3':
        multi_rate = recipesS3.get(plant_code,{}).get('S3_mult_rate',1)

    res = math.ceil(math.ceil(req) / multi_rate)

    return res

# def get_stage_original_value(stage, req):
#     global recipes, recipesS3
#     multi_rate = 1
#     res = 0
#     # act = req_by_week[plant_code]['stage2_actuals'][str(tweek)]['rem']
#     if stage == 'stage2':
#         multi_rate = recipes.get(plant_code,{}).get('S2_mult_rate',1)
#     if stage == 'stage3':
#         multi_rate = recipesS3.get(plant_code,{}).get('S3_mult_rate',1)
#
#     res = math.ceil(math.ceil(req) / multi_rate)
#     return res

def get_cut_hours(plant_code, data):
    global report_obj, req_by_week, recipes, recipesS3
    productivity_s2 = recipes.get(plant_code,{}).get('cut_productivity',0)
    productivity_s3 = recipesS3.get(plant_code,{}).get('cut_productivity',0)
    if not productivity_s2:
        productivity_s2 = 0
    if not productivity_s3:
        productivity_s3 = 0
    for tweek, plants in data['stage2_asigne'].items():
        if not data['stage2_hours'].get(tweek):
            data['stage2_hours'][tweek] = 0
        if productivity_s2:
            data['stage2_hours'][tweek] = round(plants / productivity_s2,2)
    for tweek, plants in data['stage3_asigne'].items():
        if not data['stage3_hours'].get(tweek):
            data['stage3_hours'][tweek] = 0
        if productivity_s3:
            data['stage3_hours'][tweek] = round(plants / productivity_s3,2)
    for tweek, plants in data['stage4_forcast'].items():
        if tweek =='total':
            continue
        s4_recipe = report_obj.select_S4_recipe(recipesS4[plant_code], str(tweek)[-2:])
        productivity_s4 = s4_recipe.get('cut_productivity',0)
        per_container = s4_recipe.get('per_container',72)
        if not productivity_s4:
            productivity_s4 = 0
        if not data['stage4_hours'].get(tweek):
            data['stage4_hours'][tweek] = 0
        if productivity_s4:
            data['stage4_hours'][tweek] = round(plants / (productivity_s4*per_container),2)
    return True

def format_tabledata():
    global req_by_week
    res = []
    for plant_code, data in req_by_week.items():
        assing_s2(plant_code, data['stage2'], data['stage2_actuals'], data['stage2_forcast'] )
        assing_s3(plant_code, data['stage3'],  data['stage2_actuals'], data['stage3_forcast_all'])
        get_cut_hours(plant_code, data)
        # print('stage3_forcast_availabe',data['stage4_fuf'])
        res.append(format_stage(plant_code, data['stage4_harvest'], 'Stage 4 Harvest Week'))
        res.append(format_stage(plant_code, data['stage4_req'], 'Stage 4 Required'))
        res.append(format_stage(plant_code, data['stage4_forcast'], 'Stage 4 Forcast'))
        res.append(format_stage(plant_code, data['stage4_fuf'], 'Stage 4 Fulfillment'))
        res.append(format_stage(plant_code, data['stage4_hours'], 'Stage4 Work Hours'))
        res.append(format_stage(plant_code, data['stage4_entering'], 'Stage 4 Planting Week'))
        res.append(format_stage(plant_code, data['stage3'], 'Stage3 Required'))
        res.append(format_stage(plant_code, data['stage3_forcast_all'], 'Stage3 Forcast All Actuals'))
        res.append(format_stage(plant_code, data['stage3_forcast_availabe'], 'Stage3 Forcast Avalable'))
        res.append(format_stage(plant_code, data['stage3_asigne'], 'Stage3 Can Asigne'))
        res.append(format_stage(plant_code, data['stage3_hours'], 'Stage3 Work Hours'))
        res.append(format_stage(plant_code, data['stage3_fufilment'], 'Stage3 Fulfillment'))
        res.append(format_stage(plant_code, data['stage2'], 'Stage2 Required'))
        res.append(format_stage(plant_code, data['stage2_actuals'], 'Stage2 Actuals'))
        res.append(format_stage(plant_code, data['stage2_forcast'], 'Stage2 Forcast'))
        res.append(format_stage(plant_code, data['stage2_asigne'], 'Stage2 Can Asigne'))
        res.append(format_stage(plant_code, data['stage2_hours'], 'Stage2 Work Hours'))
        res.append(format_stage(plant_code, data['stage2_fufilment'], 'Stage2 Fulfillment'))
        res.append(format_stage(plant_code, data['stage1'], 'Stage1 Required'))
    insert_cols()
    return res


class Reports(Reports):

    def get_S2_requiers(self, plant_code):
        global req_by_week, cycles
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.PRODUCTION_PLAN,
            }
        if plant_code:
            match_query.update({f"answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}":plant_code,})
        query = [
            {"$match": match_query },
            {"$unwind": f"$answers.{self.f['prod_plan_development_group']}"},
            {"$match": {f"answers.{self.f['prod_plan_development_group']}.{self.f['prod_plan_S2_requier_yearweek']}": {"$gte":year_week  }}},
            {"$project":{
                "_id":1,
                'folio':"$folio",
                "demand":f"$answers.{self.f['prod_plan_ready_date']}",
                "demand_plan":f"$answers.{self.f['prod_plan_demand_plan']}",
                "demand_client":f"$answers.{self.f['prod_plan_demand_client']}",
                "plant_code":f"$answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}",
                "plant_name":{ "$arrayElemAt": [ f"$answers.{self.PRODUCT_OBJ_ID}.{self.f['product_name']}", 0 ] },
                "year_week":f"$answers.{self.f['prod_plan_development_group']}.{self.f['prod_plan_S2_requier_yearweek']}",
                "req":f"$answers.{self.f['prod_plan_development_group']}.{self.f['prod_plan_require_S2']}",
                "starter":f"$answers.{self.f['prod_plan_development_group']}.{self.f['prod_plan_starter']}",
            }},
            {"$project":{
                "_id":0,
                'folio':"$folio",
                'demand':"$demand",
                'demand_plan':"$demand_plan",
                'demand_client':"$demand_client",
                "plant_code":"$plant_code",
                "plant_name": "$plant_name",
                "year_week":"$year_week",
                "req":"$req",
                # "starter":{"$cond": [{"$and":[{"$lte":["$req",stage_1_min]}, {"$eq":["$starter","yes"]}]},'yes','no']}
            }},
            {"$sort": {"year_week": 1}},
            {"$group":{
                "_id":{
                    'folio':"$folio",
                    'demand':"$demand",
                    'demand_plan':"$demand_plan",
                    'demand_client':"$demand_client",
                    "plant_code":"$plant_code",
                    # "cycle":"$cycle",
                    # "starter":"$starter"
                    },
                "year_week":{"$min":"$year_week"},
                "req":{"$min":"$req"}
            }},
            {"$project":{
                "_id":0,
                "folio":"$_id.folio",
                "demand":"$_id.demand",
                "demand_plan":"$_id.demand_plan",
                "demand_client":"$_id.demand_client",
                "plant_code":"$_id.plant_code",
                "year_week":"$year_week",
                # "starter":"$_id.starter",
                "req":"$req",
            }},
            # {"$project":{
            #     "_id":0,
            #     "plant_code":"$plant_code",
            #     "plant_name": "$plant_name",
            #     "year_week":"$year_week",
            #     "req":"$req",
            #     "starter":{"$cond": [{"$and":[{"$lte":["$req",stage_1_min]}, {"$eq":["$starter","yes"]}]},'yes','no']}
            # }},
            # {"$group":{
            #     "_id":{
            #         "plant_code":"$plant_code",
            #         # "cycle":"$cycle",
            #         "year_week":"$year_week",
            #         "starter":"$starter"
            #         },
            #     "req":{"$sum":"$req"}
            # }},
            # {"$project":{
            #     "_id":0,
            #     "plant_code":"$_id.plant_code",
            #     "year_week":"$_id.year_week",
            #     "starter":"$_id.starter",
            #     "req":"$req",
            # }},
            {"$sort": {"plant_code":1,"year_week": 1}}
        ]
        ## TODO:
        # 1.- acomodar por ciclos, obtener el cylco dependiendo de la semana de cultivo o la semana de arranque
        cr_result = self.cr.aggregate(query)

        result = self.get_starters(cr_result)
        setup_plants(result, 'stage2', 'req')
        return query

    def get_starters(self, cr_result):
        global year_week, req_by_week, OLDEST_WEEK, recipes, cycles
        result = []
        for dem in cr_result:
            yearweek = dem.get('year_week')
            result.append(dem)
            plant_code = dem['plant_code']
            if not plant_code:
                continue
            start_plant_code(plant_code)
            # req_by_week[plant_code]['develop'].append(dem)
            growth_time = recipes[plant_code]['S2_growth_weeks']
            if growth_time not in cycles:
                cycles[growth_time] = {}
            if yearweek not in cycles[growth_time]:
                cycles[growth_time][yearweek] = self.get_cycle_group(yearweek, growth_time)
            dem['cycle'] = cycles[growth_time][yearweek]
            set_oldest_week(growth_time)
            #TODO BORRAR ESTA FUNCION Y TODO OLDESWEEK
        return result

    def query_report_actuals(self, plant_code):
        global year_week
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.FORM_INVENTORY_ID,
            f"answers.{self.f['inventory_status']}":"active",
            f"answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}":'S2',
            }
        match_query.update({f"answers.{self.f['new_cutweek']}": {"$gte":year_week }})
        if plant_code:
            match_query.update({f"answers.{self.SKU_OBJ_ID}.{self.f['product_code']}":plant_code})
        query = [
            {"$match": match_query },
            {"$project":{
                "_id":1,
                "plant_code":f"$answers.{self.SKU_OBJ_ID}.{self.f['product_code']}",
                "cycle":f"$answers.{self.f['plant_cycle']}",
                "next_cut":f"$answers.{self.f['new_cutweek']}",
                "actuals":f"$answers.{self.f['actual_eaches_on_hand']}",
            }},
            {"$group":{
                "_id":{
                    "plant_code":"$plant_code",
                    "cycle":"$cycle",
                    "next_cut":"$next_cut",
                    },
                "actuals":{"$sum":"$actuals"}
            }},
            {"$project":{
                "_id":0,
                "plant_code":"$_id.plant_code",
                "cycle":"$_id.cycle",
                "next_cut":  { "$toInt": "$_id.next_cut"},
                "actuals":"$actuals",
            }},
            {"$sort": {"cycle": 1}}
        ]
        result = self.cr.aggregate(query)
        res = []
        # for r in result:
        #     print('r',r)
        #     res.append(r)
        # return res
        return [r for r in result]
 
    def query_report_due_actuals(self, plant_code):
        global year_week
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.FORM_INVENTORY_ID,
            f"answers.{self.f['inventory_status']}":"active",
            f"answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}":'S2',
            }
        match_query.update({f"answers.{self.f['new_cutweek']}": {"$lt": year_week }})
        if plant_code:
            match_query.update({f"answers.{self.SKU_OBJ_ID}.{self.f['product_code']}":plant_code})
        query = [
            {"$match": match_query },
            {"$project":{
                "_id":1,
                "plant_code":f"$answers.{self.SKU_OBJ_ID}.{self.f['product_code']}",
                "actuals":f"$answers.{self.f['actual_eaches_on_hand']}",
            }},
            {"$group":{
                "_id":{
                    "plant_code":"$plant_code",
                    },
                "actuals":{"$sum":"$actuals"}
            }},
            {"$project":{
                "_id":0,
                "plant_code":"$_id.plant_code",
                "actuals":"$actuals",
            }},
        ]
        result = self.cr.aggregate(query)
        return [r for r in result]


def get_report(all_plant_code):
    global report_obj, year_week, cycles, recipes, all_due_actuals
    # print('recipes', recipes)
    report_obj.get_S2_requiers(all_plant_code)
    all_actuals = report_obj.query_report_actuals(all_plant_code)
    # #####
    if not all_due_actuals.get(all_plant_code):
        # print('plant_code',all_plant_code)
        due_actuals = report_obj.query_report_due_actuals(all_plant_code)
        # print('due_actuals',due_actuals)
        if type(due_actuals) == dict:
            due_actuals = [due_actuals,]
        for due_rec in due_actuals:
            # print('due_rec', due_rec)
            plant_code = due_rec.get('plant_code')
            try:
                gweeks = recipes[plant_code]['S2_growth_weeks']
            except KeyError:
                gweeks = 8
            if cycles:
                this_plant_cycle = cycles[gweeks][year_week]
            else:
                this_plant_cycle = 8
            if due_rec:
                # due_actuals =  due_actuals[0]
                due_rec['cycle'] = this_plant_cycle
                due_rec['next_cut'] = int(year_week)
                due_rec['plant_code'] = plant_code
                due_rec['add_due'] = False
                all_due_actuals[plant_code] = due_rec
                # print('all_due_actuals',all_due_actuals)

    for idx, actuals in enumerate(all_actuals):
        # print('actuals=', actuals)
        plant_code = actuals.get('plant_code')
        if not recipes.get(plant_code):
            all_actuals.pop(idx)
            continue
        gweeks = recipes[plant_code]['S2_growth_weeks']
        if cycles:
            this_plant_cycle = cycles[gweeks].get(year_week,0)
        else:
            this_plant_cycle = 8

        if actuals['cycle'] == this_plant_cycle:
            if all_due_actuals.get(plant_code) and not all_due_actuals[plant_code].get('add_due'):
                actuals['actuals'] += all_due_actuals[plant_code]['actuals']
                all_due_actuals[plant_code] = {'add_due':True}

    for plant_code, due_actulas in all_due_actuals.items():
        if not due_actulas.get('add_due'):
            all_actuals.append(due_actulas)

    setup_plant_actuals('stage2', all_actuals)

    results3 = report_obj.get_S3_requiers(all_plant_code, year_week,  OLDEST_WEEK)
    for x in results3:
        print('x=',x)
        if x.get('plant_code') == 'LAGBF':
            print(x)
    setup_plants(results3, 'stage3', 'requierd_S3','year_week_S3')
    return format_tabledata()

if __name__ == "__main__":
    # print(sys.argv)
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    all_data = report_obj.data
    # all_data = simplejson.loads(sys.argv[2])
    data = all_data.get("data", {})
    plant_code = data.get("plant_code",[])
    test = data.get("test",[])
    extra_weeks = data.get("extra_weeks",0)
    if type(plant_code) == str:
        plant_code = plant_code.upper()
    # plant_code = all_data.get("plant_code")
    # print('data', plant_code)
    # report_model = ReportModel()
    #try:
    if True:
        #jwt_complete = simplejson.loads(sys.argv[2])
        #config["USER_JWT_KEY"] = jwt_complete
        #settings.config.update(config)
        recipes = report_obj.get_plant_recipe(plant_code, stage=[2,])
        recipesS3 = report_obj.get_plant_recipe(plant_code, stage=[3,])
        recipesS4 = report_obj.get_plant_recipe(plant_code, stage=[4,'Ln72'])
        # recipesS4 = get_plant_recipe(plant_code, stage=[3,])
        response = get_report(plant_code)
        # print('res', response)
        # query_report_second(date_from, date_to )
        # query_report_fourth(date_from, date_to )


        if not test:
            sys.stdout.write(simplejson.dumps(
                {"firstElement":{
                    'tabledata':response, 'colsData':columns_data
                    }
                }
                )
            )
    # except:
    #     sys.stdout.write(simplejson.dumps({"firstElement": {"error":"Something went wrong"}}))
