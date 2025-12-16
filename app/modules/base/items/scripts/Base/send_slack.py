# coding: utf-8
#####
# Script para enviar notificacion Slack
# Forma: 
#####
import requests, sys, simplejson, json

from base_utils import Base
from account_settings import *

class Base(Base):

    def __init__(self, settings, sys_argv=None, use_api=False):
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.f.update({
            'empresa_slack': '67dc1b351cd723ff9b872434',
            'email_slack': '67dc1b351cd723ff9b872435'
        })

    def create_response(self, status, status_code, message="", data=[]):
        response = {}
        response = {
            "status": status,
            "status_code": status_code,
            "message": message,
            "data": data
        }
        return response
    
    def get_user_id(self, token, email):
        url = "https://slack.com/api/users.lookupByEmail"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"email": email}

        try:
            response = requests.get(url, headers=headers, params=params)
            data = response.json()
            
            if data.get("ok"):
                user_id = [{
                    "user_id": data["user"]["id"]
                }]
                response = self.create_response("success", 200, "Exito al realizar la busqueda", data=user_id)
                return response
            else:
                response = self.create_response("error", 500, f"Ocurrio un error al obtener el user_id: {data.get('error')}")
                return response
        except Exception as e:
            response = self.create_response("error", 500, f"Error al realizar la peticion: {e}")
            return response

    def get_user_ids_in_channel(self, token, channel_id):
        url = f"https://slack.com/api/conversations.members?channel={channel_id}"
        headers = {
            "Authorization": f"Bearer {token}"
        }

        try:
            response = requests.get(url, headers=headers)
            data = response.json()
            
            if data.get("ok"):
                user_ids = [{
                    "user_ids": data['members']
                }]
                response = self.create_response("success", 200, "Exito al realizar la busqueda", data=user_ids)
                return response
            else:
                response = self.create_response("error", 500, f"Ocurrio un error al obtener el user_id: {data.get('error')}")
                return response
        except Exception as e:
            response = self.create_response("error", 500, f"Error al realizar la peticion: {e}")
            return response

    def get_user_info(self, token, user_id):
        url = f"https://slack.com/api/users.info?user={user_id}"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get("ok"):
            user_info = data.get("user", {})
            return user_info
        else:
            print(f"Error: {data.get('error')}")
            return None
        
    def get_channel_id(self, token, company):
        url = "https://slack.com/api/conversations.list"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        params = {
            "exclude_archived": "true",
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            channels = response.json().get("channels", [])
            
            for channel in channels:
                if company == channel['name']:
                    channel_id = [{'channel_id': channel['id']}]
                    response = self.create_response("success", 200, "Exito al realizar la busqueda", data=channel_id)
                    return response
                
            response = self.create_response("error", 200, "No se encontro el canal")
            return response
        except Exception as e:
            response = self.create_response("error", 500, f"Error al realizar la peticion: {e}")
            return response

    def send_slack_dm(self, token, user_id):
        message = (
            "📢 *Aviso importante*\n\n"
            "La persona que invitó ha llegado a nuestras instalaciones. \n"
            "Por favor, diríjase a la recepción 🏢 para recibirla y completar el registro.\n\n"
            "Si necesita ayuda, nuestro equipo está disponible para asistirle. ✨"
        )

        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "channel": user_id,
            "text": message
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            data = response.json()

            if response.status_code == 200 and data.get("ok"):
                response = self.create_response("success", 200, "Exito al enviar el mensaje")
                return response
            else:
                response = self.create_response("error", 500, f"Ocurrio un error al obtener el user_id: {data.get('error')}")
                return response
        except Exception as e:
            response = self.create_response("error", 500, f"Error al realizar la peticion: {e}")
            return response

    def send_message_to_channel(self, token, channel, user_id, message):
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "channel": channel,
            "text": f"<@{user_id}> {message}"
        }

        response = requests.post(url, json=data, headers=headers)
        print(response.json())

    def search_user_by_id(self, token, user_ids, user_to_search):
        for id in user_ids:
            searching_user = self.get_user_info(token=token, user_id=id)
            if searching_user.get('profile', {}).get('email') == user_to_search:
                return searching_user
        return None
    
    def send_slack_notification(self, token, company='', email='', in_organization=True):
        if in_organization:
            response = base_obj.get_user_id(token=token, email=email)
            if response.get('status') == 'success':
                user_id = response.get('data', [])[0].get('user_id')
                if user_id:
                    response = base_obj.send_slack_dm(token=token, user_id=user_id)
                    return response
            response = self.create_response("error", 500, "Ocurrio un error al enviar slack_notification")
            return response
        # elif not in_organization:
        #     # company = "soter-notifications-dev"
        #     company = f"soter-notifications-{company.lower().replace(' ', '-')}"
        #     response = base_obj.get_channel_id(token=token, company=company)
        #     if response.get('status') == 'success':
        #         channel_id = response.get('data', [])[0].get('channel_id')
        #         response = base_obj.get_user_ids_in_channel(token=token, channel_id=channel_id)
        #         if response.get('status') == 'success':
        #             user_ids = response.get('data', [])[0].get('user_ids')
        #             #TODO Podrian almacenarse los ids en un registro de la forma para no tener que buscarlos cada vez
        #             usuario = base_obj.search_user_by_id(token=token, user_ids=user_ids, user_to_search=email)
        #             user_id = usuario.get('id')
        #             if user_id:
        #                 response = base_obj.send_slack_dm(token=token, user_id=user_id)
        #                 print(response)

if __name__ == "__main__":
    base_obj = Base(settings, sys_argv=sys.argv)
    base_obj.console_run()
    data = base_obj.data.get('data', {})
    slack_email = data.get('slack_email', '')

    token = ""

    response = base_obj.send_slack_notification(token=token, email=slack_email)
    base_obj.HttpResponse({"data": response})