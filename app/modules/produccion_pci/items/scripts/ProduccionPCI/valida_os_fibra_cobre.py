# -*- coding: utf-8 -*-
import sys, simplejson
from produccion_pci_utils import Produccion_PCI
from account_settings import *

class ValidacionesOrdenDeServicio( Produccion_PCI ):
    """docstring for ValidacionesOrdenDeServicio"""
    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

    def validar_orden_de_servicio(self):
        validar_os.validaciones_generales()
        

if __name__ == '__main__':
    print("--- --- --- Validaciones de orden de servicio --- --- ---")
    lkf_obj = ValidacionesOrdenDeServicio(settings, sys_argv=sys.argv, use_api=False)

    # lkf_obj.console_run()
    
    edited_by_script = lkf_obj.answers.get( lkf_obj.f['field_id_cargado_desde_script'] ) == 'sí'

    print(f"Folio = {lkf_obj.folio} ::: Editado desde script {edited_by_script}")

    if lkf_obj.folio and edited_by_script:
        # Si el registro esta marcado como cargado desde script hay que quitarle el valor para que si lo editan pase por las validaciones
        lkf_obj.answers.pop( lkf_obj.f['field_id_cargado_desde_script'], None )
        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans': lkf_obj.answers
        }))
    else:
        # El registro no fue actualizado por el script, se ejecutan las validaciones
        from pci_get_connection_db import CollectionConnection
        colection_connection = CollectionConnection(1259, settings)
        cr_admin = colection_connection.get_collections_connection()

        from pci_base_utils import PCI_Utils
        p_utils = PCI_Utils(cr=lkf_obj.cr, cr_admin=cr_admin, lkf_api=lkf_obj.lkf_api, net=lkf_obj.net, settings=settings, lkf_obj=lkf_obj)

        config['JWT_KEY_ADMIN'] = p_utils.get_jwt_admin()
        # Usuario que está enviando el registro
        jwt_complete = simplejson.loads(sys.argv[2])
        config['USER_JWT_KEY'] = jwt_complete["jwt"].split(' ')[1]
        settings.config.update(config)
        
        from validaciones_orden_servicio import ValidarOS
        validar_os = ValidarOS(
            cr=lkf_obj.cr, 
            lkf_api=lkf_obj.lkf_api, 
            p_utils=p_utils, 
            form_id=lkf_obj.form_id, 
            current_record=lkf_obj.current_record,
            lkf_obj=lkf_obj
        )

        lkf_obj.validar_orden_de_servicio()