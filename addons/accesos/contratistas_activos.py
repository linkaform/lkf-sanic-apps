# -*- coding: utf-8 -*-
"""Activos de Mi Empresa: equipos, vehículos y herramientas (ME-08-B).

Ficha: contratistas_me08_activos.md. Decisiones de Paco (2026-11-24):
- Se reusa la forma `activos_fijos` (módulo Activo_Fijo), la que lee
  Concesiones por catálogo; se le agregó la página "Contratista" (empresa,
  folio, tipo de activo, cantidad, asignado a, lectura IA) con gen.py.
- Mantenimientos en su propia forma (Mantenimientos de activos) con historial
  de estatus, comentarios y evidencias.
- Foto con IA: analizar_foto_activo identifica nombre, tipo, marca y modelo.

Reglas:
- Dueño = empresa activa. La empresa propia también ve los activos sin
  empresa_id (los que ya tenía la cuenta).
- Obligatorios al alta: nombre, tipo, costo, ubicación y área (catálogo de
  áreas de la cuenta) y foto (la forma la exige). Vehículos y equipos son
  siempre Único; Herramienta puede ser Stock con cantidad > 0. Al editar,
  "Asignado a" es obligatorio (diseño).
- Inactivo = fuera de operación: queda No disponible y no se asigna.
- Eliminar solo si no tiene concesiones ni mantenimientos abiertos.
- Concesiones del activo: se empatan por nombre del equipo (la concesión guarda
  el catálogo de activos, no el _id).
- Mantenimiento: asignado, prioridad y fecha límite obligatorios; cada cambio
  de estatus agrega un renglón al historial; al cerrarse actualiza la fecha de
  último mantenimiento del activo. La tarea en "Mis tareas" está fuera.
"""
import base64
import re

import requests
import simplejson

from .contratistas_contratos import _fecha, _int, _num, label, opt

CLASES = ["Vehículo", "Equipo", "Herramienta"]
INVENTARIOS = {"Único": "unico", "Stock": "stock"}
PRIORIDADES = ["Alta", "Media", "Baja"]
ESTATUS_MANT = ["Abierta", "En proceso", "Cerrada"]
MAX_IMG_BYTES = 10 * 1024 * 1024

# Campos propios de la forma activos_fijos (XML de addons, módulo activo_fijo).
AF = {
    "nombre": "66c192ef89463aa27fc1818b",
    "ubicacion": "663e5c57f5b8a7ce8211ed0b", "area": "663e5d44f5b8a7ce8211ed0f",
    "tipo_vehiculo": "65f22098d1dc5e0b9529e89a", "marca_vehiculo": "65f22098d1dc5e0b9529e89b",
    "modelo_vehiculo": "65f22098d1dc5e0b9529e89c",
    "serie_chasis": "6646393c3fa8b818265d0325", "serie_motor1": "66c174ec89463aa27fc1816c",
    "serie_motor2": "66c174ec89463aa27fc1816d",
    "km": "66c189f689463aa27fc18188", "km_fecha": "66c189f689463aa27fc18189",
    "km2": "66c1758989463aa27fc18171", "km2_fecha": "66c176dc89463aa27fc18175",
    "horometro": "66c1758989463aa27fc1816e", "horometro_fecha": "66c176ac89463aa27fc18172",
    "horometro2": "66c1758989463aa27fc1816f", "horometro2_fecha": "66c176ac89463aa27fc18173",
    "imagen": "6646393c3fa8b818265d0326", "marca": "6646393c3fa8b818265d0323", "modelo": "6646393c3fa8b818265d0324",
    "adquisicion": "6646393c3fa8b818265d0327", "costo": "697991fffd83f49bb9fe074e",
    "ultimo_mantenimiento": "6646393c3fa8b818265d0328",
    "disponible": "6646393c3fa8b818265d0329",  # disponible | no_disponible
    "estado": "66c1940b89463aa27fc1818c",  # activo | inactivo
    "inventario": "6aa33c3a8711c7a4f571a738",  # unico | stock
}

PROMPT_FOTO = """Identifica el activo de la foto (vehículo, equipo o herramienta de trabajo).
Responde SOLO un JSON:
{
  "legible": true|false,
  "nombre": "nombre corto y genérico del activo, p. ej. 'Taladro percutor' o 'Camioneta pickup'",
  "clase": "Vehículo" | "Equipo" | "Herramienta",
  "tipo_vehiculo": "solo vehículos: Pickup, Automóvil, Camión de carga, Montacargas, Maquinaria pesada o Grúa; si no, null",
  "marca": "marca visible o null",
  "modelo": "modelo visible o null (no lo adivines)",
  "confianza": {"nombre": 0-100, "clase": 0-100, "marca": 0-100, "modelo": 0-100}
}"""
SYSTEM_FOTO = "Eres un asistente que identifica activos de empresa en fotos. No inventes marca ni modelo."


class ActivosMixin:
    """Se mezcla en Accesos junto con EmpleadosMixin y ContratosMixin."""

    def _act_error(self, msg, status=400):
        return self.LKFException({"title": "Activos", "msg": msg, "status_code": status})

    @property
    def ACTIVOS_FORM(self):
        return getattr(getattr(self, "AF", None), "ACTIVOS_FIJOS", None)

    def _act_requiere(self):
        if not self.ACTIVOS_FORM:
            self._act_error("La forma Activos Fijos no está instalada en esta cuenta.", 409)

    def _act_empresa(self):
        """(empresa_id, es_propia) de la empresa activa."""
        empresa_id, es_propia, _ = self._emp_alcance(None)
        return empresa_id, es_propia

    def _act_match(self, empresa_id, es_propia):
        campo = f"answers.{self.ctr_f['activos_fijos']['empresa_id']}"
        if es_propia:  # los activos de siempre de la cuenta no tienen empresa
            return {"$or": [{campo: empresa_id}, {campo: {"$in": [None, ""]}}]}
        return {campo: empresa_id}

    def _act_get(self, activo_id):
        self._act_requiere()
        rec = self._ctr_get(self.ACTIVOS_FORM, str(activo_id or ""))
        if not rec:
            self._act_error("El activo no existe.", 404)
        empresa_id, es_propia = self._act_empresa()
        dueno = str((rec.get("answers") or {}).get(self.ctr_f["activos_fijos"]["empresa_id"]) or "")
        if dueno != empresa_id and not (es_propia and not dueno):
            self._act_error("El activo no es de tu empresa.", 403)
        return rec

    # ------------------------------------------------------------ salida

    def act_out(self, rec, mant=None):
        fa = self.ctr_f["activos_fijos"]
        a = rec.get("answers") or {}
        ubic = a.get(self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID) or {}
        veh = a.get(self.AF.TIPO_DE_VEHICULO_OBJ_ID) or {}
        uno = lambda v: (v[0] if isinstance(v, list) and v else v) or None  # noqa: E731
        imgs = a.get(AF["imagen"]) or []
        clase = label(CLASES, a.get(fa["clase"])) or ("Vehículo" if veh else "Equipo")
        out = {
            "id": str(rec["_id"]),
            "folio": a.get(fa["folio"]) or "",
            "nombre": a.get(AF["nombre"]) or "",
            "clase": clase,
            "foto": self._ctr_archivo(imgs[0] if isinstance(imgs, list) and imgs else imgs),
            "marca": a.get(AF["marca"]) or uno(veh.get(AF["marca_vehiculo"])),
            "modelo": a.get(AF["modelo"]) or uno(veh.get(AF["modelo_vehiculo"])),
            "estado": "Inactivo" if a.get(AF["estado"]) == "inactivo" else "Activo",
            "disponible": a.get(AF["disponible"]) != "no_disponible",
            "inventario": "Stock" if a.get(AF["inventario"]) == "stock" else "Único",
            "cantidad": _int(a.get(fa["cantidad"]), None),
            "ubicacion": uno(ubic.get(AF["ubicacion"])),
            "area": uno(ubic.get(AF["area"])),
            "asignado": {"id": str(a[fa["asignado_id"]]), "nombre": a.get(fa["asignado"]) or ""}
            if a.get(fa["asignado_id"]) else None,
            "adquisicion": a.get(AF["adquisicion"]) or None,
            "costo": _num(a.get(AF["costo"])),
            "ultimo_mantenimiento": a.get(AF["ultimo_mantenimiento"]) or None,
            "empresa": {"id": str(a[fa["empresa_id"]]), "nombre": a.get(fa["empresa"]) or ""}
            if a.get(fa["empresa_id"]) else None,
        }
        if clase == "Vehículo":
            out["vehiculo"] = {
                "tipo": uno(veh.get(AF["tipo_vehiculo"])),
                "serie_chasis": a.get(AF["serie_chasis"]) or None,
                "serie_motor1": a.get(AF["serie_motor1"]) or None,
                "serie_motor2": a.get(AF["serie_motor2"]) or None,
                "kilometraje": {"valor": _num(a.get(AF["km"])), "fecha": a.get(AF["km_fecha"]) or None},
                "horometro": {"valor": _num(a.get(AF["horometro"])), "fecha": a.get(AF["horometro_fecha"]) or None},
                "kilometraje2": {"valor": _num(a.get(AF["km2"])), "fecha": a.get(AF["km2_fecha"]) or None},
                "horometro2": {"valor": _num(a.get(AF["horometro2"])), "fecha": a.get(AF["horometro2_fecha"]) or None},
            }
        if mant is not None:
            out["mantenimientos_abiertos"] = mant
        return out

    # ----------------------------------------------------------- entrada

    def _act_answers_in(self, d, previo=None):
        """Valida y arma los answers (alta = previo None; edición = mezcla sobre previo)."""
        fa = self.ctr_f["activos_fijos"]
        a = dict(previo or {})
        alta = previo is None

        def pon(k, v):
            if v is None:
                a.pop(k, None)
            else:
                a[k] = v

        if alta or "nombre" in d:
            nombre = str(d.get("nombre") or "").strip()
            if not nombre:
                self._act_error("El nombre es obligatorio.")
            a[AF["nombre"]] = nombre
        clase = d.get("clase") if (alta or "clase" in d) else label(CLASES, a.get(fa["clase"]))
        if clase not in CLASES:
            self._act_error("Tipo de activo: Vehículo, Equipo o Herramienta.")
        a[fa["clase"]] = opt(clase)
        if alta or "costo" in d:
            costo = _num(d.get("costo"))
            if costo is None or costo < 0:
                self._act_error("El costo es obligatorio y no puede ser negativo.")
            a[AF["costo"]] = costo
        if alta or "area" in d or "ubicacion" in d:
            ubic, area = str(d.get("ubicacion") or "").strip(), str(d.get("area") or "").strip()
            if not (ubic and area):
                self._act_error("Selecciona la ubicación y el área.")
            a[self.AREAS_DE_LAS_UBICACIONES_CAT_OBJ_ID] = {AF["ubicacion"]: ubic, AF["area"]: area}
        if alta or "foto" in d:
            foto = d.get("foto")
            if not (isinstance(foto, dict) and str(foto.get("file_url") or "").startswith("http")):
                self._act_error("Falta la foto del activo (name y file_url).")
            a[AF["imagen"]] = [{"file_name": foto.get("name") or foto["file_url"].rsplit("/", 1)[-1],
                                "file_url": foto["file_url"]}]
        inventario = (d.get("inventario") or "Único") if (alta or "inventario" in d) else \
            ("Stock" if a.get(AF["inventario"]) == "stock" else "Único")
        if inventario not in INVENTARIOS:
            self._act_error("Inventario: Único o Stock.")
        if clase != "Herramienta" and inventario == "Stock":
            self._act_error("Vehículos y equipos son siempre Único.")
        a[AF["inventario"]] = INVENTARIOS[inventario]
        if inventario == "Stock":
            cant = _int(d.get("cantidad") if "cantidad" in d else a.get(fa["cantidad"]), 0)
            if cant <= 0:
                self._act_error("Con inventario Stock la cantidad en existencia debe ser mayor a 0.")
            a[fa["cantidad"]] = cant
        else:
            a.pop(fa["cantidad"], None)
        for k in ("marca", "modelo"):
            if k in d:
                pon(AF[k], str(d.get(k) or "").strip() or None)
        for k in ("adquisicion", "ultimo_mantenimiento"):
            if k in d:
                f = _fecha(d.get(k))
                if d.get(k) and not f:
                    self._act_error(f"{k} no es una fecha válida (YYYY-MM-DD).")
                pon(AF[k], f.isoformat() if f else None)
        if clase == "Vehículo" and isinstance(d.get("vehiculo"), dict):
            v = d["vehiculo"]
            if v.get("tipo") or v.get("marca") or v.get("modelo"):
                a[self.AF.TIPO_DE_VEHICULO_OBJ_ID] = {
                    AF["tipo_vehiculo"]: v.get("tipo") or "",
                    AF["marca_vehiculo"]: v.get("marca") or d.get("marca") or "",
                    AF["modelo_vehiculo"]: v.get("modelo") or d.get("modelo") or ""}
            for k in ("serie_chasis", "serie_motor1", "serie_motor2"):
                if k in v:
                    pon(AF[k], str(v.get(k) or "").strip() or None)
            for k, kf in (("kilometraje", "km"), ("horometro", "horometro"), ("kilometraje2", "km2"),
                          ("horometro2", "horometro2")):
                if isinstance(v.get(k), dict):
                    pon(AF[kf], _num(v[k].get("valor")))
                    f = _fecha(v[k].get("fecha"))
                    pon(AF[f"{kf}_fecha"], f.isoformat() if f else None)
        elif clase != "Vehículo":
            a.pop(self.AF.TIPO_DE_VEHICULO_OBJ_ID, None)
        if "asignado_id" in d:
            if d.get("asignado_id"):
                if a.get(AF["estado"]) == "inactivo":
                    self._act_error("Un activo inactivo no se puede asignar.", 409)
                e, _ = self._emp_get(str(d["asignado_id"]))
                a[fa["asignado_id"]] = str(e["_id"])
                a[fa["asignado"]] = (e.get("answers") or {}).get(self.Employee.employee_fields["worker_name"]) or ""
            else:
                a.pop(fa["asignado_id"], None)
                a.pop(fa["asignado"], None)
        if d.get("lectura_ia") is not None:
            a[fa["lectura_ia"]] = simplejson.dumps(d["lectura_ia"], ensure_ascii=False)[:20000]
        return a

    def _act_siguiente_folio(self, campo, prefijo, form_id):
        n = 0
        for r in self._ctr_find(form_id):
            m = re.match(rf"^{prefijo}-(\d+)$", str((r.get("answers") or {}).get(campo) or ""))
            if m:
                n = max(n, int(m.group(1)))
        return f"{prefijo}-{n + 1:04d}"

    # ------------------------------------------------------------- API

    def get_opciones_activo(self):
        """Catálogos del formulario: áreas por ubicación y vehículos (tipo → marca → modelo)."""
        areas, vehiculos = {}, {}
        try:
            for r in self.lkf_api.search_catalog(self.AREAS_DE_LAS_UBICACIONES_CAT_ID, {}) or []:
                u, ar = r.get(AF["ubicacion"]), r.get(AF["area"])
                if u and ar:
                    areas.setdefault(u, set()).add(ar)
        except Exception:  # noqa: BLE001
            pass
        try:
            for r in self.lkf_api.search_catalog(self.AF.TIPO_DE_VEHICULO_ID, {}) or []:
                t, m, mo = r.get(AF["tipo_vehiculo"]), r.get(AF["marca_vehiculo"]), r.get(AF["modelo_vehiculo"])
                if t:
                    vehiculos.setdefault(t, {}).setdefault(m or "", set()).add(mo or "")
        except Exception:  # noqa: BLE001
            pass
        return {
            "ubicaciones": [{"ubicacion": u, "areas": sorted(v)} for u, v in sorted(areas.items())],
            "vehiculos": [{"tipo": t, "marcas": [{"marca": m, "modelos": sorted(x for x in mo if x)}
                                                  for m, mo in sorted(ms.items()) if m]}
                          for t, ms in sorted(vehiculos.items())],
            "clases": CLASES, "inventarios": list(INVENTARIOS), "prioridades": PRIORIDADES,
        }

    def list_activos(self, clase=None, disponible=None, estado=None, inventario=None, ubicacion=None,
                     mantenimiento_desde=None, mantenimiento_hasta=None, search=None, limit=25, offset=0):
        if not self.ACTIVOS_FORM:
            return {"items": [], "total": 0}
        empresa_id, es_propia = self._act_empresa()
        rows = self._ctr_find(self.ACTIVOS_FORM, self._act_match(empresa_id, es_propia), sort=[("created_at", -1)])
        abiertos = self._mant_abiertos([str(r["_id"]) for r in rows])
        items = [self.act_out(r, abiertos.get(str(r["_id"]), 0)) for r in rows]
        txt = (search or "").strip().lower()

        def ok(x):
            if clase and x["clase"] != clase:
                return False
            if disponible is not None and disponible != "" and x["disponible"] != (str(disponible).lower() in ("true", "1", "disponible")):
                return False
            if estado and x["estado"] != estado:
                return False
            if inventario and x["inventario"] != inventario:
                return False
            if ubicacion and x["ubicacion"] != ubicacion:
                return False
            um = (x["ultimo_mantenimiento"] or "")[:10]
            if mantenimiento_desde and (not um or um < str(mantenimiento_desde)):
                return False
            if mantenimiento_hasta and (not um or um > str(mantenimiento_hasta)):
                return False
            return not txt or any(txt in str(v or "").lower() for v in (x["nombre"], x["folio"], x["marca"], x["modelo"],
                                                                        (x["asignado"] or {}).get("nombre")))
        items = [x for x in items if ok(x)]
        off, lim = max(0, _int(offset)), max(1, min(_int(limit, 25), 200))
        return {"items": items[off:off + lim], "total": len(items)}

    def get_activo(self, activo_id):
        rec = self._act_get(activo_id)
        return self.act_out(rec, self._mant_abiertos([str(rec["_id"])]).get(str(rec["_id"]), 0))

    def create_activo(self, activo):
        self._act_requiere()
        d = activo if isinstance(activo, dict) else {}
        fa = self.ctr_f["activos_fijos"]
        empresa_id, es_propia = self._act_empresa()
        a = self._act_answers_in(d)
        empresa = self._ctr_empresa_ref(empresa_id, {})
        a.update({fa["empresa_id"]: empresa_id, fa["empresa"]: empresa.get("razon_social") or "",
                  fa["folio"]: self._act_siguiente_folio(fa["folio"], "A", self.ACTIVOS_FORM),
                  AF["estado"]: "activo", AF["disponible"]: "disponible"})
        activo_id = self._ctr_post(self.ACTIVOS_FORM, a, "create_activo")
        if not activo_id:
            self._act_error("LinkaForm no regresó el id del activo.", 500)
        return self.get_activo(activo_id)

    def update_activo(self, activo_id, cambios):
        rec = self._act_get(activo_id)
        d = cambios if isinstance(cambios, dict) else {}
        fa = self.ctr_f["activos_fijos"]
        a = self._act_answers_in(d, rec.get("answers") or {})
        if not a.get(fa["asignado_id"]) and a.get(AF["estado"]) != "inactivo":
            self._act_error("Selecciona a quién se asigna.")
        self._ctr_patch(self.ACTIVOS_FORM, str(rec["_id"]), a, "update_activo")
        return self.get_activo(str(rec["_id"]))

    def change_estado_activo(self, activo_id, estado):
        if estado not in ("Activo", "Inactivo"):
            self._act_error("estado debe ser Activo o Inactivo.")
        rec = self._act_get(activo_id)
        a = dict(rec.get("answers") or {})
        a[AF["estado"]] = estado.lower()
        if estado == "Inactivo":
            a[AF["disponible"]] = "no_disponible"
        elif not self._act_concesiones(rec, solo_abiertas=True):
            a[AF["disponible"]] = "disponible"
        self._ctr_patch(self.ACTIVOS_FORM, str(rec["_id"]), a, "change_estado_activo")
        return self.get_activo(str(rec["_id"]))

    def delete_activo(self, activo_id):
        rec = self._act_get(activo_id)
        if self._act_concesiones(rec):
            self._act_error("El activo tiene concesiones: desactívalo en lugar de eliminarlo.", 409)
        if self._mant_abiertos([str(rec["_id"])]).get(str(rec["_id"])):
            self._act_error("El activo tiene mantenimientos abiertos.", 409)
        self.lkf_api.patch_record_list({"deleted_objects": [f"/api/infosync/form_answer/{rec['_id']}/"]})
        return {"eliminado": str(rec["_id"]), "folio": (rec.get("answers") or {}).get(self.ctr_f["activos_fijos"]["folio"]) or ""}

    # ------------------------------------------------------- concesiones

    def _act_concesiones(self, rec, solo_abiertas=False):
        """Concesiones que incluyen el activo (se empatan por nombre del equipo)."""
        form = getattr(self, "CONCESSIONED_ARTICULOS", None)
        nombre = (rec.get("answers") or {}).get(AF["nombre"])
        if not (form and nombre):
            return []
        cf = self.cons_f
        rows = self._ctr_find(form, {f"answers.{cf['grupo_equipos']}.{cf['nombre_equipo']}": nombre},
                              sort=[("created_at", -1)])
        out = []
        for r in rows:
            a = r.get("answers") or {}
            for g in a.get(cf["grupo_equipos"]) or []:
                eq = g.get(cf["equipo_catalog_concesion"]) or {}
                if eq.get(cf["_nombre_equipo"]) != nombre:
                    continue
                persona = (a.get(cf["persona_catalog_concesion"]) or {}).get(cf["_persona_nombre_concesion"]) \
                    or a.get(cf["persona_nombre_otro"]) or ""
                estatus = g.get(cf["estatus_equipo"]) or a.get(cf["status_concesion"]) or ""
                item = {"id": str(r["_id"]), "folio": r.get("folio") or "",
                        "persona": persona[0] if isinstance(persona, list) else persona,
                        "estatus": str(estatus).replace("_", " ").capitalize(),
                        "piezas": _int(g.get(cf["cantidad_equipo_concesion"]), 1),
                        "fecha": a.get(cf["fecha_concesion"]) or None,
                        "devolucion": a.get(cf["fecha_devolucion_concesion"]) or None}
                if solo_abiertas and item["estatus"].lower() not in ("en prestamo", "en préstamo", "abierto", "abierta"):
                    continue
                out.append(item)
        return out

    def list_concesiones_activo(self, activo_id):
        return self._act_concesiones(self._act_get(activo_id))

    # ------------------------------------------------------------ IA foto

    def analizar_foto_activo(self, archivo, model=None):
        """Identifica nombre, tipo, marca y modelo de la foto. No guarda nada."""
        if not isinstance(archivo, dict) or not str(archivo.get("file_url") or "").startswith("http"):
            self._act_error("Falta la foto (file_url) a analizar.")
        nombre = (archivo.get("name") or archivo["file_url"]).lower()
        if not re.search(r"\.(jpe?g|png)(\?|$)", nombre) and not re.search(r"\.(jpe?g|png)(\?|$)", archivo["file_url"].lower()):
            self._act_error("La foto debe ser JPG o PNG.")
        if not self.ai:
            self._act_error("La IA (OpenRouter) no está configurada en esta cuenta.", 409)
        try:
            resp = requests.get(archivo["file_url"], timeout=30, headers={"User-Agent": "Clave10/1.0 (activos)"})
            resp.raise_for_status()
        except Exception as e:  # noqa: BLE001
            self._act_error(f"No se pudo bajar la foto: {str(e)[:200]}", 502)
        if len(resp.content) > MAX_IMG_BYTES:
            self._act_error("La foto pesa más de 10 MB.", 413)
        mime = "image/png" if nombre.endswith(".png") or resp.content[:4] == b"\x89PNG" else "image/jpeg"
        url = f"data:{mime};base64,{base64.b64encode(resp.content).decode()}"
        from .contratistas_documentos_ia import MAX_TOKENS, MODELO
        self.ai.headers["X-Title"] = "Clave10: Contratistas activos"
        try:
            raw = self.ai.post(messages=[{"role": "system", "content": SYSTEM_FOTO},
                                         {"role": "user", "content": [{"type": "image_url", "image_url": {"url": url}},
                                                                      {"type": "text", "text": PROMPT_FOTO}]}],
                               model=model or MODELO, max_tokens=MAX_TOKENS, temperature=0,
                               extra={"reasoning": {"effort": "minimal"}})
            ia = self.ai._parse_json(raw)["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            self._act_error(f"No se pudo leer la foto con IA: {str(e)[:300]}", 502)
        ia = ia if isinstance(ia, dict) else {}
        conf = ia.get("confianza") if isinstance(ia.get("confianza"), dict) else {}
        c = lambda k: max(0, min(100, _int(conf.get(k), 0)))  # noqa: E731
        legible = bool(ia.get("legible"))
        campos = {}
        if legible:
            for k in ("nombre", "marca", "modelo"):
                if ia.get(k):
                    campos[k] = {"valor": str(ia[k]).strip(), "confianza": c(k)}
            if ia.get("clase") in CLASES:
                campos["clase"] = {"valor": ia["clase"], "confianza": c("clase")}
            if ia.get("tipo_vehiculo") and ia.get("clase") == "Vehículo":
                campos["tipo_vehiculo"] = {"valor": str(ia["tipo_vehiculo"]), "confianza": c("clase")}
        return {"legible": legible, "identificado": (campos.get("nombre") or {}).get("valor"),
                "modelo_detectado": "modelo" in campos, "campos": campos}

    # ------------------------------------------------------ mantenimientos

    def _mant_requiere(self):
        if not getattr(self, "MANTENIMIENTOS_FORM", None):
            self._act_error("La forma Mantenimientos de activos no está instalada en esta cuenta.", 409)

    def _mant_abiertos(self, activo_ids):
        if not (getattr(self, "MANTENIMIENTOS_FORM", None) and activo_ids):
            return {}
        fm = self.ctr_f["mantenimientos_de_activos"]
        out = {}
        for r in self._ctr_find(self.MANTENIMIENTOS_FORM, {f"answers.{fm['activo_id']}": {"$in": [str(i) for i in activo_ids]},
                                                           f"answers.{fm['estatus']}": {"$ne": opt("Cerrada")}}):
            k = str((r.get("answers") or {}).get(fm["activo_id"]))
            out[k] = out.get(k, 0) + 1
        return out

    def mant_out(self, rec):
        fm = self.ctr_f["mantenimientos_de_activos"]
        a = rec.get("answers") or {}
        return {
            "id": str(rec["_id"]),
            "folio": a.get(fm["folio"]) or "",
            "activo": {"id": str(a.get(fm["activo_id"]) or ""), "nombre": a.get(fm["activo"]) or ""},
            "asignado": {"id": str(a.get(fm["asignado_id"]) or ""), "nombre": a.get(fm["asignado"]) or ""},
            "prioridad": label(PRIORIDADES, a.get(fm["prioridad"])) or "Media",
            "fecha_limite": a.get(fm["fecha_limite"]) or None,
            "descripcion": a.get(fm["descripcion"]) or "",
            "estatus": label(ESTATUS_MANT, a.get(fm["estatus"])) or "Abierta",
            "fecha_cierre": a.get(fm["fecha_cierre"]) or None,
            "historial": [{
                "estatus": label(ESTATUS_MANT, h.get(fm["historial_estatus"])) or "",
                "comentario": h.get(fm["historial_comentario"]) or "",
                "evidencias": [self._ctr_archivo(x) for x in (h.get(fm["historial_evidencias"]) or []) if self._ctr_archivo(x)],
                "autor": h.get(fm["historial_autor"]) or "",
                "fecha": h.get(fm["historial_fecha"]) or "",
            } for h in a.get(fm["historial"]) or []],
        }

    def _mant_get(self, mantenimiento_id):
        self._mant_requiere()
        rec = self._ctr_get(self.MANTENIMIENTOS_FORM, str(mantenimiento_id or ""))
        if not rec:
            self._act_error("El mantenimiento no existe.", 404)
        self._act_get((rec.get("answers") or {}).get(self.ctr_f["mantenimientos_de_activos"]["activo_id"]))
        return rec

    def _mant_renglon(self, estatus, comentario, evidencias):
        fm = self.ctr_f["mantenimientos_de_activos"]
        files = [{"file_name": e.get("name") or e["file_url"].rsplit("/", 1)[-1], "file_url": e["file_url"]}
                 for e in evidencias or [] if isinstance(e, dict) and str(e.get("file_url") or "").startswith("http")]
        return {fm["historial_estatus"]: opt(estatus), fm["historial_comentario"]: (comentario or "").strip(),
                fm["historial_evidencias"]: files, fm["historial_autor"]: self._ctr_autor(),
                fm["historial_fecha"]: self._doc_ahora()}

    def list_mantenimientos(self, activo_id):
        self._act_get(activo_id)
        if not getattr(self, "MANTENIMIENTOS_FORM", None):
            return []
        fm = self.ctr_f["mantenimientos_de_activos"]
        rows = self._ctr_find(self.MANTENIMIENTOS_FORM, {f"answers.{fm['activo_id']}": str(activo_id)},
                              sort=[("created_at", -1)])
        return [self.mant_out(r) for r in rows]

    def save_mantenimiento(self, mantenimiento, mantenimiento_id=None):
        """Alta (con comentario y evidencias iniciales) o edición de asignado, prioridad, fecha y descripción."""
        self._mant_requiere()
        d = mantenimiento if isinstance(mantenimiento, dict) else {}
        fm = self.ctr_f["mantenimientos_de_activos"]
        if mantenimiento_id:
            rec = self._mant_get(mantenimiento_id)
            a = dict(rec.get("answers") or {})
            if label(ESTATUS_MANT, a.get(fm["estatus"])) == "Cerrada":
                self._act_error("Un mantenimiento cerrado no se edita.", 409)
        else:
            act = self._act_get(d.get("activo_id"))
            if (act.get("answers") or {}).get(AF["estado"]) == "inactivo":
                self._act_error("Un activo inactivo no se puede asignar.", 409)
            empresa_id, _ = self._act_empresa()
            a = {fm["folio"]: self._act_siguiente_folio(fm["folio"], "M", self.MANTENIMIENTOS_FORM),
                 fm["activo_id"]: str(act["_id"]), fm["activo"]: (act.get("answers") or {}).get(AF["nombre"]) or "",
                 fm["empresa_id"]: empresa_id, fm["empresa"]: self._ctr_empresa_ref(empresa_id, {}).get("razon_social") or "",
                 fm["estatus"]: opt("Abierta")}
        if not mantenimiento_id or "asignado_id" in d:
            if not d.get("asignado_id"):
                self._act_error("Selecciona a quién se asigna el mantenimiento.")
            e, _ = self._emp_get(str(d["asignado_id"]))
            a[fm["asignado_id"]] = str(e["_id"])
            a[fm["asignado"]] = (e.get("answers") or {}).get(self.Employee.employee_fields["worker_name"]) or ""
        if not mantenimiento_id or "prioridad" in d:
            if d.get("prioridad") not in PRIORIDADES:
                self._act_error("Prioridad: Alta, Media o Baja.")
            a[fm["prioridad"]] = opt(d["prioridad"])
        if not mantenimiento_id or "fecha_limite" in d:
            f = _fecha(d.get("fecha_limite"))
            if not f:
                self._act_error("La fecha límite es obligatoria (YYYY-MM-DD).")
            a[fm["fecha_limite"]] = f.isoformat()
        if "descripcion" in d:
            a[fm["descripcion"]] = (d.get("descripcion") or "").strip()
        if mantenimiento_id:
            self._ctr_patch(self.MANTENIMIENTOS_FORM, str(mantenimiento_id), a, "update_mantenimiento")
            return self.mant_out(self._ctr_get(self.MANTENIMIENTOS_FORM, str(mantenimiento_id)))
        a[fm["historial"]] = [self._mant_renglon("Abierta", d.get("comentario"), d.get("evidencias"))]
        mid = self._ctr_post(self.MANTENIMIENTOS_FORM, a, "create_mantenimiento")
        if not mid:
            self._act_error("LinkaForm no regresó el id del mantenimiento.", 500)
        return self.mant_out(self._ctr_get(self.MANTENIMIENTOS_FORM, mid))

    def change_status_mantenimiento(self, mantenimiento_id, estatus, comentario="", evidencias=None):
        if estatus not in ESTATUS_MANT:
            self._act_error("Estatus: Abierta, En proceso o Cerrada.")
        rec = self._mant_get(mantenimiento_id)
        fm = self.ctr_f["mantenimientos_de_activos"]
        a = dict(rec.get("answers") or {})
        a[fm["estatus"]] = opt(estatus)
        a[fm["historial"]] = list(a.get(fm["historial"]) or []) + [self._mant_renglon(estatus, comentario, evidencias)]
        if estatus == "Cerrada":
            a[fm["fecha_cierre"]] = self._doc_ahora()
        else:
            a.pop(fm["fecha_cierre"], None)
        self._ctr_patch(self.MANTENIMIENTOS_FORM, str(rec["_id"]), a, "change_status_mantenimiento")
        if estatus == "Cerrada":
            act = self._ctr_get(self.ACTIVOS_FORM, str(a.get(fm["activo_id"])))
            if act:
                aa = dict(act.get("answers") or {})
                aa[AF["ultimo_mantenimiento"]] = self._ctr_hoy().isoformat()
                self._ctr_patch(self.ACTIVOS_FORM, str(act["_id"]), aa, "cierre_mantenimiento")
        return self.mant_out(self._ctr_get(self.MANTENIMIENTOS_FORM, str(rec["_id"])))

    def delete_mantenimiento(self, mantenimiento_id):
        rec = self._mant_get(mantenimiento_id)
        self.lkf_api.patch_record_list({"deleted_objects": [f"/api/infosync/form_answer/{rec['_id']}/"]})
        return {"eliminado": str(rec["_id"])}
