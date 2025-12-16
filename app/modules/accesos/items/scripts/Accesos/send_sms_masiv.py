# coding: utf-8
import base64
from datetime import datetime
import sys, simplejson, json
from time import time
import time
from linkaform_api import settings
from account_settings import *
import requests

from accesos_utils import Accesos
import pytz

class Accesos(Accesos):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)

    def send_test_sms_masiv(self):
        para_list = [
            
        ]
        
        
        API_URL = "https://api-sms.masivapp.com/send-message"
        
        token = base64.b64encode(f"{self.MASIV_USER}:{self.MASIV_TOKEN}".encode()).decode()

        headers = {
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json'
        }
        
        for para in para_list:
            tz = pytz.timezone('America/Mexico_City')
            current_time = datetime.now(tz).strftime("%H:%M:%S")
            data = {
                'to': para,
                'text': f"Este es un mensaje de Masiv enviado a las {current_time} timezone Mexico_City",
                "customdata": "CUS_ID_0125",
            }

            try:
                response = requests.post(API_URL, json=data, headers=headers)

                if response.status_code == 200:
                    print(response.json())
                else:
                    print('Error al enviar SMS', response.status_code, response.text)

            except Exception as e:
                print('Error al enviar SMS', e)
                
            time.sleep(5)
            
    def send_sms_masiv(self, para, texto):
        API_URL = "https://api-sms.masivapp.com/send-message"

        token = base64.b64encode(f"{self.MASIV_USER}:{self.MASIV_TOKEN}".encode()).decode()

        headers = {
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'to': para,
            'text': texto,
            "customdata": "CUS_ID_0125",
            "isLongmessage": True,
        }

        try:
            response = requests.post(API_URL, json=data, headers=headers)

            if response.status_code == 200:
                print(response.json())
            else:
                print('Error al enviar SMS', response.status_code, response.text)

        except Exception as e:
            print('Error al enviar SMS', e)
            
    def format_message(self, data_cel_msj=None, pre_sms=False, account=''):
        fecha_str_desde = data_cel_msj.get('fecha_desde', '')
        fecha_str_hasta = data_cel_msj.get('fecha_hasta', '')

        fecha_desde = datetime.strptime(fecha_str_desde, "%Y-%m-%d %H:%M:%S")
        if fecha_str_hasta:
            fecha_hasta = datetime.strptime(fecha_str_hasta, "%Y-%m-%d %H:%M:%S")

        mensaje=''
        if pre_sms:
            msg = f"Hola {data_cel_msj.get('nombre', '')}, {data_cel_msj.get('visita_a', '')} "
            msg += f"te invita a {data_cel_msj.get('ubicacion', '')} y creo un pase para ti."
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
                msg += f", te invita a {data_cel_msj.get('ubicacion', '')} el {fecha_desde_format}."
            elif data_cel_msj.get('fecha_desde', '') and data_cel_msj.get('fecha_hasta', ''):
                fecha_desde_format = fecha_desde.strftime("%d/%m/%Y")
                fecha_hasta_format = fecha_hasta.strftime("%d/%m/%Y")
                msg += f", te invita a {data_cel_msj.get('ubicacion', '')} "
                msg += f"del {fecha_desde_format} al {fecha_hasta_format}."

            msg += f" Descarga tu pase: {get_pdf_url}"
            mensaje = msg
        phone_to = data_cel_msj.get('numero', '')
        return mensaje, phone_to

if __name__ == "__main__":
    script_obj = Accesos(settings, sys_argv=sys.argv)
    script_obj.console_run()
    script_obj.MASIV_USER = ''
    script_obj.MASIV_TOKEN = ''

    # script_obj.send_test_sms_masiv()
    
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
    telefono_invitado = script_obj.answers.get(script_obj.mf['telefono_pase'], '')
    telefono_invitado = telefono_invitado.replace("+", "")
    nombre_invitado = script_obj.answers.get(script_obj.mf['nombre_pase'], '')
    link_completar_pase = script_obj.answers.get(script_obj.pase_entrada_fields['link'], '')
    grupo_visitados = script_obj.answers.get(script_obj.mf['grupo_visitados'], [])
    nombre_visita_a = ''
    for visita_a in grupo_visitados:
        vista_catalog = visita_a.get(script_obj.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID,{})
        nombre = vista_catalog.get(script_obj.mf['nombre_empleado'])
        if nombre:
            if len(nombre_visita_a) > 0:
                nombre_visita_a += ', '
            nombre_visita_a += nombre

    ubicaciones_list = []
    ubicaciones_group = script_obj.answers.get(script_obj.mf['grupo_ubicaciones_pase'], '')
    for item in ubicaciones_group:
        ubicacion = item.get(script_obj.Location.UBICACIONES_CAT_OBJ_ID,{}).get(script_obj.Location.f['location'], '')
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

    fecha_desde = script_obj.answers.get(script_obj.mf['fecha_desde_visita'], '')
    fecha_hasta = script_obj.answers.get(script_obj.mf['fecha_desde_hasta'], '')

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

    seleccion_de_visitante = script_obj.answers.get(script_obj.pase_entrada_fields['tipo_visita'])

    if(seleccion_de_visitante == 'Buscar visitantes registrados'):
        visitante_registrado = script_obj.answers.get(script_obj.pase_entrada_fields['catalogo_visitante_registrado'], {})
        nombre_visitante_registrado = visitante_registrado.get(script_obj.pase_entrada_fields['nombre_visitante_registrado'], '')
        telefono_vistante_registrado = visitante_registrado.get(script_obj.mf['telefono_visita'], [])[0][0]

        data_cel_msj['nombre'] = nombre_visitante_registrado
        data_cel_msj['numero'] = telefono_vistante_registrado

    print(simplejson.dumps(data_cel_msj, indent=4))
    
    #Enviar sms
    mensaje, phone_to = script_obj.format_message(data_cel_msj=data_cel_msj, pre_sms=pre_sms, account=cuenta_value)
    print(simplejson.dumps(mensaje, indent=4))
    script_obj.send_sms_masiv(para=phone_to, texto=mensaje)

    sys.stdout.write(simplejson.dumps({
        'status': 101,
    }))