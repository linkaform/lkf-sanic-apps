# -*- coding: utf-8 -*-

import sys, simplejson
from datetime import datetime, timedelta, date
from copy import deepcopy

from lkf_addons.inspeccion_hoteleria.app import Inspeccion_Hoteleria


class Inspeccion_Hoteleria(Inspeccion_Hoteleria):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)

        self.field_id_status = '67f0844734855c523e139132'
        #formas
        self.REVISON_HABITACION = self.lkm.form_id('revisin_de_habitaciones_maestro','id')
        
        #Formas Hoteles
        self.HI_PARQUE_FUNDIDORA = self.lkm.form_id('revisin_de_habitaciones_hi_parque_fundidora','id')
        self.CROWNE_PLAZA_TORREN = self.lkm.form_id('revisin_de_habitaciones_crowne_plaza_torren','id')
        self.TRAVO = self.lkm.form_id('revisin_de_habitaciones_travo','id')
        self.HIE_TECNOLGICO = self.lkm.form_id('revisin_de_habitaciones_hie_tecnolgico','id')
        self.WYNDHAM_GARDEN_MCALLEN = self.lkm.form_id('revisin_de_habitaciones_wyndham_garden_mcallen','id')
        self.ISTAY_VICTORIA = self.lkm.form_id('revisin_de_habitaciones_istay_victoria','id')
        self.HIE_TORREN = self.lkm.form_id('revisin_de_habitaciones_hie_torren','id')
        self.HILTON_GARDEN_SILAO = self.lkm.form_id('revisin_de_habitaciones_hilton_garden_silao','id')
        self.MS_MILENIUM = self.lkm.form_id('revisin_de_habitaciones_ms_milenium','id')
        self.ISTAY_MONTERREY_HISTRICO = self.lkm.form_id('revisin_de_habitaciones_istay_monterrey_histrico','id')
        self.HIE_GUANAJUATO = self.lkm.form_id('revisin_de_habitaciones_hie_guanajuato','id')
        self.HIE_SILAO = self.lkm.form_id('revisin_de_habitaciones_hie_silao','id')
        self.ISTAY_CIUDAD_JUREZ = self.lkm.form_id('revisin_de_habitaciones_istay_ciudad_jurez','id')
        self.CROWNE_PLAZA_MONTERREY = self.lkm.form_id('revisin_de_habitaciones_crowne_plaza_monterrey','id')
        self.HIE_GALERIAS = self.lkm.form_id('revisin_de_habitaciones_hie_galerias','id')
        self.HOLIDAY_INN_TIJUANA = self.lkm.form_id('revisin_de_habitaciones_holiday_inn_tijuana','id')

        self.f.update({
            'dias_proceso':'680bb9ae683baa875e7baa22',
            'status':'67f0844734855c523e139132'
            })

        self.form_data = {}

        self.exclude_field_ids =[
            '67ffed2115a48b68c37ba99e',
            '67f0844734855c523e1390d7'
        ]
        