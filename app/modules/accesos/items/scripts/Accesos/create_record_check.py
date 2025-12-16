import sys,json, simplejson, re
from bson import ObjectId
from linkaform_api import  base
from account_settings import *
from datetime import datetime
import pytz

from accesos_utils import Accesos

class Accesos(Accesos):
    #----Dicitionary Answers
    def get_key_answer(self, tagId):
        dic_res = {}
        match_query = { 
            'deleted_at':{"$exists":False},
            '6762f7b0922cc2a2f57d4044':tagId,
        }
        mango_query = {"selector":
            {"answers":
                {"$and":[match_query]}
            },
            "limit":1,
            "skip":0
        }
        res = self.lkf_api.search_catalog(126716, mango_query)
        if len(res) > 0:
            dic_res['keyAnswers'] = res[0].get('6762f7e30c001206307d4053','')
            dic_res['location'] = res[0].get('663e5d44f5b8a7ce8211ed0f','')
            dic_res['ubicacion'] = res[0].get('663e5c57f5b8a7ce8211ed0b','')
      
        if dic_res :
            return dic_res  
        return None

    #----Record Check
    def set_add_record_check(self, data_record, folio_bitacora_update):
        #--Value Assing
        tag_id = data_record.get('tagId','')
        folio = data_record.get('folio','')
        ubicacion = data_record.get('ubicacion','')
        rondin = data_record.get('rondin','')
        dic_check = data_record.get('list_checks',[])
        comment = data_record.get('comment','')
        list_imgs = data_record.get('list_img',[])
        #--Answers
        dic_catalog = self.get_key_answer(tag_id)
        answers_check = dic_catalog.get('keyAnswers','')
        location_check = dic_catalog.get('location','')
        #--Check
        list_check =  [key for key, value in dic_check.items() if value is True]
        if list_check != None:
            #----Create Dic
            dic_response = {
                '674e31186a5f08049c82844c':{
                    '674e31186a5f08049c82844e':rondin,
                    '674e31186a5f08049c82844d':folio,
                },
                '674e2ac6e3e7c31132939288':{
                    '663e5c57f5b8a7ce8211ed0b':ubicacion,
                    '663e5d44f5b8a7ce8211ed0f':location_check,
                },
                '676461772f3a94a85b055e91' : 'rondin_programado', 
                answers_check : list_check,
                '6740cbd734849293fe5a2735' : list_imgs, 
                '6740cbd734849293fe5a2736' : comment, 
            }
            metadata = self.lkf_api.get_metadata(126213)
            metadata['answers'] = dic_response
            dic_res = {'status_create':'400'}
            resp_create = self.lkf_api.post_forms_answers_list(metadata)
            if len(resp_create) == 1:
                data = resp_create[0].get('json',{})
                dic_res['status_create'] = resp_create[0].get('status_code','400')
                dic_res['id_request'] = str(data.get('id',''))
                dic_res['folio'] = data.get('folio','')
                #----Update
                res_update = self.update_bitacora_record(data_record, dic_res['id_request'], folio_bitacora_update)
                dic_res['res_update'] = res_update
            return dic_res
        else:
            return dic_res

    def update_bitacora_record(self,  data, id_record, folio):
        #---Create FOrmat Date
        mexico_timezone = pytz.timezone('America/Mexico_City')
        now_mexico = datetime.now(mexico_timezone)
        formatted_time = now_mexico.strftime('%Y-%m-%d %H:%M:%S')


        #---Create set
        location = data.get('location','')
        list_imgs = data.get('list_img',[])
        comment = data.get('comment','')
        str_url = f'https://app.linkaform.com/#/records/detail/{id_record}'  

        answers_set = {
            '674e2e9eecf32979019392af':{
                '663e5d44f5b8a7ce8211ed0f':location,
            },
            '6760a908a43b1b0e41abad6b': formatted_time,
            '66462b9d7124d1540f962087': list_imgs,
            '66462b9d7124d1540f962088': comment,
            '6750adb2936622aecd075607': str_url,
        }
        #----Update
        answers = {
            '66462aa5d4a4af2eea07e0d1':{'-1':answers_set}
        }
        res = self.lkf_api.patch_multi_record(answers = answers, form_id=126790, folios=[folio])
        return res

    def set_add_inspection_record(self, data):
        tag_id = data.get('tagId','')
        dic_check = data.get('list_checks',[])
        comment = data.get('comment','')
        list_imgs = data.get('list_img',[])
        #--Answers Catalog
        print('data=',data)
        dic_catalog = self.get_key_answer(tag_id)
        answers_check = dic_catalog.get('keyAnswers','')
        location_check = dic_catalog.get('location','')
        ubicacion_check = dic_catalog.get('ubicacion','')
        #--Check
        list_check =  [key for key, value in dic_check.items() if value is True]
        #---Creation Dic Inspection
        if list_check != None:
            #----Create Dic
            dic_response = {
                '674e2ac6e3e7c31132939288':{
                    '663e5c57f5b8a7ce8211ed0b':ubicacion_check,
                    '663e5d44f5b8a7ce8211ed0f':location_check,
                },
                '676461772f3a94a85b055e91' : 'inspección_de_área', 
                answers_check : list_check,
                '6740cbd734849293fe5a2735' : list_imgs, 
                '6740cbd734849293fe5a2736' : comment, 
            }
            metadata = self.lkf_api.get_metadata(126213)
            metadata['answers'] = dic_response
            dic_res = {'status_create':'400'}
            resp_create = self.lkf_api.post_forms_answers_list(metadata)
            print('resp_create', resp_create)
            if len(resp_create) == 1:
                dic_res['status_create'] = resp_create[0].get('status_code','400')
            return dic_res 

    #----Record Bitacora:
    def set_add_record_bitacora(self, tagId, config):
        res_catalog = self.get_information_catalog(tagId)
        ubication_location = res_catalog.get('ubication_location','')

        #----Create Dic
        dic_response = {
            self.f['fecha_inicio_rondin']: self.today_str(date_format='datetime'),
            self.f['status_rondin'] : 'en_proceso', 
            self.CONFIGURACION_RECORRIDOS_OBJ_ID : {
                self.mf['ubicacion']:ubication_location,
                self.f['nombre_recorrido']:config,
            },
        }
        metadata = self.lkf_api.get_metadata(126790)
        metadata['answers'] = dic_response
        resp_create = self.lkf_api.post_forms_answers_list(metadata)
        print('------------')
        print('resp_create',resp_create)
        print('------------')
        dic_res = {'status_request':'400'}
        if len(resp_create) == 1:
            data = resp_create[0].get('json',{})
            dic_res['status_request'] = resp_create[0].get('status_code','400')
            dic_res['id_request'] = str(data.get('id',''))
            dic_res['folio'] = data.get('folio','')
        return dic_res

    #----Catalog Location
    def get_information_catalog(self, tag_id):
        dic_res = {}
        match_query = { 
            'deleted_at':{"$exists":False},
            '6762f7b0922cc2a2f57d4044':{"$eq":tag_id},
        }

        mango_query = {"selector":
            {"answers":
                {"$and":[match_query]}
            },
            "limit":1,
            "skip":0
        }
        res = self.lkf_api.search_catalog(126716, mango_query)
        for item in res:
            name_location = item.get('663e5d44f5b8a7ce8211ed0f','')
            type_location = item.get('663e5e68f5b8a7ce8211ed18','')
            image_location = item.get('6763096aa99cee046ba766ad',[])
            ubication_location = item.get('663e5c57f5b8a7ce8211ed0b','')
            direction_location = item.get('663a7e0fe48382c5b1230901','')
            #----Get Last Record
            last_record = script_obj.get_last_record_check(name_location)

            dic_res = {
                "name_location": name_location,
                "type_location": type_location,
                "image_location": image_location,
                "ubication_location": ubication_location,
                "direction_location": direction_location,
                "last_record": last_record,
            }
        return dic_res

    #----Config Rodin
    def get_format_config(self, data):
        list_return = []
        for item in data:
            folio = item.get('folio','')
            nombre_rondin = item.get('nombre_rondin','')
            ubicacion = item.get('ubicacion','')
            area = item.get('area',[])
            list_return.append({
                "folio":folio,
                "nombre_rondin":nombre_rondin,
                "ubicacion":ubicacion,
                "area":area,
            })
        return list_return

    #----Get List Rondines
    def get_config_rondines(self, tag_id):
        match_query = {
            "form_id":126796,
            "deleted_at": {"$exists":False},
        }
        if tag_id :
            match_query.update({"answers.6645052ef8bc829a5ccafaf5.674e2ac6e3e7c31132939288.6762f7b0922cc2a2f57d4044":{'$in':[tag_id,[tag_id]]}})

        query = [
            {"$match": match_query},  
            {"$unwind": {  
                "path": "$answers.6645052ef8bc829a5ccafaf5",
                "preserveNullAndEmptyArrays": True
            }},
            {"$group": { 
                "_id": "$folio",  
                "nombre_rondin": {"$first": "$answers.6645050d873fc2d733961eba"},  
                "ubicacion": {"$first": "$answers.674e2ac399c0a2770c82843d.663e5c57f5b8a7ce8211ed0b"},
                "areas": {
                    "$addToSet": {
                        "nombre":"$answers.6645052ef8bc829a5ccafaf5.674e2ac6e3e7c31132939288.663e5d44f5b8a7ce8211ed0f",
                        "tagId":"$answers.6645052ef8bc829a5ccafaf5.674e2ac6e3e7c31132939288.6762f7b0922cc2a2f57d4044",
                    }
                } 
            }},
            {"$project": {  
                "_id": 1,
                "folio": "$_id",
                "nombre_rondin": 1,
                "ubicacion": 1,
                "area": "$areas"
            }}
        ]
        result = self.cr.aggregate(query)
        result_format = self.get_format_config(result)
        return result_format

    #----Update Record Rondin
    def update_record_rondin(self, folio):
        #----Update
        answers = {
            '6639b2744bb44059fc59eb62' : 'realizado', 
        }
        res = self.lkf_api.patch_multi_record(answers = answers, form_id=126790, folios=[folio])
        res.update({'status_request':res.get('status_code')})
        return res

    #----Config Tag
    def get_data_tag(self, tag_id):
        dic_res = {
            'status_request':''
        }
        match_query = { 
            'deleted_at':{"$exists":False},
        }
        mango_query = {"selector":
            {"answers":
                {"$and":[match_query]}
            },
            "limit":10000,
            "skip":0
        }
        res = self.lkf_api.search_catalog(126716, mango_query)
        #-----Format
        catalog_list = []
        flag_find = False

        for item_catalog in res:
            _id_catalog =  str(item_catalog.get('_id',None))
            tag_id_catalog =  item_catalog.get('6762f7b0922cc2a2f57d4044',None)
            ubicacion_catalog =  item_catalog.get('663e5c57f5b8a7ce8211ed0b',None)
            nombre_area_catalog =  item_catalog.get('663e5d44f5b8a7ce8211ed0f',None)
            imagen_area_catalog =  item_catalog.get('6763096aa99cee046ba766ad',None)
            if tag_id_catalog == tag_id and tag_id :
                flag_find = True 
                dic_res['status_request'] = 'included'
                dic_res['data_tag'] = {
                    'ubicacion_catalog': ubicacion_catalog,
                    'nombre_area_catalog': nombre_area_catalog,
                    'imagen_area_catalog': imagen_area_catalog,
                    'tag_id_catalog': tag_id_catalog,
                }
            catalog_list.append({
                'ubicacion_catalog': ubicacion_catalog,
                'nombre_area_catalog': nombre_area_catalog,
                'imagen_area_catalog': imagen_area_catalog,
                '_id_catalog': _id_catalog,
            })

        if not flag_find:
            dic_res['status_request'] = 'not_included'
            dic_res['catalog_list'] = catalog_list
        return dic_res

    def set_update_tag(self, tag_id, list_images_dic, id_catalog_record):
        res_update = {
            '6762f7b0922cc2a2f57d4044': tag_id,
            '6763096aa99cee046ba766ad': list_images_dic,
        }
        res_update = self.lkf_api.update_catalog_multi_record( res_update, 126716, record_id=[id_catalog_record])
        dic_res = {'status_request':'400'}
        dic_res['status_request'] = res_update.get('status_code','400')
        return dic_res

    #----Last Record Check
    def get_last_record_check(self, location):
        match_query = {
            "form_id":126213,
            "deleted_at": {"$exists":False},
        }
        if tag_id :
            match_query.update({"answers.674e2ac6e3e7c31132939288.663e5d44f5b8a7ce8211ed0f":{'$in':[location,[location]]}})

        query = [
            {"$match": match_query},  
            {"$project": {  
                "_id": 1,
                "folio": "$_id",
                "created": "$created_at",
            }},
            {'$sort': {'created': -1 }},
            {'$limit':1}
        ]
        result = self.cr.aggregate(query)
        #------Date
        msg_return = ''
        date = ''
        for item in result:
            date = item.get('created','')

        if date and date != '':  
            if isinstance(date, str):
                fecha_creada = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f')
            elif isinstance(date, datetime):
                fecha_creada = date

            fecha_actual = datetime.now()
            diferencia = fecha_actual - fecha_creada  # Esto es un objeto timedelta
            dias_transcurridos = diferencia.days

            if dias_transcurridos == 0:
                horas_transcurridas = diferencia.seconds // 3600
                minutos_transcurridos = (diferencia.seconds % 3600) // 60
                msg_return = f'Última inspección hace {horas_transcurridas} horas y {minutos_transcurridos} minutos'
            else:
                msg_return = f'Última inspección hace {dias_transcurridos} días'
        else:
            msg_return = f'No hay registros de inspección'
        return msg_return

if __name__ == "__main__":
    script_obj = Accesos(settings, sys_argv=sys.argv, use_api=True)
    script_obj.console_run()
    #-FILTROS
    data = script_obj.data
    data = data.get('data',[])

    dataFilter = data.get('formInformation',[])
    #----Paramters
    tag_id = data.get('tagId','')
    user = data.get('user','')
    option = data.get('option','')
    location = data.get('location','')
    config = data.get('config','')
    folio_update = data.get('folioUpdate','')
    list_images_dic = data.get('listImagesDic',[])
    id_catalog_record = data.get('idCatalog','')
    form_information = data.get('formInformation','')
    #----Functions
    if option == 'add_record_check':
        response = script_obj.set_add_record_check(form_information, folio_update);
        script_obj.HttpResponse({"data":response})
    elif option == 'add_inspection_check':
        response = script_obj.set_add_inspection_record(form_information)
        sys.stdout.write(simplejson.dumps({'data':response}))
    elif option == 'add_record_bitacora':
        response = script_obj.set_add_record_bitacora(tag_id,config);
        sys.stdout.write(simplejson.dumps({'data':response}))
    elif option == 'get_catalog':
        response = script_obj.get_information_catalog(tag_id)
        sys.stdout.write(simplejson.dumps({'data':response}))
    elif option == 'get_config':
        response = script_obj.get_config_rondines(tag_id)
        sys.stdout.write(simplejson.dumps({'data':response}))
    elif option == 'update_record_bitacora':
        response = script_obj.update_record_rondin(folio_update)
        sys.stdout.write(simplejson.dumps({'data':response}))
    elif option == 'get_information_tag':
        response = script_obj.get_data_tag(tag_id)
        sys.stdout.write(simplejson.dumps({'data':response}))
    elif option == 'update_information_tag':
        response = script_obj.set_update_tag(tag_id, list_images_dic, id_catalog_record)
        sys.stdout.write(simplejson.dumps({'data':response}))
    else:
        sys.stdout.write(simplejson.dumps({'msg':'empty'}))
