# -*- coding: utf-8 -*-
# Override plano para que get_module_class('Contratistas') (app/loader.py) lo
# encuentre en CUSTOM_MODULE_PATHS, que busca 'contratistas_service.py' /
# 'service.py' antes de caer al fallback lkf_addons.contratistas.app.
# La implementacion real vive en addons/contratistas/service.py.
#
# Punto de extension por cuenta: aqui se sobreescriben metodos para un cliente
# especifico sin tocar el modulo base.
from lkf_addons.contratistas.service import Contratistas


class Contratistas(Contratistas):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
