# -*- coding: utf-8 -*-
import sys, simplejson, json
from bson import ObjectId
from inspeccion_hoteleria_utils import Inspeccion_Hoteleria

from account_settings import *


preguntas_revisar = ['67ed67dfc61cd5bd89f317f9',
                    '67ed67dfc61cd5bd89f317fa',
                    '67ed662ab178b35ea5a103b8',
                    '67ed662ab178b35ea5a103b9']

class Inspeccion_Hoteleria(Inspeccion_Hoteleria):

    def actualiza_status_habitacion(self):
        """Acutaliza status de habitacion seguns su nombre.
        Obtiene del registro el nombre de la habitacion y lo envia para su actualizacion

        Returns:
            True, si se actualizo correctamente
            False, si fallo la actualizacion
        """
        self.load(module='Location', **self.kwargs)
        name = self.answers[self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID][self.Location.f['area']]
        res = self.Location.update_status_habitacion(name, 'inactiva')
        if res.get('status_code') == 202:
            return True
        else:
            return False

    def check_pending_answers(self):
        status = 'proceso'
        t = 0
        for q_id in preguntas_revisar:
            if self.answers.get(q_id):
                if self.answers.get(q_id) in ('si','no', 'sí'):
                   t += 1
        if t == len(preguntas_revisar):
            status = 'completada'
        return status

    def update_status_record(self,  status, msg_comentarios='' ):
        print('UPDATING status...', status)
        res = self.cr.update_one({'_id': ObjectId(self.record_id)}, {'$set': {f"answers.{self.field_id_status}":status}})
        return res

    def set_comentarios(self):
        comentarios = ''
        for q_id in preguntas_revisar:
            if self.answers.get(q_id):
                comentarios += f"{self.answers.get(q_id)}\n"
        return comentarios

    def is_question(self, field):
        field_type = field.get('field_type')
        if field.get('field_id') in self.exclude_field_ids:
            return False
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

        question = self.answers.get(question_id)
        if question == 'no':
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
            max_points = score_per_page['sections'][page_name]['max_points']
            if max_points:
                score_per_page['sections'][page_name]['grade'] = round(
                    score_per_page['sections'][page_name]['obtained_points'] / max_points, 2
                )
            else:
                score_per_page['sections'][page_name]['grade'] = 0
            score_per_page['grade'] = round(score_per_page['obtained_points'] / score_per_page['max_points'], 2)
        return score_per_page

    def save_results(self, score_per_page):
        data = {}
        data.update(score_per_page)
        data.update({
            '_id': ObjectId(self.record_id),
            'folio': self.folio,
            'form_id': self.form_id,
            'comments': self.comments,
            'media': self.media,
            'field_label': self.field_label,
            })
        return self.create(data, collection='inspeccion_hoteleria')

        
if __name__ == '__main__':
    module_obj = Inspeccion_Hoteleria(settings, sys_argv=sys.argv, use_api=False)
    module_obj.console_run()
    
    starting_status = module_obj.answers.get(module_obj.field_id_status)
    status = module_obj.check_pending_answers() 
    data_raw = json.loads(sys.argv[2])
    option = data_raw.get('option', '')
    
    if option == 'before':
        # module_obj.actualiza_status_habitacion()
        # Todo ver q hacer si no se actualzia bien el status de la habitacion....
        if starting_status != status:
            # res = module_obj.update_status_record(status)
            # if res.acknowledged:
            #     update_res = module_obj.cr.update_one({'form_id':module_obj.form_id,'folio':module_obj.folio}, {'$set':{'editable': False}})
            module_obj.answers[module_obj.f['status']] = 'completada'
        
        sys.stdout.write(simplejson.dumps({
            'status': 101,
            'replace_ans': module_obj.answers,
        }))
    elif option == 'after':
        module_obj.cr_inspeccion = module_obj.net.get_collections(collection='inspeccion_hoteleria')
        score_per_page = module_obj.get_grading_obj()
        res = module_obj.save_results(score_per_page)
        doc = module_obj.cr_inspeccion.find_one({'_id': ObjectId(module_obj.record_id)})
        print('FOUND DOC:', doc)
