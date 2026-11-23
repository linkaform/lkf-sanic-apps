# -*- coding: utf-8 -*-
"""Servicios, perfiles y equipos de Contratistas (CF-02-B).

Spec: clave10-sdk/specs/contratos/contratos-001-modelo-de-datos.md (forma
Recursos de contrato). Contrato con el front: RecursoContrato / RecursoInput
en clave10/src/types/contratistas/contratos.ts.

- Una sola forma para los tres catálogos (campo tipo). Configuración de la
  cuenta: no se filtra por empresa activa.
- Nombre único por tipo entre los activos. Al menos un requerimiento.
- Perfil solo acepta requerimientos de ámbito Persona; Equipo solo de ámbito
  Equipo; Servicio cualquiera. Clase (Equipo/Vehículo/Herramienta) solo en Equipo.
- Borrar = desactivar: el motor (ME-15) deja de exigir sus requerimientos.
- Guardar recalcula el cumplimiento de los contratos que lo usan.
"""
import re

from .contratistas_contratos import _int, label, opt

TIPOS = ["Servicio", "Perfil", "Equipo"]
CLASES = ["Equipo", "Vehículo", "Herramienta"]
AMBITOS = ["Empresa", "Persona", "Equipo"]
AMBITO_PERMITIDO = {"Perfil": "Persona", "Equipo": "Equipo"}
ESTATUS = ["Activo", "Inactivo"]


class RecursosMixin:
    """Se mezcla en Accesos junto con RequerimientosMixin y CumplimientoMixin."""

    def _rec_error(self, msg, status=400):
        return self.LKFException({"title": "Servicios, perfiles y equipos", "msg": msg, "status_code": status})

    def _rec_requiere_forma(self):
        if not self.RECURSOS_CONTRATO_FORM:
            self._rec_error("La forma Recursos de contrato no está instalada en esta cuenta.", 409)

    def _rec_requerimientos(self, ids, cache):
        """{id: requerimiento normalizado} (None si no existe)."""
        fq = self.ctr_f["requerimientos_de_cumplimiento"]
        out = {}
        for i in ids:
            if i not in cache:
                r = self._ctr_get(self.REQUERIMIENTOS_FORM, i) if self.REQUERIMIENTOS_FORM else None
                a = (r or {}).get("answers") or {}
                cache[i] = {"id": i, "nombre": a.get(fq["nombre"]) or "",
                            "ambito": label(AMBITOS, a.get(fq["ambito"])) or "Empresa",
                            "activo": a.get(fq["estatus"]) != opt("Inactivo")} if r else None
            out[i] = cache[i]
        return out

    def rec_out(self, rec, cache=None):
        cache = {} if cache is None else cache
        f = self.ctr_f["recursos_de_contrato"]
        a = rec.get("answers") or {}
        tipo = label(TIPOS, a.get(f["tipo"])) or "Servicio"
        ids = [str(g.get(f["requerimientos_id"])) for g in a.get(f["requerimientos"]) or [] if g.get(f["requerimientos_id"])]
        reqs = self._rec_requerimientos(ids, cache)
        out = {
            "id": str(rec["_id"]), "tipo": tipo, "nombre": a.get(f["nombre"]) or "",
            "descripcion": a.get(f["descripcion"]) or None, "categoria": a.get(f["categoria"]) or None,
            "clase": label(CLASES, a.get(f["clase"])) if tipo == "Equipo" else None,
            # ámbito va de más para los chips por ámbito de la lista.
            "requerimientos": [{"id": i, "nombre": (reqs.get(i) or {}).get("nombre") or
                                next((g.get(f["requerimientos_nombre"]) for g in a.get(f["requerimientos"]) or []
                                      if str(g.get(f["requerimientos_id"])) == i), ""),
                                "ambito": (reqs.get(i) or {}).get("ambito")} for i in ids],
            "estatus": label(ESTATUS, a.get(f["estatus"])) or "Activo",
        }
        return {k: v for k, v in out.items() if v is not None}

    # ------------------------------------------------------------------ API

    def list_recursos(self, tipo, categoria=None, clase=None, estatus=None, search=None, limit=25, offset=0):
        if tipo not in TIPOS:
            self._rec_error("tipo debe ser Servicio, Perfil o Equipo.")
        if not self.RECURSOS_CONTRATO_FORM:
            return {"items": [], "total": 0}
        f = self.ctr_f["recursos_de_contrato"]
        match = {f"answers.{f['tipo']}": opt(tipo)}
        if categoria:
            match[f"answers.{f['categoria']}"] = categoria
        if clase:
            if clase not in CLASES:
                self._rec_error(f"Clase no válida: {clase}.")
            match[f"answers.{f['clase']}"] = opt(clase)
        if estatus:
            if estatus not in ESTATUS:
                self._rec_error(f"Estatus no válido: {estatus}.")
            match[f"answers.{f['estatus']}"] = opt(estatus)
        if search and search.strip():
            rx = {"$regex": re.escape(search.strip()), "$options": "i"}
            match["$or"] = [{f"answers.{f['nombre']}": rx}, {f"answers.{f['descripcion']}": rx}]
        q = {"form_id": self.RECURSOS_CONTRATO_FORM, "deleted_at": {"$exists": False}, **match}
        total = self.cr.count_documents(q)
        rows = self._ctr_find(self.RECURSOS_CONTRATO_FORM, match, sort=[(f"answers.{f['nombre']}", 1)],
                              skip=max(0, _int(offset)), limit=max(1, min(_int(limit, 25), 200)))
        cache = {}
        return {"items": [self.rec_out(r, cache) for r in rows], "total": total}

    def get_recurso(self, recurso_id):
        self._rec_requiere_forma()
        rec = self._ctr_get(self.RECURSOS_CONTRATO_FORM, recurso_id)
        if not rec:
            self._rec_error("El servicio, perfil o equipo no existe.", 404)
        return self.rec_out(rec)

    def save_recurso(self, recurso, recurso_id=None):
        """Alta (sin id) o edición completa (con id)."""
        self._rec_requiere_forma()
        r = recurso if isinstance(recurso, dict) else {}
        f = self.ctr_f["recursos_de_contrato"]
        errores = []
        tipo = r.get("tipo")
        if tipo not in TIPOS:
            errores.append("El tipo debe ser Servicio, Perfil o Equipo.")
        nombre = " ".join(str(r.get("nombre") or "").split())
        if not nombre:
            errores.append("El nombre es obligatorio.")
        clase = r.get("clase")
        if tipo == "Equipo" and clase not in CLASES:
            errores.append("La clase del equipo debe ser Equipo, Vehículo o Herramienta.")
        estatus = r.get("estatus") if r.get("estatus") in ESTATUS else "Activo"
        ids = list(dict.fromkeys(str(i) for i in r.get("requerimientos") or []))
        if not ids:
            errores.append("Liga al menos un requerimiento.")
        reqs = self._rec_requerimientos(ids, {})
        for i, q in reqs.items():
            if not q:
                errores.append(f"El requerimiento {i} no existe.")
            elif not q["activo"]:
                errores.append(f"{q['nombre']} está inactivo.")
            elif AMBITO_PERMITIDO.get(tipo) and q["ambito"] != AMBITO_PERMITIDO[tipo]:
                errores.append(f"{q['nombre']} es de ámbito {q['ambito']}; un {tipo} solo acepta "
                               f"requerimientos de ámbito {AMBITO_PERMITIDO[tipo]}.")
        if errores:
            self._rec_error("\n".join(errores))
        if estatus == "Activo":
            match = {f"answers.{f['tipo']}": opt(tipo), f"answers.{f['estatus']}": {"$ne": opt("Inactivo")},
                     f"answers.{f['nombre']}": {"$regex": f"^{re.escape(nombre)}$", "$options": "i"}}
            if any(str(x["_id"]) != str(recurso_id or "") for x in self._ctr_find(self.RECURSOS_CONTRATO_FORM, match)):
                self._rec_error(f"Ya hay un {tipo.lower()} activo llamado {nombre}.", 409)
        a = {
            f["tipo"]: opt(tipo), f["nombre"]: nombre, f["estatus"]: opt(estatus),
            f["requerimientos"]: [{f["requerimientos_id"]: i, f["requerimientos_nombre"]: reqs[i]["nombre"]} for i in ids],
        }
        if (r.get("descripcion") or "").strip():
            a[f["descripcion"]] = r["descripcion"].strip()
        if (r.get("categoria") or "").strip() and tipo != "Perfil":
            a[f["categoria"]] = r["categoria"].strip()
        if tipo == "Equipo":
            a[f["clase"]] = opt(clase)
        if recurso_id:
            if not self._ctr_get(self.RECURSOS_CONTRATO_FORM, recurso_id):
                self._rec_error("El servicio, perfil o equipo no existe.", 404)
            self._ctr_patch(self.RECURSOS_CONTRATO_FORM, str(recurso_id), a, "save_recurso")
        else:
            recurso_id = self._ctr_post(self.RECURSOS_CONTRATO_FORM, a, "save_recurso")
            if not recurso_id:
                self._rec_error("LinkaForm no regresó el id.", 500)
        if self.CUMPLIMIENTO_FORM:  # motor ME-15 de los contratos que lo usan
            cache = {}
            for c in self._req_contratos([str(recurso_id)]):
                self.recalcular_contrato(str(c["_id"]), cache)
        return self.get_recurso(str(recurso_id))

    def get_aplicacion_recurso(self, recurso_id):
        """Pestaña Aplicación: requerimientos ligados (con detalle) y contratos
        donde se usa (en los que mi empresa es cliente)."""
        recurso = self.get_recurso(recurso_id)
        mi_empresa = self.ctr_empresa_activa_id()
        fc = self.ctr_f["contratos_de_servicio"]
        requerimientos = []
        for q in recurso["requerimientos"]:
            rec = self._ctr_get(self.REQUERIMIENTOS_FORM, q["id"]) if self.REQUERIMIENTOS_FORM else None
            if rec:
                d = self.req_out(rec)
                requerimientos.append({k: d.get(k) for k in ("id", "nombre", "descripcion", "tipo", "ambito",
                                                              "vigencia_modo", "vigencia", "periodicidad",
                                                              "limitante", "estatus")})
        contratos = [{"id": str(c["_id"]), "folio": c["answers"].get(fc["folio"]) or "",
                      "objeto": c["answers"].get(fc["objeto"]) or "",
                      "contratista": c["answers"].get(fc["contratista"]) or "",
                      "cumplimiento_pct": c["answers"].get(fc["cumplimiento_pct"]) or 0}
                     for c in self._req_contratos([str(recurso_id)])
                     if str(c["answers"].get(fc["cliente_id"]) or "") == mi_empresa]
        return {"requerimientos": requerimientos, "contratos": contratos}
