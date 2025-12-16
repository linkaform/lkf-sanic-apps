# coding: utf-8
import sys, simplejson
from linkaform_api import settings
from account_settings import *

from accesos_utils import Accesos



if __name__ == "__main__":
    # print('sysarg',sys.argv)
    #acceso_obj = Accesos(settings, sys_argv=sys.argv, use_api=True) 
    acceso_obj = Accesos(settings, sys_argv=sys.argv)
    acceso_obj.console_run()
    data = acceso_obj.data.get('data',{})
    print('data==',data)
    location = data.get('location')
    area = data.get('area')
    employee_list = data.get('support_guards',[])
    checkin_id = data.get('checkin_id')
    checkin_type = data.get('checkin_type')
    if checkin_type:
        if checkin_type not in ('in', 'out'):
            msg = "Checking type can ONLY be 'in' or 'out'"
            acceso_obj.LKFException(msg)
    if not location:
        location = acceso_obj.get_answer(acceso_obj.checkin_fields['cat_location'])
    if not area:
        area = acceso_obj.get_answer(acceso_obj.checkin_fields['cat_area'])
    if not checkin_type:
        area = acceso_obj.get_answer(acceso_obj.checkin_fields['checkin_type'])
    if not checkin_type:
        msg = "Checking type can ONLY be 'in' or 'out'"
        msg_error_app = {
            acceso_obj.checkin_fields['checkin_type']:{ "msg": ["Es requerido indicar el tipo de checking"], "label": "Estatus", "error":[] }
        }
        raise acceso_obj.LKFException(msg_error_app)

    if checkin_type == "in":
        acceso_obj.do_checkin(location, area, employee_list)
    elif checkin_type == "out":
        acceso_obj.do_checkout(checkin_id, location, area, employee_list)