#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from linkaform_api import settings
from account_settings import *
from middleware.auth import dispatch_with_api_key

if __name__ == "__main__":
    current_record = simplejson.loads(sys.argv[1])
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    api_key = data.get('api_key') or config.get('APIKEY')
    print('..... arranca rutina update_status_pass')
    response = dispatch_with_api_key("update_status_pass", api_key, params={
        'current_record': current_record,
        'answers': current_record.get('answers', {}),
    }, method='post', **params)
    sys.stdout.write(simplejson.dumps(response.json()))
