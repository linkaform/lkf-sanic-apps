# -*- coding: utf-8 -*-
"""Registro de empresas de Contratistas (RG-01).

Spec: clave10-sdk/specs/empresa/empresa-001-modelo-de-datos.md. Ficha de
diseño: lkf-claude/knowledge/modules/contratistas/contratistas_rg02_registro_wizard.md.

LinkaForm no permite crear una cuenta nueva por API, así que la empresa se
registra DENTRO de la cuenta Clave10 del account_id de la página pública (el
script corre con el API key de esa cuenta, sin sesión):

1. Valida todo del lado del back (RFC, CURP, contraseña, correo, dominio,
   términos) y que el RFC, el correo y el dominio no estén tomados.
2. Crea la empresa en Empresas (CT-0001 / CL-0001).
3. Crea el usuario con el alta con contraseña de UsersAdmin (queda activo, sin
   correo) y SIN empleado automático: ese camino le da todos los menús de
   guardia (Configuración Accesos).
4. Crea su registro en Empleados ligado a la empresa, para que su empresa
   activa sea la nueva.

Si falla el paso 3 o 4, la empresa queda Inactiva (no se borra) y el error
dice qué se alcanzó a crear. El dominio se guarda como reservado: no se
configura ningún subdominio. Menús del usuario: F0-04. Relación con la
empresa de la cuenta: R-02.
"""
import re
import unicodedata
from datetime import datetime, timedelta

import pytz

from .contratistas_contratos import _fecha, opt

PERFILES = ["Cliente", "Contratista"]
PERFILES_FUTUROS = ["Visitante", "Transportista"]
TIPOS_PERSONA = ["Moral", "Física"]
FOLIO_POR_PERFIL = {"Contratista": "CT", "Cliente": "CL"}
DIAS_REPSE_POR_VENCER = 60
TERMINOS_VERSION = "2026-11"
# Campos del domicilio fiscal de la CSF (sufijo de domicilio_* en Empresas).
DOMICILIO = ["cp", "tipo_vialidad", "vialidad", "num_exterior", "num_interior", "colonia", "localidad",
             "municipio", "estado", "entre_calle", "y_calle"]
ESTATUS_PADRON = ["Activo", "Inactivo"]
DOMINIOS_RESERVADOS = {"www", "app", "api", "admin", "web", "mail", "soporte", "clave10", "portal", "staging",
                       "dev", "test", "demo"}

RFC_MORAL = re.compile(r"^[A-ZÑ&]{3}\d{6}[A-Z0-9]{3}$")
RFC_FISICA = re.compile(r"^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$")
CURP_RE = re.compile(r"^[A-Z][AEIOUX][A-Z]{2}\d{6}[HMX][A-Z]{5}[A-Z0-9]\d$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalizar_dominio(s):
    """Mismas reglas que el diseño: minúsculas, sin acentos ni ñ, espacios y _ a
    guion, solo a-z0-9-, sin guiones dobles ni en las orillas."""
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    return re.sub(r"-{2,}", "-", s).strip("-")


def _fecha_rfc_valida(rfc, n):
    try:
        datetime.strptime(rfc[n:n + 6], "%y%m%d")
        return True
    except ValueError:
        return False


class RegistroMixin:
    """Se mezcla en Accesos junto con ContratosMixin."""

    def _reg_error(self, msg, status=400):
        return self.LKFException({"title": "Registro", "msg": msg, "status_code": status})

    def _reg_users_admin(self):
        from ..base.routes import users_admin_service  # singleton de la pantalla Usuarios
        return users_admin_service

    # ---------------------------------------------------------- validación

    def _reg_validar(self, d):
        errores = []
        perfil = (d.get("perfil") or "").strip()
        if perfil in PERFILES_FUTUROS:
            self._reg_error(f"El registro como {perfil} todavía no está disponible.", 422)
        if perfil not in PERFILES:
            errores.append("Elige el perfil: Cliente o Contratista.")
        tipo = (d.get("tipo_persona") or "").strip()
        tipo = "Física" if tipo.lower() in ("fisica", "física") else ("Moral" if tipo.lower() == "moral" else tipo)
        if tipo not in TIPOS_PERSONA:
            errores.append("Elige el tipo de persona: moral o física.")
        razon = " ".join(str(d.get("razon_social") or "").split())
        if not razon:
            errores.append("La razón social (o nombre completo) es obligatoria.")
        rfc = re.sub(r"\s", "", str(d.get("rfc") or "")).upper()
        patron, n = (RFC_FISICA, 4) if tipo == "Física" else (RFC_MORAL, 3)
        if not patron.match(rfc) or not _fecha_rfc_valida(rfc, n):
            errores.append(f"El RFC no es válido para persona {tipo.lower() or 'moral'} "
                           f"({13 if tipo == 'Física' else 12} caracteres con fecha válida).")
        curp = re.sub(r"\s", "", str(d.get("curp") or "")).upper()
        if tipo == "Física" and not CURP_RE.match(curp):
            errores.append("La CURP no es válida (18 caracteres).")
        rep = " ".join(str(d.get("representante_legal") or "").split())
        if tipo == "Moral" and not rep:
            errores.append("El representante legal es obligatorio en persona moral.")
        email = str(d.get("email") or "").strip().lower()
        if not EMAIL_RE.match(email):
            errores.append("El correo no es válido.")
        tel = re.sub(r"\D", "", str(d.get("telefono") or ""))
        if tel.startswith("52") and len(tel) == 12:
            tel = tel[2:]
        if len(tel) != 10:
            errores.append("El teléfono debe tener 10 dígitos.")
        direccion = " ".join(str(d.get("direccion") or "").split())
        if not direccion:
            errores.append("La dirección es obligatoria.")
        dominio = normalizar_dominio(d.get("dominio"))
        if tipo == "Moral" and not dominio:
            errores.append("El dominio es obligatorio en persona moral.")
        if dominio and not (3 <= len(dominio) <= 40):
            errores.append("El dominio debe tener entre 3 y 40 caracteres.")
        if dominio in DOMINIOS_RESERVADOS:
            errores.append(f"El dominio {dominio} está reservado; elige otro.")
        pw = str(d.get("password") or "")
        if len(pw) < 8 or not re.search(r"[A-Z]", pw) or not re.search(r"\d", pw) \
                or not re.search(r"[^A-Za-z0-9]", pw):
            errores.append("La contraseña debe tener al menos 8 caracteres, una mayúscula, un número y "
                           "un carácter especial.")
        if "password2" in d and d.get("password2") != pw:
            errores.append("Las contraseñas no coinciden.")
        if d.get("terminos") is not True:
            errores.append("Debes aceptar los Términos y el Aviso de Privacidad.")
        if errores:
            self._reg_error("\n".join(errores))
        return {"perfil": perfil, "tipo": tipo, "razon": razon, "rfc": rfc, "curp": curp, "rep": rep,
                "email": email, "tel": tel, "direccion": direccion, "dominio": dominio, "password": pw}

    def _reg_unicos(self, v):
        """RFC, dominio y correo libres en la cuenta."""
        f = self.ctr_f["empresas"]
        activa = {f"answers.{f['estatus']}": {"$ne": opt("Inactivo")}}
        if self._ctr_find(self.EMPRESAS_FORM, {f"answers.{f['rfc']}": v["rfc"], **activa}, one=True):
            self._reg_error("Ya hay una empresa registrada con ese RFC.", 409)
        if v["dominio"] and self._ctr_find(self.EMPRESAS_FORM, {f"answers.{f['dominio']}": v["dominio"], **activa},
                                           one=True):
            self._reg_error(f"El dominio {v['dominio']}.clave10.com ya está tomado.", 409)
        ua = self._reg_users_admin()
        uf = ua.user_fields
        rx = {"$regex": f"^{re.escape(v['email'])}$", "$options": "i"}
        if self.cr.find_one({"form_id": ua.usuarios_form, "deleted_at": {"$exists": False},
                             "$or": [{f"answers.{uf['email']}": rx}, {f"answers.{uf['username']}": rx}]},
                            {"_id": 1}):
            self._reg_error("Ya existe un usuario con ese correo.", 409)

    # -------------------------------------------------------------- pasos

    def _reg_folio(self, prefijo):
        f = self.ctr_f["empresas"]
        n = 0
        for r in self._ctr_find(self.EMPRESAS_FORM):
            m = re.match(rf"^{prefijo}-(\d+)$", str((r.get("answers") or {}).get(f["folio"]) or ""))
            if m:
                n = max(n, int(m.group(1)))
        return f"{prefijo}-{n + 1:04d}"

    def _reg_repse(self, repse):
        """Campos del REPSE (RG-03 lo prellena; omitido = Sin REPSE)."""
        f = self.ctr_f["empresas"]
        repse = repse if isinstance(repse, dict) else {}
        folio = str(repse.get("folio") or "").strip()
        ini, fin = _fecha(repse.get("inicio")), _fecha(repse.get("fin"))
        if not folio or not fin:
            return {f["repse_estatus"]: opt("Sin REPSE")}, "Pendiente"
        hoy = self._ctr_hoy()
        estatus = "Vencido" if fin < hoy else ("Por vencer" if fin - hoy <= timedelta(days=DIAS_REPSE_POR_VENCER)
                                               else "Vigente")
        out = {f["repse_folio"]: folio, f["repse_fin"]: fin.isoformat(), f["repse_estatus"]: opt(estatus)}
        if ini:
            out[f["repse_inicio"]] = ini.isoformat()
        actividades = [a for a in repse.get("actividades") or [] if isinstance(a, dict)]
        if actividades:
            out[f["actividades_stps"]] = [{f["actividad_clave"]: str(a.get("clave") or "").strip(),
                                           f["actividad_descripcion"]: str(a.get("descripcion") or "").strip()}
                                          for a in actividades]
        return out, folio

    def _reg_csf(self, csf, direccion):
        """Datos de la CSF (los que regresa leer_documento_registro) y la dirección
        capturada. Con domicilio de la CSF se guarda desglosado; sin él, la
        dirección capturada va en vialidad."""
        f = self.ctr_f["empresas"]
        csf = csf if isinstance(csf, dict) else {}
        dom = csf.get("domicilio") if isinstance(csf.get("domicilio"), dict) else {}
        out = {}
        for k in DOMICILIO:
            if dom.get(k):
                out[f[f"domicilio_{k}"]] = str(dom[k]).strip()
        if not out.get(f["domicilio_vialidad"]):
            out[f["domicilio_vialidad"]] = direccion
        for k in ("regimen_fiscal", "actividad_preponderante", "nombre_comercial"):
            if csf.get(k):
                out[f[k]] = str(csf[k]).strip()
        if csf.get("estatus_padron") in ESTATUS_PADRON:
            out[f["estatus_sat"]] = opt(csf["estatus_padron"])
        return out

    def _reg_crear_empresa(self, v, d):
        f = self.ctr_f["empresas"]
        repse_ans, repse_folio = self._reg_repse(d.get("repse"))
        folio = self._reg_folio(FOLIO_POR_PERFIL[v["perfil"]])
        a = {
            f["folio"]: folio, f["razon_social"]: v["razon"], f["rfc"]: v["rfc"],
            f["tipo_persona"]: opt(v["tipo"]), f["es_propia"]: opt("No"), f["estatus"]: opt("Activo"),
            f["perfil_registro"]: opt(v["perfil"]),
            # Zona del usuario (o México), como el resto de fechas de Clave10.
            f["terminos_aceptados_fecha"]: datetime.now(pytz.timezone((self.user or {}).get("timezone")
                                                                    or "America/Mexico_City")).strftime("%Y-%m-%d %H:%M:%S"),
            f["terminos_version"]: str(d.get("terminos_version") or TERMINOS_VERSION),
            f["contactos"]: [{
                f["contacto_nombre"]: v["rep"] or v["razon"],
                f["contacto_rol"]: opt("Representante legal"),
                f["contacto_telefono"]: v["tel"], f["contacto_email"]: v["email"],
            }],
            **repse_ans, **self._reg_csf(d.get("csf"), v["direccion"]),
        }
        if v["curp"] and v["tipo"] == "Física":
            a[f["curp"]] = v["curp"]
        if v["dominio"]:
            a[f["dominio"]] = v["dominio"]
        empresa_id = self._ctr_post(self.EMPRESAS_FORM, a, "registrar_empresa")
        if not empresa_id:
            self._reg_error("LinkaForm no regresó el id de la empresa.", 500)
        return empresa_id, folio, repse_folio, a

    def _reg_desactivar_empresa(self, empresa_id, answers):
        f = self.ctr_f["empresas"]
        try:
            self._ctr_patch(self.EMPRESAS_FORM, empresa_id, {**answers, f["estatus"]: opt("Inactivo")},
                            "registrar_empresa_rollback")
        except Exception:  # noqa: BLE001
            pass

    def _reg_crear_usuario(self, v):
        """Alta con contraseña (activa, sin correo, sin empleado automático). Regresa user_id."""
        ua = self._reg_users_admin()
        uf = ua.user_fields
        ua.create_user(name=v["rep"] if v["tipo"] == "Moral" else v["razon"], username=v["email"],
                       email=v["email"], phone=v["tel"], role=v["perfil"], password=v["password"])
        rec = self.cr.find_one({"form_id": ua.usuarios_form, "deleted_at": {"$exists": False},
                                f"answers.{uf['username']}": v["email"]}, {"answers": 1},
                               sort=[("created_at", -1)])
        user_id = ua._one(((rec or {}).get("answers") or {}).get(uf["user_id"]))
        if not user_id:
            self._reg_error("El usuario se dio de alta pero LinkaForm no regresó su id.", 500)
        return user_id

    def _reg_crear_empleado(self, v, user_id, empresa_id):
        ua = self._reg_users_admin()
        emp = self.Employee
        fe = self.ctr_f["empleados"]
        nombre = v["rep"] if v["tipo"] == "Moral" else v["razon"]
        answers = {
            ua.employee_fields["name"]: nombre,
            ua.employee_fields["status"]: "activo",
            fe["empresa_id"]: empresa_id, fe["empresa"]: v["razon"],
            **ua._employee_user_answers(nombre, v["email"], v["email"], user_id),
        }
        metadata = self.lkf_api.get_metadata(form_id=emp.EMPLEADOS)
        metadata.update({"answers": answers,
                         "properties": {"device_properties": {"System": "Script", "Module": "Accesos",
                                                              "Process": "Contratistas · registro"}}})
        # El catálogo Usuarios puede tardar en tener al usuario nuevo: mismo reintento del alta.
        res = ua.retry_catalog(lambda: self.lkf_api.post_forms_answers(metadata))
        if (res or {}).get("status_code") not in (200, 201, 202):
            raise RuntimeError(f"{(res or {}).get('status_code')} {(res or {}).get('json') or res}")
        return (res.get("json") or {}).get("id")

    # ---------------------------------------------------------------- API

    def registrar_empresa(self, datos):
        if not self.EMPRESAS_FORM:
            self._reg_error("El registro de empresas no está habilitado en esta cuenta.", 409)
        d = datos if isinstance(datos, dict) else {}
        v = self._reg_validar(d)
        self._reg_unicos(v)
        empresa_id, folio, repse_folio, empresa_ans = self._reg_crear_empresa(v, d)
        try:
            user_id = self._reg_crear_usuario(v)
        except Exception as e:  # noqa: BLE001
            self._reg_desactivar_empresa(empresa_id, empresa_ans)
            self._reg_error(f"No se pudo crear el usuario: {self._reg_users_admin()._error_text(e)[:300]}", 500)
        try:
            empleado_id = self._reg_crear_empleado(v, user_id, empresa_id)
        except Exception as e:  # noqa: BLE001
            self._reg_desactivar_empresa(empresa_id, empresa_ans)
            self._reg_error(f"El usuario {v['email']} (id {user_id}) se creó, pero falló su registro en "
                            f"Empleados; la empresa {folio} quedó inactiva. Hay que completarlo a mano: "
                            f"{str(e)[:300]}", 500)
        return {
            "empresa": {"id": empresa_id, "folio": folio, "razon_social": v["razon"], "rfc": v["rfc"]},
            "usuario": {"email": v["email"], "user_id": user_id, "empleado_id": empleado_id},
            "perfil": v["perfil"],
            "dominio": f"{v['dominio']}.clave10.com" if v["dominio"] else None,
            "repse": repse_folio,
            "completitud": 25,
        }

    # ------------------------------------------------- RG-03-B: prellenado

    def leer_documento_registro(self, archivo, tipo, rfc=None):
        """Lee el REPSE o la CSF del wizard y regresa los datos con la forma que
        acepta registrar_empresa (`repse` / `csf`) más lo que el paso 5 prellena.

        Público (registro sin sesión): el prompt NO lleva datos de la cuenta.
        No guarda nada; el archivo lo sube el front."""
        tipo = str(tipo or "").upper()
        if tipo not in LECTURA_PROMPTS:
            self._reg_error("tipo debe ser REPSE o CSF.")
        if not isinstance(archivo, dict) or not str(archivo.get("file_url") or "").startswith("http"):
            self._reg_error("Falta el archivo (file_url) a leer.")
        if not self.ai:
            self._reg_error("La lectura de documentos no está disponible en esta cuenta.", 409)
        try:
            ia = self._dia_llamar(archivo, LECTURA_PROMPTS[tipo], None)
        except Exception as e:  # noqa: BLE001
            self._reg_error(f"No se pudo leer el documento: {str(e)[:300]}", 502)
        ia = ia if isinstance(ia, dict) else {}
        legible = bool(ia.get("legible"))
        detectado = str(ia.get("tipo_documento") or "").upper()
        alertas = []
        if not legible:
            alertas.append({"nivel": "error", "titulo": "No pudimos leer el documento",
                            "detalle": "Sube un PDF más nítido o captura los datos a mano."})
            return {"legible": False, "tipo": tipo, "alertas": alertas}
        if detectado and detectado != tipo:
            alertas.append({"nivel": "error", "titulo": f"Esto no parece {('un ' if tipo == 'REPSE' else 'una ')}{tipo}",
                            "detalle": f"El documento parece ser {ia.get('tipo_documento')}."})
        rfc_doc = re.sub(r"[^A-Z0-9&Ñ]", "", str(ia.get("rfc") or "").upper()) or None
        if rfc and rfc_doc and rfc_doc != re.sub(r"\s", "", str(rfc)).upper():
            alertas.append({"nivel": "error", "titulo": "El RFC no coincide",
                            "detalle": f"El documento es del RFC {rfc_doc} y capturaste {str(rfc).upper()}."})
        nombre = {k: (str(ia.get(k)).strip() if ia.get(k) else None)
                  for k in ("razon_social", "nombre", "primer_apellido", "segundo_apellido")}
        out = {"legible": True, "tipo": tipo, "rfc": rfc_doc,
               "tipo_persona": "Física" if rfc_doc and len(rfc_doc) == 13 else ("Moral" if rfc_doc else None),
               **nombre, "alertas": alertas}
        if not out["razon_social"] and nombre["nombre"]:
            out["razon_social"] = " ".join(x for x in (nombre["nombre"], nombre["primer_apellido"],
                                                       nombre["segundo_apellido"]) if x)

        if tipo == "REPSE":
            ini, fin = _fecha(ia.get("inicio")), _fecha(ia.get("fin"))
            hoy = self._ctr_hoy()
            meses = ((fin.year - hoy.year) * 12 + fin.month - hoy.month) if fin else None
            if fin and fin < hoy:
                alertas.append({"nivel": "error", "titulo": "El REPSE está vencido",
                                "detalle": f"Su vigencia terminó el {fin.isoformat()}."})
            out["repse"] = {
                "folio": str(ia.get("folio") or "").strip() or None,
                "inicio": ini.isoformat() if ini else None, "fin": fin.isoformat() if fin else None,
                "meses_restantes": max(0, meses) if meses is not None else None,
                "actividades": [{"clave": str(a.get("clave") or "").strip(), "descripcion": str(a.get("descripcion") or "").strip()}
                                for a in ia.get("actividades") or [] if isinstance(a, dict)],
            }
            if ia.get("representante_legal"):
                out["representante_legal"] = str(ia["representante_legal"]).strip()
            return out

        dom_ia = ia.get("domicilio") if isinstance(ia.get("domicilio"), dict) else {}
        dom = {k: str(dom_ia[k]).strip() for k in DOMICILIO if dom_ia.get(k)}
        padron = next((e for e in ESTATUS_PADRON if str(ia.get("estatus_padron") or "").strip().lower().startswith(e.lower())), None)
        if padron == "Inactivo":
            alertas.append({"nivel": "aviso", "titulo": "Estatus en el padrón: Inactivo",
                            "detalle": "El SAT reporta al contribuyente como inactivo."})
        correo = str(ia.get("correo") or "").strip().lower() or None
        out["csf"] = {"domicilio": dom, "estatus_padron": padron,
                      "regimen_fiscal": str(ia.get("regimen_fiscal") or "").strip() or None,
                      "actividad_preponderante": str(ia.get("actividad_preponderante") or "").strip() or None}
        out["curp"] = re.sub(r"\s", "", str(ia.get("curp") or "")).upper() or None
        out["correo"] = correo
        # Prellenado del paso 5 (mismas reglas que el diseño).
        out["direccion"] = ", ".join(x for x in (
            " ".join(x for x in (dom.get("vialidad"), dom.get("num_exterior")) if x),
            f"Int. {dom['num_interior']}" if dom.get("num_interior") else None,
            dom.get("colonia"), f"C.P. {dom['cp']}" if dom.get("cp") else None,
            dom.get("municipio"), dom.get("estado")) if x) or None
        out["dominio_sugerido"] = normalizar_dominio(correo.split("@", 1)[1].split(".", 1)[0]) \
            if correo and "@" in correo else None
        return out


LECTURA_COMUN = (
    "Lee el documento adjunto. Responde SOLO un objeto JSON. Si un dato no aparece o no se lee con claridad usa "
    "null; nunca lo inventes. Si el texto no se lee con claridad, legible=false.\n"
    '"legible": true|false, "tipo_documento": "REPSE" | "CSF" | "Otro", "rfc": "...", "razon_social": "... (persona '
    'moral) o null", "nombre": "... (persona física) o null", "primer_apellido": "...", "segundo_apellido": "...",\n'
)
LECTURA_PROMPTS = {
    "REPSE": LECTURA_COMUN + (
        '"folio": "número de registro REPSE", "inicio": "YYYY-MM-DD (fecha de registro o inicio de vigencia)", '
        '"fin": "YYYY-MM-DD (vencimiento del registro)", "representante_legal": "... o null", '
        '"actividades": [{"clave": "...", "descripcion": "..."}] (actividades autorizadas ante la STPS)'),
    "CSF": LECTURA_COMUN + (
        '"curp": "... (persona física) o null", "correo": "correo electrónico registrado o null", '
        '"estatus_padron": "Activo | Inactivo", "regimen_fiscal": "...", "actividad_preponderante": "... o null", '
        '"domicilio": {"cp": "...", "tipo_vialidad": "...", "vialidad": "...", "num_exterior": "...", '
        '"num_interior": "...", "colonia": "...", "localidad": "...", "municipio": "...", "estado": "...", '
        '"entre_calle": "...", "y_calle": "..."}'),
}
