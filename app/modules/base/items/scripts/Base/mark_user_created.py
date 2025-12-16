# coding: utf-8
#####
# Script para cambiar el status del usuario a Creado
# Forma: Usuarios
#####
import sys, simplejson, json

from base_utils import Base
from account_settings import *

class Base(Base):

    def __init__(self, settings, sys_argv=None, use_api=True):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

if __name__ == "__main__":
    base_obj = Base(settings, sys_argv=sys.argv)
    base_obj.console_run()
    data = base_obj.data.get('data', {})
    userId = data.get('userId', '')
    username = data.get('username', '')

    response = base_obj.update_user_register(userId=userId, username=username)
    status_code = response.get('status_code', 400)

    sys.stdout.write(simplejson.dumps({
        'status': status_code,
    }))