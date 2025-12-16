# -*- coding: utf-8 -*-

import sys, simplejson
from datetime import datetime, timedelta, date
from copy import deepcopy

from lkf_addons.contratistas.app import Contratistas


class Contratistas(Contratistas):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

        
        self.CATALOGO_CONTRATISTAS = self.lkm.catalog_id('catalogo_de_contratistas_10',{} )
        self.CATALOGO_CONTRATISTAS_ID = self.CATALOGO_CONTRATISTAS.get('id')
        self.CATALOGO_CONTRATISTAS_OBJ_ID = self.CATALOGO_CONTRATISTAS.get('obj_id')