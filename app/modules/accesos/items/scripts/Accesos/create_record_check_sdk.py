#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from linkaform_api import settings
from account_settings import *
from middleware.auth import dispatch_with_api_key


def add_record_check(params, api_key):
    data = params.get("data", {})
    return dispatch_with_api_key("add_record_check", api_key, params={
        'formInformation': data.get('formInformation', {}),
        'folioUpdate': data.get('folioUpdate', ''),
    }, method='post', **params)

def add_inspection_check(params, api_key):
    data = params.get("data", {})
    return dispatch_with_api_key("add_inspection_check", api_key, params={
        'formInformation': data.get('formInformation', {}),
    }, method='post', **params)

def add_record_bitacora(params, api_key):
    data = params.get("data", {})
    return dispatch_with_api_key("add_record_bitacora_tag", api_key, params={
        'tagId': data.get('tagId', ''),
        'config': data.get('config', ''),
    }, method='post', **params)

def get_catalog(params, api_key):
    data = params.get("data", {})
    return dispatch_with_api_key("get_catalog_tag", api_key, params={
        'tagId': data.get('tagId', ''),
    }, method='get', **params)

def get_config(params, api_key):
    data = params.get("data", {})
    return dispatch_with_api_key("get_config_rondines_tag", api_key, params={
        'tagId': data.get('tagId', ''),
    }, method='get', **params)

def update_record_bitacora(params, api_key):
    data = params.get("data", {})
    return dispatch_with_api_key("update_record_bitacora_tag", api_key, params={
        'folioUpdate': data.get('folioUpdate', ''),
    }, method='get', **params)

def get_information_tag(params, api_key):
    data = params.get("data", {})
    return dispatch_with_api_key("get_information_tag", api_key, params={
        'tagId': data.get('tagId', ''),
    }, method='get', **params)

def update_information_tag(params, api_key):
    data = params.get("data", {})
    return dispatch_with_api_key("update_information_tag", api_key, params={
        'tagId': data.get('tagId', ''),
        'listImagesDic': data.get('listImagesDic', []),
        'idCatalog': data.get('idCatalog', ''),
    }, method='post', **params)


DISPATCHER = {
    "add_record_check": add_record_check,
    "add_inspection_check": add_inspection_check,
    "add_record_bitacora": add_record_bitacora,
    "get_catalog": get_catalog,
    "get_config": get_config,
    "update_record_bitacora": update_record_bitacora,
    "get_information_tag": get_information_tag,
    "update_information_tag": update_information_tag,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option", "")
    api_key = data.get('api_key') or config.get('APIKEY')
    print('..... arranca script create_record_check')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params, api_key)
        sys.stdout.write(simplejson.dumps(response.json()))
