# -*- coding: utf-8 -*-
"""Mi Empresa · Generales y contactos de Contratistas (ME-01-B).

Spec: clave10-sdk/specs/empresa/empresa-001-modelo-de-datos.md (forma Empresas).
Ficha: lkf-claude contratistas_me01_generales.md. Contrato con el front:
Empresa / Contacto en clave10/src/types/contratistas/empresa.ts.

- get_mi_empresa: la empresa activa del usuario. get_empresa: otra empresa,
  solo si hay relación directa con la activa (solo lectura).
- update_mi_empresa solo cambia razón social, RFC (mayúsculas, único entre
  activas), objeto social y domicilio fiscal; el resto de llaves se ignora.
- REPSE: estatus calculado al leer (Por vencer = 60 días o menos) y guardado
  al editar. Trabajadores registrados = suma de los registros patronales.
- Contactos: grupo repetible sin id, se editan y borran por índice.
"""
import re

from .contratistas_contratos import _fecha, _int, label, opt
from .contratistas_registro import DOMICILIO, EMAIL_RE, RFC_FISICA, RFC_MORAL

DIAS_REPSE_POR_VENCER = 60
ROLES_CONTACTO = ["Representante legal", "Apoderado legal", "Contacto"]
TIPOS_PERSONA = {"moral": "Moral", "fisica": "Física"}
EDITABLES = ("razon_social", "rfc", "objeto_social", "domicilio_fiscal")


def repse_out(f, a, hoy):
    """REPSE de un registro de Empresas con estatus, días y % transcurrido."""
    folio = a.get(f["repse_folio"]) or ""
    ini, fin = _fecha(a.get(f["repse_inicio"])), _fecha(a.get(f["repse_fin"]))
    if not folio or not fin:
        return {"folio": folio, "inicio": ini.isoformat() if ini else "", "fin": fin.isoformat() if fin else "",
                "estatus": "Sin REPSE", "dias_restantes": 0}
    dias = (fin - hoy).days
    out = {"folio": folio, "inicio": ini.isoformat() if ini else "", "fin": fin.isoformat(),
           "estatus": "Vencido" if dias < 0 else "Por vencer" if dias <= DIAS_REPSE_POR_VENCER else "Vigente",
           "dias_restantes": dias}
    if ini and fin > ini:
        out["transcurrido_pct"] = max(0, min(100, round((hoy - ini).days * 100 / (fin - ini).days)))
    return out


class EmpresaMixin:
    """Se mezcla en Accesos junto con ContratosMixin."""

    def _emp_e_error(self, msg, status=400):
        return self.LKFException({"title": "Mi Empresa", "msg": msg, "status_code": status})

    def empresa_out(self, rec):
        f = self.ctr_f["empresas"]
        a = rec.get("answers") or {}
        dom = {k: a.get(f[f"domicilio_{k}"]) for k in DOMICILIO if a.get(f[f"domicilio_{k}"])}
        repse = repse_out(f, a, self._ctr_hoy())
        aviso = self._ctr_archivo(a.get(f["repse_aviso"]))
        if aviso:
            repse["aviso"] = aviso
        acta = {k: a.get(f[f"acta_{k}"]) or "" for k in
                ("num_escritura", "fecha_protocolizacion", "notario", "num_notaria", "entidad")}
        nrps = [{"nrp": g.get(f["nrp"]) or "", "descripcion": g.get(f["nrp_descripcion"]) or None,
                 "trabajadores_registrados": _int(g.get(f["nrp_trabajadores"]), 0)
                 if g.get(f["nrp_trabajadores"]) not in (None, "") else None}
                for g in a.get(f["registros_patronales"]) or []]
        cargados = [n["trabajadores_registrados"] for n in nrps if n["trabajadores_registrados"] is not None]
        tipo = label(list(TIPOS_PERSONA.values()), a.get(f["tipo_persona"])) or "Moral"
        out = {
            "id": str(rec["_id"]), "folio": a.get(f["folio"]) or "",
            "razon_social": a.get(f["razon_social"]) or "", "nombre_comercial": a.get(f["nombre_comercial"]) or None,
            "rfc": a.get(f["rfc"]) or "", "tipo_persona": "fisica" if tipo == "Física" else "moral",
            "curp": a.get(f["curp"]) or None, "regimen_fiscal": a.get(f["regimen_fiscal"]) or None,
            "actividad_preponderante": a.get(f["actividad_preponderante"]) or None,
            "objeto_social": a.get(f["objeto_social"]) or None,
            "estatus_sat": label(["Activo", "Inactivo"], a.get(f["estatus_sat"])),
            "domicilio_fiscal": dom or None,
            "repse": repse,
            "actividades_stps": [{"clave": g.get(f["actividad_clave"]) or "",
                                  "descripcion": g.get(f["actividad_descripcion"]) or ""}
                                 for g in a.get(f["actividades_stps"]) or []],
            "acta": {**acta, **({"archivo": self._ctr_archivo(a.get(f["acta_archivo"]))}
                                if a.get(f["acta_archivo"]) else {})} if any(acta.values()) else None,
            "registros_patronales": [{k: v for k, v in n.items() if v is not None} for n in nrps],
            "trabajadores_registrados": sum(cargados) if cargados else None,
            "contactos": [{"indice": i, "nombre": c.get(f["contacto_nombre"]) or "",
                           "rol": label(ROLES_CONTACTO, c.get(f["contacto_rol"])) or "Contacto",
                           "telefono": c.get(f["contacto_telefono"]) or None,
                           "email": c.get(f["contacto_email"]) or None}
                          for i, c in enumerate(a.get(f["contactos"]) or [])],
            "logo": self._ctr_archivo(a.get(f["logo"])),
            "es_propia": a.get(f["es_propia"]) == opt("Sí"),
            "estatus": "Inactivo" if a.get(f["estatus"]) == opt("Inactivo") else "Activo",
        }
        out["contactos"] = [{k: v for k, v in c.items() if v is not None} for c in out["contactos"]]
        return {k: v for k, v in out.items() if v is not None or k == "trabajadores_registrados"}

    def _emp_e_mia(self):
        rec = self._ctr_get(self.EMPRESAS_FORM, self.ctr_empresa_activa_id()) if self.EMPRESAS_FORM else None
        if not rec:
            self._emp_e_error("Tu empresa no está registrada en la forma Empresas.", 409)
        return rec

    def _emp_e_guardar(self, rec, a, accion):
        f = self.ctr_f["empresas"]
        repse = repse_out(f, a, self._ctr_hoy())  # estatus calculado se guarda (convención 9)
        a[f["repse_estatus"]] = opt(repse["estatus"])
        self._ctr_patch(self.EMPRESAS_FORM, str(rec["_id"]), a, accion)
        return self.empresa_out(self._ctr_get(self.EMPRESAS_FORM, str(rec["_id"])))

    # ---------------------------------------------------------------- API

    def get_mi_empresa(self):
        return self.empresa_out(self._emp_e_mia())

    def get_empresa(self, empresa_id):
        """Contraparte (detalle de cliente/contratista): solo con relación directa."""
        mi = self.ctr_empresa_activa_id()
        empresa_id = str(empresa_id or "")
        if empresa_id and empresa_id != mi:
            fr = self.ctr_f["relaciones_entre_empresas"]
            rel = self._ctr_find(self.RELACIONES_FORM, {"$or": [
                {f"answers.{fr['cliente_id']}": mi, f"answers.{fr['contratista_id']}": empresa_id},
                {f"answers.{fr['contratista_id']}": mi, f"answers.{fr['cliente_id']}": empresa_id}]},
                one=True) if self.RELACIONES_FORM else None
            if not rel:
                self._emp_e_error("No tienes acceso a esa empresa.", 403)
        rec = self._ctr_get(self.EMPRESAS_FORM, empresa_id or mi)
        if not rec:
            self._emp_e_error("La empresa no existe.", 404)
        return self.empresa_out(rec)

    def update_mi_empresa(self, empresa):
        """Solo razón social, RFC, objeto social y domicilio fiscal."""
        e = empresa if isinstance(empresa, dict) else {}
        rec = self._emp_e_mia()
        f = self.ctr_f["empresas"]
        a = dict(rec.get("answers") or {})
        errores = []
        if "razon_social" in e:
            razon = " ".join(str(e.get("razon_social") or "").split())
            if not razon:
                errores.append("La razón social es obligatoria.")
            a[f["razon_social"]] = razon
        if "rfc" in e:
            rfc = re.sub(r"\s+", "", str(e.get("rfc") or "")).upper()
            fisica = a.get(f["tipo_persona"]) == opt("Física")
            if rfc == str(a.get(f["rfc"]) or "").upper():
                pass  # sin cambio (p. ej. el RFC genérico del seed)
            elif not (RFC_FISICA if fisica else RFC_MORAL).match(rfc):
                errores.append(f"El RFC debe tener {13 if fisica else 12} caracteres válidos "
                               f"(persona {'física' if fisica else 'moral'}).")
            else:
                otra = self._ctr_find(self.EMPRESAS_FORM, {f"answers.{f['rfc']}": rfc,
                                                           f"answers.{f['estatus']}": {"$ne": opt("Inactivo")}})
                if any(str(x["_id"]) != str(rec["_id"]) for x in otra):
                    errores.append("Ya hay otra empresa registrada con ese RFC.")
            a[f["rfc"]] = rfc
        if "objeto_social" in e:
            a[f["objeto_social"]] = str(e.get("objeto_social") or "").strip()
        if "domicilio_fiscal" in e:
            d = e.get("domicilio_fiscal") if isinstance(e.get("domicilio_fiscal"), dict) else {}
            faltan = [k for k in ("cp", "vialidad", "municipio", "estado") if not str(d.get(k) or "").strip()]
            if faltan:
                errores.append(f"Domicilio fiscal: faltan {', '.join(faltan)}.")
            if d.get("cp") and not re.fullmatch(r"\d{5}", str(d["cp"]).strip()):
                errores.append("El código postal debe tener 5 dígitos.")
            for k in DOMICILIO:
                v = str(d.get(k) or "").strip()
                if v:
                    a[f[f"domicilio_{k}"]] = v
                else:
                    a.pop(f[f"domicilio_{k}"], None)
        if errores:
            self._emp_e_error("\n".join(errores))
        return self._emp_e_guardar(rec, a, "update_mi_empresa")

    def _emp_e_contacto_in(self, c):
        f = self.ctr_f["empresas"]
        c = c if isinstance(c, dict) else {}
        nombre = " ".join(str(c.get("nombre") or "").split())
        tel = re.sub(r"\D", "", str(c.get("telefono") or ""))
        email = str(c.get("email") or "").strip().lower()
        rol = c.get("rol") or "Contacto"
        errores = []
        if len(nombre) < 3:
            errores.append("El nombre completo debe tener al menos 3 caracteres.")
        if len(tel) < 10:
            errores.append("El teléfono debe tener al menos 10 dígitos.")
        if not EMAIL_RE.match(email):
            errores.append("El correo no es válido.")
        if rol not in ROLES_CONTACTO:
            errores.append(f"Cargo no válido: {rol}.")
        if errores:
            self._emp_e_error("\n".join(errores))
        return {f["contacto_nombre"]: nombre, f["contacto_rol"]: opt(rol), f["contacto_telefono"]: tel,
                f["contacto_email"]: email}

    def save_contacto(self, contacto, indice=None):
        """Alta (sin indice) o edición del contacto en esa posición."""
        rec = self._emp_e_mia()
        f = self.ctr_f["empresas"]
        a = dict(rec.get("answers") or {})
        contactos = list(a.get(f["contactos"]) or [])
        nuevo = self._emp_e_contacto_in(contacto)
        if indice is None or indice == "":
            contactos.append(nuevo)
        else:
            i = _int(indice, -1)
            if not 0 <= i < len(contactos):
                self._emp_e_error("El contacto no existe.", 404)
            contactos[i] = nuevo
        a[f["contactos"]] = contactos
        return self._emp_e_guardar(rec, a, "save_contacto")

    def delete_contacto(self, indice):
        rec = self._emp_e_mia()
        f = self.ctr_f["empresas"]
        a = dict(rec.get("answers") or {})
        contactos = list(a.get(f["contactos"]) or [])
        i = _int(indice, -1)
        if not 0 <= i < len(contactos):
            self._emp_e_error("El contacto no existe.", 404)
        contactos.pop(i)
        a[f["contactos"]] = contactos
        return self._emp_e_guardar(rec, a, "delete_contacto")
