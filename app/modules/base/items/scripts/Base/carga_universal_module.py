# -*- coding: utf-8 -*-
import sys, simplejson


from lkf_addons.base.app import CargaUniversal
from account_settings import *


if __name__ == '__main__':
    class_obj = CargaUniversal(settings=settings, sys_argv=sys.argv, use_api=True)
    class_obj.console_run()
    resp_cu = class_obj.carga_doctos()