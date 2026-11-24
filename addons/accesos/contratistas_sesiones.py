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
"""
import re

from .contratistas_contratos import _fecha, _int, label, opt

TIPOS = ["Curso", "Capacitación", "Plática", "Inducción"]
ESTATUS = ["Programada", "En curso", "Finalizada", "Cancelada"]
ORDEN_ESTATUS = ["En curso", "Programada", "Finalizada", "Cancelada"]
MATERIALES = ["Video", "Lectura", "Presentación", "Cuestionario", "Clase en vivo"]
ORIGENES = ["Archivo", "Enlace"]
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
