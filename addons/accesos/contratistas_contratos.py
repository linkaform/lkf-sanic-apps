# -*- coding: utf-8 -*-
"""Contratos de servicio de Contratistas (ME-14).

Spec: clave10-sdk/specs/contratos/contratos-001-modelo-de-datos.md.

- La empresa activa sale del JWT: el registro del usuario en Empleados
  (campo empresa_id); sin empleado o sin empresa = la empresa propia.
- Cada usuario solo ve y edita contratos donde su empresa es cliente o
  contratista.
- El estatus lo calcula el back con el orden de la spec. Las filas de
  cumplimiento las genera el motor de ME-15 (contratistas_cumplimiento.py)
  después de cada alta y cambio.
- Cada alta y cambio deja un evento en Historial de contratos.
"""
import re
import unicodedata
from datetime import date, datetime, timedelta

import pytz
import simplejson
from bson import ObjectId

DIAS_POR_VENCER = 30

PROPS = {
    "device_properties": {
        "System": "Script",
        "Module": "Accesos",
        "Process": "Contratistas · contratos",
        "File": "accesos/contratistas_contratos.py",
    }
}

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
ESTATUS = ["Activo", "Por vencer", "En documentación", "Vencido", "Pausado", "Cancelado"]
ESTATUS_MANUAL = ["Pausado", "Cancelado"]
ESTATUS_UBICACION = ["Activa", "En apertura", "Inactiva"]
CLASES_EQUIPO = ["Equipo", "Vehículo", "Herramienta"]
RECURRENCIA_TIPOS = ["Por día", "Semanal", "Mensual", "Configurable"]
UNIDADES = ["día", "semana", "mes", "año"]

# Campo de la referencia -> evento del historial cuando cambia.
EVENTO_POR_CAMPO = [
    ("ubicaciones", "Ubicaciones"),
    ("perfiles", "Perfiles"),
    ("equipos", "Equipos"),
    ("servicios", "Servicios"),
    ("empleados", "Empleados"),
    ("monto", "Monto"),
    ("inicio", "Vigencia"),
    ("fin", "Vigencia"),
]
CAMPOS_EDITABLES = [
    "numero_contrato", "objeto", "descripcion", "monto", "inicio", "fin", "responsable",
    "contrato_firmado", "permite_subcontratacion", "servicios", "perfiles", "equipos",
    "ubicaciones", "empleados", "recurrencia",
]


def opt(label):
    """Valor que guarda LinkaForm para una opción (mismo slug que el XML)."""
    s = unicodedata.normalize("NFD", label).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def label(opciones, valor):
    """Del slug guardado a la etiqueta; None si no está."""
    if valor in (None, ""):
        return None
    for o in opciones:
        if opt(o) == valor or o == valor:
            return o
    return None


def _num(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _fecha(v):
    if not v:
        return None
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _ids(v):
    """requerimientos_excluidos se guarda como lista JSON de ids."""
    if isinstance(v, list):
        return [str(x) for x in v]
    if not v:
        return []
    try:
        out = simplejson.loads(v)
        return [str(x) for x in out] if isinstance(out, list) else []
    except (ValueError, TypeError):
        return []


class ContratosMixin:
    """Se mezcla en Accesos: usa self.cr, self.lkf_api, self.user y self.ctr_f."""

    # ------------------------------------------------------------------ util

    def _ctr_error(self, msg, status=400):
        return self.LKFException({"title": "Contratos", "msg": msg, "status_code": status})

    def _ctr_hoy(self):
        tz = (self.user or {}).get("timezone") or "America/Mexico_City"
        try:
            return datetime.now(pytz.timezone(tz)).date()
        except pytz.UnknownTimeZoneError:
            return datetime.now(pytz.timezone("America/Mexico_City")).date()

    def _ctr_find(self, form_id, match=None, one=False, sort=None, skip=0, limit=0):
        q = {"form_id": form_id, "deleted_at": {"$exists": False}}
        q.update(match or {})
        cur = self.cr.find(q, {"answers": 1, "folio": 1, "created_at": 1, "updated_at": 1})
        if sort:
            cur = cur.sort(sort)
        if skip:
            cur = cur.skip(skip)
        if limit:
            cur = cur.limit(limit)
        rows = list(cur)
        return (rows[0] if rows else None) if one else rows

    def _ctr_get(self, form_id, record_id):
        try:
            oid = ObjectId(record_id)
        except Exception:  # noqa: BLE001
            return None
        return self._ctr_find(form_id, {"_id": oid}, one=True)

    def _ctr_post(self, form_id, answers, accion):
        metadata = self.lkf_api.get_metadata(form_id=form_id)
        props = {"device_properties": {**PROPS["device_properties"], "Action": accion}}
        metadata.update({"properties": props, "answers": answers})
        res = self.lkf_api.post_forms_answers(metadata)
        if res.get("status_code") not in (200, 201, 202):
            self._ctr_error(f"No se pudo guardar el registro: {res.get('json') or res}", 500)
        return (res.get("json") or {}).get("id")

    def _ctr_patch(self, form_id, record_id, answers, accion):
        """Reemplaza answers completo (patch_record no mergea: se manda todo)."""
        metadata = self.lkf_api.get_metadata(form_id=form_id)
        props = {"device_properties": {**PROPS["device_properties"], "Action": accion}}
        metadata.update({"properties": props, "answers": answers})
        res = self.lkf_api.patch_record(data=metadata, record_id=record_id)
        if res.get("status_code") not in (200, 201, 202):
            self._ctr_error(f"No se pudo actualizar el contrato: {res.get('json') or res}", 500)
        return res

    # ------------------------------------------------------- empresa activa

    def ctr_empresa_propia(self):
        f = self.ctr_f["empresas"]
        return self._ctr_find(self.EMPRESAS_FORM, {f"answers.{f['es_propia']}": opt("Sí")}, one=True)

    def ctr_empresa_activa_id(self):
        """_id (str) de la empresa del usuario del JWT."""
        user_id = (self.user or {}).get("user_id")
        emp_mod = getattr(self, "Employee", None)
        empleados_form = getattr(emp_mod, "EMPLEADOS", None) if user_id else None
        if empleados_form:
            # Mismo match que Employee.get_employee_data(user_id=...).
            uid_field = f"answers.{emp_mod.USUARIOS_OBJ_ID}.{emp_mod.employee_fields['user_id_id']}"
            # user_id se guarda a veces como texto y a veces como número.
            uids = [user_id, str(user_id)] + ([int(user_id)] if str(user_id).isdigit() else [])
            emp = self._ctr_find(empleados_form, {uid_field: {"$in": uids}}, one=True)
            empresa_id = ((emp or {}).get("answers") or {}).get(self.ctr_f["empleados"]["empresa_id"])
            if empresa_id:
                return str(empresa_id)
        propia = self.ctr_empresa_propia()
        if not propia:
            self._ctr_error("La cuenta no tiene empresa propia registrada (forma Empresas).", 409)
        return str(propia["_id"])

    # ----------------------------------------------------- lectura / formato

    def _ctr_empresa_ref(self, empresa_id, cache):
        if not empresa_id:
            return None
        if empresa_id not in cache:
            f = self.ctr_f["empresas"]
            e = self._ctr_get(self.EMPRESAS_FORM, empresa_id)
            a = (e or {}).get("answers") or {}
            cache[empresa_id] = {
                "id": empresa_id,
                "razon_social": a.get(f["razon_social"], ""),
                "rfc": a.get(f["rfc"], ""),
            }
        return cache[empresa_id]

    def _ctr_archivo(self, v):
        if isinstance(v, list):
            v = v[0] if v else None
        if not isinstance(v, dict):
            return None
        return {"name": v.get("file_name") or v.get("name", ""), "file_url": v.get("file_url", "")}

    def _ctr_recurrencia_out(self, a, forma="contratos_de_servicio"):
        """Grupo recurrencia_* de `forma` (contratos o requerimientos) al formato del front."""
        f = self.ctr_f[forma]
        tipo = label(RECURRENCIA_TIPOS, a.get(f["recurrencia_tipo"]))
        if not tipo:
            return None
        def idx(lista, valores, base=0):
            return [i + base for i, o in enumerate(lista) if opt(o) in (valores or [])]
        modo = a.get(f["recurrencia_mensual_modo"])
        out = {
            "tipo": tipo,
            "dias_semana": idx(DIAS, a.get(f["recurrencia_dias_semana"])),
            "cada_horas": _int(a.get(f["recurrencia_cada_horas"]), None),
            "semanas_mes": [int(x) for x in a.get(f["recurrencia_semanas_mes"]) or [] if str(x).isdigit()],
            "mensual_modo": {"dia_del_mes": "dia", "ordinal": "ordinal"}.get(modo),
            "mensual_dia": _int(a.get(f["recurrencia_mensual_dia"]), None),
            "mensual_ordinal": _int(a.get(f["recurrencia_mensual_ordinal"]), None),
            "mensual_dia_semana": next(iter(idx(DIAS, [a.get(f["recurrencia_mensual_dia_semana"])])), None),
            "meses": idx(MESES, a.get(f["recurrencia_meses"]), base=1),
            "cada_n": _int(a.get(f["recurrencia_cada_n"]), None),
            "unidad": label(UNIDADES, a.get(f["recurrencia_unidad"])),
            "hora_desde": (a.get(f["recurrencia_hora_desde"]) or "")[:5] or None,
            "hora_hasta": (a.get(f["recurrencia_hora_hasta"]) or "")[:5] or None,
        }
        return {k: v for k, v in out.items() if v not in (None, [])}

    def ctr_contrato_out(self, rec, cache=None):
        cache = {} if cache is None else cache
        f = self.ctr_f["contratos_de_servicio"]
        a = rec.get("answers") or {}

        def ref(k_id, k):
            return {"id": str(a.get(f[k_id]) or ""), "nombre": a.get(f[k]) or ""}

        def grupo(clave):
            return a.get(f[clave]) or []

        responsable = None
        if a.get(f["responsable_id"]):
            responsable = {"id": _int(a.get(f["responsable_id"])), "nombre": a.get(f["responsable"]) or ""}
        out = {
            "id": str(rec["_id"]),
            "folio": a.get(f["folio"]) or rec.get("folio") or "",
            "numero_contrato": a.get(f["numero_contrato"]) or None,
            "relacion": str(a.get(f["relacion_id"]) or ""),
            "cliente": self._ctr_empresa_ref(a.get(f["cliente_id"]), cache)
            or {"id": "", "razon_social": a.get(f["cliente"]) or "", "rfc": ""},
            "contratista": self._ctr_empresa_ref(a.get(f["contratista_id"]), cache)
            or {"id": "", "razon_social": a.get(f["contratista"]) or "", "rfc": ""},
            "objeto": a.get(f["objeto"]) or "",
            "descripcion": a.get(f["descripcion"]) or None,
            "monto": _num(a.get(f["monto"])),
            "inicio": a.get(f["inicio"]) or "",
            "fin": a.get(f["fin"]) or "",
            "responsable": responsable,
            "contrato_firmado": self._ctr_archivo(a.get(f["contrato_firmado"])),
            "permite_subcontratacion": a.get(f["permite_subcontratacion"]) == opt("Sí"),
            "servicios": [{"id": str(g.get(f["servicio_id"]) or ""), "nombre": g.get(f["servicio"]) or ""}
                          for g in grupo("servicios")],
            "perfiles": [{
                "perfil": {"id": str(g.get(f["perfil_id"]) or ""), "nombre": g.get(f["perfil"]) or ""},
                "cantidad": _int(g.get(f["perfil_cantidad"])),
                "requerimientos_excluidos": _ids(g.get(f["perfil_requerimientos_excluidos"])),
            } for g in grupo("perfiles")],
            "equipos": [{
                "equipo": {"id": str(g.get(f["equipo_id"]) or ""), "nombre": g.get(f["equipo"]) or ""},
                "clase": label(CLASES_EQUIPO, g.get(f["equipo_clase"])) or "Equipo",
                "cantidad": _int(g.get(f["equipo_cantidad"])),
                "requerimientos_excluidos": _ids(g.get(f["equipo_requerimientos_excluidos"])),
            } for g in grupo("equipos")],
            "ubicaciones": [{
                "ubicacion": {"id": str(g.get(f["ubicacion_id"]) or ""), "nombre": g.get(f["ubicacion"]) or ""},
                "estatus": label(ESTATUS_UBICACION, g.get(f["ubicacion_estatus"])) or "Activa",
            } for g in grupo("ubicaciones")],
            "empleados": [{
                "empleado": {"id": str(g.get(f["empleado_id"]) or ""), "nombre": g.get(f["empleado"]) or ""},
                "perfil": {"id": str(g.get(f["empleado_perfil_id"]) or ""), "nombre": g.get(f["empleado_perfil"]) or ""},
                **({"ubicacion": {"id": str(g.get(f["empleado_ubicacion_id"])), "nombre": g.get(f["empleado_ubicacion"]) or ""}}
                   if g.get(f["empleado_ubicacion_id"]) else {}),
                "fecha_alta": g.get(f["empleado_fecha_alta"]) or "",
            } for g in grupo("empleados")],
            "recurrencia": self._ctr_recurrencia_out(a),
            "estatus": label(ESTATUS, a.get(f["estatus"])) or "En documentación",
            "motivo_estatus": a.get(f["motivo_estatus"]) or None,
            "cumplimiento": {
                "total": _num(a.get(f["cumplimiento_pct"])) or 0,
                "contrato": _num(a.get(f["cumplimiento_contrato_pct"])) or 0,
                "empleados": _num(a.get(f["cumplimiento_empleados_pct"])) or 0,
                "periodicos": _num(a.get(f["cumplimiento_periodicos_pct"])) or 0,
            },
        }
        return {k: v for k, v in out.items() if v is not None}

    # ------------------------------------------------------------- escritura

    def _ctr_recurrencia_in(self, r, forma="contratos_de_servicio"):
        f = self.ctr_f[forma]
        claves = [k for k in f if k.startswith("recurrencia_")]
        out = {f[k]: None for k in claves}
        if not r:
            return out
        if r.get("tipo") not in RECURRENCIA_TIPOS:
            self._ctr_error(f"Recurrencia inválida: {r.get('tipo')}")
        out[f["recurrencia_tipo"]] = opt(r["tipo"])
        out[f["recurrencia_dias_semana"]] = [opt(DIAS[i]) for i in r.get("dias_semana") or [] if 0 <= i < 7]
        out[f["recurrencia_cada_horas"]] = r.get("cada_horas")
        # LinkaForm instaló las opciones "1".."5" como números.
        out[f["recurrencia_semanas_mes"]] = [int(i) for i in r.get("semanas_mes") or [] if 1 <= int(i) <= 5]
        out[f["recurrencia_mensual_modo"]] = {"dia": "dia_del_mes", "ordinal": "ordinal"}.get(r.get("mensual_modo"))
        out[f["recurrencia_mensual_dia"]] = r.get("mensual_dia")
        out[f["recurrencia_mensual_ordinal"]] = r.get("mensual_ordinal")
        ds = r.get("mensual_dia_semana")
        out[f["recurrencia_mensual_dia_semana"]] = opt(DIAS[ds]) if isinstance(ds, int) and 0 <= ds < 7 else None
        out[f["recurrencia_meses"]] = [opt(MESES[i - 1]) for i in r.get("meses") or [] if 1 <= i <= 12]
        out[f["recurrencia_cada_n"]] = r.get("cada_n")
        out[f["recurrencia_unidad"]] = opt(r["unidad"]) if r.get("unidad") in UNIDADES else None
        out[f["recurrencia_hora_desde"]] = f"{r['hora_desde']}:00" if r.get("hora_desde") else None
        out[f["recurrencia_hora_hasta"]] = f"{r['hora_hasta']}:00" if r.get("hora_hasta") else None
        return out

    def _ctr_answers_in(self, c):
        """Del ContratoInput (front) a answers. Solo las claves que vienen en c."""
        f = self.ctr_f["contratos_de_servicio"]
        a = {}
        if "numero_contrato" in c:
            a[f["numero_contrato"]] = c.get("numero_contrato") or None
        if "objeto" in c:
            a[f["objeto"]] = (c.get("objeto") or "").strip()
        if "descripcion" in c:
            a[f["descripcion"]] = c.get("descripcion") or None
        if "monto" in c:
            a[f["monto"]] = _num(c.get("monto"))
        for k in ("inicio", "fin"):
            if k in c:
                if c.get(k) and not _fecha(c.get(k)):
                    self._ctr_error(f"Fecha inválida en {k}: {c.get(k)} (YYYY-MM-DD)")
                a[f[k]] = str(c.get(k))[:10] if c.get(k) else None
        if "responsable" in c:
            r = c.get("responsable") or {}
            a[f["responsable_id"]] = str(r["id"]) if r.get("id") not in (None, "") else None
            a[f["responsable"]] = r.get("nombre") or None
        if "contrato_firmado" in c:
            arch = c.get("contrato_firmado")
            a[f["contrato_firmado"]] = [{"file_name": arch.get("name", ""), "file_url": arch.get("file_url", "")}] \
                if arch and arch.get("file_url") else []
        if "permite_subcontratacion" in c:
            a[f["permite_subcontratacion"]] = opt("Sí") if c.get("permite_subcontratacion") else opt("No")
        if "servicios" in c:
            a[f["servicios"]] = [{f["servicio_id"]: s.get("id"), f["servicio"]: s.get("nombre")}
                                 for s in c.get("servicios") or []]
        if "perfiles" in c:
            a[f["perfiles"]] = [{
                f["perfil_id"]: (p.get("perfil") or {}).get("id"),
                f["perfil"]: (p.get("perfil") or {}).get("nombre"),
                f["perfil_cantidad"]: _int(p.get("cantidad"), 1),
                f["perfil_requerimientos_excluidos"]: simplejson.dumps(p.get("requerimientos_excluidos") or []),
            } for p in c.get("perfiles") or []]
        if "equipos" in c:
            a[f["equipos"]] = [{
                f["equipo_id"]: (e.get("equipo") or {}).get("id"),
                f["equipo"]: (e.get("equipo") or {}).get("nombre"),
                f["equipo_clase"]: opt(e["clase"]) if e.get("clase") in CLASES_EQUIPO else opt("Equipo"),
                f["equipo_cantidad"]: _int(e.get("cantidad"), 1),
                f["equipo_requerimientos_excluidos"]: simplejson.dumps(e.get("requerimientos_excluidos") or []),
            } for e in c.get("equipos") or []]
        if "ubicaciones" in c:
            a[f["ubicaciones"]] = [{
                f["ubicacion_id"]: (u.get("ubicacion") or {}).get("id"),
                f["ubicacion"]: (u.get("ubicacion") or {}).get("nombre"),
                f["ubicacion_estatus"]: opt(u["estatus"]) if u.get("estatus") in ESTATUS_UBICACION else opt("Activa"),
            } for u in c.get("ubicaciones") or []]
        if "empleados" in c:
            a[f["empleados"]] = [{
                f["empleado_id"]: (e.get("empleado") or {}).get("id"),
                f["empleado"]: (e.get("empleado") or {}).get("nombre"),
                f["empleado_perfil_id"]: (e.get("perfil") or {}).get("id"),
                f["empleado_perfil"]: (e.get("perfil") or {}).get("nombre"),
                f["empleado_ubicacion_id"]: (e.get("ubicacion") or {}).get("id"),
                f["empleado_ubicacion"]: (e.get("ubicacion") or {}).get("nombre"),
                f["empleado_fecha_alta"]: (e.get("fecha_alta") or "")[:10] or self._ctr_hoy().isoformat(),
            } for e in c.get("empleados") or []]
        if "recurrencia" in c:
            a.update(self._ctr_recurrencia_in(c.get("recurrencia")))
        return a

    def _ctr_validar(self, a):
        f = self.ctr_f["contratos_de_servicio"]
        if not a.get(f["objeto"]):
            self._ctr_error("El objeto del contrato es requerido.")
        ini, fin = _fecha(a.get(f["inicio"])), _fecha(a.get(f["fin"]))
        if not ini or not fin:
            self._ctr_error("Inicio y fin del contrato son requeridos.")
        if fin < ini:
            self._ctr_error("La fecha de fin no puede ser anterior a la de inicio.")
        for g, k in (("perfiles", "perfil_cantidad"), ("equipos", "equipo_cantidad")):
            for r in a.get(f[g]) or []:
                if _int(r.get(f[k])) < 1:
                    self._ctr_error(f"La cantidad en {g} debe ser al menos 1.")

    def _ctr_siguiente_folio(self):
        f = self.ctr_f["contratos_de_servicio"]
        n = 0
        for r in self._ctr_find(self.CONTRATOS_FORM):
            m = re.match(r"^C-(\d+)$", str((r.get("answers") or {}).get(f["folio"]) or ""))
            if m:
                n = max(n, int(m.group(1)))
        return f"C-{n + 1:04d}"

    def _ctr_limitantes_pendientes(self, contrato_id, relacion_id=None):
        """True si algún requerimiento limitante del contrato (o asignado a su
        relación) no está cumplido. Sin motor (forma no instalada) o sin id = True."""
        if not contrato_id or not self.CUMPLIMIENTO_FORM:
            return True
        f = self.ctr_f["cumplimiento_de_requerimientos"]
        match = {f"answers.{f['contrato_id']}": str(contrato_id)}
        if relacion_id:
            match = {"$or": [match, {f"answers.{f['relacion_id']}": str(relacion_id),
                                     f"answers.{f['contrato_id']}": {"$in": [None, ""]}}]}
        match[f"answers.{f['limitante']}"] = opt("Sí")
        ok = {opt(e) for e in ("Cumplido", "En ceros", "No aplica", "Por transcurrir")}
        for r in self._ctr_find(self.CUMPLIMIENTO_FORM, match):
            a = r.get("answers") or {}
            if (a.get(f["estado_manual"]) or a.get(f["estado"])) not in ok:
                return True
        return False

    def ctr_calcular_estatus(self, a, contrato_id=None):
        """Orden de la spec: manual > Vencido > En documentación > Por vencer > Activo."""
        f = self.ctr_f["contratos_de_servicio"]
        manual = label(ESTATUS_MANUAL, a.get(f["estatus_manual"]))
        if manual:
            return manual
        hoy = self._ctr_hoy()
        fin = _fecha(a.get(f["fin"]))
        if fin and fin < hoy:
            return "Vencido"
        if self._ctr_limitantes_pendientes(contrato_id, a.get(f["relacion_id"])):
            return "En documentación"
        if fin and fin - hoy <= timedelta(days=DIAS_POR_VENCER):
            return "Por vencer"
        return "Activo"

    def _ctr_relacion_visible(self, relacion_id, mi_empresa):
        f = self.ctr_f["relaciones_entre_empresas"]
        rel = self._ctr_get(self.RELACIONES_FORM, relacion_id) if relacion_id else None
        if not rel:
            self._ctr_error("La relación no existe.", 404)
        a = rel.get("answers") or {}
        cliente, contratista = str(a.get(f["cliente_id"]) or ""), str(a.get(f["contratista_id"]) or "")
        if mi_empresa not in (cliente, contratista):
            self._ctr_error("No tienes acceso a esta relación.", 403)
        return {"cliente_id": cliente, "cliente": a.get(f["cliente"]) or "",
                "contratista_id": contratista, "contratista": a.get(f["contratista"]) or ""}

    def _ctr_contrato_visible(self, contrato_id):
        mi_empresa = self.ctr_empresa_activa_id()
        rec = self._ctr_get(self.CONTRATOS_FORM, contrato_id)
        if not rec:
            self._ctr_error("El contrato no existe.", 404)
        f = self.ctr_f["contratos_de_servicio"]
        a = rec.get("answers") or {}
        if mi_empresa not in (str(a.get(f["cliente_id"]) or ""), str(a.get(f["contratista_id"]) or "")):
            self._ctr_error("No tienes acceso a este contrato.", 403)
        return rec

    # ------------------------------------------------------------- historial

    def _ctr_autor(self):
        u = self.user or {}
        return u.get("name") or u.get("username") or u.get("email") or str(u.get("user_id") or "")

    def _ctr_evento(self, contrato_id, folio, evento, detalle, antes=None, despues=None):
        if not self.HISTORIAL_CONTRATOS_FORM:
            return None
        f = self.ctr_f["historial_de_contratos"]
        tz = (self.user or {}).get("timezone") or "America/Mexico_City"
        try:
            ahora = datetime.now(pytz.timezone(tz))
        except pytz.UnknownTimeZoneError:
            ahora = datetime.now(pytz.timezone("America/Mexico_City"))
        return self._ctr_post(self.HISTORIAL_CONTRATOS_FORM, {
            f["contrato_id"]: str(contrato_id),
            f["contrato"]: folio,
            f["evento"]: opt(evento),
            f["detalle"]: detalle[:500],
            f["antes"]: simplejson.dumps(antes, ensure_ascii=False) if antes is not None else None,
            f["despues"]: simplejson.dumps(despues, ensure_ascii=False) if despues is not None else None,
            f["autor"]: self._ctr_autor(),
            f["fecha"]: ahora.strftime("%Y-%m-%d %H:%M:%S"),
        }, "historial_contrato")

    @staticmethod
    def _ctr_fmt(v):
        if isinstance(v, (int, float)):
            return f"{v:,.2f}".rstrip("0").rstrip(".")
        if isinstance(v, list):
            partes = []
            for it in v:
                if not isinstance(it, dict):
                    continue
                if "nombre" in it:  # servicios: Ref directo
                    partes.append(it["nombre"])
                    continue
                ref = next((x for x in it.values() if isinstance(x, dict) and "nombre" in x), {})
                txt = ref.get("nombre", "")
                if it.get("cantidad"):
                    txt += f" ×{it['cantidad']}"
                if it.get("estatus"):
                    txt += f" ({it['estatus']})"
                partes.append(txt)
            return ", ".join(p for p in partes if p) or "ninguno"
        return "—" if v in (None, "") else str(v)

    def _ctr_eventos_cambio(self, antes_out, despues_out):
        """Un evento por grupo de cambio (Monto, Vigencia, Perfiles…); el resto, Modificatorio."""
        cambios = [k for k in CAMPOS_EDITABLES if antes_out.get(k) != despues_out.get(k)]
        eventos, usados = {}, set()
        for campo, evento in EVENTO_POR_CAMPO:
            if campo in cambios:
                eventos.setdefault(evento, []).append(campo)
                usados.add(campo)
        resto = [c for c in cambios if c not in usados]
        if resto:
            eventos.setdefault("Modificatorio", []).extend(resto)
        out = []
        for evento, campos in eventos.items():
            detalle = "; ".join(
                f"{c.replace('_', ' ').capitalize()}: {self._ctr_fmt(antes_out.get(c))} → {self._ctr_fmt(despues_out.get(c))}"
                for c in campos)
            out.append((evento, detalle, {c: antes_out.get(c) for c in campos}, {c: despues_out.get(c) for c in campos}))
        return out

    # ------------------------------------------------------------------ API

    def list_contratos(self, relacion_id=None, estatus=None, fin_desde=None, fin_hasta=None,
                       search=None, limit=25, offset=0):
        mi_empresa = self.ctr_empresa_activa_id()
        f = self.ctr_f["contratos_de_servicio"]
        match = {"$or": [{f"answers.{f['cliente_id']}": mi_empresa},
                         {f"answers.{f['contratista_id']}": mi_empresa}]}
        if relacion_id:
            match[f"answers.{f['relacion_id']}"] = str(relacion_id)
        if estatus:
            match[f"answers.{f['estatus']}"] = {"$in": [opt(e) for e in estatus]}
        rango = {}
        if fin_desde:
            rango["$gte"] = str(fin_desde)[:10]
        if fin_hasta:
            rango["$lte"] = str(fin_hasta)[:10]
        if rango:
            match[f"answers.{f['fin']}"] = rango
        if search:
            rx = {"$regex": re.escape(search.strip()), "$options": "i"}
            match["$and"] = [{"$or": [{f"answers.{f[k]}": rx} for k in
                                      ("folio", "numero_contrato", "objeto", "cliente", "contratista")]}]
        q = {"form_id": self.CONTRATOS_FORM, "deleted_at": {"$exists": False}, **match}
        total = self.cr.count_documents(q)
        limit = max(1, min(_int(limit, 25), 200))
        rows = self._ctr_find(self.CONTRATOS_FORM, match, sort=[("created_at", -1)],
                              skip=max(0, _int(offset)), limit=limit)
        cache = {}
        return {"items": [self.ctr_contrato_out(r, cache) for r in rows], "total": total}

    def get_contrato(self, contrato_id):
        return self.ctr_contrato_out(self._ctr_contrato_visible(contrato_id))

    def create_contrato(self, contrato):
        if not self.CONTRATOS_FORM:
            self._ctr_error("La forma Contratos de servicio no está instalada en esta cuenta.", 409)
        contrato = contrato or {}
        mi_empresa = self.ctr_empresa_activa_id()
        rel = self._ctr_relacion_visible(contrato.get("relacion"), mi_empresa)
        f = self.ctr_f["contratos_de_servicio"]
        a = {f[k]: None for k in f if k not in ("servicios", "perfiles", "equipos", "ubicaciones", "empleados")
             and not k.startswith(("servicio_", "perfil_", "equipo_", "ubicacion_", "empleado_"))}
        a.update({f["servicios"]: [], f["perfiles"]: [], f["equipos"]: [], f["ubicaciones"]: [], f["empleados"]: []})
        a.update(self._ctr_answers_in(contrato))
        self._ctr_validar(a)
        folio = self._ctr_siguiente_folio()
        a.update({
            f["folio"]: folio,
            f["relacion_id"]: str(contrato.get("relacion")),
            f["relacion"]: f"{rel['cliente']} → {rel['contratista']}",
            f["cliente_id"]: rel["cliente_id"], f["cliente"]: rel["cliente"],
            f["contratista_id"]: rel["contratista_id"], f["contratista"]: rel["contratista"],
            f["permite_subcontratacion"]: a.get(f["permite_subcontratacion"]) or opt("No"),
            f["estatus"]: opt("En documentación"),
            f["cumplimiento_pct"]: 0, f["cumplimiento_contrato_pct"]: 0,
            f["cumplimiento_empleados_pct"]: 0, f["cumplimiento_periodicos_pct"]: 0,
        })
        a = {k: v for k, v in a.items() if v is not None}
        contrato_id = self._ctr_post(self.CONTRATOS_FORM, a, "create_contrato")
        if not contrato_id:
            self._ctr_error("LinkaForm no regresó el id del contrato creado.", 500)
        self._ctr_evento(contrato_id, folio, "Creación", f"Contrato {folio} creado: {a.get(f['objeto'])}")
        self.cum_despues_de_contrato(contrato_id)
        return self.get_contrato(contrato_id)

    def _ctr_guardar_cambio(self, rec, nuevos, accion, eventos_extra=None):
        f = self.ctr_f["contratos_de_servicio"]
        contrato_id = str(rec["_id"])
        antes_out = self.ctr_contrato_out(rec)
        a = {**(rec.get("answers") or {}), **nuevos}
        self._ctr_validar(a)
        a[f["estatus"]] = opt(self.ctr_calcular_estatus(a, contrato_id))
        self._ctr_patch(self.CONTRATOS_FORM, contrato_id, a, accion)
        despues_out = self.ctr_contrato_out({**rec, "answers": a})
        folio = antes_out.get("folio", "")
        for evento, detalle, antes, despues in (eventos_extra or []) + self._ctr_eventos_cambio(antes_out, despues_out):
            self._ctr_evento(contrato_id, folio, evento, detalle, antes, despues)
        if antes_out.get("estatus") != despues_out.get("estatus") and not eventos_extra:
            self._ctr_evento(contrato_id, folio, "Estatus",
                             f"Estatus: {antes_out.get('estatus')} → {despues_out.get('estatus')}",
                             {"estatus": antes_out.get("estatus")}, {"estatus": despues_out.get("estatus")})
        # Motor de cumplimiento (ME-15): filas, % y estatus con los datos nuevos.
        self.cum_despues_de_contrato(contrato_id)
        return self.ctr_contrato_out(self._ctr_get(self.CONTRATOS_FORM, contrato_id))

    def update_contrato(self, contrato_id, contrato):
        rec = self._ctr_contrato_visible(contrato_id)
        cambios = {k: v for k, v in (contrato or {}).items() if k in CAMPOS_EDITABLES}
        if not cambios:
            return self.ctr_contrato_out(rec)
        return self._ctr_guardar_cambio(rec, self._ctr_answers_in(cambios), "update_contrato")

    def change_status_contrato(self, contrato_id, estatus_manual=None, motivo=""):
        rec = self._ctr_contrato_visible(contrato_id)
        f = self.ctr_f["contratos_de_servicio"]
        motivo = (motivo or "").strip()
        if estatus_manual not in (None, "", *ESTATUS_MANUAL):
            self._ctr_error(f"Estatus manual inválido: {estatus_manual}")
        if not motivo:
            self._ctr_error("El motivo es requerido.")
        actual = label(ESTATUS_MANUAL, (rec.get("answers") or {}).get(f["estatus_manual"]))
        if actual == "Cancelado":
            self._ctr_error("Un contrato cancelado no se puede reanudar ni pausar.", 409)
        nuevo = estatus_manual or None
        if nuevo == actual:
            return self.ctr_contrato_out(rec)
        evento = {"Pausado": "Pausa", "Cancelado": "Cancelación", None: "Reanudación"}[nuevo]
        detalle = f"{evento}: {motivo}"
        extra = [(evento, detalle, {"estatus_manual": actual}, {"estatus_manual": nuevo})]
        return self._ctr_guardar_cambio(rec, {
            f["estatus_manual"]: opt(nuevo) if nuevo else None,
            f["motivo_estatus"]: motivo,
        }, "change_status_contrato", eventos_extra=extra)

    def get_historial_contrato(self, contrato_id):
        self._ctr_contrato_visible(contrato_id)
        f = self.ctr_f["historial_de_contratos"]
        eventos = ["Creación", "Ubicaciones", "Perfiles", "Equipos", "Servicios", "Empleados", "Monto",
                   "Vigencia", "Estatus", "Pausa", "Reanudación", "Cancelación", "Modificatorio"]
        rows = self._ctr_find(self.HISTORIAL_CONTRATOS_FORM, {f"answers.{f['contrato_id']}": str(contrato_id)},
                              sort=[("created_at", -1)])
        out = []
        for r in rows:
            a = r.get("answers") or {}
            item = {
                "id": str(r["_id"]),
                "contrato": str(contrato_id),
                "evento": label(eventos, a.get(f["evento"])) or "",
                "detalle": a.get(f["detalle"]) or "",
                "autor": a.get(f["autor"]) or "",
                "fecha": a.get(f["fecha"]) or "",
            }
            for k in ("antes", "despues"):
                try:
                    item[k] = simplejson.loads(a[f[k]]) if a.get(f[k]) else None
                except (ValueError, TypeError):
                    item[k] = None
            doc = self._ctr_archivo(a.get(f["documento"]))
            if doc:
                item["documento"] = doc
            out.append({k: v for k, v in item.items() if v is not None})
        return out
