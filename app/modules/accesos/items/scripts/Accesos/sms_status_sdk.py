#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def send_cel_msj(params):
    data = params.get("data", {})
    return dispatch("send_cel_msj", params={
        'data_cel_msj': data.get('data_cel_msj', {}),
    }, method='post', **params)


DISPATCHER = {
    "send_cel_msj": send_cel_msj,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option", "send_cel_msj")
    print('..... arranca script sms_status')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
