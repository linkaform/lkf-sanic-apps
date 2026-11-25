# -*- coding: utf-8 -*-
"""Cumplimiento documental de Mi Empresa (ME-07-B).

Spec: clave10-sdk/specs/contratos/contratos-001-modelo-de-datos.md (las
obligaciones son requerimientos de ámbito Empresa; el acuse es un documento
con periodo y en_ceros). Ficha: contratistas_me07_cumplimiento.md.

- Filas = requerimientos activos de ámbito Empresa que algún cliente le exige a
  la empresa activa (filas del motor ME-15) más los que requieren acuse.
- Pestañas por periodicidad (Mensuales … Anuales), "Por vigencia" (un solo
  documento con vigencia) y "Sin vencimiento".
- Celda = estatus global del documento de la empresa para ese periodo (regla
  de MX-02): Aceptado (En ceros si es acuse en ceros), Por revisar, Rechazado,
  Vencido. Sin documento: "Por subir" hasta su fecha límite, luego
  "No entregado". Periodos futuros = null. "No aplica" si todos los clientes
  que lo exigen lo marcaron así en el motor.
- % = Aceptado + En ceros entre las celdas que cuentan (no cuentan null,
  No aplica ni Por subir de periodos; en "Por vigencia" Por subir sí cuenta);
  null si no hay ninguna que cuente.
- Subir acuse: reemplaza el del periodo si ya hay (versión nueva, aprobaciones
  a Pendiente) o da de alta uno nuevo; en ceros solo en cuatrimestrales.
- Generar cumplimiento: ZIP con CSV de contratos y trabajadores del periodo
  (ICSOE / SISUB); en ceros o sin contratos = "SIN INFORMACION".
- Descargar cumplimiento: ZIP con los archivos del ejercicio + resumen .xlsx.
"""
import csv
import io
import os
import re
import tempfile
import unicodedata
import zipfile
from datetime import date

from dateutil.relativedelta import relativedelta

from .contratistas_contratos import _fecha, _int, label, opt
from .contratistas_cumplimiento import ESTADOS, ESTADOS_MANUALES, periodos

PESTANAS_PERIODO = {"Mensual": "Mensuales", "Bimestral": "Bimestrales", "Trimestral": "Trimestrales",
                    "Cuatrimestral": "Cuatrimestrales", "Semestral": "Semestrales", "Anual": "Anuales"}
PESTANAS = list(PESTANAS_PERIODO.values()) + ["Por vigencia", "Sin vencimiento"]
CUMPLE = ("Aceptado", "En ceros")
PENDIENTES = ("Por subir", "No entregado", "Rechazado", "Vencido")
SIN_INFO = "SIN INFORMACION"
MAX_ARCHIVOS = 300


def _slug(s, n=40):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_")[:n] or "x"


def _pct(estados, cuenta_por_subir=False):
    fuera = (None, "No aplica") if cuenta_por_subir else (None, "No aplica", "Por subir")
    aplicables = [e for e in estados if e not in fuera]
    if not aplicables:
        return None  # nada que cuente todavía: el front muestra "—"
    return round(sum(1 for e in aplicables if e in CUMPLE) * 100 / len(aplicables))


class CumplimientoDocumentalMixin:
    """Se mezcla en Accesos junto con DocumentosMixin, CumplimientoMixin y RequerimientosMixin."""

    def _cd_error(self, msg, status=400):
        return self.LKFException({"title": "Cumplimiento documental", "msg": msg, "status_code": status})

    # ----------------------------------------------------------- datos

    def _cd_contexto(self, mi_empresa):
        """Requerimientos que aplican, documentos de la empresa y No aplica del motor."""
        fq = self.ctr_f["requerimientos_de_cumplimiento"]
        fd = self.ctr_f["documentos_de_cumplimiento"]
        fcu = self.ctr_f["cumplimiento_de_requerimientos"]
        motor = self._ctr_find(self.CUMPLIMIENTO_FORM, {
            f"answers.{fcu['sujeto_empresa_id']}": mi_empresa,
            f"answers.{fcu['sujeto_tipo']}": opt("Empresa")}) if self.CUMPLIMIENTO_FORM else []
        exigidos = {str((m.get("answers") or {}).get(fcu["requerimiento_id"]) or "") for m in motor}
        manual = {}
        for m in motor:
            a = m.get("answers") or {}
            k = (str(a.get(fcu["requerimiento_id"]) or ""), a.get(fcu["periodo_clave"]) or "unico")
            manual.setdefault(k, []).append(label(ESTADOS_MANUALES, a.get(fcu["estado_manual"])))
        no_aplica = {k for k, v in manual.items() if v and all(x == "No aplica" for x in v)}
        reqs = []
        if self.REQUERIMIENTOS_FORM:
            cache = {}
            for r in self._ctr_find(self.REQUERIMIENTOS_FORM, {f"answers.{fq['ambito']}": opt("Empresa"),
                                                               f"answers.{fq['estatus']}": {"$ne": opt("Inactivo")}}):
                out = self.req_out(r)
                if out["id"] not in exigidos and not out["requiere_acuse"]:
                    continue
                norm = self._cum_requerimiento(out["id"], cache)
                if norm:
                    reqs.append((out, norm))
        reqs.sort(key=lambda x: x[0]["nombre"].lower())
        docs = {}
        if self.DOCUMENTOS_FORM:
            for d in self._ctr_find(self.DOCUMENTOS_FORM, {f"answers.{fd['dueno_empresa_id']}": mi_empresa,
                                                           f"answers.{fd['dueno_tipo']}": opt("Empresa")},
                                    sort=[("updated_at", -1)]):
                a = d.get("answers") or {}
                k = (str(a.get(fd["requerimiento_id"]) or ""), a.get(fd["periodo_clave"]) or "unico")
                docs.setdefault(k, d)  # el más reciente
        return reqs, docs, no_aplica

    @staticmethod
    def _cd_pestana(norm, out):
        if norm["vigencia_modo"] == "Periodo" and norm["periodicidad"] in PESTANAS_PERIODO:
            return PESTANAS_PERIODO[norm["periodicidad"]]
        return "Por vigencia" if out.get("vigencia") or norm["periodicidad"] in ("Cada 3 años", "Cada 10 años") \
            else "Sin vencimiento"

    def _cd_doc_estado(self, doc):
        fd = self.ctr_f["documentos_de_cumplimiento"]
        a = doc.get("answers") or {}
        e = self._doc_estatus(a)
        return "En ceros" if e == "Aceptado" and a.get(fd["en_ceros"]) == opt("Sí") else e

    def _cd_doc_ref(self, doc):
        fd = self.ctr_f["documentos_de_cumplimiento"]
        a = doc.get("answers") or {}
        return {"id": str(doc["_id"]), "folio": a.get(fd["folio"]) or "",
                "archivo": self._ctr_archivo(a.get(fd["archivo"])) or {"name": "", "file_url": ""},
                "en_ceros": a.get(fd["en_ceros"]) == opt("Sí"),
                "vigencia_inicio": a.get(fd["vigencia_inicio"]) or None, "vigencia_fin": a.get(fd["vigencia_fin"]) or None}

    def _cd_celda(self, req_id, p, docs, no_aplica, hoy):
        if p["inicio"] > hoy:
            return {"clave": p["clave"], "estado": None, "documento": None}
        doc = docs.get((req_id, p["clave"]))
        if doc:
            estado, ref = self._cd_doc_estado(doc), self._cd_doc_ref(doc)
        else:
            estado, ref = ("No entregado" if p["vence"] < hoy else "Por subir"), None
        if (req_id, p["clave"]) in no_aplica:
            estado = "No aplica"
        return {"clave": p["clave"], "estado": estado, "documento": ref}

    def _cd_matriz(self, mi_empresa, anio):
        reqs, docs, no_aplica = self._cd_contexto(mi_empresa)
        hoy = self._ctr_hoy().isoformat()
        ini, fin = date(anio, 1, 1), date(anio, 12, 31)
        pestanas = {}
        for out, norm in reqs:
            nombre = self._cd_pestana(norm, out)
            t = pestanas.setdefault(nombre, {"pestana": nombre, "columnas": None, "filas": []})
            req = {k: out.get(k) for k in ("id", "nombre", "descripcion", "tipo", "plataforma", "plataforma_url",
                                           "periodicidad", "vigencia", "requiere_acuse", "limitante")}
            if nombre in PESTANAS_PERIODO.values():
                ps = periodos(norm, anio, ini, fin)
                if t["columnas"] is None:
                    t["columnas"] = [{k: p[k] for k in ("clave", "inicio", "fin")} for p in ps]
                celdas = [{**self._cd_celda(out["id"], p, docs, no_aplica, hoy), "vence": p["vence"]} for p in ps]
                t["filas"].append({"requerimiento": req, "celdas": celdas,
                                   "cumplimiento_pct": _pct([c["estado"] for c in celdas])})
            else:
                doc = docs.get((out["id"], "unico"))
                estado = self._cd_doc_estado(doc) if doc else "Por subir"
                if (out["id"], "unico") in no_aplica:
                    estado = "No aplica"
                fila = {"requerimiento": req, "estado": estado, "documento": self.doc_out(doc, mi_empresa) if doc else None}
                t["filas"].append(fila)
        res = []
        for nombre in PESTANAS:
            t = pestanas.get(nombre)
            if not t:
                continue
            if t["columnas"] is not None:
                t["pie"] = [_pct([f["celdas"][i]["estado"] for f in t["filas"]]) for i in range(len(t["columnas"]))]
                estados = [c["estado"] for f in t["filas"] for c in f["celdas"]]
                t["cumplimiento_pct"] = _pct(estados)
            else:
                t.pop("columnas")
                estados = [f["estado"] for f in t["filas"]]
                t["cumplimiento_pct"] = _pct(estados, cuenta_por_subir=True)
            t["pendientes"] = sum(1 for e in estados if e in PENDIENTES)
            res.append(t)
        return res

    # ------------------------------------------------------------- API

    def get_cumplimiento_documental(self, anio=None):
        """Matriz obligación × periodo (y vistas por vigencia) de la empresa activa."""
        anio = _int(anio, self._ctr_hoy().year)
        if not 2000 <= anio <= 2100:
            self._cd_error("Ejercicio no válido.")
        mi_empresa = self.ctr_empresa_activa_id()
        return {"anio": anio, "hoy": self._ctr_hoy().isoformat(), "pestanas": self._cd_matriz(mi_empresa, anio)}

    def _cd_req_periodo(self, requerimiento_id, periodo_clave):
        """(req_out, norm, periodo) validados para un requerimiento por periodo."""
        rec = self._ctr_get(self.REQUERIMIENTOS_FORM, str(requerimiento_id or "")) if self.REQUERIMIENTOS_FORM else None
        norm = self._cum_requerimiento(str(rec["_id"]), {}) if rec else None
        if not norm:
            self._cd_error("El requerimiento no existe o está inactivo.", 404)
        out = self.req_out(rec)
        if norm["ambito"] != "Empresa":
            self._cd_error("Solo los requerimientos de ámbito Empresa van en el cumplimiento documental.")
        clave = str(periodo_clave or "unico")
        if clave == "unico":
            return out, norm, {"clave": "unico", "inicio": "", "fin": "", "vence": ""}
        if not re.match(r"^\d{4}", clave):
            self._cd_error(f"Periodo no válido: {clave}.")
        anio = int(clave[:4])
        p = next((x for x in periodos(norm, anio, date(anio, 1, 1), date(anio, 12, 31)) if x["clave"] == clave), None)
        if not p:
            self._cd_error(f"El periodo {clave} no corresponde a la periodicidad de {out['nombre']}.")
        return out, norm, p

    def get_periodo_cumplimiento(self, requerimiento_id, periodo_clave=None):
        """Detalle del periodo: obligación (con su nota), periodo, estado y acuse."""
        out, norm, p = self._cd_req_periodo(requerimiento_id, periodo_clave)
        mi_empresa = self.ctr_empresa_activa_id()
        _, docs, no_aplica = self._cd_contexto(mi_empresa)
        hoy = self._ctr_hoy().isoformat()
        doc = docs.get((out["id"], p["clave"]))
        if p["clave"] == "unico":
            estado = self._cd_doc_estado(doc) if doc else "Por subir"
            estado = "No aplica" if (out["id"], "unico") in no_aplica else estado
        else:
            estado = self._cd_celda(out["id"], p, docs, no_aplica, hoy)["estado"]
        return {"requerimiento": out, "periodo": p, "estado": estado,
                "documento": self.doc_out(doc, mi_empresa) if doc else None}

    def subir_acuse(self, acuse):
        """Alta o reemplazo del documento de un periodo (o del único)."""
        self._doc_requiere_forma()
        x = acuse if isinstance(acuse, dict) else {}
        out, norm, p = self._cd_req_periodo(x.get("requerimiento_id"), x.get("periodo_clave"))
        fecha = _fecha(x.get("fecha"))
        if not fecha:
            self._cd_error("La fecha (emisión o presentación) es obligatoria, YYYY-MM-DD.")
        en_ceros = bool(x.get("en_ceros"))
        if en_ceros and norm["periodicidad"] != "Cuatrimestral":
            self._cd_error("La declaración en ceros solo aplica a obligaciones cuatrimestrales.")
        vig = out.get("vigencia") or {}
        unidad = {"días": "days", "meses": "months", "años": "years"}.get(vig.get("unidad"))
        vence = (fecha + relativedelta(**{unidad: _int(vig.get("n"), 0)})).isoformat() if vig.get("n") and unidad else ""
        mi_empresa = self.ctr_empresa_activa_id()
        _, docs, _ = self._cd_contexto(mi_empresa)
        previo = docs.get((out["id"], p["clave"]))
        datos = {"archivo": x.get("archivo"), "vigencia_inicio": fecha.isoformat(), "vigencia_fin": vence,
                 "en_ceros": en_ceros}
        if x.get("lectura_ia") is not None:
            datos["lectura_ia"] = x["lectura_ia"]
        if p["clave"] != "unico":
            datos["periodo"] = {k: p[k] for k in ("clave", "inicio", "fin")}
        if previo:
            doc = self.upload_documento({**datos, "reemplaza_id": str(previo["_id"])})
        else:
            nombre = f"{out['nombre']} {p['clave']}" if p["clave"] != "unico" else out["nombre"]
            nuevo = {**datos, "nombre": nombre, "categoria": "Acuse" if out.get("requiere_acuse") else None,
                     "requerimiento_id": out["id"], "dueno": {"tipo": "Empresa", "empresa_id": mi_empresa}}
            if x.get("compartido_con") is not None:
                nuevo["compartido_con"] = x["compartido_con"]
            doc = self.upload_documento({k: v for k, v in nuevo.items() if v is not None})
        return {"documento": doc, "reemplazado": bool(previo)}

    # ---------------------------------------------------------- archivos

    def _cd_subir_zip(self, nombre, contenido):
        """Sube el ZIP al campo archivo de Documentos y regresa {name, file_url}."""
        ruta = os.path.join(tempfile.gettempdir(), nombre)
        with open(ruta, "wb") as fh:
            fh.write(contenido)
        try:
            with open(ruta, "rb") as fh:
                res = self.lkf_api.post_upload_file(
                    data={"form_id": self.DOCUMENTOS_FORM, "field_id": self.ctr_f["documentos_de_cumplimiento"]["archivo"]},
                    up_file={"File": fh})
            url = ((res or {}).get("data") or {}).get("file")
        finally:
            os.remove(ruta)
        if not url:
            self._cd_error(f"No se pudo subir el archivo: {str(res)[:200]}", 502)
        return {"name": nombre, "file_url": url}

    @staticmethod
    def _cd_csv(encabezado, filas):
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(encabezado)
        if filas:
            w.writerows(filas)
        else:
            w.writerow([SIN_INFO] + [""] * (len(encabezado) - 1))
        return buf.getvalue().encode("utf-8-sig")

    def generar_cumplimiento(self, requerimiento_id, periodo_clave):
        """ZIP con contratos y trabajadores del periodo para la plataforma (ICSOE / SISUB)."""
        self._doc_requiere_forma()
        out, norm, p = self._cd_req_periodo(requerimiento_id, periodo_clave)
        if p["clave"] == "unico":
            self._cd_error("Generar cumplimiento es por periodo.")
        mi_empresa = self.ctr_empresa_activa_id()
        empresa = self._ctr_empresa_ref(mi_empresa, {})
        _, docs, _ = self._cd_contexto(mi_empresa)
        doc = docs.get((out["id"], p["clave"]))
        en_ceros = bool(doc) and (doc.get("answers") or {}).get(
            self.ctr_f["documentos_de_cumplimiento"]["en_ceros"]) == opt("Sí")
        fc = self.ctr_f["contratos_de_servicio"]
        contratos, trabajadores = [], []
        if not en_ceros and self.CONTRATOS_FORM:
            emp = self.Employee
            ef = emp.employee_fields
            for c in self._ctr_find(self.CONTRATOS_FORM, {f"answers.{fc['contratista_id']}": mi_empresa},
                                    sort=[("created_at", 1)]):
                a = c.get("answers") or {}
                if a.get(fc["estatus"]) == opt("Cancelado"):
                    continue
                ini, fin = str(a.get(fc["inicio"]) or "")[:10], str(a.get(fc["fin"]) or "")[:10]
                if (ini and ini > p["fin"]) or (fin and fin < p["inicio"]):
                    continue
                cliente = self._ctr_empresa_ref(str(a.get(fc["cliente_id"]) or ""), {})
                contratos.append([a.get(fc["folio"]) or "", a.get(fc["numero_contrato"]) or "", cliente.get("rfc") or "",
                                  cliente.get("razon_social") or "", a.get(fc["objeto"]) or "", ini, fin,
                                  a.get(fc["monto"]) or "", label(["Activo", "Por vencer", "En documentación", "Vencido",
                                                                   "Pausado", "Cancelado"], a.get(fc["estatus"])) or ""])
                for g in a.get(fc["empleados"]) or []:
                    alta = str(g.get(fc["empleado_fecha_alta"]) or "")[:10]
                    if alta and alta > p["fin"]:
                        continue
                    e = (self._ctr_get(emp.EMPLEADOS, str(g.get(fc["empleado_id"]) or "")) or {}).get("answers") or {}
                    trabajadores.append([a.get(fc["folio"]) or "", g.get(fc["empleado"]) or e.get(ef["worker_name"]) or "",
                                         e.get(ef["curp"]) or "", e.get(ef["rfc"]) or "", e.get(ef["nss"]) or "",
                                         g.get(fc["empleado_perfil"]) or "", alta])
        tag = _slug(out["nombre"], 12).upper().replace("_", "")
        rfc = _slug(empresa.get("rfc") or mi_empresa, 20).upper()
        base = f"{tag}_{rfc}_{p['clave']}"
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{tag}_contratos_{rfc}_{p['clave']}.csv", self._cd_csv(
                ["folio", "numero_contrato", "rfc_cliente", "cliente", "objeto", "inicio", "fin", "monto", "estatus"],
                contratos))
            z.writestr(f"{tag}_trabajadores_{rfc}_{p['clave']}.csv", self._cd_csv(
                ["contrato", "nombre", "curp", "rfc", "nss", "perfil", "fecha_alta"], trabajadores))
        archivo = self._cd_subir_zip(f"{base}.zip", zbuf.getvalue())
        return {"archivo": archivo, "en_ceros": en_ceros, "contratos": len(contratos), "trabajadores": len(trabajadores),
                "plataforma": out.get("plataforma"), "plataforma_url": out.get("plataforma_url")}

    def descargar_cumplimiento(self, anio=None, pestanas=None):
        """ZIP con los archivos del ejercicio (pestañas elegidas) y un resumen .xlsx."""
        import requests
        from openpyxl import Workbook

        self._doc_requiere_forma()
        anio = _int(anio, self._ctr_hoy().year)
        mi_empresa = self.ctr_empresa_activa_id()
        tabs = self._cd_matriz(mi_empresa, anio)
        if pestanas:
            pestanas = [pestanas] if isinstance(pestanas, str) else pestanas
            malas = [x for x in pestanas if x not in PESTANAS]
            if malas:
                self._cd_error(f"Pestaña no válida: {', '.join(malas)}.")
            tabs = [t for t in tabs if t["pestana"] in pestanas]
        wb = Workbook()
        wb.remove(wb.active)
        archivos = []
        for t in tabs:
            ws = wb.create_sheet(t["pestana"][:31])
            if "columnas" in t:
                ws.append(["Obligación"] + [c["clave"] for c in t["columnas"]] + ["% cumplimiento"])
                for f in t["filas"]:
                    ws.append([f["requerimiento"]["nombre"]] + [c["estado"] or "" for c in f["celdas"]]
                              + [f["cumplimiento_pct"]])
                    archivos += [(t["pestana"], f["requerimiento"]["nombre"], c["clave"], c["documento"]["archivo"])
                                 for c in f["celdas"] if c.get("documento") and c["documento"]["archivo"].get("file_url")]
                ws.append(["% por periodo"] + t["pie"] + [t["cumplimiento_pct"]])
            else:
                ws.append(["Requerimiento", "Estado", "Vigencia inicio", "Vigencia fin", "Folio"])
                for f in t["filas"]:
                    d = f.get("documento") or {}
                    ws.append([f["requerimiento"]["nombre"], f["estado"], d.get("vigencia_inicio") or "",
                               d.get("vigencia_fin") or "", d.get("folio") or ""])
                    if (d.get("archivo") or {}).get("file_url"):
                        archivos.append((t["pestana"], f["requerimiento"]["nombre"], "vigente", d["archivo"]))
        if not tabs:
            wb.create_sheet("Sin datos").append(["No hay obligaciones para este ejercicio."])
        if len(archivos) > MAX_ARCHIVOS:
            self._cd_error(f"Son {len(archivos)} archivos; elige menos periodicidades (máximo {MAX_ARCHIVOS}).")
        xbuf = io.BytesIO()
        wb.save(xbuf)
        omitidos = []
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"resumen_cumplimiento_{anio}.xlsx", xbuf.getvalue())
            for pestana, req, clave, arch in archivos:
                nombre_arch = arch.get("name") or arch["file_url"].rsplit("/", 1)[-1]
                base, ext = os.path.splitext(nombre_arch)
                ruta = f"{_slug(pestana)}/{_slug(req)}/{clave}_{_slug(base, 80)}{('.' + _slug(ext[1:], 10)) if ext else ''}"
                try:
                    r = requests.get(arch["file_url"], timeout=30)
                    r.raise_for_status()
                    z.writestr(ruta, r.content)
                except Exception:  # noqa: BLE001
                    omitidos.append({"requerimiento": req, "periodo": clave, "archivo": nombre_arch})
        empresa = self._ctr_empresa_ref(mi_empresa, {})
        archivo = self._cd_subir_zip(f"cumplimiento_{_slug(empresa.get('rfc') or mi_empresa, 20)}_{anio}.zip",
                                     zbuf.getvalue())
        return {"archivo": archivo, "documentos": len(archivos) - len(omitidos), "omitidos": omitidos}

    # ------------------------------------------------------------ panel

    def get_resumen_cumplimiento(self, limit=50):
        """Panel lateral de Generales: anillo (Empresa, Empleados, Acuses del año) y pendientes."""
        mi_empresa = self.ctr_empresa_activa_id()
        anio = self._ctr_hoy().year
        tabs = self._cd_matriz(mi_empresa, anio)
        empresa, acuses, pendientes = [], [], []
        for t in tabs:
            for f in t["filas"]:
                r = f["requerimiento"]
                destino = acuses if r.get("requiere_acuse") else empresa
                if "celdas" in f:
                    destino += [c["estado"] for c in f["celdas"]]
                    for c in f["celdas"]:
                        if c["estado"] in PENDIENTES:
                            pendientes.append({"requerimiento": {"id": r["id"], "nombre": r["nombre"]},
                                               "requiere_acuse": bool(r.get("requiere_acuse")), "periodo": c["clave"],
                                               "vence": c["vence"], "estado": c["estado"]})
                else:
                    # Sin fecha límite: un "Por subir" por vigencia sí cuenta como pendiente.
                    destino.append(f["estado"] if f["estado"] != "Por subir" else "No entregado")
                    if f["estado"] in PENDIENTES:
                        pendientes.append({"requerimiento": {"id": r["id"], "nombre": r["nombre"]},
                                           "requiere_acuse": bool(r.get("requiere_acuse")), "periodo": None,
                                           "vence": (f.get("documento") or {}).get("vigencia_fin"), "estado": f["estado"]})
        fcu = self.ctr_f["cumplimiento_de_requerimientos"]
        emp_estados = []
        if self.CUMPLIMIENTO_FORM:
            for m in self._ctr_find(self.CUMPLIMIENTO_FORM, {f"answers.{fcu['sujeto_empresa_id']}": mi_empresa,
                                                             f"answers.{fcu['sujeto_tipo']}": opt("Persona")}):
                a = m.get("answers") or {}
                emp_estados.append(label(ESTADOS_MANUALES, a.get(fcu["estado_manual"]))
                                   or label(ESTADOS, a.get(fcu["estado"])) or "En plazo")
        from .contratistas_cumplimiento import porcentaje
        orden = {"No entregado": 0, "Rechazado": 1, "Vencido": 2, "Por subir": 3}
        pendientes.sort(key=lambda x: (orden.get(x["estado"], 9), x["vence"] or "9999"))
        lim = max(1, min(_int(limit, 50), 200))
        return {
            "anio": anio,
            "empresa_pct": _pct(empresa),
            "empleados_pct": porcentaje(emp_estados),
            "acuses_pct": _pct(acuses),
            "pendientes": pendientes[:lim],
            "total_pendientes": len(pendientes),
        }
