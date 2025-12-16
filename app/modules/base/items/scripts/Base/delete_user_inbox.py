# coding: utf-8
import sys, simplejson

from base_utils import Base

from account_settings import *


class Base(Base):


    def delete_user_inbox(self, user_id, record_id):
        cr_couch = self.lkf_api.couch
        cr_db = cr_couch.set_db(f'user_inbox_{user_id}')
        mango_query = {
            "selector":
            {"record_json._id":record_id},
            "limit":20,"skip":0}
        records = cr_db.find(mango_query)
        for record in records:
            rec = {'_id':record['_id'], '_rev':record['_rev']}
            return cr_couch.delete_records(cr_db, [rec,])
        return {"status": 404}


    def get_user_record(self, folio):
        query = {}
        #res = self.cr.find(query)
        record_id = '3'
        user_id = 126
        return record_id, user_id

    def run_delete_user_inbox(self, data):
        folio = data.get('folio')
        record_id, user_id = self.get_user_record(folio)
        res = self.delete_user_inbox(user_id, record_id)
        return res

if __name__ == "__main__":
    base_obj = Base(settings, sys_argv=sys.argv)
    base_obj.console_run()
    response = base_obj.run_delete_user_inbox(base_obj.data)

    sys.stdout.write(simplejson.dumps({
        'status': 201,
        'data': response
    }))

