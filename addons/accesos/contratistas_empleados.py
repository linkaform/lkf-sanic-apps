"""Empleados de Mi Empresa (ME-03-B).

Spec: clave10-sdk/specs/empresa/empresa-001-modelo-de-datos.md (forma Empleados
existente + página Contratista). Ficha: lkf-claude contratistas_me03_empleados.md.
Contrato con el front: EmpleadoContratista / EmpleadoInput en
clave10/src/types/contratistas/empresa.ts.

- Se reusa la forma Empleados. empresa_id vacío = empresa propia, así que los
  empleados de siempre de la cuenta salen en la empresa propia.
- Ver empleados de otra empresa solo si hay relación con ella (solo lectura);
  crear y editar solo en la empresa activa.
- CURP única en toda la cuenta. Eliminar = Inactivo (no se borra).
- La cuenta del empleado se liga a un usuario existente o se crea con el alta
  de Usuarios (UsersAdmin.create_user, manda la liga de activación).
- Cumplimiento = filas del motor (ME-15) del empleado; sin filas = null.
- Puesto es un catálogo de la forma: se lee, no se escribe (ni en la carga masiva).

Detalle del empleado (ME-04-B):
- Generales: datos personales y de contratación de la forma; domicilio,
  compañía y jefe directo son catálogos (solo lectura).
- Documentos: requerimientos de sus perfiles + filas del motor (contratos y
  asignados a la relación), cruzados con sus documentos (ME-06-B).
- Configuraciones: QR (id del empleado; inactivo si está desactivado o vetado),
  veto con motivo, preferencias (sin efecto todavía salvo Disponible para
  contratos) y restaurar contraseña (UsersAdmin.reset_password).
- Centros múltiples con áreas quedan para ME-02: aquí solo centro_trabajo.

Contratos del empleado (ME-05-B):
- El contrato guarda un renglón por (empleado, perfil). Ligar, editar perfiles
  y remover rehacen esos renglones con _ctr_guardar_cambio (historial
  "Empleados" y motor ME-15). Los perfiles nuevos se suman al empleado.
- Solo se liga a contratos vigentes donde la empresa del empleado es la
  contratista; no se liga a un empleado inactivo, vetado o no disponible.
- Sanciones del empleado: con la forma de R-07.
"""
import base64
import csv
import io
import re
import unicodedata

import requests

from .contratistas_contratos import ESTATUS as ESTATUS_CONTRATO
from .contratistas_contratos import _fecha, _int, _num, label, opt
from .contratistas_cumplimiento import ESTADOS, ESTADOS_MANUALES, porcentaje
from .contratistas_relaciones import CONTRATO_NO_VIGENTE

ESTATUS = ["Activo", "Inactivo"]
CURP_RE = re.compile(r"^[A-Z][AEIOUX][A-Z]{2}\d{6}[HMX][A-Z]{5}[A-Z\d]\d$")
RFC_RE = re.compile(r"^[A-ZÑ&]{4}\d{6}[A-Z\d]{3}$")
NSS_RE = re.compile(r"^\d{11}$")
TEL_RE = re.compile(r"^\d{10}$")
ROL_EMPLEADO = "Empleado"
MAX_ARCHIVOS_IA = 6
MAX_CARGA_BYTES = 50 * 1024 * 1024
MAX_FILAS = 1000
COLUMNAS = {  # encabezado normalizado -> clave
    "nombre completo": "nombre", "nombre": "nombre", "curp": "curp", "rfc": "rfc", "nss": "nss",
    "puesto": "puesto",
}
# Campos de la forma Empleados que no están en employee_fields (dict LOCAL).
EMPLEADO_EXTRA = {
    "estado_civil": "663bcd72cb24017b604d7f26",
    "tipo_contrato": "663fa630583de096e9326cc0",
    "fecha_ingreso": "663bcd72cb24017b604d7f28",
    "vacaciones": "663fa630583de096e9326cc3",
    "numero_empleado": "663bcd72cb24017b604d7f27",
    "nombre_direccion": "663a7e0fe48382c5b1230901",
    "direccion": "663a7e0fe48382c5b1230902",
    "colonia": "663a7f79e48382c5b123090a",
    "estado": "663a7dd6e48382c5b12308ff",
    "pais": "663a7ca6e48382c5b12308fa",
    "compania": "663a8153e48382c5b1230918",
    "jefe_directo": "663bd36eb19b7fb7d9e97ccb",
}
GENERO = {"Femenino": "femenino", "Masculino": "masculino"}
ESTADO_CIVIL = {"Soltero(a)": "soltero(a)", "Casado(a)": "casado(a)", "Viudo(a)": "viudo(a)",
                "Unión libre": "unión_libre"}
TIPO_CONTRATO = {"Permanente": "permanente", "Eventual": "eventual", "Planta": "planta", "Becario": "becario"}
PREFERENCIAS = ("notificaciones_correo", "acceso_app", "checkin_foto")
URGENCIA = ["Rechazado", "Vencido", "Por subir", "Por revisar", "Aceptado"]
ESTADO_MOTOR_A_DOC = {"Cumplido": "Aceptado", "En ceros": "Aceptado", "Por revisar": "Por revisar",
                      "Rechazado": "Rechazado", "Vencido": "Vencido", "Por subir": "Por subir"}
TIPOS_DOC_EMPLEADO = ["INE", "CURP", "Comprobante de domicilio", "Constancia de situación fiscal", "CV", "Otro"]

PROMPT_EMPLEADO = """Analiza el documento adjunto. Es un documento personal de un empleado en México.

Responde con este JSON:
{{
  "legible": true|false,
  "tipo_documento": uno de {tipos},
  "confianza": 0-100,
  "nombre": "nombre completo de la persona tal como aparece (nombre(s) y apellidos) o null",
  "curp": "CURP de 18 caracteres o null",
  "rfc": "RFC de persona física (13 caracteres) o null",
  "nss": "número de seguridad social (11 dígitos) o null"
}}"""


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _up(v):
    return re.sub(r"\s+", "", str(v or "")).upper()


def _digitos(v):
    s = str(v or "").strip()
    if re.fullmatch(r"\d+\.0", s):  # Excel guarda el NSS como número
        s = s[:-2]
    return re.sub(r"\D", "", s)


def _uno(v):
    """Los catalog-detail de LinkaForm se guardan como lista."""
    if isinstance(v, list):
        return v[0] if v else None
    return v


class EmpleadosMixin:
    """Se mezcla en Accesos (usa self.Employee, helpers _ctr_*, el motor y la IA de F0-11)."""

    def _emp_error(self, msg, status=400):
        return self.LKFException({"title": "Empleados", "msg": msg, "status_code": status})

    def _emp_mod(self):
        emp = getattr(self, "Employee", None)
        if not emp or not getattr(emp, "EMPLEADOS", None):
            self._emp_error("La forma Empleados no está instalada en esta cuenta.", 409)
        return emp

    def _emp_ua(self):
        from ..base.routes import (
            users_admin_service,  # singleton de la pantalla Usuarios
        )
        return users_admin_service

    # ------------------------------------------------------------ alcance

    def _emp_alcance(self, empresa_id=None):
        """(empresa_id, es_propia, editable). Otra empresa solo con relación."""
        mi = self.ctr_empresa_activa_id()
        propia = self.ctr_empresa_propia()
        propia_id = str(propia["_id"]) if propia else ""
        empresa_id = str(empresa_id or "") or mi
        if empresa_id != mi:
            fr = self.ctr_f["relaciones_entre_empresas"]
            rel = self._ctr_find(self.RELACIONES_FORM, {"$or": [
                {f"answers.{fr['cliente_id']}": mi, f"answers.{fr['contratista_id']}": empresa_id},
                {f"answers.{fr['contratista_id']}": mi, f"answers.{fr['cliente_id']}": empresa_id}]},
                one=True) if self.RELACIONES_FORM else None
            if not rel:
                self._emp_error("No tienes acceso a los empleados de esa empresa.", 403)
        return empresa_id, empresa_id == propia_id, empresa_id == mi

    def _emp_match_empresa(self, empresa_id, es_propia):
        campo = f"answers.{self.ctr_f['empleados']['empresa_id']}"
        if es_propia:  # los empleados de siempre no tienen empresa_id
            return {"$or": [{campo: empresa_id}, {campo: {"$in": [None, ""]}}]}
        return {campo: empresa_id}

    def _emp_get(self, empleado_id, empresa_id=None):
        emp = self._emp_mod()
        rec = self._ctr_get(emp.EMPLEADOS, empleado_id)
        if not rec:
            self._emp_error("El empleado no existe.", 404)
        dueno = str((rec.get("answers") or {}).get(self.ctr_f["empleados"]["empresa_id"]) or "")
        empresa_id, es_propia, editable = self._emp_alcance(empresa_id or dueno or None)
        if dueno != empresa_id and not (es_propia and not dueno):
            self._emp_error("El empleado no es de esa empresa.", 403)
        return rec, editable

    # ------------------------------------------------------------ lectura

    def _emp_contexto(self, ids):
        """Contratos y cumplimiento de varios empleados en dos consultas."""
        ids = [str(i) for i in ids]
        contratos, filas = {i: [] for i in ids}, {i: [] for i in ids}
        if ids and self.CONTRATOS_FORM:
            fc = self.ctr_f["contratos_de_servicio"]
            for c in self._ctr_find(self.CONTRATOS_FORM, {f"answers.{fc['empleados']}.{fc['empleado_id']}": {"$in": ids}}):
                a = c.get("answers") or {}
                if label(ESTATUS_CONTRATO, a.get(fc["estatus"])) == "Cancelado":
                    continue
                ref = {"id": str(c["_id"]), "folio": a.get(fc["folio"]) or "", "objeto": a.get(fc["objeto"]) or ""}
                for g in a.get(fc["empleados"]) or []:
                    i = str(g.get(fc["empleado_id"]) or "")
                    if i in contratos and ref not in contratos[i]:
                        contratos[i].append(ref)
        if ids and self.CUMPLIMIENTO_FORM:
            f = self.ctr_f["cumplimiento_de_requerimientos"]
            for r in self._ctr_find(self.CUMPLIMIENTO_FORM, {f"answers.{f['sujeto_empleado_id']}": {"$in": ids}}):
                a = r.get("answers") or {}
                estado = label(ESTADOS_MANUALES, a.get(f["estado_manual"])) or label(ESTADOS, a.get(f["estado"])) \
                    or "En plazo"
                filas[str(a.get(f["sujeto_empleado_id"]))].append(estado)
        return {i: {"contratos": contratos[i],
                    "cumplimiento_pct": porcentaje(filas[i]) if filas[i] else None} for i in ids}

    @staticmethod
    def _emp_cat(a, key):
        """Valor de un campo que puede ir suelto o dentro de un catálogo."""
        if a.get(key) not in (None, ""):
            return _uno(a[key])
        for v in a.values():
            if isinstance(v, dict) and v.get(key) not in (None, ""):
                return _uno(v[key])
        return None

    def _emp_puesto(self, a):
        return self._emp_cat(a, self.Employee.employee_fields["worker_position"])

    def emp_out(self, rec, ctx=None):
        emp = self.Employee
        ef, fe = emp.employee_fields, self.ctr_f["empleados"]
        a = rec.get("answers") or {}
        i = str(rec["_id"])
        ctx = (ctx or {}).get(i) or self._emp_contexto([i])[i]
        usr = a.get(emp.USUARIOS_OBJ_ID) if isinstance(a.get(emp.USUARIOS_OBJ_ID), dict) else {}
        uf = self._emp_ua().user_fields
        uid = _uno(usr.get(uf["user_id"]))
        vetado = None
        if a.get(fe["vetado_fecha"]) or a.get(fe["vetado_motivo"]):
            vetado = {"fecha": a.get(fe["vetado_fecha"]) or "", "motivo": a.get(fe["vetado_motivo"]) or "",
                      "por": a.get(fe["vetado_por"]) or ""}
        empresa = {"id": str(a[fe["empresa_id"]]), "razon_social": a.get(fe["empresa"]) or ""} \
            if a.get(fe["empresa_id"]) else None
        out = {
            "id": i, "folio": a.get(fe["folio"]) or "", "nombre": a.get(ef["worker_name"]) or "",
            "foto": self._ctr_archivo(a.get(ef["picture"])),
            "curp": a.get(ef["curp"]) or "", "rfc": a.get(ef["rfc"]) or None, "nss": a.get(ef["nss"]) or None,
            "empresa": empresa, "puesto": self._emp_puesto(a),
            "registro_patronal": a.get(fe["registro_patronal"]) or None,
            "salario_base_cotizacion": _num(a.get(fe["salario_base_cotizacion"])),
            "alta_imss": a.get(fe["alta_imss"]) or None,
            "perfiles": [{"id": str(g.get(fe["perfiles_id"])), "nombre": g.get(fe["perfiles_nombre"]) or ""}
                         for g in a.get(fe["perfiles"]) or [] if g.get(fe["perfiles_id"])],
            "disponible_para_contratos": a.get(fe["disponible_para_contratos"]) != opt("No"),
            "vetado": vetado,
            "estatus": "Inactivo" if a.get(ef["estatus_dentro_empresa"]) == "inactivo" else "Activo",
            "usuario_id": _int(uid) if uid not in (None, "") else None,
            "usuario": {"id": _int(uid), "username": _uno(usr.get(uf["username"])) or "",
                        "email": _uno(usr.get(uf["email"])) or ""} if uid not in (None, "") else None,
            "centro_trabajo": {"id": str(a[fe["centro_trabajo_id"]]), "nombre": a.get(fe["centro_trabajo"]) or ""}
            if a.get(fe["centro_trabajo_id"]) else None,
            "contratos": ctx["contratos"],
            "cumplimiento_pct": ctx["cumplimiento_pct"],
        }
        return {k: v for k, v in out.items() if v is not None or k in ("empresa", "cumplimiento_pct")}

    # ---------------------------------------------------------------- API

    def list_empleados(self, empresa_id=None, estatus=None, usuario=None, cumplimiento=None, perfil_id=None,
                       contrato_id=None, search=None, limit=25, offset=0):
        """usuario: con|sin · cumplimiento: Completo|Incompleto · contrato_id: id o 'libre'."""
        emp = self._emp_mod()
        ef = emp.employee_fields
        empresa_id, es_propia, editable = self._emp_alcance(empresa_id)
        match = self._emp_match_empresa(empresa_id, es_propia)
        if estatus:
            if estatus not in ESTATUS:
                self._emp_error(f"Estatus no válido: {estatus}.")
            match[f"answers.{ef['estatus_dentro_empresa']}"] = "inactivo" if estatus == "Inactivo" \
                else {"$ne": "inactivo"}
        if search and search.strip():
            rx = {"$regex": re.escape(search.strip()), "$options": "i"}
            fe = self.ctr_f["empleados"]
            match = {"$and": [match, {"$or": [{f"answers.{ef[k]}": rx} for k in ("worker_name", "curp", "rfc", "nss")]
                                      + [{f"answers.{fe['folio']}": rx}]}]}
        rows = self._ctr_find(emp.EMPLEADOS, match, sort=[(f"answers.{ef['worker_name']}", 1)])
        ctx = self._emp_contexto([r["_id"] for r in rows])
        uid_key = f"{emp.USUARIOS_OBJ_ID}"

        def pasa(r):
            a, c = r.get("answers") or {}, ctx[str(r["_id"])]
            if usuario in ("con", "sin"):
                tiene = bool(_uno(((a.get(uid_key) or {}) if isinstance(a.get(uid_key), dict) else {})
                                  .get(self._emp_ua().user_fields["user_id"])))
                if tiene != (usuario == "con"):
                    return False
            if cumplimiento in ("Completo", "Incompleto"):
                completo = c["cumplimiento_pct"] is None or c["cumplimiento_pct"] >= 100
                if completo != (cumplimiento == "Completo"):
                    return False
            if perfil_id:
                fe = self.ctr_f["empleados"]
                if str(perfil_id) not in [str(g.get(fe["perfiles_id"])) for g in a.get(fe["perfiles"]) or []]:
                    return False
            if contrato_id:
                if contrato_id == "libre":
                    return not c["contratos"]
                return any(x["id"] == str(contrato_id) for x in c["contratos"])
            return True

        rows = [r for r in rows if pasa(r)]
        ini = max(0, _int(offset))
        fin = ini + max(1, min(_int(limit, 25), 500))
        return {"items": [self.emp_out(r, ctx) for r in rows[ini:fin]], "total": len(rows), "editable": editable}

    def get_empleado(self, empleado_id):
        """Detalle (ME-04): lo de la lista + generales, preferencias y QR."""
        rec, editable = self._emp_get(empleado_id)
        out = self.emp_out(rec)
        a = rec.get("answers") or {}
        return {**out, **self._emp_generales(a, out), "preferencias": self._emp_preferencias(a, out),
                "qr_activo": out["estatus"] == "Activo" and not out.get("vetado"), "editable": editable}

    def _emp_generales(self, a, out):
        ef, x = self.Employee.employee_fields, EMPLEADO_EXTRA
        inv = {v: k for d in (GENERO, ESTADO_CIVIL, TIPO_CONTRATO) for k, v in d.items()}
        usr = a.get(self.Employee.USUARIOS_OBJ_ID) if isinstance(a.get(self.Employee.USUARIOS_OBJ_ID), dict) else {}
        ingreso = _fecha(str(a.get(x["fecha_ingreso"]) or "")[:10])
        antig = None
        if ingreso:
            m = (self._ctr_hoy().year - ingreso.year) * 12 + self._ctr_hoy().month - ingreso.month \
                - (1 if self._ctr_hoy().day < ingreso.day else 0)
            anios, meses = divmod(max(m, 0), 12)
            antig = " ".join(x for x in (f"{anios} año{'s' if anios != 1 else ''}" if anios else "",
                                         f"{meses} mes{'es' if meses != 1 else ''}" if meses or not anios else "") if x)
        dom = {k: self._emp_cat(a, x[k]) for k in ("nombre_direccion", "direccion", "colonia", "estado", "pais")}
        gen = {
            "fecha_nacimiento": str(a.get(ef["fecha_nacimiento"]) or "")[:10] or None,
            "genero": inv.get(a.get(ef["genero"])),
            "estado_civil": inv.get(a.get(x["estado_civil"])),
            "cuenta": {"email": _uno(usr.get(self._emp_ua().user_fields["email"])) or "",
                       "telefono": _uno(usr.get(self._emp_ua().user_fields["phone"])) or ""} if out.get("usuario") else None,
            "domicilio": {k: v for k, v in dom.items() if v} or None,
            "contratacion": {
                "compania": self._emp_cat(a, x["compania"]), "jefe_directo": self._emp_cat(a, x["jefe_directo"]),
                "tipo_contrato": inv.get(a.get(x["tipo_contrato"])),
                "numero_empleado": a.get(x["numero_empleado"]),
                "fecha_ingreso": ingreso.isoformat() if ingreso else None, "antiguedad": antig,
                "dias_vacaciones": a.get(x["vacaciones"]),
            },
        }
        gen["contratacion"] = {k: v for k, v in gen["contratacion"].items() if v not in (None, "")}
        return {k: v for k, v in gen.items() if v is not None}

    def _emp_preferencias(self, a, out):
        fe = self.ctr_f["empleados"]

        def yn(k, default):
            return default if not a.get(fe[k]) else a.get(fe[k]) == opt("Sí")
        return {"disponible_para_contratos": out["disponible_para_contratos"],
                "notificaciones_correo": yn("notificaciones_correo", True),
                "acceso_app": bool(out.get("usuario")) and yn("acceso_app", True),
                "checkin_foto": yn("checkin_foto", False)}

    # ------------------------------------------------------------ escritura

    def _emp_curp_libre(self, curp, excepto=None):
        emp = self.Employee
        rx = {"$regex": f"^{re.escape(curp)}$", "$options": "i"}
        for r in self._ctr_find(emp.EMPLEADOS, {f"answers.{emp.employee_fields['curp']}": rx}):
            if str(r["_id"]) != str(excepto or ""):
                return False
        return True

    def _emp_perfiles(self, perfiles, errores):
        out = []
        f = self.ctr_f["recursos_de_contrato"]
        for p in perfiles or []:
            pid = str(p.get("id") if isinstance(p, dict) else p)
            rec = self._ctr_get(self.RECURSOS_CONTRATO_FORM, pid) if self.RECURSOS_CONTRATO_FORM else None
            a = (rec or {}).get("answers") or {}
            if not rec or a.get(f["tipo"]) != opt("Perfil"):
                errores.append(f"El perfil {pid} no existe.")
            elif a.get(f["estatus"]) == opt("Inactivo"):
                errores.append(f"El perfil {a.get(f['nombre'])} está inactivo.")
            elif pid not in [x["id"] for x in out]:
                out.append({"id": pid, "nombre": a.get(f["nombre"]) or ""})
        return out

    def _emp_validar(self, e, empleado_id=None, parcial=False):
        """Regresa (answers de la forma, cuenta) o lanza con todos los errores."""
        ef, fe = self.Employee.employee_fields, self.ctr_f["empleados"]
        errores, a = [], {}

        def tiene(k):
            return not parcial or k in e

        if tiene("nombre"):
            nombre = " ".join(str(e.get("nombre") or "").split())
            if not nombre:
                errores.append("El nombre es obligatorio.")
            a[ef["worker_name"]] = nombre
        if tiene("curp"):
            curp = _up(e.get("curp"))
            if not CURP_RE.match(curp):
                errores.append("La CURP debe tener 18 caracteres válidos.")
            elif not self._emp_curp_libre(curp, empleado_id):
                errores.append("La CURP ya está registrada en otro empleado.")
            a[ef["curp"]] = curp
        if tiene("rfc"):
            rfc = _up(e.get("rfc"))
            if rfc and not RFC_RE.match(rfc):
                errores.append("El RFC debe tener 13 caracteres (persona física).")
            a[ef["rfc"]] = rfc or None
        if tiene("nss"):
            nss = _digitos(e.get("nss"))
            if nss and not NSS_RE.match(nss):
                errores.append("El NSS debe tener 11 dígitos.")
            a[ef["nss"]] = nss or None
        if tiene("registro_patronal"):
            a[fe["registro_patronal"]] = _up(e.get("registro_patronal")) or None
        if tiene("salario_base_cotizacion"):
            sbc = e.get("salario_base_cotizacion")
            if sbc not in (None, "") and (_num(sbc) is None or _num(sbc) < 0):
                errores.append("El salario base de cotización no es válido.")
            a[fe["salario_base_cotizacion"]] = _num(sbc) if sbc not in (None, "") else None
        if tiene("alta_imss"):
            alta = e.get("alta_imss")
            if alta and not _fecha(alta):
                errores.append("La fecha de alta ante el IMSS no es válida (YYYY-MM-DD).")
            a[fe["alta_imss"]] = _fecha(alta).isoformat() if alta and _fecha(alta) else None
        if tiene("perfiles"):
            perfiles = self._emp_perfiles(e.get("perfiles"), errores)
            a[fe["perfiles"]] = [{fe["perfiles_id"]: p["id"], fe["perfiles_nombre"]: p["nombre"]} for p in perfiles]
        if tiene("disponible_para_contratos"):
            a[fe["disponible_para_contratos"]] = opt("No") if e.get("disponible_para_contratos") is False else opt("Sí")
        if tiene("estatus"):
            estatus = e.get("estatus") or "Activo"
            if estatus not in ESTATUS:
                errores.append(f"Estatus no válido: {estatus}.")
            a[ef["estatus_dentro_empresa"]] = "inactivo" if estatus == "Inactivo" else "activo"
        for k, campo, opciones in (("genero", ef["genero"], GENERO),
                                   ("estado_civil", EMPLEADO_EXTRA["estado_civil"], ESTADO_CIVIL),
                                   ("tipo_contrato", EMPLEADO_EXTRA["tipo_contrato"], TIPO_CONTRATO)):
            if parcial and k not in e:
                continue
            if e.get(k) and e[k] not in opciones:
                errores.append(f"{k} no válido: {e[k]} (opciones: {', '.join(opciones)}).")
            a[campo] = opciones.get(e.get(k)) if e.get(k) else None
        for k, campo, hora in (("fecha_nacimiento", ef["fecha_nacimiento"], False),
                               ("fecha_ingreso", EMPLEADO_EXTRA["fecha_ingreso"], True)):
            if parcial and k not in e:
                continue
            d = _fecha(e.get(k)) if e.get(k) else None
            if e.get(k) and not d:
                errores.append(f"{k} no es una fecha válida (YYYY-MM-DD).")
            a[campo] = (f"{d.isoformat()} 00:00:00" if hora else d.isoformat()) if d else None
        if tiene("centro_trabajo"):
            c = e.get("centro_trabajo") if isinstance(e.get("centro_trabajo"), dict) else {}
            a[fe["centro_trabajo_id"]] = str(c.get("id") or "") or None
            a[fe["centro_trabajo"]] = str(c.get("nombre") or "").strip() or None
        if tiene("foto"):
            foto = e.get("foto") if isinstance(e.get("foto"), dict) else None
            if foto and not str(foto.get("file_url") or "").startswith("http"):
                errores.append("La foto no tiene file_url.")
            a[ef["picture"]] = [{"file_name": foto.get("name") or foto["file_url"].rsplit("/", 1)[-1],
                                 "file_url": foto["file_url"]}] if foto else None
        cuenta = self._emp_validar_cuenta(e.get("cuenta"), empleado_id, errores) if "cuenta" in e else None
        if errores:
            self._emp_error("\n".join(errores))
        return a, cuenta

    def _emp_validar_cuenta(self, c, empleado_id, errores):
        """cuenta: {modo: sin_cuenta | ligar (usuario_id) | crear (username, email, telefono)}."""
        c = c if isinstance(c, dict) else {}
        modo = c.get("modo") or "sin_cuenta"
        ua = self._emp_ua()
        uf = ua.user_fields
        if modo == "sin_cuenta":
            return {"modo": modo}
        if modo == "ligar":
            uid = _int(c.get("usuario_id"), 0)
            rec = self.cr.find_one({"form_id": ua.usuarios_form, "deleted_at": {"$exists": False},
                                    f"answers.{uf['user_id']}": {"$in": [uid, str(uid)]}}, {"answers": 1}) \
                if uid else None
            if not rec:
                errores.append("El usuario a vincular no existe.")
                return None
            if self._emp_usuario_ocupado(uid, empleado_id):
                errores.append("Ese usuario ya está asignado a otro empleado.")
            a = rec.get("answers") or {}
            return {"modo": modo, "usuario_id": uid, "username": _uno(a.get(uf["username"])) or "",
                    "email": _uno(a.get(uf["email"])) or "", "nombre": _uno(a.get(uf["name"])) or ""}
        if modo == "crear":
            username = str(c.get("username") or "").strip().lower()
            email = str(c.get("email") or "").strip().lower()
            tel = _digitos(c.get("telefono"))
            if not username or not ua.USERNAME_RE.match(username):
                errores.append("El usuario solo puede llevar letras, números, punto, guion, + y @.")
            if not ua.EMAIL_RE.match(email):
                errores.append("El correo no es válido.")
            if not TEL_RE.match(tel):
                errores.append("El teléfono debe tener 10 dígitos.")
            for k, v in (("username", username), ("email", email)):
                if v and self.cr.find_one({"form_id": ua.usuarios_form, "deleted_at": {"$exists": False},
                                           f"answers.{uf[k]}": {"$regex": f"^{re.escape(v)}$", "$options": "i"}},
                                          {"_id": 1}):
                    errores.append(f"Ya existe un usuario con ese {'usuario' if k == 'username' else 'correo'}.")
            return {"modo": modo, "username": username, "email": email, "telefono": tel}
        errores.append("La cuenta debe ser sin_cuenta, ligar o crear.")
        return None

    def _emp_usuario_ocupado(self, uid, excepto=None):
        emp = self.Employee
        campo = f"answers.{emp.USUARIOS_OBJ_ID}.{self._emp_ua().user_fields['user_id']}"
        return any(str(r["_id"]) != str(excepto or "")
                   for r in self._ctr_find(emp.EMPLEADOS, {campo: {"$in": [uid, str(uid), [uid], [str(uid)]]}}))

    def _emp_crear_usuario(self, nombre, cuenta):
        ua = self._emp_ua()
        uf = ua.user_fields
        try:
            ua.create_user(name=nombre, username=cuenta["username"], email=cuenta["email"],
                           phone=cuenta["telefono"], role=ROL_EMPLEADO)
        except Exception as e:  # noqa: BLE001
            self._emp_error(f"No se pudo crear el usuario: {ua._error_text(e)[:300]}", 500)
        rec = self.cr.find_one({"form_id": ua.usuarios_form, "deleted_at": {"$exists": False},
                                f"answers.{uf['username']}": cuenta["username"]}, {"answers": 1},
                               sort=[("created_at", -1)])
        uid = ua._one(((rec or {}).get("answers") or {}).get(uf["user_id"]))
        if not uid:
            self._emp_error("El usuario se dio de alta pero LinkaForm no regresó su id.", 500)
        return {**cuenta, "usuario_id": uid}

    def _emp_folio(self):
        fe = self.ctr_f["empleados"]
        n = 0
        for r in self._ctr_find(self.Employee.EMPLEADOS, {f"answers.{fe['folio']}": {"$regex": r"^E-\d+$"}}):
            n = max(n, int(r["answers"][fe["folio"]][2:]))
        return n

    def _emp_guardar(self, answers, empleado_id=None, accion="save_empleado"):
        """POST o PATCH (answers completos) con el reintento del catálogo Usuarios."""
        emp = self.Employee
        clean = {k: v for k, v in answers.items() if v not in (None, "", [])}
        metadata = self.lkf_api.get_metadata(form_id=emp.EMPLEADOS)
        metadata.update({"answers": clean, "properties": {"device_properties": {
            "System": "Script", "Module": "Accesos", "Process": "Contratistas · empleados", "Action": accion}}})
        ua = self._emp_ua()
        if empleado_id:
            res = ua.retry_catalog(lambda: self.lkf_api.patch_record(data=metadata, record_id=str(empleado_id)))
        else:
            res = ua.retry_catalog(lambda: self.lkf_api.post_forms_answers(metadata))
        if (res or {}).get("status_code") not in (200, 201, 202):
            self._emp_error(f"No se pudo guardar el empleado: {str((res or {}).get('json') or res)[:300]}", 500)
        return str(empleado_id) if empleado_id else (res.get("json") or {}).get("id")

    def _emp_usuario_answers(self, cuenta, nombre):
        ua = self._emp_ua()
        return ua._employee_user_answers(cuenta.get("nombre") or nombre, cuenta["email"], cuenta["username"],
                                         cuenta["usuario_id"])

    def create_empleado(self, empleado, folio=None):
        e = empleado if isinstance(empleado, dict) else {}
        emp = self._emp_mod()
        empresa_id = self._emp_alcance()[0]
        a, cuenta = self._emp_validar(e)
        fe = self.ctr_f["empleados"]
        empresa = self._ctr_get(self.EMPRESAS_FORM, empresa_id) or {}
        a.update({fe["empresa_id"]: empresa_id,
                  fe["empresa"]: (empresa.get("answers") or {}).get(self.ctr_f["empresas"]["razon_social"]) or "",
                  fe["folio"]: folio or f"E-{self._emp_folio() + 1:04d}"})
        if cuenta and cuenta["modo"] == "crear":
            cuenta = self._emp_crear_usuario(a[emp.employee_fields["worker_name"]], cuenta)
        if cuenta and cuenta["modo"] in ("ligar", "crear"):
            a.update(self._emp_usuario_answers(cuenta, a[emp.employee_fields["worker_name"]]))
        empleado_id = self._emp_guardar(a, accion="create_empleado")
        if not empleado_id:
            self._emp_error("LinkaForm no regresó el id del empleado.", 500)
        return self.get_empleado(empleado_id)

    def update_empleado(self, empleado_id, empleado):
        """Edición parcial: solo cambia las llaves que trae `empleado`."""
        e = empleado if isinstance(empleado, dict) else {}
        rec, editable = self._emp_get(empleado_id)
        if not editable:
            self._emp_error("Solo puedes editar empleados de tu empresa.", 403)
        emp = self.Employee
        cambios, cuenta = self._emp_validar(e, empleado_id, parcial=True)
        a = {**(rec.get("answers") or {}), **cambios}
        nombre = a.get(emp.employee_fields["worker_name"]) or ""
        if cuenta:
            if cuenta["modo"] == "sin_cuenta":
                a.pop(emp.USUARIOS_OBJ_ID, None)
            else:
                if cuenta["modo"] == "crear":
                    cuenta = self._emp_crear_usuario(nombre, cuenta)
                a.update(self._emp_usuario_answers(cuenta, nombre))
        self._emp_guardar(a, empleado_id, "update_empleado")
        return self.get_empleado(empleado_id)

    def change_status_empleado(self, empleado_id, estatus):
        """Eliminar en la UI = Inactivo (no se borra el registro)."""
        if estatus not in ESTATUS:
            self._emp_error("El estatus debe ser Activo o Inactivo.")
        return self.update_empleado(empleado_id, {"estatus": estatus})

    # -------------------------------------------------------- alta con IA

    def analizar_documentos_empleado(self, archivos, model=None):
        """Paso 1 del alta: lee INE, CURP, comprobante, CSF y CV; sugiere nombre,
        CURP, RFC y NSS. No guarda nada."""
        archivos = [x for x in (archivos or []) if isinstance(x, dict)]
        if not archivos:
            self._emp_error("Sube al menos un documento.")
        if len(archivos) > MAX_ARCHIVOS_IA:
            self._emp_error(f"Máximo {MAX_ARCHIVOS_IA} documentos a la vez.")
        if not self.ai:
            self._emp_error("La IA (OpenRouter) no está configurada en esta cuenta.", 409)
        from .contratistas_documentos_ia import _conf
        prompt = PROMPT_EMPLEADO.format(tipos=", ".join(TIPOS_DOC_EMPLEADO))
        documentos = []
        for arch in archivos:
            d = {"archivo": {"name": arch.get("name") or "", "file_url": arch.get("file_url") or ""}}
            if not str(arch.get("file_url") or "").startswith("http"):
                documentos.append({**d, "estado": "error", "error": "Falta file_url."})
                continue
            try:
                ia = self._dia_llamar(arch, prompt, model)
            except Exception as ex:  # noqa: BLE001
                documentos.append({**d, "estado": "error", "error": f"No se pudo leer: {str(ex)[:200]}"})
                continue
            ia = ia if isinstance(ia, dict) else {}
            curp, rfc, nss = _up(ia.get("curp")), _up(ia.get("rfc")), _digitos(ia.get("nss"))
            documentos.append({
                **d, "estado": "ok" if ia.get("legible") else "ilegible",
                "tipo": ia.get("tipo_documento") if ia.get("tipo_documento") in TIPOS_DOC_EMPLEADO else "Otro",
                "confianza": _conf(ia.get("confianza")),
                "datos": {k: v for k, v in {
                    "nombre": " ".join(str(ia.get("nombre") or "").split()).upper() or None,
                    "curp": curp if CURP_RE.match(curp) else None,
                    "rfc": rfc if RFC_RE.match(rfc) else None,
                    "nss": nss if NSS_RE.match(nss) else None}.items() if v},
            })
        sugerido, inconsistencias = {}, []
        for k in ("nombre", "curp", "rfc", "nss"):
            valores = [(x["datos"][k], x["archivo"]["name"]) for x in documentos
                       if x.get("estado") == "ok" and x["datos"].get(k)]
            distintos = {(_norm(v) if k == "nombre" else v) for v, _ in valores}
            if valores:
                sugerido[k] = valores[0][0]
            if len(distintos) > 1:
                inconsistencias.append({"campo": k, "valores": [{"valor": v, "documento": n} for v, n in valores]})
        if sugerido.get("curp") and sugerido.get("rfc") and sugerido["curp"][:10] != sugerido["rfc"][:10]:
            inconsistencias.append({"campo": "rfc", "mensaje": "El RFC no corresponde a la CURP."})
        alertas = []
        if sugerido.get("curp") and not self._emp_curp_libre(sugerido["curp"]):
            alertas.append("La CURP ya está registrada en otro empleado.")
        return {"documentos": documentos, "sugerido": sugerido, "inconsistencias": inconsistencias,
                "alertas": alertas}

    # ------------------------------------------------------- carga masiva

    def _emp_leer_archivo(self, archivo):
        if not isinstance(archivo, dict) or not str(archivo.get("file_url") or "").startswith("http"):
            self._emp_error("Falta el archivo (file_url).")
        url = archivo["file_url"]
        nombre = (archivo.get("name") or url.rsplit("/", 1)[-1].split("?")[0]).lower()
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
        except Exception as e:  # noqa: BLE001
            self._emp_error(f"No se pudo descargar el archivo: {str(e)[:200]}", 502)
        if len(resp.content) > MAX_CARGA_BYTES:
            self._emp_error("El archivo pesa más de 50 MB.", 413)
        if nombre.endswith(".xlsx"):
            import openpyxl
            try:
                ws = openpyxl.load_workbook(io.BytesIO(resp.content), read_only=True, data_only=True).worksheets[0]
            except Exception:  # noqa: BLE001
                self._emp_error("No se pudo leer el Excel; usa la plantilla (.xlsx o .csv).")
            filas = [["" if c is None else str(c) for c in row] for row in ws.iter_rows(values_only=True)]
        elif nombre.endswith(".csv"):
            try:
                texto = resp.content.decode("utf-8-sig")
            except UnicodeDecodeError:
                texto = resp.content.decode("latin-1")
            dialecto = csv.Sniffer().sniff(texto[:2048], delimiters=",;\t") if texto.strip() else csv.excel
            filas = list(csv.reader(io.StringIO(texto), dialecto))
        else:
            self._emp_error("Formato no soportado: sube un .xlsx o .csv.")
        filas = [f for f in filas if any(str(c).strip() for c in f)]
        if not filas:
            self._emp_error("El archivo está vacío.")
        return filas

    def _emp_filas_carga(self, archivo):
        filas = self._emp_leer_archivo(archivo)
        encabezado = [COLUMNAS.get(_norm(c)) for c in filas[0]]
        faltan = [n for n, k in (("Nombre completo", "nombre"), ("CURP", "curp")) if k not in encabezado]
        if faltan:
            self._emp_error(f"Faltan columnas: {', '.join(faltan)}. Usa la plantilla.")
        if len(filas) - 1 > MAX_FILAS:
            self._emp_error(f"Máximo {MAX_FILAS} empleados por archivo.")
        emp = self.Employee
        existentes = {_up((r.get("answers") or {}).get(emp.employee_fields["curp"]))
                      for r in self._ctr_find(emp.EMPLEADOS, {f"answers.{emp.employee_fields['curp']}": {"$nin": [None, ""]}})}
        validas, omitidas, errores, vistas = [], [], [], {}
        for n, fila in enumerate(filas[1:], start=2):
            d = {k: str(fila[i]).strip() for i, k in enumerate(encabezado) if k and i < len(fila)}
            e = {"nombre": " ".join(d.get("nombre", "").split()), "curp": _up(d.get("curp")),
                 "rfc": _up(d.get("rfc")), "nss": _digitos(d.get("nss"))}
            msgs = []
            if not e["nombre"]:
                msgs.append("Falta el nombre")
            if not e["curp"]:
                msgs.append("Falta la CURP")
            elif not CURP_RE.match(e["curp"]):
                msgs.append("CURP no válida")
            if e["rfc"] and not RFC_RE.match(e["rfc"]):
                msgs.append("RFC no válido (13 caracteres)")
            if e["nss"] and not NSS_RE.match(e["nss"]):
                msgs.append("NSS no válido (11 dígitos)")
            if msgs:
                errores.append({"fila": n, "mensaje": " · ".join(msgs)})
            elif e["curp"] in existentes:
                omitidas.append({"fila": n, "curp": e["curp"], "motivo": "La CURP ya está registrada"})
            elif e["curp"] in vistas:
                omitidas.append({"fila": n, "curp": e["curp"], "motivo": f"CURP repetida (fila {vistas[e['curp']]})"})
            else:
                vistas[e["curp"]] = n
                validas.append({"fila": n, **e})
        return validas, omitidas, errores

    def validar_carga_empleados(self, archivo):
        validas, omitidas, errores = self._emp_filas_carga(archivo)
        return {"valido": not errores and bool(validas), "total": len(validas) + len(omitidas) + len(errores),
                "por_cargar": len(validas), "omitidos": omitidas, "errores": errores,
                "muestra": [{k: v for k, v in x.items() if k != "fila"} for x in validas[:5]]}

    def cargar_empleados(self, archivo):
        """Crea los válidos (sin cuenta, Activos). Con errores no carga nada."""
        self._emp_mod()
        validas, omitidas, errores = self._emp_filas_carga(archivo)
        if errores:
            self._emp_error("El archivo tiene errores; corrígelos y vuelve a subirlo:\n"
                            + "\n".join(f"Fila {x['fila']} · {x['mensaje']}" for x in errores[:20]))
        n = self._emp_folio()
        creados, fallidos = [], []
        for x in validas:
            n += 1
            try:
                r = self.create_empleado({k: x[k] for k in ("nombre", "curp", "rfc", "nss")}, folio=f"E-{n:04d}")
                creados.append({"fila": x["fila"], "id": r["id"], "folio": r["folio"], "nombre": r["nombre"]})
            except Exception as e:  # noqa: BLE001
                n -= 1
                fallidos.append({"fila": x["fila"], "curp": x["curp"], "error": str(e)[:200]})
        return {"creados": creados, "omitidos": omitidas, "fallidos": fallidos}

    # ------------------------------------------------- detalle: documentos

    def list_documentos_empleado(self, empleado_id, estatus=None, origen=None, search=None, limit=25, offset=0):
        """Pestaña Documentos: un renglón por requerimiento (de sus perfiles, de
        sus contratos y asignados a la relación) con su documento más reciente;
        los documentos sin requerimiento van aparte con origen Carga."""
        rec, _ = self._emp_get(empleado_id)
        empleado_id = str(rec["_id"])
        fe = self.ctr_f["empleados"]
        a = rec.get("answers") or {}
        cache, renglones = {}, {}

        def renglon(req_id):
            if req_id not in renglones:
                req = self._cum_requerimiento(req_id, cache)
                if not req:
                    return None
                renglones[req_id] = {"requerimiento": {"id": req_id, "nombre": req["nombre"]},
                                     "recurrencia": req["periodicidad"], "limitante": req["limitante"],
                                     "origenes": [], "estado_motor": None}
            return renglones[req_id]

        for g in a.get(fe["perfiles"]) or []:
            pid = str(g.get(fe["perfiles_id"]) or "")
            for req_id in self._cum_reqs_recurso(pid, cache) if pid else []:
                r = renglon(req_id)
                if r and (self._cum_requerimiento(req_id, cache) or {}).get("ambito") == "Persona":
                    r["origenes"].append({"tipo": "Perfil", "nombre": g.get(fe["perfiles_nombre"]) or ""})
                elif r and not r["origenes"]:
                    renglones.pop(req_id, None)
        if self.CUMPLIMIENTO_FORM:
            fc = self.ctr_f["cumplimiento_de_requerimientos"]
            folios = {}
            for row in self._ctr_find(self.CUMPLIMIENTO_FORM, {f"answers.{fc['sujeto_empleado_id']}": empleado_id},
                                      sort=[(f"answers.{fc['periodo_inicio']}", -1)]):
                f = self.cum_fila_out(row)
                r = renglon(f["requerimiento"]["id"])
                if not r:
                    continue
                if f["contrato"]:
                    if f["contrato"] not in folios:
                        c = self._ctr_get(self.CONTRATOS_FORM, f["contrato"]) or {}
                        folios[f["contrato"]] = (c.get("answers") or {}).get(
                            self.ctr_f["contratos_de_servicio"]["folio"]) or f["contrato"]
                    o = {"tipo": "Contrato", "nombre": folios[f["contrato"]], "id": f["contrato"]}
                else:
                    o = {"tipo": "Expediente base", "nombre": "Asignado por el cliente"}
                if o not in r["origenes"]:
                    r["origenes"].append(o)
                if r["estado_motor"] is None and f["estado"] in ESTADO_MOTOR_A_DOC:
                    r["estado_motor"], r["periodo"] = f["estado"], f["periodo"]
        docs = {}
        sueltos = []
        if self.DOCUMENTOS_FORM:
            fd = self.ctr_f["documentos_de_cumplimiento"]
            for d in self._ctr_find(self.DOCUMENTOS_FORM, {f"answers.{fd['dueno_empleado_id']}": empleado_id},
                                    sort=[("updated_at", -1)]):
                out = self.doc_out(d)
                rid = (out.get("requerimiento") or {}).get("id")
                if rid and rid not in docs:
                    docs[rid] = out
                    renglon(rid)
                elif not rid:
                    sueltos.append(out)

        def doc_light(d):
            ultimo = (d.get("comentarios") or [])[-1:] or [{}]
            rechazo = next((x.get("motivo") for x in d.get("aprobaciones") or [] if x.get("motivo")), None)
            return {"id": d["id"], "folio": d["folio"], "nombre": d["nombre"], "archivo": d["archivo"],
                    "vigencia_inicio": d.get("vigencia_inicio"), "vigencia_fin": d.get("vigencia_fin"),
                    "versiones": d["versiones"], "comentario": rechazo or ultimo[0].get("texto")}

        items = []
        for rid, r in renglones.items():
            d = docs.get(rid)
            est = d["estatus"] if d else ESTADO_MOTOR_A_DOC.get(r["estado_motor"] or "", "Por subir")
            if not r["origenes"]:
                r["origenes"] = [{"tipo": "Carga", "nombre": "Subido sin requerimiento ligado"}]
            item = {"requerimiento": r["requerimiento"], "origen": r["origenes"][0],
                    "tambien_lo_requiere": r["origenes"][1:], "recurrencia": r["recurrencia"],
                    "limitante": r["limitante"], "estatus": est, "documento": doc_light(d) if d else None}
            if r.get("periodo"):
                item["periodo"] = r["periodo"]
            items.append(item)
        for d in sueltos:
            items.append({"requerimiento": None, "origen": {"tipo": "Carga", "nombre": d["nombre"]},
                          "tambien_lo_requiere": [], "recurrencia": None, "limitante": False,
                          "estatus": d["estatus"], "documento": doc_light(d)})
        conteo = {e: sum(1 for i in items if i["estatus"] == e) for e in URGENCIA}
        if estatus:
            items = [i for i in items if i["estatus"] in ([estatus] if isinstance(estatus, str) else estatus)]
        if origen:
            items = [i for i in items if any(o["tipo"] == origen for o in [i["origen"], *i["tambien_lo_requiere"]])]
        if search and search.strip():
            s = _norm(search)
            items = [i for i in items if s in _norm((i["requerimiento"] or {}).get("nombre"))
                     or s in _norm((i["documento"] or {}).get("nombre"))]
        items.sort(key=lambda i: (URGENCIA.index(i["estatus"]) if i["estatus"] in URGENCIA else 9,
                                  _norm((i["requerimiento"] or {}).get("nombre") or (i["documento"] or {}).get("nombre"))))
        ini = max(0, _int(offset))
        fin = ini + max(1, min(_int(limit, 25), 200))
        return {"items": items[ini:fin], "total": len(items), "conteo": conteo,
                "pendientes": conteo["Rechazado"] + conteo["Vencido"] + conteo["Por subir"]}

    # --------------------------------------------- detalle: configuraciones

    def _emp_editable(self, empleado_id):
        rec, editable = self._emp_get(empleado_id)
        if not editable:
            self._emp_error("Solo puedes cambiar empleados de tu empresa.", 403)
        return rec

    def get_qr_empleado(self, empleado_id):
        """QR para registrar entrada en caseta: lleva el id del empleado."""
        import qrcode
        d = self.get_empleado(empleado_id)
        img = qrcode.make(d["id"])
        b = io.BytesIO()
        img.save(b, format="PNG")
        motivo = "Empleado vetado" if d.get("vetado") else ("Empleado desactivado" if d["estatus"] != "Activo" else None)
        out = {"contenido": d["id"], "activo": d["qr_activo"], "nombre": d["nombre"], "folio": d["folio"],
               "imagen": "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()}
        if motivo:
            out["motivo_inactivo"] = motivo
        return out

    def vetar_empleado(self, empleado_id, motivo):
        """No se asigna a contratos ni centros nuevos; lo activo no se cancela solo."""
        rec = self._emp_editable(empleado_id)
        fe = self.ctr_f["empleados"]
        motivo = " ".join(str(motivo or "").split())
        if not motivo:
            self._emp_error("Escribe el motivo del veto.")
        a = rec.get("answers") or {}
        if a.get(fe["vetado_fecha"]):
            self._emp_error("El empleado ya está vetado.", 409)
        por = (self.user or {}).get("name") or (self.user or {}).get("email") or ""
        a = {**a, fe["vetado_fecha"]: self._ctr_hoy().isoformat(), fe["vetado_motivo"]: motivo,
             fe["vetado_por"]: por, fe["disponible_para_contratos"]: opt("No")}
        self._emp_guardar(a, empleado_id, "vetar_empleado")
        return self.get_empleado(empleado_id)

    def levantar_veto_empleado(self, empleado_id):
        rec = self._emp_editable(empleado_id)
        fe = self.ctr_f["empleados"]
        a = dict(rec.get("answers") or {})
        if not a.get(fe["vetado_fecha"]):
            self._emp_error("El empleado no está vetado.", 409)
        for k in ("vetado_fecha", "vetado_motivo", "vetado_por"):
            a.pop(fe[k], None)
        a[fe["disponible_para_contratos"]] = opt("Sí")
        self._emp_guardar(a, empleado_id, "levantar_veto_empleado")
        return self.get_empleado(empleado_id)

    def update_preferencias_empleado(self, empleado_id, preferencias):
        """Interruptores de Configuraciones; solo cambia las llaves que trae."""
        p = preferencias if isinstance(preferencias, dict) else {}
        rec = self._emp_editable(empleado_id)
        fe = self.ctr_f["empleados"]
        a = dict(rec.get("answers") or {})
        validas = ("disponible_para_contratos", *PREFERENCIAS)
        malas = [k for k in p if k not in validas or not isinstance(p[k], bool)]
        if malas:
            self._emp_error(f"Preferencias no válidas: {', '.join(malas)} (true/false).")
        if p.get("disponible_para_contratos") and a.get(fe["vetado_fecha"]):
            self._emp_error("Un empleado vetado no puede estar disponible para contratos.", 409)
        if p.get("acceso_app") and not a.get(self.Employee.USUARIOS_OBJ_ID):
            self._emp_error("El acceso a la app móvil requiere que el empleado tenga cuenta.", 409)
        for k, v in p.items():
            a[fe[k]] = opt("Sí") if v else opt("No")
        self._emp_guardar(a, empleado_id, "update_preferencias_empleado")
        return self.get_empleado(empleado_id)

    def restaurar_password_empleado(self, empleado_id):
        """Manda al correo del usuario la liga para poner contraseña nueva."""
        d = self.emp_out(self._emp_editable(empleado_id))
        if not d.get("usuario"):
            self._emp_error("El empleado no tiene cuenta.", 409)
        ua = self._emp_ua()
        uf = ua.user_fields
        uid = d["usuario"]["id"]
        rec = self.cr.find_one({"form_id": ua.usuarios_form, "deleted_at": {"$exists": False},
                                f"answers.{uf['user_id']}": {"$in": [uid, str(uid)]}}, {"_id": 1},
                               sort=[("created_at", -1)])
        if not rec:
            self._emp_error("No se encontró el registro del usuario en Usuarios.", 404)
        try:
            ua.reset_password(str(rec["_id"]))
        except Exception as e:  # noqa: BLE001
            self._emp_error(f"No se pudo restaurar la contraseña: {ua._error_text(e)[:300]}", 409)
        return {"enviado": True, "email": d["usuario"]["email"]}

    # ------------------------------------------------ contratos (ME-05-B)

    def _emp_renglones(self, a, empleado_id):
        fc = self.ctr_f["contratos_de_servicio"]
        return [g for g in a.get(fc["empleados"]) or [] if str(g.get(fc["empleado_id"]) or "") == str(empleado_id)]

    def _emp_pendientes_contrato(self, contrato_id, empleado_id):
        if not self.CUMPLIMIENTO_FORM:
            return {"pendientes": 0, "total": 0}
        f = self.ctr_f["cumplimiento_de_requerimientos"]
        estados = []
        for r in self._ctr_find(self.CUMPLIMIENTO_FORM, {f"answers.{f['contrato_id']}": str(contrato_id),
                                                         f"answers.{f['sujeto_empleado_id']}": str(empleado_id)}):
            a = r.get("answers") or {}
            estados.append(label(ESTADOS_MANUALES, a.get(f["estado_manual"])) or label(ESTADOS, a.get(f["estado"]))
                           or "En plazo")
        aplicables = [e for e in estados if e not in ("No aplica", "Por transcurrir")]
        return {"pendientes": sum(1 for e in aplicables if e not in ("Cumplido", "En ceros")), "total": len(aplicables)}

    def list_contratos_empleado(self, empleado_id, estatus=None, search=None, limit=25, offset=0):
        """Pestaña Contratos: estatus Activo = contrato vigente."""
        rec, _ = self._emp_get(empleado_id)
        eid = str(rec["_id"])
        fc = self.ctr_f["contratos_de_servicio"]
        items = []
        for c in self._ctr_find(self.CONTRATOS_FORM, {f"answers.{fc['empleados']}.{fc['empleado_id']}": eid},
                                sort=[(f"answers.{fc['folio']}", -1)]) if self.CONTRATOS_FORM else []:
            d = self.ctr_contrato_out(c)
            mios = [x for x in d["empleados"] if x["empleado"]["id"] == eid]
            item = {"id": d["id"], "folio": d["folio"], "objeto": d["objeto"], "cliente": d["cliente"],
                    "contratista": d["contratista"], "servicios": d["servicios"],
                    "perfiles": [x["perfil"] for x in mios],
                    "fecha_alta": min((x["fecha_alta"] for x in mios if x["fecha_alta"]), default=""),
                    "vigencia": {"inicio": d["inicio"], "fin": d["fin"]}, "estatus_contrato": d["estatus"],
                    "estatus": "Inactivo" if d["estatus"] in CONTRATO_NO_VIGENTE else "Activo",
                    "requerimientos": self._emp_pendientes_contrato(d["id"], eid)}
            items.append(item)
        if estatus in ("Activo", "Inactivo"):
            items = [i for i in items if i["estatus"] == estatus]
        if search and search.strip():
            s = _norm(search)
            items = [i for i in items if s in _norm(f"{i['folio']} {i['objeto']} {i['cliente']['razon_social']}")]
        ini = max(0, _int(offset))
        return {"items": items[ini:ini + max(1, min(_int(limit, 25), 200))], "total": len(items)}

    def _emp_ligable(self, rec):
        out = self.emp_out(rec)
        if out["estatus"] != "Activo":
            self._emp_error("El empleado está desactivado.", 409)
        if out.get("vetado"):
            self._emp_error("El empleado está vetado: no se puede ligar a contratos.", 409)
        if not out["disponible_para_contratos"]:
            self._emp_error("El empleado no está disponible para contratos.", 409)
        return out

    def list_contratos_para_ligar(self, empleado_id, cliente_id=None, perfil_id=None, search=None):
        """Paso 1 de Ligar Contrato: vigentes de mi empresa como contratista donde
        el empleado no está; primero los que coinciden con sus perfiles."""
        rec = self._emp_editable(empleado_id)
        eid = str(rec["_id"])
        mios = {p["id"] for p in self.emp_out(rec)["perfiles"]}
        fc = self.ctr_f["contratos_de_servicio"]
        items = []
        for c in self._ctr_find(self.CONTRATOS_FORM, {f"answers.{fc['contratista_id']}": self.ctr_empresa_activa_id()},
                                sort=[(f"answers.{fc['folio']}", -1)]) if self.CONTRATOS_FORM else []:
            if self._emp_renglones(c.get("answers") or {}, eid):
                continue
            d = self.ctr_contrato_out(c)
            if d["estatus"] in CONTRATO_NO_VIGENTE:
                continue
            asignados = {}
            for x in d["empleados"]:
                asignados[x["perfil"]["id"]] = asignados.get(x["perfil"]["id"], 0) + 1
            perfiles = [{**p["perfil"], "cantidad": p["cantidad"], "asignados": asignados.get(p["perfil"]["id"], 0),
                         "ya_lo_tiene": p["perfil"]["id"] in mios} for p in d["perfiles"]]
            items.append({"id": d["id"], "folio": d["folio"], "objeto": d["objeto"], "cliente": d["cliente"],
                          "vigencia": {"inicio": d["inicio"], "fin": d["fin"]}, "estatus_contrato": d["estatus"],
                          "perfiles": perfiles, "coincide": [p for p in perfiles if p["ya_lo_tiene"]]})
        if cliente_id:
            items = [i for i in items if i["cliente"]["id"] == str(cliente_id)]
        if perfil_id:
            items = [i for i in items if any(p["id"] == str(perfil_id) for p in i["perfiles"])]
        if search and search.strip():
            s = _norm(search)
            items = [i for i in items if s in _norm(f"{i['folio']} {i['objeto']} {i['cliente']['razon_social']}")]
        items.sort(key=lambda i: not i["coincide"])
        return {"items": items, "total": len(items)}

    def _emp_contrato_mio(self, contrato_id):
        rec = self._ctr_contrato_visible(contrato_id)
        fc = self.ctr_f["contratos_de_servicio"]
        if str((rec.get("answers") or {}).get(fc["contratista_id"]) or "") != self.ctr_empresa_activa_id():
            self._emp_error("Solo la empresa contratista liga a sus empleados al contrato.", 403)
        return rec

    def _emp_guardar_renglones(self, contrato, empleado, perfiles, accion):
        """Reemplaza los renglones del empleado por uno por perfil (conserva la
        fecha de alta de los que ya tenía) y suma los perfiles nuevos al empleado."""
        eid = str(empleado["_id"])
        d = self.ctr_contrato_out(contrato)
        del_contrato = {p["perfil"]["id"]: p["perfil"] for p in d["perfiles"]}
        ids = list(dict.fromkeys(str(p.get("id") if isinstance(p, dict) else p) for p in perfiles or []))
        malos = [i for i in ids if i not in del_contrato]
        if malos:
            self._emp_error(f"Perfiles que no pide el contrato {d['folio']}: {', '.join(malos)}.")
        antes = {x["perfil"]["id"]: x for x in d["empleados"] if x["empleado"]["id"] == eid}
        nombre = self.emp_out(empleado)["nombre"]
        hoy = self._ctr_hoy().isoformat()
        renglones = [x for x in d["empleados"] if x["empleado"]["id"] != eid] + [
            {**(antes.get(i) or {}), "empleado": {"id": eid, "nombre": nombre}, "perfil": del_contrato[i],
             "fecha_alta": (antes.get(i) or {}).get("fecha_alta") or hoy} for i in ids]
        self._ctr_guardar_cambio(contrato, self._ctr_answers_in({"empleados": renglones}), accion)
        agregados = []
        if ids:
            tiene = self.emp_out(empleado)["perfiles"]
            agregados = [del_contrato[i] for i in ids if i not in {p["id"] for p in tiene}]
            if agregados:
                self.update_empleado(eid, {"perfiles": tiene + agregados})
        return {"contrato": {"id": d["id"], "folio": d["folio"]}, "perfiles_agregados": agregados,
                "empleado": self.get_empleado(eid)}

    def ligar_contrato_empleado(self, empleado_id, contrato_id, perfiles):
        rec = self._emp_editable(empleado_id)
        self._emp_ligable(rec)
        contrato = self._emp_contrato_mio(contrato_id)
        if self._emp_renglones(contrato.get("answers") or {}, rec["_id"]):
            self._emp_error("El empleado ya está ligado a ese contrato; edita sus perfiles.", 409)
        if self.ctr_contrato_out(contrato)["estatus"] in CONTRATO_NO_VIGENTE:
            self._emp_error("Solo se liga a contratos vigentes.", 409)
        if not perfiles:
            self._emp_error("Elige al menos un perfil del contrato.")
        return self._emp_guardar_renglones(contrato, rec, perfiles, "ligar_contrato_empleado")

    def editar_perfiles_contrato_empleado(self, empleado_id, contrato_id, perfiles):
        rec = self._emp_editable(empleado_id)
        contrato = self._emp_contrato_mio(contrato_id)
        if not self._emp_renglones(contrato.get("answers") or {}, rec["_id"]):
            self._emp_error("El empleado no está ligado a ese contrato.", 404)
        if not perfiles:
            self._emp_error("Elige al menos un perfil; para quitarlo del contrato usa Remover.")
        return self._emp_guardar_renglones(contrato, rec, perfiles, "editar_perfiles_contrato_empleado")

    def remover_contrato_empleado(self, empleado_id, contrato_id):
        """Sus documentos se conservan; el motor quita sus filas del contrato."""
        rec = self._emp_editable(empleado_id)
        contrato = self._emp_contrato_mio(contrato_id)
        if not self._emp_renglones(contrato.get("answers") or {}, rec["_id"]):
            self._emp_error("El empleado no está ligado a ese contrato.", 404)
        return self._emp_guardar_renglones(contrato, rec, [], "remover_contrato_empleado")
