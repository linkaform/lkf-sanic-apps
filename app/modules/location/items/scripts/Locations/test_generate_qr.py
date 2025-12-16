# -*- coding: utf-8 -*-
import sys, simplejson
from linkaform_api import settings, network, utils, generar_qr
from account_settings import *

from location_util import Location


def create_qr( current_record ):
    record_id = current_record['answers']['664f8ce1aa9907e44a490ee5']['5ea0897550b8dfe1f4d83a9f']
    print('record_id',record_id)
    if type(record_id) == list:
        record_id = record_id[0]

    field_id_qr = '64ef5b5fff1bec97d2ca27b6'
    qr_generado = lkf_qr.procesa_qr( record_id, 'nombre_qr', current_record['form_id'], img_field_id=field_id_qr )
    cr.update({
        'form_id': current_record['form_id'],
        'folio': current_record['folio'],
        'deleted_at': {'$exists': False}
    },{'$set': {
        'answers.{}'.format(field_id_qr): [qr_generado,]
    }})


if __name__ == '__main__':
    print(sys.argv)
    location_obj = Location(settings, sys_argv=sys.argv)
    location_obj.console_run()
    lkf_qr = generar_qr.LKF_QR(settings)
    net = network.Network(settings)
    cr = net.get_collections()
    print(location_obj.current_record)
    create_qr( location_obj.current_record )
