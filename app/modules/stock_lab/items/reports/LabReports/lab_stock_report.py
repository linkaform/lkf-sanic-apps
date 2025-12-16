#-*- coding: utf-8 -*-
import simplejson, sys
from linkaform_api import settings
from bson import ObjectId
import time
from datetime import datetime, timedelta, date

from stock_report import Reports

from account_settings import *


table_data = []
plants = {}
WEEKS = []

def set_header(pcode):
    return {
        "plant_code":pcode,
        "stage_2_actuals":0,
        "stage_2_forcast":0,
        "stage_3_actuals":0,
        "stage_3_forcast":0,
        "cut_weeks":{},
        "_children":[]}

def arrange_info(data, stage, col, recipes={}):
    global plants, WEEKS
    today = date.today()
    today_week = int(today.strftime('%Y%W'))
    for x in data:
        #pcode = x.get('plant_code')
        pcode = x.get('product_code')
        multi_rate = 1
        grow_weeks = 0
        if col == 'forcast':
            if stage == 3:
                cut_yearWeek = x['cut_yearWeek']
                if recipes.get(pcode,{}):
                    recipe = report_obj.select_S4_recipe(recipes.get(pcode,{}), str(cut_yearWeek)[4:])
                else:
                    print('not found...')
                    continue
                    #plants[pcode]
                stage_multi_rate = 'S{}_overage'.format(stage+1)
                stage_grow_weeks = 'S{}_growth_weeks'.format(stage+1)

                multi_rate = 1 - recipe.get(stage_multi_rate,0)
                #grow_weeks = recipes.get(pcode,{})[0].get(stage_grow_weeks,1)
                grow_weeks = recipe.get(stage_grow_weeks,1)
            else:
                stage_multi_rate = 'S{}_mult_rate'.format(stage)
                stage_grow_weeks = 'S{}_growth_weeks'.format(stage)
                multi_rate = recipes.get(pcode,{}).get(stage_multi_rate,1)
                grow_weeks = recipes.get(pcode,{}).get(stage_grow_weeks,1)
        if x.get('cut_yearWeek'):
            year_week = int(x.get('cut_yearWeek'))
            cut_week = str(year_week)[4:]
            t_grow_weeks = int(cut_week) + grow_weeks
            harvest_date = datetime.strptime(str(year_week)[:4], "%Y") + timedelta(weeks=t_grow_weeks -1 )
            harvest_week= int(harvest_date.strftime('%Y%W'))
            ready_year_week = int(x.get('cut_yearWeek')) + grow_weeks
            if col == 'forcast':
                if harvest_week < today_week:
                    year_week = today_week
                else:
                    year_week = harvest_week
        else:
            year_week = int(x.get('year_week',0))
        stage_key = 'stage_{}_{}'.format(stage, col)
        if year_week not in WEEKS and col =='actuals':
            WEEKS.append(year_week)
        if not plants.get(pcode):
            plants[pcode] = set_header(pcode)
        plants[pcode][stage_key] += int(round(x.get('total') * multi_rate,0))
        
        plants[pcode]['year_week'] = plants[pcode].get('year_week',{}) 
        plants[pcode]['year_week'][year_week] = plants[pcode]['year_week'].get(year_week,{}) 
        plants[pcode]['year_week'][year_week][stage_key] = plants[pcode]['year_week'][year_week].get(stage_key,0)
        plants[pcode]['year_week'][year_week][stage_key] +=  int(round(x.get('total') * multi_rate))

        '''
        if not plants[pcode]['year_week'].get(year_week):
                plants[pcode]['year_week'][year_week] = {}
        ### cutweeks detail
        plants[pcode]['year_week'][year_week][stage_key] = plants[pcode]['year_week'][year_week].get(stage_key,0)
        plants[pcode]['year_week'][year_week][stage_key] +=  x.get('total') * multi_rate
        '''

def get_report(plant_code, stage=2):
    res, all_codes = report_obj.query_get_stock(plant_code, stage)
    if stage == 3:
        recipes = report_obj.get_plant_recipe(all_codes, stage=[4,])

        #recipes = report_obj.get_plant_recipe(all_codes, stage=[3,])
    else:
        recipes = report_obj.get_plant_recipe(all_codes, stage=[stage,])
    arrange_info(res, stage, 'actuals')
    arrange_info(res, stage, 'forcast', recipes)
    if stage == 2:
        get_report(plant_code, 3)
    return res

def set_children():
    global plants
    res = []
    for plant_code, plant in plants.items():
        year_week = plant.pop('year_week')
        weeks = list(year_week.keys())
        weeks.sort()
        weeks.reverse()
        for w in weeks:
            if year_week.get(w):
                year_week[w]['cut_week'] = w
                plant['_children'].append(year_week[w])

if __name__ == "__main__":
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()

    #--Filters
    data = report_obj.data.get('data')
    plant_code = data.get("plant_code")
    response = get_report(plant_code)
    response = set_children()
    sys.stdout.write(simplejson.dumps(
        {"firstElement":{
            'tabledata':list(plants.values())
            }
        }
        )
    )