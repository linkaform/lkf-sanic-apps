#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch

if __name__ == "__main__":
    current_record = simplejson.loads(sys.argv[1])
    params = simplejson.loads(sys.argv[2])
    print('..... arranca hook update_qr')
    response = dispatch("update_qr", params={
        'answers': current_record.get('answers', {}),
    }, method='post', **params)
    sys.stdout.write(simplejson.dumps(response.json()))
