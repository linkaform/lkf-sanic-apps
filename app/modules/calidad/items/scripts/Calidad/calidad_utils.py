# -*- coding: utf-8 -*-
from datetime import datetime
from linkaform_api import base
from lkf_addons.calidad.app import Calidad
from bson import ObjectId

from linkaform_api import settings, utils
from account_settings import *

class Calidad(Calidad):
    print('Entra a calidad utils')

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        
        # FIELDS
        # self.f.update({})
        