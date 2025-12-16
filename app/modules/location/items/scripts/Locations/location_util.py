# -*- coding: utf-8 -*-
from datetime import datetime
from linkaform_api import base
from lkf_addons.location.location_util import Location

class Location(Location):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        #use self.lkm.catalog_id() to get catalog id
        self.name =  __class__.__name__
        self.settings = settings
        self.f.update( {
            'location_id':'68101945f4996c72247baac4',
            })