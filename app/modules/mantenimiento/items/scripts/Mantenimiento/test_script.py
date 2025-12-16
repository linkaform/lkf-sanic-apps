# coding: utf-8
import sys, simplejson, json
from linkaform_api import settings
from account_settings import *

from mantenimiento_utils import Mantenimiento

class Mantenimiento(Mantenimiento):
    pass

if __name__ == "__main__":
    mantenimiento_obj = Mantenimiento(settings, sys_argv=sys.argv)
    mantenimiento_obj.console_run()
    mantenimiento_obj.test_module()