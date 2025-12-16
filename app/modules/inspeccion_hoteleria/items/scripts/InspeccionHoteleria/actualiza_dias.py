# -*- coding: utf-8 -*-
import sys, simplejson
from bson import ObjectId

from inspeccion_hoteleria_utils import Inspeccion_Hoteleria

from account_settings import *


preguntas_revisar = ['67ed67dfc61cd5bd89f317f9',
                    '67ed67dfc61cd5bd89f317fa',
                    '67ed662ab178b35ea5a103b8',
                    '67ed662ab178b35ea5a103b9']

class Inspeccion_Hoteleria(Inspeccion_Hoteleria):

    def get_autidotira_en_proceso(self):
        fomrs_hoteles = [
            self.HI_PARQUE_FUNDIDORA,
            self.CROWNE_PLAZA_TORREN,
            self.TRAVO,
            self.HIE_TECNOLGICO,
            self.WYNDHAM_GARDEN_MCALLEN,
            self.ISTAY_VICTORIA,
            self.HIE_TORREN,
            self.HILTON_GARDEN_SILAO,
            self.MS_MILENIUM,
            self.ISTAY_MONTERREY_HISTRICO,
            self.HIE_GUANAJUATO,
            self.HIE_SILAO,
            self.ISTAY_CIUDAD_JUREZ,
            self.CROWNE_PLAZA_MONTERREY,
            self.HIE_GALERIAS,
            self.HOLIDAY_INN_TIJUANA]
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": {"$in":fomrs_hoteles},
            f"answers.{self.field_id_status}": 'proceso',
        }
        res = self.cr.find(
            match_query, 
            {
                'folio':1, 
                'form_id':1, 
                f"answers.{self.field_id_status}":1,
                f"answers.{self.f['dias_proceso']}":1,
                }
            )
        return self.format_cr(res)

    def update_dias_auditoria(self):
        auditorias = self.get_autidotira_en_proceso()
        update_by_form_day = {}
        for aud in auditorias:
            dias = aud.get('dias_proceso',0)
            form_id = aud['form_id']
            day_plus_one = dias + 1
            update_by_form_day[form_id] = update_by_form_day.get(form_id,{})
            update_by_form_day[form_id][day_plus_one] = update_by_form_day[form_id].get(day_plus_one,[])
            update_by_form_day[form_id][day_plus_one].append(aud['_id'])

        for form_id, record_by_day in update_by_form_day.items():
            for day, record_ids in record_by_day.items():
                match_query = {'_id':{'$in':[ObjectId(r) for r in record_ids]}}
                set_answers = {f"answers.{self.f['dias_proceso']}": day}
                if day > 7:
                    set_answers.update({
                        f'answers.{self.field_id_status}':'incompleta',
                        'editable': False
                        })
                update_res = self.cr.update_many(match_query, {'$set':set_answers})
                # res = self.lkf_api.patch_multi_record( answers = answers, form_id=form_id, record_id=record_ids)
                # print('update_res',dir(update_res))

        return False

if __name__ == '__main__':
    module_obj = Inspeccion_Hoteleria(settings, sys_argv=sys.argv, use_api=True)
    module_obj.console_run()
    module_obj.update_dias_auditoria()

