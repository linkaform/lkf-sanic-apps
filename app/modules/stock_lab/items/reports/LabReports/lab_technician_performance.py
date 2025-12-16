#-*- coding: utf-8 -*-

import simplejson, sys
from linkaform_api import settings, network, utils
from bson import ObjectId
import time, copy
from datetime import datetime, timedelta, date

from stock_report import Reports

from account_settings import *

BG_COLORS = {'Stage 2':'#5677fc','Stage 3':'#81C784'}

class Reports(Reports):
        
    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.json = {
                    "firstElement":{
                        'tabledata':[]
                    },
                    "secondElement":{},
                    "thirdElement":{},
                    "fourthElement":{
                        'tabledata':[]
                    },
                    "fivethElement":{
                        'tabledata':[]
                    },
                    "sixthElement":{},
                    "seventhElement":{
                        'tabledata':[]
                    },
                    "eighthElement":{},
                    "ninthElement":{},
                    "tenthElement":{},
                    "eleventhElement":{
                        'tabledata':[]
                    },
                }

    def get_productivity(self, yearweek_form, yearweek_to, plant_code, stage):
        res = []
        # productivity_lab = self.get_plants_per_hr(yearweek_form, yearweek_to, plant_code, stage, by_team=False)
        # productivity_lab += self.get_plants_per_hr(yearweek_form, yearweek_to, plant_code, stage)
        prod_stage = self.get_plants_per_hr_by_stage(yearweek_form, yearweek_to, plant_code, stage)

        prod_stage, prod_stage_char = arrage_stage(prod_stage)
        # print('prod_stage_char=' ,prod_stage_chard)
        ###
        # print('1- prod_stage',prod_stage)
        # print('2- prod_stage_char',prod_stage_char)
        prod_code = self.get_plants_per_hr_by_plant(yearweek_form, yearweek_to, plant_code, stage, sort_by={'plants_per_hr':-1})

        ## Por Codigo
        prod_code_char = arrage_stage_plants(prod_code)
        # print('3- prod_code_char',prod_code_char)
        ##
        prod_code_team = self.get_plants_per_hr_by_plant_team(yearweek_form, yearweek_to, plant_code, stage)
        plant_team_table = arrage_tems(prod_code, prod_code_team)
        # print('4- plant_team_table',plant_team_table)
        ##
        prod_code_cutter = self.get_plants_per_hr_by_plant_cutter(yearweek_form, yearweek_to, plant_code, stage, group='cutter')
        prod_code_cutter_plant = self.get_plants_per_hr_by_plant_cutter(yearweek_form, yearweek_to, plant_code, stage, group='plant')
        # print('prod_code_cutter_plant',prod_code_cutter_plant )
        plant_cutter_table = arrage_plant_cutter(prod_code, prod_code_cutter_plant)
        cutter_plant_table = arrage_cutter_plant(prod_code_cutter, prod_code_cutter_plant)
        cutter_plant_char = arrage_cutter_plant_chart(prod_code_cutter)
        # print('5- plant_cutter_table',plant_cutter_table)
        # print('6. cutter_plant_char',cutter_plant_char)
        ## hours
        # print('4- prod_code_team',prod_code_team)
        team_hour_chart, plant_hour_chart = arrage_hours_team(prod_code_team)
        # print('8. team_hour_chart',team_hour_chart)
        # print('9. plant_hour_chart',plant_hour_chart)
        cutter_hours_chart = arrage_hours_cutter(prod_code_cutter_plant)
        # print('10.cuter_hour_chart',cutter_hours_chart)
        cutter_hours_table = table_hours_cutter(cutter_hours_chart)
        # print('11. plant_hour_chart',cutter_hours_table)

        #---Asign
        self.json['firstElement']['tabledata'] = prod_stage
        self.json['secondElement'] = prod_stage_char
        self.json['thirdElement'] = prod_code_char
        self.json['fourthElement']['tabledata'] = plant_team_table
        self.json['fivethElement']['tabledata'] = plant_cutter_table
        self.json['sixthElement'] = cutter_plant_char
        self.json['seventhElement']['tabledata'] = cutter_plant_table
        self.json['eighthElement'] = team_hour_chart
        self.json['ninthElement'] = plant_hour_chart
        self.json['tenthElement'] = cutter_hours_chart
        self.json['eleventhElement']['tabledata'] = cutter_hours_table
        # return prod_stage

    def get_plants_per_hr(self, yearweek_form, yearweek_to, plant_code, stage, by_team=True):
        aggregate = self.get_productivity_base(yearweek_form, yearweek_to, plant_code, stage)
        if by_team:
            group = '$team'
        else:
            group = 'Company'
        group_by ={'$group':
                    {
                        '_id':
                        {
                            'team': group,
                          },
                        'total_plants': {'$sum': '$total_plants'},
                        'total_hours': {'$sum': '$total_hours'},
                    }
                }
        project = {'$project':{
                    '_id':0,
                    'team':'$_id.team',
                    'plants_per_hr':{'$divide':['$total_plants','$total_hours']}
            }
        }
        sort = {'$sort':{'team':1} }
        aggregate.append(group_by)
        aggregate.append(project)
        aggregate.append(sort)
        res = self.cr.aggregate(aggregate)
        result = []
        for r in res:
            r['plants_per_hr'] = '{} pl/hr'.format(int(r['plants_per_hr']))
            result.append(r)
        return result

    def get_plants_per_hr_by_stage(self, yearweek_form, yearweek_to, plant_code, stage):
        aggregate = self.get_productivity_base(yearweek_form, yearweek_to, plant_code, stage)
        group_by ={'$group':
                    {
                        '_id':
                        {
                            'team': '$team',
                            'stage': '$stage',
                          },
                        'total_plants': {'$sum': '$total_plants'},
                        'total_hours': {'$sum': '$total_hours'},                }
                }
        project = {'$project':{
                    '_id':0,
                    'team':'$_id.team',
                    'stage':'$_id.stage',
                    'plants_per_hr':{'$divide':['$total_plants','$total_hours']}
            }
        }
        sort = {'$sort':{'team':1,'stage':1 } }

        aggregate.append(group_by)
        aggregate.append(project)
        aggregate.append(sort)
        res = self.cr.aggregate(aggregate)
        result = []
        for r in res:
            r['plants'] = int(r['plants_per_hr'])
            r['plants_per_hr'] = '{} pl/hr'.format(int(r['plants_per_hr']))
            if r['stage'] == 'S2':
                r['stage'] = 'Stage 2'
            elif r['stage'] == 'S3':
                r['stage'] = 'Stage 3'
            result.append(r)
        return result

    def get_plants_per_hr_by_plant(self, yearweek_form, yearweek_to, plant_code, stage, sort_by={'plant_code':1} ):
        aggregate = self.get_productivity_base(yearweek_form, yearweek_to, plant_code, stage)
        group_by ={'$group':
                    {
                        '_id':
                        {
                            'plant_code': '$plant_code',
                          },
                        'total_plants': {'$sum': '$total_plants'},
                        'total_hours': {'$sum': '$total_hours'},                 }
                }
        project = {'$project':{
                    '_id':0,
                    'plant_code':'$_id.plant_code',
                    'total_hours':'$total_hours',
                    'plants_per_hr':{'$divide':['$total_plants','$total_hours']}
            }
        }
        sort = {'$sort':sort_by }
        aggregate.append(group_by)
        aggregate.append(project)
        aggregate.append(sort)
        res = self.cr.aggregate(aggregate)
        result = []
        for r in res:
            result.append(r)
        return result

    def get_plants_per_hr_by_plant_team(self, yearweek_form, yearweek_to, plant_code, stage):
        aggregate = self.get_productivity_base(yearweek_form, yearweek_to, plant_code, stage)
        group_by ={'$group':
                    {
                        '_id':
                        {
                            'team': '$team',
                            'plant_code': '$plant_code',
                          },
                        'total_plants': {'$sum': '$total_plants'},
                        'total_hours': {'$sum': '$total_hours'},                   }
                }
        project = {'$project':{
                    '_id':0,
                    'team':'$_id.team',
                    'plant_code':'$_id.plant_code',
                    'total_hours':'$total_hours',
                    'plants_per_hr':{'$divide':['$total_plants','$total_hours']}
            }
        }
        aggregate.append(group_by)
        aggregate.append(project)
        res = self.cr.aggregate(aggregate)
        result = []
        for r in res:
            result.append(r)
        return result

    def get_plants_per_hr_by_plant_cutter(self, yearweek_form, yearweek_to, plant_code, stage, group='cutter'):
        aggregate = self.get_productivity_base(yearweek_form, yearweek_to, plant_code, stage)
        if group == 'cutter':
            group_by ={'$group':
                        {
                            '_id':
                            {
                                'cutter': '$cutter',
                              },
                            'total_plants': {'$sum': '$total_plants'},
                            'total_hours': {'$sum': '$total_hours'},                   }
                    }
            project = {'$project':{
                        '_id':0,
                        'cutter':'$_id.cutter',
                        'total_hours':'$total_hours',
                        'plants_per_hr':{'$divide':['$total_plants','$total_hours']}
                }
            }

        if group == 'plant':
            group_by ={'$group':
                        {
                            '_id':
                            {
                                'cutter': '$cutter',
                                'plant_code': '$plant_code',
                              },
                            'total_plants': {'$sum': '$total_plants'},
                            'total_hours': {'$sum': '$total_hours'},                   }
                    }
            project = {'$project':{
                        '_id':0,
                        'cutter':'$_id.cutter',
                        'plant_code':'$_id.plant_code',
                        'total_plants':'$total_plants',
                        'total_hours':'$total_hours',
                        # 'plants_per_hr':{'$divide':['$total_plants','$total_hours']}
                }
            }
        sort = {'$sort':{'plants_per_hr': -1 } }
        aggregate.append(group_by)
        aggregate.append(project)
        aggregate.append(sort)
        res = self.cr.aggregate(aggregate)
        result = []
        for r in res:
            result.append(r)
        return result

    def get_productivity_base(self, yearweek_form, yearweek_to, plant_code, stage):
        year_from = False
        year_to = False
        week_from = False
        week_to = False
        aggregate = []
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.PRODUCTION_FORM_ID,
            }
        if plant_code:
            match_query.update({f"answers.{self.SKU_OBJ_ID}.{self.f['product_code']}":plant_code})
        if stage:
            match_query.update({f"$answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}":stage})
        if yearweek_form:
            year_form = int(yearweek_form[:4])
        if yearweek_to:
            year_to = int(yearweek_to[:4])
        if yearweek_form:
            week_form = int(yearweek_form[-2:])
        if yearweek_to:
            week_to = int(yearweek_to[-2:])
        # match_query.update(get_date_query(year_form, year_to, date_field_id='61f1da41b112fe4e7fe8582f'))
        # match_query.update(get_date_query(week_form, week_to, date_field_id='62e8343e236c89c216a7cec3'))
        aggregate.append({'$match': match_query })
        aggregate.append({'$unwind': f"$answers.{self.f['production_group']}" })
        match_query_2 = {'$match':{f"answers.{self.f['production_group']}.{self.f['production_status']}":'posted'}}
        match_query_2['$match'].update(self.get_date_query(yearweek_form, yearweek_to, date_field_id=f"{self.f['production_group']}.{self.f['set_production_date']}"))
        aggregate.append(match_query_2)
        project = {'$project':{
            '_id':1,
            'stage':f"$answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}",
            'team':f"$answers.{self.TEAM_OBJ_ID}.{self.f['team_name']}",
            'plant_code':f"$answers.{self.SKU_OBJ_ID}.{self.f['product_code']}",
            'total_hours':f"$answers.{self.f['production_group']}.{self.f['set_total_hours']}",
            'plants_per_hr':f"$answers.{self.f['production_group']}.{self.f['set_products_per_hours']}",
            'time_in':f"$answers.{self.f['production_group']}.{self.f['time_in']}",
            'time_out':f"$answers.{self.f['production_group']}.{self.f['time_out']}",
            'multiplication_rate':f"$answers.{self.f['production_group']}.{self.f['production_multiplication_rate']}",
            'cutter':f"$answers.{self.f['production_group']}.{self.EMPLOYEE_OBJ_ID}.{self.f['worker_name']}",
            'total_plants':{'$multiply': [
                f"$answers.{self.f['production_group']}.{self.f['set_total_hours']}", #total hrs
                f"$answers.{self.f['production_group']}.{self.f['set_products_per_hours']}" #plants per hour
                ]
                }
            }
        }
        aggregate.append(project)
        return aggregate



def arrage_stage(prod_stage):
    char = {'labels':[], 'datasets':[]}
    res_by_stage = {'Stage 2':{'total':0},'Stage 3':{'total':0}}
    res = []
    for stage in res_by_stage.keys():
        for idx, team in enumerate(prod_stage):
            if team.get('stage') == stage:
                team_name = team['team'].replace(' ','_').lower()
                if team['team'] not in char['labels']:
                    char['labels'].append(team['team'])
                total = res_by_stage[stage]['total']
                total += team['plants']
                res_by_stage[stage].update({team_name:team['plants_per_hr'], 'total':total})
    for key, value in res_by_stage.items():
        x = copy.deepcopy(value)
        data = []
        for z in list(value.values()):
            if type(z) == str and 'pl/hr' in z:
                data.append(int(z.strip(' pl/hr')))
        char['datasets'].append({'label':key, 'data':data, 'backgroundColor':BG_COLORS.get(key,'#7C4DFF')})
        divide_qty = len(value) -1
        if divide_qty <= 0 :
            divide_qty = 1
        x.update({'stage':key, 'magnolia': '{} pl/hr'.format(int(value['total']/divide_qty)) })
        res.append(x)
    return res, char

def arrage_stage_plants(prod_code):
    char = {'labels':[], 'datasets':[]}
    data = []
    for plant in prod_code:
        char['labels'].append(plant['plant_code'])
        data.append(int(plant['plants_per_hr']))
    char['datasets'].append({'label':'Produced','data':data, 'backgroundColor':BG_COLORS.get('none','#7C4DFF')})
    return char

def arrage_plant_chart(prod_code):
    char = {'labels':[], 'datasets':[]}
    data = []
    for plant in prod_code:
        char['labels'].append(plant['cutter'])
        data.append(int(plant['plants_per_hr']))
    char['datasets'].append({'label':'Cutter','data':data, 'backgroundColor':BG_COLORS.get('none','#7C4DFF')})
    return char

def arrage_tems(prod_code, prod_code_team):

    by_plant_dict = {}
    for plant in prod_code:
        pcode = plant.get('plant_code')
        by_plant_dict[pcode] = by_plant_dict.get(pcode, {'value_plant':pcode,'_children':[]})
        by_plant_dict[pcode]['value_cut'] = '{} pl/hr'.format(int(plant['plants_per_hr']))
    for plant in prod_code_team:
        pcode = plant.get('plant_code')
        by_plant_dict[pcode]['_children'].append({
            'value_plant':plant['team'],
            'value_cut': '{} pl/hr'.format(int(plant['plants_per_hr']))
            })
    res = []
    for key, values in by_plant_dict.items():
        values.update({'value_plant':key})
        res.append(values)
    return res

def arrage_plant_cutter(prod_code, prod_code_cutter):
    by_plant_dict = {}
    for plant in prod_code:
        pcode = plant.get('plant_code')
        by_plant_dict[pcode] = by_plant_dict.get(pcode, {'value_plant':pcode,'_children':[]})
        by_plant_dict[pcode]['value_cut'] = '{} pl/hr'.format(int(plant['plants_per_hr']))
    for plant in prod_code_cutter:
        pcode = plant.get('plant_code')
        if plant['total_hours'] == 0 or  plant['total_plants'] == 0:
            continue
        plants_per_hr =  plant['total_plants']/plant['total_hours']
        by_plant_dict[pcode]['_children'].append({
            'value_plant':plant['cutter'],
            'value_cut': '{} pl/hr'.format(int(plants_per_hr))
            })
    res = []
    for key, values in by_plant_dict.items():
        values.update({'value_plant':key})
        res.append(values)
    return res

def arrage_cutter_plant(prod_code, prod_code_cutter):
    by_plant_dict = {}
    for plant in prod_code:
        cutter = plant.get('cutter')
        by_plant_dict[cutter] = by_plant_dict.get(cutter, {'value_plant':cutter,'_children':[]})
        by_plant_dict[cutter]['value_cut'] = '{} pl/hr'.format(int(plant['plants_per_hr']))
    for plant in prod_code_cutter:
        cutter = plant.get('cutter')
        if plant['total_hours'] == 0 or  plant['total_plants'] == 0:
            continue
        plants_per_hr =  plant['total_plants']/plant['total_hours']
        by_plant_dict[cutter]['_children'].append({
            'value_plant':plant['plant_code'],
            'value_cut': '{} pl/hr'.format(int(plants_per_hr))
            })
    res = []
    for key, values in by_plant_dict.items():
        values.update({'value_plant':key})
        res.append(values)
    return res

def arrage_cutter_plant_chart(prod_code):
    char = {'labels':[], 'datasets':[]}
    data = []
    for plant in prod_code:
        char['labels'].append(plant['cutter'])
        data.append(int(plant['plants_per_hr']))
    char['datasets'].append({'label':'Cutter','data':data, 'backgroundColor':BG_COLORS.get('none','#7C4DFF')})
    return char

def arrage_hours_team(data):
    hteam_dir = {}
    hplant_dir = {}
    char = {'labels':[], 'datasets':[]}
    char_pl = {'labels':[], 'datasets':[]}
    for rec in data:
        team = rec['team']
        pcode = rec['plant_code']
        total = rec['total_hours']
        hteam_dir[team] = hteam_dir.get(team, 0)
        hteam_dir[team] += total
        hplant_dir[pcode] = hplant_dir.get(pcode, 0)
        hplant_dir[pcode] += total
    data = []
    hteam_sorted = sorted(hteam_dir.items(), key=lambda x:x[1], reverse=True)
    for vals in hteam_sorted:
        team  = vals[0]
        hours = vals[1]
        char['labels'].append(team)
        data.append(int(hours))
    char['datasets'].append({'label':'Hours by Team','data':data, 'backgroundColor':BG_COLORS.get('none','#7C4DFF')})

    data = []
    hplant_sorted = sorted(hplant_dir.items(), key=lambda x:x[1], reverse=True)
    for vals in hplant_sorted:
        pcode  = vals[0]
        hours = vals[1]
        char_pl['labels'].append(pcode)
        data.append(int(hours))
    # print('hplant_dir=',hplant_dir)
    char_pl['datasets'].append({'label':'Hours by Plant','data':data, 'backgroundColor':BG_COLORS.get('none','#7C4DFF')})
    return char, char_pl

def arrage_hours_cutter(prod_code):
    hcutter_dir = {}
    char = {'labels':[], 'datasets':[]}
    char_pl = {'labels':[], 'datasets':[]}
    for rec in prod_code:
        cutter = rec['cutter']
        pcode = rec['plant_code']
        total = rec['total_hours']
        hcutter_dir[cutter] = hcutter_dir.get(cutter, 0)
        hcutter_dir[cutter] += total
    data = []
    data = []
    hcutter_sorted = sorted(hcutter_dir.items(), key=lambda x:x[1], reverse=True)
    for vals in hcutter_sorted:
        cutter  = vals[0]
        hours = vals[1]
        char['labels'].append(cutter)
        data.append(int(hours))
    char['datasets'].append({'label':'Hours by Team','data':data, 'backgroundColor':BG_COLORS.get('none','#7C4DFF')})

    return char

def table_hours_cutter(data):
    dic_data = []
    count = 0
    for x in range(len(data['labels'])):
        name_cutter = data['labels'][count]
        hours_cutter = data['datasets'][0]['data'][count]
        count += 1
        dic_data.append({
            "cutter":name_cutter,
            "work_hours" : hours_cutter,
        })
    return dic_data

if __name__ == "__main__":
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    all_data = report_obj.data
    data = all_data.get("data", {})
    plant_code = data.get("plant_code")
    stage = data.get("stage")
    test = data.get("test",[])
    if stage == "":
        stage = None
    if stage =='stage2' or stage == 'stage_2' or stage == '2':
        stage = 'S2'
    if stage =='stage3' or stage == 'stage_3' or stage == '3':
        stage = 'S3'
    date_from = data.get("date_from")
    date_to = data.get("date_to")

    yearweek_form = date_from
    yearweek_to = date_to
    try:
        ####
        productivity = report_obj.get_productivity(yearweek_form, yearweek_to, plant_code, stage)
        sys.stdout.write(simplejson.dumps(report_obj.report_print()))

    except:
        sys.stdout.write(simplejson.dumps({"firstElement": {"error":"Something went wrong"}}))
