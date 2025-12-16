# -*- coding: utf-8 -*-
import sys, simplejson, re
from datetime import datetime

# from linkaform_api import settings, network, utils
# from pci_settings_p3 import *

# if __name__ == '__main__':
#     current_record = simplejson.loads(sys.argv[1])
#     jwt_complete = simplejson.loads(sys.argv[2])
#     config['USER_JWT_KEY'] = jwt_complete["jwt"].split(' ')[1]
#     settings.config.update(config)

#     net = network.Network(settings)
#     cr = net.get_collections()

#     lkf_api = utils.Cache(settings)

class ValidarOS():
    """docstring for ValidarOS"""
    def __init__(self, cr=None, lkf_api=None, p_utils=None, form_id=None, current_record=None, from_carga_prod=False, lkf_obj=None):
        self.cr = cr
        self.lkf_api = lkf_api
        self.p_utils = p_utils
        self.form_id = form_id
        self.from_carga_prod = from_carga_prod
        self.current_record = current_record
        self.folio = self.current_record['folio']
        self.answers = self.current_record['answers']
        self.max_metraje_aceptado = 1125 # Cantidad máxima de metraje aceptado
        self.parent_id = lkf_obj.user.get('parent_id')

        self.catalog_tipos_tarea_factibles = self.p_utils.CATALOG_ID_TIPOS_TAREA_FACTIBLES
        
        self.form_id_listado_tecnicos = self.p_utils.FORM_ID_LISTADO_TECNICOS
        self.form_id_os_ftth_metro = lkf_obj.ORDEN_SERVICIO_FIBRA
        self.form_id_os_ftth_sur = lkf_obj.ORDEN_SERVICIO_FIBRA_SURESTE
        self.form_id_os_ftth_norte = lkf_obj.ORDEN_SERVICIO_FIBRA_NORTE
        self.form_id_os_ftth_occidente = lkf_obj.ORDEN_SERVICIO_FIBRA_OCCIDENTE
        self.form_id_os_cobre_metro = lkf_obj.ORDEN_SERVICIO_COBRE
        self.form_id_os_cobre_sur = lkf_obj.ORDEN_SERVICIO_COBRE_SURESTE
        self.form_id_os_cobre_norte = lkf_obj.ORDEN_SERVICIO_COBRE_NORTE
        self.form_id_os_cobre_occidente = lkf_obj.ORDEN_SERVICIO_COBRE_OCCIDENTE

        self.info_to_complete_record = {
            '5f0e23eaca2ca23aa12f21a9': self.p_utils.get_date_now() # Fecha de Carga Contratista
        }
        self.map_forms_os_ftth = {
            self.form_id_os_ftth_metro: {'form_other_tec': self.form_id_os_cobre_metro, 'field_pdf': '5a8aefa7b43fdd100602f7be', 'field_memo': '5a623e71b43fdd2b2d5a5893'}, # FTTH - COBRE METRO
            self.form_id_os_ftth_sur: {'form_other_tec': self.form_id_os_cobre_sur, 'field_pdf': '5ad14051f851c220dd0eb772', 'field_memo': '5a623ed8b43fdd2b2bffb905'}, # FTTH - COBRE SUR
            self.form_id_os_ftth_norte: {'form_other_tec': self.form_id_os_cobre_norte, 'field_pdf': '5ad14687f851c23d8a4d95c9', 'field_memo': '5a623f3af851c2270c8dc073'}, # FTTH - COBRE NORTE
            self.form_id_os_ftth_occidente: {'form_other_tec': self.form_id_os_cobre_occidente, 'field_pdf': '5ad4b4a9b43fdd7af0f65899', 'field_memo': '5a623faff851c227180570a0'}, # FTTH - COBRE OCCIDENTE
        }

        self.map_forms_os_cobre = {
            self.form_id_os_cobre_metro: {'form_other_tec': self.form_id_os_ftth_metro}, # COBRE - FTTH METRO
            self.form_id_os_cobre_sur: {'form_other_tec': self.form_id_os_ftth_sur, 'field_pdf': '5ad13e8cf851c220dd0eb769'}, # COBRE - FTTH SUR
            self.form_id_os_cobre_norte: {'form_other_tec': self.form_id_os_ftth_norte}, # COBRE - FTTH NORTE
            self.form_id_os_cobre_occidente: {'form_other_tec': self.form_id_os_ftth_occidente, 'field_pdf': '5ad13f95f851c2467770da9e'}, # COBRE - FTTH OCCIDENTE
        }

        self.map_forms_os_general = {**self.map_forms_os_ftth, **self.map_forms_os_cobre}
        self.is_os_cobre = self.form_id in self.map_forms_os_cobre
        self.tecnologia = 'cobre' if self.is_os_cobre else 'fibra'
        
        self.id_field_os_pdf = self.map_forms_os_general.get(self.form_id, {}).get('field_pdf', '5ad13efef851c23d8a4d95af')
        self.id_field_memo = self.map_forms_os_general.get(self.form_id, {}).get('field_memo', '5a623e30f851c2271179f823')

        # Hay fields_ids que cambian entre fibra y cobre, por tanto, se debe validar para obtener el id correcto para el campo
        # Se inicializan los ids como fibra
        self.field_id_fecha_liquidacion = 'f1054000a02000000000fa02'
        self.field_id_distrito = 'f1054000a0100000000000d5'
        self.field_id_tipo_tarea = 'f1054000a010000000000021'
        self.field_id_telefono = 'f1054000a010000000000005'
        self.field_id_cargado_desde_script = lkf_obj.f['field_id_cargado_desde_script']
        self.field_id_cope = 'f1054000a010000000000002'
        self.field_id_os = 'f1054000a0100000000000a1'
        self.field_id_validacion_sistema = '66b25bedd23f3efc6902bb5d'
        self.field_id_mts_bajante = 'f1054000a0200000000000d7'
        self.field_id_mts_adicionales = 'f1054000a020000000000bd7'
        self.field_id_tipo_instalacion = 'f1054000a020000000000004'
        self.field_id_terminal_optica = 'f1054000a020000000000aa1'
        self.field_id_ftth_vsi = 'f1054000a020000000000022'
        self.field_id_expediente_tecnico = 'f1054000a0100000000000d6'
        self.field_id_descuento_x_desfase = '601c7ae006478d9cbee17e00'
        self.field_id_alfanumerico = 'f1054000a0200000000000a3'
        self.field_id_tecnico_pic = '5eb091915ae0d087df1163de'
        self.field_id_proyecto = '633d9f63eb936fb6ec9bf580'
        
        if self.is_os_cobre:
            self.field_id_fecha_liquidacion = '5a1eecfbb43fdd65914505a1'
            self.field_id_distrito = 'f1054000a010000000000003'
            self.field_id_tipo_tarea = 'f1054000a0100000000000a4'
            self.field_id_mts_bajante = 'f1054000a020000000000007'
            self.field_id_expediente_tecnico = 'f1054000a010000000000007'
        
        self.fecha_liquidacion = self.answers.get( self.field_id_fecha_liquidacion )
        self.telefono = self.answers.get( self.field_id_telefono )
        self.record_is_cargado_desde_script = self.answers.get( self.field_id_cargado_desde_script, 'no' ) == 'sí'
        self.record_is_cargado_desde_pic = self.answers.get( '5eb0326a9e6fda7cb11163f1', 'no' ) == 'sí'
        self.cope = self.answers.get( self.field_id_cope )
        self.tipo_instalacion = self.answers.get( self.field_id_tipo_instalacion )

        self.fields_invalid_queja = {
            "5f1721afa63c9a750b820482": "Bonificacion por distancia y volumen de 1 a 5 o.s construidas",
            "5f1721afa63c9a750b820483": "Bonificacion por distancia y volumen de 6 a 15 o.s construidas",
            "5f1721afa63c9a750b820484": "Bonificacion por distancia y volumen de 16 a 25 o.s construidas",
            "5f1721afa63c9a750b820485": "Bonificacion por distancia y volumen mas de 25 o.s construidas",
            "5f1721afa63c9a750b820486": "Montaje de puente en distribuidor general",
            "5f1721afa63c9a750b820487": "INSTALACIÓN DE POSTE DE 25'",
            "5f1721afa63c9a750b820488": "Pruebas de transmision de datos vdsl en roseta de datos con equipo homologado",
            "5f1721afa63c9a750b820489": "Cableado interior 1 aparato y modem para infinitum (dit con splitter con proteccion)",
            "5f1721afa63c9a750b82048a": "IDENTIFICACION DE NUMERO TELEFONICO EN RED PRINCIPAL, INCLUYE MARCACION *080",
            "5f1721afa63c9a750b82048b": "IDENTIFICACION DE NUMERO TELEFONICO EN RED SECUNDARIA, INCLUYE MARCACION *080",
            "5f1721afa63c9a750b82048c": "UBICACIÓN DEL CLIENTE Y PRUEBA DE TRANSMISION VDSL EN TERMINAL AEREA",
            "5f1721afa63c9a750b82048d": "PRUEBA DE TRANSMISION VDSL ADICIONAL EN TERMINAL AREA",
            "5f1f5efb3198fe9c5ccef32d": "Radial en banqueta",
            "5f1f5efb3198fe9c5ccef32e": "Radial en cepa libre",
            "5f1f5efb3198fe9c5ccef32f": "Reparacion de tropezon en radial",
            "5f7f627c6ca87fa5ca92cd1c": "Cableado interior adicional para el dit con splitter con proteccion (extension)",
            "5f90e812f84ca4590ebc5946": "Migración TBA"
        }
        self.lkf_obj = lkf_obj

    """ Se valida que no exista otro registro con folio - telefono cargados en una tecnologia diferente """
    def eval_folio_in_other_tec(self):
        id_form_other_tec = self.map_forms_os_general[ self.form_id ].get('form_other_tec')
        
        record_found = self.cr.find_one({
            'form_id': id_form_other_tec, 
            'deleted_at': {'$exists': False}, 
            'folio': self.folio,
            f'answers.{self.field_id_telefono}': self.telefono
        }, {'folio': 1})
        
        if record_found:
            msg_error = "El folio ya fue cargado en una Tecnología diferente"
            return self.set_msg_error("folio", "Folio", msg_error)
    
    """ Se marca mensaje de error, si es desde la Carga de produccion se devuelve el mensaje, si no, se marca como Exception """
    def set_msg_error(self, fieldId, fieldLabel, msg, extra_fields={}):
        if self.from_carga_prod:
            return msg_error
        msg_error_app = {
            fieldId:{
                "msg": [msg], "label": fieldLabel, "error":[]
            }
        }
        msg_error_app.update( extra_fields )
        raise Exception(simplejson.dumps(msg_error_app))
        return False

    def get_system_record(self):
        return self.current_record.get('properties', {}).get('device_properties', {}).get('system', '')

    def validate_correct_folio(self):
        if not self.folio:
            return self.set_msg_error("folio", "Folio", "El folio es obligatorio")

        if not re.match(r"^[0-9]*$", self.folio):
            return self.set_msg_error("folio", "Folio", "El folio debe ser solo numeros y sin espacios en blanco")
        
        try:
            int( self.folio )
        except Exception as e:
            return self.set_msg_error("folio", "Folio", "El folio solo debe ser numerico")
        
        if len( str( self.folio ).strip() ) != 8:
            return self.set_msg_error("folio", "Folio", "El folio debe tener la logitud de 8 caracteres")
        
        return False

    def validate_fecha_correcta( self, lbl_fecha, field_fecha ):
        fecha_to_validate = self.answers.get(field_fecha)
        if not fecha_to_validate:
            return False
        try:
            if not self.validate_fecha_periodo_aceptado(fecha_to_validate):
                return self.set_msg_error( field_fecha, lbl_fecha, f'La {lbl_fecha} no es valida ya que es menor al 2019 o mayor al dia de hoy' )
        except:
            return self.set_msg_error( field_fecha, lbl_fecha, 'La fecha trae un formato incorrecto' )
        return False

    def validate_fecha_periodo_aceptado(self, fecha_to_validate):
        return self.p_utils.str_to_date('2019-01-01') <= self.p_utils.str_to_date( fecha_to_validate ) <= self.p_utils.str_to_date( self.p_utils.get_today() )
    
    def validate_clave_tecnico(self):
        # Se busca que el usuario este registrado en el Listado de Tecnicos
        query = {
            'form_id':self.form_id_listado_tecnicos, 
            'deleted_at' : {'$exists':False},
            'answers.5e17ceab6a4b343af06d200e': self.current_record['user_id']
        }
        record_tecnico = self.cr.find_one( query, { 'folio':1, 'answers':1 } )

        # Se marca error si no existe registro para el usuario que se esta procesando
        if not record_tecnico:
            return self.set_msg_error('f1054000a02000000000fb04', 'ID Usuario', 'Usuario no existe en Listado de Técnicos o el registro no tiene su ID.')
        
        # Antes se buscaba por el folio del registro con el dato de folio_tecnico, pero ahora ya no se hace
        # folio_tecnico = self.answers.get('f1054000a02000000000fb04')
        # if folio_tecnico and folio_tecnico[:2] == "T-":
        
        id_nombre_tecnico = '59e1280bb43fdd7cd6fc9f63' if self.is_os_cobre else 'f1054000a02000000000fa04'
        answers_tecnico = record_tecnico['answers']
        self.info_to_complete_record.update({
            id_nombre_tecnico: f"{answers_tecnico.get('f1216500a010000000000004', '')} {answers_tecnico.get('f1216500a010000000000005', '')} {answers_tecnico.get('f1216500a010000000000006', '')}",
            'f1054000a02000000000fb04': record_tecnico['folio']
        })
        return False
    
    def validate_correct_tipo_tarea(self, tipo_tarea):
        # Se revisa en el catalogo Tipos de Tarea Factibles
        mango_query = { 
            "selector": { 
                "answers": { 
                    '$and':[ 
                        { "5ec44fd1ac6a37c45828230a": { "$eq": tipo_tarea.upper() } },
                        { "5ec44ff4e065a60b1e282307": { "$in": ['COBRE', 'FIBRA'] } } 
                    ]
                }
            }
        }
        row_catalog = self.lkf_api.search_catalog(self.catalog_tipos_tarea_factibles, mango_query, jwt_settings_key='JWT_KEY_ADMIN')
        
        # Lista de tecnologias donde se encontró el Tipo de Tarea
        tecnologies_tipo_tarea = [ r['5ec44ff4e065a60b1e282307'].lower() for r in row_catalog ] if row_catalog else []

        # Si no hay tecnologias, puede ser que no este registrado en el catalogo
        if not tecnologies_tipo_tarea:
            return self.set_msg_error(self.field_id_tipo_tarea, 'Tipo de Tarea', 'El Tipo de Tarea no se encontró en el catálogo Tipos de Tarea Factibles')


        is_validacion_sistemas = self.answers.get(self.field_id_validacion_sistema, '') in ('pci-fibra', 'pci-cobre')
        
        # Se revisa que el Tipo de Tarea este registrado con la Tecnlogia de la OS
        if not self.tecnologia in tecnologies_tipo_tarea:
            if not is_validacion_sistemas:
                return self.set_msg_error(self.field_id_tipo_tarea, 'Tipo de Tarea', 'El Tipo de Tarea no se encontró en el catálogo Tipos de Tarea Factibles')

            # Si llega hasta aqui, quiere decir que es validacion de sistemas, por tanto se busca que este registrado como su tecnologia contraria
            map_tecnologia_contraria = {'fibra': 'cobre', 'cobre': 'fibra'}
            if not map_tecnologia_contraria[self.tecnologia] in tecnologies_tipo_tarea:
                return self.set_msg_error(self.field_id_tipo_tarea, 'Tipo de Tarea', 'El Tipo de Tarea no se encontró en el catálogo Tipos de Tarea Factibles')

        return False
    
    def validate_doctos(self):
        if not self.answers.get( self.id_field_os_pdf ) and not self.answers.get( self.id_field_memo ):
            return self.set_msg_error( self.id_field_os_pdf, 'Orden de Servicio Escaneada (PDF)', "Debe cargar su Orden de servicio escaneada", 
                extra_fields={ self.id_field_memo: {"msg": ["Si no tiene su OS escaneada, cargue el Campo Memo"], "label": "Metraje Adicional", "error": []} } )
        return False
    
    def validate_metraje(self, tipo_tarea):
        mts_bajante = int( self.answers.get( self.field_id_mts_bajante ) )
        mts_adicionales = self.answers.get( self.field_id_mts_adicionales, 0 )

        # Si hay metraje adicional es porque los metros bajante es 300
        if mts_adicionales and mts_bajante != 300:
            msg_error = "Se indica metraje adicional, por tanto, Metros Bajante deben ser 300"
            return self.set_msg_error( self.field_id_mts_bajante, 'Metros Bajante', msg_error, 
                extra_fields={ self.field_id_mts_adicionales: {"msg": [msg_error], "label": "Metraje Adicional", "error": []} } )

        # Metraje + Adicional no debe exceder el metraje aceptado
        mts_bajante_con_adicional = mts_bajante + mts_adicionales
        if mts_bajante_con_adicional > self.max_metraje_aceptado:
            msg_adicional = " + Adicional" if not self.is_os_cobre else ""
            return self.set_msg_error( self.field_id_mts_bajante, 'Metros Bajante', f"Metros Bajante{msg_adicional} no debe exceder {self.max_metraje_aceptado} Mts" )
        
        # Metraje cero solo en algunos tipos de tarea y aplica para fibra
        if not self.is_os_cobre:
            if mts_bajante_con_adicional == 0 and tipo_tarea not in self.p_utils.list_tareas_solo_vsi:
                msg_error = "No hay metraje registrado"
                return self.set_msg_error( self.field_id_mts_bajante, 'Metros Bajante', msg_error, 
                    extra_fields={ self.field_id_mts_adicionales: {"msg": [msg_error], "label": "Metraje Adicional", "error": []} } )

            if mts_bajante_con_adicional > 300 and not self.answers.get('5ff63afdde49fee5e218a474', '').strip():
                return self.set_msg_error( '5ff63afdde49fee5e218a474', 'Dirección', "Este campo es requerido" )

    def validate_only_queja(self):
        return {
            code: {
                "msg": ["Valor no permitido ya que el tipo de tarea es QUEJA"], "label": label, "error": []
            }
            for code, label in self.fields_invalid_queja.items()
            if self.answers.get(code)
        }

    def validate_terminal_optica(self, terminal_optica):
        if not terminal_optica:
            return False
        try:
            if len(terminal_optica) != 2:
                return self.set_msg_error(self.field_id_terminal_optica, "Terminal Optica", "Terminal Optica debe de contener 2 caracteres")
            
            regex = re.compile('[a-z]|[A-Z]')
            if not regex.findall(terminal_optica[0]):
                return self.set_msg_error(self.field_id_terminal_optica, "Terminal Optica", "El primer digito de la terminal optica debe de ser un caracter A-Z")
            
            if not terminal_optica[1].isdigit():
                return self.set_msg_error(self.field_id_terminal_optica, "Terminal Optica", "El segundo digito de la terminal optica debe de ser un numero 0-9")
        
        except Exception as e:
            print('pass sin terminal optica',e)
            raise Exception(e)
            return False
        return False

    def validaciones_generales(self):
        data_fields_cope = {}
        # El registro no puede existir en otra tecnologia
        record_other_tec = self.eval_folio_in_other_tec()
        if record_other_tec:
            return record_other_tec

        # Fecha de liquidacion requerida
        if not self.fecha_liquidacion:
            return self.set_msg_error( self.field_id_fecha_liquidacion, 'Fecha de Liquidacion', 'Debe agregar la fecha de Liquidacion' )

        # Se revisa que el registro no sea enviado desde Carga de Produccion o PIC
        if self.get_system_record() not in ('SCRIPT','PIC'):
            # Se revisa que el folio tenga la estructura correcta
            incorrect_folio = self.validate_correct_folio()
            if incorrect_folio:
                return incorrect_folio

            # Validaciones para el Distrito
            distrito = str( self.answers.get( self.field_id_distrito, '' ) ).strip()
            if len( distrito ) != 7:
                return self.set_msg_error( self.field_id_distrito, 'Distrito', f"Longitud del Distrito es diferente de 7 {distrito}" )

            # Validaciones para el Tipo de Tarea
            tipo_tarea = self.answers.get( self.field_id_tipo_tarea )
            if tipo_tarea == distrito:
                return self.set_msg_error( self.field_id_tipo_tarea, 'Tipo de Tarea', "El Tipo de Tarea no debe ser igual al Distrito" )


            # Se valida la longitud de digitos del telefono
            if len( str(self.telefono) ) != 10:
                return self.set_msg_error( self.field_id_telefono, 'Teléfono', "El teléfono debe tener 10 dígitos" )

            # Validaciones cuando el script no está siendo creado/editado desde el script
            if not self.record_is_cargado_desde_script:
                # Se valida el COPE y se complementa el answers con la información obtenida del catálogo
                list_copes = self.p_utils.get_cope_in_catalogo( self.cope.strip().replace('_', ' '), jwt_settings_key='JWT_KEY_ADMIN' )

                if not list_copes:
                    return self.set_msg_error( self.field_id_cope, 'COPE', "Error al encontrar el COPE, favor de revisar con soporte" )

                if len(list_copes) > 1:
                    return self.set_msg_error( self.field_id_cope, 'COPE', "El COPE se encontró más de una vez, favor de revisar con soporte" )

                data_cope = list_copes[0]
                data_fields_cope.update({
                    'f1054000a0100000000000b2': data_cope['division'],
                    'f1054000a0100000000000c2': data_cope['subdireccion'],
                    'f1054000a0100000000000a2': data_cope['area']
                })

                # Se valida los campos de Documentos
                incorrect_doctos = self.validate_doctos()
                if incorrect_doctos:
                    return incorrect_doctos

                # Si ya lleva el PDF pero no lleva la fecha de Carga, se debe integrar
                if self.answers.get(self.id_field_os_pdf) and not self.answers.get('60882afbf33276990d3f8edf'):
                    self.info_to_complete_record['60882afbf33276990d3f8edf'] = self.p_utils.get_date_now()

                # Se valida la clave del tecnico, solo aplica para Admin
                if self.lkf_obj.account_id == 1259:
                    invalid_clave = self.validate_clave_tecnico()
                    if invalid_clave:
                        return invalid_clave
            
            # Validaciones para la Fecha de Liquidacion
            fecha_liquidacion_no_accepted = self.validate_fecha_correcta('Fecha Liquidada', self.field_id_fecha_liquidacion)
            if fecha_liquidacion_no_accepted:
                return fecha_liquidacion_no_accepted

            """
            Validaciones que hará si la carga NO fue desde PIC
            """
            if not self.record_is_cargado_desde_pic:

                # Se valida el tipo de tarea
                incorrect_tipo_tarea = self.validate_correct_tipo_tarea(tipo_tarea)
                if incorrect_tipo_tarea:
                    return incorrect_tipo_tarea

                # Se valida el metraje
                incorrect_metraje = self.validate_metraje(tipo_tarea)
                if incorrect_metraje:
                    return incorrect_metraje

                # Se requiere el Tipo de Instalacion
                if not self.tipo_instalacion:
                    return self.set_msg_error( self.field_id_tipo_instalacion, 'Tipo de Instalacion', 'Debe seleccionar un Tipo de Instalacion' )
            
            """
            Validaciones propias de Cobre
            """
            default_queja = None
            if self.is_os_cobre:
                if self.answers.get('609bf813b3f4e5c00cf76ee0', 0) > 1:
                    return self.set_msg_error("609bf813b3f4e5c00cf76ee0", "Línea de cliente básica de 1 par (bajante) (sin modem)", "Valor no permitido")

                # Tipo de Tarea y Tipo de OS
                tipo_os_in_tarea = tipo_tarea[:2].upper()

                # Se revisa si el folio corresponde a una QUEJA, entonces hay campos que no se aceptan con valor
                if tipo_os_in_tarea in ('QI','RI','EI'):
                    default_queja = 1
                    fields_error_queja = self.validate_only_queja()
                    if fields_error_queja:
                        raise Exception(simplejson.dumps(fields_error_queja))
                
                # Se valida que el tipo de OS sean los dos primeros digitos del Tipo de Tarea
                tipo_os = self.answers.get(self.field_id_os, '')
                if tipo_os != tipo_os_in_tarea:
                    return self.set_msg_error(self.field_id_os, "Tipo de OS", "El Tipo de OS deben ser los dos primeros dígitos del Tipo de Tarea")

            else:
                # Validaciones propias de FTTH
                alfanumerico = self.answers.get(self.field_id_alfanumerico)
                if alfanumerico and len(alfanumerico) != 12:
                    return self.set_msg_error(self.field_id_alfanumerico, "Alfanumerico", "Alfanumerico debe tener longitud de 12 caracteres")

                if not self.record_is_cargado_desde_pic:
                    
                    # Valida ONT NUMERICO
                    if self.form_id == self.form_id_os_ftth_sur:
                        ontnumerico = self.answers.get('f1054000a020000000000aa3')
                        if ontnumerico and len( str( ontnumerico ) ) not in (11, 12):
                            return self.set_msg_error("f1054000a020000000000aa3", "ONT Numerico", "Longitud de ONT NUMERICO es diferente de 11 o 12 dígitos")

                    # Validar Fecha Reportado
                    fecha_reporte_no_accepted = self.validate_fecha_correcta('Fecha Reportado', 'f1054000a030000000000e14')
                    if fecha_reporte_no_accepted:
                        return fecha_reporte_no_accepted

                    # Validar Fecha de Asignacion
                    fecha_asignacion_no_accepted = self.validate_fecha_correcta('Fecha de Asignacion', 'f1054000a02000000000fa01')
                    if fecha_asignacion_no_accepted:
                        return fecha_asignacion_no_accepted

                    # Se valida la Terminal Optica
                    terminal_optica = self.answers.get(self.field_id_terminal_optica)
                    terminal_optica_no_accepted = self.validate_terminal_optica(terminal_optica)
                    if terminal_optica_no_accepted:
                        return terminal_optica_no_accepted
                    
                    # Valida Puerto
                    puerto = self.answers.get('f1054000a020000000000aa2')
                    if puerto:
                        puerto = str(puerto)
                        if not ( len(puerto) == 1 and puerto.isdigit() ):
                            return self.set_msg_error("f1054000a020000000000aa2", "Puerto", "El Puerto debe ser solo un dígitos numérico")
            
            """
            # Asignacion y edicion de registro existente, o bien, se revisa si hay permisos para crear el registro
            """

            print(f'self.from_carga_prod = {self.from_carga_prod} -- self.record_is_cargado_desde_script = {self.record_is_cargado_desde_script}')

            if not self.from_carga_prod and not self.record_is_cargado_desde_script:
                # Revisar si existe el registro
                existing_record = self.p_utils.get_records_existentes(self.form_id, self.folio, extra_params={f'answers.{self.field_id_telefono}': self.telefono})
                
                # Consulta que el folio este en la forma de autorizaciones
                autorizaciones_carga_folio = self.p_utils.find_folio_autorizado( self.folio, self.telefono, data_cope['division'], self.tecnologia)
                folio_autorizado = 'pic' in autorizaciones_carga_folio or 'pisa/verde_o_pisa/plex' in autorizaciones_carga_folio

                # Aplica para Fibra
                if not self.is_os_cobre:
                    # Hay algunos tipos de tarea donde solo se paga el VSI por lo que no se tomará en cuenta el metraje que el contratista haya cargado
                    if existing_record:
                        info_record = existing_record[ self.folio ]
                        tipo_tarea = info_record.get('answers', {}).get( self.field_id_tipo_tarea )
                    if tipo_tarea in self.p_utils.list_tareas_solo_vsi:
                        self.info_to_complete_record.update({
                            self.field_id_mts_bajante: '0',
                            self.field_id_mts_adicionales: 0,
                            self.field_id_ftth_vsi: 'vsi'
                        })

                if default_queja:
                    self.info_to_complete_record['5f90e812f84ca4590ebc5947'] = default_queja

                if existing_record:
                    info_record = existing_record[self.folio]
                    
                    # Si el registro ya tiene una conexion no puede ser cargado por otro contratista
                    print(f"conexion record = {info_record.get('connection_id')} Cuenta padre = {self.parent_id}")
                    if info_record.get('connection_id') and info_record['connection_id'] != self.parent_id:
                        return self.set_msg_error('folio', 'Folio', 'Este folio ya fue cargado por otro contratista')

                    
                    if not folio_autorizado:
                        '''
                        >> Si el folio no esta autorizado por la forma, realiza la validacion de la fecha de liquidacion
                        '''
                        if 'fecha_de_liquidacion' not in autorizaciones_carga_folio:
                            fecha_liquidada = info_record.get('answers',{}).get(self.field_id_fecha_liquidacion,'')
                            date_fecha_liquidada = self.p_utils.str_to_date(fecha_liquidada)
                            diff_dates = datetime.now() - date_fecha_liquidada
                            dias_transcurridos = diff_dates.days
                            is_cfe = info_record['answers'].get(self.field_id_proyecto, '') == 'cfe'
                            if dias_transcurridos > 14 and not autorizaciones_carga_folio and not is_cfe:
                                info_record['answers'][ self.field_id_descuento_x_desfase ] = 'sí'
                        
                        '''
                        >> Se consulta si el contratista tiene permisos sobre el expediente
                        '''
                        if 'expediente' not in autorizaciones_carga_folio:
                            tecnico_pic = info_record.get('answers', {}).get(self.field_id_tecnico_pic, '')
                            if tecnico_pic.lower().strip() == 'pisaplex':
                                permiso_expediente_contratista = 'si'
                            else:
                                permisos_contratista = self.p_utils.get_permisos_contratista_from_catalog(self.parent_id)
                                permiso_expediente_contratista = permisos_contratista.get('expediente')
                            
                            if not permiso_expediente_contratista or permiso_expediente_contratista.lower() == 'no':
                                # Se revisa que el expediente le pertenezca al contratista
                                num_expediente = info_record['answers'].get( self.field_id_expediente_tecnico, '' )
                                is_in_listado_tecnicos = self.p_utils.get_expedientes_contratistas(
                                    list_expedientes=[int(num_expediente)], 
                                    with_item_idUser=True, 
                                    filter_id_contratista=self.lkf_obj.account_id
                                )
                                if not is_in_listado_tecnicos:
                                    return self.set_msg_error('folio', 'Folio', 'No se pudo crear el registro de OS. Favor de revisar con soporte')

                    # Se asigna el registro al contratista
                    new_record = '/api/infosync/form_answer/' + str(info_record['_id']) +'/'
                    response_assign = self.lkf_api.assigne_connection_records( self.parent_id, [new_record,])
                    
                    """
                    # Se actualiza el registro con la informacion que se fue agregando durante el proceso
                    """
                    info_record['answers'].pop(self.field_id_cargado_desde_script, None)
                    
                    if not info_record['answers'].get('f1054000a0100000000000b2'):
                        info_record['answers'].update(data_fields_cope)
                    
                    info_record['answers'].update(self.info_to_complete_record)
                    
                    """
                    # Se hace el merge del registro con la informacion que se integro
                    """
                    sys.stdout.write(simplejson.dumps({
                        'status': 101,
                        'merge': {
                            'primary': False,
                            'replace': False,
                            'answers': info_record['answers']
                        },
                        'id': str(info_record['_id']),
                    }))
                else:
                    # Se busca si esta registrado como PSR
                    os_in_psr = self.p_utils.review_psr_exists(self.folio, self.telefono)
                    if os_in_psr:
                        print(f"OS se encontro en PSR {os_in_psr['folio']}")
                        answers_psr = os_in_psr.get('answers', {})
                        self.info_to_complete_record.update({
                            self.field_id_cope: answers_psr.get(self.field_id_cope).lower().replace(' ', '_'), # cope
                            'f1054000a0100000000000a2': answers_psr.get('66eb90ae4a3470f509f0129e').lower().replace(' ', '_'), # area
                            'f1054000a0100000000000c2': answers_psr.get('66eb90ae4a3470f509f0129d').lower().replace(' ', '_'), # subdireccion
                            'f1054000a0100000000000b2': answers_psr.get('66eb90ae4a3470f509f0129c').lower().replace(' ', '_'), # Division
                            self.field_id_tecnico_pic: answers_psr.get(self.field_id_tecnico_pic), #: tecnico,
                            self.field_id_telefono: answers_psr.get(self.field_id_telefono), #: telefono
                            self.field_id_expediente_tecnico: answers_psr.get('f1054000a0100000000000d6'),
                            self.field_id_tipo_tarea: answers_psr.get('f1054000a010000000000021'),
                            self.field_id_fecha_liquidacion: answers_psr.get('66eb905a9abafdd48af01241'),
                            self.field_id_proyecto: 'psr'
                        })
                        if self.tecnologia == 'fibra':
                            self.info_to_complete_record.update({
                                self.field_id_distrito: answers_psr.get('f1054000a0100000000000d5'),
                                self.field_id_alfanumerico: answers_psr.get(self.field_id_alfanumerico)
                            })
                        folio_autorizado = True
                        resp_update_psr = self.lkf_api.patch_multi_record(
                            {'6670a0a6fe5560837d1cc9bc': 'autorizado'}, 
                            self.p_utils.FORM_ID_PSR, 
                            folios=[ os_in_psr['folio'] ], 
                            threading=True
                        )

                    # No existe el registro
                    if not folio_autorizado:
                        # Si el folio no esta autorizado por la forma, consulta si el contratista esta autorizado para carga
                        permisos_contratista = self.p_utils.get_permisos_contratista_from_catalog(self.parent_id)
                        autorizar_carga = permisos_contratista.get('carga')
                        folio_autorizado = False if (not autorizar_carga or autorizar_carga.lower() == 'no') else True
                    
                    if folio_autorizado:
                        info_to_add = {}
                        info_to_add.update(data_fields_cope)
                        info_to_add.update(self.info_to_complete_record)

                        sys.stdout.write(simplejson.dumps({
                            'status': 206,
                            'merge':{
                                'primary': False,
                                'replace': False,
                                'answers': info_to_add
                            },
                            'replace': self.answers
                        }))
                    else:
                        return self.set_msg_error('folio', 'Folio', 'Verifica que tu folio sea el correcto y se encuentre liquidado completado en PIC Movil')