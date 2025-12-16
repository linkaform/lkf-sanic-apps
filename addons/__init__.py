#!/usr/local/bin/python
# coding: utf-8

import sys
app_root = '/srv/lkf-sanic-app/app'  
if app_root not in sys.path:
    sys.path.insert(0, app_root)