# -*- coding: utf-8 -*-
import sys, simplejson
from datetime import datetime, timedelta
from bson import errors, ObjectId

from lkf_addons.base.app import Schedule

from account_settings import *

class Schedule(Schedule):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.load(module='Location', **self.kwargs)
        self.load(module='Accesos', **self.kwargs)

        self.f.update({
            'status_cron': 'abcde00010000000a0000000',
            'cron_id': 'abcde0001000000000000000',
            'anticipacion': 'abcde0002000000000010001',
            'timeframe_ant': 'abcde0002000000000010004',
            'timeframe_unit_ant': 'abcde0002000000000010005',
            'end_date': 'abcde0001000000000010099',
            'timeframe': 'abcde0001000000000010004',
            'timeframe_unit': 'abcde0001000000000010005',
            'task_name': '6645050d873fc2d733961eba',
            'task_st': 'abcde0001000000000000006',
            'duration': 'abcde0001000000000000016',
            'description': 'abcde0001000000000000007',
            'status': 'abcde0001000000000000020',
            'assigned_users': 'abcde0001000000000020002',
            'field_map': 'abcded001000000000000001',
            'group_field_map': 'abcde0001000000000000008',
            'action': 'abcde00010000000a0000001',
        })
        
    def schedule_task_recorrido(self):
        '''
        start_date: es la fecha con la que se va a porgramar la recurrencia del dag
        ojo si esta fecha aun no pasa, las tareas del dag sencillamente no corren
        por default el start date es igual a la fecha de la primer ejecucion, a menos de que se 
        programe con anticipacion.
        '''
        response = {}
        #TODO obtener el huzo horario del usuario y calcular us tzoffset
        tz_offset = self.current_record.get('tz_offset', -300) 
        dag_id = self.answers.get(self.mf['dag_id'])
        action = self.answers.get(self.f['action'])
        if not self.answers or  action in ('eliminar', 'delete'):
            if dag_id:
                return self.delete_cron(cron_id = dag_id)
            else:
                return self.delete_cron(self.current_record.get('item_id'), self.current_record.get('folio'))
        task_type = 'create_and_assign'
        if action in ('pausar', 'pause','pausa'):
            if not dag_id:
                msg_error_app = {
                    "error":{"msg": ["Cron ID is needed, only existing Crons can be paused!"], "label": "Cron Id", "error":["Cron ID is needed, only existing Crons can be paused!!!"]},
                }
                raise Exception(simplejson.dumps(msg_error_app))
            body = {
                'dag_id': dag_id,
                'is_paused': True
            }
            response = self.lkf_api.update_cron(body)
            if response.get('status_code') == 200:
                response['is_paused'] = True
            return response
        elif action in ('corriendo', 'running','programar','program') and dag_id:
            body = {
                'dag_id': dag_id,
                'is_pause': False
            }
            response = self.lkf_api.update_cron(body)
            if response.get('satus_code') == 200:
                response['is_paused'] = False

        first_date = self.answers.get(self.mf['fecha_primer_evento'])
        #por default se corre en UTC+0
        start_date = first_date
        anticipacion = self.answers.get(self.f['anticipacion'])
        timeframe_ant = self.answers.get(self.f['timeframe_ant'])
        timeframe_unit_ant = self.answers.get(self.f['timeframe_unit_ant'], 'horas')
        if anticipacion == 'si':
            if timeframe_ant:
                start_date = self.calc_date(first_date, timeframe_ant, timeframe_unit_ant, operator='-')
                start_date = self.calc_date(start_date, tz_offset, 'minutes')
        # print('start date ', start_datestop)
        end_date = self.answers.get(self.f['end_date'])
        timeframe = self.answers.get(self.f['timeframe'])
        timeframe_unit = self.answers.get(self.f['timeframe_unit'], 1)
        due_date = self.calc_date_as_function(first_date, tz_offset, timeframe, timeframe_unit)
        first_date = self.calc_date_as_function(first_date, tz_offset)
        task_name = self.answers.get(self.f['task_name'])
        task_st = self.answers.get(self.f['task_st'])
        duration = self.answers.get(self.f['duration'], 1) * 3600
        description = self.answers.get(self.f['description'], '')
        status = self.answers.get(self.f['status'])
        # field_map = {self.f['field_map']: self.answers.get(self.f['field_map'], '')}
        # group_field_map = {self.f['group_field_map']: self.answers.get(self.f['group_field_map'], '')}

        # asigne_to = self.answers.get('abcde0001000000000020001',[])
        asigne_to = []

        # assigned_users = self.answers.get(self.f['assigned_users'], [])
        custom_cron = False
        schedule_config = self.get_schedule_config(self.answers)
        print('schedule_config=', schedule_config)
        if not schedule_config:
            error_msg = 'No se encontro configuracion'
        body = {}
        item_id = self.Accesos.BITACORA_RONDINES
        item_type = 'form'
        
        if not item_type or not item_id:
            msg_error_app = {
                "error":{"msg": ["Error al obtener el tipo de recurso (item)"], "label": "Cron Id", "error":["Error al obtener el tipo de recurso (item)"]},
            }
            raise Exception(simplejson.dumps(msg_error_app))
        if type(item_type) == list:
            item_type = item_type[0]
        item_type = item_type.lower()

        if dag_id:
            body['id'] = dag_id
        body['subscription_id'] = item_id
        body['subscription_type'] = item_type
        body['name'] = task_name
        body['description'] = description
        body['default_args'] = {
            "email":["josepato@linkaform.com","roman.lezama@linkaform.com"],
            "retries":1,
            "email_on_failure" : True,
            "retry_delay" : "timedelta(seconds=30)"
        }
        APIKEY = self.settings.config.get('APIKEY',self.settings.config.get('API_KEY'))
        body['params'] = {'api_key':APIKEY}
        #TODO calcular el first date , para que arrance la recurrencia tomando en cuenta
        # el tiempo de anticipacion
        body['dag_params'] = {
            "concurrency":3,
            "catchup": False,
            "duration": duration,
            "start_date":"datetime({} ,{}, {}, {}, {})".format(
                int(start_date[:4]),
                int(start_date[5:7]),
                int(start_date[8:10]),
                int(start_date[11:13]),
                int(start_date[14:16]),
                int(start_date[17:19]),
            )
        }

        if custom_cron:
            #TODO BRORRA se me hace que era para poner tu cron directo...
            body['dag_params'].update({'schedule_interval':custom_cron})
        else:
            body['dag_params'].update({'schedule_config':schedule_config})

        if end_date:
            body['dag_params'].update({
                "end_date":"datetime({} ,{}, {}, {}, {})".format(
                int(end_date[:4]),
                int(end_date[5:7]),
                int(end_date[8:10]),
                int(end_date[11:13]),
                int(end_date[14:16]),
                int(end_date[17:19]),
                )
                })

        body['tasks'] = [{
            "name":"LKF Login",
            "operator_lib":"lkf_operator",
            "operator":"LKFLogin",
            "downstream_task_id":[]
        }]
        downstream_task_id = 1
        if task_type == 'create_and_assign':
            task = {
                "name":task_name,
                "operator_lib":"lkf_operator",
                "operator":"CreateRecord",
                # "options":{"no_assign": True},
                "params":{
                    "form_id":item_id,
                    "answers": {
                        self.Accesos.CONFIGURACION_RECORRIDOS_OBJ_ID: {
                            self.Location.f['location']: self.answers.get(self.Location.UBICACIONES_CAT_OBJ_ID, {}).get(self.Location.f['location'], ''),
                            self.Accesos.mf['nombre_del_recorrido']: self.answers.get(self.Accesos.mf['nombre_del_recorrido'], ''),
                        },
                        self.Accesos.f['fecha_programacion']: first_date,
                        self.Accesos.mf['estatus_del_recorrido']: "programado",
                    },
                }
            }
            #if 'todos_los_usuarios_que_tengan_el_formulario_ compartido' in asigne_to:
            body['tasks'].append(task)
            downstream_task_id += 1
            body['tasks'][0]['downstream_task_id'].append(downstream_task_id)
            # all_user_ids = []
            # assigne_2_group = []
            # if 'todos_los_usuarios_que_tengan_el_formulario_compartido' in  asigne_to:
            #     fileshare_user_ids = self.get_form_fileshare(item_id)
            #     all_user_ids += self.convert_usr_id_to_dict(fileshare_user_ids)
            # for gset in assigned_users:
            #     if gset.get(self.f['asignar_a']) == 'grupo':
            #         udata = gset.get(self.GROUP_OBJ_ID,{})
            #         group_id = self.unlist(udata.get(self.f['group_id']))
            #         group_name = self.unlist(udata.get(self.f['group_name']))
            #         assigne_type = gset.get(self.f['asignar_de_grupo'])
            #         if assigne_type == 'un_solo_registro':
            #             assigne_2_group.append({'group_id':group_id, 'group_name':group_name})
            #         else:
            #             group_users = self.lkf_api.get_group_users(group_id)
            #             all_user_ids += self.update_users(all_user_ids, group_users)
            #     elif gset.get(self.f['asignar_a']) == 'usuario':
            #         udata = gset.get(self.USUARIOS_OBJ_ID,{})
            #         data = {
            #             "name":udata.get(self.Accesos.f['new_user_complete_name']),
            #             "email":udata.get(self.Accesos.f['new_user_email'],[])[0],
            #             "username":udata.get(self.Accesos.f['new_user_username'],[])[0],
            #             "user_id":udata.get(self.Accesos.f['new_user_id'],[])[0],
            #             "account_id":self.account_id,
            #             "resource_kind":"user"
            #         }
            #         all_user_ids += self.update_users(all_user_ids, data)
            # if all_user_ids:
            #     body['assign'] = {'assign_users':[]}
            # elif assigne_2_group:
            #     body['assign'] = {'assign_group': assigne_2_group}

            # for assige_usr in all_user_ids:
            #     body['assign']['assign_users'].append(assige_usr)
            print('body=', simplejson.dumps(body, indent=3))
            response.update(self.subscribe_cron(body))

        return response    
        
 
if __name__ == "__main__":
    # print(sys.argv)
    schedule_obj = Schedule(settings, sys_argv=sys.argv, use_api=True)
    schedule_obj.console_run()
    lkf_api = schedule_obj.lkf_api
    res = schedule_obj.schedule_task_recorrido()
    print("res=", res)
    data = res.get('data')
    if res.get('status_code') == 0:
        print('Ningun cambio')
    elif res.get('status_code') == 200:
        if res.get('deleted'):
            schedule_obj.answers[schedule_obj.f['status_cron']] = 'eliminado'
        else:
            schedule_obj.answers[schedule_obj.f['cron_id']] = data.get('dag_id')
            schedule_obj.answers.update(schedule_obj.get_dag_dates(data))
            if res.get('is_paused') == True:
                schedule_obj.answers[schedule_obj.f['status_cron']] = 'pausado'
            else:
                schedule_obj.answers[schedule_obj.f['status_cron']] = 'corriendo'

        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans': schedule_obj.answers,
        }))
    else:
        msg_error_app = "Something went wrong!!!"
        if res.get('json',{}).get('error') or res.get('status_code') == 400:
            if res.get('json',{}).get('error'):
                msg_error_app = res['json']['error']
            else:
                msg_error_app = res['json'].get('message','Something went wrong!!!')
        else:
            msg_error_app = {
                "error":{"msg": [msg_error_app], "label": "Cron Id", "error":[msg_error_app]},
            }
        raise Exception(simplejson.dumps(msg_error_app))