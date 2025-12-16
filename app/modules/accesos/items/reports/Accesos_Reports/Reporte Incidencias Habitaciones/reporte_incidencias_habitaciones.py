#-*- coding: utf-8 -*-
import sys, simplejson, time
from datetime import datetime, timedelta, date
from linkaform_api import settings, network, utils, base
from account_settings import *
import re
import calendar
from linkaform_api import mongo_util
from collections import defaultdict
from collections import Counter

#Se agrega path para que obtenga el archivo de Stock de este modulo
sys.path.append('/srv/scripts/addons/modules/accesos/items/scripts/Accesos')
from accesos_utils import Accesos

def get_first_filter():
    selector = {"_id": {"$gt": None}}

    fields = ["_id", f"answers.{script_obj.mf['ubicacion']}"]

    mango_query = {
        "selector": selector,
        "fields": fields,
        "limit": 100
    }

    try:
        row_catalog = script_obj.lkf_api.search_catalog(script_obj.UBICACIONES_CAT_ID, mango_query)
        data_formateada = format_first_filter(row_catalog)
        return data_formateada
    except Exception as e:
        print(f"Error al realizar la búsqueda en get_first_filter: {e}")

def format_first_filter(data_to_format):
    format_list = []
    for ubicacion in data_to_format:
        format_list.append({
            "ubicacion": ubicacion.get(script_obj.mf['ubicacion'])
        })
    return format_list

def get_all_rooms(ubicacion=''):
    selector = {}

    selector.update({f"answers.{script_obj.mf['ubicacion']}": ubicacion})

    if not selector:
        selector = {"_id": {"$gt": None}}

    fields = ["_id", f"answers.{script_obj.mf['nombre_area']}"]

    mango_query = {
        "selector": selector,
        "fields": fields,
        "limit": 1000
    }

    try:
        row_catalog = script_obj.lkf_api.search_catalog(script_obj.AREAS_DE_LAS_UBICACIONES_CAT_ID, mango_query)
        res, cantidad = format_get_all_rooms(row_catalog)
        return res, cantidad
    except Exception as e:
        print(f"Error al realizar la búsqueda en get_all_rooms: {e}")

def format_get_all_rooms(data):
    rooms = []
    for room in data:
        if "HABITACIÓN " in room.get(script_obj.mf['nombre_area']):
            rooms.append({
                "habitacion": room.get(script_obj.mf['nombre_area'])
            })
    res, cantidad = final_format_rooms(rooms)
    return res, cantidad

def final_format_rooms(data):
    pisos = {}

    for habitacion in data:
        numero_habitacion = habitacion['habitacion'].split()[-1]
        piso = numero_habitacion[0]
        
        if piso not in pisos:
            pisos[piso] = []
        
        pisos[piso].append(numero_habitacion)

    resultado = []
    cantidad_por_piso = {}

    for piso, habitaciones in pisos.items():
        piso_dict = {"piso": piso}
        
        habitaciones_ordenadas = sorted(habitaciones, key=lambda x: int(x))
        
        cantidad_por_piso[piso] = len(habitaciones_ordenadas)
        
        for i, numero_habitacion in enumerate(habitaciones_ordenadas, start=1):
            clave = f"hab{i}"
            piso_dict[clave] = {"numero": numero_habitacion, "id": "", "status": ""}
        
        resultado.append(piso_dict)
    
    return resultado, cantidad_por_piso

def get_report_data(ubicacion='', mes='', date_from='', date_to=''):
    rooms, cantidad_rooms = get_all_rooms(ubicacion=ubicacion)
    match_query_visitas = {
        "deleted_at": {"$exists": False},
        "form_id": 126656,
        f"answers.{script_obj.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{script_obj.mf['ubicacion']}": ubicacion,
        f"answers.{script_obj.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{script_obj.mf['nombre_area']}": {
            "$regex": ".*HABITACIÓN.*",
            "$options": "i"
        },
    }

    if mes and mes != 'custom':
        meses = {
            'enero': 1,
            'febrero': 2,
            'marzo': 3,
            'abril': 4,
            'mayo': 5,
            'junio': 6,
            'julio': 7,
            'agosto': 8,
            'septiembre': 9,
            'octubre': 10,
            'noviembre': 11,
            'diciembre': 12
        }
        mes_num = meses.get(mes.lower())
        if mes_num:
            year = datetime.now().year
            first_day_of_month = datetime(year, mes_num, 1)
            last_day_of_month = datetime(year, mes_num, calendar.monthrange(year, mes_num)[1])

            date_from_mes = first_day_of_month
            date_to_mes = last_day_of_month

            match_query_visitas["created_at"] = {
                "$gte": date_from_mes,
                "$lte": date_to_mes
            }
    if date_from:
        date_from = datetime.strptime(date_from, "%Y-%m-%d")
        match_query_visitas["created_at"] = {"$gte": date_from}
    if date_to:
        date_to = datetime.strptime(date_to, "%Y-%m-%d")
        if "created_at" not in match_query_visitas:
            match_query_visitas["created_at"] = {}
        match_query_visitas["created_at"]["$lte"] = date_to

    proyect_fields_visitas = {
        '_id': 1,
        'created_date': '$created_at',
        'numero': f"$answers.{script_obj.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{script_obj.mf['nombre_area']}",
        'total_nos': '$points'
    }

    query_visitas = [
        {'$match': match_query_visitas},
        {'$project': proyect_fields_visitas},
    ]

    resultado = script_obj.format_cr(script_obj.cr.aggregate(query_visitas))
    cards = format_get_cards(resultado, cantidad_rooms=cantidad_rooms)
    res = actualizar_habitaciones_con_ids(rooms, resultado)
    graphic = get_graphic_data(ubicacion=ubicacion, mes=mes, date_from=date_from, date_to=date_to)
    return res, cantidad_rooms, cards, graphic

def actualizar_habitaciones_con_ids(formato_final, data_con_ids):
    mapeo_habitaciones_ids = {}
    inspecciones_adicionales = {}

    for item in data_con_ids:
        numero_habitacion = item['numero'].replace("HABITACIÓN ", "")
        _id = item['_id']

        if numero_habitacion not in mapeo_habitaciones_ids:
            mapeo_habitaciones_ids[numero_habitacion] = _id
            inspecciones_adicionales[numero_habitacion] = []
        else:
            inspecciones_adicionales[numero_habitacion].append(_id)

    for piso in formato_final:
        for clave, habitacion in piso.items():
            if clave.startswith("hab"):
                numero_habitacion = habitacion['numero']
                if numero_habitacion in mapeo_habitaciones_ids:
                    habitacion['id'] = mapeo_habitaciones_ids[numero_habitacion]
                    habitacion['status'] = 'revisada'
                    if numero_habitacion in inspecciones_adicionales and inspecciones_adicionales[numero_habitacion]:
                        habitacion['inspecciones'] = inspecciones_adicionales[numero_habitacion]
    
    return formato_final

def format_get_cards(data, cantidad_rooms):
    total_inspecciones = 0
    total_nos = 0
    data_cards = {}
    
    habitaciones_inspeccionadas = set()
    
    for inspeccion in data:
        total_inspecciones += 1
        total_nos += int(inspeccion.get('total_nos', 0))
        
        numero_habitacion = inspeccion['numero'].replace("HABITACIÓN ", "")
        habitaciones_inspeccionadas.add(numero_habitacion)
    
    total_habitaciones = sum(cantidad_rooms.values())
    
    if total_inspecciones > 0:
        promedio_cumplimiento = 100 - round(total_nos / total_inspecciones, 2)
    else:
        promedio_cumplimiento = 0
    
    if total_habitaciones > 0:
        porcentaje_inspecciones = round((len(habitaciones_inspeccionadas) / total_habitaciones) * 100, 2)
    else:
        porcentaje_inspecciones = 0
    
    data_cards.update({
        'totalinspecciones': total_inspecciones,
        'calificacionpromedio': promedio_cumplimiento,
        'porcentajeinspeccion':  porcentaje_inspecciones,
        'totalnos': total_nos
    })

    return data_cards

def get_graphic_data(ubicacion='', mes='', date_from='', date_to=''):
    match_query_visitas = {
        "deleted_at": {"$exists": False},
        "form_id": 126656,
        f"answers.{script_obj.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{script_obj.mf['ubicacion']}": ubicacion,
        f"answers.{script_obj.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{script_obj.mf['nombre_area']}": {
            "$regex": ".*HABITACIÓN.*",
            "$options": "i"
        },
    }

    if mes and mes != 'custom':
        meses = {
            'enero': 1,
            'febrero': 2,
            'marzo': 3,
            'abril': 4,
            'mayo': 5,
            'junio': 6,
            'julio': 7,
            'agosto': 8,
            'septiembre': 9,
            'octubre': 10,
            'noviembre': 11,
            'diciembre': 12
        }
        mes_num = meses.get(mes.lower())
        if mes_num:
            year = datetime.now().year
            first_day_of_month = datetime(year, mes_num, 1)
            last_day_of_month = datetime(year, mes_num, calendar.monthrange(year, mes_num)[1])

            date_from_mes = first_day_of_month - timedelta(days=180)
            date_to_mes = last_day_of_month + timedelta(days=180)

            match_query_visitas["created_at"] = {
                "$gte": date_from_mes,
                "$lte": date_to_mes
            }
    if date_from:
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, "%Y-%m-%d")
        match_query_visitas["created_at"] = {"$gte": date_from}
    if date_to:
        if isinstance(date_to, str):
            date_to = datetime.strptime(date_to, "%Y-%m-%d")
        if "created_at" not in match_query_visitas:
            match_query_visitas["created_at"] = {}
        match_query_visitas["created_at"]["$lte"] = date_to

    proyect_fields_visitas = {
        '_id': 1,
        'created_date': '$created_at',
        'numero': f"$answers.{script_obj.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{script_obj.mf['nombre_area']}",
        'total_nos': '$points'
    }

    query_visitas = [
        {'$match': match_query_visitas},
        {'$project': proyect_fields_visitas},
    ]

    resultado = script_obj.format_cr(script_obj.cr.aggregate(query_visitas))
    res = format_graphic(resultado)
    return res

def format_graphic(data):
    inspecciones_por_mes = {}
    nos_por_mes = {}

    for inspeccion in data:
        fecha = inspeccion['created_date']
        mes_año = fecha.strftime('%Y-%b')

        if mes_año not in inspecciones_por_mes:
            inspecciones_por_mes[mes_año] = 0
            nos_por_mes[mes_año] = 0

        inspecciones_por_mes[mes_año] += 1

        nos_por_mes[mes_año] += int(inspeccion.get('total_nos', 0))

    meses_ordenados = sorted(inspecciones_por_mes.keys(), key=lambda x: datetime.strptime(x, '%Y-%b'))

    labels = [mes for mes in meses_ordenados]
    data_inspecciones = [inspecciones_por_mes[mes] for mes in meses_ordenados]
    data_nos = [nos_por_mes[mes] for mes in meses_ordenados]

    resultado = {
        'labels': labels,
        'datasets': [
            {
                'label': 'Inspecciones',
                'data': data_inspecciones,
                'order': 2,
                'borderColor': 'rgb(255, 99, 132)',
                'backgroundColor': 'rgba(255, 99, 132, 0.2)'
            },
            {
                'type': 'line',
                'label': "No's",
                'data': data_nos,
                'fill': False,
                'borderWidth': 3,
                'tension': 0,
                'order': 1,
                'borderColor': 'rgb(54, 162, 235)',
                'pointBackgroundColor': 'rgba(255, 0, 0, 1)'
            }
        ]
    }
    return resultado

def get_second_table_data(ubicacion='', mes='', date_from='', date_to=''):
    match_query_visitas = {
        "deleted_at": {"$exists": False},
        "form_id": 126656,
        f"answers.{script_obj.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{script_obj.mf['ubicacion']}": ubicacion,
        f"answers.{script_obj.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID}.{script_obj.mf['nombre_area']}": {
            "$regex": ".*HABITACIÓN.*",
            "$options": "i"
        },
    }

    if mes and mes != 'custom':
        meses = {
            'enero': 1,
            'febrero': 2,
            'marzo': 3,
            'abril': 4,
            'mayo': 5,
            'junio': 6,
            'julio': 7,
            'agosto': 8,
            'septiembre': 9,
            'octubre': 10,
            'noviembre': 11,
            'diciembre': 12
        }
        mes_num = meses.get(mes.lower())
        if mes_num:
            year = datetime.now().year
            first_day_of_month = datetime(year, mes_num, 1)
            last_day_of_month = datetime(year, mes_num, calendar.monthrange(year, mes_num)[1])

            date_from_mes = first_day_of_month
            date_to_mes = last_day_of_month

            match_query_visitas["created_at"] = {
                "$gte": date_from_mes,
                "$lte": date_to_mes
            }
    if date_from:
        date_from = datetime.strptime(date_from, "%Y-%m-%d")
        match_query_visitas["created_at"] = {"$gte": date_from}
    if date_to:
        date_to = datetime.strptime(date_to, "%Y-%m-%d")
        if "created_at" not in match_query_visitas:
            match_query_visitas["created_at"] = {}
        match_query_visitas["created_at"]["$lte"] = date_to

    query_visitas = [
        {'$match': match_query_visitas},
    ]

    resultado = script_obj.format_cr(script_obj.cr.aggregate(query_visitas))
    res = format_data_second_table(resultado)
    return res

def format_data_second_table(data):
    list_pages_incidencia = []

    for d in data:
        pages = {
            'GENERAL': {},
            'BAÑO': {},
            'CLOSET': {},
            'HABITACION GENERAL': {},
            'ESCRITORIO': {},
            'CREDENZA T.V.': {},
        }
        pages['GENERAL'] = {
            'Puerta principal': d.get('6749fe3a9f61868c0b4a19e4', ''),
            'Chapa': d.get('6749fe3a9f61868c0b4a19e5', ''),
            'Mirilla': d.get('6749fe3a9f61868c0b4a19e6', ''),
            'Master switch': d.get('6749fe3a9f61868c0b4a19e7', ''),
            'Tarjeta de "No Molestar"': d.get('6749fe3a9f61868c0b4a19e8', ''),
            'Plano evacuación': d.get('6749fe3a9f61868c0b4a19e9', ''),
            'Apagadores': d.get('6749fe3a9f61868c0b4a19ea', ''),
            'Pasador': d.get('6749fe3a9f61868c0b4a19eb', ''),
            'Tope de pasador': d.get('6749fe3a9f61868c0b4a19ec', ''),                                                                                                     
        }
        pages['BAÑO'] = {
            'Secadora': d.get('6749fe84b841cb116d0755eb', ''),
            'Kleenera': d.get('6749ffcb33e84f4eb44a19bd', ''),
            'Limpieza lavabo': d.get('6749ffcb33e84f4eb44a19be', ''),
            'Espejo limpio': d.get('6749ffcb33e84f4eb44a19bf', ''),
            'Espejo de vanidad': d.get('6749ffcb33e84f4eb44a19c0', ''),
            'Toalla de mano': d.get('6749ffcb33e84f4eb44a19c1', ''),
            'Toalla de baño': d.get('6749ffcb33e84f4eb44a19c2', ''),
            'Cortina de baño': d.get('6749ffcb33e84f4eb44a19c3', ''),
            'Limpieza w.c.': d.get('6749ffcb33e84f4eb44a19c4', ''),
            'Funcionamiento w.c.': d.get('6749ffcb33e84f4eb44a19c5', ''),
            'Tina limpia': d.get('6749ffcb33e84f4eb44a19c6', ''),
            'Cromos limpios': d.get('6749ffcb33e84f4eb44a19c7', ''),
            'Techo de regadera': d.get('6749ffcb33e84f4eb44a19c8', ''),
            'Focos funcionando': d.get('6749ffcb33e84f4eb44a19c9', ''),
            '2 rollos papel sanitario': d.get('6749ffcb33e84f4eb44a19ca', ''),
            'Cesto de basura': d.get('6749ffcb33e84f4eb44a19cb', ''),
            'Amenidades / Despachadores': d.get('6749ffcb33e84f4eb44a19cc', ''),
            'Tapete antiderrapante': d.get('6749ffcb33e84f4eb44a19cd', ''),
            'Cebolleta regadera': d.get('6749ffcb33e84f4eb44a19ce', ''),
            'Tapete': d.get('6749ffcb33e84f4eb44a19cf', ''),
            'Piso limpio': d.get('6749ffcb33e84f4eb44a19d0', ''),
            'Puerta y espejo limpios': d.get('6749ffcb33e84f4eb44a19d1', ''),
        }
        pages['CLOSET'] = {
            'Ganchos': d.get('674a001bcc56e7f30c939286', ''),
            'Pared closet limpia': d.get('674a006c98371866c716036a', ''),
            'Caja fuerte abierta y con baterias': d.get('674a006c98371866c716036b', ''),
            'Rack limpio': d.get('674a006c98371866c716036c', ''),
            'Techo de closet': d.get('674a006c98371866c716036d', ''),
            'Tabla de planchar': d.get('674a006c98371866c716036e', ''),
            'Plancha': d.get('674a006c98371866c716036f', ''),
            'Puerta cierra bien': d.get('674a006c98371866c7160370', ''),
            'Estado de puertas closet': d.get('674a006c98371866c7160371', ''),
        }
        pages['HABITACION GENERAL'] = {
            'Papel tapiz en gral.': d.get('674a00cf5f05ce94969392ba', ''),
            'A/C (Funcionando y sin ruido)': d.get('674a0257ce0d9173204a19c5', ''),
            'Olor': d.get('674a0257ce0d9173204a19c6', ''),
            'Lamparas c/focos y switch funcion': d.get('674a0257ce0d9173204a19c7', ''),
            'Limpieza lamparas': d.get('674a0257ce0d9173204a19c8', ''),
            'Lampara de pie': d.get('674a0257ce0d9173204a19c9', ''),
            'Estado de lamparas': d.get('674a0257ce0d9173204a19ca', ''),
            'Tendido de cama': d.get('674a0257ce0d9173204a19cb', ''),
            'Cama sin cabellos(limpieza)': d.get('674a0257ce0d9173204a19cc', ''),
            'Bajo cama': d.get('674a0257ce0d9173204a19cd', ''),
            'Limpieza cabecera cama': d.get('674a0257ce0d9173204a19ce', ''),
            'Almohadas': d.get('674a0257ce0d9173204a19cf', ''),
            'Hielera': d.get('674a0257ce0d9173204a19d0', ''),
            'Tijera portamaletas': d.get('674a0257ce0d9173204a19d1', ''),
            'Limpieza buros': d.get('674a0257ce0d9173204a19d2', ''),
            'Cajones limpios': d.get('674a0257ce0d9173204a19d3', ''),
            'Cajones corren suavemente': d.get('674a0257ce0d9173204a19d4', ''),
            'Telefono': d.get('674a0257ce0d9173204a19d5', ''),
            'Cuadros decorativos sin polvo': d.get('674a0257ce0d9173204a19d6', ''),
            'Sofacama limpio (hab. Sencilla)': d.get('674a0257ce0d9173204a19d7', ''),
            'Sillon (hab. Doble)': d.get('674a0257ce0d9173204a19d8', ''),
            'Microondas limpio (hab. Ejecutiva)': d.get('674a0257ce0d9173204a19d9', ''),
            'Refrijerador limpio (hab. Ejecutiva)': d.get('674a0257ce0d9173204a19da', ''),
            'Puerta de comunicacion': d.get('674a0257ce0d9173204a19db', ''),
            'Balcon': d.get('674a0257ce0d9173204a19dc', ''),
            'Estado de cortinas': d.get('674a0257ce0d9173204a19dd', ''),
            'Ventanal': d.get('674a0257ce0d9173204a19de', ''),
            'Guia de canales': d.get('674a0257ce0d9173204a19df', ''),
        }
        pages['ESCRITORIO'] = {
            'Escritorio limpio': d.get('674a0312d080d8ec99075621', ''),
            'Lampara limpia y funcionando': d.get('674a033bce0d9173204a1a16', ''),
            'Reglamento': d.get('674a033bce0d9173204a1a17', ''),
            'Silla limpia': d.get('674a033bce0d9173204a1a18', ''),
        }
        pages['CREDENZA T.V.'] = {
            'Mueble sin polvo': d.get('674a03706d15fa34f3828411', ''),
            'Television funcionando': d.get('674a03c186f66205504a1a55', ''),
            'Canales funcionando': d.get('674a03c186f66205504a1a56', ''),
            'Control remoto funcionando': d.get('674a03c186f66205504a1a57', ''),
            'Color': d.get('674a03c186f66205504a1a58', ''),
            'Volumen': d.get('674a03c186f66205504a1a59', ''),
            'Cajones limpios': d.get('674a03c186f66205504a1a5a', ''),
            'Cajones corren suavemente': d.get('674a03c186f66205504a1a5b', ''),
            'Cesto de basura en un lado': d.get('674a03c186f66205504a1a5c', ''),
        }
        list_pages_incidencia.append(pages)

    no_counts = count_no_responses(list_pages_incidencia)
    formatted_data = format_results(no_counts)
    top_10 = get_top_10_no_responses(formatted_data)
    return top_10

def count_no_responses(data):
    no_counts = defaultdict(int)

    for entry in data:
        for page, questions in entry.items():
            for question, response in questions.items():
                if response.lower() == 'no':
                    no_counts[(question, page)] += 1

    return no_counts

def format_results(no_counts):
    formatted_data = []
    for (question, page), count in no_counts.items():
        formatted_data.append({
            "pregunta": question,
            "area": page,
            "nos": str(count)
        })
    return formatted_data

def get_top_10_no_responses(formatted_data):
    sorted_data = sorted(formatted_data, key=lambda x: int(x["nos"]), reverse=True)
    
    return sorted_data[:10]

if __name__ == "__main__":
    script_obj = Accesos(settings, sys_argv=sys.argv, use_api=True)
    script_obj.console_run()

    data = script_obj.data
    data = data.get('data', {})
    option = data.get('option','report')
    ubicacion = data.get('ubicacion', '')
    area = data.get('area', '')
    mes = data.get('mes', '')
    date_from = data.get('dateFrom', '')
    date_to = data.get('dateTo', '')
    habitaciones_x_piso = data.get('habitaciones_x_piso', '')

    if option == 'first_filter':
        response = get_first_filter()
        sys.stdout.write(simplejson.dumps({'data':{
            'response': response,
        }}))
    elif option == 'report':
        response, cantidad_rooms, cards, graphic = get_report_data(ubicacion=ubicacion, mes=mes, date_from=date_from, date_to=date_to)
        top_10 = get_second_table_data(ubicacion=ubicacion, mes=mes, date_from=date_from, date_to=date_to)
        sys.stdout.write(simplejson.dumps({'data':{
            'firstTable': response,
            'cantidad_habitaciones': cantidad_rooms,
            'cards_response': cards,
            'graphic_response': graphic,
            'secondTable': top_10
        }}))
    