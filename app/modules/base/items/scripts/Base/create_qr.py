# coding: utf-8
import sys, simplejson

from base_utils import Base
from linkaform_api import generar_qr
from account_settings import settings


def create_qr(field_id):
    record_id = base_obj.record_id
    lkf_qr = generar_qr.LKF_QR(settings)
    qr_generado = lkf_qr.procesa_qr( record_id, f"qr_{record_id}", base_obj.form_id, img_field_id=field_id )
    return qr_generado


if __name__ == "__main__":
    base_obj = Base(settings, sys_argv=sys.argv)
    base_obj.console_run()

    field_id = base_obj.data.get('field_id')
    if not field_id:
        base_obj.LKFException({"msg":"No se encontro el dato de field_id en los argumentos de script create_qr. Favor de agregar `fild_id` a los argumentos"})
    if not base_obj.record_id:
        base_obj.record_id = base_obj.object_id()
    base_obj.answers[field_id] = [create_qr(field_id),]
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans':  base_obj.answers,
        'metadata':{"id":base_obj.record_id}

    }))

