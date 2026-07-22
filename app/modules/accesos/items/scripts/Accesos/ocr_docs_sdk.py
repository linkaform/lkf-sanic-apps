#!/usr/local/bin/python
# coding: utf-8
import sys, simplejson, lkf_addons
from middleware.auth import dispatch


def ocr_id(params):
    data = params.get("data", {})
    return dispatch("ocr_identificacion", params={
        'image_source': data.get('image_source', ''),
        'form_id': data.get('form_id'),
        'model': data.get('model', 'google/gemini-2.5-flash-lite'),
        'name': data.get('name'),
        'is_employee': data.get('is_employee', False),
    }, method='post', **params)

def ocr_doc(params):
    data = params.get("data", {})
    return dispatch("ocr_documento", params={
        'image_source': data.get('image_source', ''),
        'fields': data.get('fields'),
        'extra_instructions': data.get('extra_instructions', ''),
        'form_id': data.get('form_id'),
        'model': data.get('model'),
    }, method='post', **params)

def ocr_batch(params):
    data = params.get("data", {})
    images = data.get('images') or ([data['image_source']] if data.get('image_source') else [])
    return dispatch("ocr_batch", params={
        'images': images,
        'option_type': data.get('ocr_type', 'ocr_id'),
        'form_id': data.get('form_id'),
        'model': data.get('model'),
    }, method='post', **params)

def ocr_articulo_perdido(params):
    data = params.get("data", {})
    return dispatch("ocr_articulo_perdido", params={
        'image_source': data.get('image_source', ''),
        'model': data.get('model', 'google/gemini-2.5-flash-lite'),
    }, method='post', **params)

def ocr_articulo(params):
    # Se llama "ocr_articulo" (no "ocr_articulo_concesionado") para mantener
    # el mismo nombre de opción que ya usaba el script equivalente en lkf-addons.
    data = params.get("data", {})
    print('data',data)
    return dispatch("ocr_articulo_concesionado", params={
        'image_source': data.get('image_source', ''),
        'extra_instructions': data.get('extra_instructions', ''),
        'model': data.get('model', 'google/gemini-2.5-flash-lite'),
    }, method='post', **params)

def ocr_paquete(params):
    data = params.get("data", {})
    return dispatch("ocr_paquete", params={
        'image_source': data.get('image_source', ''),
        'fields': data.get('fields', {}),
        'extra_instructions': data.get('extra_instructions', ''),
        'model': data.get('model', 'google/gemini-2.5-flash-lite'),
    }, method='post', **params)

def ocr_truck(params):
    data = params.get("data", {})
    return dispatch("ocr_truck", params={
        'image_source': data.get('image_source', ''),
        'fields': data.get('fields', {}),
        'extra_instructions': data.get('extra_instructions', ''),
        'model': data.get('model', 'google/gemini-2.5-flash-lite'),
    }, method='post', **params)

def ocr_vehiculo(params):
    data = params.get("data", {})
    return dispatch("ocr_vehiculo", params={
        'image_source': data.get('image_source', ''),
        'fields': data.get('fields', {}),
        'extra_instructions': data.get('extra_instructions', ''),
        'model': data.get('model', 'google/gemini-2.5-flash-lite'),
    }, method='post', **params)

def ocr_persona(params):
    data = params.get("data", {})
    return dispatch("ocr_persona", params={
        'image_source': data.get('image_source', ''),
        'extra_instructions': data.get('extra_instructions', ''),
        'model': data.get('model', 'google/gemini-2.5-flash-lite'),
    }, method='post', **params)

def ocr_equipo(params):
    data = params.get("data", {})
    return dispatch("ocr_equipo", params={
        'image_source': data.get('image_source', ''),
        'extra_instructions': data.get('extra_instructions', ''),
        'model': data.get('model', 'google/gemini-2.5-flash-lite'),
    }, method='post', **params)


DISPATCHER = {
    "ocr_id": ocr_id,
    "ocr_doc": ocr_doc,
    "ocr_batch": ocr_batch,
    "ocr_articulo_perdido": ocr_articulo_perdido,
    "ocr_articulo": ocr_articulo,
    "ocr_paquete": ocr_paquete,
    "ocr_truck": ocr_truck,
    "ocr_vehiculo": ocr_vehiculo,
    "ocr_persona": ocr_persona,
    "ocr_equipo": ocr_equipo,
}

if __name__ == "__main__":
    params = simplejson.loads(sys.argv[2])
    data = params.get("data", {})
    option = data.get("option")
    print('..... arranca script ocr_docs con option=', option)
    handler = DISPATCHER.get(option)
    if not handler:
        response = {"error": f"Option '{option}' not supported", "valid_options": list(DISPATCHER.keys())}
        sys.stdout.write(simplejson.dumps(response))
    else:
        response = handler(params)
        sys.stdout.write(simplejson.dumps(response.json()))
