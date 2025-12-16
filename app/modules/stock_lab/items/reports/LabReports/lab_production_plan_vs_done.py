#-*- coding: utf-8 -*-

import simplejson, sys
from copy import deepcopy
from linkaform_api import settings
from bson import ObjectId
import time
from datetime import datetime, timedelta, date

from stock_report import Reports

from account_settings import *


table_data = []
plants = {}
WEEKS = []






def arrange_info(planned, produced):
    total_planned = 0
    total_planned_s2 = 0
    total_planned_s3 = 0
    total_produced = 0
    total_produced_s2 = 0
    total_produced_s3 = 0
    teams = {}
    for x in planned:
        team = x['team']
        total_planned += x.get('total')
        teams[team] = teams.get(team,{'range':0,'value':0,'stage2':{'range':0, 'value':0}, 'stage3':{'range':0, 'value':0}})
        teams[team]['range'] += x.get('total')
        if x['stage'] == 'S2':
            total_planned_s2 += x.get('total')
            teams[team]['stage2']['range'] += x.get('total')
        if x['stage'] == 'S3':
            total_planned_s3 += x.get('total')
            teams[team]['stage3']['range'] += x.get('total')
    for x in produced:
        team = x['team']
        total_produced += x.get('total')
        teams[team] = teams.get(team, {'range':0,'value':0,'stage2':{'range':0, 'value':0}, 'stage3':{'range':0, 'value':0}})
        teams[team]['value'] += x.get('total')
        if x['stage'] == '2' or x['stage'] == 2:
            total_produced_s2 += x.get('total')
            teams[team]['stage2']['value'] += x.get('total')
        if x['stage'] == '3' or x['stage'] == 3:
            total_produced_s3 += x.get('total')
            teams[team]['stage3']['value'] += x.get('total')
    res = []
    row1 = [
        {"label":"Total", "range":total_planned,  "value":total_produced},
        {"label":"Stage 2", "range":total_planned_s2,"value":total_produced_s2 },
        {"label":"Stage 3", "range":total_planned_s3,"value":total_produced_s3 },
        ]
    res.append(row1)
    for t, val in teams.items():
        row = [{},{},{}]
        row[1] = val.pop('stage2')
        row[2] = val.pop('stage3')
        row[0] = val
        row[1]['label'] = 'Stage 2'
        row[2]['label'] = 'Stage 3'
        row[0]['label'] = t
        res.append(row)
    return res

def week_hours(hours, hours_w, worked_hours, estimated_hours):
    teams = {'total':{'available':0, 'worked':0, 'estimated':0, 'consumed':0}}
    for x in hours:
        print('x=',x)
        team = x['team']
        teams[team]=  teams.get(team,{'available':0, 'worked':0, 'stage2':0, 'stage3':0,  'estimated':0, 'consumed':0})
        teams[team]['available']= x.get('hours', 0)
        teams[team]['estimated'] =round( estimated_hours.get(team,{}).get('S2',0) +  estimated_hours.get(team,{}).get('S3',0),2)
        teams[team]['stage2_estimated'] = estimated_hours.get(team,{}).get('S2',0)
        teams[team]['stage3_estimated'] = estimated_hours.get(team,{}).get('S3',0)
    for x in hours_w:
        print('2x=',x)
        team = x['team']
        teams[team]=  teams.get(team,{'available':0, 'worked':2, 'stage2':0, 'stage3':0, 'estimated':0, 'consumed':0})
        teams[team]['available'] = x.get('hours', 0)
        teams[team]['estimated'] =round( estimated_hours.get(team,{}).get('S2',0) +  estimated_hours.get(team,{}).get('S3',0),2)
        teams[team]['stage2_estimated'] = estimated_hours.get(team,{}).get('S2',0)
        teams[team]['stage3_estimated'] = estimated_hours.get(team,{}).get('S3',0)
    for x in worked_hours:
        team = x['team']
        teams[team]=  teams.get(team, {'available':0, 'worked':0, 'stage2':0, 'stage3':0, 'estimated':0, 'consumed':0})
        teams[team]['worked'] += round(x.get('hours', 0),2)
        teams[team]['estimated'] = round(estimated_hours.get(team,{}).get('S2',0) +  estimated_hours.get(team,{}).get('S3',0),2)
        if x['stage'] == 'S2':
            teams[team]['stage2'] = round(x.get('hours', 0),2)
        if x['stage'] == 'S3':
            teams[team]['stage3'] = round(x.get('hours', 0),2)
    for t, val in teams.items():
        teams['total']['available'] += val['available']
        teams['total']['worked'] += val['worked']
        teams['total']['estimated'] += round(val['estimated'],2)
        if val['available'] > 0:
            teams[t]['consumed'] =  round(val['worked'] / float(val['available']) * 100, 2)
    teams['total']['consumed'] = round(teams['total']['worked'] / float(teams['total']['available']) * 100, 2)
    return teams

def plants_table(produced_plants):
    rows = []
    for code, stage in produced_plants.items():
        plant_name = stage.get('plant_name')
        for stage, container in stage.items():
            if stage == 'plant_name':
                continue
            for name, res in container.items():
                row = {
                    'plant_code': code,
                    'plant_name': plant_name,
                    'container': name,
                    'stage': stage,
                    'produced': res.get('produced',0),
                    'planned': res.get('planned',0),
                    }
                if row['planned'] == 0:
                    row['progress'] = 0
                else:
                    row['progress'] = round(row['produced']/row['planned']*100,2)
                rows.append(row)
    return rows

def get_report(cut_year, cut_week):
    global plants, WEEKS, yearweek

    to_week  = cut_week
    from_week = cut_week
    planned = report_obj.get_production_plan(cut_year, cut_week)
    produced = report_obj.get_produced(cut_week, cut_year, from_week, to_week)
    produced_plants = report_obj.get_produced_by_plant(cut_year, from_week, to_week)
    produced_plants = report_obj.get_plan_by_plant(cut_year, cut_week, produced_plants)
    plant_rows = plants_table(produced_plants)
    hours = report_obj.available_hours()
    hours_w = report_obj.available_hours(yearweek)
    worked_hours = report_obj.get_worked_hours(cut_week, cut_year, from_week, to_week)
    # print('worked_hours=',worked_hours)
    estimated_hours = report_obj.get_estimated_hours(cut_year, cut_week)
    hours = week_hours(hours, hours_w, worked_hours, estimated_hours)
    res = arrange_info(planned, produced,)
    return plant_rows, res, hours



if __name__ == "__main__":
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    data = report_obj.data

    # plant_code = data.get("plant_code")
    # plant_code = all_data.get("plant_code")
    # report_model = ReportModel()
    #try:
    if True:
        #jwt_complete = simplejson.loads(sys.argv[2])
        #config["USER_JWT_KEY"] = jwt_complete
        #settings.config.update(config)
        tnow = time.time()
        tnow = datetime.fromtimestamp(tnow)
        yearweek = tnow.strftime('%Y%W')
        cut_year = int(str(yearweek)[:4])
        cut_week =   int(str(yearweek)[-2:])
        plant_rows, response, hours = get_report(cut_year, cut_week)
        sys.stdout.write(simplejson.dumps(
            {"firstElement":{
                'hours':hours
                },
            "secondElement":{
                'tabledata':response
                },
            "thirdElement":{
                'tabledata':plant_rows
                },
            "params":{"week":cut_week}
            })
        )
    # except:
    #     sys.stdout.write(simplejson.dumps({"firstElement": {"error":"Something went wrong"}}))
