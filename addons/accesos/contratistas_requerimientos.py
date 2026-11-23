# -*- coding: utf-8 -*-
"""Catálogo de requerimientos de cumplimiento de Contratistas (CF-01-B).

Spec: clave10-sdk/specs/contratos/contratos-001-modelo-de-datos.md (forma
Requerimientos de cumplimiento). Contrato con el front: Requerimiento /
RequerimientoInput en clave10/src/types/contratistas/contratos.ts.

- Es configuración de la cuenta: no se filtra por empresa activa.
- Nombre único (sin distinguir mayúsculas) entre los activos.
- Borrar = desactivar (estatus Inactivo); el motor deja de exigirlo.
- Guardar recalcula el cumplimiento (motor ME-15) de los contratos que lo
  exigen por sus recursos y de las relaciones que lo tienen asignado.
- Aplicación (pestaña del detalle): recursos que lo exigen, relaciones que lo
  tienen asignado, contratos donde se solicita y sujetos con su estado.
"""
import re

from .contratistas_contratos import _int, _num, label, opt

TIPOS = ["Documento", "Examen", "Inspección"]
AMBITOS = ["Empresa", "Persona", "Equipo"]
PLATAFORMAS = ["Sin plataforma", "SAT", "IMSS", "INFONAVIT", "STPS", "Registro Público de Comercio", "INE", "Otra"]
PERIODICIDADES = ["Única", "Mensual", "Bimestral", "Trimestral", "Cuatrimestral", "Semestral", "Anual",
                  "Cada 3 años", "Cada 10 años"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
         "Noviembre", "Diciembre"]
UNIDADES_VIGENCIA = ["días", "meses", "años"]
UNIDADES_AVISO = ["días", "semanas", "meses"]
ESTATUS = ["Activo", "Inactivo"]
DIA_LIMITE = 17
CALIFICACION_MINIMA = 80


class RequerimientosMixin:
    """Se mezcla en Accesos junto con ContratosMixin y CumplimientoMixin."""

    def _req_error(self, msg, status=400):
        return self.LKFException({"title": "Requerimientos", "msg": msg, "status_code": status})

    def _req_requiere_forma(self):
        if not self.REQUERIMIENTOS_FORM:
            self._req_error("La forma Requerimientos de cumplimiento no está instalada en esta cuenta.", 409)

    # -------------------------------------------------------------- salida

    def req_out(self, rec):
        f = self.ctr_f["requerimientos_de_cumplimiento"]
        a = rec.get("answers") or {}
        tipo = label(TIPOS, a.get(f["tipo"])) or "Documento"
        n_vig = _int(a.get(f["vigencia_n"]), None)
        out = {
            "id": str(rec["_id"]),
            "nombre": a.get(f["nombre"]) or "",
            "descripcion": a.get(f["descripcion"]) or None,
            "tipo": tipo,
            "ambito": label(AMBITOS, a.get(f["ambito"])) or "Empresa",
            "plataforma": label(PLATAFORMAS, a.get(f["plataforma"])) or "Sin plataforma",
            "plataforma_url": a.get(f["plataforma_url"]) or None,
            "vigencia_modo": "periodo" if a.get(f["vigencia_modo"]) == opt("Periodo") else "vigencia",
            "vigencia": {"n": n_vig, "unidad": label(UNIDADES_VIGENCIA, a.get(f["vigencia_unidad"])) or "meses"}
            if n_vig else None,
            "periodicidad": label(PERIODICIDADES, a.get(f["periodicidad"])),
            "meses_periodo": [i + 1 for i, m in enumerate(MESES) if opt(m) in (a.get(f["meses_periodo"]) or [])] or None,
            "dia_limite": _int(a.get(f["dia_limite"]), None),
            "recurrencia": self._ctr_recurrencia_out(a, "requerimientos_de_cumplimiento") if tipo != "Documento" else None,
            "tolerancia_dias": _int(a.get(f["tolerancia_dias"]), None),
            "aviso": {"n": _int(a.get(f["aviso_n"]), 1), "unidad": label(UNIDADES_AVISO, a.get(f["aviso_unidad"])) or "días",
                      "repetir": a.get(f["aviso_repetir"]) == opt("Sí")} if a.get(f["aviso_activo"]) == opt("Sí") else None,
            "requiere_acuse": a.get(f["requiere_acuse"]) == opt("Sí"),
            "limitante": a.get(f["limitante"]) == opt("Sí"),
            "criterios": [c.get(f["criterio"]) for c in a.get(f["criterios"]) or [] if c.get(f["criterio"])],
            "documento_ejemplo": self._ctr_archivo(a.get(f["documento_ejemplo"])),
            "inspeccion": a.get(f["inspeccion"]) or None,
            "estatus": label(ESTATUS, a.get(f["estatus"])) or "Activo",
        }
        if tipo == "Examen":
            vr_n = _int(a.get(f["examen_vigencia_resultado_n"]), None)
            out["examen"] = {
                "modalidad": "digital" if a.get(f["examen_modalidad"]) == opt("Digital") else "fisico",
                "intentos": _int(a.get(f["examen_intentos"]), 1),
                "calificacion_minima": _num(a.get(f["examen_calificacion_minima"])) or CALIFICACION_MINIMA,
                "preguntas_aleatorias": a.get(f["examen_preguntas_aleatorias"]) == opt("Sí"),
                "respuestas_aleatorias": a.get(f["examen_respuestas_aleatorias"]) == opt("Sí"),
                **({"vigencia_resultado": {"n": vr_n, "unidad": label(UNIDADES_VIGENCIA, a.get(f["examen_vigencia_resultado_unidad"])) or "meses"}}
                   if vr_n else {}),
            }
        return {k: v for k, v in out.items() if v is not None or k == "vigencia"}

    # --------------------------------------------------------------- entrada

    def _req_answers_in(self, r):
        """RequerimientoInput -> answers completos (valida todo)."""
        f = self.ctr_f["requerimientos_de_cumplimiento"]
        errores = []
        nombre = " ".join(str(r.get("nombre") or "").split())
        if not nombre:
            errores.append("El nombre es obligatorio.")
        tipo, ambito = r.get("tipo"), r.get("ambito")
        if tipo not in TIPOS:
            errores.append("El tipo debe ser Documento, Examen o Inspección.")
        if ambito not in AMBITOS:
            errores.append("El ámbito debe ser Empresa, Persona o Equipo.")
        plataforma = r.get("plataforma") or "Sin plataforma"
        if plataforma not in PLATAFORMAS:
            errores.append(f"Plataforma no válida: {plataforma}.")
        modo = r.get("vigencia_modo") or "vigencia"
        if modo not in ("vigencia", "periodo"):
            errores.append("vigencia_modo debe ser vigencia o periodo.")
        a = {f[k]: None for k in f if k not in ("criterios", "criterio")}
        a.update({
            f["nombre"]: nombre, f["descripcion"]: (r.get("descripcion") or "").strip() or None,
            f["tipo"]: opt(tipo) if tipo in TIPOS else None, f["ambito"]: opt(ambito) if ambito in AMBITOS else None,
            f["plataforma"]: opt(plataforma), f["plataforma_url"]: (r.get("plataforma_url") or "").strip() or None,
            f["vigencia_modo"]: opt("Periodo" if modo == "periodo" else "Vigencia"),
            f["requiere_acuse"]: opt("Sí") if r.get("requiere_acuse") else opt("No"),
            f["limitante"]: opt("Sí") if r.get("limitante") else opt("No"),
            f["estatus"]: opt(r.get("estatus") if r.get("estatus") in ESTATUS else "Activo"),
            f["inspeccion"]: ((r.get("inspeccion") or "").strip() or None) if tipo == "Inspección" else None,
        })
        if modo == "vigencia":
            vig = r.get("vigencia")
            if vig:  # vacío = permanente
                n = _int(vig.get("n"), 0)
                if n < 1 or vig.get("unidad") not in UNIDADES_VIGENCIA:
                    errores.append("La vigencia necesita cantidad ≥ 1 y unidad días, meses o años.")
                a.update({f["vigencia_n"]: n, f["vigencia_unidad"]: opt(vig.get("unidad") or "meses")})
        else:
            per = r.get("periodicidad")
            if per not in PERIODICIDADES:
                errores.append("La periodicidad es obligatoria en modo periodo.")
            meses = [m for m in r.get("meses_periodo") or [] if isinstance(m, int) and 1 <= m <= 12]
            dia = _int(r.get("dia_limite"), DIA_LIMITE)
            if not 1 <= dia <= 31:
                errores.append("El día límite debe estar entre 1 y 31.")
            a.update({f["periodicidad"]: opt(per) if per in PERIODICIDADES else None, f["dia_limite"]: dia,
                      f["meses_periodo"]: [opt(MESES[m - 1]) for m in sorted(set(meses))] or None})
        if tipo in ("Examen", "Inspección"):
            if r.get("recurrencia"):
                a.update(self._ctr_recurrencia_in(r["recurrencia"], "requerimientos_de_cumplimiento"))
            tol = _int(r.get("tolerancia_dias"), 0)
            if tol < 0:
                errores.append("La tolerancia no puede ser negativa.")
            a[f["tolerancia_dias"]] = tol or None
        if tipo == "Examen":
            ex = r.get("examen") or {}
            intentos = _int(ex.get("intentos"), 1)
            minima = _num(ex.get("calificacion_minima"))
            minima = CALIFICACION_MINIMA if minima is None else minima
            if not 1 <= intentos <= 10:
                errores.append("Los intentos del examen van de 1 a 10.")
            if not 0 <= minima <= 100:
                errores.append("La calificación mínima va de 0 a 100.")
            vr = ex.get("vigencia_resultado") or {}
            a.update({
                f["examen_modalidad"]: opt("Digital" if ex.get("modalidad") == "digital" else "Físico"),
                f["examen_intentos"]: intentos, f["examen_calificacion_minima"]: minima,
                f["examen_preguntas_aleatorias"]: opt("Sí") if ex.get("preguntas_aleatorias") else opt("No"),
                f["examen_respuestas_aleatorias"]: opt("Sí") if ex.get("respuestas_aleatorias") else opt("No"),
                f["examen_vigencia_resultado_n"]: _int(vr.get("n"), None) if vr.get("n") else None,
                f["examen_vigencia_resultado_unidad"]: opt(vr["unidad"]) if vr.get("unidad") in UNIDADES_VIGENCIA else None,
            })
        aviso = r.get("aviso")
        if aviso:
            n = _int(aviso.get("n"), 0)
            if n < 1 or aviso.get("unidad") not in UNIDADES_AVISO:
                errores.append("El aviso necesita cantidad ≥ 1 y unidad días, semanas o meses.")
            a.update({f["aviso_activo"]: opt("Sí"), f["aviso_n"]: n, f["aviso_unidad"]: opt(aviso.get("unidad") or "días"),
                      f["aviso_repetir"]: opt("Sí") if aviso.get("repetir") else opt("No")})
        else:
            a[f["aviso_activo"]] = opt("No")
        a[f["criterios"]] = [{f["criterio"]: str(c).strip()} for c in r.get("criterios") or [] if str(c).strip()]
        ejemplo = r.get("documento_ejemplo")
        if isinstance(ejemplo, dict) and str(ejemplo.get("file_url") or "").startswith("http"):
            a[f["documento_ejemplo"]] = [{"file_name": ejemplo.get("name") or "ejemplo", "file_url": ejemplo["file_url"]}]
        if errores:
            self._req_error("\n".join(errores))
        return {k: v for k, v in a.items() if v is not None}

    def _req_nombre_libre(self, nombre, excepto=None):
        f = self.ctr_f["requerimientos_de_cumplimiento"]
        match = {f"answers.{f['nombre']}": {"$regex": f"^{re.escape(nombre)}$", "$options": "i"},
                 f"answers.{f['estatus']}": {"$ne": opt("Inactivo")}}
        for r in self._ctr_find(self.REQUERIMIENTOS_FORM, match):
            if str(r["_id"]) != str(excepto or ""):
                self._req_error(f"Ya hay un requerimiento activo llamado {nombre}.", 409)

    # --------------------------------------------------------- dónde se usa

    def _req_recursos(self, req_id):
        fr = self.ctr_f["recursos_de_contrato"]
        if not self.RECURSOS_CONTRATO_FORM:
            return []
        return self._ctr_find(self.RECURSOS_CONTRATO_FORM,
                              {f"answers.{fr['requerimientos']}.{fr['requerimientos_id']}": str(req_id)})

    def _req_contratos(self, recurso_ids):
        fc = self.ctr_f["contratos_de_servicio"]
        if not recurso_ids or not self.CONTRATOS_FORM:
            return []
        ids = [str(i) for i in recurso_ids]
        return self._ctr_find(self.CONTRATOS_FORM, {"$or": [
            {f"answers.{fc['servicios']}.{fc['servicio_id']}": {"$in": ids}},
            {f"answers.{fc['perfiles']}.{fc['perfil_id']}": {"$in": ids}},
            {f"answers.{fc['equipos']}.{fc['equipo_id']}": {"$in": ids}}]})

    def _req_relaciones(self, req_id):
        fr = self.ctr_f["relaciones_entre_empresas"]
        if not self.RELACIONES_FORM:
            return []
        return self._ctr_find(self.RELACIONES_FORM,
                              {f"answers.{fr['requerimientos_asignados']}.{fr['requerimientos_asignados_id']}": str(req_id)})

    def _req_recalcular(self, req_id):
        """Motor ME-15 de todo lo que exige este requerimiento."""
        if not self.CUMPLIMIENTO_FORM:
            return
        cache = {}
        recursos = [str(r["_id"]) for r in self._req_recursos(req_id)]
        for c in self._req_contratos(recursos):
            self.recalcular_contrato(str(c["_id"]), cache)
        for rel in self._req_relaciones(req_id):
            self.recalcular_relacion(str(rel["_id"]), cache)

    # ------------------------------------------------------------------ API

    def list_requerimientos(self, tipo=None, ambito=None, estatus=None, search=None, limit=25, offset=0):
        if not self.REQUERIMIENTOS_FORM:
            return {"items": [], "total": 0}
        f = self.ctr_f["requerimientos_de_cumplimiento"]
        match = {}
        for valor, campo, opciones in ((tipo, "tipo", TIPOS), (ambito, "ambito", AMBITOS), (estatus, "estatus", ESTATUS)):
            if valor:
                if valor not in opciones:
                    self._req_error(f"{campo} no válido: {valor}.")
                match[f"answers.{f[campo]}"] = opt(valor)
        if search and search.strip():
            rx = {"$regex": re.escape(search.strip()), "$options": "i"}
            match["$or"] = [{f"answers.{f['nombre']}": rx}, {f"answers.{f['descripcion']}": rx}]
        q = {"form_id": self.REQUERIMIENTOS_FORM, "deleted_at": {"$exists": False}, **match}
        total = self.cr.count_documents(q)
        rows = self._ctr_find(self.REQUERIMIENTOS_FORM, match, sort=[(f"answers.{f['nombre']}", 1)],
                              skip=max(0, _int(offset)), limit=max(1, min(_int(limit, 25), 200)))
        return {"items": [self.req_out(r) for r in rows], "total": total}

    def get_requerimiento(self, requerimiento_id):
        self._req_requiere_forma()
        rec = self._ctr_get(self.REQUERIMIENTOS_FORM, requerimiento_id)
        if not rec:
            self._req_error("El requerimiento no existe.", 404)
        return self.req_out(rec)

    def save_requerimiento(self, requerimiento, requerimiento_id=None):
        """Alta (sin id) o edición completa (con id: se manda el requerimiento entero)."""
        self._req_requiere_forma()
        r = requerimiento if isinstance(requerimiento, dict) else {}
        a = self._req_answers_in(r)
        f = self.ctr_f["requerimientos_de_cumplimiento"]
        if a.get(f["estatus"]) != opt("Inactivo"):
            self._req_nombre_libre(a[f["nombre"]], excepto=requerimiento_id)
        if requerimiento_id:
            if not self._ctr_get(self.REQUERIMIENTOS_FORM, requerimiento_id):
                self._req_error("El requerimiento no existe.", 404)
            self._ctr_patch(self.REQUERIMIENTOS_FORM, str(requerimiento_id), a, "save_requerimiento")
        else:
            requerimiento_id = self._ctr_post(self.REQUERIMIENTOS_FORM, a, "save_requerimiento")
            if not requerimiento_id:
                self._req_error("LinkaForm no regresó el id del requerimiento.", 500)
        self._req_recalcular(str(requerimiento_id))
        return self.get_requerimiento(str(requerimiento_id))

    def get_aplicacion_requerimiento(self, requerimiento_id):
        """Pestaña Aplicación: dónde se exige y a quién (relaciones donde soy cliente)."""
        self._req_requiere_forma()
        self.get_requerimiento(requerimiento_id)
        mi_empresa = self.ctr_empresa_activa_id()
        fr, fc = self.ctr_f["recursos_de_contrato"], self.ctr_f["contratos_de_servicio"]
        frel, fcu = self.ctr_f["relaciones_entre_empresas"], self.ctr_f["cumplimiento_de_requerimientos"]
        recursos = self._req_recursos(requerimiento_id)
        exigencia = [{"id": str(r["_id"]), "nombre": (r.get("answers") or {}).get(fr["nombre"]) or "",
                      "tipo": label(["Servicio", "Perfil", "Equipo"], (r.get("answers") or {}).get(fr["tipo"])) or ""}
                     for r in recursos]
        mis = lambda a, k: str(a.get(k) or "") == mi_empresa  # noqa: E731
        contratos = [{"id": str(c["_id"]), "folio": c["answers"].get(fc["folio"]) or "",
                      "contratista": c["answers"].get(fc["contratista"]) or ""}
                     for c in self._req_contratos([x["id"] for x in exigencia]) if mis(c["answers"], fc["cliente_id"])]
        relaciones = [{"id": str(r["_id"]), "folio": r["answers"].get(frel["folio"]) or "",
                       "contratista": r["answers"].get(frel["contratista"]) or ""}
                      for r in self._req_relaciones(requerimiento_id) if mis(r["answers"], frel["cliente_id"])]
        sujetos = []
        if self.CUMPLIMIENTO_FORM:
            mis_rel = [str(r["_id"]) for r in self._ctr_find(self.RELACIONES_FORM, {f"answers.{frel['cliente_id']}": mi_empresa})]
            filas = self._ctr_find(self.CUMPLIMIENTO_FORM, {f"answers.{fcu['requerimiento_id']}": str(requerimiento_id),
                                                            f"answers.{fcu['relacion_id']}": {"$in": mis_rel}},
                                   sort=[(f"answers.{fcu['periodo_inicio']}", 1)])
            for x in filas:
                fila = self.cum_fila_out(x)
                sujetos.append({"tipo": fila["sujeto"]["tipo"],
                                "sujeto": fila["sujeto"].get("empleado") or fila["sujeto"].get("equipo") or fila["sujeto"]["empresa"],
                                "empresa": fila["sujeto"]["empresa"], "contrato": fila["contrato"],
                                "periodo": fila["periodo"]["clave"], "estado": fila["estado"]})
        return {"exigencia": exigencia, "relaciones": relaciones, "contratos": contratos, "sujetos": sujetos}
