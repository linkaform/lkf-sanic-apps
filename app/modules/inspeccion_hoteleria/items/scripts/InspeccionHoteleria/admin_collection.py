# -*- coding: utf-8 -*-
import sys, simplejson, json
from bson import ObjectId
from inspeccion_hoteleria_utils import Inspeccion_Hoteleria

from account_settings import *

class Inspeccion_Hoteleria(Inspeccion_Hoteleria):

    def is_question(self, field):
        field_type = field.get('field_type')
        if field.get('field_id') in self.exclude_field_ids:
            return False
        if field_type == 'radio':
            if field.get('options'):
                for option in field.get('options'):
                    if option.get('value') in ['si','no']:
                        return True
        return False

    def get_field_points(self, field):
        """
        Obtiene los puntos de un campo
        
        Args:
            field (dict): campo

        Returns:
            int: puntos del campo
        """
        grading_criteria = field.get('grading_criteria')
        if grading_criteria:
            for criteria in grading_criteria.get('equal'):
                if criteria.get('value').lower() in ['si','no']:
                    return criteria.get('points')
        return 0

    def set_comments(self, question_id, label, field):
        field_type = field.get('field_type')
        field_id = field.get('field_id')

        question = self.answers.get(question_id)
        if question in ['no']:
            self.field_label[question_id] = label
            
        if field_type == 'textarea' and self.answers.get(field_id):
            self.comments[question_id] = self.answers[field_id]
        elif field_type == 'images' and self.answers.get(field_id):
            self.media[question_id] = self.answers[field_id]

    def get_grading_obj(self):
        points_per_page = []
        score_per_page = {'max_points': 0, 'obtained_points': 0, 'grade': 0,'fallas':0, 'aciertos':0, 'sections':{}}
        if not self.form_data.get(self.form_id):
            self.form_data[self.form_id] = self.lkf_api.get_form_id_fields(self.form_id)
        form_data = self.form_data[self.form_id]
        if form_data:
            form_data = form_data[0]
        else:
            self.LKFException('No se encontro el formulario')
        form_pages = form_data.get('form_pages')
        self.comments = {}
        self.media = {}
        self.field_label = {}
        for page in form_pages:
            page_name = page.get('page_name')
            if page_name in ['Estación', 'Cierre']:
                continue
            score_per_page['sections'][page_name] = {'max_points': 0, 'obtained_points': 0, 'grade': 0,'fallas':0, 'aciertos':0}
            fields = page.get('page_fields')
            for idx, field in enumerate(fields):
                field_id = field.get('field_id')
                field_label = field.get('label')
                if self.is_question(field):
                    field_points = self.get_field_points(field)
                    score_per_page['sections'][page_name]['max_points'] += field_points
                    score_per_page['max_points'] += field_points
                    # print('=====================', self.answers.get(field_id))
                    if self.answers.get(field_id) in ['si']:
                        score_per_page['sections'][page_name]['obtained_points'] += field_points
                        score_per_page['sections'][page_name]['aciertos'] += 1
                        score_per_page['obtained_points'] += field_points
                        score_per_page['aciertos'] += 1
                        
                    elif self.answers.get(field_id) in ['no']:
                        score_per_page['sections'][page_name]['fallas'] += 1
                        score_per_page['fallas'] += 1
                    self.set_comments(field_id, field_label, fields[idx+1])
                    self.set_comments(field_id, field_label, fields[idx+2])
                else:
                    continue
            max_points = score_per_page['sections'][page_name]['max_points']
            if max_points:
                score_per_page['sections'][page_name]['grade'] = round(
                    score_per_page['sections'][page_name]['obtained_points'] / max_points, 2
                )
            else:
                score_per_page['sections'][page_name]['grade'] = 0
            # score_per_page['grade'] = round(score_per_page['obtained_points'] / score_per_page['max_points'], 2)
            score_per_page['grade'] = 0
            # print('score_per_page:', score_per_page)
            # print('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')
        return score_per_page

    def save_results(self, score_per_page):
        data = {}
        data.update(score_per_page)
        data.update({
            # '_id': self.record_id,
            '_id': ObjectId(self.record_id),
            'folio': self.folio,
            'form_id': self.form_id,
            'comments': self.comments,
            'media': self.media,
            'field_label': self.field_label,
            })
        # print('data:', simplejson.dumps(data, indent=3))
        # breakpoint()
        return self.create(data, collection='inspeccion_collection')
    
    def dev_get_record(self):
        query = [
            {"$match": {
                "form_id": 129506,
                "deleted_at": {"$exists": False},
                "_id": ObjectId('68842bcc0fcff4b1f18ace75')
            }},
            {"$limit": 1},
        ]
        
        answers = self.format_cr(self.cr.aggregate(query))
        answers = self.unlist(answers)
        self.answers = answers
        
    def dev_get_inspecciones_collection(self, form_id):
        query = {"form_id": form_id}
        project = {'field_label': 1}
        # pipeline = [
        #     {"$group": {
        #         "_id": "$folio",
        #         "count": {"$sum": 1},
        #         "ids": {"$push": "$_id"}
        #     }},
        #     {"$match": {"count": {"$gt": 1}}}
        # ]
        res = self.cr_inspeccion.find(query)
        res = list(res)
        print(f"Total de inspecciones encontradas: {len(res)}")
        # for r in res:
        #     print(r)
            
    def dev_clear_collection(self):
        """Elimina todos los registros de la coleccion inspeccion_collection"""
        self.cr_inspeccion.delete_many({})
        print('Colección inspeccion_collection limpiada.')

    def get_form_records(self, form_id):
        match_query = {
            "deleted_at": {"$exists": False},
            "form_id": form_id,
        }
        res = self.cr.find(match_query)
        return [x for x in res]
        
if __name__ == '__main__':
    module_obj = Inspeccion_Hoteleria(settings, sys_argv=sys.argv, use_api=False)
    module_obj.console_run()

    # DEV UTILS
    module_obj.cr_inspeccion = module_obj.net.get_collections(collection='inspeccion_collection')
    # Limpiar collection
    # module_obj.dev_clear_collection()
    # Obtener toda la collection
    # module_obj.dev_get_inspecciones_collection(141323)
    
    # Cargar todos los registros de inspeccion_collection    
    records = module_obj.get_form_records(141323)
    print('Total records found:', len(records))
    for record in records:
        module_obj.record_id = record.get('_id')
        module_obj.answers = record.get('answers')
        module_obj.form_id = record.get('form_id')
        module_obj.folio = record.get('folio')
        module_obj.created_at = record.get('created_at')
        score_per_page = module_obj.get_grading_obj()
        res = module_obj.save_results(score_per_page)
        print('res==========', res)
    
    # Esto es lo que ejecuta cada registro creado para la coleccion inspeccion_collection
    # score_per_page = module_obj.get_grading_obj()
    # res = module_obj.save_results(score_per_page)
    # print('res==========', res)    
