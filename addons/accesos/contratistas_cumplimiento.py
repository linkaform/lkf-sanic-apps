# -*- coding: utf-8 -*-
"""Motor de cumplimiento de Contratistas (ME-15).

Spec: clave10-sdk/specs/contratos/contratos-001-modelo-de-datos.md
(secciones "Requerimientos que exige un contrato" y "Cumplimiento de
requerimientos").

- Materializa en la forma Cumplimiento de requerimientos una fila por
  (contrato, requerimiento, sujeto, periodo). Solo el motor la escribe.
- Requerimientos de un contrato = los de sus servicios + perfiles + equipos,
  menos los excluidos de cada renglón. Ámbito Empresa aplica al contratista,
  Persona a cada empleado ligado (según su perfil; los de servicio a todos),
  Equipo a cada renglón de equipo (los activos reales son de ME-08).
- Los requerimientos asignados a la relación generan filas con contrato vacío.
- Periodos: único / por vigencia = una fila "unico"; por periodo = los
  periodos del año en curso dentro de la vigencia del sujeto.
- Sincroniza por diferencia: crea lo nuevo, actualiza lo que cambió y borra
  lo que ya no aplica (renglón o empleado quitado, contrato cancelado).
- Recalcula los % y el estatus del contrato, y el % de la relación.
"""
from datetime import date

from .contratistas_contratos import ESTATUS, MESES, _fecha, _ids, _int, label, opt

AMBITOS = ["Empresa", "Persona", "Equipo"]
ESTADOS = ["Por transcurrir", "En plazo", "Por subir", "Por revisar", "Cumplido", "Rechazado",
           "Vencido", "En ceros", "No aplica"]
ESTADOS_MANUALES = ["No aplica", "Cumplido", "Rechazado", "Vencido"]
CUMPLE = ("Cumplido", "En ceros")
NO_APLICABLE = ("No aplica", "Por transcurrir", "En plazo")
# No bloquean el contrato aunque el requerimiento sea limitante.
NO_PENDIENTE = ("Cumplido", "En ceros", "No aplica", "Por transcurrir")
DECISIONES = ["Pendiente", "Aprobado", "Rechazado"]
PERIODICIDAD_MESES = {"Mensual": 1, "Bimestral": 2, "Trimestral": 3, "Cuatrimestral": 4,
                      "Semestral": 6, "Anual": 12}
PERIODICIDAD_LETRA = {2: "B", 3: "T", 4: "C", 6: "S"}
PERIODICIDADES = ["Única", "Mensual", "Bimestral", "Trimestral", "Cuatrimestral", "Semestral", "Anual",
                  "Cada 3 años", "Cada 10 años"]
DIA_LIMITE = 17


def _fin_de_mes(anio, mes):
    sig = date(anio + mes // 12, mes % 12 + 1, 1)
    return date.fromordinal(sig.toordinal() - 1)


def _dia(anio, mes, dia):
    """Día `dia` del mes (recortado al último día); mes 13 = enero del siguiente."""
    while mes > 12:
        anio, mes = anio + 1, mes - 12
    return date(anio, mes, min(dia, _fin_de_mes(anio, mes).day))


def periodos(req, anio, desde, hasta):
    """Periodos de `req` en `anio` que tocan [desde, hasta] (fechas)."""
    unico = [{"clave": "unico", "inicio": desde.isoformat(), "fin": hasta.isoformat(), "vence": desde.isoformat()}]
    if req["vigencia_modo"] != "Periodo":
        return unico
    n = PERIODICIDAD_MESES.get(req["periodicidad"])
    if not n:  # Única, Cada 3 años, Cada 10 años
        return unico
    dia = req["dia_limite"] or DIA_LIMITE
    vence_meses = req["meses_periodo"]
    out = []
    for i, mes_ini in enumerate(range(1, 13, n)):
        mes_fin = mes_ini + n - 1
        inicio, fin = date(anio, mes_ini, 1), _fin_de_mes(anio, mes_fin)
        if fin < desde or inicio > hasta:
            continue
        # Vence el día límite del mes siguiente al periodo o, si hay meses
        # indicados (ICSOE: ene, may, sep), del primero que viene después.
        despues = [m for m in vence_meses if m > mes_fin]
        if despues:
            vence = _dia(anio, despues[0], dia)
        elif vence_meses:
            vence = _dia(anio + 1, vence_meses[0], dia)
        else:
            vence = _dia(anio, mes_fin + 1, dia)
        if n == 1:
            clave = f"{anio}-{mes_ini:02d}"
        elif n == 12:
            clave = f"{anio}"
        else:
            clave = f"{anio}-{PERIODICIDAD_LETRA[n]}{i + 1}"
        out.append({"clave": clave, "inicio": inicio.isoformat(), "fin": fin.isoformat(),
                    "vence": vence.isoformat()})
    return out


def porcentaje(estados):
    aplicables = [e for e in estados if e not in NO_APLICABLE]
    if not aplicables:
        return 100
    return round(sum(1 for e in aplicables if e in CUMPLE) * 100 / len(aplicables))


class CumplimientoMixin:
    """Se mezcla en Accesos junto con ContratosMixin y RelacionesMixin."""

    def _cum_error(self, msg, status=400):
        return self.LKFException({"title": "Cumplimiento", "msg": msg, "status_code": status})

    # --------------------------------------------------------- catálogos

    def _cum_requerimiento(self, req_id, cache):
        """Requerimiento normalizado (o None si no existe o está inactivo)."""
        key = f"req:{req_id}"
        if key not in cache:
            f = self.ctr_f["requerimientos_de_cumplimiento"]
            a = (self._ctr_get(self.REQUERIMIENTOS_FORM, req_id) or {}).get("answers")
            if not a or a.get(f["estatus"]) == opt("Inactivo"):
                cache[key] = None
            else:
                meses = a.get(f["meses_periodo"]) or []
                meses = meses if isinstance(meses, list) else [meses]
                cache[key] = {
                    "id": str(req_id),
                    "nombre": a.get(f["nombre"]) or "",
                    "ambito": label(AMBITOS, a.get(f["ambito"])) or "Empresa",
                    "vigencia_modo": label(["Vigencia", "Periodo"], a.get(f["vigencia_modo"])) or "Vigencia",
                    "periodicidad": label(PERIODICIDADES, a.get(f["periodicidad"])) or "Única",
                    "meses_periodo": sorted(MESES.index(m) + 1 for m in (label(MESES, x) for x in meses) if m),
                    "dia_limite": _int(a.get(f["dia_limite"]), 0),
                    "limitante": a.get(f["limitante"]) == opt("Sí"),
                }
        return cache[key]

    def _cum_reqs_recurso(self, recurso_id, cache):
        key = f"rec:{recurso_id}"
        if key not in cache:
            f = self.ctr_f["recursos_de_contrato"]
            a = (self._ctr_get(self.RECURSOS_CONTRATO_FORM, recurso_id) or {}).get("answers") or {}
            activo = a.get(f["estatus"]) != opt("Inactivo")
            cache[key] = [str(r.get(f["requerimientos_id"])) for r in (a.get(f["requerimientos"]) or [])
                          if activo and r.get(f["requerimientos_id"])]
        return cache[key]

    def _cum_documentos(self, empresa_id, cache):
        """Documentos de la empresa sujeto, del más reciente al más viejo."""
        key = f"docs:{empresa_id}"
        if key not in cache:
            f = self.ctr_f["documentos_de_cumplimiento"]
            cache[key] = self._ctr_find(self.DOCUMENTOS_FORM, {f"answers.{f['dueno_empresa_id']}": empresa_id},
                                        sort=[("updated_at", -1)]) if self.DOCUMENTOS_FORM else []
        return cache[key]

    # ------------------------------------------------------------ estado

    def _cum_estado(self, fila, cliente_id, cache):
        """Estado calculado y documento que lo cubre (regla de la spec)."""
        hoy = self._ctr_hoy().isoformat()
        p = fila["periodo"]
        if p["clave"] != "unico" and p["inicio"] > hoy:
            return "Por transcurrir", None
        f = self.ctr_f["documentos_de_cumplimiento"]
        suj = fila["sujeto"]
        doc = None
        for d in self._cum_documentos(suj["empresa"]["id"], cache):
            a = d.get("answers") or {}
            if str(a.get(f["requerimiento_id"]) or "") != fila["requerimiento"]["id"]:
                continue
            if suj["tipo"] == "Persona" and str(a.get(f["dueno_empleado_id"]) or "") != suj["empleado"]["id"]:
                continue
            if suj["tipo"] == "Equipo" and str(a.get(f["dueno_equipo_id"]) or "") != suj["equipo"]["id"]:
                continue
            if p["clave"] != "unico" and a.get(f["periodo_clave"]) != p["clave"]:
                continue
            # MX-02: solo cubre al cliente con quien se compartió.
            if cliente_id not in {str(x.get(f["compartido_con_id"]) or "") for x in a.get(f["compartido_con"]) or []}:
                continue
            doc = d
            break
        if not doc:
            return ("Por subir" if p["vence"] < hoy else "En plazo"), None
        a = doc.get("answers") or {}
        decision = None
        for apr in a.get(f["aprobaciones"]) or []:
            if str(apr.get(f["aprobacion_cliente_id"]) or "") == cliente_id:
                decision = label(DECISIONES, apr.get(f["aprobacion_decision"]))
        if decision == "Rechazado":
            return "Rechazado", doc
        if decision == "Aprobado":
            vfin = a.get(f["vigencia_fin"])
            if vfin and str(vfin)[:10] < hoy:
                return "Vencido", doc
            return ("En ceros" if a.get(f["en_ceros"]) == opt("Sí") else "Cumplido"), doc
        return "Por revisar", doc

    # ------------------------------------------------------ filas deseadas

    def _cum_filas_contrato(self, rec, cache):
        """Filas que exige el contrato hoy (sin estado aún)."""
        fc = self.ctr_f["contratos_de_servicio"]
        a = rec.get("answers") or {}
        if a.get(fc["estatus_manual"]) == opt("Cancelado"):
            return []
        anio = self._ctr_hoy().year
        ini, fin = _fecha(a.get(fc["inicio"])), _fecha(a.get(fc["fin"]))
        if not ini or not fin:
            return []
        y0, y1 = date(anio, 1, 1), date(anio, 12, 31)
        base = {
            "relacion": {"id": str(a.get(fc["relacion_id"]) or ""), "nombre": a.get(fc["relacion"]) or ""},
            "contrato": {"id": str(rec["_id"]), "nombre": a.get(fc["folio"]) or ""},
        }
        empresa = {"id": str(a.get(fc["contratista_id"]) or ""), "nombre": a.get(fc["contratista"]) or ""}
        filas = []

        def agregar(req, sujeto, desde):
            d, h = max(desde, ini), fin
            if h < y0 or d > y1:
                return
            for p in periodos(req, anio, d, h):
                filas.append({**base, "requerimiento": {"id": req["id"], "nombre": req["nombre"]},
                              "limitante": req["limitante"], "sujeto": sujeto, "periodo": p})

        def reqs(ids, ambito, excluidos=()):
            for i in dict.fromkeys(ids):
                r = self._cum_requerimiento(i, cache)
                if r and r["ambito"] == ambito and i not in excluidos:
                    yield r

        servicio_reqs = [i for g in a.get(fc["servicios"]) or [] for i in
                         self._cum_reqs_recurso(str(g.get(fc["servicio_id"]) or ""), cache)]
        # Empresa: de los servicios.
        for r in reqs(servicio_reqs, "Empresa"):
            agregar(r, {"tipo": "Empresa", "empresa": empresa}, ini)
        # Persona: perfil del empleado (menos excluidos del renglón) + servicios.
        perfiles = {str(g.get(fc["perfil_id"]) or ""): g for g in a.get(fc["perfiles"]) or []}
        for e in a.get(fc["empleados"]) or []:
            perfil_id = str(e.get(fc["empleado_perfil_id"]) or "")
            renglon = perfiles.get(perfil_id) or {}
            excl = _ids(renglon.get(fc["perfil_requerimientos_excluidos"]))
            sujeto = {"tipo": "Persona", "empresa": empresa,
                      "empleado": {"id": str(e.get(fc["empleado_id"]) or ""), "nombre": e.get(fc["empleado"]) or ""}}
            alta = _fecha(e.get(fc["empleado_fecha_alta"])) or ini
            for r in reqs(self._cum_reqs_recurso(perfil_id, cache) + servicio_reqs, "Persona", excl):
                agregar(r, sujeto, alta)
        # Equipo: cada renglón.
        for g in a.get(fc["equipos"]) or []:
            eq_id = str(g.get(fc["equipo_id"]) or "")
            excl = _ids(g.get(fc["equipo_requerimientos_excluidos"]))
            sujeto = {"tipo": "Equipo", "empresa": empresa, "equipo": {"id": eq_id, "nombre": g.get(fc["equipo"]) or ""}}
            for r in reqs(self._cum_reqs_recurso(eq_id, cache) + servicio_reqs, "Equipo", excl):
                agregar(r, sujeto, ini)
        return filas

    def _cum_filas_relacion(self, rel, cache):
        """Filas de los requerimientos asignados a la relación (contrato vacío)."""
        fr = self.ctr_f["relaciones_entre_empresas"]
        a = rel.get("answers") or {}
        if a.get(fr["estatus"]) == opt("Inactivo"):
            return []
        anio = self._ctr_hoy().year
        desde = max(_fecha(a.get(fr["fecha_alta"])) or date(anio, 1, 1), date(anio, 1, 1))
        hasta = date(anio, 12, 31)
        empresa = {"id": str(a.get(fr["contratista_id"]) or ""), "nombre": a.get(fr["contratista"]) or ""}
        base = {"relacion": {"id": str(rel["_id"]), "nombre": a.get(fr["folio"]) or ""}, "contrato": None}
        filas = []
        for g in a.get(fr["requerimientos_asignados"]) or []:
            r = self._cum_requerimiento(str(g.get(fr["requerimientos_asignados_id"]) or ""), cache)
            if not r or r["ambito"] != "Empresa":
                continue
            for p in periodos(r, anio, desde, hasta):
                filas.append({**base, "requerimiento": {"id": r["id"], "nombre": r["nombre"]},
                              "limitante": r["limitante"], "sujeto": {"tipo": "Empresa", "empresa": empresa},
                              "periodo": p})
        return filas

    # --------------------------------------------------------- escritura

    @staticmethod
    def _cum_llave(fila):
        s = fila["sujeto"]
        sid = (s.get("empleado") or s.get("equipo") or s["empresa"])["id"]
        return ((fila["contrato"] or {}).get("id") or "", fila["requerimiento"]["id"], s["tipo"], sid,
                fila["periodo"]["clave"])

    def _cum_llave_rec(self, rec):
        f = self.ctr_f["cumplimiento_de_requerimientos"]
        a = rec.get("answers") or {}
        tipo = label(AMBITOS, a.get(f["sujeto_tipo"])) or "Empresa"
        sid = a.get({"Persona": f["sujeto_empleado_id"], "Equipo": f["sujeto_equipo_id"]}.get(tipo, f["sujeto_empresa_id"]))
        return (str(a.get(f["contrato_id"]) or ""), str(a.get(f["requerimiento_id"]) or ""), tipo, str(sid or ""),
                a.get(f["periodo_clave"]) or "")

    def _cum_answers(self, fila, estado, doc):
        f = self.ctr_f["cumplimiento_de_requerimientos"]
        fd = self.ctr_f["documentos_de_cumplimiento"]
        s, p = fila["sujeto"], fila["periodo"]
        a = {
            f["relacion_id"]: fila["relacion"]["id"], f["relacion"]: fila["relacion"]["nombre"],
            f["requerimiento_id"]: fila["requerimiento"]["id"], f["requerimiento"]: fila["requerimiento"]["nombre"],
            f["limitante"]: opt("Sí") if fila["limitante"] else opt("No"),
            f["sujeto_tipo"]: opt(s["tipo"]),
            f["sujeto_empresa_id"]: s["empresa"]["id"], f["sujeto_empresa"]: s["empresa"]["nombre"],
            f["periodo_clave"]: p["clave"], f["periodo_inicio"]: p["inicio"], f["periodo_fin"]: p["fin"],
            f["periodo_vence"]: p["vence"],
            f["estado"]: opt(estado),
            f["documento_id"]: str(doc["_id"]) if doc else "",
            f["documento"]: ((doc.get("answers") or {}).get(fd["folio"]) or "") if doc else "",
        }
        if fila["contrato"]:
            a.update({f["contrato_id"]: fila["contrato"]["id"], f["contrato"]: fila["contrato"]["nombre"]})
        if s.get("empleado"):
            a.update({f["sujeto_empleado_id"]: s["empleado"]["id"], f["sujeto_empleado"]: s["empleado"]["nombre"]})
        if s.get("equipo"):
            a.update({f["sujeto_equipo_id"]: s["equipo"]["id"], f["sujeto_equipo"]: s["equipo"]["nombre"]})
        return a

    def _cum_sincronizar(self, filas, existentes, cliente_id, cache):
        """Deja la forma igual a `filas`. Regresa los estados finales (con manual)."""
        f = self.ctr_f["cumplimiento_de_requerimientos"]
        por_llave, duplicadas = {}, []
        for r in existentes:
            k = self._cum_llave_rec(r)
            if k in por_llave:
                duplicadas.append(r)
            else:
                por_llave[k] = r
        nuevas, cambios, estados, vistas = [], {}, [], set()
        for fila in filas:
            k = self._cum_llave(fila)
            if k in vistas:
                continue
            vistas.add(k)
            estado, doc = self._cum_estado(fila, cliente_id, cache)
            ans = self._cum_answers(fila, estado, doc)
            r = por_llave.get(k)
            if not r:
                nuevas.append(ans)
                estados.append(estado)
                continue
            actual = r.get("answers") or {}
            manual = label(ESTADOS_MANUALES, actual.get(f["estado_manual"]))
            estados.append(manual or estado)
            # estado_manual y motivo_manual no se tocan: los fija el cliente.
            dif = {c: v for c, v in ans.items() if (actual.get(c) if actual.get(c) is not None else "") != v}
            if dif:
                cambios.setdefault(tuple(sorted(dif.items())), []).append(str(r["_id"]))
        sobran = [str(r["_id"]) for k, r in por_llave.items() if k not in vistas] + [str(r["_id"]) for r in duplicadas]
        if nuevas:
            metadata = self.lkf_api.get_metadata(form_id=self.CUMPLIMIENTO_FORM)
            props = {"device_properties": {"System": "Script", "Module": "Accesos",
                                           "Process": "Contratistas · cumplimiento", "Action": "motor_cumplimiento"}}
            res = self.lkf_api.post_forms_answers_list(
                [{**metadata, "properties": props, "answers": a} for a in nuevas])
            malas = [x for x in res or [] if x.get("status_code") not in (200, 201, 202)]
            if malas:
                self._cum_error(f"No se pudieron crear {len(malas)} de {len(nuevas)} filas de cumplimiento: "
                                f"{(malas[0].get('json') or malas[0])}", 500)
        for dif, ids in cambios.items():
            # Sin threading: esa ruta no copia el JWT de la petición a los hilos.
            self.lkf_api.patch_multi_record(dict(dif), self.CUMPLIMIENTO_FORM, record_id=ids)
        if sobran:
            self.lkf_api.patch_record_list({"deleted_objects": [f"/api/infosync/form_answer/{i}/" for i in sobran]})
        return {"creadas": len(nuevas), "actualizadas": sum(len(v) for v in cambios.values()),
                "borradas": len(sobran), "estados": estados}

    # ------------------------------------------------------------ motor

    def recalcular_contrato(self, contrato_id, cache=None):
        """Sincroniza las filas del contrato y guarda % y estatus. Regresa resumen."""
        if not self.CUMPLIMIENTO_FORM:
            return None
        cache = {} if cache is None else cache
        fc = self.ctr_f["contratos_de_servicio"]
        fcu = self.ctr_f["cumplimiento_de_requerimientos"]
        rec = self._ctr_get(self.CONTRATOS_FORM, contrato_id)
        if not rec:
            return None
        a = rec.get("answers") or {}
        filas = self._cum_filas_contrato(rec, cache)
        existentes = self._ctr_find(self.CUMPLIMIENTO_FORM, {f"answers.{fcu['contrato_id']}": str(contrato_id)})
        res = self._cum_sincronizar(filas, existentes, str(a.get(fc["cliente_id"]) or ""), cache)

        # % del contrato (los tres anillos) y estatus.
        rows = self._ctr_find(self.CUMPLIMIENTO_FORM, {f"answers.{fcu['contrato_id']}": str(contrato_id)})
        def est(r):
            x = r.get("answers") or {}
            return label(ESTADOS_MANUALES, x.get(fcu["estado_manual"])) or label(ESTADOS, x.get(fcu["estado"])) or "En plazo"
        def tipo(r):
            return label(AMBITOS, (r.get("answers") or {}).get(fcu["sujeto_tipo"]))
        def unico(r):
            return (r.get("answers") or {}).get(fcu["periodo_clave"]) == "unico"
        nuevos = {
            fc["cumplimiento_pct"]: porcentaje([est(r) for r in rows]),
            fc["cumplimiento_contrato_pct"]: porcentaje([est(r) for r in rows if tipo(r) == "Empresa" and unico(r)]),
            fc["cumplimiento_empleados_pct"]: porcentaje([est(r) for r in rows if tipo(r) == "Persona"]),
            fc["cumplimiento_periodicos_pct"]: porcentaje([est(r) for r in rows if not unico(r)]),
        }
        antes = label(ESTATUS, a.get(fc["estatus"]))
        a2 = {**a, **nuevos}
        despues = self.ctr_calcular_estatus(a2, str(contrato_id))
        a2[fc["estatus"]] = opt(despues)
        if any(a.get(k) != v for k, v in a2.items()):
            self._ctr_patch(self.CONTRATOS_FORM, str(contrato_id), a2, "motor_cumplimiento")
            if antes != despues:
                self._ctr_evento(str(contrato_id), a.get(fc["folio"]) or "", "Estatus",
                                 f"Estatus: {antes} → {despues} (cumplimiento)",
                                 {"estatus": antes}, {"estatus": despues})
        res.pop("estados", None)
        res.update({"contrato": str(contrato_id), "estatus": despues, "cumplimiento_pct": nuevos[fc["cumplimiento_pct"]]})
        return res

    def recalcular_relacion(self, relacion_id, cache=None):
        """Sincroniza las filas asignadas a la relación y guarda su %."""
        if not self.CUMPLIMIENTO_FORM:
            return None
        cache = {} if cache is None else cache
        fr = self.ctr_f["relaciones_entre_empresas"]
        fcu = self.ctr_f["cumplimiento_de_requerimientos"]
        rel = self._ctr_get(self.RELACIONES_FORM, relacion_id)
        if not rel:
            return None
        a = rel.get("answers") or {}
        existentes = self._ctr_find(self.CUMPLIMIENTO_FORM, {
            f"answers.{fcu['relacion_id']}": str(relacion_id),
            f"answers.{fcu['contrato_id']}": {"$in": [None, ""]}})
        res = self._cum_sincronizar(self._cum_filas_relacion(rel, cache), existentes,
                                    str(a.get(fr["cliente_id"]) or ""), cache)
        rows = self._ctr_find(self.CUMPLIMIENTO_FORM, {f"answers.{fcu['relacion_id']}": str(relacion_id)})
        pct = porcentaje([label(ESTADOS_MANUALES, (r.get("answers") or {}).get(fcu["estado_manual"]))
                          or label(ESTADOS, (r.get("answers") or {}).get(fcu["estado"])) or "En plazo" for r in rows])
        if a.get(fr["cumplimiento_pct"]) != pct:
            self._ctr_patch(self.RELACIONES_FORM, str(relacion_id), {**a, fr["cumplimiento_pct"]: pct},
                            "motor_cumplimiento")
        res.pop("estados", None)
        res.update({"relacion": str(relacion_id), "cumplimiento_pct": pct})
        return res

    def cum_despues_de_contrato(self, contrato_id):
        """Gancho de ME-14: recalcula contrato y relación tras guardar."""
        if not self.CUMPLIMIENTO_FORM:
            return
        cache = {}
        self.recalcular_contrato(contrato_id, cache)
        rel_id = ((self._ctr_get(self.CONTRATOS_FORM, contrato_id) or {}).get("answers") or {}).get(
            self.ctr_f["contratos_de_servicio"]["relacion_id"])
        if rel_id:
            self.recalcular_relacion(str(rel_id), cache)

    # ------------------------------------------------------------------ API

    def _cum_relaciones_visibles(self, mi_empresa):
        fr = self.ctr_f["relaciones_entre_empresas"]
        return [str(r["_id"]) for r in self._ctr_find(self.RELACIONES_FORM, {"$or": [
            {f"answers.{fr['cliente_id']}": mi_empresa}, {f"answers.{fr['contratista_id']}": mi_empresa}]})]

    def cum_fila_out(self, rec):
        f = self.ctr_f["cumplimiento_de_requerimientos"]
        a = rec.get("answers") or {}
        tipo = label(AMBITOS, a.get(f["sujeto_tipo"])) or "Empresa"
        sujeto = {"tipo": tipo, "empresa": {"id": str(a.get(f["sujeto_empresa_id"]) or ""),
                                            "nombre": a.get(f["sujeto_empresa"]) or ""}}
        if a.get(f["sujeto_empleado_id"]):
            sujeto["empleado"] = {"id": str(a[f["sujeto_empleado_id"]]), "nombre": a.get(f["sujeto_empleado"]) or ""}
        if a.get(f["sujeto_equipo_id"]):
            sujeto["equipo"] = {"id": str(a[f["sujeto_equipo_id"]]), "nombre": a.get(f["sujeto_equipo"]) or ""}
        manual = label(ESTADOS_MANUALES, a.get(f["estado_manual"]))
        out = {
            "id": str(rec["_id"]),
            "relacion": str(a.get(f["relacion_id"]) or ""),
            "contrato": str(a.get(f["contrato_id"])) if a.get(f["contrato_id"]) else None,
            "requerimiento": {"id": str(a.get(f["requerimiento_id"]) or ""), "nombre": a.get(f["requerimiento"]) or ""},
            "limitante": a.get(f["limitante"]) == opt("Sí"),
            "sujeto": sujeto,
            "periodo": {"clave": a.get(f["periodo_clave"]) or "", "inicio": a.get(f["periodo_inicio"]) or "",
                        "fin": a.get(f["periodo_fin"]) or "", "vence": a.get(f["periodo_vence"]) or ""},
            "documento": a.get(f["documento_id"]) or None,
            "estado": manual or label(ESTADOS, a.get(f["estado"])) or "En plazo",
        }
        if manual:
            out["motivo_manual"] = a.get(f["motivo_manual"]) or ""
        return out

    def list_cumplimiento(self, relacion_id=None, contrato_id=None, sujeto_tipo=None, empleado_id=None, anio=None):
        if not self.CUMPLIMIENTO_FORM:
            return []
        mi_empresa = self.ctr_empresa_activa_id()
        f = self.ctr_f["cumplimiento_de_requerimientos"]
        if contrato_id:
            self._ctr_contrato_visible(contrato_id)
            match = {f"answers.{f['contrato_id']}": str(contrato_id)}
        elif relacion_id:
            self._rel_visible(relacion_id, mi_empresa)
            match = {f"answers.{f['relacion_id']}": str(relacion_id)}
        else:
            match = {f"answers.{f['relacion_id']}": {"$in": self._cum_relaciones_visibles(mi_empresa)}}
        if sujeto_tipo:
            if sujeto_tipo not in AMBITOS:
                self._cum_error(f"sujeto_tipo no válido: {sujeto_tipo}.")
            match[f"answers.{f['sujeto_tipo']}"] = opt(sujeto_tipo)
        if empleado_id:
            match[f"answers.{f['sujeto_empleado_id']}"] = str(empleado_id)
        if anio:
            match["$or"] = [{f"answers.{f['periodo_clave']}": "unico"},
                            {f"answers.{f['periodo_inicio']}": {"$regex": f"^{_int(anio)}-"}}]
        rows = self._ctr_find(self.CUMPLIMIENTO_FORM, match,
                              sort=[(f"answers.{f['requerimiento']}", 1), (f"answers.{f['periodo_inicio']}", 1)])
        return [self.cum_fila_out(r) for r in rows]

    def set_estado_cumplimiento(self, cumplimiento_id, estado=None, motivo=""):
        """Fija o quita el estado manual (ccOv). Solo el cliente de la relación."""
        if not self.CUMPLIMIENTO_FORM:
            self._cum_error("La forma Cumplimiento de requerimientos no está instalada.", 409)
        f = self.ctr_f["cumplimiento_de_requerimientos"]
        fr = self.ctr_f["relaciones_entre_empresas"]
        motivo = (motivo or "").strip()
        if not motivo:
            self._cum_error("El motivo es obligatorio.")
        if estado not in (None, "", *ESTADOS_MANUALES):
            self._cum_error(f"Estado manual no válido: {estado}. Opciones: {', '.join(ESTADOS_MANUALES)}.")
        rec = self._ctr_get(self.CUMPLIMIENTO_FORM, cumplimiento_id)
        if not rec:
            self._cum_error("La fila de cumplimiento no existe.", 404)
        a = rec.get("answers") or {}
        mi_empresa = self.ctr_empresa_activa_id()
        rel = self._rel_visible(str(a.get(f["relacion_id"]) or ""), mi_empresa)
        if str((rel.get("answers") or {}).get(fr["cliente_id"]) or "") != mi_empresa:
            self._cum_error("Solo el cliente de la relación puede fijar el estado.", 403)
        self.lkf_api.patch_multi_record({f["estado_manual"]: opt(estado) if estado else "",
                                         f["motivo_manual"]: motivo if estado else ""},
                                        self.CUMPLIMIENTO_FORM, record_id=[str(cumplimiento_id)])
        if a.get(f["contrato_id"]):
            self.cum_despues_de_contrato(str(a[f["contrato_id"]]))
        else:
            self.recalcular_relacion(str(a.get(f["relacion_id"])))
        return self.cum_fila_out(self._ctr_get(self.CUMPLIMIENTO_FORM, cumplimiento_id))

    def recalcular_cumplimiento(self, contrato_id=None, relacion_id=None):
        """Recalcula un contrato, una relación (con sus contratos) o todo lo de mi empresa.

        Para soporte y para la corrida diaria (cambio de periodo y vencidos)."""
        mi_empresa = self.ctr_empresa_activa_id()
        cache, out = {}, []
        if contrato_id:
            self._ctr_contrato_visible(contrato_id)
            self.cum_despues_de_contrato(str(contrato_id))
            return [self.recalcular_contrato(str(contrato_id), cache)]
        rel_ids = [str(relacion_id)] if relacion_id else self._cum_relaciones_visibles(mi_empresa)
        if relacion_id:
            self._rel_visible(relacion_id, mi_empresa)
        fc = self.ctr_f["contratos_de_servicio"]
        for rid in rel_ids:
            for c in self._ctr_find(self.CONTRATOS_FORM, {f"answers.{fc['relacion_id']}": rid}):
                out.append(self.recalcular_contrato(str(c["_id"]), cache))
            out.append(self.recalcular_relacion(rid, cache))
        return [x for x in out if x]
