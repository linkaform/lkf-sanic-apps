# -*- coding: utf-8 -*-
'''
Licencia BSD
Copyright (c) 2024 Infosync / LinkaForm.
Todos los derechos reservados.

Se permite la redistribución y el uso en formas de código fuente y binario, con o sin modificaciones, siempre que se cumplan las siguientes condiciones:

1. Se debe conservar el aviso de copyright anterior, esta lista de condiciones y el siguiente descargo de responsabilidad en las redistribuciones del código fuente.
2. Se debe reproducir el aviso de copyright anterior, esta lista de condiciones y el siguiente descargo de responsabilidad en la documentación y/u otros materiales proporcionados con las distribuciones en formato binario.
3. Ni el nombre del Infosync ni los nombres de sus colaboradores pueden ser utilizados para respaldar o promocionar productos derivados de este software sin permiso específico previo por escrito.
'''
# Backend de la pantalla publica "Invitacion de contratista" del front clave10.
#
# Modelo: el cliente INVITA a un contratista creando un registro del form
# Contratistas con su correo. El contratista abre la liga del correo, se
# identifica con SU PROPIA cuenta de LinkaForm, acepta la invitacion, y al
# aceptar se escribe su account_id en el campo "Id Cuenta" del registro del
# cliente, junto con el perfil y los documentos que captura en la pagina.
#
# El account_id NUNCA se toma del payload: sale del claim `parent_id` del JWT
# del contratista, verificado con firma RS256 (ver _caller_from_jwt).

import re

import jwt as pyjwt
from bson import ObjectId
from bson.errors import InvalidId

from lkf_addons.base.app import Base


class Contratistas(Base):

    # Regex deliberadamente estricta: rechaza & # ? / , ; y espacios porque
    # get_user_by_email interpola el correo en un query string SIN urlencode
    # (linkaform_api/utils.py:471 -> url.format(email)), asi que un "correo"
    # con & inyectaria filtros en la peticion a Django.
    EMAIL_RE = re.compile(r'^[^@\s,;&#?/=%]+@[^@\s,;&#?/=%]+\.[A-Za-z]{2,}$')

    # Hosts permitidos para los archivos que llegan del front. El upload
    # (clave10 src/lib/get-upload-image.tsx -> /api/infosync/cloud_upload/) es
    # publico y sin auth, asi que sin esta validacion el contratista podria
    # guardar una URL arbitraria en el registro del cliente, que despues el
    # personal va a abrir.
    ALLOWED_FILE_HOSTS = (
        'linkaform.com',
        'backblazeb2.com',
        'amazonaws.com',
    )

    MAX_FILES_POR_CAMPO = 5

    # Identidad con la que se leen/escriben los datos DEL CLIENTE.
    #
    # Es obligatorio pasarla explicitamente en cada llamada a lkf_api: por
    # default esos metodos usan config['JWT_KEY'], y el decorador @reload_user
    # (addons/base/tools.py:20, usado por accesos/service.py) lo SOBREESCRIBE
    # con el token de quien llama sobre el singleton compartido y nunca lo
    # restaura. Es decir, JWT_KEY puede traer el token de cualquier request
    # anterior de cualquier otra ruta del contenedor.
    #
    # APIKEY_JWT_KEY siempre trae el JWT del API key de la cuenta
    # (linkaform_api/lkf_base/base.py:775), asi que fijarla vuelve estas
    # operaciones inmunes a esa fuga de identidad.
    #
    # Este modulo NO debe usar @reload_user por la misma razon; la identidad
    # de quien llama se obtiene sin mutar nada, en _caller_from_jwt.
    JWT_CLIENTE = 'APIKEY_JWT_KEY'

    def __init__(self, settings, folio_solicitud=None, sys_argv=None, use_api=False, **kwargs):
        # La firma tiene que conservar folio_solicitud/**kwargs:
        # app/modules/contratistas/items/scripts/Contratistas/contratistas_utils.py
        # hereda de esta clase y llama super().__init__(settings, sys_argv=..., use_api=...).
        super().__init__(settings, sys_argv=sys_argv, use_api=use_api)
        self.kwargs['MODULES'] = self.kwargs.get('MODULES', [])
        if self.__class__.__name__ not in kwargs:
            self.kwargs['MODULES'].append(self.__class__.__name__)

        # forms
        self.CONTRATISTAS = self.lkm.form_id('contratistas', 'id')

        # OJO: dict LOCAL, no self.f.update(). 'email', 'telefono' y
        # 'razon_social' YA existen en lkf_addons/base/app.py y self.f es
        # compartido por el singleton que routes.py crea al importar el modulo
        # -> pisarlos provoca perdida silenciosa de datos en otros modulos.
        # Ver lkf-claude/knowledge/patterns/self_f_label_collision.md
        self.contratista_fields = {
            'razon_social':          '65fc814fb170488cf4d44c51',  # text,     req
            'rfc':                   '65fc814fb170488cf4d44c52',  # text,     req
            'email_contratista':     '65fc814fb170488cf4d44c53',  # email,    req
            'telefono_contratista':  '663cebbe200dc8983df27573',  # text,     req
            'id_cuenta':             '664ce7e2d266d1c0b7e70125',  # integer,  opt
            'servicios':             '65fc814fb170488cf4d44c54',  # checkbox, req
            'estatus_solicitud':     '664ce0d8eb5090c56a684eb0',  # select,   req
            'estatus_contratista':   '65fc814fb170488cf4d44c55',  # radio  <- NUNCA escribir
            'alta_fiscal':           '664cde59f7796cf5a926fba6',  # files
            'identificacion':        '664cdeb6b10373f0783885d2',  # files
            'comprobante_domicilio': '664cdeb6b10373f0783885d3',  # files
        }

        # Los <value> del XML conservan el acento en 'construcción'
        # (contratistas.xml:457). Un .lower().replace(' ','_') generico dejaria
        # entrar variantes sin acento como basura en un checkbox requerido, asi
        # que se usa un mapa explicito.
        self.SERVICIOS_VALIDOS = {
            'mantenimiento': 'mantenimiento',
            'construccion':  'construcción',
            'construcción':  'construcción',
            'limpieza':      'limpieza',
        }

        # Etiquetas para los mensajes de "falta informacion" al enviar.
        self.LABELS_REQUERIDOS = {
            'razon_social':          'Razón social',
            'rfc':                   'RFC',
            'telefono_contratista':  'Teléfono',
            'servicios':             'Servicios a Prestar',
            'alta_fiscal':           'Alta de Situación Fiscal',
            'identificacion':        'Identificación del Representante Legal',
            'comprobante_domicilio': 'Comprobante de Domicilio',
        }

    # ============================================
    # Helpers internos
    # ============================================

    def _assert_module(self):
        """ lkm.form_id regresa {} (y solo imprime un warning) cuando el modulo
        no esta registrado en LKFModules de la cuenta. Sin este fail-fast el
        $match saldria con form_id={} y devolveria 'no encontrado' siempre.
        """
        if not self.CONTRATISTAS:
            raise self.LKFException({
                'msg': 'El módulo Contratistas no está instalado en esta cuenta.',
                'status_code': 500})

    def _clean_email(self, email):
        email = (email or '').strip().lower()
        if not self.EMAIL_RE.match(email):
            raise self.LKFException({
                'msg': 'El correo no tiene un formato válido.', 'status_code': 400})
        return email

    def _oid(self, record_id):
        try:
            return ObjectId(record_id)
        except (InvalidId, TypeError):
            # Sin esto, bson.InvalidId sube como 500 por middleware/error_handlers.py
            raise self.LKFException({
                'msg': 'La invitación no es válida.', 'status_code': 400})

    def _find_platform_user(self, email):
        """ Busca usuarios de plataforma por correo, con coincidencia EXACTA.

        get_user_by_email pega a /api/infosync/user/?email__contains={0}
        (linkaform_api/urls.py:167) y __contains es SUBSTRING: 'ana@x.com'
        matchea 'mariana@x.com'. Por eso se filtra despues.
        """
        email = self._clean_email(email)
        users = self.lkf_api.get_user_by_email(
            email, jwt_settings_key=self.JWT_CLIENTE) or []
        exactos = [u for u in users
                   if (u.get('email') or '').strip().lower() == email]
        if exactos:
            return exactos
        # Segundo intento por conexiones: get_user_connection pega a
        # /api/infosync/user_connection/load_user/?email= (utils.py:829), que
        # resuelve usuarios FUERA del roster de la cuenta -- justo el caso de un
        # contratista con cuenta propia. El shape de la respuesta no esta
        # verificado contra una cuenta real, asi que nunca debe tumbar la
        # compuerta: en duda, se reporta "no existe" y el login decide.
        try:
            conexion = self.lkf_api.get_user_connection(
                email, jwt_settings_key=self.JWT_CLIENTE)
        except Exception:
            return []
        if not conexion:
            return []
        return conexion if isinstance(conexion, list) else [conexion]

    def _caller_from_jwt(self, auth_header):
        """ Decodifica y VERIFICA el JWT de quien llama.

        A proposito NO usa self.decode_jwt(): ese lee self.config['JWT_KEY']
        (linkaform_api/lkf_object.py:107-114), que en Sanic es el JWT del dueño
        del APIKEY y esta COMPARTIDO por el singleton del servicio -- pisarlo
        por request seria un race que rompe la auth de todas las demas rutas.

        El claim `parent_id` es el account_id del usuario; mismo uso que
        lkf_addons/accesos/app.py:2654 para armar el ?user= de estas ligas.
        """
        if not auth_header:
            raise self.LKFException({
                'msg': 'Necesitas iniciar sesión para continuar.', 'status_code': 401})
        token = auth_header.split(' ')[-1].strip()
        try:
            with open('/etc/ssl/certs/lkf_jwt_key.pub', 'r') as fh:
                pub_key = fh.read()
            claims = pyjwt.decode(token, pub_key, algorithms='RS256')
        except Exception:
            raise self.LKFException({
                'msg': 'Tu sesión no es válida o expiró. Inicia sesión de nuevo.',
                'status_code': 401})
        account_id = claims.get('parent_id') or claims.get('account_id')
        return {
            'email': (claims.get('email') or '').strip().lower(),
            'user_id': claims.get('user_id') or claims.get('id'),
            'account_id': account_id,
        }

    def _get_record(self, record_id):
        """ Lee el registro de la invitacion por su _id. """
        self._assert_module()
        f = self.contratista_fields
        query = [
            {'$match': {
                '_id': self._oid(record_id),
                'form_id': self.CONTRATISTAS,
                'deleted_at': {'$exists': False},
            }},
            {'$project': {
                '_id': 1,
                'folio': '$folio',
                'razon_social':          f"$answers.{f['razon_social']}",
                'rfc':                   f"$answers.{f['rfc']}",
                'email_contratista':     f"$answers.{f['email_contratista']}",
                'telefono':              f"$answers.{f['telefono_contratista']}",
                'id_cuenta':             f"$answers.{f['id_cuenta']}",
                'servicios':             f"$answers.{f['servicios']}",
                'estatus_solicitud':     f"$answers.{f['estatus_solicitud']}",
                'alta_fiscal':           f"$answers.{f['alta_fiscal']}",
                'identificacion':        f"$answers.{f['identificacion']}",
                'comprobante_domicilio': f"$answers.{f['comprobante_domicilio']}",
            }},
            {'$limit': 1},
        ]
        record = self.format_cr(self.cr.aggregate(query), get_one=True)
        if not record:
            raise self.LKFException({
                'msg': 'No encontramos esta invitación.', 'status_code': 404})
        record['record_id'] = str(record.pop('_id'))
        return record

    def _assert_invitado(self, record, email):
        """ El correo tiene que ser EL de la invitacion.

        Mensaje generico y mismo status para "no coincide": no confirmamos ni
        negamos nada del registro, para que la ruta no sirva de oraculo para
        adivinar record_ids validos.
        """
        record_email = (record.get('email_contratista') or '').strip().lower()
        if not record_email or record_email != self._clean_email(email):
            raise self.LKFException({
                'msg': 'Esta invitación no corresponde a ese correo. '
                       'Revisa el enlace que recibiste.',
                'status_code': 403})

    def _assert_owns_record(self, record, caller):
        """ Autorizacion de las rutas que leen/escriben el registro. """
        record_email = (record.get('email_contratista') or '').strip().lower()
        if record_email and record_email == caller['email']:
            return True
        id_cuenta = record.get('id_cuenta')
        if id_cuenta and caller.get('account_id'):
            try:
                if int(id_cuenta) == int(caller['account_id']):
                    return True
            except (TypeError, ValueError):
                pass
        raise self.LKFException({
            'msg': 'Esta invitación no corresponde a tu cuenta.', 'status_code': 403})

    def _clean_files(self, files, label):
        """ Normaliza un campo `files` y valida el host de cada archivo. """
        if isinstance(files, dict):
            files = [files]
        if not isinstance(files, list):
            raise self.LKFException({
                'msg': f'El formato de los archivos de "{label}" no es válido.',
                'status_code': 400})
        if len(files) > self.MAX_FILES_POR_CAMPO:
            raise self.LKFException({
                'msg': f'Máximo {self.MAX_FILES_POR_CAMPO} archivos en "{label}".',
                'status_code': 400})
        limpios = []
        for item in files:
            if not isinstance(item, dict):
                continue
            file_url = (item.get('file_url') or '').strip()
            if not file_url:
                continue
            if not self._host_permitido(file_url):
                raise self.LKFException({
                    'msg': f'Uno de los archivos de "{label}" no se subió correctamente. '
                           f'Vuelve a cargarlo.',
                    'status_code': 400})
            limpios.append({
                'file_url': file_url,
                'file_name': (item.get('file_name') or '').strip(),
            })
        return limpios

    def _host_permitido(self, url):
        match = re.match(r'^https://([^/:?#]+)', url or '')
        if not match:
            return False
        host = match.group(1).lower()
        return any(host == dom or host.endswith('.' + dom)
                   for dom in self.ALLOWED_FILE_HOSTS)

    def _faltantes(self, record, answers):
        """ Valida completitud EN EL SERVIDOR (zod en el front es conveniencia).
        Mezcla lo que ya esta guardado con lo que viene en este patch.
        """
        f = self.contratista_fields
        pendientes = []
        for key, label in self.LABELS_REQUERIDOS.items():
            nuevo = answers.get(f[key], None)
            actual = record.get('telefono') if key == 'telefono_contratista' \
                else record.get(key)
            valor = nuevo if nuevo is not None else actual
            if not valor:
                pendientes.append(label)
        return pendientes

    # ============================================
    # Rutas publicas (sin JWT del contratista)
    # ============================================

    def check_invitacion(self, record_id='', email=''):
        """ Valida la invitacion y dice si ese correo ya tiene usuario.

        `user_exists` es orientativo: la consulta corre con el APIKEY de la
        cuenta del CLIENTE, asi que probablemente solo ve usuarios de esa
        cuenta y un contratista con cuenta en otro lado saldria como que no
        existe. El front debe tolerar que el login funcione de todas formas.
        """
        record = self._get_record(record_id)
        self._assert_invitado(record, email)
        return {
            'invitacion_valida': True,
            'razon_social': record.get('razon_social') or '',
            'email': (record.get('email_contratista') or '').strip().lower(),
            'ya_aceptada': bool(record.get('id_cuenta')),
            'estatus_solicitud': record.get('estatus_solicitud') or '',
            'user_exists': bool(self._find_platform_user(email)),
        }

    def crear_cuenta_contratista(self, **kwargs):
        """ FASE 2 -- crear la cuenta del contratista desde la pagina.

        Bloqueado a proposito: no existe endpoint de alta de cuenta
        independiente. `linkaform_api/urls.py` get_users_url() solo expone
        create_user (POST /api/infosync/user_admin/), que crea un SUB-USUARIO
        de la cuenta dueña del APIKEY -- el modelo equivocado, porque aqui el
        contratista tiene que ser dueño de su propia cuenta para poder servir a
        varios clientes.

        Cuando la plataforma exponga el alta de cuenta, este es el UNICO metodo
        que cambia: debe devolver {'account_id': <int>} y nada mas.
        Mientras, el front manda al signup de LinkaForm y regresa a la liga.
        """
        raise self.LKFException({
            'msg': 'El registro en línea todavía no está disponible. '
                   'Crea tu cuenta en LinkaForm y vuelve a abrir esta invitación.',
            'status_code': 501})

    # ============================================
    # Rutas con JWT del contratista
    # ============================================

    def aceptar_invitacion(self, record_id='', auth_header=None):
        """ El contratista acepta: se escribe SU account_id en el registro del
        cliente. Idempotente.
        """
        caller = self._caller_from_jwt(auth_header)
        record = self._get_record(record_id)
        self._assert_invitado(record, caller['email'])

        account_id = caller.get('account_id')
        if not account_id:
            raise self.LKFException({
                'msg': 'No pudimos identificar tu cuenta. Vuelve a iniciar sesión.',
                'status_code': 401})

        ya = record.get('id_cuenta')
        if ya and int(ya) == int(account_id):
            return {'record_id': record['record_id'],
                    'account_id': int(account_id), 'aceptada': True, 'nueva': False}
        if ya:
            raise self.LKFException({
                'msg': 'Esta invitación ya fue aceptada por otra cuenta.',
                'status_code': 409})

        f = self.contratista_fields
        answers = {f['id_cuenta']: int(account_id)}
        if not record.get('estatus_solicitud'):
            answers[f['estatus_solicitud']] = 'en_proceso'
        res = self.lkf_api.patch_multi_record(
            answers=answers, form_id=self.CONTRATISTAS, record_id=[record['record_id']],
            jwt_settings_key=self.JWT_CLIENTE)
        if res.get('status_code') not in (200, 201, 202):
            raise self.LKFException({
                'msg': 'No pudimos registrar tu aceptación. Intenta de nuevo.',
                'status_code': 400})
        return {'record_id': record['record_id'],
                'account_id': int(account_id), 'aceptada': True, 'nueva': True}

    def get_contratista_by_id(self, record_id='', auth_header=None):
        """ Detalle del registro para precargar el wizard. """
        caller = self._caller_from_jwt(auth_header)
        record = self._get_record(record_id)
        self._assert_owns_record(record, caller)
        record['servicios'] = record.get('servicios') or []
        for key in ('alta_fiscal', 'identificacion', 'comprobante_domicilio'):
            record[key] = record.get(key) or []
        return record

    def update_contratista(self, record_id='', razon_social=None, rfc=None,
                           telefono=None, servicios=None, alta_fiscal=None,
                           identificacion=None, comprobante_domicilio=None,
                           marcar_completada=False, auth_header=None):
        """ Guardado parcial del perfil y los documentos.

        Solo escribe los campos de la whitelist. `estatus_contratista`
        (65fc...c55) e `id_cuenta` NUNCA se aceptan del payload: el primero es
        la decision de autorizacion del cliente (contratistas_rules.xml lo
        restringe al user 20) y dispara la action_id 12 del workflow que
        sincroniza al catalogo -- aceptarlo permitiria auto-autorizarse. El
        segundo lo escribe unicamente aceptar_invitacion.
        """
        f = self.contratista_fields
        caller = self._caller_from_jwt(auth_header)
        record = self._get_record(record_id)
        self._assert_owns_record(record, caller)

        if record.get('estatus_solicitud') == 'completada' and not marcar_completada:
            raise self.LKFException({
                'msg': 'Esta solicitud ya fue enviada como completada.',
                'status_code': 409})

        answers = {}
        if razon_social is not None:
            answers[f['razon_social']] = (razon_social or '').strip()
        if rfc is not None:
            answers[f['rfc']] = (rfc or '').strip().upper()
        if telefono is not None:
            answers[f['telefono_contratista']] = str(telefono or '').strip()

        if servicios is not None:
            if isinstance(servicios, str):
                servicios = [servicios]
            valores = []
            for item in servicios or []:
                clave = (item or '').strip().lower().replace(' ', '_')
                if clave not in self.SERVICIOS_VALIDOS:
                    raise self.LKFException({
                        'msg': f'Servicio no válido: {item}', 'status_code': 400})
                valor = self.SERVICIOS_VALIDOS[clave]
                if valor not in valores:
                    valores.append(valor)
            if not valores:
                raise self.LKFException({
                    'msg': 'Selecciona al menos un servicio a prestar.',
                    'status_code': 400})
            answers[f['servicios']] = valores

        for key, files in (('alta_fiscal', alta_fiscal),
                           ('identificacion', identificacion),
                           ('comprobante_domicilio', comprobante_domicilio)):
            if files is None:
                continue
            answers[f[key]] = self._clean_files(files, self.LABELS_REQUERIDOS[key])

        if marcar_completada:
            pendientes = self._faltantes(record, answers)
            if pendientes:
                raise self.LKFException({
                    'msg': 'Falta información: ' + ', '.join(pendientes),
                    'status_code': 400})
            answers[f['estatus_solicitud']] = 'completada'
        elif not record.get('estatus_solicitud'):
            answers[f['estatus_solicitud']] = 'en_proceso'

        if not answers:
            return {'record_id': record['record_id'], 'updated': False,
                    'status': record.get('estatus_solicitud') or ''}

        res = self.lkf_api.patch_multi_record(
            answers=answers, form_id=self.CONTRATISTAS, record_id=[record['record_id']],
            jwt_settings_key=self.JWT_CLIENTE)
        if res.get('status_code') not in (200, 201, 202):
            raise self.LKFException({
                'msg': 'No se pudo guardar tu información. Intenta de nuevo.',
                'status_code': 400})
        return {
            'record_id': record['record_id'],
            'updated': True,
            'status': answers.get(f['estatus_solicitud'], record.get('estatus_solicitud') or ''),
        }
