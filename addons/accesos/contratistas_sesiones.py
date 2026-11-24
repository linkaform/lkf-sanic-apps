# -*- coding: utf-8 -*-
"""Sesiones de capacitación de Contratistas (CF-03-B).

Spec: clave10-sdk/specs/contratos/contratos-001-modelo-de-datos.md (forma
Sesiones de capacitación). Ficha: lkf-claude contratistas_cf03_sesiones.md.
Contrato con el front: Sesion / SesionInput en clave10/src/types/contratistas/contratos.ts.

Decisiones de Paco (2026-11-24), distintas de la spec original:
- Tipos del diseño: Curso, Capacitación, Plática, Inducción.
- Varios exámenes (requerimientos tipo Examen, ámbito Persona) y varios
  requerimientos que otorga (tipo Documento, ámbito Persona).
- Grupo `recursos` (materiales de apoyo) aparte del temario.
- Eliminar = Cancelar: no hay borrado.

- Configuración de la cuenta: no se filtra por empresa activa (como CF-01/02).
- Estatus calculado al leer y guardado al escribir: Cancelada; si no,
  Programada antes de fecha_inicio, Finalizada después del fin (o de
  repetir_hasta) y En curso entre ambas.
- Modalidad se deduce: lugar = Presencial, enlace = Virtual, ambos = Híbrida.
- Participantes, asistencia y resultados son de CF-04-B: aquí se conservan.

Participantes (CF-04-B):
- Inscribir en Programada o En curso, respetando cupo; quitar solo en Programada.
- Asistencia por fecha (Asistió | Faltó) en días de la sesión ya transcurridos.
  Días: cada fecha de inicio a fin; con recurrencia Semanal los días de la
  semana marcados hasta repetir_hasta; Por día, todos; otras recurrencias,
  inicio + fechas ya registradas.
- Calificación por examen (0–100) en participante_calificaciones (JSON);
  `calificacion` guarda la menor. Requiere haber asistido.
- Resultado: con exámenes, Aprobado si todas las calificaciones >= la mínima
  de cada examen (80 por defecto); sin exámenes, Aprobado con asistencia
  completa. Al quedar Aprobado se crea, una sola vez, un Documento por cada
  requerimiento otorgado (origen Sesión, ya Aceptado, con una constancia PDF
  simple como archivo). Si después cambia a No aprobado, no se revoca.
"""
import re
from datetime import timedelta

from .contratistas_contratos import _fecha, _int, label, opt

TIPOS = ["Curso", "Capacitación", "Plática", "Inducción"]
ESTATUS = ["Programada", "En curso", "Finalizada", "Cancelada"]
ORDEN_ESTATUS = ["En curso", "Programada", "Finalizada", "Cancelada"]
MATERIALES = ["Video", "Lectura", "Presentación", "Cuestionario", "Clase en vivo"]
ORIGENES = ["Archivo", "Enlace"]
CALIFICACION_MINIMA = 80
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
HORA_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
REQ_TIPOS = ["Documento", "Examen", "Inspección"]
REQ_AMBITOS = ["Empresa", "Persona", "Equipo"]


def _modalidad(lugar, enlace):
    if lugar and enlace:
        return "Híbrida"
    return "Virtual" if enlace else "Presencial"


class SesionesMixin:
    """Se mezcla en Accesos (usa helpers _ctr_*)."""

    def _ses_error(self, msg, status=400):
        return self.LKFException({"title": "Sesiones", "msg": msg, "status_code": status})

    def _ses_requiere_forma(self):
        if not self.SESIONES_FORM:
            self._ses_error("La forma Sesiones de capacitación no está instalada en esta cuenta.", 409)

    def _ses_estatus(self, a):
        f = self.ctr_f["sesiones_de_capacitacion"]
        if a.get(f["cancelada"]) == opt("Sí"):
            return "Cancelada"
        hoy = self._ctr_hoy()
        ini = _fecha(a.get(f["fecha_inicio"]))
        fin = _fecha(a.get(f["recurrencia_repetir_hasta"])) if a.get(f["recurrencia_tipo"]) else None
        fin = fin or _fecha(a.get(f["fecha_fin"])) or ini
        if ini and hoy < ini:
            return "Programada"
        if fin and hoy > fin:
            return "Finalizada"
        return "En curso"

    @staticmethod
    def _ses_material_out(origen, archivo, enlace, ctr_archivo):
        if origen == "Enlace":
            return enlace or None
        return ctr_archivo(archivo)

    def ses_out(self, rec):
        f = self.ctr_f["sesiones_de_capacitacion"]
        a = rec.get("answers") or {}

        def reflist(g, k_id, k_n):
            return [{"id": str(x.get(f[k_id]) or ""), "nombre": x.get(f[k_n]) or ""} for x in a.get(f[g]) or []]

        lugar, enlace = a.get(f["lugar"]) or None, a.get(f["enlace"]) or None
        rec_out = self._ctr_recurrencia_out(a, "sesiones_de_capacitacion")
        if rec_out and a.get(f["recurrencia_repetir_hasta"]):
            rec_out["repetir_hasta"] = str(a[f["recurrencia_repetir_hasta"]])[:10]
        participantes = a.get(f["participantes"]) or []
        cupo = _int(a.get(f["cupo"]), 0) or None
        out = {
            "id": str(rec["_id"]), "nombre": a.get(f["nombre"]) or "", "descripcion": a.get(f["descripcion"]) or None,
            "tipo": label(TIPOS, a.get(f["tipo"])) or "Curso", "instructor": a.get(f["instructor"]) or None,
            "fecha_inicio": str(a.get(f["fecha_inicio"]) or "")[:10], "fecha_fin": str(a.get(f["fecha_fin"]) or "")[:10],
            "hora_inicio": str(a.get(f["hora_inicio"]) or "")[:5] or None,
            "hora_fin": str(a.get(f["hora_fin"]) or "")[:5] or None,
            "recurrencia": rec_out, "lugar": lugar, "enlace": enlace, "modalidad": _modalidad(lugar, enlace),
            "areas": reflist("areas", "areas_id", "areas_nombre"),
            "cupo": cupo,
            "examenes": reflist("examenes", "examenes_id", "examenes_nombre"),
            "otorgados": reflist("otorgados", "otorgados_id", "otorgados_nombre"),
            "temario": [{
                "tema": g.get(f["tema"]) or "", "leccion": g.get(f["leccion"]) or "",
                "minutos": _int(g.get(f["minutos"]), 0) or None,
                "material_tipo": label(MATERIALES, g.get(f["material_tipo"])) or "Lectura",
                "material_origen": label(ORIGENES, g.get(f["material_origen"])) or "Archivo",
                "material": self._ses_material_out(label(ORIGENES, g.get(f["material_origen"])),
                                                   g.get(f["material_archivo"]), g.get(f["material_enlace"]),
                                                   self._ctr_archivo),
            } for g in a.get(f["temario"]) or []],
            "recursos": [{
                "nombre": g.get(f["recurso_nombre"]) or "",
                "material_tipo": label(MATERIALES, g.get(f["recurso_tipo"])) or "Lectura",
                "material_origen": label(ORIGENES, g.get(f["recurso_origen"])) or "Archivo",
                "material": self._ses_material_out(label(ORIGENES, g.get(f["recurso_origen"])),
                                                   g.get(f["recurso_archivo"]), g.get(f["recurso_enlace"]),
                                                   self._ctr_archivo),
            } for g in a.get(f["recursos"]) or []],
            "participantes": [{
                "empleado": {"id": str(p.get(f["participante_id"]) or ""), "nombre": p.get(f["participante"]) or ""},
                "asistencia": self._ses_json(p.get(f["participante_asistencia"])),
                **({"calificacion": p[f["participante_calificacion"]]}
                   if p.get(f["participante_calificacion"]) not in (None, "") else {}),
                **({"resultado": label(["Aprobado", "No aprobado"], p[f["participante_resultado"]])}
                   if p.get(f["participante_resultado"]) else {}),
                **({"calificaciones": self._ses_json(p.get(f["participante_calificaciones"]))}
                   if p.get(f["participante_calificaciones"]) else {}),
            } for p in participantes],
            "inscritos": len(participantes),
            "motivo_cancelacion": a.get(f["motivo_cancelacion"]) or None,
            "estatus": self._ses_estatus(a),
        }
        for g in ("temario", "recursos"):
            out[g] = [{k: v for k, v in x.items() if v is not None} for x in out[g]]
        return {k: v for k, v in out.items() if v is not None or k == "cupo"}

    @staticmethod
    def _ses_json(v):
        import simplejson
        try:
            d = simplejson.loads(v) if v else {}
        except (ValueError, TypeError):
            d = {}
        return d if isinstance(d, dict) else {}

    # ---------------------------------------------------------------- API

    def list_sesiones(self, tipo=None, modalidad=None, estatus=None, desde=None, hasta=None, search=None,
                      limit=25, offset=0):
        """Orden: en curso, programadas, resto. `conteo` = chips de filtros."""
        if not self.SESIONES_FORM:
            return {"items": [], "total": 0, "conteo": {}}
        f = self.ctr_f["sesiones_de_capacitacion"]
        match = {}
        if search and search.strip():
            rx = {"$regex": re.escape(search.strip()), "$options": "i"}
            match["$or"] = [{f"answers.{f[k]}": rx} for k in ("nombre", "descripcion", "instructor")]
        items = [self.ses_out(r) for r in self._ctr_find(self.SESIONES_FORM, match,
                                                         sort=[(f"answers.{f['fecha_inicio']}", 1)])]
        if desde:
            items = [s for s in items if (s.get("recurrencia", {}).get("repetir_hasta") or s["fecha_fin"]) >= desde]
        if hasta:
            items = [s for s in items if s["fecha_inicio"] <= hasta]
        conteo = {k: {} for k in ("tipo", "modalidad", "estatus")}
        for s in items:
            for k, c in conteo.items():
                c[s[k]] = c.get(s[k], 0) + 1
        for k, v in (("tipo", tipo), ("modalidad", modalidad), ("estatus", estatus)):
            if v:
                vs = v if isinstance(v, list) else [v]
                items = [s for s in items if s[k] in vs]
        items.sort(key=lambda s: ORDEN_ESTATUS.index(s["estatus"]))
        ini = max(0, _int(offset))
        return {"items": items[ini:ini + max(1, min(_int(limit, 25), 500))], "total": len(items), "conteo": conteo}

    def get_sesion(self, sesion_id):
        self._ses_requiere_forma()
        rec = self._ctr_get(self.SESIONES_FORM, sesion_id)
        if not rec:
            self._ses_error("La sesión no existe.", 404)
        return self.ses_out(rec)

    def _ses_reqs(self, refs, tipo, etiqueta, errores):
        """Valida que sean requerimientos activos del tipo pedido y ámbito Persona."""
        fq = self.ctr_f["requerimientos_de_cumplimiento"]
        out = []
        for r in refs or []:
            rid = str(r.get("id") if isinstance(r, dict) else r)
            rec = self._ctr_get(self.REQUERIMIENTOS_FORM, rid) if self.REQUERIMIENTOS_FORM else None
            a = (rec or {}).get("answers") or {}
            nombre = a.get(fq["nombre"]) or rid
            if not rec:
                errores.append(f"{etiqueta}: el requerimiento {rid} no existe.")
            elif a.get(fq["estatus"]) == opt("Inactivo"):
                errores.append(f"{etiqueta}: {nombre} está inactivo.")
            elif label(REQ_TIPOS, a.get(fq["tipo"])) != tipo:
                errores.append(f"{etiqueta}: {nombre} no es de tipo {tipo}.")
            elif (label(REQ_AMBITOS, a.get(fq["ambito"])) or "Empresa") != "Persona":
                errores.append(f"{etiqueta}: {nombre} no es de ámbito Persona.")
            elif rid not in [x["id"] for x in out]:
                out.append({"id": rid, "nombre": nombre})
        return out

    def _ses_material_in(self, m, prefijo, errores, donde):
        """(answers del renglón para tipo/origen/archivo/enlace) de un material."""
        f = self.ctr_f["sesiones_de_capacitacion"]
        k = {"material": ("material_tipo", "material_origen", "material_archivo", "material_enlace"),
             "recurso": ("recurso_tipo", "recurso_origen", "recurso_archivo", "recurso_enlace")}[prefijo]
        tipo = m.get("material_tipo") or "Lectura"
        origen = m.get("material_origen") or ("Enlace" if isinstance(m.get("material"), str) else "Archivo")
        if tipo not in MATERIALES:
            errores.append(f"{donde}: tipo de material no válido ({tipo}).")
        if origen not in ORIGENES:
            errores.append(f"{donde}: origen no válido ({origen}).")
        out = {f[k[0]]: opt(tipo), f[k[1]]: opt(origen)}
        mat = m.get("material")
        if origen == "Enlace" and mat:
            if not str(mat).startswith("http"):
                errores.append(f"{donde}: el enlace debe empezar con http.")
            out[f[k[3]]] = str(mat).strip()
        elif origen == "Archivo" and isinstance(mat, dict) and mat.get("file_url"):
            out[f[k[2]]] = [{"file_name": mat.get("name") or mat["file_url"].rsplit("/", 1)[-1],
                             "file_url": mat["file_url"]}]
        return out

    def save_sesion(self, sesion, sesion_id=None):
        """Alta (sin id) o edición completa (con id). Conserva participantes."""
        self._ses_requiere_forma()
        s = sesion if isinstance(sesion, dict) else {}
        f = self.ctr_f["sesiones_de_capacitacion"]
        actual = None
        if sesion_id:
            actual = self._ctr_get(self.SESIONES_FORM, sesion_id)
            if not actual:
                self._ses_error("La sesión no existe.", 404)
            if self._ses_estatus(actual.get("answers") or {}) == "Cancelada":
                self._ses_error("Una sesión cancelada no se edita.", 409)
        errores = []
        nombre = " ".join(str(s.get("nombre") or "").split())
        if not nombre:
            errores.append("El nombre es obligatorio.")
        tipo = s.get("tipo")
        if tipo not in TIPOS:
            errores.append(f"El tipo debe ser {', '.join(TIPOS)}.")
        ini, fin = _fecha(s.get("fecha_inicio")), _fecha(s.get("fecha_fin") or s.get("fecha_inicio"))
        if not ini:
            errores.append("La fecha de inicio es obligatoria (YYYY-MM-DD).")
        elif not fin or fin < ini:
            errores.append("La fecha de fin no puede ser anterior a la de inicio.")
        hi, hf = s.get("hora_inicio") or None, s.get("hora_fin") or None
        for h, n in ((hi, "inicio"), (hf, "fin")):
            if h and not HORA_RE.match(str(h)):
                errores.append(f"La hora de {n} debe ser HH:MM.")
        if hi and hf and ini and fin and ini == fin and str(hf) <= str(hi):
            errores.append("La hora de fin debe ser después de la de inicio.")
        lugar, enlace = str(s.get("lugar") or "").strip(), str(s.get("enlace") or "").strip()
        if not lugar and not enlace:
            errores.append("Indica el lugar, el enlace de la reunión o ambos.")
        if enlace and not enlace.startswith("http"):
            errores.append("El enlace debe empezar con http.")
        cupo = s.get("cupo")
        if cupo not in (None, ""):
            if _int(cupo, 0) < 1:
                errores.append("El cupo debe ser al menos 1 (vacío = sin límite).")
            elif actual and _int(cupo) < len((actual.get("answers") or {}).get(f["participantes"]) or []):
                errores.append("El cupo no puede ser menor que los inscritos.")
        examenes = self._ses_reqs(s.get("examenes"), "Examen", "Exámenes", errores)
        otorgados = self._ses_reqs(s.get("otorgados"), "Documento", "Requerimientos que otorga", errores)
        temario = []
        for i, t in enumerate(s.get("temario") or [], start=1):
            t = t if isinstance(t, dict) else {}
            tema, leccion = str(t.get("tema") or "").strip(), str(t.get("leccion") or "").strip()
            if not tema or not leccion:
                errores.append(f"Temario renglón {i}: tema y lección son obligatorios.")
            row = {f["tema"]: tema, f["leccion"]: leccion,
                   **self._ses_material_in(t, "material", errores, f"Temario renglón {i}")}
            if t.get("minutos") not in (None, ""):
                row[f["minutos"]] = _int(t["minutos"], 0)
            temario.append(row)
        if tipo == "Curso" and not temario:
            errores.append("Un curso necesita al menos una sección con una lección.")
        recursos = []
        for i, r in enumerate(s.get("recursos") or [], start=1):
            r = r if isinstance(r, dict) else {}
            if not str(r.get("nombre") or "").strip():
                errores.append(f"Recurso {i}: el nombre es obligatorio.")
            recursos.append({f["recurso_nombre"]: str(r.get("nombre") or "").strip(),
                             **self._ses_material_in(r, "recurso", errores, f"Recurso {i}")})
        rec_in = {}
        if s.get("recurrencia"):
            try:
                rec_in = self._ctr_recurrencia_in(s["recurrencia"], "sesiones_de_capacitacion")
            except Exception as e:  # noqa: BLE001 — el error de contratos lleva otro título
                errores.append(str(e)[:200])
            hasta = s["recurrencia"].get("repetir_hasta")
            if hasta and (not _fecha(hasta) or (ini and _fecha(hasta) < ini)):
                errores.append("Repetir hasta debe ser una fecha posterior al inicio.")
            elif hasta:
                rec_in[f["recurrencia_repetir_hasta"]] = _fecha(hasta).isoformat()
        if errores:
            self._ses_error("\n".join(errores))
        a = {
            f["nombre"]: nombre, f["tipo"]: opt(tipo), f["fecha_inicio"]: ini.isoformat(), f["fecha_fin"]: fin.isoformat(),
            f["examenes"]: [{f["examenes_id"]: x["id"], f["examenes_nombre"]: x["nombre"]} for x in examenes],
            f["otorgados"]: [{f["otorgados_id"]: x["id"], f["otorgados_nombre"]: x["nombre"]} for x in otorgados],
            f["temario"]: temario, f["recursos"]: recursos,
            f["areas"]: [{f["areas_id"]: str(x.get("id") or ""), f["areas_nombre"]: str(x.get("nombre") or "")}
                         for x in s.get("areas") or [] if isinstance(x, dict) and x.get("id")],
            **rec_in,
        }
        for k, v in (("descripcion", s.get("descripcion")), ("instructor", s.get("instructor")),
                     ("lugar", lugar), ("enlace", enlace)):
            if str(v or "").strip():
                a[f[k]] = str(v).strip()
        if hi:
            a[f["hora_inicio"]] = f"{hi}:00"
        if hf:
            a[f["hora_fin"]] = f"{hf}:00"
        if cupo not in (None, ""):
            a[f["cupo"]] = _int(cupo)
        if actual:  # lo de CF-04 se conserva
            prev = actual.get("answers") or {}
            for k in ("participantes", "cancelada", "motivo_cancelacion"):
                if prev.get(f[k]):
                    a[f[k]] = prev[f[k]]
        a[f["estatus"]] = opt(self._ses_estatus(a))
        a = {k: v for k, v in a.items() if v not in (None, "")}
        if actual:
            self._ctr_patch(self.SESIONES_FORM, str(sesion_id), a, "save_sesion")
        else:
            sesion_id = self._ctr_post(self.SESIONES_FORM, a, "save_sesion")
            if not sesion_id:
                self._ses_error("LinkaForm no regresó el id.", 500)
        return self.get_sesion(str(sesion_id))

    def cancel_sesion(self, sesion_id, motivo=""):
        """Solo Programada. "Eliminar" en la UI también usa esta ruta."""
        self._ses_requiere_forma()
        rec = self._ctr_get(self.SESIONES_FORM, sesion_id)
        if not rec:
            self._ses_error("La sesión no existe.", 404)
        f = self.ctr_f["sesiones_de_capacitacion"]
        a = dict(rec.get("answers") or {})
        estatus = self._ses_estatus(a)
        if estatus != "Programada":
            self._ses_error(f"Solo se cancela una sesión Programada (esta está {estatus}).", 409)
        motivo = " ".join(str(motivo or "").split())
        if not motivo:
            self._ses_error("El motivo de cancelación es obligatorio.")
        a.update({f["cancelada"]: opt("Sí"), f["motivo_cancelacion"]: motivo, f["estatus"]: opt("Cancelada")})
        self._ctr_patch(self.SESIONES_FORM, str(sesion_id), a, "cancel_sesion")
        return self.get_sesion(str(sesion_id))

    # ------------------------------------------------- participantes (CF-04-B)

    def _ses_get(self, sesion_id):
        self._ses_requiere_forma()
        rec = self._ctr_get(self.SESIONES_FORM, sesion_id)
        if not rec:
            self._ses_error("La sesión no existe.", 404)
        return rec

    def _ses_dias(self, a):
        """Fechas (date) de la sesión, sin pasar de hoy."""
        f = self.ctr_f["sesiones_de_capacitacion"]
        ini = _fecha(a.get(f["fecha_inicio"]))
        if not ini:
            return []
        tipo = label(["Por día", "Semanal", "Mensual", "Configurable"], a.get(f["recurrencia_tipo"]))
        fin = (_fecha(a.get(f["recurrencia_repetir_hasta"])) if tipo else None) or _fecha(a.get(f["fecha_fin"])) or ini
        hoy = self._ctr_hoy()
        fin = min(fin, hoy)
        if fin < ini:
            return []
        todos = [ini + timedelta(days=i) for i in range((fin - ini).days + 1)]
        if tipo == "Semanal":
            dias = {DIAS_SEMANA.index(x) for x in (label(DIAS_SEMANA, v) for v in a.get(f["recurrencia_dias_semana"]) or []) if x}
            return [d for d in todos if d.weekday() in dias] if dias else todos
        if tipo in (None, "Por día"):
            return todos
        registrados = set()
        for p in a.get(f["participantes"]) or []:
            registrados |= {_fecha(k) for k in self._ses_json(p.get(f["participante_asistencia"]))}
        return sorted({ini} | {d for d in registrados if d and ini <= d <= fin})

    def _ses_minimas(self, a):
        """{examen_id: calificación mínima} de los exámenes de la sesión."""
        f, fq = self.ctr_f["sesiones_de_capacitacion"], self.ctr_f["requerimientos_de_cumplimiento"]
        out = {}
        for g in a.get(f["examenes"]) or []:
            eid = str(g.get(f["examenes_id"]) or "")
            q = (self._ctr_get(self.REQUERIMIENTOS_FORM, eid) or {}).get("answers") or {}
            out[eid] = _int(q.get(fq["examen_calificacion_minima"]), 0) or CALIFICACION_MINIMA
        return out

    def _ses_resultado(self, p, dias, minimas):
        f = self.ctr_f["sesiones_de_capacitacion"]
        asis = self._ses_json(p.get(f["participante_asistencia"]))
        if minimas:
            cal = self._ses_json(p.get(f["participante_calificaciones"]))
            if not all(k in cal for k in minimas):
                return None
            return "Aprobado" if all(float(cal[k]) >= m for k, m in minimas.items()) else "No aprobado"
        if not dias or any(asis.get(d.isoformat()) not in ("Asistió", "Faltó") for d in dias):
            return None  # falta registrar días
        return "Aprobado" if all(asis.get(d.isoformat()) == "Asistió" for d in dias) else "No aprobado"

    def _ses_constancia(self, sesion, empleado, requerimiento, fecha):
        """PDF simple de constancia (el formato oficial no está en el diseño),
        subido al campo archivo de Documentos. Regresa el valor del campo."""
        import io
        import os
        import tempfile

        from PIL import Image, ImageDraw, ImageFont
        im = Image.new("RGB", (1240, 1754), "white")
        d = ImageDraw.Draw(im)
        titulo, texto = ImageFont.load_default(size=44), ImageFont.load_default(size=30)
        y = 160
        d.text((120, y), "Constancia de capacitación", fill="black", font=titulo)
        for linea in ("", f"Se hace constar que {empleado}", f"acreditó la sesión «{sesion}»",
                      f"y cumple el requerimiento «{requerimiento}».", "", f"Fecha: {fecha}", "",
                      "Emitida por Clave 10 al aprobar la sesión."):
            y += 70
            d.text((120, y), linea, fill="black", font=texto)
        nombre = re.sub(r"[^A-Za-z0-9_-]+", "_", f"constancia_{empleado}")[:80] + ".pdf"
        ruta = os.path.join(tempfile.gettempdir(), nombre)
        buf = io.BytesIO()
        im.save(buf, "PDF")
        with open(ruta, "wb") as fh:
            fh.write(buf.getvalue())
        try:
            with open(ruta, "rb") as fh:
                res = self.lkf_api.post_upload_file(
                    data={"form_id": self.DOCUMENTOS_FORM,
                          "field_id": self.ctr_f["documentos_de_cumplimiento"]["archivo"]},
                    up_file={"File": fh})
            url = ((res or {}).get("data") or {}).get("file")
        finally:
            os.remove(ruta)
        if not url:
            self._ses_error(f"No se pudo subir la constancia: {str(res)[:200]}", 502)
        return [{"file_name": nombre, "file_url": url}]

    def _ses_otorgar(self, a, p):
        """Documento ya Aceptado por cada requerimiento otorgado (una sola vez)."""
        if not self.DOCUMENTOS_FORM:
            return []
        f, fd = self.ctr_f["sesiones_de_capacitacion"], self.ctr_f["documentos_de_cumplimiento"]
        emp = self.Employee
        eid = str(p.get(f["participante_id"]) or "")
        e = self._ctr_get(emp.EMPLEADOS, eid)
        if not e:
            return []
        ea = e.get("answers") or {}
        propia = self.ctr_empresa_propia()
        empresa_id = str(ea.get(self.ctr_f["empleados"]["empresa_id"]) or "") or (str(propia["_id"]) if propia else "")
        empresa = self._ctr_empresa_ref(empresa_id, {}) or {"razon_social": ""}
        clientes = self._doc_clientes(empresa_id) or ({empresa_id: empresa["razon_social"]} if empresa_id else {})
        nombre_emp = ea.get(emp.employee_fields["worker_name"]) or p.get(f["participante"]) or ""
        creados = []
        for g in a.get(f["otorgados"]) or []:
            rid = str(g.get(f["otorgados_id"]) or "")
            ya = self._ctr_find(self.DOCUMENTOS_FORM, {f"answers.{fd['requerimiento_id']}": rid,
                                                       f"answers.{fd['dueno_empleado_id']}": eid,
                                                       f"answers.{fd['origen']}": opt("Sesión")}, one=True)
            if ya:
                continue
            ahora = self._doc_ahora()
            archivo = self._ses_constancia(a.get(f["nombre"]) or "", nombre_emp, g.get(f["otorgados_nombre"]) or "",
                                           self._ctr_hoy().isoformat())
            doc = {
                fd["folio"]: self._doc_siguiente_folio(),
                fd["nombre"]: f"{a.get(f['nombre']) or 'Sesión'} · {nombre_emp}",
                fd["requerimiento_id"]: rid, fd["requerimiento"]: g.get(f["otorgados_nombre"]) or "",
                fd["dueno_tipo"]: opt("Persona"), fd["dueno_empresa_id"]: empresa_id,
                fd["dueno_empresa"]: empresa["razon_social"], fd["dueno_empleado_id"]: eid, fd["dueno_empleado"]: nombre_emp,
                fd["origen"]: opt("Sesión"), fd["en_ceros"]: opt("No"), fd["estatus"]: opt("Aceptado"),
                fd["vigencia_inicio"]: self._ctr_hoy().isoformat(),
                fd["compartido_con"]: [{fd["compartido_con_id"]: i, fd["compartido_con_nombre"]: n} for i, n in clientes.items()],
                fd["aprobaciones"]: [{fd["aprobacion_cliente_id"]: i, fd["aprobacion_cliente"]: n,
                                      fd["aprobacion_decision"]: opt("Aprobado"), fd["aprobacion_revisor"]: "Sesión",
                                      fd["aprobacion_fecha"]: ahora} for i, n in clientes.items()],
                fd["archivo"]: archivo,
                fd["versiones"]: [{fd["version_numero"]: 1, fd["version_archivo"]: archivo,
                                   fd["version_estatus"]: opt("Aceptado"), fd["version_subido_por"]: "Sesión",
                                   fd["version_fecha"]: ahora}],
                fd["comentarios"]: [{fd["comentario_autor"]: self._ctr_autor(), fd["comentario_fecha"]: ahora,
                                                          fd["comentario_texto"]: f"Otorgado al aprobar la sesión {a.get(f['nombre']) or ''}."}],
                fd["contratos"]: [],
            }
            doc_id = self._ctr_post(self.DOCUMENTOS_FORM, doc, "otorgar_por_sesion")
            if doc_id:
                creados.append({"id": doc_id, "requerimiento": g.get(f["otorgados_nombre"]) or "", "empleado": nombre_emp})
        if creados:
            self._doc_recalcular(empresa_id, set(clientes))
        return creados

    def _ses_guardar_participantes(self, rec, participantes, accion):
        """Recalcula resultados, guarda y otorga a los nuevos Aprobados."""
        f = self.ctr_f["sesiones_de_capacitacion"]
        a = dict(rec.get("answers") or {})
        a[f["participantes"]] = participantes
        dias, minimas = self._ses_dias(a), self._ses_minimas(a)
        aprobados = []
        for p in participantes:
            res = self._ses_resultado(p, dias, minimas)
            if res:
                p[f["participante_resultado"]] = opt(res)
            else:
                p.pop(f["participante_resultado"], None)
            if res == "Aprobado":  # _ses_otorgar no duplica: reintenta si antes falló
                aprobados.append(p)
        a[f["estatus"]] = opt(self._ses_estatus(a))
        self._ctr_patch(self.SESIONES_FORM, str(rec["_id"]), a, accion)
        otorgados = [d for p in aprobados for d in self._ses_otorgar(a, p)]
        out = self.get_participantes(str(rec["_id"]))
        if otorgados:
            out["documentos_otorgados"] = otorgados
        return out

    def get_participantes(self, sesion_id):
        """Pestaña Participantes: KPIs, días de la sesión y por empleado puesto,
        centro, asistencia (N de M días, %) y exámenes."""
        rec = self._ses_get(sesion_id)
        s = self.ses_out(rec)
        a = rec.get("answers") or {}
        dias = [d.isoformat() for d in self._ses_dias(a)]
        minimas = self._ses_minimas(a)
        emp = self.Employee
        fe = self.ctr_f["empleados"]
        filas = []
        for p in s["participantes"]:
            e = (self._ctr_get(emp.EMPLEADOS, p["empleado"]["id"]) or {}).get("answers") or {}
            asistio = sum(1 for d in dias if p["asistencia"].get(d) == "Asistió")
            filas.append({**p, "puesto": self._emp_cat(e, emp.employee_fields["worker_position"]) if e else None,
                          "centro_trabajo": e.get(fe["centro_trabajo"]) or None,
                          "asistencia_resumen": {"asistio": asistio, "dias": len(dias),
                                                 "pct": round(asistio * 100 / len(dias)) if dias else None}})
        asistieron = sum(1 for x in filas if x["asistencia_resumen"]["asistio"])
        return {"sesion": {k: s[k] for k in ("id", "nombre", "estatus", "cupo", "inscritos", "examenes", "otorgados")},
                "dias": dias, "examenes_minimas": minimas,
                "kpi": {"inscritos": len(filas), "cupo": s["cupo"], "asistieron": asistieron,
                        "asistencia_pct": round(sum(x["asistencia_resumen"]["asistio"] for x in filas) * 100
                                                / (len(filas) * len(dias))) if filas and dias else None},
                "participantes": filas}

    def inscribir_participantes(self, sesion_id, empleado_ids):
        rec = self._ses_get(sesion_id)
        f = self.ctr_f["sesiones_de_capacitacion"]
        a = rec.get("answers") or {}
        estatus = self._ses_estatus(a)
        if estatus not in ("Programada", "En curso"):
            self._ses_error(f"Solo se inscribe en una sesión Programada o En curso (esta está {estatus}).", 409)
        actuales = list(a.get(f["participantes"]) or [])
        ya = {str(p.get(f["participante_id"])) for p in actuales}
        nuevos = [str(i) for i in dict.fromkeys(empleado_ids or []) if str(i) not in ya]
        if not nuevos:
            self._ses_error("Elige al menos un empleado que no esté inscrito.")
        cupo = _int(a.get(f["cupo"]), 0)
        if cupo and len(actuales) + len(nuevos) > cupo:
            self._ses_error(f"Se alcanzó el cupo de la sesión: quedan {max(cupo - len(actuales), 0)} lugares.", 409)
        emp = self.Employee
        errores = []
        for i in nuevos:
            e = self._ctr_get(emp.EMPLEADOS, i)
            ea = (e or {}).get("answers") or {}
            nombre = ea.get(emp.employee_fields["worker_name"]) or i
            if not e:
                errores.append(f"El empleado {i} no existe.")
            elif ea.get(emp.employee_fields["estatus_dentro_empresa"]) == "inactivo":
                errores.append(f"{nombre} está desactivado.")
            elif ea.get(self.ctr_f["empleados"]["vetado_fecha"]):
                errores.append(f"{nombre} está vetado.")
            else:
                actuales.append({f["participante_id"]: i, f["participante"]: nombre,
                                 f["participante_asistencia"]: "{}"})
        if errores:
            self._ses_error("\n".join(errores))
        return self._ses_guardar_participantes(rec, actuales, "inscribir_participantes")

    def quitar_participante(self, sesion_id, empleado_id):
        rec = self._ses_get(sesion_id)
        f = self.ctr_f["sesiones_de_capacitacion"]
        a = rec.get("answers") or {}
        if self._ses_estatus(a) != "Programada":
            self._ses_error("Solo se quita a un participante de una sesión Programada.", 409)
        actuales = list(a.get(f["participantes"]) or [])
        quedan = [p for p in actuales if str(p.get(f["participante_id"])) != str(empleado_id)]
        if len(quedan) == len(actuales):
            self._ses_error("El empleado no está inscrito.", 404)
        return self._ses_guardar_participantes(rec, quedan, "quitar_participante")

    def registrar_asistencia(self, sesion_id, asistencias):
        """asistencias: [{empleado_id, fecha, estado: Asistió | Faltó | null}]."""
        import simplejson
        rec = self._ses_get(sesion_id)
        f = self.ctr_f["sesiones_de_capacitacion"]
        a = rec.get("answers") or {}
        estatus = self._ses_estatus(a)
        if estatus not in ("En curso", "Finalizada"):
            self._ses_error(f"La asistencia se registra en una sesión En curso o Finalizada (esta está {estatus}).", 409)
        dias = {d.isoformat() for d in self._ses_dias(a)}
        if not label(["Por día", "Semanal"], a.get(f["recurrencia_tipo"])) and a.get(f["recurrencia_tipo"]):
            ini = _fecha(a.get(f["fecha_inicio"]))
            fin = min(_fecha(a.get(f["recurrencia_repetir_hasta"])) or self._ctr_hoy(), self._ctr_hoy())
            dias |= {(ini + timedelta(days=i)).isoformat() for i in range((fin - ini).days + 1)} if ini else set()
        actuales = list(a.get(f["participantes"]) or [])
        por_id = {str(p.get(f["participante_id"])): p for p in actuales}
        errores = []
        for x in asistencias or []:
            x = x if isinstance(x, dict) else {}
            p = por_id.get(str(x.get("empleado_id") or ""))
            fecha = _fecha(x.get("fecha"))
            estado = x.get("estado")
            if not p:
                errores.append(f"El empleado {x.get('empleado_id')} no está inscrito.")
            elif not fecha or fecha.isoformat() not in dias:
                errores.append(f"{x.get('fecha')} no es un día transcurrido de la sesión.")
            elif estado not in ("Asistió", "Faltó", None):
                errores.append(f"Estado no válido: {estado}.")
            else:
                asis = self._ses_json(p.get(f["participante_asistencia"]))
                if estado:
                    asis[fecha.isoformat()] = estado
                else:
                    asis.pop(fecha.isoformat(), None)
                p[f["participante_asistencia"]] = simplejson.dumps(asis, sort_keys=True)
        if errores:
            self._ses_error("\n".join(errores))
        return self._ses_guardar_participantes(rec, actuales, "registrar_asistencia")

    def calificar_participante(self, sesion_id, empleado_id, calificaciones):
        """calificaciones: {examen_id: 0–100}; null borra la de ese examen."""
        import simplejson
        rec = self._ses_get(sesion_id)
        f = self.ctr_f["sesiones_de_capacitacion"]
        a = rec.get("answers") or {}
        minimas = self._ses_minimas(a)
        if not minimas:
            self._ses_error("La sesión no tiene exámenes.", 409)
        if self._ses_estatus(a) not in ("En curso", "Finalizada"):
            self._ses_error("Se califica en una sesión En curso o Finalizada.", 409)
        actuales = list(a.get(f["participantes"]) or [])
        p = next((x for x in actuales if str(x.get(f["participante_id"])) == str(empleado_id)), None)
        if not p:
            self._ses_error("El empleado no está inscrito.", 404)
        if "Asistió" not in self._ses_json(p.get(f["participante_asistencia"])).values():
            self._ses_error("Registra primero su asistencia: solo se califica a quien asistió.", 409)
        cal = self._ses_json(p.get(f["participante_calificaciones"]))
        errores = []
        for k, v in (calificaciones or {}).items():
            if k not in minimas:
                errores.append(f"El examen {k} no es de esta sesión.")
            elif v is None or v == "":
                cal.pop(k, None)
            else:
                try:
                    n = float(v)
                except (TypeError, ValueError):
                    n = -1
                if not 0 <= n <= 100:
                    errores.append("La calificación va de 0 a 100.")
                else:
                    cal[k] = n
        if errores:
            self._ses_error("\n".join(errores))
        p[f["participante_calificaciones"]] = simplejson.dumps(cal, sort_keys=True) if cal else ""
        if cal:
            p[f["participante_calificacion"]] = min(cal.values())
        else:
            p.pop(f["participante_calificacion"], None)
        return self._ses_guardar_participantes(rec, actuales, "calificar_participante")
