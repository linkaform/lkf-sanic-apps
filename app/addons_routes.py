#!/usr/local/bin/python
# coding: utf-8

from loader import extend_routes

#### Subscribir aqui routas de modulos a cargar
from lkf_addons.accesos.routes import accesos_bp
from lkf_addons.employee.routes import employee_bp
from lkf_addons.location.routes import location_bp
from lkf_addons.contratistas.routes import contratistas_bp

### Extend routes de modulos

blueprints = [
    'Accesos',
    'Employee',
    'Location',
    'Contratistas'
    ]


for bp in blueprints:
    bp_name =  bp.lower() + '_bp'
    extend_routes(eval(bp_name), bp)


