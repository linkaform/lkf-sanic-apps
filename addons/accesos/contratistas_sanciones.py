# -*- coding: utf-8 -*-
"""Sanciones de Contratistas (R-07, incluye las del empleado de ME-05).

Fichas: contratistas_r07_sanciones.md y contratistas_me05_empleado_contratos.md.
Decisiones de Paco (2026-11-24):
- Una forma Sanciones; el sancionado es un Empleado (diseño de ME-05) o la
  Empresa contratista ("Nueva Sanción" de Contratistas, mismos campos).
- Estatus Vigente / Cumplida, calculado: con días sin acceso es Vigente hasta
  que termina la suspensión; una amonestación (sin días) queda Cumplida.
  Abierto / En proceso / Cerrado es de las incidencias de Seguridad (no se toca).
- "Sin días de acceso" solo se registra: el empleado expone `suspendido_hasta`;
  bloquear pases o check-in queda para después.
- Acta = PDF simple provisional (sin diseño), guardado en la sanción.

Reglas:
- Empleado propio (su empresa = empresa activa): sanción interna, sin relación.
  Empleado de otra empresa: hace falta una relación Activa donde la empresa
  activa es el cliente y la del empleado el contratista.
- Empresa: solo el cliente de una relación Activa sanciona a su contratista.
- Ven la sanción la empresa que registra y la sancionada; comentan las dos;
  editan, borran e imprimen el acta solo quien registra.
- Motivo "Otro" pide el texto; días sin acceso de 1 a 8 con fecha de inicio,
  solo para empleados.
"""
import io
import os
import re
import tempfile
from datetime import timedelta

from .contratistas_contratos import _fecha, _int, label, opt

SUJETOS = ["Empleado", "Empresa"]
MOTIVOS = ["Retardos", "Falta injustificada", "No portar EPP", "Abandono de puesto",
           "Incumplimiento de procedimiento", "Conducta inapropiada", "Otro"]
MAX_DIAS = 8
MAX_COMENTARIO = 2000


def fuente(size, negrita=False):
    """TTF con acentos (DejaVu); la default de PIL no trae á, é, í, ó, ú, ñ."""
    from PIL import ImageFont
    nombre = "DejaVuSans-Bold.ttf" if negrita else "DejaVuSans.ttf"
    for ruta in (nombre, f"/usr/share/fonts/truetype/dejavu/{nombre}"):
        try:
            return ImageFont.truetype(ruta, size)
        except OSError:
            pass
    try:
        import matplotlib
        return ImageFont.truetype(os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf", nombre), size)
    except Exception:  # noqa: BLE001
        return ImageFont.load_default(size=size)


class SancionesMixin:
    """Se mezcla en Accesos junto con EmpleadosMixin, RelacionesMixin y DocumentosMixin."""

    def _san_error(self, msg, status=400):
        return self.LKFException({"title": "Sanciones", "msg": msg, "status_code": status})

    def _san_requiere(self):
        if not getattr(self, "SANCIONES_FORM", None):
            self._san_error("La forma Sanciones no está instalada en esta cuenta.", 409)

    # ------------------------------------------------------------ salida

    def _san_estatus(self, a):
        fs = self.ctr_f["sanciones"]
        if a.get(fs["sin_acceso"]) == opt("Sí") and a.get(fs["fin_suspension"]):
            return "Vigente" if str(a[fs["fin_suspension"]])[:10] >= self._ctr_hoy().isoformat() else "Cumplida"
        return "Cumplida"

    def san_out(self, rec, mi_empresa=None):
        fs = self.ctr_f["sanciones"]
        a = rec.get("answers") or {}

        def ref(k):
            return {"id": str(a[fs[f"{k}_id"]]), "nombre": a.get(fs[k]) or ""} if a.get(fs[f"{k}_id"]) else None

        sin = a.get(fs["sin_acceso"]) == opt("Sí")
        motivo = label(MOTIVOS, a.get(fs["motivo"])) or "Otro"
        comentarios = [{
            "autor": c.get(fs["comentario_autor"]) or "", "fecha": c.get(fs["comentario_fecha"]) or "",
            "texto": c.get(fs["comentario_texto"]) or "",
            "evidencias": [x for x in (self._ctr_archivo(e) for e in c.get(fs["comentario_evidencias"]) or []) if x],
        } for c in a.get(fs["comentarios"]) or []]
        out = {
            "id": str(rec["_id"]),
            "folio": a.get(fs["folio"]) or "",
            "sujeto_tipo": label(SUJETOS, a.get(fs["sujeto_tipo"])) or "Empleado",
            "empleado": ref("empleado"),
            "empresa": ref("empresa"),
            "registra": ref("registra"),
            "relacion": ref("relacion"),
            "contrato": ref("contrato"),
            "motivo": motivo,
            "motivo_otro": a.get(fs["motivo_otro"]) or None,
            "fecha": a.get(fs["fecha"]) or None,
            "sin_acceso": sin,
            "dias_sin_acceso": _int(a.get(fs["dias_sin_acceso"]), 0) if sin else 0,
            "inicio_suspension": a.get(fs["inicio_suspension"]) if sin else None,
            "fin_suspension": a.get(fs["fin_suspension"]) if sin else None,
            "registro": a.get(fs["registro"]) or "",
            "acta": self._ctr_archivo((a.get(fs["acta"]) or [None])[0] if isinstance(a.get(fs["acta"]), list) else a.get(fs["acta"])),
            "comentarios": comentarios,
            "evidencias": sum(len(c["evidencias"]) for c in comentarios),
            "estatus": self._san_estatus(a),
        }
        if mi_empresa is not None:
            out["editable"] = (out["registra"] or {}).get("id") == mi_empresa
        return out

    # ------------------------------------------------------- validación

    def _san_visible(self, sancion_id, mi_empresa):
        self._san_requiere()
        rec = self._ctr_get(self.SANCIONES_FORM, str(sancion_id or ""))
        if not rec:
            self._san_error("La sanción no existe.", 404)
        fs = self.ctr_f["sanciones"]
        a = rec.get("answers") or {}
        if mi_empresa not in (str(a.get(fs["registra_id"]) or ""), str(a.get(fs["empresa_id"]) or "")):
            self._san_error("No tienes acceso a esta sanción.", 403)
        return rec

    def _san_propia_id(self):
        propia = self.ctr_empresa_propia()
        return str(propia["_id"]) if propia else ""

    def _san_relacion_activa(self, cliente_id, contratista_id):
        fr = self.ctr_f["relaciones_entre_empresas"]
        return self._ctr_find(self.RELACIONES_FORM, {
            f"answers.{fr['cliente_id']}": cliente_id, f"answers.{fr['contratista_id']}": contratista_id,
            f"answers.{fr['estatus']}": opt("Activo")}, one=True) if self.RELACIONES_FORM else None

    def _san_sujeto(self, d, mi_empresa, cache):
        """answers del sancionado (empleado o empresa) y de la relación."""
        fs = self.ctr_f["sanciones"]
        fr = self.ctr_f["relaciones_entre_empresas"]
        tipo = d.get("sujeto_tipo") or ("Empleado" if d.get("empleado_id") else "Empresa")
        if tipo not in SUJETOS:
            self._san_error("Sancionado: Empleado o Empresa.")
        a = {fs["sujeto_tipo"]: opt(tipo)}
        if tipo == "Empleado":
            emp = self.Employee
            e = self._ctr_get(emp.EMPLEADOS, str(d.get("empleado_id") or ""))
            if not e:
                self._san_error("El empleado no existe.", 404)
            ea = e.get("answers") or {}
            empresa_id = str(ea.get(self.ctr_f["empleados"]["empresa_id"]) or "") or self._san_propia_id()
            a.update({fs["empleado_id"]: str(e["_id"]), fs["empleado"]: ea.get(emp.employee_fields["worker_name"]) or ""})
            rel = None
            if empresa_id != mi_empresa:
                rel = self._san_relacion_activa(mi_empresa, empresa_id)
                if not rel:
                    self._san_error("Solo sancionas a tus empleados o a los de un contratista tuyo con relación activa.", 403)
        else:
            rel = self._ctr_get(self.RELACIONES_FORM, str(d.get("relacion_id") or "")) if self.RELACIONES_FORM else None
            if not rel:
                self._san_error("Falta la relación con el contratista.", 404)
            ra = rel.get("answers") or {}
            if str(ra.get(fr["cliente_id"]) or "") != mi_empresa:
                self._san_error("Solo el cliente sanciona a su contratista.", 403)
            if ra.get(fr["estatus"]) == opt("Inactivo"):
                self._san_error("La relación está inactiva.", 409)
            empresa_id = str(ra.get(fr["contratista_id"]) or "")
        a.update({fs["empresa_id"]: empresa_id, fs["empresa"]: self._ctr_empresa_ref(empresa_id, cache).get("razon_social") or ""})
        if rel:
            a.update({fs["relacion_id"]: str(rel["_id"]), fs["relacion"]: (rel.get("answers") or {}).get(fr["folio"]) or ""})
        return a, tipo, rel

    def _san_datos(self, d, a, tipo):
        """Motivo, fecha y suspensión (alta o edición, sobre `a`)."""
        fs = self.ctr_f["sanciones"]
        if "motivo" in d or not a.get(fs["motivo"]):
            if d.get("motivo") not in MOTIVOS:
                self._san_error("Elige el motivo.")
            a[fs["motivo"]] = opt(d["motivo"])
        motivo = label(MOTIVOS, a.get(fs["motivo"]))
        if "motivo_otro" in d:
            a[fs["motivo_otro"]] = (d.get("motivo_otro") or "").strip()
        if motivo == "Otro" and not (a.get(fs["motivo_otro"]) or "").strip():
            self._san_error("Escribe el motivo.")
        if motivo != "Otro":
            a.pop(fs["motivo_otro"], None)
        if "fecha" in d or not a.get(fs["fecha"]):
            f = _fecha(d.get("fecha")) or self._ctr_hoy()
            a[fs["fecha"]] = f.isoformat()
        if "sin_acceso" in d or "dias_sin_acceso" in d or "inicio_suspension" in d:
            sin = bool(d.get("sin_acceso", a.get(fs["sin_acceso"]) == opt("Sí")))
            if sin and tipo != "Empleado":
                self._san_error("Los días sin acceso son solo para empleados.")
            if sin:
                dias = _int(d.get("dias_sin_acceso", a.get(fs["dias_sin_acceso"])), 0)
                if not 1 <= dias <= MAX_DIAS:
                    self._san_error(f"Los días sin acceso van de 1 a {MAX_DIAS} (Ley Federal del Trabajo).")
                ini = _fecha(d.get("inicio_suspension", a.get(fs["inicio_suspension"])))
                if not ini:
                    self._san_error("Falta la fecha de inicio de la suspensión.")
                a.update({fs["sin_acceso"]: opt("Sí"), fs["dias_sin_acceso"]: dias, fs["inicio_suspension"]: ini.isoformat(),
                          fs["fin_suspension"]: (ini + timedelta(days=dias - 1)).isoformat()})
            else:
                a[fs["sin_acceso"]] = opt("No")
                for k in ("dias_sin_acceso", "inicio_suspension", "fin_suspension"):
                    a.pop(fs[k], None)
        a[fs["estatus"]] = opt(self._san_estatus(a))
        return a

    def _san_comentario(self, texto, evidencias):
        fs = self.ctr_f["sanciones"]
        texto = (texto or "").strip()
        if len(texto) > MAX_COMENTARIO:
            self._san_error(f"El comentario pasa de {MAX_COMENTARIO} caracteres.")
        files = [{"file_name": e.get("name") or e["file_url"].rsplit("/", 1)[-1], "file_url": e["file_url"]}
                 for e in evidencias or [] if isinstance(e, dict) and str(e.get("file_url") or "").startswith("http")]
        if not texto and not files:
            return None
        return {fs["comentario_autor"]: self._ctr_autor(), fs["comentario_fecha"]: self._doc_ahora(),
                fs["comentario_texto"]: texto, fs["comentario_evidencias"]: files}

    # ------------------------------------------------------------- API

    def get_opciones_sancion(self):
        return {"motivos": MOTIVOS, "max_dias_sin_acceso": MAX_DIAS, "sujetos": SUJETOS}

    def list_sanciones(self, empleado_id=None, relacion_id=None, sujeto_tipo=None, estatus=None, search=None,
                       limit=25, offset=0):
        if not getattr(self, "SANCIONES_FORM", None):
            return {"items": [], "total": 0}
        mi = self.ctr_empresa_activa_id()
        fs = self.ctr_f["sanciones"]
        match = {"$or": [{f"answers.{fs['registra_id']}": mi}, {f"answers.{fs['empresa_id']}": mi}]}
        for valor, campo in ((empleado_id, "empleado_id"), (relacion_id, "relacion_id")):
            if valor:
                match[f"answers.{fs[campo]}"] = str(valor)
        if sujeto_tipo:
            if sujeto_tipo not in SUJETOS:
                self._san_error("sujeto_tipo: Empleado o Empresa.")
            match[f"answers.{fs['sujeto_tipo']}"] = opt(sujeto_tipo)
        items = [self.san_out(r, mi) for r in self._ctr_find(self.SANCIONES_FORM, match, sort=[("created_at", -1)])]
        if estatus:
            items = [x for x in items if x["estatus"] == estatus]
        txt = (search or "").strip().lower()
        if txt:
            items = [x for x in items if any(txt in str(v or "").lower() for v in (
                x["folio"], x["motivo"], x["motivo_otro"], (x["empleado"] or {}).get("nombre"),
                (x["empresa"] or {}).get("nombre"), x["registro"]))]
        off, lim = max(0, _int(offset)), max(1, min(_int(limit, 25), 200))
        return {"items": items[off:off + lim], "total": len(items)}

    def get_sancion(self, sancion_id):
        mi = self.ctr_empresa_activa_id()
        return self.san_out(self._san_visible(sancion_id, mi), mi)

    def save_sancion(self, sancion, sancion_id=None):
        """Alta (con comentario y evidencias iniciales) o edición de motivo, fecha y suspensión."""
        self._san_requiere()
        d = sancion if isinstance(sancion, dict) else {}
        fs = self.ctr_f["sanciones"]
        mi = self.ctr_empresa_activa_id()
        cache = {}
        if sancion_id:
            rec = self._san_visible(sancion_id, mi)
            a = dict(rec.get("answers") or {})
            if str(a.get(fs["registra_id"]) or "") != mi:
                self._san_error("Solo quien registró la sanción la edita.", 403)
            a = self._san_datos(d, a, label(SUJETOS, a.get(fs["sujeto_tipo"])) or "Empleado")
            self._ctr_patch(self.SANCIONES_FORM, str(rec["_id"]), a, "update_sancion")
            return self.get_sancion(str(rec["_id"]))
        a, tipo, rel = self._san_sujeto(d, mi, cache)
        if d.get("contrato_id"):
            fc = self.ctr_f["contratos_de_servicio"]
            c = self._ctr_get(self.CONTRATOS_FORM, str(d["contrato_id"])) if self.CONTRATOS_FORM else None
            if not c or not rel or str((c.get("answers") or {}).get(fc["relacion_id"]) or "") != str(rel["_id"]):
                self._san_error("El contrato no es de esa relación.", 404)
            a.update({fs["contrato_id"]: str(c["_id"]), fs["contrato"]: (c.get("answers") or {}).get(fc["folio"]) or ""})
        a.update({fs["folio"]: self._act_siguiente_folio(fs["folio"], "S", self.SANCIONES_FORM),
                  fs["registra_id"]: mi, fs["registra"]: self._ctr_empresa_ref(mi, cache).get("razon_social") or "",
                  fs["registro"]: self._ctr_autor()})
        if "sin_acceso" not in d:
            d = {**d, "sin_acceso": False}
        a = self._san_datos(d, a, tipo)
        c = self._san_comentario(d.get("comentario"), d.get("evidencias"))
        a[fs["comentarios"]] = [c] if c else []
        sid = self._ctr_post(self.SANCIONES_FORM, a, "create_sancion")
        if not sid:
            self._san_error("LinkaForm no regresó el id de la sanción.", 500)
        return self.get_sancion(sid)

    def comment_sancion(self, sancion_id, texto="", evidencias=None):
        mi = self.ctr_empresa_activa_id()
        rec = self._san_visible(sancion_id, mi)
        c = self._san_comentario(texto, evidencias)
        if not c:
            self._san_error("Escribe un comentario o agrega una evidencia.")
        fs = self.ctr_f["sanciones"]
        a = dict(rec.get("answers") or {})
        a[fs["comentarios"]] = list(a.get(fs["comentarios"]) or []) + [c]
        self._ctr_patch(self.SANCIONES_FORM, str(rec["_id"]), a, "comment_sancion")
        return self.get_sancion(str(rec["_id"]))

    def delete_sancion(self, sancion_id):
        mi = self.ctr_empresa_activa_id()
        rec = self._san_visible(sancion_id, mi)
        fs = self.ctr_f["sanciones"]
        if str((rec.get("answers") or {}).get(fs["registra_id"]) or "") != mi:
            self._san_error("Solo quien registró la sanción la elimina.", 403)
        self.lkf_api.patch_record_list({"deleted_objects": [f"/api/infosync/form_answer/{rec['_id']}/"]})
        return {"eliminado": str(rec["_id"]), "folio": (rec.get("answers") or {}).get(fs["folio"]) or ""}

    def imprimir_acta(self, sancion_id):
        """Genera el acta (PDF simple provisional), la guarda en la sanción y la regresa."""
        mi = self.ctr_empresa_activa_id()
        rec = self._san_visible(sancion_id, mi)
        fs = self.ctr_f["sanciones"]
        a = dict(rec.get("answers") or {})
        if str(a.get(fs["registra_id"]) or "") != mi:
            self._san_error("Solo quien registró la sanción imprime el acta.", 403)
        s = self.san_out(rec)
        archivo = self._san_pdf(s)
        a[fs["acta"]] = [{"file_name": archivo["name"], "file_url": archivo["file_url"]}]
        self._ctr_patch(self.SANCIONES_FORM, str(rec["_id"]), a, "imprimir_acta")
        return {"acta": archivo, "sancion": self.get_sancion(str(rec["_id"]))}

    def suspension_empleado(self, empleado_id):
        """Fin de la suspensión vigente más lejana del empleado (o None)."""
        if not getattr(self, "SANCIONES_FORM", None):
            return None
        fs = self.ctr_f["sanciones"]
        hoy = self._ctr_hoy().isoformat()
        fines = [str((r.get("answers") or {}).get(fs["fin_suspension"]) or "")[:10]
                 for r in self._ctr_find(self.SANCIONES_FORM, {f"answers.{fs['empleado_id']}": str(empleado_id),
                                                               f"answers.{fs['sin_acceso']}": opt("Sí")})]
        fines = [f for f in fines if f and f >= hoy]
        return max(fines) if fines else None

    # ---------------------------------------------------------------- acta

    def _san_pdf(self, s):
        from PIL import Image, ImageDraw
        im = Image.new("RGB", (1240, 1754), "white")
        d = ImageDraw.Draw(im)
        titulo, texto = fuente(44, negrita=True), fuente(26)
        sujeto = (s["empleado"] or s["empresa"] or {}).get("nombre") or ""
        motivo = s["motivo_otro"] if s["motivo"] == "Otro" and s["motivo_otro"] else s["motivo"]
        lineas = ["", f"Folio: {s['folio']}", f"Fecha: {s['fecha'] or ''}",
                  f"Sancionado: {sujeto}" + (f" ({s['empresa']['nombre']})" if s["empleado"] and s["empresa"] else ""),
                  f"Registra: {(s['registra'] or {}).get('nombre') or ''} · {s['registro']}",
                  f"Motivo: {motivo}"]
        if s["sin_acceso"]:
            lineas.append(f"Suspensión: {s['dias_sin_acceso']} día(s), del {s['inicio_suspension']} al {s['fin_suspension']}")
        else:
            lineas.append("Amonestación (sin días de suspensión)")
        lineas += ["", "Comentarios:"] + [f"- {c['fecha']} {c['autor']}: {c['texto'][:90]}" for c in s["comentarios"][:12]]
        lineas += ["", "", "_______________________          _______________________",
                   "Firma de quien registra               Firma del sancionado"]
        y = 140
        d.text((120, y), "Acta de sanción", fill="black", font=titulo)
        for linea in lineas:
            y += 56
            d.text((120, y), linea, fill="black", font=texto)
        nombre = re.sub(r"[^A-Za-z0-9_-]+", "_", f"acta_{s['folio']}")[:60] + ".pdf"
        ruta = os.path.join(tempfile.gettempdir(), nombre)
        buf = io.BytesIO()
        im.save(buf, "PDF")
        with open(ruta, "wb") as fh:
            fh.write(buf.getvalue())
        try:
            with open(ruta, "rb") as fh:
                res = self.lkf_api.post_upload_file(
                    data={"form_id": self.SANCIONES_FORM, "field_id": self.ctr_f["sanciones"]["acta"]},
                    up_file={"File": fh})
            url = ((res or {}).get("data") or {}).get("file")
        finally:
            os.remove(ruta)
        if not url:
            self._san_error(f"No se pudo subir el acta: {str(res)[:200]}", 502)
        return {"name": nombre, "file_url": url}
