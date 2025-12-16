# -*- coding: utf-8 -*-

import sys, simplejson
from datetime import datetime, timedelta, date
from copy import deepcopy

from lkf_addons.restore_folios_produccion_pci.app import RestoreFoliosProduccion

class RestoreFoliosProduccion(RestoreFoliosProduccion):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)