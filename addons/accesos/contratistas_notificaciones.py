# -*- coding: utf-8 -*-
"""Notificar incumplimientos al contratista (MX-03-B).

Ficha: contratistas_mx03_notificar.md. Decisiones de Paco (2026-11-24):
- Correo al representante legal; si no tiene correo, al primer contacto con
  correo; si ninguno, solo el aviso en el portal y se reporta "sin correo".
  El correo sale por la forma Envío de notificaciones (tipo email, clase
  general), como los demás avisos de Clave10.
- Aviso en el portal = bandeja del usuario (CouchDB clave_{user_id}, doc
  inbox: true, type "aviso_cumplimiento") de cada usuario de la empresa
  contratista (Empleados con esa empresa y usuario ligado).
- Historial en la relación: grupo "notificaciones" (fecha, autor, motivo,
  incumplimientos, correo, si se envió y usuarios avisados). La última sale
  en la relación como `ultima_notificacion` ("Alerta enviada").

Reglas:
- Solo el cliente notifica a su contratista (en espejo solo Contratistas
  notifica) y solo con la relación Activa.
- Incumplimiento = filas del motor ME-15 de la relación en Rechazado, Vencido
  o Por subir (ya venció sin documento = "No entregado"); estado manual gana.
  Con requerimiento_id, solo ese requerimiento.
- Motivo obligatorio. Las relaciones sin incumplimientos no se notifican
  (se regresan en `omitidas`).
"""
import time

import simplejson

from .contratistas_contratos import _int, label, opt
from .contratistas_cumplimiento import ESTADOS, ESTADOS_MANUALES

INCUMPLE = {"Rechazado": "Rechazado", "Vencido": "Vencido", "Por subir": "No entregado"}
MAX_MOTIVO = 5000
MAX_RELACIONES = 200


class NotificacionesMixin:
    """Se mezcla en Accesos junto con RelacionesMixin y CumplimientoMixin."""

    def _ntf_error(self, msg, status=400):
        return self.LKFException({"title": "Notificaciones", "msg": msg, "status_code": status})

    # ------------------------------------------------------------ datos

    def _ntf_incumplimientos(self, relacion_id, requerimiento_id=None):
        """[{requerimiento, periodos: [{clave, estado, sujeto}]}] de la relación."""
        if not self.CUMPLIMIENTO_FORM:
            return []
        fcu = self.ctr_f["cumplimiento_de_requerimientos"]
        match = {f"answers.{fcu['relacion_id']}": str(relacion_id)}
        if requerimiento_id:
            match[f"answers.{fcu['requerimiento_id']}"] = str(requerimiento_id)
        por_req = {}
        for r in self._ctr_find(self.CUMPLIMIENTO_FORM, match):
            a = r.get("answers") or {}
            estado = label(ESTADOS_MANUALES, a.get(fcu["estado_manual"])) or label(ESTADOS, a.get(fcu["estado"]))
            if estado not in INCUMPLE:
                continue
            rid = str(a.get(fcu["requerimiento_id"]) or "")
            g = por_req.setdefault(rid, {"requerimiento": {"id": rid, "nombre": a.get(fcu["requerimiento"]) or ""},
                                         "periodos": []})
            sujeto = a.get(fcu["sujeto_empleado"]) or a.get(fcu["sujeto_equipo"]) or None
            g["periodos"].append({"clave": a.get(fcu["periodo_clave"]) or "unico", "estado": INCUMPLE[estado],
                                  **({"sujeto": sujeto} if sujeto else {})})
        out = sorted(por_req.values(), key=lambda g: g["requerimiento"]["nombre"].lower())
        for g in out:
            g["periodos"].sort(key=lambda p: (p["clave"], p.get("sujeto") or ""))
        return out

    def _ntf_destinatario(self, empresa_id):
        """Representante legal con correo; si no, el primer contacto con correo."""
        fe = self.ctr_f["empresas"]
        a = (self._ctr_get(self.EMPRESAS_FORM, empresa_id) or {}).get("answers") or {}
        contactos = [c for c in a.get(fe["contactos"]) or [] if (c.get(fe["contacto_email"]) or "").strip()]
        rep = [c for c in contactos if c.get(fe["contacto_rol"]) == opt("Representante legal")]
        c = (rep or contactos or [None])[0]
        if not c:
            return None
        return {"nombre": c.get(fe["contacto_nombre"]) or "", "email": c[fe["contacto_email"]].strip(),
                "rol": label(["Representante legal", "Apoderado legal", "Contacto"], c.get(fe["contacto_rol"])) or "Contacto"}

    def _ntf_usuarios(self, empresa_id):
        """user_id de los usuarios ligados a empleados activos de la empresa."""
        emp = getattr(self, "Employee", None)
        if not (emp and getattr(emp, "EMPLEADOS", None)):
            return []
        campo = emp.employee_fields["user_id_id"]
        uids = []
        for e in self._ctr_find(emp.EMPLEADOS, {f"answers.{self.ctr_f['empleados']['empresa_id']}": str(empresa_id)}):
            u = ((e.get("answers") or {}).get(emp.USUARIOS_OBJ_ID) or {}).get(campo)
            u = u[0] if isinstance(u, list) and u else u
            if u and str(u).isdigit() and int(u) not in uids:
                uids.append(int(u))
        return uids

    @staticmethod
    def _ntf_mensaje(destinatario, cliente, incumplimientos, anio):
        saludo = f"Hola {destinatario['nombre']}," if destinatario and destinatario.get("nombre") else "Hola,"
        lineas = [saludo, "", f"{cliente} te avisa que estas obligaciones no se cumplieron en {anio}:", ""]
        for g in incumplimientos:
            periodos = ", ".join(f"{p['clave'] if p['clave'] != 'unico' else 'vigente'}"
                                 f"{' (' + p['sujeto'] + ')' if p.get('sujeto') else ''}: {p['estado']}"
                                 for p in g["periodos"])
            lineas.append(f"- {g['requerimiento']['nombre']}: {periodos}")
        lineas += ["", "Sube o corrige los documentos en tu portal de Clave 10 para regularizarte."]
        return "\n".join(lineas)

    def _ntf_relacion(self, relacion_id, mi_empresa):
        fr = self.ctr_f["relaciones_entre_empresas"]
        rec = self._ctr_get(self.RELACIONES_FORM, str(relacion_id or "")) if self.RELACIONES_FORM else None
        if not rec:
            self._ntf_error(f"La relación {relacion_id} no existe.", 404)
        a = rec.get("answers") or {}
        if str(a.get(fr["cliente_id"]) or "") != mi_empresa:
            self._ntf_error("Solo el cliente notifica incumplimientos a su contratista.", 403)
        return rec

    def ntf_ultima(self, answers):
        """Última notificación guardada en la relación (o None)."""
        fr = self.ctr_f["relaciones_entre_empresas"]
        hist = answers.get(fr["notificaciones"]) or []
        if not hist:
            return None
        h = hist[-1]
        return {"fecha": h.get(fr["notif_fecha"]) or "", "autor": h.get(fr["notif_autor"]) or "",
                "correo_enviado": h.get(fr["notif_correo_enviado"]) == opt("Sí"), "total": len(hist)}

    # ------------------------------------------------------------- API

    def get_incumplimientos(self, relacion_ids, requerimiento_id=None):
        """Destinatarios del modal: por relación, contacto, incumplimientos y mensaje sugerido."""
        ids = [relacion_ids] if isinstance(relacion_ids, str) else list(relacion_ids or [])
        if not ids:
            self._ntf_error("Elige al menos un contratista.")
        mi_empresa = self.ctr_empresa_activa_id()
        cliente = self._ctr_empresa_ref(mi_empresa, {}).get("razon_social") or ""
        fr = self.ctr_f["relaciones_entre_empresas"]
        anio = self._ctr_hoy().year
        items = []
        for rid in dict.fromkeys(str(i) for i in ids):
            rec = self._ntf_relacion(rid, mi_empresa)
            a = rec.get("answers") or {}
            contratista_id = str(a.get(fr["contratista_id"]) or "")
            inc = self._ntf_incumplimientos(rid, requerimiento_id)
            dest = self._ntf_destinatario(contratista_id)
            items.append({
                "relacion_id": rid, "folio": a.get(fr["folio"]) or "",
                "contratista": self._ctr_empresa_ref(contratista_id, {}),
                "estatus": "Inactivo" if a.get(fr["estatus"]) == opt("Inactivo") else "Activo",
                "destinatario": dest,
                "incumplimientos": inc,
                "total": sum(len(g["periodos"]) for g in inc),
                "mensaje_sugerido": self._ntf_mensaje(dest, cliente, inc, anio) if inc else "",
                "ultima_notificacion": self.ntf_ultima(a),
            })
        con = [x for x in items if x["total"]]
        generico = (f"{cliente} te avisa que tienes obligaciones de cumplimiento pendientes en {anio}. "
                    "Revisa el detalle en tu portal de Clave 10 y sube o corrige los documentos para regularizarte.")
        return {"items": items, "con_incumplimientos": len(con),
                "mensaje_sugerido": con[0]["mensaje_sugerido"] if len(con) == 1 else generico}

    def notificar_incumplimientos(self, relacion_ids, motivo, requerimiento_id=None):
        """Correo + aviso en la bandeja + historial en la relación, por contratista con incumplimientos."""
        motivo = (motivo or "").strip()
        if not motivo:
            self._ntf_error("Escribe el motivo.")
        if len(motivo) > MAX_MOTIVO:
            self._ntf_error(f"El motivo pasa de {MAX_MOTIVO} caracteres.")
        ids = list(dict.fromkeys(str(i) for i in ([relacion_ids] if isinstance(relacion_ids, str) else relacion_ids or [])))
        if not ids:
            self._ntf_error("Elige al menos un contratista.")
        if len(ids) > MAX_RELACIONES:
            self._ntf_error(f"Se pueden notificar hasta {MAX_RELACIONES} contratistas a la vez.")
        mi_empresa = self.ctr_empresa_activa_id()
        cliente = self._ctr_empresa_ref(mi_empresa, {}).get("razon_social") or ""
        fr = self.ctr_f["relaciones_entre_empresas"]
        # Validar todo antes de enviar nada.
        plan = []
        omitidas = []
        for rid in ids:
            rec = self._ntf_relacion(rid, mi_empresa)
            a = rec.get("answers") or {}
            if a.get(fr["estatus"]) == opt("Inactivo"):
                self._ntf_error(f"La relación {a.get(fr['folio']) or rid} está inactiva.", 409)
            inc = self._ntf_incumplimientos(rid, requerimiento_id)
            if not inc:
                omitidas.append({"relacion_id": rid, "folio": a.get(fr["folio"]) or "", "motivo": "Sin incumplimientos"})
                continue
            plan.append((rec, inc))
        items = []
        ahora, autor = self._doc_ahora(), self._ctr_autor()
        for rec, inc in plan:
            a = dict(rec.get("answers") or {})
            rid = str(rec["_id"])
            contratista_id = str(a.get(fr["contratista_id"]) or "")
            contratista = self._ctr_empresa_ref(contratista_id, {})
            dest = self._ntf_destinatario(contratista_id)
            titulo = f"Incumplimientos de cumplimiento · {cliente}"
            correo_ok = False
            error_correo = None
            if dest:
                try:
                    correo_ok = self._ntf_enviar_correo(dest, titulo, motivo)
                except Exception as e:  # noqa: BLE001
                    error_correo = str(e)[:200]
            portal = self._ntf_bandeja(contratista_id, rid, titulo, motivo, cliente, inc, ahora)
            a[fr["notificaciones"]] = list(a.get(fr["notificaciones"]) or []) + [{
                fr["notif_fecha"]: ahora, fr["notif_autor"]: autor, fr["notif_motivo"]: motivo,
                fr["notif_incumplimientos"]: simplejson.dumps(inc, ensure_ascii=False)[:20000],
                fr["notif_correo"]: (dest or {}).get("email") or "",
                fr["notif_correo_enviado"]: opt("Sí") if correo_ok else opt("No"),
                fr["notif_portal"]: portal}]
            self._ctr_patch(self.RELACIONES_FORM, rid, a, "notificar_incumplimientos")
            items.append({"relacion_id": rid, "folio": a.get(fr["folio"]) or "", "contratista": contratista,
                          "correo": (dest or {}).get("email"), "correo_enviado": correo_ok,
                          **({"error_correo": error_correo} if error_correo else {}),
                          **({} if dest else {"sin_correo": True}),
                          "portal": portal, "incumplimientos": sum(len(g["periodos"]) for g in inc),
                          "fecha": ahora})
        return {"enviadas": len(items), "items": items, "omitidas": omitidas}

    # --------------------------------------------------------- canales

    def _ntf_enviar_correo(self, dest, titulo, mensaje):
        f = self.envio_correo_fields
        form = getattr(self, "ENVIO_DE_NOTIFICACIONES_FORM", None)
        if not form:
            self._ntf_error("La forma Envío de notificaciones no está instalada en esta cuenta.", 409)
        answers = {
            f["tipo_de_notificacion"]: "email", f["clase"]: "general",
            f["titulo"]: titulo, f["nombre"]: dest.get("nombre") or "", f["msj"]: mensaje,
            f["email_from"]: "no-reply@linkaform.com", f["email_to"]: dest["email"],
            f["enviado_desde"]: "Contratistas · Cumplimiento",
        }
        self._ctr_post(form, answers, "notificar_incumplimientos")  # truena si LinkaForm no lo guarda
        return True

    def _ntf_bandeja(self, empresa_id, relacion_id, titulo, motivo, cliente, inc, ahora):
        """Aviso en la bandeja de cada usuario de la empresa; regresa cuántos se avisaron."""
        n = 0
        for uid in self._ntf_usuarios(empresa_id):
            try:
                db = self.get_couch_user_db(f"clave_{uid}")
                db.save({
                    "_id": f"aviso_{relacion_id}_{int(time.time() * 1000)}",
                    "type": "aviso_cumplimiento", "inbox": True, "status": "synced", "status_user": "new",
                    "created_at": int(time.time()), "updated_at": ahora,
                    "record": {"titulo": titulo, "cliente": cliente, "motivo": motivo, "relacion_id": relacion_id,
                               "incumplimientos": inc,
                               "total": sum(len(g["periodos"]) for g in inc)},
                })
                n += 1
            except Exception as e:  # noqa: BLE001
                print(f"notificar_incumplimientos: no se pudo avisar a clave_{uid}: {e}")
        return _int(n, 0)
