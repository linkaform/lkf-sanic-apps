# -*- coding: utf-8 -*-
import sys

from inspeccion_hoteleria_utils import Inspeccion_Hoteleria

from account_settings import *



class Inspeccion_Hoteleria(Inspeccion_Hoteleria):


    def set_comentarios(self):
        comentarios = ''
        for q_id in preguntas_revisar:
            if self.answers.get(q_id):
                comentarios += f"{self.answers.get(q_id)}\n"
        return comentarios

    def is_question(self, field):
        field_type = field.get('field_type')
        if field_type == 'radio':
            if field.get('options'):
                for option in field.get('options'):
                    if option.get('value') in ('si','no', 'sí'):
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
                if criteria.get('value').lower() in ('si','no', 'sí'):
                    return criteria.get('points')
        return 0

    def set_comments(self, question_id, label, field):
        field_type = field.get('field_type')
        field_id = field.get('field_id')
        if field_type == 'textarea' and self.answers.get(field_id):
            self.comments[question_id] = self.answers[field_id]
            self.field_label[question_id] = label
        elif field_type == 'images' and self.answers.get(field_id):
            self.media[question_id] = self.answers[field_id]
            self.field_label[question_id] = label

    def get_grading_obj(self):
        points_per_page = []
        score_per_page = {'max_points': 0, 'obtained_points': 0, 'grade': 0,'fallas':0, 'aciertos':0, 'sections':{}}
        form_data = self.lkf_api.get_form_id_fields(self.form_id)
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
            score_per_page['sections'][page_name] = {'max_points': 0, 'obtained_points': 0, 'grade': 0,'fallas':0, 'aciertos':0}
            fields = page.get('page_fields')
            for idx, field in enumerate(fields):
                field_id = field.get('field_id')
                field_label = field.get('label')
                if self.is_question(field):
                    field_points = self.get_field_points(field)
                    score_per_page['sections'][page_name]['max_points'] += field_points
                    score_per_page['max_points'] += field_points
                    if self.answers.get(field_id) in ('si', 'sí'):
                        score_per_page['sections'][page_name]['obtained_points'] += field_points
                        score_per_page['sections'][page_name]['aciertos'] += 1
                        score_per_page['obtained_points'] += field_points
                        score_per_page['aciertos'] += 1
                        
                    elif self.answers.get(field_id) == 'no':
                        score_per_page['sections'][page_name]['fallas'] += 1
                        score_per_page['fallas'] += 1
                    self.set_comments(field_id, field_label, fields[idx+1])
                    self.set_comments(field_id, field_label, fields[idx+2])
                else:
                    continue
            score_per_page['sections'][page_name]['grade'] = round(score_per_page['sections'][page_name]['obtained_points'] / score_per_page['sections'][page_name]['max_points'], 2)
            score_per_page['grade'] = round(score_per_page['obtained_points'] / score_per_page['max_points'], 2)
        return score_per_page

    def save_results(self, score_per_page):
        data = {}
        data.update(score_per_page)
        data.update({
            '_id': self.record_id,
            'folio': self.folio,
            'form_id': self.form_id,
            'comments': self.comments,
            'media': self.media,
            'field_label': self.field_label,
            'created_at': self.created_at,
            })
        return self.create(data, collection='inspeccion_hoteleria')

    def get_record(self, folder_id):
        forms = self.lkf_api.get_folder_forms(folder_id)
        forms = [x['form_id'] for x in forms]
        records = self.cr.find({'form_id': {'$in': forms}},{'answers': 1, 'form_id': 1, 'folio': 1, 'created_at': 1})        
        return records
        
        
if __name__ == '__main__':
    module_obj = Inspeccion_Hoteleria(settings, sys_argv=sys.argv, use_api=False)
    module_obj.console_run()
    records = module_obj.get_record(131836)
    for record in records:
        print('record', record['folio'])
        module_obj.record_id = record.get('_id')
        module_obj.answers = record.get('answers')
        module_obj.form_id = record.get('form_id')
        module_obj.folio = record.get('folio')
        module_obj.created_at = record.get('created_at')
        score_per_page = module_obj.get_grading_obj()
        res = module_obj.save_results(score_per_page)
        print('saved on', res)

