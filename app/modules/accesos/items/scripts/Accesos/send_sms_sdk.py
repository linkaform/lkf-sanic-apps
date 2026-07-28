#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, json, lkf_addons
from middleware.auth import dispatch


if __name__ == "__main__":
    # qr_code llega en sys.argv[1] como el _id (extended JSON) del pase que disparó el workflow.
    record = json.loads(sys.argv[1])
    qr_code = record.get('_id', '').get('$oid', '')

    # pre_sms/cuenta llegan en el nivel superior de sys.argv[2], no anidados bajo "data".
    params = simplejson.loads(sys.argv[2])
    pre_sms_value = params.get('pre_sms', '')
    cuenta_value = params.get('cuenta', '')

    if isinstance(pre_sms_value, bool):
        pre_sms = pre_sms_value
    else:
        pre_sms = pre_sms_value.lower() == 'true'

    response = dispatch("send_pase_sms", params={
        'qr_code': qr_code,
        'pre_sms': pre_sms,
        'cuenta': cuenta_value,
    }, method='post', **params)
    sys.stdout.write(simplejson.dumps(response.json()))
