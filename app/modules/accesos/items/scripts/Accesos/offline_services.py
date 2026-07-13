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
    option = data.get("option", '')
    print('..... arranca script offline_services')

    base_params = {
        'current_record': current_record,
        'user_id': current_record.get('created_by_id'),
    }

    if option == 'get_user_catalogs':
        response = dispatch_with_api_key("get_user_catalogs", api_key, params=base_params, method='post', **params)
    elif option == 'assign_user_inbox':
        response = dispatch_with_api_key("assign_user_inbox", api_key, params={
            **base_params,
            'answers': current_record.get('answers', {}),
            'record_id': current_record.get('_id'),
            'geolocation': current_record.get('geolocation', []),
            'folio': current_record.get('folio'),
        }, method='post', **params)
    elif option == 'complete_rondines':
        response = dispatch_with_api_key("complete_rondines", api_key, params={
            **base_params,
            'records': data.get('records', []),
        }, method='post', **params)
    elif option == 'delete_rondines':
        response = dispatch_with_api_key("delete_rondines", api_key, params={
            **base_params,
            'records': data.get('records', []),
        }, method='post', **params)
    elif option == 'reasignar_rondines':
        response = dispatch_with_api_key("reasignar_rondines", api_key, params={
            **base_params,
            'records': data.get('records', []),
            'user_to_assign': data.get('user_to_assign', {}),
        }, method='post', **params)
    elif option == 'get_active_guards':
        response = dispatch_with_api_key("get_active_guards", api_key, params=base_params, method='post', **params)
    elif option in ('sync', 'synced', 'rondin', 'check_area', 'sync_to_lkf'):
        response = dispatch_with_api_key("sync_records", api_key, params={
            **base_params,
            'records': data.get('records', []),
            'test': data.get('test', False),
        }, method='post', **params)
    elif option == 'clean_db':
        response = dispatch_with_api_key("clean_db", api_key, params=base_params, method='post', **params)
    elif option == 'fix':
        response = dispatch_with_api_key("fix_rondines", api_key, params=base_params, method='post', **params)
    else:
        response = None

    if response is None:
        sys.stdout.write(simplejson.dumps({"error": f"Option '{option}' not supported"}))
    else:
        sys.stdout.write(simplejson.dumps(response.json()))
