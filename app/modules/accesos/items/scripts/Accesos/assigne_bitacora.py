# coding: utf-8
import sys
from linkaform_api import settings
from account_settings import *

from accesos_utils import Accesos

class Accesos(Accesos):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)


    def get_active_guards_in_location(self, location):
        query = [
            {"$match": {
                "deleted_at": {"$exists": False},
                "form_id": self.REGISTRO_ASISTENCIA,
                f"answers.{self.f['start_shift']}": {"$exists": True},
                f"answers.{self.f['end_shift']}": {"$exists": False},
                f"answers.{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['ubicacion']}": location,
            }},
            {"$project": {
                "_id": 1,
                "created_at": 1,
                "created_by_id": 1,
            }},
            {"$sort": {
                "created_at": -1
            }},
            {"$limit": 1}

        ]
        response = self.format_cr(self.cr.aggregate(query), get_one=True)
        return response.get('created_by_id')


    def assigne_bitacora(self):
        location = self.answers.get(self.CONFIGURACION_RECORRIDOS_OBJ_ID,{}).get(self.f['ubicacion'], None)
        print('location', location)
        if not location:
            return
        user_id = self.get_active_guards_in_location(location=location)
        if user_id:
            print('Assigning user_id', user_id)
            res = self.lkf_api.assigne_user_records(user_id, [self.record_id,])
            print('res', res)
            
if __name__ == "__main__":
    script_obj = Accesos(settings, sys_argv=sys.argv)
    script_obj.console_run()
    script_obj.assigne_bitacora()