# -*- coding: utf-8 -*-
"""Mapeo y homologación de requerimientos del contrato (ME-13).

Ficha: contratistas_me13_mapeo.md. Decisiones de Paco (2026-11-24):
- El catálogo maestro son los Requerimientos de cumplimiento de la cuenta
  (CF-01); "Crear +" da de alta ahí un requerimiento Documento sin vencimiento
  con su `codigo` (MAYÚSCULAS, máx. 24, único entre los activos).
- El mapeo se guarda en el contrato (grupo `mapeo`: texto del cliente, nivel,
  requerimiento y % de coincidencia) y los homologados SE EXIGEN: el motor
  ME-15 los suma a los de los servicios (Empresa al contratista, Persona a
  cada empleado ligado, Equipo a cada equipo).
- La similitud se calcula en el back: coeficiente de Dice sobre bigramas del
  texto normalizado (sin acentos ni símbolos), contra nombre y código.
  ≥ 40 % sugiere / auto-mapea; ≥ 60 % homologa al agregar.

Solo el cliente del contrato edita su mapeo; las dos partes lo leen.
"""
import re
import unicodedata

from .contratistas_contratos import _num, label, opt
from .contratistas_requerimientos import codigo_sistema

NIVELES = ["Empresa", "Persona", "Equipo"]
SUGIERE = 0.40
HOMOLOGA = 0.60
MAX_FILAS = 200


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def similitud(a, b):
    """Dice sobre bigramas de caracteres (0..1)."""
    a, b = _norm(a).replace(" ", ""), _norm(b).replace(" ", "")
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) < 2 or len(b) < 2:
        return 0.0
    ba = [a[i:i + 2] for i in range(len(a) - 1)]
    bb = {}
    for i in range(len(b) - 1):
        bb[b[i:i + 2]] = bb.get(b[i:i + 2], 0) + 1
    inter = 0
    for g in ba:
        if bb.get(g):
            inter += 1
            bb[g] -= 1
    return 2.0 * inter / (len(ba) + len(b) - 1)


class MapeoMixin:
    """Se mezcla en Accesos junto con ContratosMixin, RequerimientosMixin y CumplimientoMixin."""

    def _map_error(self, msg, status=400):
        return self.LKFException({"title": "Mapeo de requerimientos", "msg": msg, "status_code": status})

    def _map_catalogo(self):
        """Requerimientos activos: [{id, nombre, codigo, nivel}] por nombre."""
        if not self.REQUERIMIENTOS_FORM:
            return []
        fq = self.ctr_f["requerimientos_de_cumplimiento"]
        out = []
        for r in self._ctr_find(self.REQUERIMIENTOS_FORM, {f"answers.{fq['estatus']}": {"$ne": opt("Inactivo")}}):
            a = r.get("answers") or {}
            out.append({"id": str(r["_id"]), "nombre": a.get(fq["nombre"]) or "", "codigo": a.get(fq["codigo"]) or None,
                        "nivel": label(NIVELES, a.get(fq["ambito"])) or "Empresa"})
        return sorted(out, key=lambda x: x["nombre"].lower())

    @staticmethod
    def _map_mejor(origen, catalogo, nivel=None):
        """(requerimiento, similitud) con mejor match: primero en su nivel, luego en todo."""
        def score(c):
            return max(similitud(origen, c["nombre"]), similitud(origen, c["codigo"] or ""))
        mejor = (None, 0.0)
        for grupo in ([c for c in catalogo if c["nivel"] == nivel] if nivel else [], catalogo):
            for c in grupo:
                s = score(c)
                if s > mejor[1]:
                    mejor = (c, s)
            if mejor[1] >= SUGIERE:
                break
        return mejor

    def _map_contrato(self, contrato_id, editar=False):
        rec = self._ctr_contrato_visible(str(contrato_id or ""))
        fc = self.ctr_f["contratos_de_servicio"]
        a = rec.get("answers") or {}
        editable = str(a.get(fc["cliente_id"]) or "") == self.ctr_empresa_activa_id()
        if editar and not editable:
            self._map_error("Solo el cliente del contrato edita su mapeo de requerimientos.", 403)
        return rec, editable

    def _map_filas_out(self, a, catalogo):
        fc = self.ctr_f["contratos_de_servicio"]
        por_id = {c["id"]: c for c in catalogo}
        filas = []
        for g in a.get(fc["mapeo"]) or []:
            rid = str(g.get(fc["mapeo_requerimiento_id"]) or "")
            req = por_id.get(rid) or ({"id": rid, "nombre": g.get(fc["mapeo_requerimiento"]) or "", "codigo": None,
                                       "nivel": None, "inactivo": True} if rid else None)
            filas.append({"origen": g.get(fc["mapeo_origen"]) or "",
                          "nivel": label(NIVELES, g.get(fc["mapeo_nivel"])) or "Persona",
                          "requerimiento": req, "similitud": _num(g.get(fc["mapeo_similitud"]))})
        return filas

    # ------------------------------------------------------------- API

    def get_mapeo_contrato(self, contrato_id):
        """Catálogo maestro y filas homologadas del contrato ("N de M homologados")."""
        rec, editable = self._map_contrato(contrato_id)
        catalogo = self._map_catalogo()
        filas = self._map_filas_out(rec.get("answers") or {}, catalogo)
        return {"contrato": {"id": str(rec["_id"]), "folio": (rec.get("answers") or {}).get(
                    self.ctr_f["contratos_de_servicio"]["folio"]) or ""},
                "catalogo": catalogo, "filas": filas, "editable": editable,
                "homologados": sum(1 for f in filas if f["requerimiento"]), "total": len(filas),
                "umbral_sugerir": round(SUGIERE * 100), "umbral_homologar": round(HOMOLOGA * 100)}

    def sugerir_mapeo(self, filas, solo_sin_match=False):
        """Auto-mapear / sugerir. filas = [{origen, nivel?, requerimiento_id?}] → con match y %.

        - Sin requerimiento: busca el mejor match (su nivel y luego todo). ≥ 40 %
          lo propone (`sugerido`); ≥ 60 % lo marca `homologa` (al agregar).
        - Con requerimiento y solo_sin_match: no lo toca (Auto-Mapear).
        - El nivel lo toma del catálogo si la coincidencia pasa de 40 %; si no, Persona.
        """
        if not isinstance(filas, list):
            self._map_error("filas debe ser una lista.")
        catalogo = self._map_catalogo()
        por_id = {c["id"]: c for c in catalogo}
        out = []
        for f in filas[:MAX_FILAS]:
            f = f if isinstance(f, dict) else {"origen": str(f)}
            origen = str(f.get("origen") or "").strip()
            nivel = f.get("nivel") if f.get("nivel") in NIVELES else None
            actual = por_id.get(str(f.get("requerimiento_id") or ""))
            if actual and solo_sin_match:
                out.append({"origen": origen, "nivel": nivel or actual["nivel"], "requerimiento": actual,
                            "similitud": f.get("similitud"), "sugerido": False, "homologa": True})
                continue
            req, s = self._map_mejor(origen, catalogo, nivel)
            pct = round(s * 100)
            sug = req if s >= SUGIERE else None
            out.append({"origen": origen, "nivel": (sug or {}).get("nivel") or nivel or "Persona",
                        "requerimiento": sug, "similitud": pct if sug else None,
                        "sugerido": bool(sug), "homologa": s >= HOMOLOGA})
        return {"filas": out, "homologados": sum(1 for f in out if f["requerimiento"]), "total": len(out)}

    def save_mapeo_contrato(self, contrato_id, filas):
        """Guarda la configuración (lista completa) y recalcula lo que exige el contrato."""
        rec, _ = self._map_contrato(contrato_id, editar=True)
        if not isinstance(filas, list):
            self._map_error("filas debe ser una lista.")
        if len(filas) > MAX_FILAS:
            self._map_error(f"Máximo {MAX_FILAS} filas.")
        fc = self.ctr_f["contratos_de_servicio"]
        catalogo = {c["id"]: c for c in self._map_catalogo()}
        previos = {str(g.get(fc["mapeo_requerimiento_id"]) or ""): g.get(fc["mapeo_requerimiento"]) or ""
                   for g in (rec.get("answers") or {}).get(fc["mapeo"]) or []}
        grupo = []
        for f in filas:
            f = f if isinstance(f, dict) else {}
            origen = " ".join(str(f.get("origen") or "").split())
            if not origen:
                self._map_error("Cada fila necesita el texto del cliente.")
            nivel = f.get("nivel") if f.get("nivel") in NIVELES else "Persona"
            rid = str(f.get("requerimiento_id") or "")
            if rid and rid not in catalogo and rid not in previos:
                self._map_error(f"El requerimiento {rid} no existe o está inactivo.", 404)
            nombre = (catalogo.get(rid) or {}).get("nombre") or previos.get(rid, "")
            sim = _num(f.get("similitud"))
            if rid and sim is None:  # misma regla que sugerir_mapeo: contra nombre y código
                sim = round(max(similitud(origen, nombre),
                                similitud(origen, (catalogo.get(rid) or {}).get("codigo") or "")) * 100)
            grupo.append({fc["mapeo_origen"]: origen[:300], fc["mapeo_nivel"]: opt(nivel),
                          **({fc["mapeo_requerimiento_id"]: rid, fc["mapeo_requerimiento"]: nombre} if rid else {}),
                          **({fc["mapeo_similitud"]: sim} if rid and sim is not None else {})})
        a = dict(rec.get("answers") or {})
        a[fc["mapeo"]] = grupo
        self._ctr_patch(self.CONTRATOS_FORM, str(rec["_id"]), a, "save_mapeo_contrato")
        self.cum_despues_de_contrato(str(rec["_id"]))  # motor ME-15: los homologados se exigen
        return self.get_mapeo_contrato(str(rec["_id"]))

    def crear_en_catalogo(self, requerimiento):
        """Alta en catálogo maestro: nombre canónico, código, nivel y descripción o norma."""
        d = requerimiento if isinstance(requerimiento, dict) else {}
        nombre = " ".join(str(d.get("nombre") or "").split())
        if not nombre:
            self._map_error("El nombre canónico es obligatorio.")
        nivel = d.get("nivel") if d.get("nivel") in NIVELES else None
        if not nivel:
            self._map_error("Nivel: Empresa, Persona o Equipo.")
        codigo = codigo_sistema(d.get("codigo") or nombre)
        if not codigo:
            self._map_error("El código solo admite letras, números y guion bajo.")
        return self.save_requerimiento({"nombre": nombre, "codigo": codigo, "tipo": "Documento", "ambito": nivel,
                                        "vigencia_modo": "vigencia", "vigencia": None,
                                        "descripcion": (d.get("descripcion") or "").strip() or None})
