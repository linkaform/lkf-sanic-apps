#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch

if __name__ == "__main__":
    current_record = simplejson.loads(sys.argv[1])
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option", '')
    print('..... arranca script config_access')
    if option == 'get_user_menu':
        response = dispatch("get_config_accesos", params={}, method='get', **params)
    else:
        response = dispatch("set_config", params={
            'answers': current_record.get('answers', {}),
        }, method='post', **params)
    sys.stdout.write(simplejson.dumps(response.json()))
