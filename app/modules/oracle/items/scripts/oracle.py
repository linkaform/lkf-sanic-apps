# -*- coding: utf-8 -*-
from datetime import datetime
from linkaform_api import base

from linkaform_api import base
from lkf_addons.employee.app import Employee
from lkf_addons.activo_fijo.app import Vehiculo

from lkf_addons.oracle.app import Oracle

class Oracle(Oracle):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        print('de aqui...')
        #use self.lkm.catalog_id() to get catalog id
        self.name =  __class__.__name__
        self.settings = settings
        print('self f', self.f)


#         # Forms

#         # #--Variable Catalogs
#         # self.ACCESOS = self.lkm.catalog_id('accesos')
#         # self.ACCESOS_ID = self.ACCESOS.get('id')
#         # self.ACCESOS_OBJ_ID = self.ACCESOS.get('obj_id')

        # self.mf =  {
        #     'CIUDADID': self.f['city'] ,
        #     'DESCRIPCION': self.f['city'] , 
        #     'PROVINCIA': f"{self.ESTADO_OBJ_ID}.{self.f['state']}"
              
        #   }

#         self.fecha = self.date_from_str('2024-01-15')
    
#     #---Format Functions 

    def sync_db_catalog(self, db_name, query={}):
        header, data = self.query_view(db_name, query=query)
        return header, data