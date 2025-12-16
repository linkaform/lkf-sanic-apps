# -*- coding: utf-8 -*-
import sys, simplejson
from linkaform_api import generar_qr
from account_settings import *

from location_util import Location


class Location(Location):


    def create_qr(self ):
        lkf_qr = generar_qr.LKF_QR(settings)
        record_id = self.record_id
        print('record_id',record_id)
        if type(record_id) == list:
            record_id = record_id[0]

        area = self.answers.get(self.f['area'])
        location = self.answers.get(self.UBICACIONES_CAT_OBJ_ID,{}).get(self.f['location'])
        print('area', area)
        print('location', location)
        field_id_qr = self.f['area_qr_code']
        url= f'https://srv.linkaform.com/solucion_accesos/ingreso.html?caseta="{area}"&ubicacion="{location}"&acc_id={self.user.get("user_id", 0)}'
        print('url', url)
        qr_generado = lkf_qr.procesa_qr( url, area, self.form_id, img_field_id=field_id_qr )
        self.cr.update_one({
            'form_id': self.form_id,
            'folio': self.folio,
            'deleted_at': {'$exists': False}
        },{'$set': {
            f'answers.{field_id_qr}': [qr_generado,]
        }})


if __name__ == '__main__':
    print(sys.argv)
    location_obj = Location(settings, sys_argv=sys.argv)
    location_obj.console_run()
    print(location_obj.current_record)
    location_obj.create_qr()
