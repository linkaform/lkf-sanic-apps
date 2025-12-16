# coding: utf-8
#####
# Script para enviar mensaje de texto con nuevo proveedor
#####
from datetime import datetime
import requests, sys, simplejson, json

from accesos_utils import Accesos
from account_settings import *

class Accesos(Accesos):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)

    def format_pass_sms(self, data_cel_msj=None, pre_sms=False, account=''):
        fecha_str_desde = data_cel_msj.get('fecha_desde', '')
        fecha_str_hasta = data_cel_msj.get('fecha_hasta', '')

        ubicaciones = data_cel_msj.get('ubicacion', '')
        ubicaciones_nombres = []
        for ubicacion in ubicaciones:
            nombre_ubicacion = ubicacion.get(self.Location.UBICACIONES_CAT_OBJ_ID, {}).get(self.mf['ubicacion'], '')
            if nombre_ubicacion:
                ubicaciones_nombres.append(nombre_ubicacion)
        
        if len(ubicaciones_nombres) == 1:
            ubicaciones_str = ubicaciones_nombres[0]
        elif len(ubicaciones_nombres) == 2:
            ubicaciones_str = f"{ubicaciones_nombres[0]} y {ubicaciones_nombres[1]}"
        elif len(ubicaciones_nombres) > 2:
            ubicaciones_str = f"{ubicaciones_nombres[0]}, {ubicaciones_nombres[1]} y {len(ubicaciones_nombres) - 2} más"
        else:
            ubicaciones_str = ''

        fecha_desde = datetime.strptime(fecha_str_desde, "%Y-%m-%d %H:%M:%S")
        if fecha_str_hasta:
            fecha_hasta = datetime.strptime(fecha_str_hasta, "%Y-%m-%d %H:%M:%S")

        mensaje=''
        if pre_sms:
            msg = f"Hola {data_cel_msj.get('nombre', '')}, {data_cel_msj.get('visita_a', '')} "
            msg += f"te invita a {ubicaciones_str} y creo un pase para ti."
            msg += f" Completa tus datos de registro aquí: {data_cel_msj.get('link', '')}"
            mensaje = msg
        else:
            if account == 'milenium':
                get_pdf_url = self.get_pdf(data_cel_msj.get('qr_code', ''), template_id=553)
                get_pdf_url = get_pdf_url.get('data', '').get('download_url', '')
            else:
                get_pdf_url = self.get_pdf(data_cel_msj.get('qr_code', ''))
                get_pdf_url = get_pdf_url.get('data', '').get('download_url', '')
            msg = f"Estimado {data_cel_msj.get('nombre', '')}, {data_cel_msj.get('visita_a', '')}"

            if data_cel_msj.get('fecha_desde', '') and not data_cel_msj.get('fecha_hasta', ''):
                fecha_desde_format = fecha_desde.strftime("%d/%m/%Y a las %H:%M")
                msg += f", te invita a {ubicaciones_str} el {fecha_desde_format}."
            elif data_cel_msj.get('fecha_desde', '') and data_cel_msj.get('fecha_hasta', ''):
                fecha_desde_format = fecha_desde.strftime("%d/%m/%Y")
                fecha_hasta_format = fecha_hasta.strftime("%d/%m/%Y")
                msg += f", te invita a {ubicaciones_str} "
                msg += f"del {fecha_desde_format} al {fecha_hasta_format}."

            msg += f" Descarga tu pase: {get_pdf_url}"
            mensaje = msg
        phone_to = data_cel_msj.get('numero', '')
        return mensaje, phone_to


    def send_sms(self, phone_number, message, data_cel_msj=None, pre_sms=None, account=None):
        API_URL = f"http://api.alprotel.com/v1/sms"
        twilio_creds = self.lkf_api.get_user_twilio_creds(use_api_key=True, jwt_settings_key=False)
        alprotel_token = twilio_creds.get('json').get('alprotel_token')

        headers = {
            'Authorization': f'{alprotel_token}',
            'Content-Type': 'application/json'
        }

        data = {
            'para': phone_number,
            'texto': message
        }

        try:
            response = requests.post(API_URL, json=data, headers=headers)

            if response.status_code == 200:
                message_data = {
                    "phone_to": phone_to,
                    "body": message,
                    "status": "enviado desde alprotel",
                    "created_at": datetime.now(),
                }
                message_record = self.create(_object=message_data, is_json=True, collection="messages")
                message_id = message_record.get('_id')
                print('message_id in collection messages', message_id)
                print('SMS enviado correctamente')
                return response.json()
            
        except Exception as e:
            print('Error al enviar SMS', e)
            print('Enviando nuevamente SMS por alternativa...')
            self.send_msj_pase(data_cel_msj=data_cel_msj, pre_sms=pre_sms, account=account)


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
    telefono_formateado = telefono_invitado[1:]
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

    ubicacion = acceso_obj.answers.get(acceso_obj.mf['grupo_ubicaciones_pase'], [])
    fecha_desde = acceso_obj.answers.get(acceso_obj.mf['fecha_desde_visita'], '')
    fecha_hasta = acceso_obj.answers.get(acceso_obj.mf['fecha_desde_hasta'], '')

    data_cel_msj = {
        'numero': telefono_formateado,
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
    
    mensaje, phone_to = acceso_obj.format_pass_sms(data_cel_msj=data_cel_msj, pre_sms=pre_sms, account=cuenta_value)

    # msg = 'Test de SMS desde Back'
    # tel = '528340000000' # => +52 834 000 0000

    data_cel_msj['numero'] = telefono_invitado
    response = acceso_obj.send_sms(phone_number=phone_to, message=mensaje, data_cel_msj=data_cel_msj, pre_sms=pre_sms, account=cuenta_value)

    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'response_sms': response
    }))