# -*- coding: utf-8 -*-
import sys, simplejson
from datetime import datetime

from workflow_log_report import Reports

from account_settings import *

LINKA_RECORD_URL = "https://app.linkaform.com/#/records/detail/"

class WorkflowLogsReport(Reports):
    """
    Reporte de ejecuciones de workflows desde la colección workflow_log.
    Devuelve una lista con:
      - folio
      - record_status
      - workflow_rule_name (acción)
      - workflow_sucess
      - form_id
      - created_at (string YYYY-MM-DD HH:mm:ss)
      - link (URL directa al record)
    """

    def _get_date_query(self, date_from, date_to):
        """
        Construye filtro de fechas sobre created_at (Date).
        Acepta strings 'YYYY-MM-DD'. Devuelve dict parcial para $match.
        """
        q = {}
        if date_from:
            if isinstance(date_from, str):
                date_from = datetime.strptime(date_from, "%Y-%m-%d")
            q.setdefault("created_at", {})["$gte"] = date_from
        if date_to:
            if isinstance(date_to, str):
                # incluir todo el día -> fin: 23:59:59
                date_to = datetime.strptime(date_to, "%Y-%m-%d")
                # sumamos 1 día, y el operador < siguiente día
                from datetime import timedelta
                date_to = date_to + timedelta(days=1)
            q.setdefault("created_at", {})["$lt"] = date_to
        return q

    def query_workflow_logs(self, date_from=None, date_to=None, form_id=None, only_failed=True, limit=100):
        """
        Ejecuta el aggregation sobre workflow_log.
        """
        # --- Colección de workflow logs

        # --- Match base
        match_query = {}
        # Opcional: filtrar por form_id
        if form_id:
            try:
                # permitir int o str
                form_id = int(form_id)
            except Exception:
                pass
            match_query.update({"form_id": form_id})

        # Fechas
        date_q = self._get_date_query(date_from, date_to)
        if date_q:
            match_query.update(date_q)

        # Solo fallidos (workflow_sucess != true o no existe)
        if only_failed:
            match_query.update({
                "$or": [
                    {"workflow_sucess": {"$ne": True}},
                    {"workflow_sucess": {"$exists": False}}
                ]
            })

        pipeline = [
            {"$match": match_query},
            {
                "$project": {
                    "_id": 0,
                    "folio": {"$ifNull": ["$workflow_record_folio", "$folio"]},
                    "record_status": 1,
                    "workflow_rule_name": 1,
                    "workflow_sucess": 1,
                    "workflow_rule": 1,
                    "form_id": 1,
                    "name": 1,
                    "user_id": 1,
                    "workflow_response_content": 1,
                    # fecha legible
                    "created_at_str": {
                        "$dateToString": {"date": "$created_at", "format": "%Y-%m-%d %H:%M:%S", "timezone": "America/Monterrey"}
                    },
                    # link directo al record
                    "link": {
                        "$concat": [LINKA_RECORD_URL, {"$toString": "$record_id"}]
                    }
                }
            },
            {"$sort": {"created_at_str": -1}},
        ]

        if limit and isinstance(limit, int) and limit > 0:
            pipeline.append({"$limit": limit})
        print('pipeline=', simplejson.dumps(pipeline, indent=4))
        res = self.cr_wkf.aggregate(pipeline)
        return [x for x in res]

if __name__ == "__main__":
    # Inicializa estilo addons
    report_obj = WorkflowLogsReport(settings, sys_argv=sys.argv, use_api=True)
    report_obj.console_run()

    # Lee parámetros desde el payload del addon
    data = report_obj.data
    data = data.get("data", {}) if isinstance(data, dict) else {}

    # Filtros opcionales:
    date_from = data.get("date_from", "")      # "YYYY-MM-DD"
    date_to = data.get("date_to", "")          # "YYYY-MM-DD"
    form_id = data.get("form_id", None)        # ej. 64605
    only_failed = data.get("only_failed", True)  # True/False
    limit = data.get("limit", 1000)

    # Ejecuta query
    rows = report_obj.query_workflow_logs(
        date_from=date_from or None,
        date_to=date_to or None,
        form_id=form_id,
        only_failed=only_failed,
        limit=limit,
    )

    # Salida JSON (lista plana lista para tabla)
    sys.stdout.write(simplejson.dumps({
        "workflows": rows
    }))
