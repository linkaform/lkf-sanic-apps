# -*- coding: utf-8 -*-
"""Relaciones cliente↔contratista de Contratistas (R-01).

Spec: clave10-sdk/specs/relaciones/relaciones-001-modelo-de-datos.md.

- Una relación se guarda una vez. Con E = empresa activa del usuario:
  direccion "contratistas" = relaciones con cliente = E (la fila muestra al
  contratista); "clientes" = relaciones con contratista = E (muestra al cliente).
- Solo una relación por (cliente, contratista, relacion_padre): dar de alta
  otra igual reactiva la existente.
- No se desactiva una relación con contratos vigentes (hay que pausarlos o
  cancelarlos antes).
- num_contratos se calcula al leer (contratos no cancelados). cumplimiento_pct
  lo guarda el motor de ME-15 (contratistas_cumplimiento.py).
- Subcontratación (R-03): la hija tiene relacion_padre. Al crearla o
  reactivarla: el padre está Activo, el cliente de la hija es el contratista
  del padre, sin ciclos (el contratista no aparece en la cadena), nivel <= 3 y
  algún contrato vigente del padre permite subcontratación.
- Visibilidad por cadena: además de las dos partes, cualquier empresa de una
  relación de arriba puede leer (get_relacion, get_arbol_relacion) a las de
  abajo; escribir solo las dos partes.
- No se desactiva una relación con subcontrataciones activas.
"""
import re

from .contratistas_contratos import DIAS_POR_VENCER, _fecha, _int, _num, label, opt

DIRECCIONES = ("clientes", "contratistas")
ESTATUS_RELACION = ["Activo", "Inactivo"]
NIVEL_MAX = 3
# Estatus de contrato que no impiden desactivar la relación.
CONTRATO_NO_VIGENTE = ("Pausado", "Cancelado", "Vencido")
MAX_CADENA = 10  # tope de seguridad al subir por relacion_padre


class RelacionesMixin:
    """Se mezcla en Accesos junto con ContratosMixin (usa sus helpers _ctr_*)."""

    # ------------------------------------------------------------------ util

    def _rel_error(self, msg, status=400):
        return self.LKFException({"title": "Relaciones", "msg": msg, "status_code": status})

    def _rel_requiere_forma(self):
        if not self.RELACIONES_FORM:
            self._rel_error("La forma Relaciones entre empresas no está instalada en esta cuenta.", 409)

    def _rel_visible(self, relacion_id, mi_empresa=None):
        mi_empresa = mi_empresa or self.ctr_empresa_activa_id()
        rec = self._ctr_get(self.RELACIONES_FORM, relacion_id) if relacion_id else None
        if not rec:
            self._rel_error("La relación no existe.", 404)
        f = self.ctr_f["relaciones_entre_empresas"]
        a = rec.get("answers") or {}
        if mi_empresa not in (str(a.get(f["cliente_id"]) or ""), str(a.get(f["contratista_id"]) or "")):
            self._rel_error("No tienes acceso a esta relación.", 403)
        return rec

    def _rel_cadena(self, rec):
        """[rec, padre, abuelo, …] hasta la relación directa."""
        f = self.ctr_f["relaciones_entre_empresas"]
        cadena, vistos = [rec], {str(rec["_id"])}
        while len(cadena) < MAX_CADENA:
            pid = str((cadena[-1].get("answers") or {}).get(f["relacion_padre_id"]) or "")
            if not pid or pid in vistos:
                break
            padre = self._ctr_get(self.RELACIONES_FORM, pid)
            if not padre:
                break
            cadena.append(padre)
            vistos.add(pid)
        return cadena

    def _rel_visible_cadena(self, relacion_id, mi_empresa=None):
        """Como _rel_visible, pero también deja leer a las empresas de arriba."""
        mi_empresa = mi_empresa or self.ctr_empresa_activa_id()
        rec = self._ctr_get(self.RELACIONES_FORM, relacion_id) if relacion_id else None
        if not rec:
            self._rel_error("La relación no existe.", 404)
        f = self.ctr_f["relaciones_entre_empresas"]
        for r in self._rel_cadena(rec):
            a = r.get("answers") or {}
            if mi_empresa in (str(a.get(f["cliente_id"]) or ""), str(a.get(f["contratista_id"]) or "")):
                return rec
        self._rel_error("No tienes acceso a esta relación.", 403)

    def _rel_validar_subcontratacion(self, padre, cliente_id, contratista_id):
        """Reglas de la spec al crear o reactivar una hija. Regresa el nivel."""
        f = self.ctr_f["relaciones_entre_empresas"]
        pa = padre.get("answers") or {}
        if pa.get(f["estatus"]) != opt("Activo"):
            self._rel_error("La relación padre está inactiva.", 409)
        if str(pa.get(f["contratista_id"]) or "") != cliente_id:
            self._rel_error("El cliente de la subcontratación debe ser el contratista de la relación padre.")
        nivel = _int(pa.get(f["nivel"]), 1) + 1
        if nivel > NIVEL_MAX:
            self._rel_error(f"Se excede el nivel máximo de subcontratación ({NIVEL_MAX}).")
        for r in self._rel_cadena(padre):
            a = r.get("answers") or {}
            if contratista_id in (str(a.get(f["cliente_id"]) or ""), str(a.get(f["contratista_id"]) or "")):
                self._rel_error("No se puede subcontratar a una empresa que ya está en la cadena "
                                "(se formaría un ciclo).", 409)
        fc = self.ctr_f["contratos_de_servicio"]
        permite = False
        if self.CONTRATOS_FORM:
            for c in self._ctr_find(self.CONTRATOS_FORM, {f"answers.{fc['relacion_id']}": str(padre["_id"]),
                                                         f"answers.{fc['permite_subcontratacion']}": opt("Sí")}):
                if self.ctr_calcular_estatus(c.get("answers") or {}, str(c["_id"])) not in CONTRATO_NO_VIGENTE:
                    permite = True
                    break
        if not permite:
            self._rel_error("Ningún contrato vigente de la relación padre permite subcontratación.", 409)
        return nivel

    def _rel_hijas(self, relacion_ids, solo_activas=False):
        f = self.ctr_f["relaciones_entre_empresas"]
        match = {f"answers.{f['relacion_padre_id']}": {"$in": [str(i) for i in relacion_ids]}}
        if solo_activas:
            match[f"answers.{f['estatus']}"] = opt("Activo")
        return self._ctr_find(self.RELACIONES_FORM, match, sort=[(f"answers.{f['folio']}", 1)])

    def _rel_num_contratos(self, relacion_ids):
        """{relacion_id: contratos no cancelados}."""
        if not relacion_ids or not self.CONTRATOS_FORM:
            return {}
        f = self.ctr_f["contratos_de_servicio"]
        rows = self.cr.aggregate([
            {"$match": {
                "form_id": self.CONTRATOS_FORM, "deleted_at": {"$exists": False},
                f"answers.{f['relacion_id']}": {"$in": [str(i) for i in relacion_ids]},
                f"answers.{f['estatus']}": {"$ne": opt("Cancelado")},
            }},
            {"$group": {"_id": f"$answers.{f['relacion_id']}", "n": {"$sum": 1}}},
        ])
        return {str(r["_id"]): r["n"] for r in rows}

    def _rel_siguiente_folio(self):
        f = self.ctr_f["relaciones_entre_empresas"]
        n = 0
        for r in self._ctr_find(self.RELACIONES_FORM):
            m = re.match(r"^R-(\d+)$", str((r.get("answers") or {}).get(f["folio"]) or ""))
            if m:
                n = max(n, int(m.group(1)))
        return f"R-{n + 1:04d}"

    # ----------------------------------------------------------- formato

    def _rel_empresa_fila(self, empresa_id, cache):
        """Contraparte con logo, representante legal y REPSE (columnas de R-04)."""
        key = f"fila:{empresa_id}"
        if key in cache:
            return cache[key]
        f = self.ctr_f["empresas"]
        a = (self._ctr_get(self.EMPRESAS_FORM, empresa_id) or {}).get("answers") or {}
        out = {"contraparte": {"id": empresa_id, "razon_social": a.get(f["razon_social"], ""),
                               "rfc": a.get(f["rfc"], "")}}
        logo = self._ctr_archivo(a.get(f["logo"]))
        if logo:
            out["contraparte"]["logo"] = logo
        for c in a.get(f["contactos"]) or []:
            if c.get(f["contacto_rol"]) == opt("Representante legal"):
                out["representante"] = {"nombre": c.get(f["contacto_nombre"], ""),
                                        "email": c.get(f["contacto_email"]) or None}
                break
        repse_folio = a.get(f["repse_folio"])
        fin = _fecha(a.get(f["repse_fin"]))
        if repse_folio and fin:
            dias = (fin - self._ctr_hoy()).days
            estatus = "Vencido" if dias < 0 else "Por vencer" if dias <= DIAS_POR_VENCER else "Vigente"
            out["repse"] = {"folio": repse_folio, "fin": fin.isoformat(), "dias_restantes": dias,
                            "estatus": estatus}
        else:
            out["repse"] = {"folio": repse_folio or "", "fin": fin.isoformat() if fin else "",
                            "dias_restantes": 0, "estatus": "Sin REPSE"}
        cache[key] = out
        return out

    def rel_out(self, rec, cache=None, nums=None):
        """Registro -> Relacion del front."""
        cache = {} if cache is None else cache
        f = self.ctr_f["relaciones_entre_empresas"]
        a = rec.get("answers") or {}
        rid = str(rec["_id"])
        if nums is None:
            nums = self._rel_num_contratos([rid])
        return {
            "id": rid,
            "folio": a.get(f["folio"]) or "",
            "cliente": self._ctr_empresa_ref(str(a.get(f["cliente_id"]) or ""), cache),
            "contratista": self._ctr_empresa_ref(str(a.get(f["contratista_id"]) or ""), cache),
            "relacion_padre": a.get(f["relacion_padre_id"]) or None,
            "nivel": _int(a.get(f["nivel"]), 1),
            "requerimientos_asignados": [
                {"id": r.get(f["requerimientos_asignados_id"]), "nombre": r.get(f["requerimientos_asignados_nombre"], "")}
                for r in a.get(f["requerimientos_asignados"]) or []],
            "estatus": label(ESTATUS_RELACION, a.get(f["estatus"])) or "Activo",
            "fecha_alta": a.get(f["fecha_alta"]) or "",
            "notas": a.get(f["notas"]) or "",
            "num_contratos": nums.get(rid, 0),
            "cumplimiento_pct": _num(a.get(f["cumplimiento_pct"])) or 0,
        }

    def rel_fila(self, rec, direccion, cache, nums):
        """Registro -> RelacionFila (lista única Clientes/Contratistas)."""
        f = self.ctr_f["relaciones_entre_empresas"]
        a = rec.get("answers") or {}
        lado = "cliente_id" if direccion == "clientes" else "contratista_id"
        rid = str(rec["_id"])
        return {
            "id": rid,
            "folio": a.get(f["folio"]) or "",
            **self._rel_empresa_fila(str(a.get(f[lado]) or ""), cache),
            "num_contratos": nums.get(rid, 0),
            "cumplimiento_pct": _num(a.get(f["cumplimiento_pct"])) or 0,
            "estatus": label(ESTATUS_RELACION, a.get(f["estatus"])) or "Activo",
        }

    # ------------------------------------------------------------------ API

    def list_relaciones(self, direccion, estatus=None, search=None, limit=25, offset=0):
        if direccion not in DIRECCIONES:
            self._rel_error("direccion debe ser 'clientes' o 'contratistas'.")
        if not self.RELACIONES_FORM:
            return {"items": [], "total": 0}
        mi_empresa = self.ctr_empresa_activa_id()
        f = self.ctr_f["relaciones_entre_empresas"]
        # Mis contratistas = yo soy el cliente; mis clientes = yo soy el contratista.
        mio, otro = ("contratista", "cliente") if direccion == "clientes" else ("cliente", "contratista")
        match = {f"answers.{f[mio + '_id']}": mi_empresa}
        if estatus:
            if estatus not in ESTATUS_RELACION:
                self._rel_error(f"Estatus no válido: {estatus}.")
            match[f"answers.{f['estatus']}"] = opt(estatus)
        if search and search.strip():
            rx = {"$regex": re.escape(search.strip()), "$options": "i"}
            fe = self.ctr_f["empresas"]
            por_rfc = [str(e["_id"]) for e in self._ctr_find(self.EMPRESAS_FORM, {f"answers.{fe['rfc']}": rx})]
            match["$or"] = [{f"answers.{f[otro]}": rx}, {f"answers.{f['folio']}": rx},
                            {f"answers.{f[otro + '_id']}": {"$in": por_rfc}}]
        q = {"form_id": self.RELACIONES_FORM, "deleted_at": {"$exists": False}, **match}
        total = self.cr.count_documents(q)
        limit = max(1, min(_int(limit, 25), 200))
        rows = self._ctr_find(self.RELACIONES_FORM, match, sort=[("created_at", -1)],
                              skip=max(0, _int(offset)), limit=limit)
        nums = self._rel_num_contratos([r["_id"] for r in rows])
        cache = {}
        return {"items": [self.rel_fila(r, direccion, cache, nums) for r in rows], "total": total}

    def get_relacion(self, relacion_id):
        self._rel_requiere_forma()
        return self.rel_out(self._rel_visible_cadena(relacion_id))

    def create_relacion(self, relacion):
        self._rel_requiere_forma()
        relacion = relacion or {}
        direccion = relacion.get("direccion")
        if direccion not in DIRECCIONES:
            self._rel_error("direccion debe ser 'clientes' o 'contratistas'.")
        mi_empresa = self.ctr_empresa_activa_id()
        otra_id = str(relacion.get("contraparte_id") or "")
        if not otra_id:
            self._rel_error("Falta la contraparte.")
        if otra_id == mi_empresa:
            self._rel_error("La contraparte no puede ser tu propia empresa.")
        cache = {}
        otra = self._ctr_get(self.EMPRESAS_FORM, otra_id)
        if not otra:
            self._rel_error("La empresa contraparte no existe.", 404)
        cliente_id, contratista_id = (otra_id, mi_empresa) if direccion == "clientes" else (mi_empresa, otra_id)
        cliente = self._ctr_empresa_ref(cliente_id, cache)
        contratista = self._ctr_empresa_ref(contratista_id, cache)

        f = self.ctr_f["relaciones_entre_empresas"]
        padre_id = str(relacion.get("relacion_padre") or "") or None
        nivel = 1
        if padre_id:
            nivel = self._rel_validar_subcontratacion(self._rel_visible(padre_id, mi_empresa), cliente_id,
                                                      contratista_id)

        # Unicidad por (cliente, contratista, padre): reactivar la existente.
        existente = self._ctr_find(self.RELACIONES_FORM, {
            f"answers.{f['cliente_id']}": cliente_id,
            f"answers.{f['contratista_id']}": contratista_id,
            f"answers.{f['relacion_padre_id']}": padre_id if padre_id else {"$in": [None, ""]},
        }, one=True)
        if existente:
            a = dict(existente.get("answers") or {})
            if a.get(f["estatus"]) != opt("Activo"):
                a[f["estatus"]] = opt("Activo")
                self._ctr_patch(self.RELACIONES_FORM, str(existente["_id"]), a, "create_relacion")
            return self.get_relacion(str(existente["_id"]))

        a = {
            f["folio"]: self._rel_siguiente_folio(),
            f["cliente_id"]: cliente_id, f["cliente"]: cliente["razon_social"],
            f["contratista_id"]: contratista_id, f["contratista"]: contratista["razon_social"],
            f["nivel"]: nivel,
            f["estatus"]: opt("Activo"),
            f["fecha_alta"]: self._ctr_hoy().isoformat(),
            f["num_contratos"]: 0,
            f["cumplimiento_pct"]: 0,
            f["requerimientos_asignados"]: [],
        }
        if padre_id:
            pa_folio = (self._ctr_get(self.RELACIONES_FORM, padre_id) or {}).get("answers", {}).get(f["folio"])
            a.update({f["relacion_padre_id"]: padre_id, f["relacion_padre"]: pa_folio or padre_id})
        if relacion.get("notas"):
            a[f["notas"]] = relacion["notas"]
        relacion_id = self._ctr_post(self.RELACIONES_FORM, a, "create_relacion")
        if not relacion_id:
            self._rel_error("LinkaForm no regresó el id de la relación creada.", 500)
        return self.get_relacion(relacion_id)

    def update_relacion(self, relacion_id, cambios):
        self._rel_requiere_forma()
        cambios = cambios or {}
        rec = self._rel_visible(relacion_id)
        f = self.ctr_f["relaciones_entre_empresas"]
        a = dict(rec.get("answers") or {})
        if "notas" in cambios:
            a[f["notas"]] = cambios.get("notas") or ""
        if cambios.get("requerimientos_asignados") is not None:
            ids = [str(i) for i in cambios["requerimientos_asignados"]]
            fr = self.ctr_f["requerimientos_de_cumplimiento"]
            nombres = {}
            for i in ids:
                q = self._ctr_get(self.REQUERIMIENTOS_FORM, i) if self.REQUERIMIENTOS_FORM else None
                if not q:
                    self._rel_error(f"El requerimiento {i} no existe.", 404)
                nombres[i] = (q.get("answers") or {}).get(fr["nombre"], "")
            a[f["requerimientos_asignados"]] = [
                {f["requerimientos_asignados_id"]: i, f["requerimientos_asignados_nombre"]: nombres[i]} for i in ids]
        self._ctr_patch(self.RELACIONES_FORM, relacion_id, a, "update_relacion")
        if cambios.get("requerimientos_asignados") is not None:
            self.recalcular_relacion(str(relacion_id))  # motor ME-15
        return self.get_relacion(relacion_id)

    def change_status_relacion(self, relacion_id, estatus):
        self._rel_requiere_forma()
        if estatus not in ESTATUS_RELACION:
            self._rel_error("estatus debe ser 'Activo' o 'Inactivo'.")
        rec = self._rel_visible(relacion_id)
        f = self.ctr_f["relaciones_entre_empresas"]
        a = dict(rec.get("answers") or {})
        if a.get(f["estatus"]) == opt(estatus):
            return self.rel_out(rec)
        if estatus == "Inactivo" and self._rel_hijas([relacion_id], solo_activas=True):
            self._rel_error("Desactiva primero las subcontrataciones de esta relación.", 409)
        if estatus == "Activo" and a.get(f["relacion_padre_id"]):
            padre = self._ctr_get(self.RELACIONES_FORM, str(a[f["relacion_padre_id"]]))
            if not padre:
                self._rel_error("La relación padre ya no existe.", 409)
            self._rel_validar_subcontratacion(padre, str(a.get(f["cliente_id"]) or ""),
                                              str(a.get(f["contratista_id"]) or ""))
        if estatus == "Inactivo" and self.CONTRATOS_FORM:
            fc = self.ctr_f["contratos_de_servicio"]
            for c in self._ctr_find(self.CONTRATOS_FORM, {f"answers.{fc['relacion_id']}": str(relacion_id)}):
                if self.ctr_calcular_estatus(c.get("answers") or {}, str(c["_id"])) not in CONTRATO_NO_VIGENTE:
                    self._rel_error("Pausa o cancela los contratos vigentes antes de desactivar la relación.", 409)
        a[f["estatus"]] = opt(estatus)
        self._ctr_patch(self.RELACIONES_FORM, relacion_id, a, "change_status_relacion")
        self.recalcular_relacion(str(relacion_id))  # motor ME-15
        return self.get_relacion(relacion_id)

    def get_arbol_relacion(self, relacion_id):
        """Subcontrataciones hacia abajo de una relación (sin incluirla), por
        nivel. La raíz ve toda la cadena; un intermedio, de su relación hacia abajo."""
        self._rel_requiere_forma()
        self._rel_visible_cadena(relacion_id)
        out, frontera, vistos = [], [str(relacion_id)], {str(relacion_id)}
        cache = {}
        while frontera and len(vistos) < 500:
            hijas = [h for h in self._rel_hijas(frontera) if str(h["_id"]) not in vistos]
            vistos.update(str(h["_id"]) for h in hijas)
            out.extend(hijas)
            frontera = [str(h["_id"]) for h in hijas]
        nums = self._rel_num_contratos([str(r["_id"]) for r in out]) if out else {}
        return [self.rel_out(r, cache, nums) for r in out]
