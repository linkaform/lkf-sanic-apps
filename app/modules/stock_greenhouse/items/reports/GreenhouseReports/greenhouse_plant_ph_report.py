#-*- coding: utf-8 -*-
import simplejson, sys, string
from linkaform_api import settings
from bson import ObjectId
import time
from datetime import datetime, timedelta, date

from gh_stock_report import Reports
from account_settings import *

# --- Class
class Reports(Reports):
    mf = {
        'catalog_product':'6442cbafb1b1234eb68ec178',
        'catalog_product_lot':'620a9ee0a449b98114f61d77',
        'catalog_product_plant':'61ef32bcdf0ec2ba73dec33d',
        'ec_data':'642acda613213ee1e53b6955',
        'ph_data':'644802d7b422f1278e8ec213',
        'product_code':'61ef32bcdf0ec2ba73dec33d',
        'product_lot':'620a9ee0a449b98114f61d77',
        'set_table_plant':'642acd3844f266e70d8602c1',
    }
    # --- FORMAT
    def set_format_graphic(self, data_avg, data_general):
        #---Datasets Avg
        dic_plants = {};
        list_datasets_ph_avg = []
        list_datasets_ec_avg = []
        for x in data_avg:
            plant_code = x.get('plant_code','')
            ready_year_week = x.get('ready_year_week','')
            created_at = x.get('created_at','')
            ph_data_avg = x.get('ph_data_avg','')
            ec_data_avg = x.get('ec_data_avg','')
            key_plant = f"{plant_code}-{ready_year_week}"
            if key_plant!='' and key_plant not in dic_plants:
                dic_plants[key_plant] = []
                dic_plants[key_plant].append({ 
                    'ph_data_avg':ph_data_avg,
                    'ec_data_avg':ec_data_avg,
                    'created_at':created_at,
                })
            elif key_plant!='' and key_plant in dic_plants:
                dic_plants[key_plant].append({ 
                    'ph_data_avg':ph_data_avg,
                    'ec_data_avg':ec_data_avg,
                    'created_at':created_at,
                })

        for key in dic_plants:
            data_plant = dic_plants[key];
            list_set_ph = {
                'type':'line',
                'label': f'Average {key}', 
                'data': [],
                'backgroundColor': "#686D76",
                'borderColor': "#686D76",
                'fill': 'false',
                'borderWidth': 2,
                "pointRadius": 6,
            }
            list_set_ec = {
                'type':'line',
                'label': f'Average {key}',
                'data': [],
                'backgroundColor': "#686D76",
                'borderColor': "#686D76",
                'fill': 'false',
                'borderWidth': 2,
                "pointRadius": 6,
            }

            for value_plant in data_plant:
                created_at = value_plant.get('created_at','')
                ph_data_avg = value_plant.get('ph_data_avg','')
                ec_data_avg = value_plant.get('ec_data_avg','')
                list_set_ph['data'].append({'x':created_at,'y':ph_data_avg})
                list_set_ec['data'].append({'x':created_at,'y':ec_data_avg})
                    
            list_datasets_ph_avg.append(list_set_ph)
            list_datasets_ec_avg.append(list_set_ec)
        
        #---Datasets General
        dic_plants = {};
        list_datasets_general_ph = []
        list_datasets_general_ec = []
        for x in data_general:
            plant_code = x.get('plant_code','')
            ready_year_week = x.get('ready_year_week','')
            ph_data = x.get('ph_data','')
            ec_data = x.get('ec_data','')
            created_at = x.get('created_at','')
            key_plant = f"{plant_code}-{ready_year_week}"

            if key_plant!='' and key_plant not in dic_plants:
                dic_plants[key_plant] = []
                dic_plants[key_plant].append({ 
                    'ph_data':ph_data,
                    'ec_data':ec_data,
                    'created_at':created_at,
                    'ready_year_week':ready_year_week,
                })
            elif key_plant!='' and key_plant in dic_plants:
                dic_plants[key_plant].append({ 
                    'ph_data':ph_data,
                    'ec_data':ec_data,
                    'created_at':created_at,
                    'ready_year_week':ready_year_week,
                })

        for key in dic_plants:
            data_plant = dic_plants[key];
            list_set_ph = {
                'type': 'scatter', 
                'label': f'Readings {key}',
                'data': [],
                'backgroundColor': "#EF6262",
                'borderColor': "#EF6262",
                "borderWidth": 1,
            }
            list_set_ec = {
                'type': 'scatter', 
                'label': f'Readings {key}',
                'data': [],
                'backgroundColor': "#EF6262",
                'borderColor': "#EF6262",
                "borderWidth": 1,
            }
            for value_plant in data_plant:
                created_at = value_plant.get('created_at','')
                ph_data = value_plant.get('ph_data','Nan')
                ec_data = value_plant.get('ec_data','Nan')
                list_set_ph['data'].append({'y':ph_data,'x':created_at})
                list_set_ec['data'].append({'y':ec_data,'x':created_at})
            list_datasets_general_ph.append(list_set_ph)  
            list_datasets_general_ec.append(list_set_ec)  

        combiend_datasets_ph = {'datasets':list_datasets_general_ph + list_datasets_ph_avg}
        combiend_datasets_ec = {'datasets':list_datasets_general_ec + list_datasets_ec_avg}
        return combiend_datasets_ph, combiend_datasets_ec

    def set_format_table(self, data):
        dic_all_plants = {};
        list_datatable = []
        for x in data:
            plant_code = x.get('plant_code','')
            ready_year_week = x.get('ready_year_week','')
            ph_data = x.get('ph_data','')
            ec_data = x.get('ec_data','')
            created_at = x.get('created_at','')

            if plant_code!='' and plant_code not in dic_all_plants:
                dic_all_plants[plant_code] = []
                dic_all_plants[plant_code].append({ 
                    'ph_data':ph_data,
                    'ec_data':ec_data,
                    'created_at':created_at,
                    'ready_year_week':ready_year_week,
                })
            elif plant_code!='' and plant_code in dic_all_plants:
                dic_all_plants[plant_code].append({ 
                    'ec_data':ec_data,
                    'ph_data':ph_data,
                    'created_at':created_at,
                    'ready_year_week':ready_year_week,
                })

        #----Table
        for key in dic_all_plants:
            data_plant = dic_all_plants[key]
            dic_information = {'plant_code':key,'_children':[]}
            for value_plant in data_plant:
                created_at = value_plant.get('created_at','')
                ph_data = value_plant.get('ph_data','')
                ec_data = value_plant.get('ec_data','')
                ready_year_week = value_plant.get('ready_year_week','')
                dic_information['_children'].append({
                    'created_at':created_at,
                    'ec_data':ec_data,
                    'ph_data':ph_data,
                    'lot':ready_year_week,
                })
            list_datatable.append(dic_information)
        
        return list_datatable

    # --- QUERY
    def query_get_avreage(self, date_from, date_to,  product_code, lot_number):
        global report_model

        match_query = { 
            "form_id": 108934,
            "deleted_at":{"$exists":False},
        }
        
        #---Filter
        if product_code and product_code!='':
            match_query.update({f"answers.{self.mf['catalog_product']}.{self.mf['catalog_product_plant']}":product_code})

        if lot_number and lot_number!='':
            match_query.update({f"answers.{self.mf['catalog_product']}.{self.mf['catalog_product_lot']}":int(lot_number)})

        #---Date
        if date_from:
            date_from = datetime.strptime(date_from, "%Y-%m-%d")

        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d")

        match_query.update(self.get_date_query(date_from, date_to))
        

        query = [
            {"$match": match_query},
            {"$unwind": f"$answers.{self.mf['set_table_plant']}"},
            {
                "$project": {
                    "_id": 0,
                    "plant_code": f"$answers.{self.mf['catalog_product']}.{self.mf['product_code']}",
                    "ready_year_week": f"$answers.{self.mf['catalog_product']}.{self.mf['product_lot']}",
                    "ph_data": f"$answers.{self.mf['set_table_plant']}.{self.mf['ph_data']}",
                    "ec_data": f"$answers.{self.mf['set_table_plant']}.{self.mf['ec_data']}",
                    "created_at": {"$dateToString":{"date":"$created_at","format":"%Y-%m-%d"}},
                }
            },
            {
                "$group": {
                    "_id": {
                        "plant_code": "$plant_code",
                        "ready_year_week": "$ready_year_week",
                        "created_at":"$created_at"
                    },
                    "ph_data_avg": {"$avg":"$ph_data"},
                    "ec_data_avg": {"$avg":"$ec_data"}
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "plant_code": "$_id.plant_code",
                    "ready_year_week": "$_id.ready_year_week",
                    "created_at": "$_id.created_at",
                    "ph_data_avg": "$ph_data_avg",
                    "ec_data_avg": "$ec_data_avg",
                }
            },
            {
                "$sort": {
                    "created_at": 1,
                    "plant_code":1,
                    "ready_year_week":1
                }
            }
        ]
        result = self.cr.aggregate(query)
        result_iteration = [x for x in result]
        #result_format = self.set_format_average(result)
        return result_iteration

    def query_get_data(self, date_from, date_to, product_code, lot_number):
        global report_model

        match_query = { 
            "form_id": 108934,
            "deleted_at":{"$exists":False},
        }
        #---Filter
        if product_code and product_code!='':
            match_query.update({f"answers.{self.mf['catalog_product']}.{self.mf['catalog_product_plant']}":product_code})

        if lot_number and lot_number!='':
            match_query.update({f"answers.{self.mf['catalog_product']}.{self.mf['catalog_product_lot']}":int(lot_number)})

        #---Date
        if date_from:
            date_from = datetime.strptime(date_from, "%Y-%m-%d")

        if date_to:
            date_to = datetime.strptime(date_to, "%Y-%m-%d")

        match_query.update(self.get_date_query(date_from, date_to))

        query = [
            {"$unwind": f"$answers.{self.mf['set_table_plant']}"},
            {"$match": match_query},
            {
                "$project": {
                    "_id": 0,
                    "plant_code": f"$answers.{self.mf['catalog_product']}.{self.mf['product_code']}",
                    "ready_year_week": f"$answers.{self.mf['catalog_product']}.{self.mf['product_lot']}",
                    "ph_data": f"$answers.{self.mf['set_table_plant']}.{self.mf['ph_data']}",
                    "ec_data": f"$answers.{self.mf['set_table_plant']}.{self.mf['ec_data']}",
                    "created_at":{"$dateToString":{"date":"$created_at","format":"%Y-%m-%d"}},
                }
            },
            {
                "$sort": {
                    "created_at": 1,
                    "plant_code":1,
                    "ready_year_week":1
                }
            }
        ]
        result = self.cr.aggregate(query)
        result_iteration = [x for x in result]
        #result_format_graphic,result_format_table  = self.set_format_data(result)
        #return result_format_graphic,result_format_table
        return result_iteration;

    def query_get_filter(self):
        match_query = { 
            "form_id": 108934,
            "deleted_at":{"$exists":False},
        }

        query = [
            {"$unwind": f"$answers.{self.mf['set_table_plant']}"},
            {
                "$project": {
                    "_id": 0,
                    "plant_code": f"$answers.{self.mf['catalog_product']}.{self.mf['product_code']}",
                    "ready_year_week": f"$answers.{self.mf['catalog_product']}.{self.mf['product_lot']}",
                }
            },
            {
                "$sort": {
                    "plant_code":1,
                    "ready_year_week":1
                }
            }
        ]
        result = self.cr.aggregate(query)
        result_format  = self.set_format_filter(result)
        return result_format

if __name__ == "__main__":
    report_obj = Reports(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()
    plants = {}
    data = report_obj.data
    data = data.get('data',[])
    test = data.get("test", False)
    #---Filters
    date_to = data.get("date_to",'')
    date_from = data.get("date_from",'')
    product_code = data.get("productCode",'')
    lot_number = data.get("lotNumber",'')
    #--Test
    #product_code = 'LAGBG'
    #lot_number = 202426
    #---Function
    response_average = report_obj.query_get_avreage(date_from, date_to, product_code, lot_number)
    response_data = report_obj.query_get_data(date_from, date_to, product_code, lot_number)
    res_graphic_ph, res_graphic_ec = report_obj.set_format_graphic(response_average, response_data)
    res_table_product = report_obj.set_format_table(response_data)
    sys.stdout.write(simplejson.dumps(
        {
            "firstElement":res_table_product,
            "secondElement":res_graphic_ph,
            "thirdElement":res_graphic_ec,
        },
    ))
