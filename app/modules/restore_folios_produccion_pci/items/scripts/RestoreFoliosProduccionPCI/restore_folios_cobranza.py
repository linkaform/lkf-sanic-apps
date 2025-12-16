# -*- coding: utf-8 -*-
"""
# Script que Eliminará la OC que se le indique, tomará los folios de OS, buscará sus liberaciones y restaura sus estatus a "liberado"
# Forma : Restaurar folios de OC y OS ( 71639 )
"""
import sys, simplejson
from bson.objectid import ObjectId
from restore_folios_produccion_pci_utils import RestoreFoliosProduccion
from account_settings import *

class RestoreFoliosCobranza( RestoreFoliosProduccion ):
    
    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
    
    def get_values_pic( self, ans, ar_not_update ):
        """
        Restaura las Ordenes de Servicio a solo la informacion de PIC
        """
        news_values = {
            '5e17674c50f45bac939c932e': 'sí', # Cargado desde script
            '5eb0326a9e6fda7cb11163f1': 'sí', # Cargado desde PIC
            'f1054000a030000000000012': 'pendiente', # Estatus de Cobranza PC
            'f1054000a030000000000013': 'en_proceso', # Estatus Cobranza Contratista
            'f1054000a030000000000002': 'liquidada' # Estatus de Orden
        }
        for id_field in ar_not_update:
            if ans.get( id_field, False ):
                news_values.update( {id_field: ans[id_field]} )
        return news_values

    def restore_os_to_pic( self, form_id_os, query_to_os, tecnologia ):
        ar_not_update = [
            'f1054000a010000000000002','f1054000a0100000000000a2','f1054000a0100000000000c2','f1054000a0100000000000b2',
            '5eb091915ae0d087df1163de','f1054000a010000000000005','5efa00c62542e523f391c636'
        ]
        
        if tecnologia == 'fibra':
            ar_not_update.extend( ['f1054000a0100000000000d6','f1054000a010000000000021','f1054000a02000000000fa02','f1054000a0100000000000d5','f1054000a0200000000000a3'] )
        else:
            ar_not_update.extend( ['f1054000a010000000000007','f1054000a0100000000000a4','f1054000a0100000000000a1','5a1eecfbb43fdd65914505a1','f1054000a010000000000003'] )
        #dict_recrods_os = p_utils.get_records_existentes( form_id_os, fols )
        records_os = cr.find(query_to_os, {'folio': 1, 'answers': 1})
        for record_os in records_os:
            print('Reestableciendo folio de OS: ',record_os['folio'])
            new_answers = self.get_values_pic( record_os.get('answers', {}), ar_not_update )
            res_update_fol = cr.update_one(
                { 'form_id': form_id_os, 'deleted_at': {'$exists': False}, '_id': ObjectId( str(record_os['_id']) ) }, \
                { '$set': { 'answers': new_answers } }\
            )
            print('+ res_update_fol=',res_update_fol)

    def get_ocs_with_folios(self, folios, telefonos, form_id_oc):
        """
        Regresa las Órdenes de Compra donde se encontraron los folios de OS
        """
        query = {
            'form_id': form_id_oc,
            'deleted_at': {'$exists': False},
            'answers.f1962000000000000000fc10.f19620000000000000001fc1': {'$in': folios},
            'answers.f1962000000000000000fc10.f19620000000000000001fc2': {'$in': telefonos}
        }
        print('query=',query)
        select_columns = { 'folio': 1, 'user_id': 1, 'form_id': 1, 'answers': 1, '_id': 1, 'connection_id': 1 }
        records_oc = cr.find(query, select_columns)
        dict_records_oc = {rec.get('folio'): rec for rec in records_oc}
        dict_folios_by_oc = { fol_oc: {\
            int(f.get('f19620000000000000001fc2', 0)): f.get('f19620000000000000001fc1', '') for f in dict_records_oc[fol_oc].get('answers', {}).get('f1962000000000000000fc10', [])\
        } for fol_oc in dict_records_oc }
        return dict_records_oc, dict_folios_by_oc
    
    def get_telefonos_en_oc(self, folios, telefonos, form_id_oc):
        list_telefonos = list(telefonos.keys())
        ocs_with_folios, folios_by_oc = self.get_ocs_with_folios(folios, list_telefonos, form_id_oc)
        return ocs_with_folios, folios_by_oc, list_telefonos

    def validar_folios_en_oc(self, ocs_with_folios, leyenda_oc, process_new_oc):
        if ocs_with_folios and process_new_oc:
            return 'No se puede continuar con el proceso ya que algunos de los folios están en Orden de Compra'
        if ocs_with_folios and not leyenda_oc:
            return 'Algunos de los folios están en Orden de Compra favor de agregar una Leyenda'
        return None

    def mapear_folios_por_oc(self, telefonos, folios_by_oc):
        dict_fols_in_oc = {}
        for telefono, folio in telefonos.items():
            oc_found = 'no_oc'
            for oc, folios_lib in folios_by_oc.items():
                # Reviso si el telefono tiene el mismo folio en la OC y en el excel
                if folios_lib.get(telefono, '') == folio:
                    oc_found = oc
                    break
            dict_fols_in_oc.setdefault(oc_found, []).append(folio)
        return dict_fols_in_oc

    def procesar_oc(self, dict_fols_in_oc, ocs_with_folios, telefonos, leyenda_oc, dict_records_file, current_record_folio):
        dict_libs_by_conexiones = {}
        error_records = []

        for fol_oc_found, fols_libs_found in dict_fols_in_oc.items():
            data_oc = ocs_with_folios.get(fol_oc_found, False)
            folios_telefonos = {}
            if data_oc:
                print(f'======== Procesando OC: {fol_oc_found} ========')
                data_oc['properties'] = self.get_metadata_properties("restore_folios_cobranza.py","Restaura folios de OS a info de PIC",
                    process="Restaurar folios de OS",folio_carga=current_record_folio)
                
                for infoFolio in data_oc.get('answers', {}).get('f1962000000000000000fc10', []):
                    fol = infoFolio['f19620000000000000001fc1']
                    if fol in fols_libs_found:
                        tel = int(infoFolio['f19620000000000000001fc2'])
                        if telefonos.get(tel, '') != fol:
                            print('No coinciden folio y telefono')
                            continue
                        infoFolio['f19620000000000000001fc1'] = f"{fol} {leyenda_oc}"
                        folios_telefonos[f'{fol}{tel}'] = fol
                response_update_oc = lkf_api.patch_record(data_oc, jwt_settings_key="USER_JWT_KEY")
                print('+ response_update_oc=', response_update_oc)
                if response_update_oc.get("status_code", 0) > 300:
                    error_records.extend([
                        dict_records_file[fol_lib] + ["No se pudo actualizar la Orden de Compra"]
                        for fol_lib in fols_libs_found
                    ])
                else:
                    conexion = data_oc.get("connection_id", 0)
                    dict_libs_by_conexiones.setdefault(conexion, {}).update(folios_telefonos)

        return dict_libs_by_conexiones, error_records
    
    def restaura_os(self, folios, form_id_oc, form_id_lib, form_id_os, records, leyenda_oc, current_record_folio, tecnologia, telefonos, process_new_oc=False):
        """
        Restaura folios de Orden de Servicio a solo información de PIC
        """
        dict_records_file = { self.strip_special_characters(rec[0]): rec for rec in records }
        
        # Busco los folios que estén en alguna OC
        ocs_with_folios, folios_by_oc, list_telefonos = self.get_telefonos_en_oc(folios, telefonos, form_id_oc)

        error = self.validar_folios_en_oc(ocs_with_folios, leyenda_oc, process_new_oc)
        if error:
            return error
        
        # Preparo un diccionario con los folios de las Órdenes de Compra y los folios que se encontraron        
        dict_fols_in_oc = self.mapear_folios_por_oc(telefonos, folios_by_oc)
        print('dict_fols_in_oc=',dict_fols_in_oc)

        # Proceso las Ordenes de Compra para modificar los folios que se encontraron
        dict_libs_by_conexiones, error_records = self.procesar_oc(
            dict_fols_in_oc, ocs_with_folios, telefonos, leyenda_oc, dict_records_file, current_record_folio
        )
                    
        # Consulto los folios que no están en orden de compra para agregarlos al diccionario y se procesen todos
        dict_fols_not_in_oc = p_utils.get_records_existentes( form_id_os, dict_fols_in_oc.get('no_oc', []), extra_params={\
            'connection_id': {'$exists': True}, \
            'answers.f1054000a010000000000005': {'$in': list_telefonos}\
        }, os_with_phone=True )

        for fol_rec_not_oc, rec_not_oc in dict_fols_not_in_oc.items():
            conexion_rec = rec_not_oc['connection_id']
            dict_libs_by_conexiones.setdefault(conexion_rec, {}).update({ fol_rec_not_oc: rec_not_oc['folio'] })
        
        
        # Elimino las Liberaciones generadas y restauro los folios de OS
        print('dict_libs_by_conexiones=',dict_libs_by_conexiones)
        for id_conexion, dict_fols in dict_libs_by_conexiones.items():

            # Para asegurar que se actualicen los registros que deben ser, consulto su id en la BD con el folio y el telefono
            _temp_telefonos = [ int(_t[8:]) for _t in list(dict_fols.keys()) ]
            _fols = list( dict_fols.values() )
            
            _recs_os = self.get_records(form_id_os, _fols, {'answers.f1054000a010000000000005': {'$in': _temp_telefonos}}, ['folio', 'answers.f1054000a010000000000005'])
            
            list_ids_records = []
            for _r in _recs_os:
                _foliotelefono = '{}{}'.format( _r['folio'], _r['answers'].get('f1054000a010000000000005') )
                if dict_fols.get( _foliotelefono ):
                    list_ids_records.append( ObjectId( str( _r['_id'] ) ) )
            
            # Para las liberaciones primero reviso si existen registros con folio tipo foliotelefono, los que no se encuentren pues los busco solo por el folio
            _recs_lib = self.get_records(form_id_lib, list( dict_fols.keys() ), select_columns=['folio'])
            list_fols_records_lib = []
            libs_found = []
            for _rl in _recs_lib:
                list_fols_records_lib.append( _rl['folio'] )
                libs_found.append( dict_fols[ _rl['folio'] ] )
            libs_only_fol = list( set(_fols) - set(libs_found) )
            list_fols_records_lib += libs_only_fol

            print('---------- Restaurando folios del contratista', id_conexion)
            query_to_libs = {'form_id':form_id_lib, 'folio':{'$in': list_fols_records_lib}, 'deleted_at':{'$exists':False}}
            query_to_os = {'form_id':form_id_os,'_id':{'$in': list_ids_records}, 'deleted_at':{'$exists':False}}

            if process_new_oc:
                # restauro los estatus de las OS
                reset_os = cr.update_many( query_to_os, 
                    {'$set':{'answers.f1054000a030000000000013': 'por_facturar', 'answers.f1054000a030000000000012': 'paco'}})
                print('+ reset_os=',reset_os)
                
                reset_os_conn = self.delete_record_contratista( id_conexion, form_id_os, [], process_new_oc=process_new_oc, update_by_ids=list_ids_records )
                
                reset_libs = cr.update_many( query_to_libs, {'$set':{'answers.f2361400a010000000000005': 'liberado'}})
                print('+ reset_libs=',reset_libs)
                
                continue
            
            # Borro las liberaciones
            res_remove_libs = cr.delete_many( query_to_libs )
            print('+ res_remove_libs=',res_remove_libs)
            
            print('Borando las OS de la BD del contratista')
            res_remove_os_contratista = self.delete_record_contratista( id_conexion, form_id_os, [], update_by_ids=list_ids_records )
            
            print('Quitando la conexion')
            unset_conn = cr.update_many( query_to_os, {"$unset":{'connection_id':''}})
            print('+ unset_conn=',unset_conn)
            
            self.restore_os_to_pic( form_id_os, query_to_os, tecnologia )
        
        return error_records

    def get_ocs(self, folios_oc, form_id_oc):
        """
        Buscar la OC según el folio
        """
        records_oc = self.get_records(form_id=form_id_oc, folio=folios_oc, select_columns=['answers','folio','connection_id','_id'])
        return {r.get('folio'): r for r in records_oc}

    def delete_record_contratista(self, id_connection_assigned, form_id, folio, process_new_oc=False, update_by_ids=None):
        """
        Se elimina el registro en la BD del contratista
        """
        try:
            colection_connection = CollectionConnection(id_connection_assigned, settings)
            cr_contratista = colection_connection.get_collections_connection()

            query_to_remove = { 'form_id': form_id, 'deleted_at': { '$exists': False } }

            if update_by_ids:
                query_to_remove['_id'] = {'$in': update_by_ids}
            else:
                query_to_remove['folio'] = {'$in': folio} if isinstance(folio, list) else folio
            
            if process_new_oc:
                reset_os_conn = cr_contratista.update_many( 
                    query_to_remove, 
                    {'$set':{'answers.f1054000a030000000000013': 'por_facturar', 'answers.f1054000a030000000000012': 'paco'}}
                )
                print('+ reset_os_conn=',reset_os_conn)
                return {'status_code': 202}

            rmv_contratista = cr_contratista.delete_many(query_to_remove)
            print('+ res bd contratista=',rmv_contratista)
            return {'status_code': 202}
        except Exception as e:
            print('++++++++++++++++ error en el Contratista:',str(e))
            return {'status_code': 400, 'msg': str(e)}

    def eliminar_ocs(self, folios, form_id_oc, form_id_lib, records):
        """
        Elima las Ordenes de Compra y restaura Liberaciones
        """
        error_records = []
        libs_to_restore_status = {}
        records_ordenes = self.get_ocs( folios, form_id_oc )
        print('records_ordenes=',records_ordenes)
        for rec in records:
            fol = self.strip_special_characters(rec[0])
            if fol not in records_ordenes:
                error_records.append(rec + ["No se econtró el registro de Orden de Compra",])
                continue
            info_oc = records_ordenes[ fol ]
            id_record_oc = str(info_oc.get('_id'))
            print(f'======== Eliminando oc {fol} id_record {id_record_oc} ========')
            
            # Se borra el registro de la BD de PCI
            response_delete = p_utils.delete_record(id_record=id_record_oc)
            if response_delete > 300:
                error_records.append(rec + ["Ocurrió un error al eliminar el registro",])
                continue

            # Si el registro se borró correctamente, se borra del contratista
            connection_id = info_oc.get('connection_id',0)
            print('Borrando la OC de la BD del contratista',connection_id)
            if connection_id and connection_id != 1259:
                resp_remove_connection = self.delete_record_contratista(connection_id, form_id_oc, fol)
                status_code_remove_connection = resp_remove_connection.get('status_code')
                if status_code_remove_connection == 400:
                    error_records.append(rec+['Eliminado de PCI pero Ocurrió error en la BD del Contratista'])
                    continue
            
            libs_to_restore_status.update({ '{}{}'.format( s.get('f19620000000000000001fc1', ''), s.get('f19620000000000000001fc2', '') ): s.get('f19620000000000000001fc1', '') \
                for s in info_oc.get('answers', {}).get('f1962000000000000000fc10', []) \
                if s.get('f19620000000000000001fc1', False)
            })

        response_update_libs = cr.update_many({
            'form_id': form_id_lib,
            'deleted_at': {'$exists': False},
            'folio': {'$in': list(libs_to_restore_status.keys())}
        },{'$set': {'answers.f2361400a010000000000005': 'liberado'}})
        print('+ response_update_libs=',response_update_libs)
        
        return error_records

    def procesar_folios(self):
        tecnologia = current_record.get('answers', {}).get('60c0d66a88affe8ff3ef3292', '')
        division = current_record.get('answers', {}).get('60c0d66a88affe8ff3ef3293', '')
        form_id_os, form_id_lib, form_id_oc = p_utils.get_id_os(division, tecnologia)

        file_url = current_record.get('answers', {}).get('60c0d66a88affe8ff3ef3291', {}).get('file_url', '')
        header, records = p_utils.read_file( file_url )

        folios = [ self.strip_special_characters(rec[0]) for rec in records if rec[0] ]
        if proceso in ['restaurar_folios_de_orden_de_servicio', 'restaurar_liberaciones_para_nueva_oc']:
            telefonos = { int(rec[1]): str(rec[0]) for rec in records if rec[1] }

        if proceso == 'eliminar_oc_y_restaurar_liberaciones':
            # Ejecuto el proceso que elima las OC y restaura estatus de las liberaciones
            error_records = self.eliminar_ocs(folios, form_id_oc, form_id_lib, records)
        elif proceso == 'restaurar_folios_de_orden_de_servicio':
            # Ejecuto el proceso para restaurar folios de Orden de Servicio a Solo PIC
            leyenda_oc = current_record.get('answers', {}).get('60c13944ab4f42193ee6c30f', '').strip()
            if len( header ) < 2:
                return p_utils.set_status_proceso(current_record, record_id, 'error', 
                    msg='Para este proceso se necesita el Telefono en la columna B', 
                    field_status='60c0d66a88affe8ff3ef3294', field_msg='60c18efba467daa9c9e6c31a')
            
            error_records = self.restaura_os(folios, form_id_oc, form_id_lib, form_id_os, records, leyenda_oc, self.folio, tecnologia, telefonos)
            if isinstance(error_records, str):
                return p_utils.set_status_proceso(current_record, record_id, 'error', msg=error_records, 
                    field_status='60c0d66a88affe8ff3ef3294', field_msg='60c18efba467daa9c9e6c31a')

        elif proceso == 'restaurar_liberaciones_para_nueva_oc':
            # Ejecuto proceso para restaurar estatus de las liberaciones y OS y así vuelvan a salir en una OC diferente
            error_records = self.restaura_os(folios, form_id_oc, form_id_lib, form_id_os, records, '', self.folio, tecnologia, telefonos, process_new_oc=True)
            if isinstance(error_records, str):
                return p_utils.set_status_proceso(current_record, record_id, 'error', msg=error_records, 
                    field_status='60c0d66a88affe8ff3ef3294', field_msg='60c18efba467daa9c9e6c31a')
        
        current_record['answers']['60c0d66a88affe8ff3ef3294'] = 'terminado'
        if error_records:
            current_record['answers']['60c0d66a88affe8ff3ef3294'] = 'error'
            current_record['answers'].update( p_utils.upload_error_file(header + ['error',], error_records, current_record['form_id'], file_field_id='60c0d66a88affe8ff3ef3295') )
        lkf_api.patch_record(current_record, record_id,jwt_settings_key='USER_JWT_KEY')


if __name__ == "__main__":
    print("--- --- --- Se empieza restaurar Orden de Compra / Orden de Servicio --- --- ---")

    lkf_obj = RestoreFoliosCobranza(settings, sys_argv=sys.argv)
    lkf_obj.console_run()

    current_record = lkf_obj.current_record
    record_id =  lkf_obj.record_id
    lkf_api = lkf_obj.lkf_api
    cr = lkf_obj.cr

    from pci_get_connection_db import CollectionConnection

    from pci_base_utils import PCI_Utils
    p_utils = PCI_Utils(cr=cr, lkf_api=lkf_api, net=lkf_obj.net, settings=settings, lkf_obj=lkf_obj)

    proceso = lkf_obj.answers.get('60c0d66a88affe8ff3ef3294', '')
    p_utils.set_status_proceso(current_record, record_id, 'procesando', msg='', field_status='60c0d66a88affe8ff3ef3294', field_msg='60c18efba467daa9c9e6c31a' )

    lkf_obj.procesar_folios()