# coding: utf-8
"""
Buscador avanzado por facets (FacetSearch del front) para lkf_addons.

Antes vivía como métodos de Accesos (portado de lkf_addons/addons/accesos/app.py);
se separó para que otros servicios (Location) lo reutilicen. Se apoya solo en
self.cr (la colección de Mongo de Base).

Uso:

    from lkf_addons.tools.FacetSearchMixin import FacetSearchMixin

    class Location(FacetSearchMixin, Base):
        pass

Cada servicio define sus campos como {key: {label, paths, options?, value_match?, missing?}}
y expone get_search_fields_<x> / get_search_counts_<x> con estos helpers.
"""
import re
import unicodedata


class FacetSearchMixin:
    FACET_ACCENTS = {
        'a': 'aáàäâAÁÀÄÂ', 'e': 'eéèëêEÉÈËÊ', 'i': 'iíìïîIÍÌÏÎ',
        'o': 'oóòöôOÓÒÖÔ', 'u': 'uúùüûUÚÙÜÛ', 'n': 'nñNÑ',
    }

    def facet_regex(self, value):
        """Patrón contains que ignora acentos ("lucia" encuentra "Lucía")."""
        base = unicodedata.normalize('NFD', str(value).strip().lower())
        base = ''.join(c for c in base if unicodedata.category(c) != 'Mn')
        # "_" y espacio son equivalentes (muchos valores se guardan como "dia_de_la_semana").
        return ''.join(
            f"[{self.FACET_ACCENTS[c]}]" if c in self.FACET_ACCENTS
            else "[ _]" if c in " _"
            else re.escape(c)
            for c in base
        )

    def build_facets_match(self, fields_def, facets):
        """Regresa la lista de condiciones (para un $and) de los facets válidos."""
        conditions = []
        for facet in facets or []:
            field = fields_def.get(facet.get('key'))
            values = [v for v in (facet.get('values') or []) if str(v).strip()]
            if not field or not values:
                continue
            # exact = el valor completo (opciones del panel o de un enum), sin
            # importar mayúsculas ni acentos; si no, "contiene".
            # 'value_match': condición propia por valor exacto (ej. "con incidencias" Si/No).
            value_match = field.get('value_match')
            if facet.get('exact') and value_match:
                conds = [value_match[str(v).strip().lower()] for v in values if str(v).strip().lower() in value_match]
                if conds:
                    conditions.append(conds[0] if len(conds) == 1 else {'$or': conds})
                continue
            wrap = (lambda p: f"^{p}$") if facet.get('exact') else (lambda p: p)
            ors = [
                {path: {'$regex': wrap(self.facet_regex(v)), '$options': 'i'}}
                for path in field['paths'] for v in values
            ]
            # 'missing': valor que el listado muestra cuando el campo viene vacío
            # (ej. tipo_rondin vacío = "qr"); al filtrar por él también cuentan los vacíos.
            missing = field.get('missing')
            if facet.get('exact') and missing and any(self.facet_regex(v) == self.facet_regex(missing) for v in values):
                ors += [{path: {'$in': [None, '']}} for path in field['paths']]
            conditions.append(ors[0] if len(ors) == 1 else {'$or': ors})
        return conditions

    def facet_distinct_options(self, form_id, path, labels=None, order=None):
        """Opciones de un campo enum a partir de los valores que ya existen en la forma.
        labels: etiqueta por valor (si no, capitalizado); order: valores que van primero."""
        values = self.cr.distinct(path, {'form_id': form_id, 'deleted_at': {'$exists': False}})
        values = sorted({str(v) for v in values if v not in (None, '')})
        if order:
            values.sort(key=lambda v: (order.index(v) if v in order else len(order), v))
        labels = labels or {}
        return [{'value': v, 'label': labels.get(v, v.capitalize().replace('_', ' '))} for v in values]

    def search_fields_config(self, fields_def):
        """Config pública de los campos para el front (sin las rutas de Mongo)."""
        config = []
        for key, field in fields_def.items():
            options = field.get('options')
            if callable(options):
                options = options()
            item = {'key': key, 'label': field['label'], 'type': 'enum' if options else 'text'}
            if options:
                item['options'] = options
            config.append(item)
        return config

    def count_facet_candidates(self, base_match, fields_def, facets, candidates, pipeline=None):
        """Cuántos registros daría agregar cada candidato {key, value, exact} a
        los facets actuales. Un solo aggregate con un $count por candidato.
        pipeline: etapas entre el $match base y los conteos, para servicios que
        filtran sobre campos proyectados (ej. Location: dirección del contacto,
        áreas por ubicación); sus paths de fields_def son los proyectados."""
        if not candidates:
            return []
        branches = {}
        for i, cand in enumerate(candidates):
            extra = {'key': cand.get('key'), 'values': [cand.get('value')], 'exact': cand.get('exact')}
            conditions = self.build_facets_match(fields_def, list(facets or []) + [extra])
            branches[f"c{i}"] = [{'$match': {'$and': conditions} if conditions else {}}, {'$count': 'n'}]
        result = list(self.cr.aggregate([{'$match': base_match}, *(pipeline or []), {'$facet': branches}]))
        row = result[0] if result else {}
        return [(row.get(f"c{i}") or [{}])[0].get('n', 0) for i in range(len(candidates))]
