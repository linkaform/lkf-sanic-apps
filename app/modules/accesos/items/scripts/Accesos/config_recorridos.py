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
    print('..... arranca hook config_recorridos')
    response = dispatch_with_api_key("config_recorridos", api_key, params={
        'answers': current_record.get('answers', {}),
        'current_record': current_record,
    }, method='post', **params)
    sys.stdout.write(simplejson.dumps(response.json()))
