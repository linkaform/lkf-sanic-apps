# coding: utf-8
#####
# Script para obtener subtotales y totales en forma Orden de Servicio
# Forma: Orden de Servicio
#####
import sys, simplejson, json
from linkaform_api import settings
from account_settings import *

from mantenimiento_utils import Mantenimiento

class Mantenimiento(Mantenimiento):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.load(module='Product', **self.kwargs)

    def get_grupo_refacciones_total(self, data):
        total = 0
        grupo_refacciones = data.get(self.Product.f['grupo_refacciones'])
        for refaccion in grupo_refacciones:
            cantidad = refaccion.get(self.Product.f['refaccion_cantidad'])
            costo_unitario = refaccion.get(self.Product.f['refaccion_costo_unitario'])
            subtotal = cantidad * costo_unitario
            total += subtotal
        return total

    def set_grupo_servicios_subtotal(self, data):
        grupo_servicios = data.get(self.Product.f['grupo_servicios'])
        for servicio in grupo_servicios:
            subtotal = 0
            servicio_precio = servicio.get(self.Product.LISTA_DE_PRECIOS_OBJ_ID, {}).get(self.Product.f['servicio_precio'], [])[0]
            servicio_cantidad = servicio.get(self.Product.f['servicio_cantidad'])
            servicio_descuento = servicio.get(self.Product.f['servicio_descuento'])
            subtotal = (servicio_precio * servicio_cantidad) * (1 - servicio_descuento / 100)
            servicio[self.Product.f['subtotal_servicio']] = subtotal
        return grupo_servicios
    
    def get_servicios_total(self, grupo_servicios_with_totals):
        total = 0
        for servicio in grupo_servicios_with_totals:
            total += servicio.get(self.Product.f['subtotal_servicio'])
        return total

if __name__ == "__main__":
    mantenimiento_obj = Mantenimiento(settings, sys_argv=sys.argv)
    mantenimiento_obj.console_run()
    registro_data = mantenimiento_obj.answers

    total_refacciones = mantenimiento_obj.get_grupo_refacciones_total(registro_data)
    registro_data[mantenimiento_obj.Product.f['costo_total_refacciones']] = total_refacciones

    grupo_servicios_with_subtotals = mantenimiento_obj.set_grupo_servicios_subtotal(registro_data)
    total_servicios = mantenimiento_obj.get_servicios_total(grupo_servicios_with_subtotals)
    registro_data[mantenimiento_obj.Product.f['grupo_servicios']] = grupo_servicios_with_subtotals
    registro_data[mantenimiento_obj.Product.f['costo_total_servicios']] = total_servicios

    print(simplejson.dumps(registro_data, indent=3))

    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': registro_data
    }))
