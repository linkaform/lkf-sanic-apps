# -*- coding: utf-8 -*-
import sys, simplejson, re, time
from linkaform_api import settings, network, utils
from datetime import datetime, timedelta

from calidad_utils import Calidad
import pytz

class Calidad(Calidad):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)

    def set_status_proceso(self, current_record, record_id, new_estatus, msg=''):
        current_record['answers'].update({ self.f['status_reporte']: new_estatus, self.f['observaciones_reporte']: msg })
        self.lkf_api.patch_record(current_record, record_id, jwt_settings_key='USER_JWT_KEY')

    """
    # Obtiene el registro del catálogo según el nombre del Producto
    """
    def get_record_producto_catalogo(self, value_field_catalog ):
        if type(value_field_catalog) == list and value_field_catalog:
            value_field_catalog = value_field_catalog[0]
        mango_query = {"selector":
            {"answers":
                {"$and":[
                    {self.f['nombre_producto_calidad']: {'$eq': value_field_catalog}}
                ]}},
            "limit":1,
            "skip":0}
        res = self.lkf_api.search_catalog( self.PRODUCTOS_CALIDAD_ID, mango_query)
        return res

    """
    # Obtiene los valores mínimo, target y máximo del catálogo para cada concepto que se graficará que inicia con aaaaa
    """
    def get_values_conceptos_to_graph(self, prod_catalogo, conceptos_to_graph ):
        info_cat = prod_catalogo[0]
        dict_concept_to_graph = {}
        for id_f in conceptos_to_graph:
            # lasLetters lleva los últimos dígitos del field_id después de aaaaa
            lastLetters = id_f[5:]
            dict_to_graph = {}
            # fields_min_max es una lista de todos los campos que tienen la misma terminación que el aaaaa
            # esto para cuadrar que sea el mínimo, target y máximo que le corresponde
            fields_min_max = [ i for i in info_cat.keys() if lastLetters in i ]
            for f in fields_min_max:
                if 'bbbbb' in f:
                    dict_to_graph.update({'lsl': info_cat[f]})
                elif 'ccccc' in f:
                    dict_to_graph.update({'target': info_cat[f]})
                elif 'ddddd' in f:
                    dict_to_graph.update({'usl': info_cat[f]})
            dict_concept_to_graph[ id_f ] = dict_to_graph
        return dict_concept_to_graph

    def get_date_query(self, date_from, date_to):
        res = {}
        if date_from and date_to:
            res.update({
            'end_date': {
            '$gte':datetime.strptime('%s 00:00:00'%(date_from), "%Y-%m-%d %H:%M:%S") - timedelta(seconds=time.timezone),
            '$lt':datetime.strptime('%s 23:59:59'%(date_to), "%Y-%m-%d %H:%M:%S") - timedelta(seconds=time.timezone),
            }
            })
        elif date_from and not date_to:
            res.update({
            'end_date': {
            '$gte':datetime.strptime('%s 00:00:00'%(date_from), "%Y-%m-%d %H:%M:%S") - timedelta(seconds=time.timezone)
            }
            })

        elif not date_from and date_to:
            res.update({
            'end_date': {
            '$lt':datetime.strptime('%s 23:59:59'%(date_to), "%Y-%m-%d %H:%M:%S") - timedelta(seconds=time.timezone)
            }
            })
        return res

    def get_production_qty(self, form_id, date_from, date_to, product_serach, orden_produccion=None):
        match_query = {'form_id': form_id, 'deleted_at': {'$exists': False}}
        match_query.update(self.get_date_query(date_from, date_to))
        match_query.update(product_serach)
        if orden_produccion:
            #! No se de donde salga este obj id, ya se busco
            match_query.update({'answers.a10000000000000000000017': orden_produccion})
        aggregate_query = [
            { "$match": match_query },
        {'$project':{
            '_id':0,
            'producto': f'$answers.{self.PRODUCTOS_CALIDAD_OBJ_ID}.{self.f["nombre_producto_calidad"]}',
            'qty':{'$sum':[
                f'$answers.{self.f["cantidad_producida_c1"]}',
                f'$answers.{self.f["cantidad_producida_c2"]}',
                f'$answers.{self.f["cantidad_producida_c3"]}',
                f'$answers.{self.f["cantidad_producida_c4"]}',
                f'$answers.{self.f["cantidad_producida_c5"]}']},
            'falla': f'$answers.{self.f["existe_alguna_falla"]}',
            'fecha':'$end_date'
        }},
        {'$group':{
        '_id':{
            'producto':'$producto'},
        'qty':{'$sum':'$qty'},
        'falla':{'$push':{'falla':'$falla','fecha':'$fecha'}}
        }
        }
        ]
        # print('aggregate_query=', aggregate_query)
        group_rec = self.cr.aggregate(aggregate_query)
        falla = ""
        qty=0
        for g in group_rec:
            #print('g={}'.format(g))
            qty = g.get('qty')
            falla_list= g.get('falla')
            for f in falla_list:
                if f.get('falla'):
                    falla += "{} : {} / ".format(f.get('fecha').strftime('%Y-%m-%d %H:%M'),f.get('falla'))
        res ={}
        if falla or qty:
            res.update({self.f['cantidad_producida_grafico']:qty, self.f['fallas_grafico']:falla})
        #todo acomdar las fallas, quitar las fechas que no tengan falla y ponerlas en text
        return res

    def get_data(self, form_id, filter_producto, filter_proceso, list_ids_to_graph=[], orden_produccion=None, codigo_producto=None,
        fecha_inicio=None, fecha_fin=None):
        codigo_record = None
        match_query = {'form_id': form_id, 'deleted_at': {'$exists': False}}

        if codigo_producto:
            #! No se que catalogo sea
            match_query.update({'answers.605548e4d8fcccc640e62897.605548e4d8fcccc640e62898': codigo_producto})
        if orden_produccion:
            #! No se de donde salga este obj id, ya se busco
            match_query.update({'answers.a10000000000000000000017': orden_produccion})

        match_query.update(self.get_date_query(fecha_inicio, fecha_fin))
        match_query.update(filter_producto)
        match_query.update(filter_proceso)

        dict_project = { l: '$answers.{}'.format(l) for l in list_ids_to_graph }
        dict_project.update({
            'auditor':'$created_by_name',
            'fecha':{ '$dateToString': { 'format': "%Y-%m-%d %H:%M:%S", 'date': "$end_date" } }
        })


        aggregate_query = [
            { "$match": match_query },
            { "$project": dict_project }
        ]
        #print('*** aggregate_query',aggregate_query)
        #print('db.form_answer.aggregate({})'.format(aggregate_query))
        records = self.cr.aggregate(aggregate_query)

        datos = {a:[] for a in list_ids_to_graph}

        for a in records:
            #print('a={}'.format(a))
            for d in datos:
                datos[ d ].append(self.format_data(a, d) if self.format_data(a, d) !=None else None )
        return datos

    def format_data(self, row, parameter):
        res = None
        if row.get(parameter):
            try:
                val_to_param = float( row.get(parameter) )
            except:
                val_to_param = 0
            res = {
                    self.f['fecha_hora_grupo_datos']: row.get('fecha'),
                    self.f['valor_grupo_datos']: val_to_param,
                    self.f['auditor_grupo_datos']: row.get('auditor'),
                }
        return res

    def proceso_graficacion(self, current_record, record_id):
        answers = current_record.get('answers', {})

        fecha_inicio = answers.get(self.f['fecha_inicio_reporte'], '')
        fecha_fin = answers.get(self.f['fecha_fin_reporte'], '')

        # Obtengo el label de los campos, después me servirá para los nombres de cada gráfico a generar
        form_fields = self.lkf_api.get_form_id_fields(current_record['form_id'], jwt_settings_key='USER_JWT_KEY')
        fields = form_fields[0]['fields']
        dict_fields_current_form = { f.get('field_id', ''): f.get('label', '') for f in fields }

        producto = ''
        field_id_catalogo_producto = ''
        id_catalogo_producto = 0
        dict_proceso_maquina = {}
        dict_producto = {}
        field_id_to_graphs = ''
        for field_id in dict_fields_current_form.keys():
            # Se identica el grupo repetitivo donde se pegarán los graficos
            if re.match(r"^fffff", field_id):
                field_id_to_graphs = field_id
        if not field_id_to_graphs:
            print('No hay campo grupo repetitivo donde el id empiece por fffff para depositar las gráficas generadas')
            self.set_status_proceso(current_record, record_id, 'error', msg='No hay campo grupo repetitivo donde el id empiece por fffff para depositar las gráficas generadas')
            return False
        if not self.INSPECCION_CALIDAD:
            print('No se identifico el ID de la forma de inspección de calidad')
            self.set_status_proceso(current_record, record_id, 'error', msg='No se identifico el ID de la forma de inspección de calidad')
            return False

        # Obtengo el label de los campos, después me servirá para los nombres de cada gráfico a generar
        form_id_inspeccion = self.INSPECCION_CALIDAD
        form_fields = self.lkf_api.get_form_id_fields(form_id_inspeccion, jwt_settings_key='USER_JWT_KEY')
        fields = form_fields[0]['fields']
        dict_fields_label = { f.get('field_id', ''): f.get('label', '') for f in fields }
        for a in answers:
            ans = answers[a]
            if type( ans ) == dict:
                # Puede ser un catálogo y debo revisar en los índices del diccionario a ver si cumple con la estructura
                # 00000ffff{idcatalogo}
                for i in ans:
                    if re.match(r"^0000[0|1|2]ffff(\d{5})", i):
                        tipo_campo = i[:5]
                        id_catalogo_campo = i[9:14]
                        try:
                            id_catalogo_campo = int(id_catalogo_campo)
                        except:
                            print( 'Campo mal configurado en el id del catalogo {}'.format( id_catalogo_campo ) )
                            self.set_status_proceso(current_record, record_id, 'error', msg='Campo mal configurado en el id del catalogo {}'.format( id_catalogo_campo ))
                            return False
                        if tipo_campo == '00000':
                            producto = ans[i]
                            id_catalogo_producto = id_catalogo_campo
                            field_id_catalogo_producto = i
                            dict_producto[ 'answers.{}.{}'.format(a, i) ] = producto
                        else:
                            dict_proceso_maquina[ 'answers.{}.{}'.format(a, i) ] = ans[i]

        # Si cumple con la regla de iniciar con aaaaa entonces es un concepto a considerar
        conceptos_to_graph = [ f_id for f_id in dict_fields_label.keys() if re.match(r"^aaaaa", f_id) ]

        print('==== producto={} id_catalogo_producto={} field_id_catalogo_producto={}'.format( producto, id_catalogo_producto, field_id_catalogo_producto ))
        print('==== conceptos_to_graph=',conceptos_to_graph)
        print('==== dict_proceso_maquina=',dict_proceso_maquina)
        print('==== dict producto', dict_producto)
        product_serach={}
        product_serach.update(dict_producto)
        product_serach.update(dict_proceso_maquina)

        prodcut_detail = self.get_production_qty(form_id_inspeccion, fecha_inicio, fecha_fin, product_serach)
        print('prodcut_detail',prodcut_detail)
        current_record['answers'].update(prodcut_detail)
        prod_catalogo = self.get_record_producto_catalogo( producto )
        if prod_catalogo:
            list_graficos = []
            list_datos = []
            # print('registro de producto encontrado')
            #print('prod_catalogo=',prod_catalogo)
            values_to_graph = self.get_values_conceptos_to_graph(prod_catalogo, conceptos_to_graph)
            # print('===== values_to_graph=',values_to_graph)
            data_records = self.get_data( form_id_inspeccion, dict_producto, dict_proceso_maquina, list_ids_to_graph=conceptos_to_graph, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin )
            #print('===== data_records=', data_records)
            for val_graph in values_to_graph:
                values_min_max = values_to_graph[ val_graph ]
                label_item = dict_fields_label.get( val_graph, '' )
                values_min_max.update({
                    'name': label_item
                    })
                data = [ s.get(self.f['valor_grupo_datos'], 0) for s in data_records.get( val_graph, [] ) if s]
                if data:
                    # try:
                    #     data = [float(d) for d in data if d]
                    # except:
                    #     print('Error al convertir a float el data', data)
                    #     continue
                    set_graph = self.get_graph_info(values_min_max, data, current_record['form_id'])
                    #print('===== grafico generado=',set_graph)
                    list_graficos.append( set_graph )
                for s in data_records.get( val_graph, [] ):
                    if s:
                        s.update({self.f['parametro_de_medicion']: label_item})
                        list_datos.append( s )
            if list_graficos:
                current_record['answers'].update({
                    field_id_to_graphs: list_graficos,
                    self.f['grupo_datos']: list_datos,
                    self.f['status_reporte']: 'realizado',
                    self.f['observaciones_reporte']: ''
                    })
                self.lkf_api.patch_record(current_record, record_id, jwt_settings_key='USER_JWT_KEY')
            else:
                self.set_status_proceso(current_record, record_id, 'error', msg='No se encontró información')

if __name__ == "__main__":
    script_obj = Calidad(settings, sys_argv=sys.argv)
    script_obj.console_run()
    current_record = simplejson.loads( sys.argv[1] )
    current_record = script_obj.lkf_api.drop_fields_for_patch(current_record)
    record_id = script_obj.record_id
    script_obj.set_status_proceso(current_record, record_id, 'procesando')
    script_obj.proceso_graficacion( current_record, record_id )
