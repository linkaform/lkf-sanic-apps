# -*- coding: utf-8 -*-
"""
Script que se ejecuta desde Airflow para procesar los folios de Orden de servicio
y crear los registros de Liberaciones y de Orden de Compra
"""
import sys, simplejson
from produccion_pci_utils import Produccion_PCI

from account_settings import *

class EjecutarLiberaciones( Produccion_PCI ):
    """docstring for EjecutarLiberaciones"""
    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

    def ejecutar_liberaciones(self):
        print('... ... Ejecutando proceso de Liberaciones ... ...')
        self.next_step_process()
        # print('.. por ahora no se hace nada')

if __name__ == '__main__':
    lkf_obj = EjecutarLiberaciones(settings, sys_argv=sys.argv)
    lkf_obj.ejecutar_liberaciones()