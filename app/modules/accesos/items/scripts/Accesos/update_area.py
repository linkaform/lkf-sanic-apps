# coding: utf-8
#####
# Script para actualizar 
#####
import sys, simplejson, json

from accesos_utils import Accesos
from account_settings import *

class Accesos(Accesos):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)

        self.configuracion_area = {
            'qr_area': '68487646684fe30a8f9f3ef3',
            'foto_area': '68487646684fe30a8f9f3ef4',
            'ubicacion': '663e5c57f5b8a7ce8211ed0b',
            'area': '663e5d44f5b8a7ce8211ed0f',
            'option': '68487646684fe30a8f9f3ef2',
            'create_area': '688a33d9e61fcd2c299ff39e',
            'nombre_nueva_area': '688a33d9e61fcd2c299ff39f',
        }

        self.area_update = {
            'foto_area': '6763096aa99cee046ba766ad',
            'tag_id_area': '6762f7b0922cc2a2f57d4044',
            'tipo_area': '663e5e68f5b8a7ce8211ed18',
            'nombre_direccion': '663a7e0fe48382c5b1230901',
            'estatus_area': '663e5e4bf5b8a7ce8211ed15',
            'estatus': '663e5e4bf5b8a7ce8211ed14',
            'qr_area': '663e5e4bf5b8a7ce8211ed13',
            'pais_area': '663a7ca6e48382c5b12308fa',
            'ciudad_area': '6654187fc85ce22aaf8bb070',
            'colonia_area': '663a7f79e48382c5b123090a',
            'direccion_area': '663a7e0fe48382c5b1230902',
            'geolocalizacion_area': '663e5c8cf5b8a7ce8211ed0c',
            'geolocalizacion_area_ubicacion': '688bac1ecfdcf8b16eb209b5'
        }
        
        self.f.update({
            'status_details': '689a46342038ded0e949be07',
            'status_details_message': '689a46342038ded0e949be08',
        })

    def format_data_area(self, data):
        formatted_data = {}

        if data.get(self.configuracion_area['qr_area']):
            formatted_data.update({
                'qr_area': data.get(self.configuracion_area['qr_area'])
            })

        if data.get(self.configuracion_area['foto_area']):
            formatted_data.update({
                'foto_area': data.get(self.configuracion_area['foto_area'])
            })

        formatted_data.update({
            'option': data.get(self.configuracion_area['option'], ''),
            'ubicacion': data.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.configuracion_area['ubicacion'], ''),
            'area': data.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.configuracion_area['area'], ''),
            'create_area': True if data.get(self.configuracion_area['create_area']) == 'no' else False,
            'nombre_nueva_area': data.get(self.configuracion_area['nombre_nueva_area'], ''),
            'geolocation_area': data.get(self.area_update['geolocalizacion_area_ubicacion'], {}), # type: ignore
        })

        return formatted_data

    def get_record_ubicacion(self, ubicacion=None, area=None, tag_id_area=None):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.AREAS_DE_LAS_UBICACIONES,
        }
        if ubicacion:
            match_query.update({
            f"answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.configuracion_area['ubicacion']}": {
                    "$regex": f"^{ubicacion}$",
                    "$options": "i"
                }
            })
        if area:
            match_query.update({
            f"answers.{self.configuracion_area['area']}": {
                    "$regex": f"^{area}$",
                    "$options": "i"
                }
            })
        if tag_id_area:
            match_query.update({
                f"answers.{self.area_update['tag_id_area']}": tag_id_area
            })

        query = [
            {'$match': match_query },
            {'$project': {
                'folio': {'$ifNull': ['$folio', '']},
                '_id': 1,
                'ubicacion': f"$answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.configuracion_area['ubicacion']}",
                'area': f"$answers.{self.configuracion_area['area']}",
                'tag_id_area': {'$ifNull': [f"$answers.{self.area_update['tag_id_area']}", '']},
                'foto_area': {'$ifNull': [f"$answers.{self.area_update['foto_area']}", []]},
                'tipo_area': f"$answers.{self.TIPO_AREA_OBJ_ID}.{self.area_update['tipo_area']}",
                'nombre_direccion': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.area_update['nombre_direccion']}",
                'pais_area': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.area_update['pais_area']}",
                'ciudad_area': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.area_update['ciudad_area']}",
                'colonia_area': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.area_update['colonia_area']}",
                'direccion_area': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.area_update['direccion_area']}",
                'geolocalizacion_area': f"$answers.{self.CONTACTO_CAT_OBJ_ID}.{self.area_update['geolocalizacion_area']}",
                'geolocation_especific': f"$answers.{self.area_update['geolocalizacion_area_ubicacion']}",
                'estatus_area': f"$answers.{self.area_update['estatus_area']}",
                'estatus': f"$answers.{self.area_update['estatus']}",
                'qr_area': f"$answers.{self.area_update['qr_area']}"
            }},
            {'$limit': 1},
            {'$sort':{'folio':-1}},
        ]
        res = self.format_cr(self.cr.aggregate(query))
        res = self.unlist(res)
        return res

    def update_area(self, data):
        ubicacion = data.get('ubicacion', '')
        area = data.get('area', '')
        if not ubicacion:
            msg = 'La ubicacion no puede estar vacia.'
            acceso_obj.LKFException({'msg': msg, 'title': 'Ubicacion vacia'})
            self.statuss = 'error'
            self.status_comment = 'La ubicacion no puede estar vacia.'
            return
        area_ubicacion_data = self.get_record_ubicacion(ubicacion=ubicacion, area=area)
        if not area_ubicacion_data:
            msg = 'No se encontro el area especificada.'
            acceso_obj.LKFException({'msg': msg, 'title': 'Area no encontrada'})
            self.statuss = 'error'
            self.status_comment = 'No se encontro el area especificada.'
            return
        folio = area_ubicacion_data.get('folio', '')
        record_id = area_ubicacion_data.get('_id', '')

        answers={}
        geolocation_especific = {
            'latitude': area_ubicacion_data.get('latitude'),
            'longitude': area_ubicacion_data.get('longitude')
        }

        for key, value in area_ubicacion_data.items():
            if key == 'area':
                answers[self.configuracion_area['area']] = value # type: ignore
            elif key == 'ubicacion':
                answers[self.UBICACIONES_CAT_OBJ_ID] = {
                    self.configuracion_area['ubicacion']: value, # type: ignore
                }
            elif key == 'tipo_area':
                answers[self.TIPO_AREA_OBJ_ID] = {
                    self.area_update['tipo_area']: value # type: ignore
                }
            elif key == 'nombre_direccion':
                answers[self.CONTACTO_CAT_OBJ_ID] = {
                    self.area_update['nombre_direccion']: value,
                    self.area_update['pais_area']: area_ubicacion_data.get('pais_area', []),
                    self.area_update['ciudad_area']: area_ubicacion_data.get('ciudad_area', []),
                    self.area_update['colonia_area']: area_ubicacion_data.get('colonia_area', []),
                    self.area_update['direccion_area']: area_ubicacion_data.get('direccion_area', []),
                    self.area_update['geolocalizacion_area']: area_ubicacion_data.get('geolocalizacion_area', [])
                }
            elif key == 'estatus_area':
                answers[self.area_update['estatus_area']] = value
            elif key == 'estatus':
                answers[self.area_update['estatus']] = value
            elif key == 'tag_id_area':
                answers[self.area_update['tag_id_area']] = data.get('qr_area') or value
            elif key == 'qr_area':
                answers[self.area_update['qr_area']] = value
            elif key == 'foto_area':
                answers[self.area_update['foto_area']] = data.get('foto_area') or value
            elif key == 'latitude' or key == 'longitude':
                answers[self.area_update['geolocalizacion_area_ubicacion']] = geolocation_especific # type: ignore
            else:
                pass

        if answers:
            metadata = self.lkf_api.get_metadata(form_id=self.AREAS_DE_LAS_UBICACIONES)
            metadata.update({
                'properties': {
                    "device_properties":{
                        "system": "Addons",
                        "process":"Actualizacion de Area", 
                        "accion":'update_area', 
                        "folio": folio, 
                        "archive": "incidencias.py"
                    }
                },
                'answers': answers,
                '_id': record_id
            })

            response = self.net.patch_forms_answers(metadata)
            response = self.detail_response(response.get('status_code', 0))
            return response
            
    def detail_response(self, status_code: int):
        """Devuelve un mensaje detallado según el código de estado HTTP.
        Args:
            status_code (int): El código de estado HTTP devuelto por la API.
        Returns:
            dict: Un diccionario con el estado y el mensaje correspondiente.
        """
        if status_code in [200, 201, 202]:
            return {"status": "success", "message": "Operation completed successfully."}
        elif status_code in [400, 404]:
            return {"status": "error", "message": "Bad request or resource not found."}
        elif status_code in [500, 502, 503]:
            return {"status": "error", "message": "Server error, please try again later."}
        else:
            return {"status": "error", "message": "Unexpected error occurred."}

    def get_contact_details(self, direccion):
        selector = {}
        
        selector.update({
            f"answers.{self.area_update['nombre_direccion']}": direccion, # type: ignore
        })
            
        fields = [
            "_id",
            f"answers.{self.area_update['nombre_direccion']}", # type: ignore
            f"answers.{self.area_update['pais_area']}",
            f"answers.{self.area_update['direccion_area']}",
            f"answers.{self.area_update['colonia_area']}",
            f"answers.{self.area_update['geolocalizacion_area']}",
            f"answers.{self.area_update['ciudad_area']}",
        ]
        
        mango_query = {
            "selector": selector,
            "fields": fields,
            "limit": 1,
        }
        res = self.lkf_api.search_catalog(131890, mango_query)
        res = self.unlist(res)
        if res:
            res.pop('_id', None)
            res.pop('_rev', None)
            res.pop('created_at', None)
            res.pop('updated_at', None)
        return res if res else {}
    
    def exists_area(self, ubicacion, area):
        query = [
            {'$match': {
                "deleted_at":{"$exists":False},
                "form_id": self.AREAS_DE_LAS_UBICACIONES,
                f"answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.configuracion_area['ubicacion']}": {
                    "$regex": f"^{ubicacion}$",
                    "$options": "i"
                },
                f"answers.{self.configuracion_area['area']}": {
                    "$regex": f"^{area}$",
                    "$options": "i"
                }
            }},
            {'$project': {
                '_id': 1,
            }},
            {'$limit': 1},
        ]
        res = self.format_cr(self.cr.aggregate(query))
        return True if res else False

    def create_new_area(self, data):
        exists_area = self.exists_area(data.get('ubicacion', {}), data.get('nombre_nueva_area', ''))
        if exists_area:
            self.status_comment = 'El area ya existe. Solo se actualizo la informacion rellenada.'
            return
        
        contact_details = self.get_contact_details(data.get('ubicacion', {}))
        
        answers = {
            self.mf['nombre_area']: data.get('nombre_nueva_area'),
            self.Location.UBICACIONES_CAT_OBJ_ID: {
                self.mf['nombre_ubicacion_salida']: data.get('ubicacion', ''),
            },
            self.Location.TIPO_AREA_OBJ_ID: {
                self.area_update['tipo_area']: 'Área Pública'
            },
            self.area_update['geolocalizacion_area_ubicacion']: self.geolocation_area if self.geolocation_area else {},
            self.CONTACTO_CAT_OBJ_ID: contact_details,
            self.area_update['estatus']: 'activa',
            self.area_update['estatus_area']: 'disponible',
        }
        
        response = self.create_register(
            module='Accesos',
            process='Creacion de una area',
            action='rondines',
            file='accesos/app.py',
            form_id=self.AREAS_DE_LAS_UBICACIONES,
            answers=answers
        )

        if response is None or response.get('status', 'unknown') != 'success':
            msg = 'Hubo un error al crear el area. Contacta a soporte'
            acceso_obj.LKFException({'msg': msg, 'title': 'Error al crear area'})
            self.statuss = 'error'
            self.status_comment = 'Hubo un error al crear el area.'
        
        return response
    
    def create_register(self, module: str, process: str, action: str, file: str, form_id: int, answers: dict):
        """Crea un registro en Linkaform con los metadatos y respuestas proporcionadas.

        Args:
            module (str): El nombre del módulo que está ejecutando la acción.
            process (str): El nombre del proceso que se está ejecutando.
            action (str): El nombre del script que se está ejecutando.
            file (str): La ruta del archivo donde se encuentra el app del modulo utilizado(Ej. jit/app.py).
            form_id (str): El ID de la forma en Linkaform.
            answers (dict): El diccionario de respuestas ya formateado.
            
        Returns:
            response: La respuesta de la API de Linkaform al crear el registro.
        """
        metadata = self.lkf_api.get_metadata(form_id=form_id)
        
        metadata.update({
            "properties": {
                "device_properties":{
                    "System": "Script",
                    "Module": module,
                    "Process": process,
                    "Action": action,
                    "File": file
                }
            },
        })
        
        metadata.update({'answers':answers})
        response = self.lkf_api.post_forms_answers(metadata)
        response = self.detail_response(response.get('status_code', 0))
        return response

if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv)
    acceso_obj.console_run()
    print('answers', simplejson.dumps(acceso_obj.answers, indent=3))
    data = acceso_obj.format_data_area(acceso_obj.answers)
    data_conf_area = json.loads(sys.argv[1])
    acceso_obj.geolocation_area = data_conf_area.get('geolocation', [])
    if acceso_obj.geolocation_area:
        acceso_obj.geolocation_area = {
            "latitude": acceso_obj.geolocation_area[0],
            "longitude": acceso_obj.geolocation_area[1]
        }
    acceso_obj.statuss = 'ok'
    acceso_obj.status_comment = ''

    #! Si trae solo el QR
    if data.get('qr_area') and not data.get('ubicacion') and not data.get('area'):
        qr_data = acceso_obj.get_record_ubicacion(tag_id_area=data.get('qr_area'))
        if qr_data:
            data['ubicacion'] = qr_data.get('ubicacion', '')
            data['area'] = qr_data.get('area', '')
            
    #! Crea el area si no existe
    if data.get('create_area', False):
        acceso_obj.create_new_area(data)
        data['area'] = data.get('nombre_nueva_area')
    else:
        #! Validacion para evitar problema con areas creadas directamente en el catalogo
        search_area = acceso_obj.get_record_ubicacion(ubicacion=data.get('ubicacion'), area=data.get('area'))
        if search_area and search_area.get('ubicacion') == data.get('ubicacion') and search_area.get('area') == data.get('area'):
            pass
        else:
            msg = 'No se encontró el área seleccionada en la forma Areas de las Ubicaciones.'
            msg += 'Intenta creandola primero y solicita a soporte borrar el area creada en catalogo.'
            acceso_obj.LKFException({'msg': msg, 'title': 'Área no encontrada'})
            data['area'] = ''
            data['qr_area'] = ''
            acceso_obj.statuss = 'error'
            acceso_obj.status_comment = 'No se encontró el área seleccionada. Intenta creandola primero.'

    #! Verificar si el qr ya esta asignado a un area
    exists_qr = False
    is_a_different_area = True
    if data.get('qr_area'):
        qr_data = acceso_obj.get_record_ubicacion(tag_id_area=data.get('qr_area'))
        if qr_data and qr_data.get('tag_id_area') == data.get('qr_area'):
            if qr_data.get('ubicacion') == data.get('ubicacion') and qr_data.get('area') == data.get('area'):
                is_a_different_area = False
            exists_qr = True

    #! Actualiza el area si ya existe
    if exists_qr and is_a_different_area:
        msg = 'Ya se ha registrado este QR en otra area.'
        acceso_obj.LKFException({'msg': msg, 'title': 'QR ya asignado'})
        acceso_obj.statuss = 'error'
        acceso_obj.status_comment = 'El QR ya esta asignado a un area diferente.'
    elif data.get('area'):
        response = acceso_obj.update_area(data)
        if response is None or response.get('status', 'unknown') != 'success':
            acceso_obj.statuss = 'error'
            acceso_obj.status_comment = 'No se pudo actualizar el area.'
        
    #! Ajuste de respuestas
    acceso_obj.answers[acceso_obj.f['status_details']] = acceso_obj.statuss
    acceso_obj.answers[acceso_obj.f['status_details_message']] = acceso_obj.status_comment

    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': acceso_obj.answers
    }))
