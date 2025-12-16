# -*- coding: utf-8 -*-

import sys, simplejson
from datetime import datetime, timedelta, date
from copy import deepcopy

from lkf_addons.stock_greenhouse.stock_reports import Reports
from lkf_addons.stock_greenhouse.stock_utils import Stock


# sys.path.append('/srv/scripts/addons/modules/stock_greenhouse/items/scripts/')


# from stock_utils import Stock

today = date.today()
year_week = int(today.strftime('%Y%W'))


class Reports(Reports, Stock):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False):
        #base.LKF_Base.__init__(self, settings, sys_argv=sys_argv, use_api=use_api)
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.GREENHOUSE_INVENTORY_ID = self.lkm.form_id('green_house_inventory','id')

    def get_requierd_plan(self, yearWeek_from, yearWeek_to):
        self.columsTable_title
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.PRODUCTION_PLAN,
            # f"answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}":"LAGAM",
            f"answers.{self.f['stage_4_plan_require_yearweek']}": {"$gte": int(yearWeek_from),"$lte": int(yearWeek_to) }
            }
        query = [
            {"$match": match_query},
            {'$project':
                {'_id': 1,
                    'product_code': f"$answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}",
                    'week': f"$answers.{self.f['stage_4_plan_require_yearweek']}",
                    'eaches': f"$answers.{self.f['stage_4_plan_requierments']}"
                    }
            },
            {'$group':
                {'_id':
                    {
                      'product_code': '$product_code',
                      'week': '$week'
                      },
                  'total': {'$sum': '$eaches'}}},
            {'$project':
                {'_id': 0,
                'product_code': '$_id.product_code',
                'week':'$_id.week',
                'total': '$total'
                }
            },
            {'$sort': {'product_code': 1, 'week':1}}
        ]
        result = self.cr.aggregate(query)
        rweeks = int(yearWeek_to) - int(yearWeek_from) + 1
        req_weeks = {}
        for x in range(rweeks):
            req_weeks['required_{}'.format(int(yearWeek_from) + x)] = 0
            this_col = deepcopy(self.col_req)
            this_col['field'] = 'required_{}'.format(int(yearWeek_from) + x)
            this_col['title'] = 'Week {}'.format(int(yearWeek_from) + x)
            self.columsTable_title.append(this_col)
        default_schema = {'available':0, 'previwes':0, 'required':0, 'plant_name':""}
        default_schema.update(req_weeks)
        for r in result:
            pcode = r.get('product_code')
            week = r.get('week')
            required = r.get('total',0)
            self.plants[pcode] = self.plants.get(pcode, deepcopy(default_schema))
            self.plants[pcode]['required_{}'.format(week)] += required
            self.plants[pcode]['required'] += required
        return True

    def query_get_stock_by_cutWeek(self, yearWeek_from, yearWeek_to, status='active'):
        global plants, col_stok, columsTable_stock
        stage ='S3'
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.FORM_INVENTORY_ID,
            f"answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['reicpe_stage']}":stage,
            f"answers.{self.f['inventory_status']}": status,
            f"answers.{self.f['new_cutweek']}": {"$lte": int(yearWeek_to) }
            }
        query= [{'$match': match_query },
            {'$project':
                {'_id': 1,
                    'plant_code': f"$answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['product_code']}",
                    'plant_name':{ "$arrayElemAt": [ f"$answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['product_name']}",0]},
                    #'plant_name': f"answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['product_name']}",
                    'cutweek':{"$toInt":f"$answers.{self.f['new_cutweek']}"},
                    'eaches': f"$answers.{self.f['actual_eaches_on_hand']}",
                    }
            },
            # {'$project':
            #     {'_id': 1,
            #         'plant_code': '$plant_code',
            #         'plant_name':'$plant_name',
            #         'cutweek':{"$sum" :['$planted_yearweek','$growth_week'] },
            #         'eaches': '$eaches'}},
            # {"$match": {'cutweek': {"$lte": int(yearWeek_to) }}},
            {'$group':
                {'_id':
                    {
                    'plant_code': '$plant_code',
                    'plant_name': '$plant_name',
                    'cutweek': '$cutweek',
                      },
                  'total': {'$sum': '$eaches'}}},
            {'$project':
                {'_id': 0,
                'plant_code': '$_id.plant_code',
                'plant_name': '$_id.plant_name',
                'cutweek': '$_id.cutweek',
                'total': '$total'
                }
            },
            {'$sort': {'plant_code': 1, 'cutweek':1}}
            ]
        # print('query=', simplejson.dumps(query, indent=4))
        res = self.cr.aggregate(query)
        result = {}

        rweeks = int(yearWeek_to) - int(yearWeek_from) + 1
        req_weeks = {}
        for x in range(rweeks):
            req_weeks['wstock_{}'.format(int(yearWeek_from) + x)] = 0
            this_col = deepcopy(self.col_req)
            this_col['field'] = 'wstock_{}'.format(int(yearWeek_from) + x)
            this_col['title'] = 'Stock Week {}'.format(int(yearWeek_from) + x)
            self.columsTable_stock.append(this_col)
        default_schema = {'available':0, 'previwes':0, 'required':0, 'plant_name':""}
        default_schema.update(req_weeks)
        for r in res:
            pcode = r.get('plant_code')
            week = r.get('cutweek')
            self.plants[pcode] = self.plants.get(pcode, deepcopy(default_schema))
            self.plants[pcode]['plant_name'] = r.get('plant_name')
            if week < int(yearWeek_from):
                self.plants[pcode]['previwes'] += r['total']
            else:
                self.plants[pcode]['available'] += r['total']
                #if week > int(yearWeek_from):
                self.plants[pcode]['wstock_{}'.format(week)] = r['total']
        return True

    def query_get_stock(self, product_code=None, stage=None, lot_number=None, warehouse=None, location=None, status='active' ):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.FORM_INVENTORY_ID,
            f"answers.{self.f['inventory_status']}": status
            }
        if product_code:
            match_query.update({f"answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['product_code']}":product_code})
        if stage:
            match_query.update({f"answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['reicpe_stage']}":stage})
        if lot_number:
            match_query.update({f"answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['product_lot']}":lot_number})
        if warehouse:
            unwind_query.update({f"answers.{self.CATALOG_INVENTORY_OBJ_ID}.{self.f['warehouse']}":warehouse})      
        if location:
            unwind_query.update({f"answers.{self.CATALOG_INVENTORY_OBJ_ID}.{self.f['warehouse_location']}":location})
        query= [{'$match': match_query },
            {'$project':
                {'_id': 1,
                    'product_code': f"$answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['product_code']}",
                    'cut_yearWeek': f"$answers.{self.f['plant_cut_year']}",
                    'cut_week': f"$answers.{self.f['production_cut_week']}",
                    'eaches': f"$answers.{self.f['actual_eaches_on_hand']}"
                    }
            },
            {'$group':
                {'_id':
                    { 'product_code': '$product_code',
                      'cut_yearWeek': '$cut_yearWeek',
                      # 'cut_week': '$cut_week'
                      },
                  'total': {'$sum': '$eaches'}}},
            {'$project':
                {'_id': 0,
                'product_code': '$_id.product_code',
                'cut_yearWeek': '$_id.cut_yearWeek',
                'total': '$total',
                'from': 'Stage 3'
                }
            },
            {'$sort': {'_id.product_code': 1, '_id.cut_yearWeek': 1, '_id.cut_week':1}}
            ]
        # print('query=', simplejson.dumps(query, indent=4))
        res = self.cr.aggregate(query)
        result = [r for r in res]
        all_codes = []
        for r in result:
            if r.get('product_code') and r.get('product_code') not in all_codes:
                all_codes.append(r['product_code'])
        return result, all_codes

    def query_greenhouse_stock(self, product_code=None, all_codes=[], status='active'):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.GREENHOUSE_INVENTORY_ID,
            f"answers.{self.f['inventory_status']}": status
            }
        if product_code:
            match_query.update({f"answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['product_code']}":product_code,})
        query= [{'$match': match_query },
            {'$project':
                {'_id': 1,
                    'product_code': f"$answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['product_code']}",
                    'plant_name': {"$arrayElemAt" : [f"$answers.{self.CATALOG_PRODUCT_RECIPE_OBJ_ID}.{self.f['product_name']}",0]},
                    'product_lot': f"$answers.{self.f['product_lot']}",
                    'eaches': f"$answers.{self.f['product_lot_actuals']}"}},
            {'$group':
                {'_id':
                    { 'product_code': '$product_code',
                      'plant_name': '$plant_name',
                      'product_lot': '$product_lot',
                      },
                  'total': {'$sum': '$eaches'}}},
            {'$project':
                {'_id': 0,
                'product_code': '$_id.product_code',
                'plant_name': '$_id.plant_name',
                'product_lot': '$_id.product_lot',
                'total_planting': '$total'
                }
            },
            {'$sort': {'_id.product_code': 1, '_id.cut_year': 1, '_id.cut_week':1}}
            ]
        res = self.cr.aggregate(query)
        # result = [r for r in res]
        result=[]
        for r in res:
            if r.get('product_code') and r.get('product_code') not in all_codes:
                all_codes.append(r['product_code'])
            product_lot = str(r['product_lot'])
            ready_year = product_lot[:4]
            ready_week = product_lot[4:]
            d = f'{ready_year}-W{ready_week}'
            harvest_date = datetime.strptime(d + '-1', "%Y-W%W-%w")
            r['havest_week'] = int(harvest_date.strftime('%W'))
            r['havest_month'] = int(harvest_date.strftime('%m'))
            r['havest_year'] = int(harvest_date.strftime('%Y'))
            r['from'] = 'GreenHouse'
            r['total_harvest'] = r['total_planting'] * 72
            result.append(r)
        return result, all_codes

