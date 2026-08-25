#!/usr/local/bin/python
# coding: utf-8
# Override plano por cuenta: app/loader.py (extend_routes -> find_module_file)
# busca '<modulo>_routes.py' en CUSTOM_MODULE_PATHS ANTES de usar el blueprint
# base, empezando por los scripts de la cuenta en
# /srv/backend.linkaform.com/.../public-client-{account_id}/scripts/.
#
# Reexportar el blueprint real permite desplegar/probar en una sola cuenta sin
# rebuild de la imagen. Ver el equivalente en
# app/modules/location/items/scripts/Locations/location_routes.py

from lkf_addons.contratistas.routes import contratistas_bp, service
