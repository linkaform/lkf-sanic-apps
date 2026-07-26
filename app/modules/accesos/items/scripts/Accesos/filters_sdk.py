#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch

DISPATCHER = {
    "recorridos": "filters_recorridos",
    "rondines": "filters_rondines",
    "check_areas": "filters_check_areas",
    "incidencias_rondines": "filters_incidencias_rondines",
    "incidencias": "filters_incidencias",
    "fallas": "filters_fallas",
    "in_and_out": "filters_in_and_out",
    "pases": "filters_pases",
    "paqueteria": "filters_paqueteria",
    "concesionados": "filters_concesionados",
    "perdidos": "filters_perdidos",
    "notas": "filters_notas",
    "areas": "filters_areas",
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option", '')
    print('..... arranca script filters')
    endpoint = DISPATCHER.get(option)
    if not endpoint:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = dispatch(endpoint, params={}, method='get', **params)
        sys.stdout.write(simplejson.dumps(response.json()))
