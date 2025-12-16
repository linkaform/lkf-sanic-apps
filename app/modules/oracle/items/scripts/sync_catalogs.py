# coding: utf-8
import sys, simplejson, time, datetime
from linkaform_api import settings
from account_settings import *

from oracle import Oracle

class Oracle(Oracle):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.class_cr = self.get_db_cr('Oracle')
        #use self.lkm.catalog_id() to get catalog id
        self.name =  __class__.__name__
        self.load('Employee', **self.kwargs)
        self.Employee.f.update({
            'worker_code':'670f585bf844ff7bc357b1dc',
            'worker_code':'670f585bf844ff7bc357b1dc',
            
            })
        self.f.update(self.Employee.f)
        self.settings = settings
        self.etl_values = {
            'A':'Activo',
            'I':'Activo',
            'H':'Masculino',
            'M':'Femenino',
            'D':'Disponible',
            'ND':'NoDisponible',
        }

        self.db_id_fields = {
            'CONTACTOID':'FEC_MODIF',
            'PAISID':'FEC_MODIF',
            'PROVINCIAID':'FEC_MODIF',
            'DEPARTAMENTOID':'FEC_MODIF',
            'CARGOID':'FEC_MODIF',
            'MARCAID':'FEC_MODIF',
            'MODELOID':'FEC_MODIF_MODELO',
            'VEHICULO_TALID':'FEC_MODIF',
            }

        self.schema_dict = {
            'LINK_EMPLEADOS':{
                'catalog_id': self.CONTACTO_CAT_ID,
                'schema':{
                    'CONTACTOID': self.f['address_code'],
                    'CIUDAD': self.f['city'],
                    'DIRECCION': self.f['address'],
                    'CODIGOPOSTAL': self.f['zip_code'],
                    'DEPARTAMENTO': self.f['worker_department'],
                    'EMAIL': self.f['email'],
                    'ESTADO_EMPLEADO': self.f['address_status'],
                    'GENERO': self.f['genero'],
                    'PUESTO': self.f['worker_position'],
                    'PAIS': self.f['country'],
                    'PROVINCIA': self.f['state'],
                    'RAZON_SOCIAL': self.f['address_name'],
                    'TELEFONO1': self.f['phone'],
                    'TELEFONO2': self.f['phone2'],
                    'TIPO_CONTACTO': self.f['address_type'],
                }
            },
            'LINK_EMPLEADOS_2':{
                'catalog_id': self.Employee.EMPLEADOS_JEFES_DIRECTOS_ID,
                'schema':{
                    'DEPARTAMENTO': self.f['worker_department'],
                    'CONTACTOID': self.f['worker_code_jefes'],
                    'EMAIL': self.f['email'],
                    'ESTADO_EMPLEADO': self.f['address_status'],
                    'GENERO': self.f['genero_jefes'],
                    'PUESTO': self.f['worker_position'],
                    'RAZON_SOCIAL': self.f['worker_name_jefes'],
                    'TELEFONO1': self.f['telefono1'],
                    'DIRECCION_CAT': self.f['address_name'],
                    'PICUTRE': self.f['picture_jefes'],
                }
            },
            'LINK_CLIENTES':{
                'catalog_id': self.CONTACTO_CAT_ID,
                'schema':{
                    'CONTACTOID': self.f['address_code'],
                    'CIUDAD': self.f['city'],
                    'DIRECCION': self.f['address'],
                    'CODIGOPOSTAL': self.f['zip_code'],
                    'DEPARTAMENTO': self.f['worker_department'],
                    'EMAIL': self.f['email'],
                    'ESTADO': self.f['address_status'],
                    'GENERO': self.f['genero'],
                    'PUESTO': self.f['worker_position'],
                    'PAIS': self.f['country'],
                    'PROVINCIA': self.f['state'],
                    'RAZON_SOCIAL': self.f['address_name'],
                    'TELEFONO1': self.f['phone'],
                    'TELEFONO2': self.f['phone2'],
                    'TIPO_CONTACTO': self.f['address_type'],
                }
            }
        }

        self.views = {
            'LINK_PAIS':{
                'catalog_id': self.COUNTRY_ID,
                'schema':{
                    'PAISID': '_id',
                    'DESCRIPCION': self.f['country'],
                    'PAISID': self.f['country_code'],
                    }
            },
            'LINK_PROVINCIAS':{
                'catalog_id': self.ESTADO_ID,
                'schema':{
                    'PROVINCIAID':  self.f['state_code'],
                    'DESCRIPCION': self.f['state'],
                    'PAIS': self.f['country'],
                    }
                },
            'LINK_DEPARTAMENTO':{
                'catalog_id': self.DEPARTAMENTOS_ID,
                'schema':{
                    'DEPARTAMENTOID': self.f['department_code'],
                    'DESCRIPCION': self.f['worker_department'],
                    }
                },
            'LINK_PUESTO':{
                'catalog_id': self.PUESTOS_ID,
                'schema':{
                    'CARGOID': self.f['worker_position_code'],
                    'DESCRIPCION': self.f['worker_position'],
                    }
            },
            'LINK_EMPLEADOS':{
                'catalog_id': self.EMPLOYEE_ID,
                'schema':{
                    'DEPARTAMENTO': self.f['worker_department'],
                    'CONTACTOID': self.f['worker_code'],
                    'EMAIL': self.f['email'],
                    'ESTADO_EMPLEADO': self.f['estatus_dentro_empresa'],
                    'GENERO': self.f['genero'],
                    'PUESTO': self.f['worker_position'],
                    'RAZON_SOCIAL': self.f['worker_name'],
                    'TELEFONO1': self.f['telefono1'],
                    'DIRECCION_CAT': self.f['address_name'],
                    'PICUTRE': self.f['picture'],
                    },
            },

            'LINK_FABRICANTE':{
                'catalog_id': self.MARCA_ID,
                'schema':{
                    'MARCAID': self.f['marca_codigo'],
                    'DESCRIPCION': self.f['marca'],
                    }
                },
            'LINK_MODELO_EQUIPOS':{
                'catalog_id': self.MODELO_ID,
                'schema':{
                    'MODELOID':  self.f['modelo_codigo'],
                    'MARCA': self.f['marca'],
                    'MODELO': self.f['modelo'],
                    'TIPO_MAQ': self.f['categoria_marca'],
                    }
                },
            'LINK_CLIENTES':{
                'catalog_id': self.CLIENTE_CAT_ID,
                'schema':{
                    'CONTACTOID': self.f['client_code'],
                    'NOMBRE_COMERCIAL': self.f['nombre_comercial'],
                    'RAZON_SOCIAL': self.f['razon_social'],
                    'DIRECCION_CAT': self.f['address_name'],
                    'RUC': self.f['rfc_razon_social'],
                    }
            },
            'LINK_EQUIPOS':{
                'catalog_id': self.ACTIVOS_FIJOS_CAT_ID,
                'schema':{
                    'VEHICULO_TALID': '_id',
                    'CATEGORIA': self.f['categoria_marca'],
                    'EQUIPO': self.f['tipo_equipo'],
                    'FABRICANTE': self.f['marca'],
                    'MODELO': self.f['modelo'],
                    'NOMBRE': self.f['nombre_equipo'],
                    'CHASIS': self.f['numero_de_serie_chasis'],
                    'CLIENTE': self.f['nombre_comercial'],
                    'ULTIMO_HOROMETRO': self.f['ultimo_horometro'],
                    'FEC_ULT_HOROMETRO': self.f['fecha_horometro'],
                    'ESTATUS': self.f['estatus'],
                    'ESTADO': self.f['estado'],
                    },
                }
            }

        self.aux_view = {
            'EQUIPOS':{
                'catalog_id': self.TIPO_DE_EQUIPO_ID,
                'schema':{
                    'VEHICULO_TALID': '_id',
                    'EQUIPO': self.f['tipo_equipo'],
                    }
                },
            'DEPARTAMENTO':{
                'catalog_id': self.CONF_DEPARTAMENTOS_PUESTOS_CAT_ID,
                'schema':{
                    'DEPARTAMENTO': self.f['worker_department'],
                    'PUESTO': self.f['worker_position'],
                    }
                }    
            }


    def find_db_id(self, data):
        res = {}
        common_key = set(data.keys()).intersection(self.db_id_fields.keys())
        if common_key:
            res = {'sync_data':{}}
            common_key = ', '.join(map(str, common_key))
            res['sync_data']['db_id'] = data[common_key]
            res['sync_data']['db_id'] = data[common_key]
            res['sync_data']['updated_at'] = self.db_updated_at
            res['sync_data']['db_updated_at'] = data[self.db_id_fields[common_key]]
        return res

    def api_etl(self, data, schema, catalog_id):
        #data: 
        translated_dict = {}
        for key, value in data.items():
            if schema.get(key) and value:
                if type(value) in (str, int, float) and self.etl_values.get(value):
                    translated_dict[schema[key]] = self.etl_values[value]
                else:
                    translated_dict[schema[key]] = value
        translated_dict.update(self.find_db_id(data))
        translated_dict.update({'catalog_id':catalog_id})
        return translated_dict

    def get_last_db_update_data(self, db_name):
        query = {"db_name":db_name}
        db_ids = self.class_cr.distinct("db_id", query)
        db_updated_at = self.class_cr.distinct("updated_at", query)
        db_updated_at.sort()
        if db_updated_at:
            db_updated_at = db_updated_at[0]
        return db_ids, db_updated_at

    def get_record_id_to_sync(self, query):
        db_ids = [r['lkf_id'] for r in self.class_cr.find(query)]
        return db_ids

    def get_oracle_id(self, data):
        common_keys = set(self.db_id_fields.keys()).intersection(data.keys())
        oracle_key = ', '.join(common_keys)
        return  data.get(oracle_key)

    def load_data(self, v, view, response, schema, catalog_id, update=False):
        metadata_catalog = self.lkf_api.get_catalog_metadata( view['catalog_id'] )
        # schema = module_obj.view_a
        data = []
        departamento_puesto = {}
        eq = self.views[v]
        for row in response:
            if v == 'LINK_EQUIPOS':
                row['CATEGORIA'] = [row['EQUIPO'],]
                row['NOMBRE'] = str(row['VEHICULO_TALID'])
                row['ESTATUS'] = 'Disponible'
                row['ESTADO'] = 'Activo'
                this_eq = row.get('EQUIPO')
                # if this_eq not in equipos:
                #     self.equipos.append(this_eq)
                #     self.equipos_row.append(row)
            elif v == 'LINK_EMPLEADOS':
                row['TIPO_CONTACTO'] = 'Persona'
                row['DIRECCION_CAT'] = row['RAZON_SOCIAL']
                row['PICUTRE'] = [{
                    'file_url':'https://f001.backblazeb2.com/file/app-linkaform/public-client-126/71202/60b81349bde5588acca320e1/64efc11e5e294b3fefca279e.png', 
                    'file_name':'default_avatar.jpg'}]
                if row.get('DEPARTAMENTO') and row['DEPARTAMENTO']:
                    departamento_puesto[row['DEPARTAMENTO']] = departamento_puesto.get(row['DEPARTAMENTO'],[])
                    if row.get('PUESTO') and row['PUESTO']:
                        if row['PUESTO'] not in departamento_puesto[row['DEPARTAMENTO']]:
                            departamento_puesto[row['DEPARTAMENTO']].append(row['PUESTO'])
            elif v == 'LINK_CLIENTES':
                row['ESTADO'] = 'Activo'
                row['DIRECCION_CAT'] = row['RAZON_SOCIAL']
                row['TIPO_CONTACTO'] = 'Empresa'
            usr = {}
            usr.update(metadata_catalog)
            usr['answers'] = self.api_etl(row, schema, catalog_id)
            usr['_id'] = usr['answers'].get('_id')
            usr['sync_data'] = usr['answers'].pop('sync_data') if usr['answers'].get('sync_data') else {}
            usr['sync_data']['oracle_id'] = self.get_oracle_id(row)
            # print('row', row.get('GENERO'))

            data.append(usr)

        if self.equipos:
            eq = self.aux_view['EQUIPOS']
            metadata_equipos = self.lkf_api.get_catalog_metadata( eq['catalog_id'] )
            data_equipos = []
            for t_eq in self.equipos_row:
                eq_ans = {}
                eq_ans.update(metadata_equipos)
                eq_ans['answers'] = self.api_etl(t_eq, eq['schema'], catalog_id)
                eq_ans['_id'] = eq_ans['answers'].get('_id')
                data_equipos.append(eq_ans)
            # self.lkf_api.post_catalog_answers_list(data_equipos)
            self.update_and_sync_db(v, eq['catalog_id'], data_equipos, update=update)         
        if departamento_puesto:
            eq = self.aux_view['DEPARTAMENTO']
            metadata_equipos = self.lkf_api.get_catalog_metadata( eq['catalog_id'] )
            this_data = []
            for dep, puestos in departamento_puesto.items():
                for puesto in puestos:
                    eq_ans = {}
                    t_row = {'DEPARTAMENTO':dep, 'PUESTO':puesto}
                    eq_ans.update(metadata_equipos)
                    eq_ans['answers'] = self.api_etl(t_row, eq['schema'], catalog_id)
                    this_data.append(eq_ans)
            # res = self.lkf_api.post_catalog_answers_list(this_data)
            query = {'db_name':'Departamentos'}
            search_db = self.search(query)
            if not search_db:
                self.update_and_sync_db('Departamentos', eq['catalog_id'], this_data, update=update)
        if data:
            # res = self.lkf_api.post_catalog_answers_list(data)
            self.update_and_sync_db(v, eq['catalog_id'], data, update=update)

    def update_and_sync_db(self, db_name, item_id, data, update=False):
        for rec in data:
            if rec.get('sync_data'):
                sync_data = rec.pop('sync_data')
                #creates
                query = {'db_id': sync_data['db_id'], 'item_id': rec['catalog_id']}
                record_id = self.get_record_id_to_sync(query)
                if record_id:
                    rec['record_id'] = record_id[0]
                    rec.pop('_id')
                    res = self.lkf_api.update_catalog_answers(rec, record_id=record_id[0])
                    res_data = res.get('json',{})
                    status_code = res['status_code']
                    if status_code in (200,201,202,204):
                        sync_data['"updated_at"'] = time.time()
                        self.update(query, sync_data, upsert=True)
                        # self.create(sync_data)
                else:
                    self.post_catalog(db_name, item_id, rec, sync_data)
            else:
                res = self.post_catalog(db_name, item_id, rec, db_sync=True)

    def post_catalog(self, db_name, item_id, rec, sync_data={}, db_sync=False):
            res = self.lkf_api.post_catalog_answers(rec)
            res_data = res.get('json',{})
            status_code = res['status_code']
            if status_code in (200,201,202,204):
                sync_data['"updated_at"'] = time.time()
                sync_data['item_id'] = res_data['catalog_id'] if res_data.get('catalog_id') else item_id
                sync_data['item_type'] = 'catalog'
                sync_data['db_name'] = db_name
                if db_sync:
                    query = {'db_name':db_name}
                    res = self.update(query, sync_data, upsert=True)
                else:
                    sync_data['lkf_id'] = res_data['id']
                    # print('Creating', sync_data)
                    res = self.create(sync_data)
            return res



if __name__ == "__main__":
    module_obj = Oracle(settings, sys_argv=sys.argv)
    module_obj.console_run()
    module_obj.db_updated_at = time.time()
    # gg = module_obj.search_views()
    # print('gg',gg)
    data = module_obj.data.get('data',{})
    option = data.get("option",'read')

    db_name = data.get('db_id',"LINK_EMPLEADOS")

    #-FUNCTIONS
    if option == 'read':

        # print('module_obj.views.keys()', module_obj.views)
        views = list(module_obj.views.keys())
        module_obj.equipos = []
        module_obj.equipos_row = []
        equipos_schema ={
                    'VEHICULO_TALID': '_id',
                    'DESCRIPCION': module_obj.f['worker_position'],
                    }
        for v in views:
            print('-----------------------------------------------------------')
            if True:
                record_ids, last_update,  = module_obj.get_last_db_update_data(v)
                # last_update_date
                update = False
                query = None
                if last_update:
                    update = True
                    #se restan 6 hrs para aplicar GMT-6:00
                    last_update = last_update - 6*60*60
                    date_time = datetime.datetime.fromtimestamp(last_update)
                    last_update_date = date_time.strftime('%Y-%m-%d %H:%M:%S')
                    print('last_update_date', last_update_date)
                    a = f"TO_TIMESTAMP('{last_update_date}', 'YYYY-MM-DD HH24:MI:SS.FF6')"
                    query = f'SELECT * FROM {v} WHERE FEC_MODIF  > {a}'

                header, response = module_obj.sync_db_catalog(db_name=v, query=query)
                # schema = getattr(module_obj, v, "Attribute not found")
                print('query=', query)
                if v == 'LINK_EMPLEADOS':
                    #Carga primero los Contactos
                    view = module_obj.schema_dict[v]
                    schema = view['schema']
                    catalog_id = view['catalog_id']
                    #module_obj.load_data(v, view, response, schema, catalog_id)
                    # Carga Jefes Directos
                    view = module_obj.schema_dict[f'{v}_2']
                    schema = view['schema']
                    catalog_id = view['catalog_id']
                    module_obj.load_data(v, view, response, schema, catalog_id, update=update)
                elif  v == 'LINK_CLIENTES':
                    view = module_obj.schema_dict[v]
                    schema = view['schema']
                    catalog_id = view['catalog_id']
                    module_obj.load_data(v, view, response, schema, catalog_id)
                view = module_obj.views[v]
                schema = view['schema']
                catalog_id = view['catalog_id']
                print('catalog_id',catalog_id)
                module_obj.load_data(v, view, response, schema, catalog_id)
