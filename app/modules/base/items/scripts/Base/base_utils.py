# -*- coding: utf-8 -*-
from datetime import datetime
from linkaform_api import base
from lkf_addons.base.app import Base


class Base(Base):
    print('Entra a base utils')

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

