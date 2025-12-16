# -*- coding: utf-8 -*-
"""
Se ejecuta en la forma Pagos SAP (Complementos de Pagos) con flujo despues de crear el registro porque nacen como pendiente y los contratistas NO deben facturar
También se puede ejecutar en la forma Contratistas para Complementos de Pago cuando Autorizan la facturacion sin complemento
Tambien se puede ejecutar en la forma Complementos de Pago Despues de crear el registro
"""
import sys, simplejson
from produccion_pci_utils import Produccion_PCI
from account_settings import *

class AutorizarComplementosDePago(Produccion_PCI):
    """docstring for AutorizarComplementosDePago"""
    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

    def get_contratista_complemento_contratista_principal( self, contratista_principal ):
        """
        Obtiene el registro donde está el contratista principal con su grupo
        """
        return self.get_records(
            self.FORMA_COMPLEMENTOS_PAGO, 
            query_answers={'answers.62d071930a1b1ff9eaa3c0f4': contratista_principal}, 
            select_columns=['answers', 'folio']
        )

    def procesar_autorizaciones(self):
        if self.form_id == self.FORMA_PAGOS_SAP:
            # Si es de la forma Pagos SAP (Complementos de Pagos) debo obtener el nombre del contratista principal para despues buscar sus cuentas
            contratista_principal = self.answers.get('62d06e922fd9244967a3c167', '')
            contratistas = get_contratista_complemento_contratista_principal(contratista_principal)
            for r in contratistas:
                cuentas_contratistas = r['answers'].get('62d071173eeb3a67815c74fe', [])
                # Se desactivan las cuentas de los contratistas para que NO puedan facturar
                p_utils.complementos_cuentas_contratistas(cuentas_contratistas, 'No')
        else:
            # Desde la forma Contratistas para Complementos de Pago cuando activan la facturacion sin complemento
            cuentas_contratistas = self.answers.get('62d071173eeb3a67815c74fe', [])
            autorizar_sin_complemento = self.answers.get('62d071930a1b1ff9eaa3c0f5', 'no')
            autorizacion_facturar = 'No' if autorizar_sin_complemento == 'no' else 'Sí'
            p_utils.complementos_cuentas_contratistas(cuentas_contratistas, autorizacion_facturar)

if __name__ == '__main__':
    lkf_obj = AutorizarComplementosDePago(settings, sys_argv=sys.argv)

    from pci_base_utils import PCI_Utils
    p_utils = PCI_Utils(cr=lkf_obj.cr, lkf_api=lkf_obj.lkf_api, settings=settings, lkf_obj=lkf_obj)

    lkf_obj.procesar_autorizaciones()