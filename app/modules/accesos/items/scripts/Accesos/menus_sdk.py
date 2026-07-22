#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch

def get_menus(params):
    data = params.get("data", {})
    return dispatch("get_menus", params={
        'platform': data.get('platform', ''),
    }, method='get', **params)

def set_permissions(params):
    data = params.get("data", {})
    return dispatch("set_permissions", params={
        'answers': data.get('answers', {}),
        'user_id': data.get('user_id'),
    }, method='post', **params)


DISPATCHER = {
    "get_menus": get_menus,
    "set_permissions": set_permissions,
}


def console_run(self):
    print(f"python { self.argv[0].split('/')[-1]} '{ self.argv[1]}' '{ self.argv[2]}'")

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    console_run(sys)
    data = params.get("data", {})
    option = data.get("option") or params.get('option', '')
    print('..... arranca script menus')
    print('nuevo build..')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
