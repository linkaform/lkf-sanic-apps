# -*- coding: utf-8 -*-
'''
Licencia BSD
Copyright (c) 2024 Infosync / LinkaForm.
Todos los derechos reservados.

Se permite la redistribución y el uso en formas de código fuente y binario, con o sin modificaciones, siempre que se cumplan las siguientes condiciones:

1. Se debe conservar el aviso de copyright anterior, esta lista de condiciones y el siguiente descargo de responsabilidad en las redistribuciones del código fuente.
2. Se debe reproducir el aviso de copyright anterior, esta lista de condiciones y el siguiente descargo de responsabilidad en la documentación y/u otros materiales proporcionados con las distribuciones en formato binario.
3. Ni el nombre del Infosync ni los nombres de sus colaboradores pueden ser utilizados para respaldar o promocionar productos derivados de este software sin permiso específico previo por escrito.
'''
# Re-export de una sola linea, igual que addons/location/app.py.
#
# Es intencional y load-bearing: get_module_class('Contratistas')
# (app/loader.py) NO carga este archivo desde el checkout -- busca
# contratistas_service.py/service.py en CUSTOM_MODULE_PATHS y, si no los
# encuentra, cae a importlib.import_module('lkf_addons.contratistas.app'),
# es decir el paquete instalado. Que app.py reexporte service.py es lo que
# hace que ese fallback entregue la clase completa y no el esqueleto.
from .service import Contratistas
