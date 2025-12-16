#-*- coding: utf-8 -*-

import simplejson, sys
from copy import deepcopy
from linkaform_api import settings, network, utils
from bson import ObjectId
import time
from datetime import datetime, timedelta, date

#from account_utils import get_plant_recipe, get_plant_names


from linkaform_api import settings
from account_settings import *

from stock_report import Reports

table_data = []
plants = {}
WEEKS = []


def arrange_info(data, stage, recipes3={}, recipes4={}):
    col = 'forcast'
    global plants, WEEKS
    today = date.today()
    today_week = int(today.strftime('%Y%W'))
    res = []
    t = 0
    res_dict = {}
    for x in data:
        pcode = x.get('product_code')
        x['plant_name'] = x.get('product_name')
        x['plant_code'] = x.get('product_code')
        # if True:
        try:
            if x.get('from') == 'Stage 3':
                cut_yearWeek = x.get('cut_yearWeek')
            else:
                cut_yearWeek = x.get('product_lot')
            selected_recipe_s4 = report_obj.select_S4_recipe(recipes4.get(pcode,{}), str(cut_yearWeek)[4:])
            multi_rate_s4 = selected_recipe_s4.get('S4_mult_rate',1)
            overage_s4 = selected_recipe_s4.get('S4_overage', selected_recipe_s4.get('S4_overage_rate',0))
            grow_weeks_s4 = selected_recipe_s4.get('S4_growth_weeks', 0)
            t_grow_weeks = int(str(cut_yearWeek)[4:]) + grow_weeks_s4
            x['total'] = x.get('total', x.get('total_harvest',0))
            if x.get('from') == 'Stage 3':
                selected_recipe = report_obj.select_S4_recipe(recipes3.get(pcode,{}), str(cut_yearWeek)[4:])
                multi_rate = selected_recipe.get('S4_mult_rate',1)
                grow_weeks = selected_recipe.get('S4_growth_weeks',0)
                overage = selected_recipe.get('S4_overage_rate', selected_recipe_s4.get('S4_overage', 0))
                x['total'] =  (x['total'] * multi_rate) * (1-overage)
                t_grow_weeks +=  grow_weeks
            harvest_date = datetime.strptime(str(cut_yearWeek)[:4], "%Y") + timedelta(weeks=t_grow_weeks-1)
            harvest_week= int(harvest_date.strftime('%Y%W'))
            # if col == 'forcast':
            #     if harvest_week < today_week:
            #         harvest_date = today
                
            x['total_harvest'] = int(round((x['total'] * multi_rate) * (1-overage_s4) ,0))
            x['havest_week'] =  int(harvest_date.strftime('%W'))
            x['havest_month'] = int(harvest_date.strftime('%m'))
            x['havest_year'] = int(harvest_date.strftime('%Y'))
            # x['total_harvest'] = int(x['total_planting'] * multi_rate)
            # x['total_harvest'] = int(x['total_harvest'] * (1-overage_s4) )
        except:
            x['plant_name'] ='Recipe not found'
            x['total_planting'] = 0
            x['havest_week'] = 0
            x['havest_month'] = 0
            x['havest_year'] = 0
            x['total_harvest'] = 0
        # print('x2=',x)
        # print('havest_year=',x['havest_year'] )
        # print('havest_year=',x['havest_year'] )
        # print('havest_week=',x['havest_week'] )
        res.append(x)
        # line_id = f"{x['plant_code']}_{x['havest_year']}_{x['havest_month']}_{x['havest_week']}_{x['from']}"
        # res_dict[line_id] = res_dict.get(line_id,0)
        # res_dict[line_id] += x['total_harvest']
    # for line, total in res_dict.items():
    #     x = {}
    #     plant_code, havest_year, havest_month, havest_week, stage_from = line.split('_')
    #     x['plant_name'] = ''
    #     x['plant_code'] = plant_code
    #     x['havest_year'] = havest_year
    #     x['havest_month'] = havest_month
    #     x['from'] = stage_from
    #     x['havest_week'] = havest_week
    #     x['total_harvest'] = total
    #     res.append(x)
    return res


def get_report(report_obj, product_code, stage='S3'):
    global plants, WEEKS
    res, all_codes = report_obj.query_get_stock(product_code, stage)
    greenhouse_stock, all_codes = report_obj.query_greenhouse_stock(product_code, all_codes)
    recipesS3 = report_obj.get_product_recipe(all_codes, stage=[4])
    recipesS4 = report_obj.get_product_recipe(all_codes, stage=[4, "Ln72"])
    res += greenhouse_stock
    res = arrange_info(res, stage, recipesS3, recipesS4)
    return res

if __name__ == '__main__':
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    #getFilters
    data = report_obj.data.get("data", {})
    product_code = data.get("product_code")
    # product_code = 'LAGTW'
    response = get_report(report_obj, product_code)
    sys.stdout.write(simplejson.dumps(
        {"firstElement":{
            'tabledata':response
            }
        }
        )
    )
