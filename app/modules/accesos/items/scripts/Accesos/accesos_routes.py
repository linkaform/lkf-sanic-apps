#!/usr/local/bin/python
# coding: utf-8


from sanic import Blueprint
from sanic.request import Request
from sanic.response import json


#     return json(res, status=201)


from lkf_addons.accesos.routes import accesos_bp

accesos_bp = Blueprint("accesos", url_prefix="/accesos")

@accesos_bp.get("/pases_dos")
async def get_pases_dos(request: Request):
    res = {"data": "Hola Mundo"}
    return json(res, status=201)

@accesos_bp.get("/pases_tres")
async def get_pases_tres(request: Request):
    res = {"data": "Hola Mundo 4546546"}
    return json(res, status=201)


# @accesos_bp.get("/pases")
# async def get_pases(request: Request):
#     res = {"data": "Hola Mundo OVERWRITE"}
#     return json(res, status=201)