#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from linkaform_api import settings
from account_settings import *
from middleware.auth import dispatch_with_api_key

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    api_key = data.get('api_key') or config.get('APIKEY')
    print('..... arranca script close_rondines')
    response = dispatch_with_api_key("close_rondines", api_key, params={}, method='post', **params)
    sys.stdout.write(simplejson.dumps(response.json()))
