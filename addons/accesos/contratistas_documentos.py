# -*- coding: utf-8 -*-
"""Documentos de cumplimiento de Contratistas (ME-06-B).

Spec: clave10-sdk/specs/contratos/contratos-001-modelo-de-datos.md (forma
Documentos de cumplimiento). Contrato con el front: Documento / DocumentoInput /
RevisionDocumento en clave10/src/types/contratistas/contratos.ts.

- Con E = empresa activa: E ve sus propios documentos (dueño) y los que le
  compartieron (E está en compartido_con, como cliente).
- Solo el dueño sube y reemplaza; solo un cliente de compartido_con aprueba o
  rechaza (rechazar exige motivo) y cada cliente decide lo suyo.
- Reemplazar agrega una versión y regresa todas las aprobaciones a Pendiente;
  "conservar ambos" es otra alta normal.
- Estatus: Rechazado si algún cliente rechazó; Aceptado si todos aprobaron;
  si no, Por revisar. Vencido gana sobre Aceptado con vigencia_fin < hoy.
- Sin compartido_con explícito se comparte con todos los clientes activos de E.
- MX-02: todo cliente de compartido_con debe aprobar (una fila en aprobaciones
  por cliente). Cualquiera que vea el documento ve todas las decisiones, el
  resumen "N de M" y, si es cliente, su propia decisión (mi_decision). El
  dueño cambia compartido_con con update_compartido_documento: cliente nuevo
  entra Pendiente, el que sale pierde su decisión.
- Cada alta, reemplazo y revisión recalcula el cumplimiento (motor ME-15) de
  las relaciones afectadas.
"""
import re
from datetime import datetime

import pytz
import simplejson

from .contratistas_contratos import _fecha, _int, label, opt

AMBITOS = ["Empresa", "Persona", "Equipo"]
ESTATUS_DOC = ["Por revisar", "Aceptado", "Rechazado", "Vencido"]
DECISIONES = ["Pendiente", "Aprobado", "Rechazado"]
ORIGENES = ["Carga", "Carga masiva", "Sesión"]
MAX_COMENTARIO = 2000


class DocumentosMixin:
    """Se mezcla en Accesos junto con ContratosMixin y CumplimientoMixin."""

    def _doc_error(self, msg, status=400):
        return self.LKFException({"title": "Documentos", "msg": msg, "status_code": status})

    def _doc_requiere_forma(self):
        if not self.DOCUMENTOS_FORM:
            self._doc_error("La forma Documentos de cumplimiento no está instalada en esta cuenta.", 409)

    def _doc_ahora(self):
        tz = (self.user or {}).get("timezone") or "America/Mexico_City"
        try:
            return datetime.now(pytz.timezone(tz)).strftime("%Y-%m-%d %H:%M:%S")
        except pytz.UnknownTimeZoneError:
            return datetime.now(pytz.timezone("America/Mexico_City")).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _doc_file(archivo):
        if not isinstance(archivo, dict) or not str(archivo.get("file_url") or "").startswith("http"):
            return None
        return [{"file_name": archivo.get("name") or archivo["file_url"].rsplit("/", 1)[-1],
                 "file_url": archivo["file_url"]}]

    # ------------------------------------------------------------ estatus

    def _doc_estatus(self, a):
        f = self.ctr_f["documentos_de_cumplimiento"]
        decisiones = [label(DECISIONES, x.get(f["aprobacion_decision"])) for x in a.get(f["aprobaciones"]) or []]
        if "Rechazado" in decisiones:
            return "Rechazado"
        if decisiones and all(d == "Aprobado" for d in decisiones):
            fin = a.get(f["vigencia_fin"])
            if fin and str(fin)[:10] < self._ctr_hoy().isoformat():
                return "Vencido"
            return "Aceptado"
        return "Por revisar"

    # -------------------------------------------------------------- salida

    def doc_out(self, rec, mi_empresa=None):
        f = self.ctr_f["documentos_de_cumplimiento"]
        a = rec.get("answers") or {}

        def ref(k_id, k):
            return {"id": str(a.get(f[k_id])), "nombre": a.get(f[k]) or ""} if a.get(f[k_id]) else None

        def reflist(g, k_id, k_n):
            return [{"id": str(x.get(f[k_id]) or ""), "nombre": x.get(f[k_n]) or ""} for x in a.get(f[g]) or []]

        dueno = {"tipo": label(AMBITOS, a.get(f["dueno_tipo"])) or "Empresa",
                 "empresa": ref("dueno_empresa_id", "dueno_empresa") or {"id": "", "nombre": ""}}
        if ref("dueno_empleado_id", "dueno_empleado"):
            dueno["empleado"] = ref("dueno_empleado_id", "dueno_empleado")
        if ref("dueno_equipo_id", "dueno_equipo"):
            dueno["equipo"] = ref("dueno_equipo_id", "dueno_equipo")
        try:
            lectura = simplejson.loads(a[f["lectura_ia"]]) if a.get(f["lectura_ia"]) else None
        except (ValueError, TypeError):
            lectura = None
        out = {
            "id": str(rec["_id"]),
            "folio": a.get(f["folio"]) or "",
            "nombre": a.get(f["nombre"]) or "",
            "categoria": a.get(f["categoria"]) or None,
            "requerimiento": ref("requerimiento_id", "requerimiento"),
            "dueno": dueno,
            "en_ceros": a.get(f["en_ceros"]) == opt("Sí"),
            "vigencia_inicio": a.get(f["vigencia_inicio"]) or None,
            "vigencia_fin": a.get(f["vigencia_fin"]) or None,
            "archivo": self._ctr_archivo(a.get(f["archivo"])) or {"name": "", "file_url": ""},
            # Se calcula al leer: Vencido depende de la fecha de hoy.
            "estatus": self._doc_estatus(a),
            "compartido_con": reflist("compartido_con", "compartido_con_id", "compartido_con_nombre"),
            "contratos": reflist("contratos", "contratos_id", "contratos_nombre"),
            "origen": label(ORIGENES, a.get(f["origen"])) or "Carga",
            "versiones": [{
                "numero": _int(v.get(f["version_numero"]), i + 1),
                "archivo": self._ctr_archivo(v.get(f["version_archivo"])) or {"name": "", "file_url": ""},
                "estatus": label(ESTATUS_DOC, v.get(f["version_estatus"])) or "Por revisar",
                "subido_por": v.get(f["version_subido_por"]) or "",
                "fecha": v.get(f["version_fecha"]) or "",
                **({"motivo_rechazo": v[f["version_motivo_rechazo"]]} if v.get(f["version_motivo_rechazo"]) else {}),
            } for i, v in enumerate(a.get(f["versiones"]) or [])],
            "comentarios": [{"autor": c.get(f["comentario_autor"]) or "", "fecha": c.get(f["comentario_fecha"]) or "",
                             "texto": c.get(f["comentario_texto"]) or ""} for c in a.get(f["comentarios"]) or []],
            "aprobaciones": [{
                "cliente": {"id": str(x.get(f["aprobacion_cliente_id"]) or ""), "nombre": x.get(f["aprobacion_cliente"]) or ""},
                "decision": label(DECISIONES, x.get(f["aprobacion_decision"])) or "Pendiente",
                **({"revisor": x[f["aprobacion_revisor"]]} if x.get(f["aprobacion_revisor"]) else {}),
                **({"fecha": x[f["aprobacion_fecha"]]} if x.get(f["aprobacion_fecha"]) else {}),
                **({"motivo": x[f["aprobacion_motivo"]]} if x.get(f["aprobacion_motivo"]) else {}),
            } for x in a.get(f["aprobaciones"]) or []],
        }
        decs = [x["decision"] for x in out["aprobaciones"]]
        out["resumen_aprobacion"] = {"aprobados": decs.count("Aprobado"), "rechazados": decs.count("Rechazado"),
                                     "pendientes": decs.count("Pendiente"), "total": len(decs)}
        if mi_empresa:
            mia = [x["decision"] for x in out["aprobaciones"] if x["cliente"]["id"] == mi_empresa]
            if mia:
                out["mi_decision"] = mia[0]
        if a.get(f["periodo_clave"]):
            out["periodo"] = {"clave": a[f["periodo_clave"]], "inicio": a.get(f["periodo_inicio"]) or "",
                              "fin": a.get(f["periodo_fin"]) or ""}
        if lectura is not None:
            out["lectura_ia"] = lectura
        return {k: v for k, v in out.items() if v is not None or k in ("requerimiento", "vigencia_fin")}

    # ---------------------------------------------------------- visibilidad

    def _doc_visible(self, documento_id, mi_empresa):
        f = self.ctr_f["documentos_de_cumplimiento"]
        rec = self._ctr_get(self.DOCUMENTOS_FORM, documento_id) if documento_id else None
        if not rec:
            self._doc_error("El documento no existe.", 404)
        a = rec.get("answers") or {}
        compartido = {str(x.get(f["compartido_con_id"]) or "") for x in a.get(f["compartido_con"]) or []}
        if mi_empresa != str(a.get(f["dueno_empresa_id"]) or "") and mi_empresa not in compartido:
            self._doc_error("No tienes acceso a este documento.", 403)
        return rec

    def _doc_clientes(self, mi_empresa):
        """{empresa_id: razón social} de los clientes activos de mi empresa."""
        fr = self.ctr_f["relaciones_entre_empresas"]
        if not self.RELACIONES_FORM:
            return {}
        return {str(r["answers"].get(fr["cliente_id"])): r["answers"].get(fr["cliente"]) or ""
                for r in self._ctr_find(self.RELACIONES_FORM, {f"answers.{fr['contratista_id']}": mi_empresa,
                                                               f"answers.{fr['estatus']}": opt("Activo")})}

    def _doc_recalcular(self, contratista_id, clientes):
        """Motor ME-15 de las relaciones (cliente en `clientes`, contratista dado)."""
        if not (self.CUMPLIMIENTO_FORM and self.RELACIONES_FORM and clientes):
            return
        fr, fc = self.ctr_f["relaciones_entre_empresas"], self.ctr_f["contratos_de_servicio"]
        cache = {}
        for rel in self._ctr_find(self.RELACIONES_FORM, {f"answers.{fr['contratista_id']}": contratista_id,
                                                         f"answers.{fr['cliente_id']}": {"$in": list(clientes)}}):
            for c in self._ctr_find(self.CONTRATOS_FORM, {f"answers.{fc['relacion_id']}": str(rel["_id"])}):
                self.recalcular_contrato(str(c["_id"]), cache)
            self.recalcular_relacion(str(rel["_id"]), cache)

    # ------------------------------------------------------------------ API

    def list_documentos(self, dueno_tipo=None, empresa_id=None, empleado_id=None, contrato_id=None,
                        requerimiento_id=None, estatus=None, search=None, limit=25, offset=0):
        if not self.DOCUMENTOS_FORM:
            return {"items": [], "total": 0}
        mi_empresa = self.ctr_empresa_activa_id()
        f = self.ctr_f["documentos_de_cumplimiento"]
        match = {"$and": [{"$or": [{f"answers.{f['dueno_empresa_id']}": mi_empresa},
                                   {f"answers.{f['compartido_con']}.{f['compartido_con_id']}": mi_empresa}]}]}
        if dueno_tipo:
            if dueno_tipo not in AMBITOS:
                self._doc_error(f"dueno_tipo no válido: {dueno_tipo}.")
            match[f"answers.{f['dueno_tipo']}"] = opt(dueno_tipo)
        for valor, campo in ((empresa_id, "dueno_empresa_id"), (empleado_id, "dueno_empleado_id"),
                             (requerimiento_id, "requerimiento_id")):
            if valor:
                match[f"answers.{f[campo]}"] = str(valor)
        if contrato_id:
            match[f"answers.{f['contratos']}.{f['contratos_id']}"] = str(contrato_id)
        if search and search.strip():
            rx = {"$regex": re.escape(search.strip()), "$options": "i"}
            match["$and"].append({"$or": [{f"answers.{f[k]}": rx} for k in
                                          ("nombre", "folio", "requerimiento", "dueno_empleado")]})
        rows = self._ctr_find(self.DOCUMENTOS_FORM, match, sort=[("updated_at", -1)])
        items = [self.doc_out(r, mi_empresa) for r in rows]
        if estatus:  # se filtra después: Vencido se calcula al leer
            estatus = [estatus] if isinstance(estatus, str) else estatus
            items = [d for d in items if d["estatus"] in estatus]
        off, lim = max(0, _int(offset)), max(1, min(_int(limit, 25), 200))
        return {"items": items[off:off + lim], "total": len(items)}

    def get_documento(self, documento_id):
        self._doc_requiere_forma()
        mi_empresa = self.ctr_empresa_activa_id()
        return self.doc_out(self._doc_visible(documento_id, mi_empresa), mi_empresa)

    def _doc_siguiente_folio(self):
        f = self.ctr_f["documentos_de_cumplimiento"]
        n = 0
        for r in self._ctr_find(self.DOCUMENTOS_FORM):
            m = re.match(r"^D-(\d+)$", str((r.get("answers") or {}).get(f["folio"]) or ""))
            if m:
                n = max(n, int(m.group(1)))
        return f"D-{n + 1:04d}"

    def _doc_datos_in(self, d):
        """Campos editables comunes de alta y reemplazo."""
        f = self.ctr_f["documentos_de_cumplimiento"]
        a = {}
        if d.get("periodo"):
            p = d["periodo"] if isinstance(d["periodo"], dict) else {}
            if not p.get("clave"):
                self._doc_error("El periodo necesita su clave (p. ej. 2026-05).")
            ini, fin = _fecha(p.get("inicio")), _fecha(p.get("fin"))
            a.update({f["periodo_clave"]: str(p["clave"]), f["periodo_inicio"]: ini.isoformat() if ini else "",
                      f["periodo_fin"]: fin.isoformat() if fin else ""})
        if "en_ceros" in d:
            a[f["en_ceros"]] = opt("Sí") if d.get("en_ceros") else opt("No")
        for k in ("vigencia_inicio", "vigencia_fin"):
            if k in d:
                fecha = _fecha(d.get(k))
                if d.get(k) and not fecha:
                    self._doc_error(f"{k} no es una fecha válida (YYYY-MM-DD).")
                a[f[k]] = fecha.isoformat() if fecha else ""
        ini, fin = _fecha(a.get(f["vigencia_inicio"])), _fecha(a.get(f["vigencia_fin"]))
        if ini and fin and fin < ini:
            self._doc_error("La vigencia termina antes de empezar.")
        if d.get("lectura_ia") is not None:
            a[f["lectura_ia"]] = simplejson.dumps(d["lectura_ia"], ensure_ascii=False)[:20000]
        return {k: v for k, v in a.items() if v is not None}

    def _doc_version(self, numero, archivo_lkf):
        f = self.ctr_f["documentos_de_cumplimiento"]
        return {f["version_numero"]: numero, f["version_archivo"]: archivo_lkf,
                f["version_estatus"]: opt("Por revisar"), f["version_subido_por"]: self._ctr_autor(),
                f["version_fecha"]: self._doc_ahora()}

    def upload_documento(self, documento):
        """Alta, o versión nueva si trae reemplaza_id (Reemplazar)."""
        self._doc_requiere_forma()
        d = documento if isinstance(documento, dict) else {}
        f = self.ctr_f["documentos_de_cumplimiento"]
        mi_empresa = self.ctr_empresa_activa_id()
        archivo = self._doc_file(d.get("archivo"))
        if not archivo:
            self._doc_error("Falta el archivo (name y file_url).")

        if d.get("reemplaza_id"):
            rec = self._doc_visible(str(d["reemplaza_id"]), mi_empresa)
            a = dict(rec.get("answers") or {})
            if str(a.get(f["dueno_empresa_id"]) or "") != mi_empresa:
                self._doc_error("Solo el dueño del documento puede reemplazarlo.", 403)
            versiones = list(a.get(f["versiones"]) or [])
            a[f["versiones"]] = versiones + [self._doc_version(len(versiones) + 1, archivo)]
            a[f["archivo"]] = archivo
            # Reemplazar regresa todas las aprobaciones a Pendiente.
            a[f["aprobaciones"]] = [{f["aprobacion_cliente_id"]: x.get(f["aprobacion_cliente_id"]),
                                     f["aprobacion_cliente"]: x.get(f["aprobacion_cliente"]),
                                     f["aprobacion_decision"]: opt("Pendiente")}
                                    for x in a.get(f["aprobaciones"]) or []]
            a.update(self._doc_datos_in(d))
            if d.get("nombre"):
                a[f["nombre"]] = str(d["nombre"]).strip()
            a[f["estatus"]] = opt(self._doc_estatus(a))
            self._ctr_patch(self.DOCUMENTOS_FORM, str(rec["_id"]), a, "reemplazar_documento")
            clientes = {str(x.get(f["compartido_con_id"])) for x in a.get(f["compartido_con"]) or []}
            self._doc_recalcular(mi_empresa, clientes)
            return self.get_documento(str(rec["_id"]))

        nombre = str(d.get("nombre") or "").strip()
        if not nombre:
            self._doc_error("El nombre del documento es obligatorio.")
        dueno = d.get("dueno") if isinstance(d.get("dueno"), dict) else {}
        tipo = dueno.get("tipo") or "Empresa"
        if tipo not in AMBITOS:
            self._doc_error(f"Tipo de dueño no válido: {tipo}.")
        if str(dueno.get("empresa_id") or mi_empresa) != mi_empresa:
            self._doc_error("Solo puedes subir documentos de tu empresa.", 403)
        cache = {}
        empresa = self._ctr_empresa_ref(mi_empresa, cache)
        a = {
            f["folio"]: self._doc_siguiente_folio(), f["nombre"]: nombre,
            f["dueno_tipo"]: opt(tipo), f["dueno_empresa_id"]: mi_empresa, f["dueno_empresa"]: empresa["razon_social"],
            f["archivo"]: archivo, f["estatus"]: opt("Por revisar"),
            f["origen"]: opt(d.get("origen") if d.get("origen") in ("Carga", "Carga masiva") else "Carga"),
            f["versiones"]: [self._doc_version(1, archivo)], f["comentarios"]: [],
            f["en_ceros"]: opt("No"),
        }
        if d.get("categoria"):
            a[f["categoria"]] = str(d["categoria"]).strip()
        if tipo == "Persona":
            emp = self.Employee
            e = self._ctr_get(emp.EMPLEADOS, str(dueno.get("empleado_id") or ""))
            if not e:
                self._doc_error("El empleado dueño del documento no existe.", 404)
            emp_empresa = str((e.get("answers") or {}).get(self.ctr_f["empleados"]["empresa_id"]) or "")
            propia = self.ctr_empresa_propia()
            if emp_empresa != mi_empresa and not (not emp_empresa and propia and str(propia["_id"]) == mi_empresa):
                self._doc_error("El empleado no es de tu empresa.", 403)
            a.update({f["dueno_empleado_id"]: str(e["_id"]),
                      f["dueno_empleado"]: (e.get("answers") or {}).get(emp.employee_fields["worker_name"]) or ""})
        if tipo == "Equipo":
            if not dueno.get("equipo_id"):
                self._doc_error("Falta el equipo dueño del documento.")
            a.update({f["dueno_equipo_id"]: str(dueno["equipo_id"]), f["dueno_equipo"]: str(dueno.get("equipo_nombre") or "")})
        if d.get("requerimiento_id"):
            fq = self.ctr_f["requerimientos_de_cumplimiento"]
            q = self._ctr_get(self.REQUERIMIENTOS_FORM, str(d["requerimiento_id"])) if self.REQUERIMIENTOS_FORM else None
            if not q:
                self._doc_error("El requerimiento no existe.", 404)
            a.update({f["requerimiento_id"]: str(q["_id"]), f["requerimiento"]: (q.get("answers") or {}).get(fq["nombre"]) or ""})
        clientes = self._doc_clientes(mi_empresa)
        if d.get("compartido_con") is not None:
            pedidos = [str(i) for i in d["compartido_con"]]
            ajenos = [i for i in pedidos if i not in clientes]
            if ajenos:
                self._doc_error("Solo puedes compartir con tus clientes activos.", 403)
            clientes = {i: clientes[i] for i in pedidos}
        a[f["compartido_con"]] = [{f["compartido_con_id"]: i, f["compartido_con_nombre"]: n} for i, n in clientes.items()]
        a[f["aprobaciones"]] = [{f["aprobacion_cliente_id"]: i, f["aprobacion_cliente"]: n,
                                 f["aprobacion_decision"]: opt("Pendiente")} for i, n in clientes.items()]
        contratos = []
        fc = self.ctr_f["contratos_de_servicio"]
        for cid in d.get("contratos") or []:
            c = self._ctr_get(self.CONTRATOS_FORM, str(cid))
            if not c or str((c.get("answers") or {}).get(fc["contratista_id"]) or "") != mi_empresa:
                self._doc_error(f"El contrato {cid} no existe o no es tuyo.", 404)
            contratos.append({f["contratos_id"]: str(c["_id"]), f["contratos_nombre"]: (c.get("answers") or {}).get(fc["folio"]) or ""})
        a[f["contratos"]] = contratos
        a.update(self._doc_datos_in(d))
        documento_id = self._ctr_post(self.DOCUMENTOS_FORM, a, "upload_documento")
        if not documento_id:
            self._doc_error("LinkaForm no regresó el id del documento.", 500)
        self._doc_recalcular(mi_empresa, set(clientes))
        return self.get_documento(documento_id)

    def review_documento(self, documento_id, decision, motivo=""):
        """Decisión del cliente activo (aprobar / rechazar con motivo)."""
        self._doc_requiere_forma()
        if decision not in ("Aprobado", "Rechazado"):
            self._doc_error("La decisión debe ser Aprobado o Rechazado.")
        motivo = (motivo or "").strip()
        if decision == "Rechazado" and not motivo:
            self._doc_error("El motivo es obligatorio al rechazar.")
        mi_empresa = self.ctr_empresa_activa_id()
        rec = self._doc_visible(documento_id, mi_empresa)
        f = self.ctr_f["documentos_de_cumplimiento"]
        a = dict(rec.get("answers") or {})
        compartido = {str(x.get(f["compartido_con_id"]) or ""): x.get(f["compartido_con_nombre"]) or ""
                      for x in a.get(f["compartido_con"]) or []}
        if mi_empresa not in compartido:
            self._doc_error("Solo un cliente con quien se compartió el documento puede revisarlo.", 403)
        nueva = {f["aprobacion_cliente_id"]: mi_empresa, f["aprobacion_cliente"]: compartido[mi_empresa],
                 f["aprobacion_decision"]: opt(decision), f["aprobacion_revisor"]: self._ctr_autor(),
                 f["aprobacion_fecha"]: self._doc_ahora()}
        if motivo:
            nueva[f["aprobacion_motivo"]] = motivo
        aprobaciones = [x for x in a.get(f["aprobaciones"]) or []
                        if str(x.get(f["aprobacion_cliente_id"]) or "") != mi_empresa]
        a[f["aprobaciones"]] = aprobaciones + [nueva]
        estatus = self._doc_estatus(a)
        a[f["estatus"]] = opt(estatus)
        versiones = list(a.get(f["versiones"]) or [])
        if versiones:
            ultima = dict(versiones[-1])
            ultima[f["version_estatus"]] = opt(estatus)
            if decision == "Rechazado":
                ultima[f["version_motivo_rechazo"]] = motivo
            else:
                ultima.pop(f["version_motivo_rechazo"], None)
            a[f["versiones"]] = versiones[:-1] + [ultima]
        self._ctr_patch(self.DOCUMENTOS_FORM, str(documento_id), a, "review_documento")
        self._doc_recalcular(str(a.get(f["dueno_empresa_id"]) or ""), {mi_empresa})
        return self.get_documento(documento_id)

    def update_compartido_documento(self, documento_id, compartido_con):
        """MX-02: el dueño cambia con qué clientes comparte (y quién aprueba)."""
        self._doc_requiere_forma()
        if not isinstance(compartido_con, list):
            self._doc_error("compartido_con debe ser una lista de ids de empresa.")
        mi_empresa = self.ctr_empresa_activa_id()
        rec = self._doc_visible(documento_id, mi_empresa)
        f = self.ctr_f["documentos_de_cumplimiento"]
        a = dict(rec.get("answers") or {})
        if str(a.get(f["dueno_empresa_id"]) or "") != mi_empresa:
            self._doc_error("Solo el dueño del documento puede cambiar con quién se comparte.", 403)
        antes = {str(x.get(f["compartido_con_id"]) or ""): x.get(f["compartido_con_nombre"]) or ""
                 for x in a.get(f["compartido_con"]) or []}
        activos = self._doc_clientes(mi_empresa)
        pedidos = list(dict.fromkeys(str(i) for i in compartido_con if str(i).strip()))
        # Un cliente que ya estaba puede quedarse aunque la relación ya no esté activa.
        ajenos = [i for i in pedidos if i not in activos and i not in antes]
        if ajenos:
            self._doc_error("Solo puedes compartir con tus clientes activos.", 403)
        nuevos = {i: activos.get(i) or antes.get(i) or "" for i in pedidos}
        previas = {str(x.get(f["aprobacion_cliente_id"]) or ""): x for x in a.get(f["aprobaciones"]) or []}
        a[f["compartido_con"]] = [{f["compartido_con_id"]: i, f["compartido_con_nombre"]: n} for i, n in nuevos.items()]
        a[f["aprobaciones"]] = [previas.get(i) or {f["aprobacion_cliente_id"]: i, f["aprobacion_cliente"]: n,
                                                   f["aprobacion_decision"]: opt("Pendiente")}
                                for i, n in nuevos.items()]
        estatus = self._doc_estatus(a)
        a[f["estatus"]] = opt(estatus)
        versiones = list(a.get(f["versiones"]) or [])
        if versiones:
            ultima = dict(versiones[-1])
            ultima[f["version_estatus"]] = opt(estatus)
            a[f["versiones"]] = versiones[:-1] + [ultima]
        self._ctr_patch(self.DOCUMENTOS_FORM, str(documento_id), a, "update_compartido_documento")
        afectados = set(antes) ^ set(nuevos)
        self._doc_recalcular(mi_empresa, afectados)
        return self.get_documento(documento_id)

    def comment_documento(self, documento_id, texto):
        self._doc_requiere_forma()
        texto = (texto or "").strip()
        if not texto:
            self._doc_error("El comentario está vacío.")
        if len(texto) > MAX_COMENTARIO:
            self._doc_error(f"El comentario pasa de {MAX_COMENTARIO} caracteres.")
        rec = self._doc_visible(documento_id, self.ctr_empresa_activa_id())
        f = self.ctr_f["documentos_de_cumplimiento"]
        a = dict(rec.get("answers") or {})
        a[f["comentarios"]] = list(a.get(f["comentarios"]) or []) + [{
            f["comentario_autor"]: self._ctr_autor(), f["comentario_fecha"]: self._doc_ahora(),
            f["comentario_texto"]: texto}]
        self._ctr_patch(self.DOCUMENTOS_FORM, str(documento_id), a, "comment_documento")
        return self.get_documento(documento_id)
