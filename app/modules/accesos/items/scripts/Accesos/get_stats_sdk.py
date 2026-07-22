#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def get_stats(params):
    data = params.get("data", {})
    return dispatch("get_stats", params={
        'area': data.get('area', ''),
        'location': data.get('location', ''),
        'page': data.get('page', ''),
    }, method='get', **params)


DISPATCHER = {
    "get_stats": get_stats,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option")
    print('..... arranca script get_stats')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
