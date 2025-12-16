#-*- coding: utf-8 -*-

import simplejson, sys
from copy import deepcopy
from linkaform_api import settings, network, utils
from bson import ObjectId
import time
from datetime import datetime, timedelta, date

# from account_settings import *
# from account_utils import get_plant_recipe, get_plant_names

from linkaform_api import settings
from account_settings import *

from gh_stock_report import Reports

req_lines = []
# req = {}

def get_requierd_plan(stage, year, plant_code=None):
    print('stage',stage)
    if stage == "stage4":
        year_id = "answers.6206b4e533536f2e4f0e3388"
        week_id = "answers.6206b4e533536f2e4f0e3389"
        eaches_id = "answers.6206b6186c0b3b00535d60d8"
    elif stage == "stage3":
        year_id = "answers.6206b4e533536f2e4f0e3386"
        week_id = "answers.6206b4e533536f2e4f0e3387"
        eaches_id = "answers.6206b6186c0b3b00535d60d5"
    elif stage == "stage2":
        year_id = "answers.6226ac11de14768c8527bb3e.6226acece895584f7d0b830a"
        week_id = "answers.6226ac11de14768c8527bb3e.6226acece895584f7d0b830b"
        eaches_id = "answers.6226ac11de14768c8527bb3e.6226acece895584f7d0b830c"

    match_query = {
        "deleted_at":{"$exists":False},
        "form_id":81420,
        year_id:year
        }

    if plant_code:
        match_query.update({"answers.6205f7690e752ce25bb30102.61ef32bcdf0ec2ba73dec33d":plant_code,})

    query = []
    if stage == 'stage2':
        query = [{'$unwind': "$answers.6226ac11de14768c8527bb3e" }]

    query += [{'$match': match_query }]

    query += [
        {'$project':
            {'_id': 1,
                'plant_code': '$answers.6205f7690e752ce25bb30102.61ef32bcdf0ec2ba73dec33d',
                'week': '${}'.format(week_id),
                'eaches': '${}'.format(eaches_id),}},
        {'$group':
            {'_id':
                { 'plant_code': '$plant_code',
                  'week': '$week'
                  },
              'total': {'$sum': '$eaches'}}},
        {'$project':
            {'_id': 0,
            'plant_code': '$_id.plant_code',
            'week': '$_id.week',
            'total': '$total'
            }
        },
        {'$sort': {'plant_code': 1, 'week':1}}
    ]
    print('query=', simplejson.dumps(query, indent=4))
    result = report_obj.cr.aggregate(query)
    return [r for r in result]

def get_month(year, week):
    tmp = datetime.strptime('%04d-%02d-1' % (year, week), '%Y-%W-%w')
    return tmp.strftime('%b').lower()

def get_rows(year, stage, data):
    global req_lines
    #req[stage] = req.get(stage, {})
    total = 0
    row = {'stage':stage, '_children' : []}
    childs = {}
    for pweek in data:
        pcode = pweek.get('plant_code')
        childs[pcode] = childs.get(pcode, {})
        month = get_month(year, pweek.get('week'))
        # print('week=', pweek.get('week'), ' Month=', month)
        row[month] = row.get(month,0)
        row[month] += pweek.get('total',0)
        childs[pcode][month] = childs[pcode].get(month,0)
        childs[pcode][month] += pweek.get('total', 0)

    for plant, months in childs.items():
        plant_row = {'stage':plant}
        plant_row.update(months)
        row['_children'].append(plant_row)
    print('row', row)
    return row


print('whcih', Reports)

if __name__ == '__main__':
    print(sys.argv)
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    # all_data = simplejson.loads(sys.argv[2])
    data = report_obj.data.get('data')
    # data = all_data.get("data", {})
    plant_code = data.get("plant_code")

    year = data.get("year",2022)
    print('year ', year)
    # plant_code = all_data.get("plant_code")
    # report_model = ReportModel()
    #try:
    if year:
        year = int(year)
        response = get_requierd_plan("stage4", year, plant_code)
        print('stage4=', response)
        for f in response:
            print('week:', f['week'])
            print('total:', f['total'])

        req_lines.append(get_rows(year, "stage4", response))

        response3 = get_requierd_plan("stage3", year, plant_code)
        req_lines.append(get_rows(year, "stage3", response3))

        response2 = get_requierd_plan("stage2", year, plant_code)
        req_lines.append(get_rows(year, "stage2", response2))
        get_rows(year, "stage2", response2)

        # query_report_second(date_from, date_to )
        # query_report_fourth(date_from, date_to )
        sys.stdout.write(simplejson.dumps(
            {"firstElement":{
                'tabledata':req_lines
                }
            }
            )
        )
    # except:
    #     sys.stdout.write(simplejson.dumps({"firstElement": {"error":"Something went wrong"}}))