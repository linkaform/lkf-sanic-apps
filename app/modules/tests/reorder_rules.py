import sys
from account_settings import *
from linkaform_api import base


if __name__ == "__main__":
    script_obj = base.LKF_Base(settings, sys_argv=sys.argv, use_api=True)
    script_obj.console_run()
    
    #-FILTROS
    data = script_obj.data
    data = data.get('data',[])
    
    option = data.get('option','get_report')
    status = data.get('status', '')
    
    # res_first = get_elements(status)
    # print('info: ', res_first)

    # #-FILTROS
    # data = script_obj.data
    # data = data.get('data',[])

    # option = data.get('option','get_report')
    # wharehouse = data.get('wharehouse', '')
    # familia = data.get('familia', '')

    if option == 'get_report':
        res_first = get_elements(status)
    #     '''
    #     script_obj.HttpResponse({
    #         "firstElement":res_first,
    #     })
    #     '''
    # elif option == 'get_catalog':
    #     #res_catalog = get_catalog_wharehouse()
    #     print('Hola catalogo')
    #     '''
    #     script_obj.HttpResponse({
    #         "dataCatalog":res_catalog,
    #     })
    #     '''
