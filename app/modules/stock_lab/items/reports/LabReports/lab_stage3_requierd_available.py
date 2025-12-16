#-*- coding: utf-8 -*-

import simplejson, sys
from copy import deepcopy
from linkaform_api import settings, network, utils
from bson import ObjectId
import time
from datetime import datetime, timedelta, date



from linkaform_api import settings
from account_settings import *

#from account_utils import get_plant_recipe, get_plant_names
from stock_report import Reports


class Reports(Reports):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False):
        #base.LKF_Base.__init__(self, settings, sys_argv=sys_argv, use_api=use_api)
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.table_data = []
        self.plants = {}
        self.WEEKS = []
        self.columsTable_title = [
          { "title":"Production Year", "field":'production_year',"hozAlign":"left","width":70},
          { "title":"Week", "field":'week',"hozAlign":"right","width":85},
          { "title":"Week Production: Plant: Plant Code", "field":'plant_code',"hozAlign":"left","width":75},
          { "title":"Week Production: Plant: Plant Name", "field":'plant_name',"hozAlign":"left","width":175},
          { "title":"Plan Required Total", "field":'required',"hozAlign":"right","width":125, "formatter": "money",
            "formatterParams": {"symbol": "", "symbolAfter": "",  "thousand": ",", "precision": 0}}
            ]
        self.col_req ={ "title":"Plan Required Total", "field":'required',"hozAlign":"right","width":125, "formatter": "money",
            "formatterParams": {"symbol": "", "symbolAfter": "",  "thousand": ",", "precision": 0}}

        self.col_stok ={ "title":"Stock Week", "field":'required',"hozAlign":"right","width":75, "formatter": "money",
          "formatterParams": {"symbol": "", "symbolAfter": "",  "thousand": ",", "precision": 0}}

        self.columsTable_stock = [
          # { "title":"Available eaches", "field":'stock_available',"hozAlign":"right","width":75,"formatter": "money",
           # "formatterParams": {"symbol": "", "symbolAfter": "", "thousand": ",", "precision": 0}},
          { "title":"PreviewsWeeks eaches", "field":'stock_previwes',"hozAlign":"right","width":75,"formatter": "money",
           "formatterParams": {"symbol": "", "symbolAfter": "", "thousand": ",", "precision": 0}},
           ]

        self.columsTable_stock_last = [
          { "title":"TotalStock eaches", "field":'stock_total',"hozAlign":"right","width":75,"formatter": "money",
           "formatterParams": {"symbol": "", "symbolAfter": "", "thousand": ",", "precision": 0}},
          { "title":"Week Production: Requierd Eaches Qty", "field":'requierd_eaches_qty',"hozAlign":"right","width":75},
          { "title":"Week Production: Priority", "field":'priority',"hozAlign":"left","width":75},
          { "title":"Week Production: Comments", "field":'comments',"hozAlign":"left","width":75},
        ]


def get_req_keys(row):
    res = {}
    for key, val in row.items():
        if 'required_' in key:
            res[key] = val
        if 'wstock_' in key:
            res[key] = val
    return res

def arrange_info(yearWeek):
    global report_obj
    res = []
    x = 0
    for pcode, data in report_obj.plants.items():
        row = {}
        if x == 0:
            row = {
                "production_year":yearWeek[:4],
                "week":yearWeek[-2:]
                }
        row.update({
            "priority":"",
            "plant_code":pcode,
            "plant_name":data.get('plant_name'),
            "required":data.get('required'),
            "stock_available":data.get('available'),
            "stock_previwes":data.get('previwes'),
            "stock_total":data.get('available') + data.get('previwes'),
            "requierd_eaches_qty":"",
            "comments":"",
            })
        row.update(get_req_keys(data))
        res.append(row)
        x += 1
    return res

if __name__ == '__main__':
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    all_data = simplejson.loads(sys.argv[2])
    data = all_data.get("data", {})
    tnow = time.time()
    tnow = datetime.fromtimestamp(tnow)

    yearWeek_from = data.get("year_week_from", tnow.strftime('%Y%W'))
    tnow = tnow + timedelta(weeks=2)

    yearWeek_to = data.get("year_week_to", tnow.strftime('%Y%W'))
    test = False
    # yearweek = 202304
    report_obj.get_requierd_plan(yearWeek_from, yearWeek_to)
    report_obj.query_get_stock_by_cutWeek(yearWeek_from, yearWeek_to)
    # print(stop)
    response = arrange_info(yearWeek_from,)
    if not test:
        sys.stdout.write(simplejson.dumps(
            {"firstElement":{
                'tabledata':response,
                'colsData':report_obj.columsTable_title + report_obj.columsTable_stock + report_obj.columsTable_stock_last,
                }
            }
            )
        )
