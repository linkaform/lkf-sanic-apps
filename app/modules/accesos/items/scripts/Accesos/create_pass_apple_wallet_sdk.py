#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    print('..... arranca script create_pass_apple_wallet')
    response = dispatch("create_pass_apple_wallet", params={
        'record_id': data.get('record_id', ''),
    }, method='post', **params)
    sys.stdout.write(simplejson.dumps(response.json()))
