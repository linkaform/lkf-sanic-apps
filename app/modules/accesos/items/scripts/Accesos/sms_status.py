# coding: utf-8
import sys, simplejson
from linkaform_api import settings
from account_settings import *
from twilio.rest import Client
from bson import ObjectId

from accesos_utils import Accesos

class Accesos(Accesos):
    
    def send_cel_msj(self, data_cel_msj):
        print('entra a send_cel_msj')

        mensaje = data_cel_msj.get('mensaje', '')
        phone_to = data_cel_msj.get('numero', '')
        
        mensaje ='Nuevo mensaje v2 Paco....'
        phone_to = '+528341227834'
        msg = self.lkf_api.send_sms(phone_to, mensaje, use_api_key=True)
        return msg

if __name__ == "__main__":
    print('ENTRA A SMS STATUS...')
    print('sys argv', sys.argv)
    acceso_obj = Accesos(settings, sys_argv=sys.argv)
    acceso_obj.console_run()
    data = acceso_obj.data.get('data',{})
    data_cel_msj = data.get('data_cel_msj', {})

    mensaje = acceso_obj.send_cel_msj(data_cel_msj=data_cel_msj)
    print('msg', mensaje)