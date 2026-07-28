#!/usr/local/bin/python
# coding: utf-8


from sanic import Blueprint
from sanic.request import Request
from sanic.response import json


#     return json(res, status=201)


from lkf_addons.location.routes import location_bp, service