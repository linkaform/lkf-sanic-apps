

# api/__init__.py
from sanic import Blueprint
from .addons import addons
from .modules import modules
from .middleware import middleware

print('loading __init__ to load addons, modules and middleware...')

content = [
    addons,
    modules,
    middleware
]

print('addons, modules and middleware loaded')
api = Blueprint.group(content, url_prefix="/api")


