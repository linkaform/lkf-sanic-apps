#-*- coding: utf-8 -*-
import sys, simplejson
from linkaform_api import settings, network, utils
from account_settings import *
import time, pytz
from pytz import timezone
from datetime import datetime, timedelta
from pprint import pprint

class ReportModel():
    def __init__(self):
        self.json={
            "firstElement":{
                "data": [],
            },
            "secondElement":{
                "data": [],
            },
            "thirdElement":{
                "data": [],
            },
            "catalog":[],
            "group_users":[],
            "listIds":[]
        }

    def print(self):
        res = {'json':{}}
        for x in self.json:
            res['json'][x] = self.json[x]
        return res

def get_date_query(date_from, date_to):
    res = {}
    timezone = pytz.timezone('America/Monterrey')
    tz_date =  datetime.strptime('%s 00:00:00'%(date_from), "%Y-%m-%d %H:%M:%S")
    
    tz_date = tz_date.replace(tzinfo=pytz.utc)
    tz_date = tz_date.astimezone(timezone)
    tz_date = timezone.normalize(tz_date)
    tz_offset = tz_date.utcoffset().total_seconds()

    
    date_from = datetime.strptime('%s 00:00:00'%(date_from), "%Y-%m-%d %H:%M:%S") - timedelta(seconds=tz_offset)
    date_to = datetime.strptime('%s 23:59:59'%(date_to), "%Y-%m-%d %H:%M:%S") - timedelta(seconds=tz_offset)
        
    if date_from and date_to:
        res.update({
        'start_date': {
        '$gte':date_from,
        '$lt':date_to,
        }
        })
    elif date_from and not date_to:
        res.update({
        'start_date': {
        '$gte':date_from
        }
        })

    elif not date_from and date_to:
        res.update({
        'start_date': {
        '$lt':date_to
        }
        })
    return res

#Parsing
def get_format_firstElement(result):
    data = [x for x in result]
    
    dataTwo = {}
    visita_promotor = {}
    meta_promotor = {}
    request = []
    url_pdf = ''
    ids_registro = []
    list_hr_final = []
    min_traslado = ''
    print("Element")
    for idElemenet, element in enumerate(data):
        print()
        print(element)
        version= str(element.get('version',''))
        folio = str(element.get('folio',''))
        record_id = str(element.get('record_id',''))
        promotor = element.get('promotor', '')
        cadena = element.get('cadena','')
        ciudad = element.get('entidad','') #Es entidad porque la forma no tiene el campo ciudad
        tienda = element.get('tienda','')
        fecha_entrada = element.get('fecha_entrada','')
        fecha_salida = element.get('fecha_salida','')
        duration = 0
        #FORMATING DATE
        fecha_limite = "2023-10-29 00:00:00-06:00"
        fecha_limite = datetime.fromisoformat(fecha_limite)
        timezone = pytz.timezone('America/Monterrey')
        if fecha_entrada:
            fecha_entrada = fecha_entrada.astimezone(timezone)
            fecha_entrada = (fecha_entrada)
            if fecha_entrada < fecha_limite:
                fecha_entrada = (fecha_entrada - timedelta(hours=1))
        if fecha_salida:
            fecha_salida = fecha_salida.astimezone(timezone)
            fecha_salida = (fecha_salida)
            if fecha_salida < fecha_limite:
                fecha_salida = (fecha_salida - timedelta(hours=1))
        
        diference = 0
        if fecha_entrada and fecha_salida:
            diference = fecha_salida - fecha_entrada
            diference = int(diference.total_seconds())
        if diference:
            minutes_register = (diference / 60)
            duration = (minutes_register / 60)
            duration = round(duration, 2)

        date_entrada = fecha_entrada.strftime('%Y-%m-%d')
        time_entrada = fecha_entrada.strftime('%I:%M %p')
        date_salida = fecha_salida.strftime('%Y-%m-%d')
        time_salida = fecha_salida.strftime('%I:%M %p')
        bandera_primero = False
        if promotor not in dataTwo:
            dataTwo[promotor] = {0:{},1:{}}
            visita_promotor[promotor] = 0
        if date_entrada not in dataTwo[promotor][1]:
            dataTwo[promotor][1][date_entrada] = [{},[]]
            dataTwo[promotor][1][date_entrada][0].update({
                "hora_inicio":time_entrada,
                "hora_salida":time_salida,
                "tiempo_visita":[duration]
            })
            list_hr_final = []
            min_traslado = ''

            bandera_primero = True
        if bandera_primero == False:
            dataTwo[promotor][1][date_entrada][0].update({
                "hora_salida":time_salida,
            })
            dataTwo[promotor][1][date_entrada][0]['tiempo_visita'].append(duration)
        
        #Calcular el tiempo de traslados en minutos
        list_hr_final.append(time_salida)
        if len(list_hr_final) > 1:
            lng_list = 0
            lng_list = len(list_hr_final)
            print(f"La longitud de list_hr_final es = {len(list_hr_final)}")
            temp_time_salida = datetime.strptime(list_hr_final[lng_list-2], '%I:%M %p').time()
            temp_time_entrada = datetime.strptime(time_entrada, '%I:%M %p').time()

            #Convertir ambos objetos a segundos
            segundos_entrada = temp_time_salida.hour * 3600 + temp_time_salida.minute * 60
            segundos_salida = temp_time_entrada.hour * 3600 + temp_time_entrada.minute * 60

            # Calcula la diferencia en segundos
            diferencia_segundos = segundos_salida - segundos_entrada

            # Convierte la diferencia de segundos a horas y minutos
            minutos = (diferencia_segundos // 60)

            min_traslado = (f"{minutos} min")

        #Creación del los urls de descarga del pdf
        format_folio = folio.replace('-','_')
        if version:
            url_pdf = "https://f001.backblazeb2.com/file/app-linkaform/public-client-13145/downloads/pdfs/105624/"+folio+"/version_"+version+"/Formulario_Loquay"+format_folio+".pdf"
            ids_registro.append(record_id)
        visita_promotor[promotor] += 1
        dataTwo[promotor][1][date_entrada][1].append({
                "usuario":promotor,
                "fecha":folio,
                "ciudad":ciudad,
                "cadena":cadena,
                "tienda":tienda,
                "fecha_inicio":date_entrada,
                "hora_inicio":time_entrada,
                "fecha_final":date_salida,
                "hora_final":time_salida,
                "duracion_visita":duration,
                "total_hrs_dia": min_traslado,
                "record_id":record_id,
                "url_download":url_pdf
            })
        
    for key, value in dataTwo.items():
        request.append(
        {"usuario": key,
        "ciudad": "Días laborados",
        "cadena": len(dataTwo[key][1]),
        "hora_inicio": "Hrs de jornada: ",
        "fecha_final": "",
        "hora_final": "Hrs de visitas: ",
        "duracion_visita": "",
        "total_hrs_dia": "Hrs de traslados: ",
        "record_id": "",
        "_children":[]

        })
        total_jornada = 0
        duration_visitas = 0
        tiempo_traslados = 0
        for key2, val2 in value[1].items():
            hora_inicio_24h = val2[0]['hora_inicio']
            hora_salida_24h = val2[0]['hora_salida']
            horas_visita = sum(val2[0]['tiempo_visita'])
            duration_visitas += horas_visita
            
            #Convertimos el formato a 24hrs
            hora_inicio_24h = datetime.strptime(hora_inicio_24h,"%I:%M %p").strftime("%H:%M")
            hora_salida_24h = datetime.strptime(hora_salida_24h,"%I:%M %p").strftime("%H:%M")
            
            #Calcular la diferencia en horas
            inicio = datetime.strptime(hora_inicio_24h, "%H:%M")
            salida = datetime.strptime(hora_salida_24h, "%H:%M")
            diferencia = salida - inicio
            #print("La diferencia es = ", diferencia)

            diference_hours = round(diferencia.total_seconds() / 3600, 2)
            total_jornada += diference_hours
            tiempo_traslados = round((diference_hours - horas_visita), 2)
            for req in request:
                if req["usuario"] == key:
                    req["_children"].append({
                        "usuario":req["usuario"],
                        "fecha": "Día " + key2,
                        "ciudad": "Inicio:",
                        "cadena": val2[0]['hora_inicio'],
                        "tienda": "Fin:",
                        "fecha_inicio": val2[0]['hora_salida'],
                        "hora_inicio": "Hrs de jornada:",
                        "fecha_final": diference_hours,
                        "hora_final": "Hrs de visitas:",
                        "duracion_visita": round(horas_visita, 2),
                        "total_hrs_dia": "Hrs traslados: " + str(tiempo_traslados),
                        "record_id": "",
                        "_children": val2[1]
                    })
                #Segundo nivel de anidación
        tiempo_traslados = round(total_jornada-duration_visitas,1)
        for req in request:
            if req["usuario"] == key:
                req.update({
                    "fecha_final": round(total_jornada,2),
                    "duracion_visita": round(duration_visitas,2),
                    "total_hrs_dia": "Hrs traslados: "+str(tiempo_traslados),    

                }) 

        """ if date_entrada not in dataTwo[promotor]:
            #dataTwo[promotor].append(date_entrada)
            dataTwo[promotor][date_entrada] = []
        else:
            dataTwo[promotor][date_entrada].append({
                "folio":folio,
                "entidad":entidad,
                "cadena":cadena,
                "tienda":tienda,
                "fecha_inicio":date_entrada,
                "hora_inicio":time_entrada,
                "hora_salida":date_salida,
                "fecha_salida":time_salida,
                "duration":duration,
                "record_id":record_id
            }) """
    
    report_model.json['firstElement']['data'] = request
    report_model.json['listIds'] = ids_registro
    #pprint(dataTwo)
    """ for el in request:
        print()
        for key, val in el.items():
            print()
            #print(key)
            #print(val)
            if key == "_children":
                print(type(val))
            print()
        print() """
    
    print(visita_promotor)

    #Configurar la gráfica
    labels = []
    data = []
    background_list = []
    dict_ordenado = dict(sorted(visita_promotor.items(), key=lambda item:item[1], reverse=True))
    colores = ["#7BD3EA", "#ECA869", "#FFB996", "#756AB6", "#C7DCA7", "#80BCBD", "#FF90BC", "#756AB6", "#F1C27B" , "#A0C49D", "#D9ACF5", "#54BAB9", "#FFCCB3", "#8FBDD3", "#9ADCFF", "#94D0CC", "#9DBC98", "#A7D397"    ]
    cont_colors = 0
    for key, value in dict_ordenado.items():
        labels.append(key)
        data.append(value)
        background_list.append(colores[cont_colors])
        cont_colors += 1        
    
    report_model.json['secondElement']['data'].append({
        "labels":labels,
        "datasets":[
            {
                "label":"Número de visitas por promotor",
                "backgroundColor":background_list,
                "data":data
            }
        ]
    })

    numero_promotor = 0
    total_visitas = 0
    total_visitas = sum(data)
    numero_promotor = len(labels)

    report_model.json['thirdElement']['data'].append({
        "total_visitas":total_visitas,
        "numero_promotor":numero_promotor
    })
    


#Querys
def query_report_firstB(date_from, date_to, cadena):
    global report_model
    match_query = {
        "form_id": {"$in": [61083]}
    }

    if cadena and '--' not in cadena:
        match_query.update({"answers.65f1d4e0ed087e734629e921.6501037f5271f9ec6754673a": cadena})
    
    match_query.update(get_date_query(date_from, date_to))

    #Query
    query = [
        {"$match": match_query},
        {"$project":{
            "_id":0,
            "folio":"$folio",
            "version":"$version",
            "record_id":"$_id",
            "cadena": "$answers.65f1d4e0ed087e734629e921.6501037f5271f9ec6754673a",
            "promotor": "$created_by_name",
            "tienda":"$answers.65f1d4e0ed087e734629e921.6501037f5271f9ec6754673c",
            "entidad":"$answers.65f1d4e0ed087e734629e921.650103c699c4de74149da1b6",
            "fecha_entrada":"$start_date",
            "fecha_salida":"$end_date",
            "duration":{
                "$divide":[
                    {"$subtract":["$end_date", "$start_date"]},
                    1000 * 60 * 60
                ]
            }
        }},
        {"$sort":{"promotor":1, "fecha_entrada":1}}
    ]

    result = cr.aggregate(query)
    get_format_firstElement(result)

def query_catalog():
    global report_model
    array_catalog = []
    match_query = {
        "deleted_at": {"$exists":False},
    }

    mango_query = {"selector":
        {"answers":
            {"$and":[match_query]}
        },
        "limit":10000
    }

    res = lkf_api.search_catalog(116388, mango_query, jwt_settings_key='USER_JWT_KEY')
    print("Catalogo es")
    print(res)
    for element in res:
        sucursal = element.get('6501037f5271f9ec6754673a','')
        if sucursal and sucursal not in array_catalog:
            array_catalog.append(sucursal)
            report_model.json['catalog'].append(element)

def get_format_users(listInformation):
    global report_model

    list_name = []
    list_users = []

    if len(listInformation['data']['users']) > 0:
        list_users = listInformation['data']['users']

    for x in list_users:
        name = x.get('name','')
        report_model.json['group_users'].append(name)

    return list_name

def query_groups():
    dicList = {
        'zona_noreste':[],
    }

    #Región Loquay
    user_group = net.dispatch({
        'url': settings.config['PROTOCOL'] + '://' + settings.config['HOST'] + '/api/infosync/group/' + str(222) + '/',
        'method':'GET'
    }, jwt_settings_key = 'USER_JWT_KEY')
    dicList['zona_noreste'] = get_format_users(user_group)

    print("**************U S E R S******************")
    print(dicList['zona_noreste'])
    print("*****************************************")

if __name__=='__main__':
    print(sys.argv)
    all_data = simplejson.loads(sys.argv[2])

    #Filter
    data = all_data.get("data",{})
    date_from = data.get('date_from', '')
    date_to = data.get('date_to','')
    cadena = data.get('cadena','')
    option = int(data.get('option',0))

    #Config
    net = network.Network(settings)
    report_model = ReportModel()
    lkf_api = utils.Cache(settings)
    jwt_key = lkf_api.get_jwt(api_key=settings.config['API_KEY'])
    config["USER_JWT_KEY"] = jwt_key
    settings.config.update(config)
    lkf_api = utils.Cache(settings)
    net = network.Network(settings)
    cr = net.get_collections()

    #Operations
    print("Data")
    if option == 2:
        print("Catalogos")
        query_catalog()
    
    else:
        print("date_to no esta definido")
        if date_to == "":
            today = datetime.now()
            today = today.strftime("%Y-%m-%d")
            timezone = pytz.timezone('America/Monterrey')

            tz_date = datetime.strptime('%s 23:59:59'%(today), "%Y-%m-%d %H:%M:%S")
            
            tz_date = tz_date.replace(tzinfo=pytz.utc)
            tz_date = tz_date.astimezone(timezone)
            tz_date = timezone.normalize(tz_date)
            tz_offset = tz_date.utcoffset().total_seconds()

            date_to = datetime.strptime(today, "%Y-%m-%d") - timedelta(seconds=tz_offset)

            date_to = date_to.strftime("%Y-%m-%d")
            print("date_to = ", date_to)

        if date_from  and date_to:
            ''''
                La función solicita la lista de usuarios que 
                pertenecen al grupo de usuarios de AlGroup, con el objetivo
                de obtener a los usuarios actuales.
            '''
            query_groups()
            
            query_report_firstB(date_from, date_to, cadena)


    sys.stdout.write(simplejson.dumps(report_model.print()))