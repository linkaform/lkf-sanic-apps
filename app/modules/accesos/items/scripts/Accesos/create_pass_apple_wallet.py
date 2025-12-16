import sys, simplejson, io, json, tempfile, requests, os, uuid
from wallet.models import Pass, Generic, Barcode, Field

from accesos_utils import Accesos

from account_settings import *

class MyPass(Pass):
    def json_dict(self):
        data = super().json_dict()
        if hasattr(self, "barcode") and self.barcode:
            data["barcode"] = self.barcode.json_dict()
        return data

class Accesos(Accesos):

    def crear_pass_json(self, data):
        visita_a = data.get('visita_a')
        nombre = data.get('nombre')
        fecha = data.get('fecha')
        hora = data.get('hora')
        ubicaciones_list = data.get('ubicacion')
        format_ubicacion = self.format_ubicaciones_to_google_pass(ubicaciones_list)
        area = data.get('area')

        pass_data = {
            "generic": {
                "headerFields": [
                    {
                        "key": "welcome",
                        "label": "Folio:",
                        "value": "PE/2505/1272"
                    }
                ],
                "primaryFields": [
                    {
                        "key": "name",
                        "label": "",
                        "value": nombre
                    }
                ],
                "secondaryFields": [
                    {
                        "key": "date2",
                        "label": "Visita a:",
                        "value": visita_a
                    },
                    {
                        "key": "date3",
                        "label": "",
                        "value": ""
                    },
                    {
                        "key": "date",
                        "label": "Fecha",
                        "value": fecha
                    }
                ],
                "auxiliaryFields": [
                    {
                        "key": "ubication",
                        "label": f"Ubicación",
                        "value": format_ubicacion
                    },
                    {
                        "key": "area",
                        "label": "Área",
                        "value": area
                    },
                    {
                        "key": "hour",
                        "label": "Hora",
                        "value": hora
                    }
                ]
            }
        }

        temp = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix='.json')
        json.dump(pass_data, temp, ensure_ascii=False, indent=4)
        temp.seek(0)

        return temp.name

    def get_image_file(self, url):
        response = requests.get(url)
        response.raise_for_status()
        return io.BytesIO(response.content)

    def create_pass_apple_wallet(self, record_id):
        if not record_id:
            raise Exception("record_id es requerido")

        access_pass = self.get_detail_access_pass(qr_code=record_id)
        file_url = ''
        if access_pass.get('apple_wallet_pass', []):
            for apple_pass in access_pass.get('apple_wallet_pass', []):
                file_url = apple_pass.get('file_url')
        else:
            fecha_completa = access_pass.get('fecha_de_caducidad', '')
            fecha, hora = fecha_completa.split(' ')
            hora_sin_segundos = hora[:5]
            foto_url = access_pass.get('foto', [])[0].get('file_url', '')

            data = {
                "qr_code": record_id,
                "nombre": access_pass.get('nombre'),
                "visita_a": access_pass.get('visita_a', [])[0].get('nombre', ''),
                "fecha": fecha,
                "hora": hora_sin_segundos,
                "ubicacion": access_pass.get('ubicaciones', []),
                "area": access_pass.get('area', 'Caseta Principal'),
            }

            pass_json_path = self.crear_pass_json(data)

            with open(pass_json_path, "r", encoding="utf-8") as f:
                pass_data = json.load(f)

            card_info = Generic()
            card_info.headerFields = [Field(**f) for f in pass_data.get("generic", {}).get("headerFields", [])]
            card_info.primaryFields = [Field(**f) for f in pass_data.get("generic", {}).get("primaryFields", [])]
            card_info.secondaryFields = [Field(**f) for f in pass_data.get("generic", {}).get("secondaryFields", [])]
            card_info.auxiliaryFields = [Field(**f) for f in pass_data.get("generic", {}).get("auxiliaryFields", [])]

            my_pass = MyPass(
                pass_information=card_info,
                pass_type_identifier="pass.com.soter.mx",
                organization_name="Soter",
                team_identifier="ME623A8A63",
            )

            my_pass.barcode = Barcode(message='681bf3e3a83be7c3b9cf802f', format='qr', encoding='iso-8859-1', alt_text='')
            my_pass.serialNumber = str(uuid.uuid4())
            my_pass.description = "Pase de prueba"

            # print(json.dumps(my_pass.json_dict(), indent=4, ensure_ascii=False))

            icon_url = "https://f001.backblazeb2.com/file/app-linkaform/public-client-126/68600/6076166dfd84fa7ea446b917/2025-05-08T08:28:17_1.png"
            logo_url = "https://f001.backblazeb2.com/file/app-linkaform/public-client-126/68600/6076166dfd84fa7ea446b917/2025-05-22T17:02:16_1.png"
            thumbnail_url = foto_url

            my_pass.add_file(name="icon.png", file_handle=self.get_image_file(icon_url))
            my_pass.add_file(name="logo.png", file_handle=self.get_image_file(logo_url))
            if thumbnail_url:
                my_pass.add_file(name="thumbnail.png", file_handle=self.get_image_file(thumbnail_url))

            cert_string = """"""

            soter_pass_string = """"""

            wwdr_string = """"""

            key_pem_password = ""

            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.pem') as cert_temp:
                cert_temp.write(cert_string)
                cert_temp_path = cert_temp.name

            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.pem') as wwdr_temp:
                wwdr_temp.write(wwdr_string)
                wwdr_temp_path = wwdr_temp.name

            with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.pem') as soter_pass_key_temp:
                soter_pass_key_temp.write(soter_pass_string)
                soter_pass_key_temp_path = soter_pass_key_temp.name

            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_pkpass:
                pkpass_path = temp_pkpass.name

            response = my_pass.create(cert_temp_path, soter_pass_key_temp_path, wwdr_temp_path, key_pem_password, pkpass_path)
            print("Archivo temporal creado:", pkpass_path)

            # Lee el archivo en bytes
            with open(pkpass_path, "rb") as f:
                zip_bytes = f.read()

            id_forma_seleccionada = self.PASE_ENTRADA
            id_field = self.pase_entrada_fields['apple_wallet_pass']
            upload_result = self.upload_zip(id_forma_seleccionada, id_field, zip_bytes, filename="SoterApplePass.zip")
            file_url = upload_result.get('file_url')
            print(upload_result)

            data = {
                'apple_wallet_pass': [
                    {
                        'file_name': upload_result.get('file_name'),
                        'file_url': file_url
                    }
                ]
            }

            update_response = self.update_pass(access_pass=data, folio=record_id)
            print('update_response', update_response)
        return file_url
    
    def upload_zip(self, id_forma_seleccionada, id_field, zip_bytes, filename="archivo.zip"):
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, filename)

        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(zip_bytes)

        rb_file = open(temp_file_path, 'rb')
        dir_file = {'File': rb_file}

        try:
            upload_data = {'form_id': id_forma_seleccionada, 'field_id': id_field}
            upload_url = self.lkf_api.post_upload_file(data=upload_data, up_file=dir_file)
            rb_file.close()
        except Exception as e:
            rb_file.close()
            os.remove(temp_file_path)
            print("Error al subir el archivo:", e)
            return {"error": "Fallo al subir el archivo"}

        try:
            file_url = upload_url['data']['file']
            update_file = {'file_name': filename, 'file_url': file_url}
        except KeyError:
            print('No se pudo obtener la URL del archivo')
            update_file = {"error": "Fallo al obtener la URL del archivo"}
        finally:
            os.remove(temp_file_path)

        return update_file


if __name__ == "__main__":
    acceso_obj = Accesos(settings, sys_argv=sys.argv)
    acceso_obj.console_run()

    data = acceso_obj.data.get('data', {})
    record_id = data.get('record_id', '')

    response = acceso_obj.create_pass_apple_wallet(record_id)

    sys.stdout.write(simplejson.dumps({
        'status': 101,
        'file_url': response
    }))