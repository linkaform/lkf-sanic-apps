# -*- coding: utf-8 -*-
# Override plano para que get_module_class('Location') lo encuentre en
# CUSTOM_MODULE_PATHS (busca 'location_service.py'/'service.py' antes de caer
# al fallback lkf_addons.location.app, que no tiene el CRUD de Ubicaciones).
# Ver addons/location/service.py en lkf-sanic-apps para la implementación real.
from datetime import datetime, timedelta
from bson import ObjectId
from linkaform_api import base
from lkf_addons.location.service import Location
import pytz, simplejson


from sanic import Blueprint
from sanic.request import Request
from sanic.response import json



class Location( Location):
    print('Entra a LocationLocationLocationLocationLocation')

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)