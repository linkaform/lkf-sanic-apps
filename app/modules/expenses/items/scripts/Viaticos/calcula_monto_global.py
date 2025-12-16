# -*- coding: utf-8 -*-
import sys, wget, bson, simplejson

#from linkaform_api import settings, utils

from account_settings import *


def read_current_record_from_txt(file_url):
    name_downloded = download_pdf( file_url, is_txt=True )
    f = open( "/tmp/{}".format( name_downloded ) )
    return simplejson.loads( f.read() )

def download_pdf(file_url, is_txt=False):
    oc_name = 'oc_{}.pdf'.format(str(bson.ObjectId()))
    if is_txt:
        oc_name = 'file_{}.txt'.format(str(bson.ObjectId()))
    wget.download(file_url, '/tmp/{}'.format(oc_name))
    return oc_name

if __name__ == '__main__':
    print('pirnt this file is depricaded')
    print(stop_depricated)
    current_record = simplejson.loads(sys.argv[1])
    total_global = 0
    
    if not current_record.get('answers'):
        current_record = read_current_record_from_txt( current_record['answers_url'] )
    
    for viatico in current_record['answers'].get('62950fd07b46d19bfd08d8fd', []):
        status = viatico.get('62952ab5ec3852e91f08d93b', '')
        if status == 'autorizado':
            total_global += viatico.get('62952ab5ec3852e91f08d93c', 0)
    current_record['answers']['62954ead595be739d4d59f80'] = total_global
    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'replace_ans': current_record['answers']
    }))