import sys,json, simplejson, re
from datetime import date
import datetime, time
from pytz import timezone
import pytz

from linkaform_api import settings, network, utils

from account_settings import *

#---FORMAT
def get_format_data(data, type_format = 'bitacora'):
    curp = ''
    name_plant = ''
    type_record = ''
    data_user = data.get('data_user','').split("|")
    data_item = data.get('list_item',[])

    #---Format
    if data_user:
        curp = data_user[0]
        name_plant = data_user[1]
        type_record = str(data_user[2]).lower()
        name_complete = str(data_user[3])
        razon_social = str(data_user[4])
        email =''
        image = {}
        type_status = 'inactivo'
        if type_record =='entrada':
            type_status = 'activo'


    if type_format == 'bitacora':
        dic_response = {
            '64ee8349998263ad9bec20cc': curp,
            '64ee8349998263ad9bec20cd': name_plant,
            '64ee8349998263ad9bec20ce': type_record,
            '5ea0693a0c12d5a8e43d37df': name_complete,
            '64ecc95271803179d68ee081': razon_social,
            '64ee8349998263ad9bec20cf': [],
        }
    elif type_format == 'colaborador':
        dic_response = {
            '5ea0693a0c12d5a8e43d37df': name_complete,
            '5ea069562f8250acf7d83aca': email,
            '5ea35de83ab7dad56c66e045': image,
            '5ea0897550b8dfe1f4d83a9f': curp,
            '65ca63ed86c50defa6f5f333': name_plant,
            '5ea1bd280ae8bad095055e62': type_status,
            '65cbb23fa3064c295a72b4ab': razon_social,
            '65c67e21d7add8306488f064': [],
        }

    #---Format Item
    if data_item:
        for x in data_item:
            data_index = x.split("|")
            name_item = ''
            desc_item = ''
            if data_user:
                name_item = data_user[0]
                desc_item = data_user[1]

            if type_format == 'bitacora':
                dic_response['64ee8349998263ad9bec20cf'].append({
                    '64ee837b0392b342498edf35': name_item,
                    '64ee837b0392b342498edf36': desc_item
                })
            elif type_format == 'colaborador':
                dic_response['65c67e21d7add8306488f064'].append({
                    '65c67f4ab8db64319658fed1': name_item,
                    '65c67f4ab8db64319658fed2': desc_item
                })
    return dic_response

def get_query_flag(data):
    curp_user = data.get('64ee8349998263ad9bec20cc','')
    location_user = data.get('64ee8349998263ad9bec20cd','')
    if curp_user!= '' and location_user !='':
        match_query = {
            "form_id":114233,
            "answers.5ea0897550b8dfe1f4d83a9f":curp_user,
            "answers.65ca63ed86c50defa6f5f333":location_user,
        }
        query= [{'$match': match_query },
            {"$project":
                {
                    "_id":0,
                    "folio":"$folio",
                    "5ea1bd280ae8bad095055e62": "$answers.5ea1bd280ae8bad095055e62",
                }
            },
            {'$limit':1}
        ]
        res = cr.aggregate(query)
        list_response = [x for x in res]
        if len(list_response) > 0:
            return True
        else:
            return False

def set_add_record_bitacora(dic):
    metadata = lkf_api.get_metadata(107815)
    metadata['answers'] = dic
    resp_create = lkf_api.post_forms_answers(metadata, jwt_settings_key = "USER_JWT_KEY")

def set_update_record_colaborador(dic):
    #----Variables
    curp = ''
    name_plant = ''
    status_record = 'inactivo'
    data_user = dic.get('data_user','').split("|")
    data_item = dic.get('list_item',[])
    #----Format
    if data_user:
        curp = data_user[0]
        type_record = str(data_user[2]).lower()
        if type_record =='entrada':
            status_record = 'activo'
    #---Format Item
    dic_items = []
    if data_item:
        for x in data_item:
            data_index = x.split("|")
            name_item = ''
            desc_item = ''
            if data_user:
                name_item = data_index[0]
                desc_item = data_index[1]
            dic_items.append({
                '65c67f4ab8db64319658fed1': name_item,
                '65c67f4ab8db64319658fed2': desc_item
            })

    #---Query
    match_query = {
        "form_id":114233,
        "answers.5ea0897550b8dfe1f4d83a9f":curp,
    }

    query= [{'$match': match_query },
        {"$project":
            {
                "folio":"$folio",
                "form_id":"$form_id",
                "answers": "$answers",
            }
        },
        {'$limit':1}
    ]
    res = cr.aggregate(query)
    list_response = [x for x in res]
    #---Update
    if len(list_response)  > 0:
        data_query = list_response[0];
        data_query['answers'].update({'5ea1bd280ae8bad095055e62':status_record,'65c67e21d7add8306488f064':dic_items});
        resp_update = lkf_api.patch_record(data_query ,jwt_settings_key = "USER_JWT_KEY")

def set_add_record_colaborador(dic):
    dic_format = get_format_data(dic,'colaborador');
    metadata = lkf_api.get_metadata(114233)
    metadata['answers'] = dic_format
    resp_create = lkf_api.post_forms_answers(metadata, jwt_settings_key = "USER_JWT_KEY")

if __name__ == "__main__":
    print(sys.argv)
    #-FILTROS
    all_data = simplejson.loads(sys.argv[2])
    data = all_data.get("data", {})
    dic_record = data.get("data_record",'')
    #-CONFIGURATION
    lkf_api = utils.Cache(settings)
    jwt_parent = lkf_api.get_jwt(api_key=config["API_KEY"])
    config["USER_JWT_KEY"] = jwt_parent
    settings.config.update(config)
    net = network.Network(settings)
    cr = net.get_collections()
    #-EXECUTION
    if dic_record:
        dic_data = get_format_data(dic_record,'bitacora');
        set_add_record_bitacora(dic_data);
        flag = get_query_flag(dic_data);
        if flag:
            set_update_record_colaborador(dic_record)
        else:
            set_add_record_colaborador(dic_data);
        sys.stdout.write(simplejson.dumps({"msg": "Success"}))
    else:
        sys.stdout.write(simplejson.dumps({"msg": "Failed"}))
