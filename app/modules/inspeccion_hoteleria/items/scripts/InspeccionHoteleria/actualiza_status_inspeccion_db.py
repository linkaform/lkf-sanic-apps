# -*- coding: utf-8 -*-
import sys
from bson import ObjectId
from actualiza_status_inspeccion import Inspeccion_Hoteleria

from account_settings import *


class Inspeccion_Hoteleria(Inspeccion_Hoteleria):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)

        self.form_ids = {
            'revison_habitacion': self.REVISON_HABITACION,
            'hi_parque_fundidora': self.HI_PARQUE_FUNDIDORA,
            'crowne_plaza_torreon': self.CROWNE_PLAZA_TORREN,
            'travo': self.TRAVO,
            'hie_tecnologico': self.HIE_TECNOLGICO,
            'wyndham_garden_mcallen': self.WYNDHAM_GARDEN_MCALLEN,
            'istay_victoria': self.ISTAY_VICTORIA,
            'hie_torreon': self.HIE_TORREN,
            'hilton_garden_silao': self.HILTON_GARDEN_SILAO,
            'ms_milenium': self.MS_MILENIUM,
            'istay_monterrey_historico': self.ISTAY_MONTERREY_HISTRICO,
            'hie_guanajuato': self.HIE_GUANAJUATO,
            'hie_silao': self.HIE_SILAO,
            'istay_ciudad_juarez': self.ISTAY_CIUDAD_JUREZ,
            'crowne_plaza_mty': self.CROWNE_PLAZA_MONTERREY,
            'hie_galerias': self.HIE_GALERIAS,
            'holiday_inn_tijuana': self.HOLIDAY_INN_TIJUANA,
        }

    def get_form_records(self,  form_id):
        match_query = {
            "deleted_at": {"$exists": False},
            "form_id": form_id,
        }
        res = self.cr.find(match_query)
        return [x for x in res]
        

        
if __name__ == '__main__':
    module_obj = Inspeccion_Hoteleria(settings, sys_argv=sys.argv, use_api=False)
    module_obj.console_run()
    for key, form_id in module_obj.form_ids.items():
        print('Hotel: ', key, ' form_id:', form_id)
        records = module_obj.get_form_records(form_id)
        for record in records:
            module_obj.record_id = record.get('_id')
            module_obj.answers = record.get('answers')
            module_obj.form_id = record.get('form_id')
            module_obj.folio = record.get('folio')
            module_obj.created_at = record.get('created_at')
            score_per_page = module_obj.get_grading_obj()
            res = module_obj.save_results(score_per_page)
            print('folio = ', module_obj.folio)
            starting_status = module_obj.answers.get(module_obj.field_id_status)
            status = module_obj.check_pending_answers() 
            # module_obj.actualiza_status_habitacion()
            # Todo ver q hacer si no se actualzia bien el status de la habitacion....
            if starting_status != status or True:
                res = module_obj.update_status_record(status)
                if res.acknowledged:
                    update_res = module_obj.cr.update_one({'form_id':form_id,'folio':module_obj.folio}, {'$set':{'editable': False}})
        