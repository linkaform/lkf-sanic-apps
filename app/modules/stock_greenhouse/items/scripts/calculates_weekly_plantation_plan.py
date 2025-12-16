# -*- coding: utf-8 -*-
import sys, simplejson, math
from datetime import datetime, timedelta

from linkaform_api import settings, utils
#from account_utils import unlist
from account_settings import *
#from account_utils import get_plant_recipe, select_S4_recipe

from lkf_addons.stock_greenhouse.stock_utils import Stock

#from account_utils import Plant, PlantRecipe


def calculations(current_record):
    folio = current_record.get('folio')
    print('******** Folio =', folio)
    # if not current_record.get('folio'):
    if True:
        current_sets = current_record['answers'].get('62e4babc46ff76c5a6bee76c', [])
        new_sets = []
        year = str( current_record['answers'].get('61f1da41b112fe4e7fe8582f', '') ).zfill(2)
        week = str( current_record['answers'].get('61f1da41b112fe4e7fe85830', '') ).zfill(2)
        year_week = year + week
        total_eaches = 0
        total_flats = 0
        total_hrs = 0
        dict_growing = {}
        #Ready YearWeek
        plant_date = datetime.strptime('%04d-%02d-1' % (int(year), int(week)), '%Y-%W-%w')
        for s in current_sets:
            if not s.get('62e4bc58d9814e169a3f6beb'):
                continue
            c = s.get('61ef32bcdf0ec2ba73dec33c')
            plant = s['61ef32bcdf0ec2ba73dec33c']
            required_eaches = s.get('62e4bc58d9814e169a3f6beb')
            total_eaches += required_eaches

            # Obteniendo la Receta
            plant_code = s.get('61ef32bcdf0ec2ba73dec33c', {}).get('61ef32bcdf0ec2ba73dec33d', '')
            # plant = Plant(plant_code, stage='4')
            # ss = plant.get_week_recipe('Ln72',start_size='S4', plant_date=plant_date )
            # print('recipes', ss)
            recipes = stock_obj.get_plant_recipe([plant_code,], stage=[4, 'Ln72',])
            if not recipes.get(plant_code):
                error_msg = {
                        "61ef32bcdf0ec2ba73dec33d": {"msg": [ "No recipe with Start Size S4 found for : {}".format(plant_code)], "label": "Plant code", "error": []}
                    }
                raise Exception(simplejson.dumps(error_msg))
            recipe = stock_obj.select_S4_recipe(recipes[plant_code], week)
            # print('=== recipe',simplejson.dumps(recipe, indent=4))

            #per container
            if folio and plant.get('6205f73281bb36a6f157335b'):
                per_container = plant.get('6205f73281bb36a6f157335b')[0]
            else:
                per_container = recipe.get('per_container')

            qty_per_container = float( per_container )
            subtotal_flats = math.ceil(required_eaches / qty_per_container)
            total_flats += subtotal_flats
            s['63f6db6474ef4ca424ff48e3'] = subtotal_flats

            #Growing Media
            if folio and plant.get('6209705080c17c97320e3383'):
                growing_media = plant.get('6209705080c17c97320e3383')
            else:
                growing_media = recipe.get('soil_type')
            dict_growing[growing_media] = dict_growing.get(growing_media,0)
            dict_growing[growing_media] += subtotal_flats

            #cut_productivity
            if folio and plant.get('6209705080c17c97320e337f'):
                cut_productivity = plant.get('6209705080c17c97320e337f')[0]
            else:
                cut_productivity = recipe.get('cut_productivity',10)

            #Estimated Hours
            est_hours = round(subtotal_flats / cut_productivity, 2)
            s['63ffa3ce39960473f4591ea6'] = est_hours
            total_hrs += est_hours

            #plant Start Week
            if folio and plant.get('6209705080c17c97320e3380'):
                start_week = plant.get('6209705080c17c97320e3380')
                print('ya trae los start weeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeek', start_week)
            else:
                start_week = recipe.get('start_week')

            if folio and plant.get('6205f73281bb36a6f1573357'):
                grow_weeks = plant.get('6205f73281bb36a6f1573357')[0]
                print('ya trae los gorw weeks', grow_weeks)
            else:
                grow_weeks = recipe.get('S4_growth_weeks')

            ready_date = plant_date + timedelta(weeks=grow_weeks)

            #plant name
            if folio and plant.get('61ef32bcdf0ec2ba73dec33e'):
                plant_name = plant.get('61ef32bcdf0ec2ba73dec33e')[0]
            else:
                plant_name = recipe.get('plant_name')

            #Start Size
            if folio and plant.get('6205f73281bb36a6f1573358'):
                start_size = plant.get('6205f73281bb36a6f1573358')
            else:
                start_size = recipe.get('start_size')




            s['63f8f4cad090912501be306a'] = int(ready_date.strftime('%Y%W'))
            # print('=== plant',simplejson.dumps(plant, indent=4))
            s['61ef32bcdf0ec2ba73dec33c'].update({
                '6205f73281bb36a6f1573358': start_size,
                '6209705080c17c97320e3383': growing_media,
                '6209705080c17c97320e3380': start_week,
                #plant.get('6209705080c17c97320e3380',recipe.get('start_week')),
                '61ef32bcdf0ec2ba73dec33e': [plant_name],
                '6205f73281bb36a6f157335b': [per_container],
                '6205f73281bb36a6f1573357': [grow_weeks],
                '6209705080c17c97320e337f': [cut_productivity],
            })
            s['640114b2cc0899ba18000006'] = s.get('640114b2cc0899ba18000006','lab')
            new_sets.append(s)
        if new_sets:
            current_record['answers']['62e4babc46ff76c5a6bee76c'] = new_sets


    current_record['answers']['63f6e1733b076aaf80ff4adb'] = total_eaches
    current_record['answers']['63f6de096468162a9a3c2ef4'] = total_flats
    current_record['answers']['63f6de096468162a9a3c2ef5'] = round(total_hrs, 2)
    current_record['answers']['62e4bd2ed9814e169a3f6bef'] = current_record['answers'].get('62e4bd2ed9814e169a3f6bef','planning')

    list_soils_requirements = []
    for growing in dict_growing:
        list_soils_requirements.append({
            '63f6de5f6468162a9a3c2f09': growing,
            '63f6de5f6468162a9a3c2f0a': dict_growing[growing]
        })
    if list_soils_requirements:
        current_record['answers']['63f6de096468162a9a3c2ef3'] = list_soils_requirements

    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': current_record['answers'],
    }))

if __name__ == '__main__':
    print(sys.argv)
    stock_obj = Stock(settings, sys_argv=sys.argv)
    current_record = stock_obj.current_record
    calculations(current_record)
