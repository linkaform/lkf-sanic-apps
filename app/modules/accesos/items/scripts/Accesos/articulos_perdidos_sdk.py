#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def nuevo_articulo(params):
    data = params.get("data", {})
    return dispatch("nuevo_articulo", params={
        'data_article': data.get('data_article', {}),
    }, method='post', **params)

def get_articles(params):
    data = params.get("data", {})
    return dispatch("get_articles_perdidos", params={
        'location': data.get('location', ''),
        'area': data.get('area', ''),
        'status': data.get('status', ''),
        'dateFrom': data.get('dateFrom', ''),
        'dateTo': data.get('dateTo', ''),
        'filterDate': data.get('filterDate', ''),
    }, method='get', **params)

def update_article(params):
    data = params.get("data", {})
    return dispatch("update_article_perdido", params={
        'data_article_update': data.get('data_article_update', {}),
        'folio': data.get('folio', ''),
    }, method='post', **params)

def delete_article(params):
    data = params.get("data", {})
    return dispatch("delete_article_perdido", params={
        'folio': data.get('folio', []) if isinstance(data.get('folio'), list) else ([data.get('folio')] if data.get('folio') else []),
    }, method='get', **params)

def catalogo_tipo_articulo(params):
    data = params.get("data", {})
    return dispatch("catalogo_tipo_articulo", params={
        'tipo': data.get('tipo', ''),
    }, method='get', **params)

def catalogo_area_empleado(params):
    data = params.get("data", {})
    return dispatch("catalogo_area_empleado", params={
        'location': data.get('location', ''),
    }, method='get', **params)


DISPATCHER = {
    "nuevo_articulo": nuevo_articulo,
    "get_articles": get_articles,
    "update_article": update_article,
    "delete_article": delete_article,
    "catalogo_tipo_articulo": catalogo_tipo_articulo,
    "catalogo_area_empleado": catalogo_area_empleado,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option")
    print('..... arranca script articulos_perdidos')
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
