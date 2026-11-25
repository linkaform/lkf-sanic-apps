# -*- coding: utf-8 -*-
"""Lectura con IA de documentos de Contratistas (F0-11).

Spec: clave10-sdk/specs/contratos/contratos-001-modelo-de-datos.md (Documentos
de cumplimiento, campo lectura_ia). Contrato con el front: AnalisisIA en
clave10/src/types/contratistas/uploader.ts (uploader de F0-10).

- Una sola llamada al modelo por documento (imagen o PDF). El prompt lleva los
  requerimientos activos de la cuenta y los propietarios posibles (la empresa
  activa y sus empleados) para que el modelo elija ids de esas listas.
- El back no confía en los ids del modelo: los valida contra las listas y, si
  no hay id, empata por CURP/RFC exacto o por nombre aproximado.
- Las alertas las calcula el back comparando contra lo guardado (RFC, registro
  patronal, vigencia, periodo ya cubierto, requerimiento esperado).
- No guarda nada: guardar el documento con su lectura_ia es de ME-06-B.
"""
import base64
import re
import unicodedata
from difflib import SequenceMatcher

import requests

from .contratistas_contratos import _fecha, label, opt

MODELO = "google/gemini-3.5-flash"
MAX_TOKENS = 4000
MAX_REQUERIMIENTOS = 200
MAX_EMPLEADOS = 300
MAX_PDF_BYTES = 15 * 1024 * 1024
TIPOS_DOCUMENTO = ["REPSE", "CSF", "Contrato", "Acuse", "Opinión de cumplimiento", "Identificación",
                   "Comprobante", "Otro"]
AMBITOS = ["Empresa", "Persona", "Equipo"]

SYSTEM = (
    "Eres un analista de cumplimiento laboral y fiscal en México (REPSE, SAT, IMSS, INFONAVIT, STPS). "
    "Lees documentos de empresas contratistas y sus empleados y respondes SOLO con un objeto JSON válido, "
    "sin texto adicional. Si un dato no aparece o no es legible, usa null; nunca lo inventes. "
    "Las listas que recibes solo sirven para elegir ids: nunca copies de ellas nombres, RFC ni otros datos "
    "que no leas en el documento. Si no puedes leer con claridad el texto (borroso, cortado, muy pequeño), "
    "responde legible=false."
)

PROMPT = """Analiza el documento adjunto.

Requerimientos de la cuenta (elige el que el documento cumple; usa su id tal cual):
{requerimientos}

Propietarios posibles (empresa y empleados; usa su id solo si el documento los nombra):
{propietarios}
{esperado}
Responde con este JSON:
{{
  "legible": true|false,
  "tipo_documento": uno de {tipos},
  "tipo": "nombre del documento · área, p. ej. 'Constancia de situación fiscal · Fiscal'",
  "confianza": 0-100,
  "nombre_sugerido": "nombre corto para guardar el documento",
  "requerimiento": {{"id": "id de la lista o null", "confianza": 0-100}},
  "propietario": {{"id": "id de la lista o null", "tipo": "Empresa|Persona", "nombre": "...", "rfc": "...",
                   "curp": "...", "confianza": 0-100}},
  "campos": {{
    "vigencia_inicio": "YYYY-MM-DD o null",
    "vigencia_fin": "YYYY-MM-DD o null (fecha de vencimiento o fin de vigencia)",
    "registro": "identificador principal: RFC en una CSF, registro patronal en acuses IMSS/ICSOE/SISUB, folio en REPSE",
    "rfc": "RFC del titular o null",
    "razon_social": "...",
    "registro_patronal": "... o null",
    "periodo": "YYYY-MM (mensual), YYYY-C1..C3 (cuatrimestral), YYYY-B1.., YYYY-T1.., YYYY-S1.., YYYY (anual) o null",
    "en_ceros": true|false
  }},
  "extraccion": {{ solo lo que aplique al tipo:
    REPSE: "folio", "fecha_registro", "fecha_vencimiento", "actividades" (lista);
    CSF: "rfc", "razon_social", "regimen_fiscal", "codigo_postal", "domicilio", "actividades" (lista), "estatus_padron";
    Contrato: "partes" (cliente y contratista con rfc), "objeto", "monto", "inicio", "fin", "numero_contrato";
    Acuse: "plataforma", "folio", "periodo", "registro_patronal", "num_trabajadores", "en_ceros";
    Identificación: "nombre", "curp", "vigencia" }}
}}"""


def _norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return " ".join(sorted(re.sub(r"[^a-z0-9 ]+", " ", s).split()))


def _clave(s):
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def _conf(v):
    try:
        return max(0, min(100, int(round(float(v)))))
    except (TypeError, ValueError):
        return 0


def _iso(v):
    d = _fecha(v)
    return d.isoformat() if d else None


class DocumentosIAMixin:
    """Se mezcla en Accesos (usa self.ai de base y helpers _ctr_* de ContratosMixin)."""

    def _dia_error(self, msg, status=400):
        return self.LKFException({"title": "Lectura con IA", "msg": msg, "status_code": status})

    # ----------------------------------------------------------- contexto

    def _dia_requerimientos(self):
        if not self.REQUERIMIENTOS_FORM:
            return []
        f = self.ctr_f["requerimientos_de_cumplimiento"]
        rows = self._ctr_find(self.REQUERIMIENTOS_FORM, {f"answers.{f['estatus']}": {"$ne": opt("Inactivo")}},
                              limit=MAX_REQUERIMIENTOS)
        return [{"id": str(r["_id"]), "nombre": (r.get("answers") or {}).get(f["nombre"]) or "",
                 "ambito": label(AMBITOS, (r.get("answers") or {}).get(f["ambito"])) or "Empresa"} for r in rows]

    def _dia_empresa(self, empresa_id):
        f = self.ctr_f["empresas"]
        a = (self._ctr_get(self.EMPRESAS_FORM, empresa_id) or {}).get("answers") or {}
        return {"id": empresa_id, "razon_social": a.get(f["razon_social"]) or "", "rfc": a.get(f["rfc"]) or "",
                "nrps": [g.get(f["nrp"]) for g in a.get(f["registros_patronales"]) or [] if g.get(f["nrp"])]}

    def _dia_empleados(self, empresa_id, es_propia):
        emp = getattr(self, "Employee", None)
        if not emp or not getattr(emp, "EMPLEADOS", None):
            return []
        ef, fe = emp.employee_fields, self.ctr_f["empleados"]
        campo = f"answers.{fe['empresa_id']}"
        # Los empleados de la empresa propia muchas veces no tienen empresa_id.
        match = {"$or": [{campo: empresa_id}, {campo: {"$in": [None, ""]}}]} if es_propia else {campo: empresa_id}
        rows = self._ctr_find(emp.EMPLEADOS, match, limit=MAX_EMPLEADOS)
        return [{"id": str(r["_id"]), "nombre": (r.get("answers") or {}).get(ef["worker_name"]) or "",
                 "curp": (r.get("answers") or {}).get(ef["curp"]) or "",
                 "rfc": (r.get("answers") or {}).get(ef["rfc"]) or ""} for r in rows]

    # ------------------------------------------------------------- modelo

    def _dia_llamar(self, archivo, prompt, model):
        url = archivo["file_url"]
        nombre = archivo.get("name") or url.rsplit("/", 1)[-1].split("?")[0]
        es_pdf = nombre.lower().endswith(".pdf") or url.split("?")[0].lower().endswith(".pdf")
        if es_pdf:
            # El proveedor no puede bajar archivos de Backblaze (robots.txt): va en base64.
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            if len(resp.content) > MAX_PDF_BYTES:
                self._dia_error("El PDF pesa más de 15 MB; sube uno más ligero.", 413)
            b64 = base64.b64encode(resp.content).decode()
            parte = {"type": "file", "file": {"filename": nombre, "file_data": f"data:application/pdf;base64,{b64}"}}
        else:
            parte = {"type": "image_url", "image_url": {"url": url}}
        self.ai.headers["X-Title"] = "Clave10: Contratistas documentos"
        raw = self.ai.post(
            messages=[{"role": "system", "content": SYSTEM},
                      {"role": "user", "content": [parte, {"type": "text", "text": prompt}]}],
            model=model or MODELO, max_tokens=MAX_TOKENS, temperature=0,
            # 3.5-flash razona siempre; sin esto gasta los tokens y el JSON llega cortado.
            extra={"reasoning": {"effort": "minimal"}},
        )
        return self.ai._parse_json(raw)["choices"][0]["message"]["content"]

    # ----------------------------------------------------------- empates

    def _dia_propietario(self, p, empresa, empleados):
        """(id, confianza) validados contra la empresa y sus empleados."""
        p = p if isinstance(p, dict) else {}
        ids = {empresa["id"]} | {e["id"] for e in empleados}
        if p.get("id") in ids:
            return p["id"], _conf(p.get("confianza"))
        curp, rfc = _clave(p.get("curp")), _clave(p.get("rfc"))
        if rfc and rfc == _clave(empresa["rfc"]):
            return empresa["id"], 99
        for e in empleados:
            if (curp and curp == _clave(e["curp"])) or (rfc and rfc == _clave(e["rfc"])):
                return e["id"], 99
        nombre = _norm(p.get("nombre"))
        if not nombre:
            return None, 0
        candidatos = [(empresa["id"], empresa["razon_social"])] + [(e["id"], e["nombre"]) for e in empleados]
        mejor, score = None, 0
        for i, n in candidatos:
            s = int(SequenceMatcher(None, nombre, _norm(n)).ratio() * 100)
            if s > score:
                mejor, score = i, s
        return (mejor, score) if score >= 75 else (None, score)

    def _dia_duplicado(self, requerimiento_id, propietario_id, empresa_id, periodo):
        if not (self.DOCUMENTOS_FORM and requerimiento_id and propietario_id):
            return None
        f = self.ctr_f["documentos_de_cumplimiento"]
        match = {f"answers.{f['requerimiento_id']}": requerimiento_id,
                 f"answers.{f['dueno_empresa_id']}": empresa_id}
        if propietario_id != empresa_id:
            match[f"answers.{f['dueno_empleado_id']}"] = propietario_id
        if periodo:
            match[f"answers.{f['periodo_clave']}"] = periodo
        d = self._ctr_find(self.DOCUMENTOS_FORM, match, one=True, sort=[("updated_at", -1)])
        return (d.get("answers") or {}).get(f["folio"]) if d else None

    # ---------------------------------------------------------------- API

    def analizar_documento(self, archivo, requerimiento_id=None, propietario_id=None, model=None):
        """Lee el documento y regresa AnalisisIA (+ extraccion). No guarda nada."""
        if not isinstance(archivo, dict) or not str(archivo.get("file_url") or "").startswith("http"):
            self._dia_error("Falta el archivo (file_url) a analizar.")
        if not self.ai:
            self._dia_error("La IA (OpenRouter) no está configurada en esta cuenta.", 409)
        mi_empresa = self.ctr_empresa_activa_id()
        propia = self.ctr_empresa_propia()
        empresa = self._dia_empresa(mi_empresa)
        empleados = self._dia_empleados(mi_empresa, bool(propia) and str(propia["_id"]) == mi_empresa)
        reqs = self._dia_requerimientos()
        req_por_id = {r["id"]: r for r in reqs}

        esperado = ""
        if requerimiento_id and requerimiento_id in req_por_id:
            esperado += f"\nSe espera que cumpla el requerimiento {requerimiento_id} ({req_por_id[requerimiento_id]['nombre']}).\n"
        if propietario_id:
            esperado += f"Se espera que el propietario sea {propietario_id}.\n"
        prompt = PROMPT.format(
            requerimientos="\n".join(f"- {r['id']}: {r['nombre']} (ámbito {r['ambito']})" for r in reqs) or "- (ninguno)",
            # Sin RFC ni CURP: el back los empata exactos y así el modelo no los copia.
            propietarios="\n".join([f"- {empresa['id']}: {empresa['razon_social']} (Empresa)"]
                                   + [f"- {e['id']}: {e['nombre']} (Persona)" for e in empleados]),
            esperado=esperado, tipos=", ".join(TIPOS_DOCUMENTO))
        try:
            ia = self._dia_llamar(archivo, prompt, model)
        except Exception as e:  # noqa: BLE001
            self._dia_error(f"No se pudo leer el documento con IA: {str(e)[:300]}", 502)
        ia = ia if isinstance(ia, dict) else {}

        legible = bool(ia.get("legible"))
        campos_ia = ia.get("campos") if isinstance(ia.get("campos"), dict) else {}
        req_id = (ia.get("requerimiento") or {}).get("id") if isinstance(ia.get("requerimiento"), dict) else None
        req_conf = _conf((ia.get("requerimiento") or {}).get("confianza")) if req_id in req_por_id else 0
        req_id = req_id if req_id in req_por_id else None
        prop_id, prop_conf = self._dia_propietario(ia.get("propietario"), empresa, empleados)
        campos = {k: v for k, v in {
            "vigencia_inicio": _iso(campos_ia.get("vigencia_inicio")),
            "vigencia_fin": _iso(campos_ia.get("vigencia_fin")),
            "registro": campos_ia.get("registro") or None,
            "rfc": campos_ia.get("rfc") or None,
            "razon_social": campos_ia.get("razon_social") or None,
            "registro_patronal": campos_ia.get("registro_patronal") or None,
            "periodo": campos_ia.get("periodo") or None,
            "en_ceros": bool(campos_ia.get("en_ceros")) or None,
        }.items() if v is not None}

        alertas = []
        if not legible:
            alertas.append({"nivel": "error", "titulo": "No pudimos leer el documento",
                            "detalle": "La imagen está borrosa, cortada o tiene baja resolución. Captura los datos "
                                       "manualmente o sube un archivo más nítido.",
                            "accion": {"tipo": "otro_archivo", "etiqueta": "Subir otro archivo"}})
        else:
            hoy = self._ctr_hoy().isoformat()
            if requerimiento_id and req_id and req_id != requerimiento_id and requerimiento_id in req_por_id:
                alertas.append({"nivel": "aviso", "titulo": "El documento no parece ser el que se pide",
                                "detalle": f"Se esperaba {req_por_id[requerimiento_id]['nombre']} y el documento "
                                           f"parece ser {req_por_id[req_id]['nombre']}."})
            rfc_doc = _clave(campos.get("rfc"))
            # Documento de empresa (no de un empleado) con RFC distinto al de mi empresa.
            if rfc_doc and empresa["rfc"] and prop_id in (None, empresa["id"]) and rfc_doc != _clave(empresa["rfc"]) \
                    and not any(rfc_doc == _clave(e["rfc"]) for e in empleados):
                alertas.append({"nivel": "error", "titulo": "El RFC no coincide",
                                "detalle": f"El documento es del RFC {campos['rfc']} y tu empresa tiene {empresa['rfc']}."})
            nrp = _clave(campos.get("registro_patronal"))
            if nrp and empresa["nrps"] and nrp not in {_clave(x) for x in empresa["nrps"]}:
                cercano = max(empresa["nrps"], key=lambda x: SequenceMatcher(None, nrp, _clave(x)).ratio())
                alerta = {"nivel": "error", "titulo": "El registro patronal no coincide",
                          "detalle": f"El documento declara {campos['registro_patronal']} y tu empresa tiene "
                                     f"dado de alta {', '.join(empresa['nrps'])}."}
                if SequenceMatcher(None, nrp, _clave(cercano)).ratio() >= 0.8:
                    alerta["accion"] = {"tipo": "usar_valor", "etiqueta": f"Usar {cercano}", "campo": "registro",
                                        "valor": cercano}
                alertas.append(alerta)
            if campos.get("vigencia_fin") and campos["vigencia_fin"] < hoy:
                alertas.append({"nivel": "error", "titulo": "El documento ya venció",
                                "detalle": f"Su vigencia terminó el {campos['vigencia_fin']}. Sube uno vigente."})
            dup = self._dia_duplicado(req_id, prop_id, mi_empresa, campos.get("periodo"))
            if dup:
                alertas.append({"nivel": "aviso", "titulo": "Ya hay un documento para este requerimiento",
                                "detalle": f"El documento {dup} ya cubre este requerimiento"
                                           f"{' en el periodo ' + campos['periodo'] if campos.get('periodo') else ''}. "
                                           "Puedes reemplazarlo o conservar ambos."})

        tipo_doc = label(TIPOS_DOCUMENTO, ia.get("tipo_documento")) or ia.get("tipo_documento")
        return {
            "legible": legible,
            "tipo": (ia.get("tipo") or None) if legible else None,
            "tipo_documento": tipo_doc if legible else None,
            "confianza": _conf(ia.get("confianza")) if legible else 0,
            "nombre_sugerido": (ia.get("nombre_sugerido") or "") if legible else "",
            "mapeo": {"id": req_id, "confianza": req_conf},
            "propietario": {"id": prop_id, "confianza": prop_conf},
            "campos": campos,
            "alertas": alertas,
            "extraccion": ia.get("extraccion") if isinstance(ia.get("extraccion"), dict) and legible else {},
        }
