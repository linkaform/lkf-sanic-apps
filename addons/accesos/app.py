# -*- coding: utf-8 -*-
"""
Re-exporta la clase Accesos para que otros modulos puedan componerla via
self.load(module='Accesos', **self.kwargs) (que importa lkf_addons.accesos.app
por convencion, igual que Employee/Location/Activo_Fijo). La logica real vive
en service.py; este archivo es solo el punto de entrada esperado por load().
"""
from .service import Accesos
