#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch

if __name__ == "__main__":
    current_record = simplejson.loads(sys.argv[1])
    params = simplejson.loads(sys.argv[2])
    print('..... arranca hook check_in_manual')
    response = dispatch("check_in_manual", params={
        'current_record': current_record,
        'user_id': current_record.get('user_id'),
        'timezone': current_record.get('timezone', 'America/Mexico_City'),
    }, method='post', **params)
    sys.stdout.write(simplejson.dumps(response.json()))
