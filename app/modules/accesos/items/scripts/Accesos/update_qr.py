# coding: utf-8
#####
# Script para actualizar QR
#####
import sys, simplejson, json

from accesos_utils import Accesos
from account_settings import *

class Accesos(Accesos):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)
        self.load(module='Location', **self.kwargs)

        self.f.update({
            'option_update_qr': '68928c76fc027d15895fa23c',
            'anterior_qr': '68928cfdc847e631ba2c157e',
            'new_qr': '68928cfdc847e631ba2c157f',
            'tag_id_area_ubicacion': '6762f7b0922cc2a2f57d4044',
            'status_new_qr': '68929562c6b050d5066a2aec',
            'details_new_qr': '68929562c6b050d5066a2aed',
        })

    def format_data_area(self, data):
        formatted_data = {}
        
        formatted_data.update({
            'option': data.get(self.f['option_update_qr'], ''),
            'ubicacion': data.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.Location.f['location'], ''),
            'area': data.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID, {}).get(self.Location.f['area'], ''),
            'qr_anterior': data.get(self.f['anterior_qr'], ''),
            'qr_nuevo': data.get(self.f['new_qr'], '')
        })

        return formatted_data
    
    def get_record_ubicacion(self, ubicacion=None, area=None, tag_id_area=None):
        match_query = {
            "deleted_at":{"$exists":False},
            "form_id": self.Location.AREAS_DE_LAS_UBICACIONES,
        }
        if ubicacion:
            match_query.update({
                f"answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}": ubicacion,
            })
        if area:
            match_query.update({
                f"answers.{self.Location.f['area']}": area
            })
        if tag_id_area:
            match_query.update({
                f"answers.{self.f['tag_id_area_ubicacion']}": tag_id_area
            })

        query = [
            {'$match': match_query },
            {'$project': {
                'folio': {'$ifNull': ['$folio', '']},
                '_id': 1,
                'ubicacion': f"$answers.{self.UBICACIONES_CAT_OBJ_ID}.{self.Location.f['location']}",
                'area': f"$answers.{self.Location.f['area']}",
                'tag_id_area': {'$ifNull': [f"$answers.{self.f['tag_id_area_ubicacion']}", '']},
            }},
            {'$limit': 1},
            {'$sort':{'folio':-1}},
        ]
        res = self.format_cr(self.cr.aggregate(query))
        res = self.unlist(res)
        return res
    
    def update_area_tag_id(self, data):
        option = data.get('option', '')
        ubicacion = data.get('ubicacion', None)
        area = data.get('area', None)
        tag_id = data.get('qr_anterior', None)
        
        if option == 'seleccionar_area_y_ubicacion':
            area_ubicacion_data = self.get_record_ubicacion(ubicacion=ubicacion, area=area)
        elif option == 'escanear_qr_anterior':
            area_ubicacion_data = self.get_record_ubicacion(tag_id_area=tag_id)
            if not area_ubicacion_data:
                return {
                    'status': 'error',
                    'details': 'No se encontró el QR anterior en ningun area registrada, favor de verificar el QR escaneado.'
                }
        
        answers = {}
        record_id = area_ubicacion_data.get('_id', '')
        answers[self.f['tag_id_area_ubicacion']] = data.get('qr_nuevo', '')

        if answers:
            response = self.lkf_api.patch_multi_record(answers=answers, form_id=self.Location.AREAS_DE_LAS_UBICACIONES, record_id=[record_id])        
            if response.get('status_code', 0) in [200, 201, 202]:
                return {
                    'status': 'success',
                    'details': 'QR actualizado correctamente',
                }
            else:
                return {
                    'status': 'error',
                    'details': 'Hubo un error al actualizar el QR',
                }
        return {
            'status': 'error',
            'details': 'Hubo un error inesperado, favor de revisar los logs...',
        }

if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv)
    acceso_obj.console_run()
    print('Formatted Answers:', simplejson.dumps(acceso_obj.answers, indent=3))
    data = acceso_obj.format_data_area(acceso_obj.answers)
    
    response = acceso_obj.update_area_tag_id(data)
    acceso_obj.answers[acceso_obj.f['status_new_qr']] = response.get('status', 'error')
    acceso_obj.answers[acceso_obj.f['details_new_qr']] = response.get('details', 'No details provided')

    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': acceso_obj.answers
    }))
