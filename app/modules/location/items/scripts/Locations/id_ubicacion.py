# -*- coding: utf-8 -*-
import sys, simplejson
from linkaform_api import generar_qr
from account_settings import *

from location_util import Location



class Location(Location):


    def create_qr(self ):
        lkf_qr = generar_qr.LKF_QR(settings)
        record_id = self.record_id
        if type(record_id) == list:
            record_id = record_id[0]

        area = self.answers.get(self.f['area'])
        field_id_qr = self.f['location_id']
        qr_generado = lkf_qr.procesa_qr( record_id, area, self.form_id, img_field_id=field_id_qr )
        self.answers[self.f['area_qr_code']] =  [qr_generado,]


if __name__ == '__main__':
    location_obj = Location(settings, sys_argv=sys.argv)
    location_obj.console_run()
    if not location_obj.record_id:
        location_obj.record_id = location_obj.object_id()
    current_record = location_obj.current_record
    location_obj.answers[location_obj.f['location_id']] = location_obj.record_id 
    location_obj.create_qr()

    sys.stdout.write(simplejson.dumps({
                'status': 101,
                'replace_ans': location_obj.answers,
                'metadata':{"id":location_obj.record_id}
            }))