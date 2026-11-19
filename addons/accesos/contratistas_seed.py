# -*- coding: utf-8 -*-
"""Datos iniciales de Contratistas por cuenta (F0-02). Idempotente.

- Los requerimientos de cumplimiento documental de ME-07 (SAT, IMSS, INFONAVIT):
  se crean solo los que no existen (por nombre).
- La empresa propia de la cuenta (es_propia = Sí): se crea solo si no hay una.
  La plataforma no expone la razón social de la cuenta, así que se pasa.

Uso desde el contenedor de Sanic, con la cuenta activa:
    service = get_module_class('Accesos')(settings)
    seed_contratistas(service, razon_social='…', rfc='…')
"""
import re
import unicodedata

PROPS = {
    "device_properties": {
        "System": "Script",
        "Module": "Accesos",
        "Process": "Contratistas · datos iniciales",
        "Action": "seed_contratistas",
        "File": "accesos/contratistas_seed.py",
    }
}

MESES_CUATRIMESTRE = ["enero", "mayo", "septiembre"]

# Obligaciones de ME-07: ámbito Empresa, por periodo, con acuse.
REQUERIMIENTOS_ME07 = [
    ("Opinión de cumplimiento SAT 32-D", "SAT", "Mensual", None),
    ("Opinión de cumplimiento IMSS", "IMSS", "Mensual", None),
    ("Opinión de cumplimiento INFONAVIT", "INFONAVIT", "Mensual", None),
    ("CFDI de nómina", "SAT", "Mensual", None),
    ("DIOT", "SAT", "Mensual", None),
    ("ICSOE", "IMSS", "Cuatrimestral", MESES_CUATRIMESTRE),
    ("SISUB", "INFONAVIT", "Cuatrimestral", MESES_CUATRIMESTRE),
]


def opt(label):
    """Valor que guarda LinkaForm para una opción (mismo slug que el XML)."""
    s = unicodedata.normalize("NFD", label).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def _existing(service, form_id, field_id):
    query = [
        {"$match": {"form_id": form_id, "deleted_at": {"$exists": False}}},
        {"$project": {"_id": 0, "v": f"$answers.{field_id}"}},
    ]
    return [r.get("v") for r in service.cr.aggregate(query)]


def _post(service, form_id, answers):
    metadata = service.lkf_api.get_metadata(form_id=form_id)
    metadata.update({"properties": PROPS, "answers": answers})
    res = service.lkf_api.post_forms_answers(metadata)
    if res.get("status_code") not in (200, 201, 202):
        raise RuntimeError(f"No se pudo crear el registro en {form_id}: {res}")
    return res


def seed_requerimientos(service):
    f = service.ctr_f["requerimientos_de_cumplimiento"]
    form_id = service.REQUERIMIENTOS_FORM
    if not form_id:
        raise RuntimeError("La forma requerimientos_de_cumplimiento no está instalada en esta cuenta")
    ya = set(_existing(service, form_id, f["nombre"]))
    creados = []
    for nombre, plataforma, periodicidad, meses in REQUERIMIENTOS_ME07:
        if nombre in ya:
            continue
        answers = {
            f["nombre"]: nombre,
            f["tipo"]: opt("Documento"),
            f["ambito"]: opt("Empresa"),
            f["plataforma"]: opt(plataforma),
            f["vigencia_modo"]: opt("Periodo"),
            f["periodicidad"]: opt(periodicidad),
            f["dia_limite"]: 17,
            f["requiere_acuse"]: opt("Sí"),
            f["limitante"]: opt("No"),
            f["estatus"]: opt("Activo"),
        }
        if meses:
            answers[f["meses_periodo"]] = meses
        _post(service, form_id, answers)
        creados.append(nombre)
    return creados


def seed_empresa_propia(service, razon_social, rfc, tipo_persona="Moral"):
    f = service.ctr_f["empresas"]
    form_id = service.EMPRESAS_FORM
    if not form_id:
        raise RuntimeError("La forma empresas no está instalada en esta cuenta")
    if opt("Sí") in _existing(service, form_id, f["es_propia"]):
        return None
    folios = [x for x in _existing(service, form_id, f["folio"]) if isinstance(x, str) and x.startswith("CL-")]
    folio = f"CL-{len(folios) + 1:04d}"
    _post(service, form_id, {
        f["folio"]: folio,
        f["razon_social"]: razon_social,
        f["rfc"]: rfc.upper(),
        f["tipo_persona"]: opt(tipo_persona),
        f["repse_estatus"]: opt("Sin REPSE"),
        f["es_propia"]: opt("Sí"),
        f["estatus"]: opt("Activo"),
    })
    return folio


def seed_contratistas(service, razon_social=None, rfc=None):
    out = {"requerimientos_creados": seed_requerimientos(service)}
    if razon_social and rfc:
        out["empresa_propia"] = seed_empresa_propia(service, razon_social, rfc)
    return out
