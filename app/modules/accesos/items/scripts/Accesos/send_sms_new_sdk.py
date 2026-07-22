#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch

if __name__ == "__main__":
    current_record = simplejson.loads(sys.argv[1])
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})

    record_id = current_record.get('_id', '')
    if isinstance(record_id, dict):
        record_id = record_id.get('$oid', '')

    print('..... arranca hook send_sms_new')
    response = dispatch("send_sms_new", params={
        'answers': current_record.get('answers', {}),
        'record_id': record_id,
        'pre_sms': data.get('pre_sms', ''),
        'cuenta': data.get('cuenta', ''),
    }, method='post', **params)
    sys.stdout.write(simplejson.dumps(response.json()))
