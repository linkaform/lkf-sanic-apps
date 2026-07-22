#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch

if __name__ == "__main__":
    current_record = simplejson.loads(sys.argv[1])
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    print('..... arranca hook boot_checkin')
    response = dispatch("boot_checkin", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'support_guards': data.get('support_guards', []),
        'checkin_id': data.get('checkin_id', ''),
        'checkin_type': data.get('checkin_type', ''),
        'answers': current_record.get('answers', {}),
    }, method='post', **params)
    sys.stdout.write(simplejson.dumps(response.json()))
