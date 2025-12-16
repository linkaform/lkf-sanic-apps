#-*- coding: utf-8 -*-

import simplejson, sys
from copy import deepcopy
from linkaform_api import settings, network, utils
from bson import ObjectId
import time
from datetime import datetime, timedelta, date

from stock_report import Reports

from account_settings import *

table_data = []
plants = {}
WEEKS = []
REQUIRED = 0
PRODUCED = 0

def date_to_week(date_from):
    week_from = datetime.strptime(date_from, '%Y-%m-%d')
    year_week = week_from.strftime('%Y%W')
    return year_week

def date_to_day(date_from):
    week_from = datetime.strptime(date_from, '%Y-%m-%d')
    year_day = week_from.strftime('%j')
    return year_day

def cut_day_to_date(cutday, year=None):
    week_from = datetime.strptime(str(year) + str(cutday), '%Y%j')
    year_week = week_from.strftime('%Y-%m-%d')
    return year_week


class Reports(Reports):

    def get_report(self, plant_code, stage, date_from, date_to):
        global REQUIRED, PRODUCED
        detail = self.query_get_production(plant_code, date_from, date_to, stage, group_by="work_order")
        for d in detail:
            prod_id = d.get('prod_id',[])
            if len(prod_id) > 0:
                d['prod_id'] = str(prod_id[0])
        grouped_res = self.query_get_production(plant_code, date_from, date_to, stage, group_by="code")
        #print('grouped_res', grouped_res)
        grouped_week = self.query_get_production(plant_code, date_from, date_to, stage, group_by="work_week")
        grouped_cut_day = self.query_get_production(plant_code, date_from, date_to, stage, group_by="cut_day")
        xx, all_codes, weeks = self.query_get_production(plant_code, date_from, date_to, stage, group_by="get_weeks")
        if not weeks:
            weeks =[False,]
            weeks.sort()
        #print('weeks',weeks)
        work_orders = self.query_get_work_orders(all_codes, weeks)
        week_from = int(date_to_week(date_from))
        week_to = int(date_to_week(date_to))
        if not stage:
            planned = self.query_planned(plant_code, weeks[0], weeks[-1], stage="S2")
            planned += self.query_planned(plant_code, weeks[0], weeks[-1], stage="S3")
            REQUIRED = self.query_planned(plant_code, week_from, week_to, stage="S2", only_qty=True)
            REQUIRED += self.query_planned(plant_code, week_from, week_to, stage="S3", only_qty=True)
        else:
            planned = self.query_planned(plant_code, weeks[0], weeks[-1], stage=stage)
            REQUIRED = self.query_planned(plant_code, week_from, week_to, stage=stage, only_qty=True)
        planned_dict = {}
        for week in planned:
            s = week.get('stage')
            pcode = week.get('plant_code')
            total = week.get('total')
            year_week = week.get('year_week')
            ### Asi queda la info {2:{'LNAFP':{202235:14900},3:{'LNAFP':{202235:100} }}
            planned_dict[s] = planned_dict.get(s, {})
            planned_dict[s][pcode] = planned_dict[s].get(pcode, {})
            if year_week:
                if not planned_dict[s][pcode].get(year_week):
                        planned_dict[s][pcode][year_week] = total

        for row in grouped_res:
            pcode = row.get('plant_code')
            stage = row.get('stage')
            print('stage=',stage)
            PRODUCED += row.get('eaches',0)
            year_week = int('{}{:02d}'.format(row.get('cut_year'), row.get('cut_week')))
            row.update({'year_week':year_week})

            if planned_dict.get(stage,{}).get(pcode,{}).get(year_week):
                req_variance =  row.get('eaches',0) - planned_dict[stage][pcode][year_week]
                row.update({'required':planned_dict[stage][pcode][year_week], 'req_variance':req_variance})
            if work_orders.get(pcode,{}).get(stage,{}).get(year_week):
                wk_total = work_orders[pcode][stage][year_week]
                variance =  wk_total - row.get('eaches',0)
                row.update({'work_order':wk_total,'variance':variance})
        return detail , grouped_res, grouped_week, grouped_cut_day

    def query_get_production(self, plant_code, date_from, date_to, stage=None, group_by=False):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.MOVE_NEW_PRODUCTION_ID,
            }
        if plant_code:
            match_query.update({f"answers.{self.SKU_OBJ_ID}.{self.f['product_code']}":plant_code})
        if stage:
            match_query.update({f"answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}":stage})
        #year
        week_from = date_to_week(date_from)
        week_to = date_to_week(date_to)
        match_query.update(self.get_date_query(int(week_from[:4]), int(week_to[:4]), date_field_id=self.f['plant_cut_year'], field_type='int'))
        #week
        #match_query.update(get_date_query(int(week_from[-2:]), int(week_to[-2:]), date_field_id='622bb9946d0d6fef17fe0842'))
        #cutday
        cutday_from = date_to_day(date_from)
        cutday_to = date_to_day(date_to)
        match_query.update(self.get_date_query(int(cutday_from), int(cutday_to), date_field_id=self.f['plant_cut_day'], field_type='int'))
        query= [{'$match': match_query },
            {'$project':
                {'_id': 0,
                    'plant_code': f"$answers.{self.SKU_OBJ_ID}.{self.f['product_code']}",
                    'stage': f"$answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}",
                    'prod_folio': f"$answers.{self.f['production_folio']}",
                    'prod_folio3': f"$answers.{self.f['production_folio']}",
                    'cut_day': f"$answers.{self.f['plant_cut_day']}",
                    'cut_week': f"$answers.{self.f['production_cut_week']}",
                    'cut_year': f"$answers.{self.f['plant_cut_year']}",
                    'team': f"$answers.{self.TEAM_OBJ_ID}.{self.f['team_name']}",
                    'containers': f"$answers.{self.f['actuals']}",
                    'eaches': f"$answers.{self.f['actual_eaches_on_hand']}"}
                    },
            {"$lookup": {
                  "from": "form_answer",
                  "localField": "prod_folio",
                  "foreignField": "folio",
                  "as": "prod"
            }},
            {'$project':
                {
                    '_id': 0,
                    'plant_code': '$plant_code',
                    'stage': '$stage',
                    'prod_folio': '$prod_folio',
                    'prod_id': '$prod._id',
                    'cut_day': '$cut_day',
                    'cut_week': '$cut_week',
                    'cut_year': '$cut_year',
                    'team': '$team',
                    'produced': '$containers',
                    'eaches': '$eaches',
                    'order_status': f"$prod.answers.{self.f['production_left_overs']}",
                    'record_id': '$prod._id',
                    'work_order_week': {'$sum':f"$prod.answers.{self.f['production_week']}"},
                    'work_order': f"$prod.answers.{self.f['production_requier_containers']}",
                }
            },
            {'$project':
                {
                    '_id': 0,
                    'plant_code': '$plant_code',
                    'stage': '$stage',
                    'order_status': '$order_status',
                    'prod_folio': '$prod_folio',
                    'prod_id': '$prod_id',
                    'record_id': '$record_id',
                    'cut_day': '$cut_day',
                    'cut_week': '$cut_week',
                    'cut_year': '$cut_year',
                    'team': '$team',
                    'produced': '$produced',
                    'eaches': '$eaches',
                    'work_order_week': '$work_order_week',
                    'work_order': '$work_order',
                    # 'variance': {'$subtract':['$produced','$work_order']}
                }
            },
            {'$sort': {'plant_code': 1, 'cut_year': 1, 'cut_week':1}}
            ]
        if group_by == 'work_order':
                query += [
                {'$group':
                    {
                        '_id':
                        {
                            'record_id': '$record_id',
                            'order_status': '$order_status',
                            'prod_folio': '$prod_folio',
                            'team': '$team',
                            'plant_code': '$plant_code',
                            'stage': '$stage',
                          },
                        'produced': {'$sum': '$produced'},
                        'variance': {'$sum': '$variance'},
                        'work_order': {'$last': '$work_order'},
                    }
                },
                {'$project':
                    {
                        '_id': 0,
                        'record_id': '$_id.record_id',
                        'prod_folio': '$_id.prod_folio',
                        'order_status': '$_id.order_status',
                        'plant_code': '$_id.plant_code',
                        'stage': '$_id.stage',
                        'team': '$_id.team',
                        'cut_year': '$_id.cut_year',
                        'cut_week': '$_id.cut_week',
                        'produced': '$produced',
                        'eaches': '$eaches',
                        'work_order': '$work_order',
                        'variance': '$variance',
                    }
                }
                ]

        if group_by =='code':
            query += [
            {'$group':
                {
                    '_id':
                    {
                        'plant_code': '$plant_code',
                        'cut_year': '$cut_year',
                        'cut_week': '$cut_week',
                        'stage': '$stage',
                      },
                    'produced': {'$sum': '$produced'},
                    'eaches': {'$sum': '$eaches'},
                }
            },
            {'$project':
                {
                    '_id': 0,
                    'plant_code': '$_id.plant_code',
                    'stage': '$_id.stage',
                    'cut_year': '$_id.cut_year',
                    'cut_week': '$_id.cut_week',
                    'produced': '$produced',
                    'eaches': '$eaches',
                }
            },
            {'$sort': {'stage': 1, 'plant_code': 1, 'year_week':1}}
            ]

        if group_by == 'work_week':
            query += [
            {'$group':
                {
                    '_id':
                    {
                        # 'plant_code': '$plant_code',
                        # 'cut_year': '$cut_year',
                        'cut_week': '$work_order_week',
                        # 'stage': '$stage',
                      },
                    'produced': {'$sum': '$produced'},
                    'eaches': {'$sum': '$eaches'},
                }
            },
            {'$project':
                {
                    '_id': 0,
                    #'plant_code': '$_id.plant_code',
                    #'stage': '$_id.stage',
                    #'cut_year': '$_id.cut_year',
                    'cut_week': '$_id.cut_week',
                    #'produced': '$produced',
                    'eaches': '$eaches',
                }
            },
            {'$sort': {'cut_week': 1}}
            ]

        if group_by == 'cut_day':
            query += [
            {'$group':
                {
                    '_id':
                    {
                        # 'plant_code': '$plant_code',
                        'cut_year': '$cut_year',
                        'cut_day': '$cut_day',
                        # 'stage': '$stage',
                      },
                    'produced': {'$sum': '$produced'},
                    'eaches': {'$sum': '$eaches'},
                }
            },
            {'$project':
                {
                    '_id': 0,
                    #'plant_code': '$_id.plant_code',
                    #'stage': '$_id.stage',
                    'cut_year': '$_id.cut_year',
                    'cut_day': '$_id.cut_day',
                    'produced': '$produced',
                    'eaches': '$eaches',
                }
            },
            {'$sort': {'cut_day': 1}}
            ]

        if group_by == 'get_weeks':
            query += [
            {'$group':
                {
                    '_id':
                    {
                        'cut_year': '$cut_year',
                        'cut_week': '$cut_week',
                      },
                    'qty': {'$sum': 1},
                }
            },
            {'$project':
                {
                    '_id': 0,
                    #'plant_code': '$_id.plant_code',
                    #'stage': '$_id.stage',
                    'cut_year': '$_id.cut_year',
                    'cut_week': '$_id.cut_week',
                    'qty': '$qty',
                }
            },
            {'$sort': {'cut_week': 1}}
            ]
    #    print('query=',simplejson.dumps(query))
        res = self.cr.aggregate(query)
        result = []
        all_codes = []
        all_weeks = []

        if group_by == 'work_order':
            for r in res:
                if r.get('record_id') and len('record_id') > 0:
                    r['record_id'] = str(r['record_id'][0])
                else:
                    r['record_id'] = ""
                if r.get('order_status') and len('order_status') > 0:
                    r['order_status'] = r['order_status'][0].replace('_',' ').title()
                else:
                    r['order_status'] = ""
                if r.get('work_order') and len('work_order') > 0:
                    r['work_order'] = r['work_order'][0]
                else:
                    r['work_order'] =0
                r['variance'] =  int(r.get('produced',0)) - int(r.get('work_order',0))
                result.append(r)

        if group_by == 'get_weeks':
            for r in res:
                if r.get('plant_code') and r.get('plant_code') not in all_codes:
                    all_codes.append(r['plant_code'])
                year_week = '{}{:02d}'.format(r.get('cut_year'), r.get('cut_week'))
                if year_week not in all_weeks:
                    all_weeks.append(int(year_week))
                result.append(r)
            return result, all_codes, all_weeks

        if group_by == 'cut_day':
            for r in res:
                r['date'] = cut_day_to_date(r.pop('cut_day'),r.pop('cut_year'),)
                result.append(r)

        if group_by == 'work_week':
            total = 0
            for r in res:
                total += int(r['eaches'])
                r['cut_week'] = int(r['cut_week'])
                result.append(r)
            for r in result:
                r['eaches'] = float('{0:.2f}'.format(r['eaches']/total*100))
        else:
            for r in res:
                result.append(r)

        return result

    def report_by_team(self, plant_code, week_from, week_to, stage=None):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.MOVE_NEW_PRODUCTION_ID,
            }
        if plant_code:
            match_query.update({f"answers.{self.SKU_OBJ_ID}.{self.f['product_code']}":plant_code})
        if stage:
            match_query.update({f"answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}":stage})
        #year
        match_query.update(self.get_date_query(int(week_from[:4]), int(week_to[:4]), date_field_id=self.f['plant_cut_year'], field_type='int'))
        #print('Variable Date Query', date_query)
        date_query = self.get_date_query(int(week_from[-2:]), int(week_to[-2:]), date_field_id=self.f['production_cut_week'], field_type='int')

        match_query.update(date_query)

        query= [{'$match': match_query },
            {'$project':
                {   '_id': 0,
                    'stage': f"$answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}",
                    'team': f"$answers.{self.TEAM_OBJ_ID}.{self.f['team_name']}",
                    'containers': f"$answers.{self.f['actuals']}",
                    'eaches': f"$answers.{self.f['actual_eaches_on_hand']}"}
                    }
                    ,
            {'$group':
                {'_id':
                    { 'team': '$team',
                      },
                  'total': {'$sum': '$containers'}}},
            {'$project':
                {
                    '_id':0,
                    'team':'$_id.team',
                    'total':'$total',
                }
            },
            {'$sort': {'team': 1, }}
            ]
        #print('query=', simplejson.dumps(query, indent=4))
        res = self.cr.aggregate(query)
        result = []
        total = 0
        for r in res:
            result.append(r)
            total += r.get('total')
        for r in result:
            percentage = round(((r.get('total') / total)*100),2)
            r.update({'percentage': percentage})
        return result

    def report_by_crop(self, plant_code, week_from, week_to, stage=None):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.MOVE_NEW_PRODUCTION_ID,
            }
        if plant_code:
            match_query.update({f"answers.{self.SKU_OBJ_ID}.{self.f['product_code']}":plant_code})
        if stage:
            match_query.update({f"answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}":stage})
        #year
        match_query.update(self.get_date_query(int(week_from[:4]), int(week_to[:4]), date_field_id=self.f['plant_cut_year'], field_type='int'))
        match_query.update(self.get_date_query(int(week_from[-2:]), int(week_to[-2:]), date_field_id=self.f['production_cut_week'], field_type='int'))
        query= [{'$match': match_query },
            {'$project':
                {   '_id': 0,
                    'plant_code': f"$answers.{self.SKU_OBJ_ID}.{self.f['product_code']}",
                    'containers': f"$answers.{self.f['actuals']}",
                    'eaches': f"$answers.{self.f['actual_eaches_on_hand']}"}
                    },
            {'$group':
                {'_id':
                    { 'plant_code': '$plant_code',
                      },
                  'total': {'$sum': '$containers'}}},
            {'$project':
                {
                    '_id':0,
                    'plant_code':'$_id.plant_code',
                    'total':'$total',
                }
            },
            {'$sort': {'total': -1, }}
            ]
        res = self.cr.aggregate(query)
        result = [r for r in res]
        return result

    def report_by_stage(self, plant_code, week_from, week_to, stage=None):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.MOVE_NEW_PRODUCTION_ID,
            }
        if plant_code:
            match_query.update({f"answers.{self.SKU_OBJ_ID}.{self.f['product_code']}":plant_code})
        #year
        match_query.update(self.get_date_query(int(week_from[:4]), int(week_to[:4]), date_field_id=self.f['plant_cut_year'], field_type='int'))
        match_query.update(self.get_date_query(int(week_from[-2:]), int(week_to[-2:]), date_field_id=self.f['production_cut_week'], field_type='int'))

        #print('Match Query', match_query)
        query= [{'$match': match_query },
            {'$project':
                {   '_id': 0,
                    'containers': f"$answers.{self.f['actuals']}",
                    'eaches': f"$answers.{self.f['actual_eaches_on_hand']}",
                    'stage': f"$answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}",
                    }
            },
            {'$group':
                {'_id':
                    { 'stage': '$stage',
                      },
                  'total': {'$sum': '$containers'}}},
            {'$project':
                {
                    '_id':0,
                    'stage':'$_id.stage',
                    'total':'$total',
                }
            },
            {'$sort': {'stage': 1, }}
            ]

        res = self.cr.aggregate(query)
        result = []
        total = 0
        for r in res:
            result.append(r)
            total += r.get('total')
        for r in result:
            percentage = round(((r.get('total') / total)*100),2)
            r.update({'percentage': percentage})
        return result

    def query_planned(self, all_codes, week_from, week_to, stage=None, only_qty=False):
        #requierd by the planned
        date_field_id = None
        if not stage:
            raise('Stage is a requierd parameter')
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.PRODUCTION_PLAN,
            }
        if stage == 2 or stage == 'stage2' or stage == 'S2':
            date_field_id = f"{self.f['prod_plan_development_group']}.{self.f['prod_plan_S2_requier_yearweek']}"
        if stage == 3 or stage == 'stage3' or stage == 'S3':
            date_field_id = f"{self.f['prod_plan_S3_requier_yearweek']}" 
        if all_codes:
            match_query.update({f"answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}":all_codes,})
        query= [{'$match': match_query }]
        if stage == 2  or stage == 'stage2' or stage == 'S2':
            query +=[
                {"$unwind": f"$answers.{self.f['prod_plan_development_group']}"},
                {'$match': self.get_date_query(week_from, week_to, date_field_id=date_field_id,  field_type='int')},
                {'$project':
                {'_id': 0,
                    'plant_code': f"$answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}",
                    'year_week': f"$answers.{self.f['prod_plan_development_group']}.{self.f['prod_plan_S2_requier_yearweek']}",
                    'eaches': f"$answers.{self.f['prod_plan_development_group']}.{self.f['prod_plan_require_S2']}",
                    'stage': stage}
                    }
                ]
        if stage == 3 or stage == 'stage3' or stage == 'S3':
            query[0].get('$match').update(self.get_date_query(week_from, week_to, date_field_id=date_field_id, field_type='int'))
            query +=[
                {'$project':
                {'_id': 0,
                    'plant_code': f"$answers.{self.PRODUCT_OBJ_ID}.{self.f['product_code']}",
                    'year_week': f"$answers.{self.f['prod_plan_S3_requier_yearweek']}",
                    'stage': stage,
                    'eaches': "$answers.{self.f['prod_plan_require_S3']}"}
                    }
                ]
        if only_qty == True:
            query +=[
                {'$group':
                    {'_id':
                        {
                          'year_week': '$year_week',
                          },
                      'total': {'$sum': '$eaches'}}},
                {'$project':
                    {
                        'total': '$total'
                    }

                }
                ]
        else:
            query +=[
                {'$group':
                    {'_id':
                        { 'plant_code': '$plant_code',
                          'stage': '$stage',
                          'year_week': '$year_week',
                          },
                      'total': {'$sum': '$eaches'}}},
                {'$project':
                    {
                        '_id': 0,
                        'plant_code': '$_id.plant_code',
                        'stage': '$_id.stage',
                        'year_week': '$_id.year_week',
                        'total': '$total'
                    }

                },
                {'$sort': {'plant_code': 1, 'year_week': 1}}
                ]
        res = self.cr.aggregate(query)
        #print('query_planned , query=', simplejson.dumps(query))
        result = []
        if only_qty:
            total = 0
            for r in res:
                total += r['total']
            return total
        else:
            for r in res:
                r['stage'] = stage
                result.append(r)
        return result

    def query_get_work_orders(self, all_codes, year_weeks):
        year_weeks.sort()

        if year_weeks[0]!=False:
            from_year = int(str(year_weeks[0])[:4])
            to_year =   int(str(year_weeks[-1])[:4])
            from_week = int(str(year_weeks[0])[-2:])
            to_week =   int(str(year_weeks[-1])[-2:])
        else:
            from_year = 0
            to_year = 0
            from_week = 0
            to_week = 0

        match_query = {
            "deleted_at":{"$exists":False},
            "form_id":self.PRODUCTION_FORM_ID,
            f"answers.{self.SKU_OBJ_ID}.{self.f['product_code']}": {"$in": all_codes},
            "$or":
                [{f"answers.{self.f['production_year']}": {"$gte": from_year,"$lte": to_year }},
                {f"answers.{self.f['production_year']}": {"$gte": str(from_year),"$lte": str(to_year) }},
            ],
            "$or":
                [{f"answers.self.f['production_week']": {"$gte": from_week,"$lte": to_week }},
                {f"answers.self.f['production_week']": {"$gte": str(from_week),"$lte": str(to_week) }},
            ],
            }
        query= [{'$match': match_query },
            {'$project':
                {   '_id': 0,
                    'plant_code': f"$answers.{self.SKU_OBJ_ID}.{self.f['product_code']}",
                    'year': f"$answers.{self.f['production_year']}",
                    'week': f"$answers.{self.f['production_week']}",
                    'stage': f"$answers.{self.SKU_OBJ_ID}.{self.f['reicpe_stage']}",
                    'per_container': f"$answers.{self.SKU_OBJ_ID}.{self.f['reicpe_per_container']}",
                    'containers': "$answers.{self.f['production_requier_containers']}"}
                    },
            {'$group':
                {'_id':
                    {
                    'plant_code': '$plant_code',
                    'year': '$year',
                    'week': '$week',
                    'per_container': '$per_container',
                    'stage': '$stage',
                      },
                  'total': {'$sum': '$containers'}}},
            {'$project':
                {
                    '_id':0,
                    'plant_code':'$_id.plant_code',
                    'year':'$_id.year',
                    'week':'$_id.week',
                    'per_container':'$_id.per_container',
                    'stage':'$_id.stage',
                    'total':'$total',
                }
            },
            {'$sort': {'plant_code': 1, }}
            ]

        res = self.cr.aggregate(query)
        result = {}
        for row in res:
            stage = row.get('stage')
            if stage == 'S2' or stage == 's2':
                stage = 2
            if stage == 'S3' or stage == 's3':
                stage = 3
            pcode = row.get('plant_code')
            year = int(row.get('year'))
            week = int(row.get('week'))
            year_week = int('{}{:02d}'.format(year, week))
            per_container = int(row.get('per_container'))
            result[pcode] = result.get('plant_code',{})
            result[pcode][stage] = result[pcode].get(stage,{})
            result[pcode][stage] = {
                year_week:row.get('total',0) * per_container
                }
        return result


if __name__ == "__main__":
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    all_data = report_obj.data
    print('\n\n\n\n\n')
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
    # plant_code = all_data.get("plant_code")
    # report_model = ReportModel()
    #try:
    if True:
        #jwt_complete = simplejson.loads(sys.argv[2])
        #config["USER_JWT_KEY"] = jwt_complete
        #settings.config.update(config)
        week_from = date_to_week(date_from)
        week_to = date_to_week(date_to)

        detail, grouped_res, grouped_week , grouped_cut_day= report_obj.get_report(plant_code, stage, date_from, date_to)
        by_team = report_obj.report_by_team(plant_code, week_from, week_to, stage)
        by_crop_s2 = report_obj.report_by_crop(plant_code, week_from, week_to, stage='S2')
        by_crop_s3 = report_obj.report_by_crop(plant_code, week_from, week_to, stage='S3')
        by_stage = report_obj.report_by_stage(plant_code, week_from, week_to, stage)
        # response = get_requires(plant_code)
        # query_report_second(date_from, date_to )
        # query_report_fourth(date_from, date_to )
        print('REQUIRED=',REQUIRED)
        if not test:
            sys.stdout.write(simplejson.dumps(
                {
                "firstElement":{
                    'tabledata':PRODUCED
                    },
                "secondElement":{
                    'tabledata':REQUIRED
                    },
                "thirdElement":{
                    'tabledata': PRODUCED - REQUIRED
                    },
                "fourthElementCutDay":{
                    'tabledata':grouped_cut_day
                    },
                "fourthElementWeek":{
                    'tabledata':grouped_week
                    },
                "fourthElement":{
                    'tabledata':by_team
                    },
                "fifthElement":{
                    'tabledata':by_crop_s2
                    },
                "sixthElement":{
                    'tabledata':by_crop_s3
                    },
                "seventhElement":{
                    'tabledata':by_stage
                    },
                "eighthElement":{
                    'tabledata':{}
                    },
                "ninthElement":{
                    'tabledata':grouped_res
                    },
                "tenthElement":{
                    'tabledata':detail
                    },
                }
                )
            )
    # except:
    #     sys.stdout.write(simplejson.dumps({"firstElement": {"error":"Something went wrong"}}))
