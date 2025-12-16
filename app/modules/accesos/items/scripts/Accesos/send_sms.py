# coding: utf-8
import sys, simplejson, json
from linkaform_api import settings
from account_settings import *

from accesos_utils import Accesos

class Accesos(Accesos):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)




if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv)
    acceso_obj.console_run()
    # print('ANSWERSSSSSSSSSSSSS', acceso_obj.answers)

    #Obtener id para obtener el link del pdf
    qr_code = json.loads(sys.argv[1])
    qr_code = qr_code.get('_id', '').get('$oid', '')

    #Saber si sera un pre_sms o no
    data_raw = json.loads(sys.argv[2])
    pre_sms_value = data_raw.get('pre_sms', '')
    cuenta_value = data_raw.get('cuenta', '')

    # Convertir a booleano de forma segura
    if isinstance(pre_sms_value, bool):
        pre_sms = pre_sms_value
    else:
        pre_sms = pre_sms_value.lower() == 'true'

    #Datos necesario para enviar el sms
    telefono_invitado = acceso_obj.answers.get(acceso_obj.mf['telefono_pase'], '')
    nombre_invitado = acceso_obj.answers.get(acceso_obj.mf['nombre_pase'], '')
    link_completar_pase = acceso_obj.answers.get(acceso_obj.pase_entrada_fields['link'], '')
    grupo_visitados = acceso_obj.answers.get(acceso_obj.mf['grupo_visitados'], [])
    nombre_visita_a = ''
    for visita_a in grupo_visitados:
        vista_catalog = visita_a.get(acceso_obj.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID,{})
        nombre = vista_catalog.get(acceso_obj.mf['nombre_empleado'])
        if nombre:
            if len(nombre_visita_a) > 0:
                nombre_visita_a += ', '
            nombre_visita_a += nombre

    ubicaciones_list = []
    ubicaciones_group = acceso_obj.answers.get(acceso_obj.mf['grupo_ubicaciones_pase'], '')
    for item in ubicaciones_group:
        ubicacion = item.get(acceso_obj.Location.UBICACIONES_CAT_OBJ_ID,{}).get(acceso_obj.Location.f['location'], '')
        ubicaciones_list.append(ubicacion)
    
    if len(ubicaciones_list) == 1:
        ubicaciones_str = ubicaciones_list[0]
    elif len(ubicaciones_list) == 2:
        ubicaciones_str = f"{ubicaciones_list[0]} y {ubicaciones_list[1]}"
    elif len(ubicaciones_list) > 2:
        ubicaciones_str = f"{ubicaciones_list[0]}, {ubicaciones_list[1]} y {len(ubicaciones_list) - 2} más"
    else:
        ubicaciones_str = ''
        
    ubicacion = ubicaciones_str

    fecha_desde = acceso_obj.answers.get(acceso_obj.mf['fecha_desde_visita'], '')
    fecha_hasta = acceso_obj.answers.get(acceso_obj.mf['fecha_desde_hasta'], '')

    data_cel_msj = {
        'numero': telefono_invitado,
        'nombre': nombre_invitado,
        'link': link_completar_pase,
        'visita_a': nombre_visita_a,
        'ubicacion': ubicacion,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
        'qr_code': qr_code,
        'pre_sms': pre_sms
    }

    seleccion_de_visitante = acceso_obj.answers.get(acceso_obj.pase_entrada_fields['tipo_visita'])

    if(seleccion_de_visitante == 'Buscar visitantes registrados'):
        visitante_registrado = acceso_obj.answers.get(acceso_obj.pase_entrada_fields['catalogo_visitante_registrado'], {})
        nombre_visitante_registrado = visitante_registrado.get(acceso_obj.pase_entrada_fields['nombre_visitante_registrado'], '')
        telefono_vistante_registrado = visitante_registrado.get(acceso_obj.mf['telefono_visita'], [])[0][0]

        data_cel_msj['nombre'] = nombre_visitante_registrado
        data_cel_msj['numero'] = telefono_vistante_registrado

    print(simplejson.dumps(data_cel_msj, indent=4))
    
    #Enviar sms
    response = acceso_obj.send_msj_pase(data_cel_msj=data_cel_msj, pre_sms=pre_sms, account=cuenta_value)

    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'response_sms': response
    }))