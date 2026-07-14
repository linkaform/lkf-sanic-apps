# -*- coding: utf-8 -*-
### Linkaform Modules / Archivo de Módulo ###
'''
Este archivo define el modelo de datos del módulo Accesos.
Contiene los IDs de formularios, catálogos y campos (fields) usados por la clase Accesos.

Separado de service.py para mantener la configuración de datos desacoplada de la
lógica de negocio (mismo patrón que lkf_addons/addons/accesos/model.py).
'''

from ..base.app import Base


### Modelo de Módulo ###
'''
AccesosModel agrupa la inicialización de IDs de formularios, catálogos y fields.
La clase Accesos en service.py hereda de esta clase para tener acceso a todas las
variables sin mezclarlas con la lógica de negocio.
'''

class AccesosModel(Base):

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        #--Variables
        # Module Globals#
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api, **kwargs)

        self.load(module='Employee', **self.kwargs)
        self.load(module='Location', **self.kwargs)
        self.load(module='Activo_Fijo', module_class='Vehiculo', import_as='AF', **self.kwargs)

        self.cr_cache = self.net.get_collections(collection='rondin_caches', create=True)


        self.support_guard = 'guardia_de_apoyo'
        self.chife_guard = 'guardia_lider'
        # Forms #
        '''
        Use `self.FORM_NAME = self.lkm.form_id('form_name',id)` ---> Aquí deberás guardar los `ID` de los formularios.
        Para ello deberás llamar el método `lkm.form_id` del objeto `lkm` (linkaform modules, por sus siglas).
        En `lkm` están todas las funciones generales de módulos.
        '''
        self.ACCESOS_NOTAS = self.lkm.form_id('notas','id')
        self.BITACORA_ACCESOS = self.lkm.form_id('bitacora_de_entradas_y_salidas','id')
        self.BITACORA_OBJETOS_PERDIDOS = self.lkm.form_id('bitacora_objetos_perdidos','id')
        self.BITACORA_FALLAS = self.lkm.form_id('bitacora_de_fallas','id')
        self.BITACORA_INCIDENCIAS = self.lkm.form_id('bitacora_de_incidencias','id')
        self.BITACORA_GAFETES_LOCKERS = self.lkm.form_id('bitacora_de_gafetes_y_lockers','id')
        self.CARGA_PERMISOS_VISITANTES = self.lkm.form_id('carga_de_permisos_de_visitantes','id')
        self.CHECKIN_CASETAS = self.lkm.form_id('checkin_checkout_casetas','id')
        self.CONCESSIONED_ARTICULOS = self.lkm.form_id('concesion_de_activos_unico','id')
        self.CONFIGURACION_AREA_FORM = self.lkm.form_id('configuracion_de_area','id')
        self.CONFIGURACION_RECORRIDOS_FORM = self.lkm.form_id('configuracion_de_recorridos','id')
        self.CONF_PERFILES = self.lkm.form_id('configuracion_de_perfiles','id')
        self.PASE_ENTRADA = self.lkm.form_id('pase_de_entrada','id')
        self.PASE_ENTRADA_TRANSPORTISTA = self.lkm.form_id('pase_de_entrada_transportista','id')
        self.BITACORA_TRANSPORTISTAS = self.lkm.form_id('bitacora_de_transportistas','id')
        self.INSPECCION_ENTRADA_CTPAT_TRACTOR = self.lkm.form_id('inspeccion_de_entrada_ctpat_tractor_cabezal','id')
        self.INSPECCION_ENTRADA_CTPAT_REMOLQUE = self.lkm.form_id('inspeccion_de_entrada_ctpat_remolque','id')
        self.INSPECCION_ENTRADA_CTPAT_CONTENEDOR = self.lkm.form_id('inspeccion_de_entrada_ctpat_contenedor','id')
        self.INSPECCION_SELLO = self.lkm.form_id('inspeccion_de_sello','id')
        self.PROGRAMAR_TAREAS = self.lkm.form_id('programar_tareas', 'id')
        self.PUESTOS_GUARDIAS = self.lkm.form_id('puestos_de_guardias','id')
        self.VISITA_AUTORIZADA = self.lkm.form_id('visita_autorizada','id')
        self.CONF_ACCESOS = self.lkm.form_id('configuracion_accesos','id')
        self.CONF_MODULO_SEGURIDAD = self.lkm.form_id('configuracion_modulo_seguridad','id')
        self.PAQUETERIA = self.lkm.form_id('paqueteria','id')
        self.BITACORA_RONDINES = self.lkm.form_id('bitacora_rondines','id')
        self.CHECK_UBICACIONES = self.lkm.form_id('check_ubicaciones','id')
        self.REGISTRO_ASISTENCIA = self.lkm.form_id('registro_de_asistencia','id')
        self.FORMATO_VACACIONES = self.lkm.form_id('formato_vacaciones_aviso','id')
        self.PROVEEDORES_FORM = self.lkm.form_id('proveedores','id')
        self.MENUS_FORM = self.lkm.form_id('configuracion_menus','id')
        self.HORARIOS = self.lkm.form_id('horarios','id')

        self.last_check_in = []
        # self.FORM_ALTA_COLABORADORES = self.lkm.form_id('alta_de_colaboradores_visitantes','id')
        # self.FORM_ALTA_EQUIPOS = self.lkm.form_id('alta_de_equipos','id')
        # self.FORM_ALTA_VEHICULOS = self.lkm.form_id('alta_de_vehiculos','id')
        # self.FORM_BITACORA = self.lkm.form_id('bitacora','id')
        # self.FORM_LOCKER = self.lkm.form_id('locker','id')
        # self.FORM_PASE_DE_ENTRADA = self.lkm.form_id('pase_de_entrada','id')
        # self.FORM_REGISTRO_PERMISOS = self.lkm.form_id('registro_de_permisos','id')

        #--Variables
        ### Catálogos ###
        '''
        Use `self.CATALOG_NAME = self.lkm.catalog_id('catalog_name',id)` ---> Aquí deberás guardar los `ID` de los catálogos.
        Para ello deberás llamar el método `lkm.catalog_id` del objeto `lkm`(linkaform modules, por sus siglas).
        En `lkm` están todas las funciones generales de módulos).
        '''

        self.ACTIVOS_FIJOS_CAT = self.lkm.catalog_id('activos_fijos')
        self.ACTIVOS_FIJOS_CAT_ID = self.ACTIVOS_FIJOS_CAT.get('id')
        self.ACTIVOS_FIJOS_CAT_OBJ_ID = self.ACTIVOS_FIJOS_CAT.get('obj_id')

        self.CONFIGURACION_GAFETES_LOCKERS = self.lkm.catalog_id('configuracion_de_gafetes_y_lockers')
        self.CONFIGURACION_GAFETES_LOCKERS_ID = self.CONFIGURACION_GAFETES_LOCKERS.get('id')
        self.CONFIGURACION_GAFETES_LOCKERS_OBJ_ID = self.CONFIGURACION_GAFETES_LOCKERS.get('obj_id')

        self.CONFIGURACION_RECORRIDOS = self.lkm.catalog_id('configuracion_de_recorridos')
        self.CONFIGURACION_RECORRIDOS_ID = self.CONFIGURACION_RECORRIDOS.get('id')
        self.CONFIGURACION_RECORRIDOS_OBJ_ID = self.CONFIGURACION_RECORRIDOS.get('obj_id')

        self.CONFIG_PERFILES = self.lkm.catalog_id('configuracion_de_perfiles')
        self.CONFIG_PERFILES_ID = self.CONFIG_PERFILES.get('id')
        self.CONFIG_PERFILES_OBJ_ID = self.CONFIG_PERFILES.get('obj_id')

        self.DEFINICION_PERMISOS = self.lkm.catalog_id('definicion_de_permisos')
        self.DEFINICION_PERMISOS_ID = self.DEFINICION_PERMISOS.get('id')
        self.DEFINICION_PERMISOS_OBJ_ID = self.DEFINICION_PERMISOS.get('obj_id')

        self.GAFETES_CAT = self.lkm.catalog_id('gafetes')
        self.GAFETES_CAT_ID = self.GAFETES_CAT.get('id')
        self.GAFETES_CAT_OBJ_ID = self.GAFETES_CAT.get('obj_id')

        self.LOCKERS_CAT = self.lkm.catalog_id('lockers')
        self.LOCKERS_CAT_ID = self.LOCKERS_CAT.get('id')
        self.LOCKERS_CAT_OBJ_ID = self.LOCKERS_CAT.get('obj_id')

        self.PERFILES = self.lkm.catalog_id('perfiles')
        self.PERFILES_ID = self.PERFILES.get('id')
        self.PERFILES_OBJ_ID = self.PERFILES.get('obj_id')

        self.PASE_ENTRADA_CAT = self.lkm.catalog_id('pase_de_entrada')
        self.PASE_ENTRADA_ID = self.PASE_ENTRADA_CAT.get('id')
        self.PASE_ENTRADA_OBJ_ID = self.PASE_ENTRADA_CAT.get('obj_id')

        self.TIPO_ARTICULOS_PERDIDOS_CAT = self.lkm.catalog_id('lista_de_objetos')
        self.TIPO_ARTICULOS_PERDIDOS_CAT_ID = self.TIPO_ARTICULOS_PERDIDOS_CAT.get('id')
        self.TIPO_ARTICULOS_PERDIDOS_CAT_OBJ_ID = self.TIPO_ARTICULOS_PERDIDOS_CAT.get('obj_id')

        self.VISITA_AUTORIZADA_CAT = self.lkm.catalog_id('visita_autorizada')
        self.VISITA_AUTORIZADA_CAT_ID = self.VISITA_AUTORIZADA_CAT.get('id')
        self.VISITA_AUTORIZADA_CAT_OBJ_ID = self.VISITA_AUTORIZADA_CAT.get('obj_id')

        self.LISTA_INCIDENCIAS_CAT = self.lkm.catalog_id('lista_de_incidentes')
        self.LISTA_INCIDENCIAS_CAT_ID = self.LISTA_INCIDENCIAS_CAT.get('id')
        self.LISTA_INCIDENCIAS_CAT_OBJ_ID = self.LISTA_INCIDENCIAS_CAT.get('obj_id')

        self.CATEGORIAS_INCIDENCIAS = self.lkm.catalog_id('categora_incidentes')
        self.CATEGORIAS_INCIDENCIAS_ID = self.CATEGORIAS_INCIDENCIAS.get('id')
        self.CATEGORIAS_INCIDENCIAS_OBJ_ID = self.CATEGORIAS_INCIDENCIAS.get('obj_id')
    
        self.CATALOGO_FORMAS = self.lkm.catalog_id('catalogo_de_formas')
        self.CATALOGO_FORMAS_CAT_ID = self.CATALOGO_FORMAS.get('id')
        self.CATALOGO_FORMAS_OBJ_ID = self.CATALOGO_FORMAS.get('obj_id')

        self.SUB_CATEGORIAS_INCIDENCIAS = self.lkm.catalog_id('subcategoras_incidentes')
        self.SUB_CATEGORIAS_INCIDENCIAS_ID = self.SUB_CATEGORIAS_INCIDENCIAS.get('id')
        self.SUB_CATEGORIAS_INCIDENCIAS_OBJ_ID = self.SUB_CATEGORIAS_INCIDENCIAS.get('obj_id')

        self.LISTA_FALLAS_CAT = self.lkm.catalog_id('lista_de_fallas')
        self.LISTA_FALLAS_CAT_ID = self.LISTA_FALLAS_CAT.get('id')
        self.LISTA_FALLAS_CAT_OBJ_ID = self.LISTA_FALLAS_CAT.get('obj_id')

        self.GRUPOS_CAT = self.lkm.catalog_id('grupos')
        self.GRUPOS_CAT_ID = self.GRUPOS_CAT.get('id')
        self.GRUPOS_CAT_OBJ_ID = self.GRUPOS_CAT.get('obj_id')

        self.PROVEEDORES_CAT = self.lkm.catalog_id('proveedores')
        self.PROVEEDORES_CAT_ID = self.PROVEEDORES_CAT.get('id')
        self.PROVEEDORES_CAT_OBJ_ID = self.PROVEEDORES_CAT.get('obj_id')

        self.PROVEEDORES_DE_PAQUETERIA_CAT = self.lkm.catalog_id('proveedores_de_paqueteria')
        self.PROVEEDORES_DE_PAQUETERIA_CAT_ID = self.PROVEEDORES_DE_PAQUETERIA_CAT.get('id')
        self.PROVEEDORES_DE_PAQUETERIA_CAT_OBJ_ID = self.PROVEEDORES_DE_PAQUETERIA_CAT.get('obj_id')


        # self.CONF_PERFIL = self.lkm.catalog_id('configuracion_de_perfiles','id')
        # self.CONF_PERFIL_ID = self.CONF_PERFIL.get('id')
        # self.CONF_PERFIL_OBJ_ID = self.CONF_PERFIL.get('obj_id')


        self.TIPO_EQUIPOS_CAT = self.lkm.catalog_id('tipo_de_equipos')
        self.TIPO_EQUIPOS_CAT_ID = self.TIPO_EQUIPOS_CAT.get('id')
        self.TIPO_EQUIPOS_CAT_OBJ_ID = self.TIPO_EQUIPOS_CAT.get('obj_id')

        self.TIPO_VEHICULOS_CAT = self.lkm.catalog_id('tipos_de_vehiculo')
        self.TIPO_VEHICULOS_CAT_ID = self.TIPO_VEHICULOS_CAT.get('id')
        self.TIPO_VEHICULOS_CAT_OBJ_ID = self.TIPO_VEHICULOS_CAT.get('obj_id')

        self.AREAS_DE_LAS_UBICACIONES_CAT = self.lkm.catalog_id('areas_de_las_ubicaciones')
        self.AREAS_DE_LAS_UBICACIONES_CAT_ID = self.AREAS_DE_LAS_UBICACIONES_CAT.get('id')
        self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID = self.AREAS_DE_LAS_UBICACIONES_CAT.get('obj_id')

        self.AREAS_DE_LAS_UBICACIONES_SALIDA = self.lkm.catalog_id('areas_de_las_ubicaciones_salidas')
        self.AREAS_DE_LAS_UBICACIONES_SALIDA_ID = self.AREAS_DE_LAS_UBICACIONES_SALIDA.get('id')
        self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID = self.AREAS_DE_LAS_UBICACIONES_SALIDA.get('obj_id')

        self.MENUS_CATALOG = self.lkm.catalog_id('elementos_menu')
        self.MENUS_CATALOG_ID = self.MENUS_CATALOG.get('id')
        self.MENUS_CATALOG_OBJ_ID = self.MENUS_CATALOG.get('obj_id')

        ### Scripts (usados en module_permits, migrado de menus.py)
        self.ARTICULOS_CONSECIONADOS = self.lkm.script_id('articulos_consecionados','id')
        self.ARTICULOS_PERDIDOS = self.lkm.script_id('articulos_perdidos','id')
        self.FALLAS = self.lkm.script_id('fallas','id')
        self.GET_STATS = self.lkm.script_id('get_stats','id')
        self.GAFETES_LOCKERS = self.lkm.script_id('gafetes_lockers','id')
        self.NOTAS = self.lkm.script_id('notes','id')
        # Nombre distinto de self.PAQUETERIA (que ya es el form_id de paqueteria) para no pisarlo.
        self.SCRIPT_PAQUETERIA = self.lkm.script_id('paqueteria','id')
        self.SCRIPT_TURNOS = self.lkm.script_id('script_turnos','id')
        self.SCRIPT_PASE_ACCESO = self.lkm.script_id('pase_de_acceso','id')
        self.SCRIPT_PASE_ACCESO_API = self.lkm.script_id('pase_de_acceso_use_api','id')
        self.SCRIPT_GOOGLE_WALLET = self.lkm.script_id('create_pass_google_wallet','id')
        self.SCRIPT_RONDINES = self.lkm.script_id('rondines','id')
        self.OFFLINE_SERVICES = self.lkm.script_id('offline_services','id')
        self.OCR_DOCS = self.lkm.script_id('ocr_docs','id')
        self.SCRIPT_MENUS = self.lkm.script_id('menus','id')
        self.FILTERS = self.lkm.script_id('filters','id')
        self.SCRIPT_INCIDENCIAS = self.lkm.script_id('incidencias','id')

        self.module_permits = {
            'always':{
                'forms':[],
                'catalogs':[
                    self.ACTIVOS_FIJOS_CAT_ID,
                    self.AREAS_DE_LAS_UBICACIONES_CAT_ID,
                    self.CATEGORIAS_INCIDENCIAS_ID,
                    self.CONFIGURACION_RECORRIDOS_ID,
                    self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_ID,
                    self.Employee.CONF_AREA_EMPLEADOS_CAT_ID,
                    self.ESTADO_ID,
                    self.LISTA_FALLAS_CAT_ID,
                    self.LISTA_INCIDENCIAS_CAT_ID,
                    self.LOCKERS_CAT_ID,
                    self.PASE_ENTRADA_ID,
                    self.PROVEEDORES_CAT_ID,
                    self.SUB_CATEGORIAS_INCIDENCIAS_ID,
                    self.TIPO_ARTICULOS_PERDIDOS_CAT_ID,
                    self.AF.TIPO_DE_EQUIPO_ID,
                    self.Location.UBICACIONES_CAT_ID,
                    self.USUARIOS_ID,
                    self.VISITA_AUTORIZADA_CAT_ID,
                    self.MENUS_CATALOG_ID,
                    self.OCR_DOCS
                    ],
                'scripts':[self.OFFLINE_SERVICES, self.SCRIPT_MENUS, self.FILTERS]
            },
            'accesos':{
                'forms':[self.CHECKIN_CASETAS, self.REGISTRO_ASISTENCIA, self.BITACORA_GAFETES_LOCKERS, self.CHECK_UBICACIONES, self.BITACORA_ACCESOS],
                'catalogs':[],
                'scripts':[]
            },
            'seguridad':{
                'forms':[self.CONFIGURACION_RECORRIDOS_FORM, self.BITACORA_RONDINES, self.BITACORA_FALLAS, self.BITACORA_INCIDENCIAS],
                'catalogs':[],
                'scripts':[self.SCRIPT_RONDINES, self.FALLAS, self.SCRIPT_INCIDENCIAS]
            },
            'activos':{
                'forms':[self.CONCESSIONED_ARTICULOS, self.BITACORA_OBJETOS_PERDIDOS],
                'catalogs':[self.ACTIVOS_FIJOS_CAT_ID, ],
                'scripts':[self.SCRIPT_PAQUETERIA, self.GET_STATS, self.GAFETES_LOCKERS, self.FALLAS, self.ARTICULOS_PERDIDOS, self.ARTICULOS_CONSECIONADOS]
            },
            'notas':{
                'forms':[self.ACCESOS_NOTAS],
                'catalogs':[],
                'scripts':[self.NOTAS]
            },
            'pases_de_entrada':{
                'forms':[self.PASE_ENTRADA],
                'catalogs':[],
                'scripts':[self.SCRIPT_PASE_ACCESO, self.GET_STATS, self.SCRIPT_PASE_ACCESO_API]
            },
            'caseta':{
                'forms':[self.CHECKIN_CASETAS, self.REGISTRO_ASISTENCIA, self.FORMATO_VACACIONES],
                'catalogs':[],
                'scripts':[self.SCRIPT_TURNOS]
            },
        }

        ### Permisos legacy (migrado de config_access.py). Esquema de permisos
        ### distinto y mas antiguo que self.module_permits (usado por menus.py),
        ### se conserva separado para no romper cuentas que aun dependan de el.
        self.config_access_module_permits = {
            'always':{
                'forms':[],
                'catalogs':[
                    self.ACTIVOS_FIJOS_CAT_ID,
                    self.AREAS_DE_LAS_UBICACIONES_CAT_ID,
                    self.CATEGORIAS_INCIDENCIAS_ID,
                    self.CONFIGURACION_RECORRIDOS_ID,
                    self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_ID,
                    self.Employee.CONF_AREA_EMPLEADOS_CAT_ID,
                    self.ESTADO_ID,
                    self.LISTA_FALLAS_CAT_ID,
                    self.LISTA_INCIDENCIAS_CAT_ID,
                    self.LOCKERS_CAT_ID,
                    self.PASE_ENTRADA_ID,
                    self.PROVEEDORES_CAT_ID,
                    self.SUB_CATEGORIAS_INCIDENCIAS_ID,
                    self.TIPO_ARTICULOS_PERDIDOS_CAT_ID,
                    self.AF.TIPO_DE_EQUIPO_ID,
                    self.Location.UBICACIONES_CAT_ID,
                    self.USUARIOS_ID,
                    self.VISITA_AUTORIZADA_CAT_ID,
                    self.FILTERS
                ],
                'scripts':[self.OFFLINE_SERVICES]
            },
            'bitacoras':{
                'forms':[self.BITACORA_ACCESOS],
                'catalogs':[],
                'scripts':[]
            },
            'accesos':{
                'forms':[self.CHECKIN_CASETAS, self.REGISTRO_ASISTENCIA, self.BITACORA_GAFETES_LOCKERS, self.CHECK_UBICACIONES],
                'catalogs':[],
                'scripts':[]
            },
            'rondines':{
                'forms':[self.CONFIGURACION_RECORRIDOS_FORM, self.BITACORA_RONDINES],
                'catalogs':[],
                'scripts':[self.SCRIPT_RONDINES]
            },
            'articulos':{
                'forms':[self.CONCESSIONED_ARTICULOS, self.BITACORA_OBJETOS_PERDIDOS, self.PAQUETERIA],
                'catalogs':[self.ACTIVOS_FIJOS_CAT_ID, ],
                'scripts':[self.SCRIPT_PAQUETERIA, self.GET_STATS, self.GAFETES_LOCKERS, self.FALLAS, self.ARTICULOS_PERDIDOS, self.ARTICULOS_CONSECIONADOS]
            },
            'incidencias':{
                'forms':[self.BITACORA_FALLAS, self.BITACORA_INCIDENCIAS],
                'catalogs':[],
                'scripts':[self.FALLAS]
            },
            'notas':{
                'forms':[self.ACCESOS_NOTAS],
                'catalogs':[],
                'scripts':[self.NOTAS]
            },
            'pases':{
                'forms':[self.PASE_ENTRADA],
                'catalogs':[],
                'scripts':[self.SCRIPT_PASE_ACCESO, self.GET_STATS, self.SCRIPT_PASE_ACCESO_API]
            },
            'turnos':{
                'forms':[self.CHECKIN_CASETAS, self.REGISTRO_ASISTENCIA, self.FORMATO_VACACIONES, self.SCRIPT_TURNOS],
                'catalogs':[],
                'scripts':[]
            },
        }

        self.menu_form_fields = {
            "username": "6759e4a7a9a6e13c7b26da33",
            "usuario_id": "638a9a99616398d2e392a9f5",
            "grupo_asignado": "638a9ab3616398d2e392a9fa",
            "grupo_id": "639b65dfaf316bacfc551ba2",
            "elementos": "69efaf4c4a59aa2591074f45",
            "menu": "69efaf883bcb25ed1458465d",
            "seccion": "69efaf883bcb25ed1458465e",
            "elemento": "69efaf883bcb25ed1458465f",
            "key": "69efb57c4a59aa2591074f4e",
            "plataforms": "69f27e8cdf4d7acc80f2e9b0"
        }

        self.menu_catalog_fields = {
            "catalog_menu_key": "69f28216c76fd3bed14949a2",
            "catalog_menu": "69efaf883bcb25ed1458465d",
            "catalog_menu_order": "69f27e8cdf4d7acc80f2e9a8",
            "catalog_menu_icon": "69f27e8cdf4d7acc80f2e9a9",
            "catalog_menu_columns": "69f27e8cdf4d7acc80f2e9aa",
            "catalog_seccion_key": "69f28216c76fd3bed14949a3",
            "catalog_seccion": "69efaf883bcb25ed1458465e",
            "catalog_seccion_order": "69f27e8cdf4d7acc80f2e9ab",
            "catalog_seccion_column": "69f27e8cdf4d7acc80f2e9ac",
            "catalog_seccion_href": "6a036ef020c6e62e1c3fdee6",
            "catalog_seccion_icon": "69f27e8cdf4d7acc80f2e9ad",
            "catalog_seccion_icon_color": "69f27e8cdf4d7acc80f2e9ae",
            "catalog_elemento": "69efaf883bcb25ed1458465f",
            "catalog_key": "69efb57c4a59aa2591074f4e",
            "catalog_type": "69efb3dcfc8545da78179bf9",
            "catalog_item_order": "69efb3dcfc8545da78179bfa",
            "catalog_href_web": "69efb3dcfc8545da78179bf8",
            "catalog_route_mobile": "69f27e8cdf4d7acc80f2e9af",
            "catalog_plataforms": "69f27e8cdf4d7acc80f2e9b0"
        }

        #----Dic Fields Forms

        ### Lista de catalogos requeridos para el uso offline de la aplicacion.
        self.clave10_catalogs = [
            self.LISTA_INCIDENCIAS_CAT_ID,
            self.SUB_CATEGORIAS_INCIDENCIAS_ID,
            self.CATEGORIAS_INCIDENCIAS_ID,
            self.AREAS_DE_LAS_UBICACIONES_CAT_ID,
            self.Location.UBICACIONES_CAT_ID,
            self.CONFIGURACION_RECORRIDOS_ID,
            self.USUARIOS_ID,
            self.Employee.CONF_AREA_EMPLEADOS_CAT_ID,
            self.TIPO_EQUIPOS_CAT_ID,
            self.TIPO_VEHICULOS_CAT_ID,
            self.LISTA_FALLAS_CAT_ID,
            self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_ID,
            self.VISITA_AUTORIZADA_CAT_ID,
            self.ESTADO_ID,
            self.PROVEEDORES_CAT_ID,
            self.LOCKERS_CAT_ID,
            self.TIPO_ARTICULOS_PERDIDOS_CAT_ID,
            self.PASE_ENTRADA_ID,
            self.ACTIVOS_FIJOS_CAT_ID,
        ]



        self.f.update(self.Employee.f)
        self.f.update(self.Location.f)
        self.f.update(self.AF.f)
        # self.CONF_PERFIL = self.lkm.catalog_id('configuracion_de_perfiles','id')
        # self.CONF_PERFIL_ID = self.CONF_PERFIL.get('id')
        # self.CONF_PERFIL_OBJ_ID = self.CONF_PERFIL.get('obj_id')


        # self.AREAS_DE_LAS_UBICACIONES_CAT = self.lkm.catalog_id('areas_de_las_ubicaciones')
        # self.AREAS_DE_LAS_UBICACIONES_CAT_ID = self.AREAS_DE_LAS_UBICACIONES_CAT.get('id')
        # self.Location.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID = self.AREAS_DE_LAS_UBICACIONES_CAT.get('obj_id')
        #----Dic Fields Forms

        ## Module Fields ##
        '''
        self.mf : Estos son los campos que deseas mantener solo dentro de este modulo.
        Asegúrese de utilizar `llave` y el `id` del campo ej.
        'nombre_campo': "1f2h3j4j5d6f7h8j9j1a",
        '''

        mf = {
            'acepto_aviso_datos_personales': '6827488724317731cb288117',
            'acepto_aviso_privacidad': '6825268e0663cce4b1bf0a17',
            'archivo_invitacion': '673773741b2adb2d05d99d63',
            'areas_grupo':'663cf9d77500019d1359eb9f',
            'articulo':'66ce2441d63bb7a3871adeaf',
            #LOS CATALOGOS NO SE CCLASIFICAN COMO CAMPOS
            'catalog_area_pase':'664fc5f3bbbef12ae61b15e9',
            'catalog_caseta':'66566d60d4619218b880cf04',
            'catalog_caseta_salida':'66566d60464fe63529d1c543',
            'catalog_estado':'664fc5b3276795e17ea76dbd',
            'catalog_guard':'664fc645276795e17ea76dc4',
            'catalog_guard_close':'664fc64242c59486fadd0a27',
            'catalog_tipo_pase':'664fc6e81d1a1fcda334b587',
            'catalog_ubicacion':'664fc5d9860deae4c20954e2',
            'catalog_visita':'664fc6f5d6078682a4dd0ab3',
            "catalogo_departamentos": "66a83a7fca3453e21ea08d16",
            'catalogo_persona_involucrada': '66ec6936fc1f0f3f111d818f',
            "catalogo_puestos": "66a83a7dee0b950748489ca1",
            "catalogo_ubicaciones": "66a83a77cfed7f342775c161",
            'codigo_qr':'6685da34f065523d8d09052b',
            'color_articulo': '663e4730724f688b3059eb3b',
            'color_vehiculo': '663e4691f54d395ed7f27465',
            'comentario_pase':'65e0a69a322b61fbf9ed23af',
            'commentario_area': '66af1a77d703592958dca5eb',
            'config_dia_de_acceso': '662c304fad7432d296d92584',
            'config_dias_acceso': '662c304fad7432d296d92585',
            'config_limitar_acceso': '6635380dc9b3e7db4d59eb49',
            'conservar_datos_por': '6827488724317731cb288118',
            'curp': '5ea0897550b8dfe1f4d83a9f',
            'departamento_empleado': '663bc4ed8a6b120eab4d7f1e',
            'dias_acceso_pase':'662c304fad7432d296d92585',
            'direccion': '663a7e0fe48382c5b1230902',
            'direccion_visita': '67466b79bd2dc53e9864ad62',
            'documento': '663e5470424ad55e32832eec',
            'documento_certificado': '66427511e93cc23f04f27467',
            'duracion': '65cbe03c6c78b071a59f481e',
            'email_empleado': '6653f3709c6d89925dc04b2f',
            'email_pase':'662c2937108836dec6d92581',
            'email_visita_a': '638a9a7767c332f5d459fc82',
            'email_vista': '5ea069562f8250acf7d83aca',
            'empresa':'65fc814fb170488cf4d44c51',
            'empresa_pase':'66357d5e4f00f9018ce97ce9',
            'estatus_del_recorrido': '6639b2744bb44059fc59eb62',
            'examen_certificado':'66297e1579900d9018c886ad',
            'fecha_cetrificado_caducidad': '66427511e93cc23f04f2746a',
            'fecha_cetrificado_expedicion': '66427511e93cc23f04f27469',
            'fecha_desde_hasta': '662c304fad7432d296d92583',
            'fecha_desde_visita': '662c304fad7432d296d92582',
            'fecha_entrada':'662c51eb194f1cb7a91e5aef',
            'fecha_hasta_pase':'662c304fad7432d296d92583',
            ##### REVISAR Y BORRAR ######
            'fecha_salida':'662c51eb194f1cb7a91e5af0',
            'field_note':'6647fadc96f80017ac388648',
            'foto':'5ea35de83ab7dad56c66e045',
            'foto_equipo':'698ca59f8797d7e10e57617d',
            'foto_vehiculo':'698ca60575c268aadf768c57',
            'grupo_areas_acceso':'663fed6cb8262fd454326cb3',
            'grupo_equipos':'663e446cadf967542759ebbb',
            'grupo_instrucciones_pase':'65e0a68a06799422eded24aa',
            "grupo_puestos": "663c015f3ac46d98e8f27495",
            'grupo_ubicaciones_pase':'6834e34fa6242006acedda0f',
            'grupo_vehiculos': '663e446cadf967542759ebba',
            'grupo_visitados': '663d4ba61b14fab90559ebb0',
            'guard_group':'663fae53fa005c70de59eb95',
            'id_grupo':'639b65dfaf316bacfc551ba2',
            'id_usuario':'638a9a99616398d2e392a9f5',
            'identificacion':'65ce34985fa9df3dbf9dd2d0',
            'locker_id':'66480101786e8cdb66e70124',
            'marca_articulo':'663e4730724f688b3059eb3a',
            'marca_vehiculo':'65f22098d1dc5e0b9529e89b',
            'modelo_articulo':'66b29872aa6b3e6c3c02baa6',
            'modelo_vehiculo':'65f22098d1dc5e0b9529e89c',
            'motivo':'66ad58a3a5515ee3174f2bb5',
            'nombre_area':'663e5d44f5b8a7ce8211ed0f',
            'nombre_area_salida':'663fb45992f2c5afcfe97ca8',
            'nombre_articulo': '663e4730724f688b3059eb39',
            'nombre_del_recorrido': '6645050d873fc2d733961eba',
            'nombre_empleado': '62c5ff407febce07043024dd',
            'nombre_estado': '663a7dd6e48382c5b12308ff',
            'nombre_grupo':'638a9ab3616398d2e392a9fa',
            'nombre_guardia_apoyo': '663bd36eb19b7fb7d9e97ccb',
            'nombre_pase':'662c2937108836dec6d92580',
            'nombre_perfil': '661dc67e901906b7e9b73bac',
            'nombre_permiso':'662962bb203407ab90c886e4',
            'nombre_ubicacion_salida': '663e5c57f5b8a7ce8211ed0b',
            'nombre_usuario':'638a9a7767c332f5d459fc81',
            'nombre_visita': '5ea0693a0c12d5a8e43d37df',
            'nota': '6647fadc96f80017ac388647',
            'nss': '67466b79bd2dc53e9864ad63',
            'numero_serie': '66426453f076652427832fd2',
            'placas_vehiculo':'663e4691f54d395ed7f27464',
            'puesto_empleado': '663bc4c79b8046ce89e97cf4',
            'qr_pase':'64ef5b5fff1bec97d2ca27b6',
            'requerimientos':'662962bb203407ab90c886e5',
            'rfc':'64ecc95271803179d68ee081',
            'status_area':'663e5e4bf5b8a7ce8211ed14',
            'status_cetrificado':'664275469d8fffff0a59eb30',
            'status_doc_cetrificado':'664275e32c12468d16cb97dc',
            'status_gafete':'663e530af52d352956832f72',
            'status_locker':'663961d5390b9ec511e97ca5',
            'status_visita':'5ea1bd280ae8bad095055e61',
            'telefono':'661ea59c15baf5666f32360e',
            'telefono_pase':'662c2937108836dec6d92582',
            'telefono_visita': '663ec042713049de31e97c93',
            'telefono_visita_a': '67be0c43a31e5161c47f2bba',
            'tipo_de_articulo_perdido':'66ce23efc5c4d148311adf86',
            'tipo_de_comentario':'66af1977ffb6fd75e769f457',
            'tipo_de_guardia': '6684484fa5fd62946c12e006',
            'tipo_equipo': '663e4730724f688b3059eb38',
            'tipo_locker': '66ccfec6acaa16b31e5593a3',
            'tipo_registro': '66358a5e50e5c61267832f90',
            #'tipo_equipo':'6639a9d9d38959539f59eb9f',
            'tipo_vehiculo': '65f22098d1dc5e0b9529e89a',
            'tipo_visita_pase': '662c304fad7432d296d92581',
            'ubicacion': '663e5c57f5b8a7ce8211ed0b',
            'user_id_empleado': '663bd32d7fb8869bbc4d7f7b',
            'username': '6759e4a7a9a6e13c7b26da33',
            'vigencia_certificado':'662962bb203407ab90c886e6',
            'vigencia_certificado_en':'662962bb203407ab90c886e7',
            'walkin':'66c4261351cc14058b020d48',
            'grupo_asignado_a':'6a309d27b3f21fceb68eeb01',
            'nombre_forma': '5d810a982628de5556500d55'
        }
        self.mf = mf
        ## Form Fields ##
        '''
        `self.form_name`: En esta sección podrás agrupar todos los campos ya sea por forma o como desees enviarlos hacia tus servicios.
        En el caso de las búsquedas de Mongo, puedes hacer las búsquedas de manera anidada. Por lo cual podrás agrupar separadas por punto,
        ej. 663d4ba61b14fab90559ebb0.665f482cc9a2f8acf685c20b y así podrás hacer las búsquedas directo en la base de datos.

        Estos campos podrás agregarlos directamente a `self.f`, donde se agrupan todos los `fields` de los módulos heredados.
        '''
        #- Para salida de bitacora  de articulos perdidos y lista
        self.perdidos_fields = {
            'area_catalog':f"{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}",
            'area_perdido':f"{self.mf['nombre_area_salida']}",
            'articulo_perdido':'6639aeeb97b12e6f4ccb9711',
            'articulo_seleccion': f"{self.mf['articulo']}",
            'articulo_seleccion_catalog':f"{self.TIPO_ARTICULOS_PERDIDOS_CAT_OBJ_ID}",
            'color_perdido':'66ce223e174f3f39c0020d65',
            'comentario_perdido':'6639affa5a9f58f5b5cb9706',
            'date_entrega_perdido':'6639affa5a9f58f5b5cb9708',
            'date_hallazgo_perdido':'6639ae65356a6efb4de97d29',
            'descripcion':'66ce2397c5c4d148311adf83',
            'estatus_perdido':'6639ae65356a6efb4de97d28',
            'foto_perdido':'6639aeeb97b12e6f4ccb9712',
            'foto_recibe_perdido':'66ce2675293aabefa3559486',
            'identificacion_recibe_perdido':'664415ce630b1fb22b07e15a',
            'locker_catalog':f"{self.LOCKERS_CAT_OBJ_ID}",
            'locker_perdido':f"{self.mf['locker_id']}",
            'quien_entrega':'66ce2646033c793281b2c414',
            'quien_entrega_catalog':f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}",
            #'quien_entrega_interno':f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_name']}",
            'quien_entrega_externo':'66ce2647033c793281b2c415',
            'quien_entrega_interno':f"{self.f['worker_name']}",
            'recibe_perdido':'6639affa5a9f58f5b5cb9707',
            'telefono_recibe_perdido':'664415ce630b1fb22b07e159',
            'tipo_articulo_catalog':f"{self.TIPO_ARTICULOS_PERDIDOS_CAT_OBJ_ID}",
            'tipo_articulo_perdido':f"{self.mf['tipo_de_articulo_perdido']}",
            'ubicacion_catalog':f"{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}",
            'ubicacion_perdido':f"{self.mf['ubicacion']}",
            "nombre_articulo_perdido":"66ce2441d63bb7a3871adeaf"
        }

        #- Para salida de bitacora y lista
        self.bitacora_fields = {
            'caseta_entrada':f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}",
            'caseta_salida':f"{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.mf['nombre_area_salida']}",
            "catalogo_pase_entrada": "66a83ad652d2643c97489d31",
            'codigo_qr':f"{self.mf['codigo_qr']}",
            'comentario':"66ba83cc079d8a54634711c1",
            'documento':f"{self.mf['documento']}",
            'email_empleado': f"{self.mf['email_empleado']}",
            'fecha_entrada':f"{self.mf['fecha_entrada']}",
            'fecha_salida':f"{self.mf['fecha_salida']}",
            "gafete_catalog": "66a83ace56d1e741159ce114",
            'grupo_comentario':"66ba83942fef3a4613a07e91",
            'nombre_area_salida':f"{self.mf['catalog_caseta_salida']}.{self.mf['nombre_area_salida']}",
            'nombre_visita':f"{self.mf['catalog_visita']}.{self.mf['nombre_visita']}",
            "pase_entrada": f"{self.PASE_ENTRADA_OBJ_ID}",
            'perfil_visita':f"{self.mf['catalog_visita']}.{self.mf['nombre_perfil']}",
            'puesto_empleado': f"{self.mf['puesto_empleado']}",
            'status_gafete':f"{self.mf['status_gafete']}",
            'status_visita':f"{self.mf['tipo_registro']}",
            'tipo_comentario':"66ba83cc079d8a54634711c2",
            'ubicacion':f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
            'visita':f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}",
            'visita_a':"663d4ba61b14fab90559ebb0",
            'visita_departamento_empleado': f"{self.mf['departamento_empleado']}",
            'visita_nombre_empleado': f"{self.mf['nombre_empleado']}",
            'visita_user_id_empleado':f"{self.mf['user_id_empleado']}",
        }

        self.checkin_fields = {
            'boot_checkin_date':'663bffc28d00553254f274e1',
            'boot_checkout_date':'663bffc28d00553254f274e2',
            'cat_area': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['area']}",
            'cat_created_by': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_name']}",
            'cat_employee_b': f"{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['worker_name_b']}",
            'cat_location': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['location']}",
            'checkin_date':'66a28f3ca6b0f085b1518caa',
            'checkin_image': '685ac4e836c1c936b97275ad',
            'checkin_position':'66a28f3ca6b0f085b1518ca9',
            'checkin_status':'66a28f3ca6b0f085b1518ca8',
            'checkin_type': '663bffc28d00553254f274e0',
            'checkout_date':'66a28f3ca6b0f085b1518cab',
            'commentario_checkin_caseta':'66a5b9bed0c44910177eb724',
            'created_by': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_name']}",
            'employee': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_name']}",
            'employee_position':'665f482cc9a2f8acf685c20b',
            'forzar_cierre':'66a5b9bed0c44910177eb723',
            'fotografia_cierre_turno':'68d384ef55840a75f2cb7e29',
            'fotografia_inicio_turno':'68d384ef55840a75f2cb7e28',
            'guard_group': mf['guard_group'],
            'nombre_suplente':'6927a1176c60848998a157a2'
        }
        self.configuracion_area = {
            'area': '663e5d44f5b8a7ce8211ed0f',
            'create_area': '688a33d9e61fcd2c299ff39e',
            'comentarios': '68504a3fd3ebdc2e9b9869d2',
            'foto_area': '68487646684fe30a8f9f3ef4',
            'nombre_nueva_area': '688a33d9e61fcd2c299ff39f',
            'option': '68487646684fe30a8f9f3ef2',
            'status': '689a46342038ded0e949be07',
            'status_comment': '689a46342038ded0e949be08',
            'qr_area': '68487646684fe30a8f9f3ef3',
            'tag_id': '68487646684fe30a8f9f3ef3',
            'ubicacion': '663e5c57f5b8a7ce8211ed0b',
        }

        #- Para salida de bitacora  de articulos consecionados y lista
        self.cons_f = {
            'area_catalog_concesion': f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}",
            'area_concesion': f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.663e5d44f5b8a7ce8211ed0f",
            '_area_concesion': "663e5d44f5b8a7ce8211ed0f",
            'cantidad_devolucion': '699fec1e0f178e858bbf1b92',
            'cantidad_equipo_concesion': '69799523aa75e6a4c99c4d3f',
            'cantidad_equipo_devuelto': '6979962e6eac7e391dbb244e',
            'cantidad_equipo_pendiente': '699fe2e679aaab897b504c65',
            'caseta_concesion':  f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.663e5d44f5b8a7ce8211ed0f",
            '_caseta_concesion':  "663e5d44f5b8a7ce8211ed0f",
            'categoria_equipo_concesion':  f"{self.ACTIVOS_FIJOS_CAT_OBJ_ID}.66ce23efc5c4d148311adf86",
            '_categoria_equipo_concesion': '66ce23efc5c4d148311adf86',
            'comentario_entrega': '69799523aa75e6a4c99c4d41',
            'costo_equipo_concesion': f"{self.ACTIVOS_FIJOS_CAT_OBJ_ID}.697991fffd83f49bb9fe074e",
            '_costo_equipo_concesion': "697991fffd83f49bb9fe074e",
            'entregado_por': '6979962e6eac7e391dbb2450',
            'equipo_catalog_concesion': f"{self.ACTIVOS_FIJOS_CAT_OBJ_ID}",
            'equipo_imagen_concesion': '6646393c3fa8b818265d0326',
            'estatus_equipo': '6979962e6eac7e391dbb244f',
            'evidencia': '6970914a3059168605ce10c8',
            'evidencia_devolucion': '6979962e6eac7e391dbb2444',
            'evidencia_entrega': '6979962e6eac7e391dbb2453',
            'fecha_cierre_concesion': '66469f47c0580e5ead07e39b',
            'fecha_concesion': '66469ef8c9d58517f85d035f',
            'fecha_devolucion_concesion': '699fed207a15d39b937d805c',
            'firma': '6979b0b4a2a5a141dfef9cc5',
            'grupo_equipos': '697991cb4298cbe60db6b883',
            'grupo_equipos_devolucion': '699fe58a0f178e858bbf1b91',
            'id_movimiento':'697b055eb9a8d97bb5614ee0',
            'id_movimiento_devolucion':'699fe63679aaab897b504c71',
            'identificacion_entrega': '6979962e6eac7e391dbb2452',
            'imagen_equipo_concesion': f"{self.ACTIVOS_FIJOS_CAT_OBJ_ID}.6646393c3fa8b818265d0326",
            '_imagen_equipo_concesion': "6646393c3fa8b818265d0326",
            'marca_equipo_concesion': '65f22098d1dc5e0b9529e89b',
            'nombre_equipo': f"{self.ACTIVOS_FIJOS_CAT_OBJ_ID}.66c192ef89463aa27fc1818b",
            '_nombre_equipo': "66c192ef89463aa27fc1818b",
            'observacion_concesion': '66469f47c0580e5ead07e39a',
            'persona_catalog_concesion': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}",
            'persona_email_concesion': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['email_visita_a']}",
            '_persona_email_concesion': self.mf['email_visita_a'],
            'persona_email_otro': '697991ad1cfb3b3210269901',
            'persona_id_concesion': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['id_usuario']}",
            '_persona_id_concesion': self.mf['id_usuario'],
            'persona_identificacion_otro': '697991ad1cfb3b3210269902',
            'persona_nombre_concesion': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.mf['nombre_empleado']}",
            '_persona_nombre_concesion': self.mf['nombre_empleado'],
            'persona_nombre_otro': '696fd2291527668d067cdb85',
            'quien_entrega': '6979962e6eac7e391dbb2451',
            'quien_entrega_company': '699feaa2a0e52f55fd5589a5',
            'status_concesion': '66469e193e6a703350f2e029',
            'status_concesion_equipo': '66469e193e6a703350f2e299',
            'subotal_concesion_equipo': '69799523aa75e6a4c99c4d40',
            'tipo_persona_solicita': '66469e5a3e6a703350f2e03a',
            'ubicacion_catalog_concesion': f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}",
            'ubicacion_concesion': f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
            '_ubicacion_concesion': self.mf['ubicacion'],
        }

        self.status_equipo_dict = {
            'complete':'completo',
            'damage':'dañado',
            'lost':'perdido',
        }
        #- Para creación , edición y lista de fallas
        self.fallas_fields = {
            'falla':'66397bae9e8b08289a59ec86',
            'falla_accion_realizada': '66f2dfb2c80d24e5e82332b3',
            'falla_caseta':f"{self.mf['nombre_area']}",
            'falla_catalog': f"{self.LISTA_FALLAS_CAT_OBJ_ID}",
            'falla_comentario_solucion':'66f2dfb2c80d24e5e82332b3',
            'falla_comentarios':'66397d8cfd99d7263f83303a',
            'falla_documento':'66f2df6b6917fe63f4233227',
            'falla_documento_solucion':'66f2dfb2c80d24e5e82332b6',
            'falla_estatus': '66397e2c59c2600b1df2742c',
            'falla_evidencia':'66f2df6b6917fe63f4233226',
            'falla_evidencia_solucion':'66f2dfb2c80d24e5e82332b5',
            'falla_fecha_hora': '66397d0cfd99d7263f833032',
            'falla_fecha_seguimiento':'679a485c66c5d089fa6b8ef9',
            'falla_folio_accion_correctiva':'66f2dfb2c80d24e5e82332b4',
            #Seguimientos
            'falla_grupo_seguimiento': '6799125d9f8d78842caa22af',
            'falla_objeto_afectado':'66ce2441d63bb7a3871adeaf',
            'falla_personas_involucradas':'66f2dfb2c80d24e5e82332b4',
            'falla_reporta_catalog':f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}",
            'falla_reporta_departamento': '663bc4ed8a6b120eab4d7f1e',
            'falla_reporta_nombre': '62c5ff407febce07043024dd',
            'falla_responsable_solucionar_catalog': f"{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}",
            'falla_responsable_solucionar_documento':'663bc4ed8a6b120eab4d7f1e',
            'falla_responsable_solucionar_nombre':'663bd36eb19b7fb7d9e97ccb',
            'falla_subconcepto': '679124a8483c5220455bcb99',
            'falla_tiempo_transcurrido':'68a667d24ac4254634d87f3e',
            'falla_ubicacion': f"{self.mf['ubicacion']}",
            'falla_ubicacion_catalog':f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}",
        }

        #- Para creación , edición y lista de incidencias
        self.incidence_fields = {
            #Campos en grupo repetitivo Seguimiento:
            'accion_correctiva_incidencia':'683de45ddcf6fcee78e61ed7',
            'acciones_tomadas':'66ec69a914bf1142b6a024e3',
            #Campos en grupo repetitivo acciones tomadas:
            # 'acciones_tomadas_incidencia':'66ec6987f251a9c2cef0126f',
            'acciones_tomadas_incidencia':'688bbd509b98fd9afaf2c401',
            'afectacion_patrimonial_incidencia':'688a9cbda7b2dd2b599ff381',
            'area_incidencia': '663e5d44f5b8a7ce8211ed0f',
            'area_incidencia_catalog': f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}",
            'area_incidencia_ver2':f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}",
            'atencion_medica':'688a9b96ccfd13dc0c12b189',
            'autoridad': '688bc5ef1037e90c4ccd4eb3',
            'cantidad':'66ec67e42bcc75c3a458778e',
            'categoria':'686807d46e41614d708f6fc9',
            'color': '684c3eaa04aaab135d7dfbb6',
            'color_cabello': '684c3e026d974f9625e11306',
            'color_piel':'684c3e026d974f9625e11305',
            'comentario_incidencia': '66397586aa8bbc0371e97c80',
            'comentarios':'688bfecfa1b4ecf477a6010a',
            'dano_incidencia':'66ec69144a27bb6151a0255a',
            'datos_deposito_incidencia':'66ec6793eb386ff970218f1f',
            'descripcion_afectacion':'688a9d52c1ce871f545b3b9d',
            'descripcion_fisica_vestimenta': '684c3e026d974f9625e11308',
            'documento':'68c305c624e99970e536dc45',
            'documento_incidencia':'66ec6846028e5550cbf012e1',
            'duracion_estimada': '688a9d52c1ce871f545b3b9c',
            'edad':'684c3e026d974f9625e11304',
            'estatura_aproximada': '684c3e026d974f9625e11307',
            'estatus': '68c04a6b213e28722aec0610',
            'estatus_afectacion':'68d4bba7c6e9e28b9e30e133',
            'evidencia':'68c305c624e99970e536dc44',
            'evidencia_incidencia':'66ec6846028e5550cbf012e0',
            'fecha_hora_incidencia': '66396efeb37283c921e97cdf',
            'fecha_inicio_seg':'683de45ddcf6fcee78e61ed9',
            'grupo_etario':'688a9b96ccfd13dc0c12b188',
            'incidencia': '663973809fa65cafa759eb97',
            'incidencia_catalog': f"{self.LISTA_INCIDENCIAS_CAT_OBJ_ID}",
            'incidencia_documento_solucion':'683de45ddcf6fcee78e61edc',
            'incidencia_evidencia_solucion':'683de45ddcf6fcee78e61edb',
            'incidencia_personas_involucradas':'684c3e026d974f9625e1130f',
            'info_coincide_con_videos': '684c3e026d974f9625e1130d',
            'llamo_a_policia': '688bbddbd40db062d071862f',
            'marca': '684c3eaa04aaab135d7dfbb4',
            'modelo': '684c3eaa04aaab135d7dfbb5',
            'monto_estimado': '688a9d52c1ce871f545b3b99',
            #Campos en grupo repetitivo personas involucradas:
            'nombre_completo': '66ec69239938c882f8222036',
            #Persona extraviada
            'nombre_completo_persona_extraviada':'684c3e026d974f9625e11303',
            'nombre_completo_responsable': '684c3e026d974f9625e11309',
            'notificacion_incidencia':'66ec6ae6c17763d760218e5e',
            'num_doc_identidad': '684c3e026d974f9625e1130b',
            'numero_folio_referencia': '688bc5ef1037e90c4ccd4eb4',
            'origen': '689e391c7ce783d3860f3f0e',
            'parentesco': '684c3e026d974f9625e1130a',
            'personas_involucradas_incidencia':'66ec69144a27bb6151a0255b',
            #Grupos Repetitivos
            'pertenencias_sustraidas': '684c3e6821796d7880117f23',
            #Robo de vehiculo
            'placas': '684c3eaa04aaab135d7dfbb3',
            'prioridad_incidencia':'66ec69144a27bb6151a0255c',
            'puesto':'68d6efb0a209c0144d6c3761',
            'reporta_incidencia': '62c5ff407febce07043024dd',
            'reporta_incidencia_catalog': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}",
            'responsable': '688bbddbd40db062d0718630',
            'responsable_accion':'66ec69a914bf1142b6a024e2',
            'responsable_que_entrega': '688bb6ca2f094c5555b2097b',
            'retenido':'688bc5ef1037e90c4ccd4eb1',
            'rol':'66ec6936fc1f0f3f111d818f',
            'seguimientos_incidencia':'683de3cfcf4a5d248ffbaf89',
            'sexo':'688a9a59244b64c3c374c9e6',
            'sub_categoria': '686807a7ee7705c5c8eb181a',
            'tag':'688abce60cf2954b12f7bbe9',
            'tags':'6834e4e8b0ed467efade7972',
            'telefono': '684c3e026d974f9625e1130c',
            'tiempo_transcurrido': '688d1b7ad3268f1968d5ddf0',
            'tipo': '684c3eaa04aaab135d7dfbb2',
            #Campos en grupo repetitivo afectacion patrimonial:
            'tipo_afectacion': '688a9d52c1ce871f545b3b98',
            'tipo_dano_incidencia': '66ec6962ea3c921534b22c54',
            'tipo_deposito': '66ec67dc608b1faed7b22c45',
            'tipo_incidencia': '66ec667d7646541f2ea024de',
            'tipo_persona': '66ec6936fc1f0f3f111d818f',
            'total_deposito_incidencia':'66ec6821ea3c921534b22c30',
            'ubicacion_incidencia': f"{self.mf['ubicacion']}",
            'ubicacion_incidencia_catalog': f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}",
            #Robo de cableado
            'valor_estimado': '684c3e6821796d7880117f22',
        }

        #- Para creación , edición y lista de gafetes y lockers
        self.gafetes_fields = {
            'caseta_gafete':f"{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}",
            'catalog_gafete':'664fc6ec8d4dfb34de095586',
            'documento_gafete':'65e0b6f7a07a72e587124dc6',
            'gafete_id':'664803e6d79bc1dfd33885e1',
            'ubicacion_gafete':f"{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
            'visita_gafete':f"{self.mf['catalog_visita']}.{self.mf['nombre_visita']}",
        }

        self.lockers_fields = {
            'locker_id':'66480101786e8cdb66e70124',
            'status_locker':"663961d5390b9ec511e97ca5",
            'tipo_locker':'66ccfec6acaa16b31e5593a3',
        }
        #- Para creación , edición y lista de notas
        self.notes_fields = {
            'note':'6647fadc96f80017ac388647',
            'note_booth':f"{self.mf['nombre_area']}",
            'note_catalog_booth':f"{self.Location.UBICACIONES_CAT_OBJ_ID}",
            'note_catalog_guard':f"{self.mf['catalog_guard']}",
            'note_catalog_guard_close':f"{self.mf['catalog_guard_close']}",
            'note_close_date':'6647fadc96f80017ac38864a',
            'note_comments':'6647fb38da07bf430e273ea2',
            'note_comments_group':'6647fb1874c1a87eb02a9037',
            'note_file':'6647fadc96f80017ac388648',
            'note_guard':f"{self.mf['nombre_empleado']}",
            'note_guard_close':f"{self.mf['nombre_guardia_apoyo']}",
            'note_open_date':'6647fadc96f80017ac388646',
            'note_pic':'6647fadc96f80017ac388649',
            'note_status':'6647f9eb6eefdb1840684dc1',
        }

        self.notes_project_fields = {
            'area': f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['area']}",
            'closed_by': f"{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['worker_name_b']}",
            'created_by': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_name']}",
            'location': f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['location']}",
            'support_guard':f"{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}.{self.f['worker_name_b']}",
        }

        self.pase_entrada_fields = {
            'acepto_aviso_datos_personales': '6827488724317731cb288117',
            'acepto_aviso_privacidad': '6825268e0663cce4b1bf0a17',
            'acompanantes':'6a22f7b7826f8544c6183362',
            'acompanantes_grupo':'6a22fc57c026befc685f4fe3',
            'apple_wallet_pass': '682785fbedd82a9104287e25',
            'archivo_invitacion': '673773741b2adb2d05d99d63',
            'area':f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}",
            'catalog_area_pase':'664fc5f3bbbef12ae61b15e9',
            'catalogo_visitante_registrado': '66a83ad456d1e741159ce118',
            'comentario_pase':'65e0a69a322b61fbf9ed23af',
            'commentario_area':"66af1a77d703592958dca5eb",
            'conf_perfiles':f"{self.CONFIG_PERFILES_OBJ_ID}",
            'conservar_datos_por': '6827488724317731cb288118',
            'creado_desde':'698b6f3d13a551df2b2ecfcb',
            'curp_catalog_pase':f"{self.PASE_ENTRADA_OBJ_ID}.{self.mf['curp']}",
            'direccion_pase':f"{self.mf['catalog_ubicacion']}.{self.mf['direccion']}",
            'email':'662c2937108836dec6d92581',
            'email_catalog_pase':f"{self.PASE_ENTRADA_OBJ_ID}.{self.mf['email_vista']}",
            'email_pase':'662c2937108836dec6d92581',
            'empresa_pase_catalog':f"{self.PASE_ENTRADA_OBJ_ID}.{self.mf['empresa']}",
            'empresa_pase':'66357d5e4f00f9018ce97ce9',
            'favoritos':'674642e2d53ce9476994dd89',
            'fecha_hasta_pase':'662c304fad7432d296d92583',
            'foto_pase':f"{self.PASE_ENTRADA_OBJ_ID}.{self.mf['foto']}",
            'foto_pase_id':f"{self.mf['foto']}",
            'google_wallet_pass_url': '6820df5a6cfcee960fb4275c',
            'grupo_areas_acceso':'663fed6cb8262fd454326cb3',
            'grupo_equipos':'663e446cadf967542759ebbb',
            'grupo_instrucciones_pase':'65e0a68a06799422eded24aa',
            'identificacion_pase':f"{self.PASE_ENTRADA_OBJ_ID}.{self.mf['identificacion']}",
            'identificacion_pase_id':f"{self.mf['identificacion']}",
            'motivo':f"{self.CONFIG_PERFILES_OBJ_ID}.{self.mf['motivo']}",
            'nombre':'662c2937108836dec6d92580',
            'nombre_area':f"{self.mf['nombre_area']}",
            'nombre_catalog_pase':f"{self.PASE_ENTRADA_OBJ_ID}.{self.mf['nombre_visita']}",
            'nombre_pase':'662c2937108836dec6d92580',
            'nombre_perfil':f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_name']}",
            'nombre_permiso':f"{self.CONFIG_PERFILES_OBJ_ID}.662962bb203407ab90c886e4",
            'nombre_tipo_pase':f"{self.CONFIG_PERFILES_OBJ_ID}.66297e1579900d9018c886ad",
            'nombre_visitante_registrado': '5ea0693a0c12d5a8e43d37df',
            'pdf_to_img': '682222d27e0ea505751e17b4',
            'perfil_pase':f"{self.CONFIG_PERFILES_OBJ_ID}.661dc67e901906b7e9b73bac",
            'perfil_pase_id':f"661dc67e901906b7e9b73bac",
            'qr_pase':'64ef5b5fff1bec97d2ca27b6',
            'requerimientos_pase':f"{self.CONFIG_PERFILES_OBJ_ID}.662962bb203407ab90c886e5",
            'status_pase':'66353daa223b8a43d7f274b5',
            'status_visita_pase':f"{self.PASE_ENTRADA_OBJ_ID}.{self.mf['status_visita']}",
            'telefono_catalog_pase':f"{self.PASE_ENTRADA_OBJ_ID}.{self.mf['telefono']}",
            'telefono_pase':'662c2937108836dec6d92582',
            'tipo_comentario':'66af1977ffb6fd75e769f457',
            'tipo_visita':"662c262cace163ca3ed3bb3a",
            'todas_las_areas':'68f9fdfbd9bf5cb7fd3caece',
            'ubicacion_pase':f"{self.mf['catalog_ubicacion']}.{self.mf['ubicacion']}",
            'ubicacion_pase':f"{self.mf['catalog_ubicacion']}.{self.mf['ubicacion']}",
            'url_hijo':"6a3dc2a391c36d239c1453a7",
            'url_padre':"6a3dc2a391c36d239c1453b7",
            'ubicaciones':'6834e34fa6242006acedda0f',
            'vigencia_expresa_pase':f"{self.CONFIG_PERFILES_OBJ_ID}.662962bb203407ab90c886e7",
            'vigencia_pase':f"{self.CONFIG_PERFILES_OBJ_ID}.662962bb203407ab90c886e6",
            'visita_a':'663d4ba61b14fab90559ebb0',
            'walkin_email':'662c2937108836dec6d92581',
            'walkin_empresa':'66357d5e4f00f9018ce97ce9',
            'walkin_fotografia':'66c4d5b6d1095c4ce8b2c42a',
            'walkin_identificacion':'66c4d5b6d1095c4ce8b2c42b',
            'walkin_nombre':'662c2937108836dec6d92580',
            'walkin_telefono':'662c2937108836dec6d92582',
            'worker_department': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_department']}",
            'habilitar_vehiculo':'6a218bf63b5cf6f0c1c55f29',
            'worker_position': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_position']}",
        }

        self.pase_grupo_visitados ={
        }

        # self.pase_entrada_fields.update(self.pase_grupo_visitados)
        self.pase_grupo_areas = {
            'nombre_perfil':     f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['area']}",
        }

        # self.pase_entrada_fields.update(self.pase_grupo_areas)
        self.pase_grupo_vehiculos = {
            'nombre_perfil':     f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.f['area']}",
            'tipo_vehiuclo':   f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_position']}",
        }

        # self.pase_entrada_fields.update(self.pase_grupo_vehiculos)
        self.pase_entrada_fields.update({
            'ubicacion_cat': f"{self.Location.UBICACIONES_CAT_OBJ_ID}",
            'ubicacion_nombre':self.mf['ubicacion'],
            'ubicacion': f"{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.f['location']}",
            'nombre_visita': f"{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{mf['nombre_visita']}",
            'email_vista': f"{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{self.mf['email_vista']}",
            'curp': self.unlist(f"{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{mf['curp']}"),
            'rfc': f"{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{mf['rfc']}",
            'telefono': f"{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{mf['telefono']}",
            'foto': f"{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{mf['foto']}",
            'identificacion': f"{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{mf['identificacion']}",
            'empresa': f"{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{mf['empresa']}",
            'status_visita': f"{self.VISITA_AUTORIZADA_CAT_OBJ_ID}.{mf['status_visita']}",
            'nombre_perfil': f"{self.CONFIG_PERFILES_OBJ_ID}.{mf['nombre_perfil']}",
            #'nombre_perfil': f"{self.mf['grupo_visitados']}{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_name']}",
            'worker_department': f"{self.mf['grupo_visitados']}{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_department']}",
            'worker_position': f"{self.mf['grupo_visitados']}{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_position']}",
            'catalago_autorizado_por': f"{self.Employee.CONF_AREA_EMPLEADOS_AP_CAT_OBJ_ID}",
            'autorizado_por': self.mf['nombre_guardia_apoyo'],
            'tipo_visita_pase': self.mf['tipo_visita_pase'],
            'grupo_visitados': self.mf['grupo_visitados'],
            'fecha_desde_visita': self.mf['fecha_desde_visita'],
            'fecha_desde_hasta': self.mf['fecha_desde_hasta'],
            'config_dia_de_acceso': self.mf['config_dia_de_acceso'],
            'config_limitar_acceso': self.mf['config_limitar_acceso'],
            'config_dias_acceso': self.mf['config_dias_acceso'],
            'area_catalog_normal':  f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}",
            'area_catalog':  f"{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}",
            'area': '663fb45992f2c5afcfe97ca8',
            'tema_cita':'67329875978e6460083c5648',
            'descripcion': '67329875978e6460083c5649',
            'link':'6732aa1189fc6b0ae27e3824',
            'enviar_correo':'6732a153496e3b26d18e7ee1',
            'enviar_correo_pre_registro':'6734c6d5254e9a61df8e7f51',
            'created_by': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}.{self.f['worker_name']}",
            'comentario_area_pase':self.mf['commentario_area'],
            'ubicaciones': '6834e34fa6242006acedda0f',
            'nombre_acompanante':'6a23408693202c1f1c149692',
            'email_acompanante':'6a23408693202c1f1c149693',
            'telefono_acompanante':'6a23408693202c1f1c149694',
            'foto_acompanante':'6a23408693202c1f1c149695',
        })

        self.conf_accesos_fields = {
            'grupos':f"{self.GRUPOS_CAT_OBJ_ID}",
            'menus':"6722472f162366c38ebe1c64",
            'usuario_cat':  f"{self.Employee.EMPLOYEE_OBJ_ID}",
        }

        self.conf_modulo_seguridad = {
            'datos_requeridos':"6769756fc728a0b63b8431ea",
            'envio_por':"6810180169eeaca9517baa5b",
            'grupo_requisitos':"676975321df93a68a609f9ce",
            'grupo_tipo_de_pase': '694055a57d064b380f010d7f',
            'ubicacion':"663e5c57f5b8a7ce8211ed0b",
            'ubicacion_cat':  f"{self.Location.UBICACIONES_CAT_OBJ_ID}",
            'prefijo_telefonico':'6a221532db633d0cf4faf12f',
            'tolerancia_de_entrada_previa':"6a2835444172819eb764943b",
            'tolerancia_de_entrada_posterior':"6a22155492b193f057990682",
        }

        self.paquetes_fields = {
            'area_paqueteria':f"{self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{self.mf['nombre_area']}",
            'descripcion_paqueteria':"67e4652619b4be1c5a76a485",
            'entregado_a_paqueteria':'67e4652619b4be1c5a76a489',
            'estatus_paqueteria': '67e4652619b4be1c5a76a488',
            'fecha_entregado_paqueteria': '67e4652619b4be1c5a76a487',
            'fecha_recibido_paqueteria': '67e4652619b4be1c5a76a486',
            'fotografia_paqueteria': "67e46624da3191c5ef4ab6d0",
            'guardado_en_paqueteria': f"{self.LOCKERS_CAT_OBJ_ID}.{self.mf['locker_id']}",
            'proveedor':'667468e3e577b8b98c852aaa',
            'proveedor_cat':f"{self.PROVEEDORES_CAT_OBJ_ID}",
            'quien_recibe_cat': f"{self.Employee.CONF_AREA_EMPLEADOS_CAT_OBJ_ID}",
            'quien_recibe_otro':"69c47a1ce96590f9dbf494b0",
            'quien_recibe_paqueteria':f"{self.mf['nombre_empleado']}",
            'ubicacion_paqueteria':f"{self.Location.UBICACIONES_CAT_OBJ_ID}.{self.mf['ubicacion']}",
        }

        self.rondin_keys = {
            'accion_recurrencia': 'abcde00010000000a0000001',
            'areas': '6645052ef8bc829a5ccafaf5',
            'cada_cuantas_horas_se_repite': 'abcde0001000000000010013',
            'cada_cuantos_dias_se_repite': 'abcde0001000000000010017',
            'cada_cuantos_meses_se_repite': 'abcde0001000000000010019',
            'cada_cuantos_minutos_se_repite': 'abcde0001000000000010011',
            'cron_id':'abcde0001000000000011111',
            'dag_id':'abcde0001000000000000000',
            'cuanto_tiempo_de_anticipacion': 'abcde0002000000000010004',
            'cuanto_tiempo_de_anticipacion_expresado_en': 'abcde0002000000000010005',
            'duracion_estimada': '6854459836ea891d9d2be7d9',
            'en_que_hora_sucede': 'abcde0001000000000010012',
            'en_que_mes': 'abcde0001000000000010018',
            'en_que_minuto_sucede': 'abcde0001000000000010010',
            'en_que_semana_sucede': 'abcde0001000000000010015',
            'fecha1':'abcde000100000000000f000',
            'fecha2':'abcde000100000000000f001',
            'fecha_final_recurrencia': 'abcde0001000000000010099',
            'fecha_hora_programada': 'abcde0001000000000010001',
            'grupo_areas':'66462aa5d4a4af2eea07e0d1',
            'grupo_asignado': '638a9ab3616398d2e392a9fa',
            'grupo_asignado_rondin':'671055aaa487da57ba57b294',
            'id_grupo':'639b65dfaf316bacfc551ba2',
            'la_recurrencia_cuenta_con_fecha_final': '64374e47a208e5c0ff95e9bd',
            'la_tarea_es_de': 'abcde0001000000000010006',
            "link":'6927eb61d92ecf923b60a0de',
            'nombre_rondin': '6645050d873fc2d733961eba',
            'programar_anticipacion': 'abcde0002000000000010001',
            'que_dia_del_mes': 'abcde0001000000000010016',
            'que_dias_de_la_semana': 'abcde0001000000000010014',
            'se_repite_cada': 'abcde0001000000000010007',
            'registro_padre':'6a345db8f1b0cf32e9021f93',
            'status':'abcde00010000000a0000000',
            'sucede_cada': 'abcde0001000000000010008',
            'sucede_recurrencia': 'abcde0001000000000010009',
            'tiempo_para_ejecutar_tarea': 'abcde0001000000000010004',
            'tiempo_para_ejecutar_tarea_expresado_en': 'abcde0001000000000010005',
            'tipo_asignacion':'6a344c7a6e574352dcccc7ba',
            'tipo_rondin':'69b9b98d2a02f4a0dd35f5c1',
            'ubicacion': '663e5c57f5b8a7ce8211ed0b',
            'grupo_asignado_a':'6a31d37adeceb005758cd4e2',
            'area':f"{self.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.mf['nombre_area_salida']}",
            'grupo':f"{self.GRUPOS_CAT_OBJ_ID}",
            'grupo_id':'5d810a982628de5556500d56',
            'prompt_inspeccion':'6a0ce90fefa8de16875f0541',
        }

        self.notes_project_fields.update(self.notes_fields)

        self.bitacora_acceos = {}
        ## Fields ##
        '''
        `self.f`: En esta variable "fields", se almacenan todos los campos de todos los módulos heredados.
        El orden de reemplazo se ve afectado por el orden en que se hereda cada módulo. El orden que se otorga, es considerando
        que la variable se iguala en la base, y se va armando en tren de dependencias ej.

            Class A:
            Class B(A):
            Class C(B):
            Class D(C):

            x_obj = D()
            el orden de herencia será, primero carga A > B > C > D.
        '''

        self.f.update(self.notes_fields)
        self.f.update(self.checkin_fields)
        self.f.update({
            'areas_del_rondin': '66462aa5d4a4af2eea07e0d1',
            'duracion_rondin':'6639b47565d8e5c06fe97cf3',
            'duracion_traslado_area':'6760a9581e31b10a38a22f1f',
            'fecha_inspeccion_area':'6760a908a43b1b0e41abad6b',
            'fecha_programacion':'6760a8e68cef14ecd7f8b6fe',
            'fecha_inicio_rondin':'6818ea068a7f3446f1bae3b3',
            'evidencia_incidencia':'66ec6846028e5550cbf012e0',
            'area_foto': '6763096aa99cee046ba766ad',
            'area_tag_id': '6762f7b0922cc2a2f57d4044',
            'tipo_de_area': '663e5e68f5b8a7ce8211ed18',
            'tipo_rondin': '69b9b98d2a02f4a0dd35f5c1',
            'foto_evidencia_area': '681144fb0d423e25b42818d2',
            'foto_equipo':'698ca59f8797d7e10e57617d',
            'foto_vehiculo':'698ca60575c268aadf768c57',
            'grupo_incidencias_check': '681144fb0d423e25b42818d3',
            'comentario_check_area': '681144fb0d423e25b42818d4',
            'check_status': '681fa6a8d916c74b691e174b',
            'status_check_ubicacion': '68e41c904da05123bf9326ee',
            'incidencia':'663973809fa65cafa759eb97',
            'categoria':'686807d46e41614d708f6fc9',
            'sub_categoria': '686807a7ee7705c5c8eb181a',
            'incidente_open': '6811455664dc22ecae83f75b',
            'incidente_accion': '681145323d9b5fa2e16e35cc',
            'incidente_evidencia': '681145323d9b5fa2e16e35cd',
            'incidente_documento': '685063ba36910b2da9952697',
            'bitacora_rondin_incidencias': '686468a637d014b9e0ab5090',
            'fecha_hora_incidente_bitacora': '69000e4c43078234e5e08390',
            'area_incidente_bitacora': '69000e4c43078234e5e0838f',
            'comentario_incidente_bitacora': '681145323d9b5fa2e16e35cb',
            'id_usuario':'638a9a99616398d2e392a9f5',
            'nombre_area_salida':'663fb45992f2c5afcfe97ca8',
            'status_cron': 'abcde00010000000a0000000',
            'fecha_primer_evento':'abcde0001000000000010001',
            'fecha_final_recurrencia': 'abcde0001000000000010099',
            'geolocalizacion_area_ubicacion': '688bac1ecfdcf8b16eb209b5',
            'grupo_de_areas_recorrido': '6645052ef8bc829a5ccafaf5',
            'tipo_guardia': '68acee270f2af5e173b7f92e',
            'status_user': '6639b2744bb44059fc59eb62',
            'grupo_roles': '6a46f1d3b89f9975dfd0bae8',
            'option_update_qr': '68928c76fc027d15895fa23c',
            'anterior_qr': '68928cfdc847e631ba2c157e',
            'new_qr': '68928cfdc847e631ba2c157f',
            'tag_id_area_ubicacion': '6762f7b0922cc2a2f57d4044',
            'status_details': '689a46342038ded0e949be07',
            'status_details_message': '689a46342038ded0e949be08',
            'status_new_qr': '68929562c6b050d5066a2aec',
            'details_new_qr': '68929562c6b050d5066a2aed',
            'porcentaje_obtenido_bitacora': '689a7ecfbf2b4be31039388e',
            'cantidad_areas_inspeccionadas': '68a7b68a22ac030a67b7f8f8',
            'ingreso_maximo': '69824e4bfdead27b0009739e',
            'folio_del_check': '688a584dfa0d4a318d9ff389',
            'estatus_area': '663e5e4bf5b8a7ce8211ed15',
            'estatus_config_area': '663e5e4bf5b8a7ce8211ed14',
            'qr_area': '663e5e4bf5b8a7ce8211ed13',
            'pais_area': '663a7ca6e48382c5b12308fa',
            'ciudad_area': '6654187fc85ce22aaf8bb070',
            'colonia_area': '663a7f79e48382c5b123090a',
            'direccion_area': '663a7e0fe48382c5b1230902',
            'geolocalizacion_area': '663e5c8cf5b8a7ce8211ed0c',
            'nombre_direccion': '663a7e0fe48382c5b1230901',
            'image_checkin': '6855e761adab5d93274da7d7',
            'foto_cierre_turno': '6879823d856f580aa0e05a3b',
            'fecha_cierre_turno': '6879828d0234f02649cad391',
            'personalizacion_pases': '695d2e1f6be562c3da95c4a7',
            'pases': '695d31b503ccc7766ac28507',
            'grupo_alertas': '695d35b618a37ea04899524f',
            'nombre_alerta': '695d36605f78faab793f497b',
            'accion_alerta': '695d36605f78faab793f497c',
            'llamar_num_alerta': '695d36605f78faab793f497d',
            'email_alerta': '695d36605f78faab793f497e',
            'url_inspeccion': '6a0c8ab354a0b8de897c62cc',
            'proveedor_de_paqueteria': '6a1764be5451b26d5de3152b',
            'tipo_de_proveedor': '6a18e4086423e82150aa527c',
            'tolerancia_de_entrada_previa':"6a2835444172819eb764943b",
            'tolerancia_de_entrada_posterior':"6a22155492b193f057990682",
            'grupo_incluir': '69974d3806cc6d6a17f8b1fa',
            'pases_incluir': '69974d55879296015c1cd8d2',
            'realizado_por': '68cd752bf911c0d6bb1e8e96',
            'comentarios_generales_rondin': '68d5cbdb12b8e764193190a7',
            'bitacora_comentario': '6639b6180bb793945af2742d',
            'rondin_area': '663e5d44f5b8a7ce8211ed0f',
            'foto_area': '6763096aa99cee046ba766ad',
            'porcentaje_de_areas_inspeccionadas': '689a7ecfbf2b4be31039388e',
            'usuarios_invitados': '69df1816f0a5742e4f94d1e3',
            'recorridos': f"{self.CONFIGURACION_RECORRIDOS_OBJ_ID}",
            'asignado_a': f"{self.USUARIOS_OBJ_ID}",
            'fecha_hora_programada_inicio': '6760a8e68cef14ecd7f8b6fe',
            'fecha_hora_inicio': '6818ea068a7f3446f1bae3b3',
            'fecha_hora_fin': '6760a8e68cef14ecd7f8b6ff',
            'porcentaje_avance': '689a7ecfbf2b4be31039388e',
            'estatus_recorrido': '6639b2744bb44059fc59eb62',
            'motivo_cancelacion': '6639b6180bb793945af2742d',
            'comentario_general': '69149dcec7b3ec9f2b9395b2',
            'comentarios_generales': '6927a0cdc03f0f8e5355437a',
            'url_rondin': '690cefdca2dff2f469da17e0',
            'nombre_emp': '638a9a7767c332f5d459fc81',
        })

        self.rondin_keys = {
            'accion_recurrencia': 'abcde00010000000a0000001',
            'areas': '6645052ef8bc829a5ccafaf5',
            'cada_cuantas_horas_se_repite': 'abcde0001000000000010013',
            'cada_cuantos_dias_se_repite': 'abcde0001000000000010017',
            'cada_cuantos_meses_se_repite': 'abcde0001000000000010019',
            'cada_cuantos_minutos_se_repite': 'abcde0001000000000010011',
            'cron_id':'abcde0001000000000011111',
            'dag_id':'abcde0001000000000000000',
            'cuanto_tiempo_de_anticipacion': 'abcde0002000000000010004',
            'cuanto_tiempo_de_anticipacion_expresado_en': 'abcde0002000000000010005',
            'duracion_estimada': '6854459836ea891d9d2be7d9',
            'en_que_hora_sucede': 'abcde0001000000000010012',
            'en_que_mes': 'abcde0001000000000010018',
            'en_que_minuto_sucede': 'abcde0001000000000010010',
            'en_que_semana_sucede': 'abcde0001000000000010015',
            'fecha1':'abcde000100000000000f000',
            'fecha2':'abcde000100000000000f001',
            'fecha_final_recurrencia': 'abcde0001000000000010099',
            'fecha_hora_programada': 'abcde0001000000000010001',
            'grupo_areas':'66462aa5d4a4af2eea07e0d1',
            'grupo_asignado': '638a9ab3616398d2e392a9fa',
            'grupo_asignado_rondin':'671055aaa487da57ba57b294',
            'id_grupo':'639b65dfaf316bacfc551ba2',
            'la_recurrencia_cuenta_con_fecha_final': '64374e47a208e5c0ff95e9bd',
            'la_tarea_es_de': 'abcde0001000000000010006',
            "link":'6927eb61d92ecf923b60a0de',
            'nombre_rondin': '6645050d873fc2d733961eba',
            'programar_anticipacion': 'abcde0002000000000010001',
            'que_dia_del_mes': 'abcde0001000000000010016',
            'que_dias_de_la_semana': 'abcde0001000000000010014',
            'se_repite_cada': 'abcde0001000000000010007',
            'registro_padre':'6a345db8f1b0cf32e9021f93',
            'status':'abcde00010000000a0000000',
            'sucede_cada': 'abcde0001000000000010008',
            'sucede_recurrencia': 'abcde0001000000000010009',
            'tiempo_para_ejecutar_tarea': 'abcde0001000000000010004',
            'tiempo_para_ejecutar_tarea_expresado_en': 'abcde0001000000000010005',
            'tipo_asignacion':'6a344c7a6e574352dcccc7ba',
            'tipo_rondin':'69b9b98d2a02f4a0dd35f5c1',
            'ubicacion': '663e5c57f5b8a7ce8211ed0b',
            'grupo_asignado_a':'6a31d37adeceb005758cd4e2',
            'area':f"{self.Location.AREAS_DE_LAS_UBICACIONES_SALIDA_OBJ_ID}.{self.mf['nombre_area_salida']}",
            'grupo':f"{self.GRUPOS_CAT_OBJ_ID}",
            'grupo_id':'5d810a982628de5556500d56',
            'prompt_inspeccion':'6a0ce90fefa8de16875f0541',
        }

        self.INSPECTION_ACCEPTED_TYPES = ['radio', 'checkbox', 'decimal', 'integer', 'text', 'slider']

        ### Transportistas (migrado de transportistas.py / transportistas_bitacoras.py) ###
        self.f.update({
            # NOTA: 'address_name' nunca se definio en el legacy (bug preexistente,
            # create_pass_transportista lo referencia sin haberlo agregado nunca a self.f).
            # Se alias temporalmente al mismo id que 'direccion' hasta confirmar el id real
            # con el esquema de LinkaForm.
            'address_name': '663a7e0fe48382c5b1230902',
        })

        self.pass_fields_transportista = {
            "tipo_de_operacion": "6a1ddb53f5a36ba1c7dd029c",

            "nombre_crea_el_pase": "6a20741046cc9cdddf3b3c07",
            "email_crea_el_pase": "6a20741046cc9cdddf3b3c08",
            "telefono_crea_el_pase": "6a20741046cc9cdddf3b3c09",

            "proveedor": "6a1ddb53f5a36ba1c7dd029d",
            "proveedor_email": "6a207762cd730fb838ce1bb1",
            "proveedor_telefono": "6a207762cd730fb838ce1bb2",

            "grupo_documentos_para_ocr": "6a2ae394b8e5ca8fd73705dc",
            "tipo_de_documento": "6a2ae3d8cf0be6f60c19f85d",
            "no_de_documento": "6a2ae3d8cf0be6f60c19f85e",
            "documento_para_ocr": "6a2ae3d8cf0be6f60c19f85f",

            "proveedor_cliente_material": "6a207762cd730fb838ce1bb4",
            "orden_de_compra": "6a1ddb53f5a36ba1c7dd02a0",
            "grupo_materiales": "6a2714954a54077ffa2394e6",
            "contenedor": "6a2714eeca6ac6897ef55d92",
            "sello":      "6a2714eeca6ac6897ef55d93",
            "tipo":       "6a2714eeca6ac6897ef55d94",
            "cantidad":   "6a2714eeca6ac6897ef55d95",
            "peso":       "6a2714eeca6ac6897ef55d96",
            "volumen":    "6a2714eeca6ac6897ef55d97",

            "direccion_de_recoleccion": "6a1ddb53f5a36ba1c7dd02a1",
            "fecha_pase_transportista_desde": "6a1ddcba20dadbb04a29b59f",
            "fecha_pase_transportista_hasta": "6a1f15aec19e655f79987c34",
            "hora_inicial": "6a1f15aec19e655f79987c36",
            "hora_final": "6a1f15aec19e655f79987c37",

            "lugar_de_recoleccion": "6a2079343d463b1222e5d794",
            "direccion_lugar_de_recoleccion": "6a2079343d463b1222e5d795",
            "fecha_de_recoleccion": "6a2079343d463b1222e5d796",
            "hora_inicial_recoleccion": "6a2079343d463b1222e5d797",
            "hora_final_recoleccion": "6a2079343d463b1222e5d798",
            "anden_recoleccion": "6a2079343d463b1222e5d799",
            "responsable": "6a2079343d463b1222e5d79a",
            "responsable_email": "6a2079343d463b1222e5d79b",
            "responsable_telefono": "6a2079343d463b1222e5d79c",
            "metodo_de_embarque": "6a2079343d463b1222e5d79d",
            "incoterm": "6a2079343d463b1222e5d79e",

            "url_del_pase_transportista": "6a20d4a39ebbf58470fe73b5",
            "qr_del_pase_transportista": "6a20a8e138dff4ad8155c325",
            "estado_transportista": "6a20bb99782fe54a2681fc56",
            "token_transportista": "6a20c1811b6edd566116f483",

            "conductor_foto_licencia": "6a2add8342320b4d1b66db84",
            "conductor_nombre": "6a2adc08877c6087f9c2326b",
            "conductor_no_licencia": "6a2adc08877c6087f9c2326c",
            "conductor_lugar_expedicion": "6a2adc08877c6087f9c2326d",
            "conductor_vigencia": "6a2adc08877c6087f9c2326e",
            "ayudante_foto_licencia": "6a2add8342320b4d1b66db85",
            "ayudante_nombre": "6a2adc08877c6087f9c2326f",
            "ayudante_no_licencia": "6a2adc08877c6087f9c23270",
            "ayudante_lugar_expedicion": "6a2adc08877c6087f9c23271",
            "ayudante_vigencia": "6a2adc08877c6087f9c23272",
            "vehiculo_tarjeta_circulacion": "6a2add8342320b4d1b66db86",
            "vehiculo_linea": "6a2add8342320b4d1b66db87",
            "vehiculo_tipo_unidad": "6a2add8342320b4d1b66db88",
            "vehiculo_marca": "6a2add8342320b4d1b66db89",
            "vehiculo_modelo": "6a2add8342320b4d1b66db8a",
            "vehiculo_year": "6a2add8342320b4d1b66db8b",
            "vehiculo_placas": "6a2add8342320b4d1b66db8c",
            "vehiculo_no_economico": "6a2add8342320b4d1b66db8d",
            "vehiculo_niv": "6a2add8342320b4d1b66db8e",
            "foto_contenedores": "6a2b045ed8034654f212c1bc",
            "grupo_contenedores": "6a2add8342320b4d1b66db8f",
            "contenedor_numero": "6a2addcfcee6b93e39ab8a51",
            "contenedor_sello": "6a2addcfcee6b93e39ab8a52",
            "contenedor_tipo": "6a2addcfcee6b93e39ab8a53",
        }

        self.bitacora_transportista_fields = {
            'estatus': '6a31921f07fb9cb5840d1f22',
            'fecha_hora_ingreso': '6a3bee0a7829a4ca9572d39e',
            'fecha_hora_descarga': '6a3bee0a7829a4ca9572d39f',

            'grupo_fotos_y_documentos': '6a3bee0a7829a4ca9572d3a0',
            'tipo_de_documento': '6a3bee394a7a0748a6fc9a56',
            'documento': '6a3bee394a7a0748a6fc9a57',

            'num_de_pase': '6a31921f07fb9cb5840d1f23',
            'empresa_transportista': '6a31929d0bf8c5fc715d7424',
            'tipo_de_operacion': '6a31929d0bf8c5fc715d7425',
            'procedencia': '6a3193dccf1326ad4b7a9a52',
            'tipo_de_vehiculo': '6a3193dccf1326ad4b7a9a53',
            'placas_de_vehiculo': '6a31921f07fb9cb5840d1f24',
            'placas_de_vehiculo_tarjeta_circulacion': '6a5018081d7498e16bbb4b75',
            'marca_vehiculo': '6a4415c7b7ce8af39efb3aa8',
            'year_vehiculo': '6a4415c7b7ce8af39efb3aa9',
            'color_vehiculo': '6a4415c7b7ce8af39efb3aaa',
            'num_eco_num_rotulo': '6a3193dccf1326ad4b7a9a56',
            'conductor': '6a3193dccf1326ad4b7a9a57',
            'ayudante': '6a42cd6385b4d5aa41c2a922',
            'num_licencia': '6a3193dccf1326ad4b7a9a58',
            'vigencia_licencia': '6a42e2eab55463ad9f31abf3',
            'rfc_conductor': '6a42e5143f8adeaa55ef9a4a',
            'firma_conductor': '6a3193dccf1326ad4b7a9a5b',
            'anden_asignado': '6a31929d0bf8c5fc715d7427',

            'proveedor_cliente': '6a42dfd48e70db919887e4b0',
            'orden_de_compra': '6a42dfd48e70db919887e4b1',

            'grupo_materiales': '6a42c5e02196461994770602',
            'lugar_material': '6a42c7a7a1555d53d6b9194c',
            'no_referencia_material': '6a42c7a7a1555d53d6b9194d',
            'producto_material': '6a44091a4e3983d839de22ee',
            'lote_material': '6a4409523a38bb598a0a18a0',
            'cantidad_material': '6a42c7a7a1555d53d6b91950',
            'cantidad_fisica_material': '6a454fb37ddcb3993dd90107',
            'peso_material': '6a42c7a7a1555d53d6b91951',
            'volumen_material': '6a42c7a7a1555d53d6b91952',

            'grupo_remolques': '6a31959ed11ece87f2b0052d',
            'tipo_remolque': '6a319693884bec802c94fa44',
            'no_referencia_remolque': '6a443aa0f4bede456259a441',
            'num_sello': '6a319693884bec802c94fa45',
            'num_caja_contenedor': '6a319693884bec802c94fa46',
            'placas_de_caja': '6a319693884bec802c94fa47',
            'color_remolque_contenedor': '6a440b059581538d55b3565e',
            'comentarios': '6a319693884bec802c94fa48',

            'grupo_sellos': '6a42c65c03f125df7ad28601',

            'grupo_inspecciones': '6a42a7068dcfbf362329a972',
            'tipo_inspeccion': '6a42c80b03f125df7ad2862b',
            'url_inspeccion': '6a42a71aec3f7153a3d2aea3',
        }

        self.inspeccion_entrada_tractor_fields = {
            'defensa': '20e7950eaac0054dbb8ca133',
            'defensa_comentarios': '7aa52ec9ded1f199a3bfa307',
            'defensa_evidencia': '529623abe2be9e64816dec78',

            'motor_caja_de_la_bateria_caja_y_filtros_de_aire': '2aa45df8132536520b2a2bdd',
            'motor_caja_de_la_bateria_caja_y_filtros_de_aire_comentarios': '4604526acf0bf06c658add75',
            'motor_caja_de_la_bateria_caja_y_filtros_de_aire_evidencia': '8f12a402e6094434d6028246',

            'llantas_y_rines_tractor_y_remolque': '4b58a0007c1730a1ff9cc56f',
            'llantas_y_rines_tractor_y_remolque_comentarios': '8e2645d9b0117869c0b93bc1',
            'llantas_y_rines_tractor_y_remolque_evidencia': 'a9be932860ceeb9face9b24d',

            'piso_tractor': 'acba826a28a8d1d48b743b53',
            'piso_tractor_comentarios': '5e5cc9112d6c74a8c0d96c6b',
            'piso_tractor_evidencia': '5e0e635e8e5e7788793dc632',

            'tanque_de_combustible': '72e1fe8cf4fad9736fbb141c',
            'tanque_de_combustible_comentarios': 'ddd7b180bcb8a98c556c67ef',
            'tanque_de_combustible_evidencia': 'cef55b76f55eed057cf64cad',

            'cabina_dormitorio_puertas_y_compartimientos_de_herramientas_seccion_de_pasajero_y_techo': '83ceff5fda79787b48219268',
            'cabina_dormitorio_puertas_y_compartimientos_de_herramientas_seccion_de_pasajero_y_techo_comentarios': '700d1c62d264a6c3039f65c1',
            'cabina_dormitorio_puertas_y_compartimientos_de_herramientas_seccion_de_pasajero_y_techo_evidencia': '6cb1dd20ae67dff1e20b08bd',

            'tanque_de_aire': 'ac82529cb6081ee6327ee04f',
            'tanque_de_aire_comentarios': '9cdc267b92fe4c144de7c370',
            'tanque_de_aire_evidencia': 'e01e5ac0be30514b35bd3d13',

            'ejes_de_transmision': 'bcb4e55eddda4821b9db0304',
            'ejes_de_transmision_comentarios': '8e5bc150c3791c9917314b92',
            'ejes_de_transmision_evidencia': '5b72adefa1c7c716e0f24941',

            'quinta_rueda': '3ad0cca2f6449042ad664cfd',
            'quinta_rueda_comentarios': 'cedf4d6e6f7120c152d9c0fb',
            'quinta_rueda_evidencia': '35ccd51789e6260465d17ea7',

            'chasis': 'd08cc0f655036b4fb2a09056',
            'chasis_comentarios': 'db0dd2a781343effa2a7153d',
            'chasis_evidencia': 'e957e4cb96e1ef8f999a5938',

            'puertas_externa': '5c100788b4211b8122e4395c',
            'puertas_externa_comentarios': '87fffff1f65ef97ddc4d23bf',
            'puertas_externa_evidencia': '666ce737007a5ccc57c9f369',

            'piso_externo_trailer_contenedor_caja': 'f87fd7be1133ee21cc723f7c',
            'piso_externo_trailer_contenedor_caja_comentarios': 'de6dffa1def019fe589a329a',
            'piso_externo_trailer_contenedor_caja_evidencia': 'e7c54e4187ee035e6bb3be7b',

            'paredes_externa': 'fc63e8996ccf5c91a80c0e2f',
            'paredes_externa_comentarios': '531d51796e724cc7f14cb496',
            'paredes_externa_evidencia': 'b2d3aaf29aa9374130881632',

            'pared_frontal_externa': '731b4abf0672038c57d8d516',
            'pared_frontal_externa_comentarios': '1f3c15fb61a4a143f773809d',
            'pared_frontal_externa_evidencia': '56d9b00ce47ae297a64aa90b',

            'techo_externo': '8b18d4aa1d62615cacf2776f',
            'techo_externo_comentarios': '85df5aa6a444e9490f14ce86',
            'techo_externo_evidencia': '5b82b568466ceebc18d49dd3',

            'unidad_de_refrigeracion': '8b4e8a6dec2392c9f267e179',
            'unidad_de_refrigeracion_comentarios': '747090a5b505163130df82e4',
            'unidad_de_refrigeracion_evidencia': '5544eaaccb74e9d09b7e2f77',

            'escape_mofles': '48de45705387f226f6551c1b',
            'escape_mofles_comentarios': '0307abb04ee4f8b3786cca23',
            'escape_mofles_evidencia': '32f0559232cbc31f5cc6a472',
        }

        self.inspeccion_entrada_ctpat_contenedor_fields = {
            'altura_interior': 'd412fb9f428dfc231c9bc3f0',
            'ancho_interior': '6477c73222d9b7e8dd1de3b9',
            'longitud_interior': 'd7c19cbd2cfe6b19f848d697',
            'exterior_parte_inferior_del_contenedor_bastidor_o_chasis': '4a819aa25c6e76080f76317a',
            'puertas_interiores_exteriores': 'b4f2b497790d8fa30739ab05',
            'pared_interior_lado_derecho': 'c334bc2360c643779bdcd495',
            'pared_interior_lado_izquierdo': '4c90dcc67f8e9f029878502c',
            'pared_interior_frontal': '14aea746aadf15c99edb8592',
            'techo_cubierta_superior': 'bc75ab3fdb2258286b0b41c0',
            'piso_interior': '371a7d9c3ae8a40a32b3762a',
        }

        self.inspeccion_entrada_ctpat_remolque_fields = {
            'altura_interior': '6703c4acd45242ffb0eb0839',
            'ancho_interior': '7bfa6fe868c1cbec93a051e5',
            'longitud_interior': '2624dc82316e99315084d385',

            'tanque_de_aire': 'd1fae4d0b2ec9569fbcf8770',
            'tanque_de_aire_comentarios': 'd2bacb536ead1a15f56bbe6c',
            'tanque_de_aire_evidencia': '28538bb0340a0eccc15e150b',

            'ejes_de_transmision': 'd57c0e9a92f8b3b552f2b66a',
            'ejes_de_transmision_comentarios': '9f6a0733c5c36bcc4e6051de',
            'ejes_de_transmision_evidencia': '089e40849794b1edbe667291',

            'quinta_rueda': 'aeed49c20dd20d18904ac28f',
            'quinta_rueda_comentarios': '481f00fd61a55c0b9aef99e4',
            'quinta_rueda_evidencia': 'c86cf900756ed0667122d999',

            'chasis': '9a6743b2e92e16e2b727e667',
            'chasis_comentarios': '6aa6dabeb1430c92bf9c36a9',
            'chasis_evidencia': 'c420045f52f188fcbd616165',

            'puertas_externa': 'b0dca85ed86edd92560f634c',
            'puertas_externa_comentarios': '3b85b7104be1df0dbe8762e7',
            'puertas_externa_evidencia': '608def717f6c6f14e1f8ab6e',

            'piso_externo_trailer_contenedor_caja': '2cb78278523b502800a47e2e',
            'piso_externo_trailer_contenedor_caja_comentarios': '7bc7a9a7a58d45946c2e70a6',
            'piso_externo_trailer_contenedor_caja_evidencia': 'c16b8d4dfc22709c7785cc63',

            'paredes_externa': '198cf876dc13d7bd658a4cbd',
            'paredes_externa_comentarios': '8a9af06c2c1045f46dfa44d2',
            'paredes_externa_evidencia': '8af47b03f950e87661b5835b',

            'pared_frontal_externa': '36b4b172e38a3dc1b8b226d1',
            'pared_frontal_externa_comentarios': 'bb279c901f91c114d1220452',
            'pared_frontal_externa_evidencia': 'ddff798b400d03d48b9ef808',

            'techo_externo': 'bbc21e44dec3040d81e005f2',
            'techo_externo_comentarios': 'e2e3ae0dbf920b1c44502fbb',
            'techo_externo_evidencia': '59bf2262a664e2b16ba1a299',

            'unidad_de_refrigeracion': 'cbb1c127c08011c3d7d4c344',
            'unidad_de_refrigeracion_comentarios': '80ad083a0f6319e6fd63d681',
            'unidad_de_refrigeracion_evidencia': 'd0240215edecf39a02c5a891',

            'escape_mofles': '545c0b134ab1d2f11cef90a9',
            'escape_mofles_comentarios': '736b1fe2e2609d47beef2a03',
            'escape_mofles_evidencia': 'b7618c209a113ef54ec2b58b',
        }

        self.inspeccion_de_sello_fields = {
            'numero_de_sello_fisico': 'ad57d9e43537244dc2f66280',
            'numero_de_sello_esperado_revisado': '22e2974e099b937e4c9c7094',
            'tipo_de_sello_clasificacion_iso_17712': '1e534c51db80d867b1922c86',
            'matriz_vttt_marca_cada_accion_verificada': '92ab37dbe06381e6100f88f0',
            '1_foto_del_sello': '1defc3e446a9ebd00c649dbc',
            '2_sello_colocado_en_las_puertas': '26f5f07d55f304e9015ae64d',
            '3_puertas_completas_del_remolque': 'be928c48d8a6353077ec5eba',
            '4_placas_o_economico': 'd7479071e6aabdeaa10ce41b',
            '5_identificacion_del_operador': '718a0a37c5a6965b2127d2c0',
            'comentarios': '0e009f7829544463cbf89e1e',
        }

        ### Offline sync (migrado de offline_services.py / lkf_addons.addons.accesos.app) ###
        self.f.update({
            'bitacora_rondin_url': '690cefdca2dff2f469da17e0',
            'fecha_inicio_turno': '6879828d0234f02649cad390',
            'grupo_comentarios_generales': '6927a0cdc03f0f8e5355437a',
            'grupo_comentarios_generales_fecha': '6927a0ea1c378cbd7f60a135',
            'grupo_comentarios_generales_texto': '6927a0ea1c378cbd7f60a136',
            'documento_check': '692a1b4e005c84ce5cd5167f',
        })

        # Allowlist de llaves (no ids de campo) usado por sync_incidence_to_lkf para
        # filtrar que llaves de un documento CouchDB (ya en formato labels) se copian
        # al payload de create_incidence/update_incidence.
        self.incidence_filter = {
            'reporta_incidencia': "", 'fecha_hora_incidencia': "", 'ubicacion_incidencia': "",
            'area_incidencia': "", 'incidencia': "", 'comentario_incidencia': "",
            'tipo_dano_incidencia': "", 'dano_incidencia': "", 'evidencia_incidencia': [],
            'documento_incidencia': [], 'prioridad_incidencia': "", 'notificacion_incidencia': "",
            'datos_deposito_incidencia': [], 'tags': [], 'categoria': "", 'sub_categoria': "",
            'incidente': "", 'nombre_completo_persona_extraviada': "", 'edad': "",
            'color_piel': "", 'color_cabello': "", 'estatura_aproximada': "",
            'descripcion_fisica_vestimenta': "", 'nombre_completo_responsable': "",
            'parentesco': "", 'num_doc_identidad': "", 'telefono': "",
            'info_coincide_con_videos': "", 'responsable_que_entrega': "",
            'responsable_que_recibe': "", 'afectacion_patrimonial_incidencia': [],
            'personas_involucradas_incidencia': [], 'acciones_tomadas_incidencia': [],
            'seguimientos_incidencia': [], 'valor_estimado': "", 'pertenencias_sustraidas': "",
            'placas': "", 'tipo': "", 'marca': "", 'modelo': "", 'color': "",
        }

        self.IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.heic'}