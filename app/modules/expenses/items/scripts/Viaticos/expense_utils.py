# -*- coding: utf-8 -*-
import sys, simplejson

from lkf_addons.expenses.expense_utils import Expenses

from account_settings import *

class Expenses(Expenses):
    """docstring for ClassName"""
    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.f.update({})

    def validaciones_solicitud(self):
        print('Editado el 7 de diciembre!!! ....')
        result = super().validaciones_solicitud()
        return result
