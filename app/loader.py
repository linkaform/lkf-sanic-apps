#!/usr/local/bin/python
# coding: utf-8

import os
import sys
import importlib.util
from pathlib import Path

# from bin.lkfaddons import module


account_id = os.getenv("ACCOUNT_ID", 126)

print('account_id', account_id)
# Rutas de búsqueda para la clase Accesos
CUSTOM_MODULE_PATHS = [
    f'/srv/backend.linkaform.com/infosync-api/backend/media/uploads/public-client-{account_id}/scripts/',
    f'/srv/lkf-sanic-app/app/modules/accesos/items/scripts/CLASS_NAME',
    '/usr/local/lib/python3.12/site-packages/lkf_addons',
]

# ============================================
# DYNAMIC CLASS LOADER
# ============================================


def find_module_file(base_paths, class_name, filenames=['accesos_utils.py', 'app.py']):
    """
    Busca archivos de módulo en múltiples rutas
    
    Args:
        base_paths: Lista de rutas base donde buscar
        filenames: Lista de nombres de archivo a buscar
    
    Returns:
        tuple: (ruta_completa, nombre_archivo) o (None, None)
    """
    for base_path in base_paths:
        # print('>>>> Buscando en : ',base_path )
        for filename in filenames:
            # print('>>>> Archivo : ', filename)
            full_path = os.path.join(base_path.replace('CLASS_NAME', class_name), filename)
            # print('full_path', full_path)
            if os.path.exists(full_path):
                return full_path, filename
    
    return None, None



def extend_routes(module_bp, module_name):
    print('Cargando Rutas de Modulo: ', module_name)
    custom_file, filename  = find_module_file(CUSTOM_MODULE_PATHS, module_name, filenames=[f'{module_name.lower()}_routes.py'])
    if custom_file:
        custom_bp = load_blueprint_from_file(custom_file)
        if custom_bp:
            print('✓ Rutas personalizadas entradas')
            # Obtener las rutas custom
            custom_routes = custom_bp._future_routes if hasattr(custom_bp, '_future_routes') else set()
            # Eliminar rutas duplicadas del blueprint base
            routes_to_remove = set()
            for custom_route in custom_routes:
                for base_route in module_bp._future_routes:
                    # Comparar URI y métodos
                    if (hasattr(custom_route, 'uri') and hasattr(base_route, 'uri') and
                        custom_route.uri == base_route.uri):
                        routes_to_remove.add(base_route)
            
            # Remover rutas duplicadas
            for route in routes_to_remove:
                module_bp._future_routes.discard(route)
                print(f'⚠ Ruta Sobrescritas: {route.uri}')
            
            # Agregar rutas custom
            module_bp._future_routes.update(custom_bp._future_routes)
            
            print(f'+ Rutas extendidas en {module_name}: {len(custom_bp._future_routes)} rutas agregadas')
            return None
        else:
            print('>>> ⚠ No se econtraron rutas personalizadas en módulo ', module_name)
    return None

def load_blueprint_from_file(file_path, blueprint_name='accesos_bp'):
    """
    Carga un blueprint dinámicamente desde un archivo Python
    Args:
        file_path: Ruta completa al archivo .py
        blueprint_name: Nombre del blueprint a cargar
    Returns:
        El blueprint cargado o None si falla
    """

    try:
        # Generar nombre de módulo único
        module_name = f"dynamic_routes_{hash(file_path)}"
        
        # Cargar el módulo desde el archivo
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            print(f'>>> ERROR: No se pudo crear spec para {file_path}')
            return None
        
        module = importlib.util.module_from_spec(spec)
        
        # Agregar al sys.modules para que las importaciones funcionen
        sys.modules[module_name] = module
        
        # Ejecutar el módulo
        spec.loader.exec_module(module)
        
        # Obtener el blueprint
        if hasattr(module, blueprint_name):
            print(f'>>> Blueprint {blueprint_name} cargado exitosamente desde {file_path}')
            return getattr(module, blueprint_name)
        else:
            print(f'>>> ERROR: Blueprint {blueprint_name} no encontrado en {file_path}')
            return None
            
    except Exception as e:
        print(f'>>> ERROR al cargar blueprint desde {file_path}: {str(e)}')
        import traceback
        traceback.print_exc()
        return None

def load_class_from_file(file_path, class_name='Accesos'):
    """
    Carga una clase dinámicamente desde un archivo Python
    
    Args:
        file_path: Ruta completa al archivo .py
        class_name: Nombre de la clase a cargar
    
    Returns:
        La clase cargada o None si falla
    """
    # try:
    if True:
        # Generar nombre de módulo único
        app_root = '/srv/lkf-sanic-app/app'  # O detectarlo dinámicamente
        print('=1111111111111111111111111111111111111111111111111111111111111111111111111========================= cargano root a syspath')
        if app_root not in sys.path:
            print('========================== cargano root a syspath')
            sys.path.insert(0, app_root)
        module_name = f"dynamic_accesos_{hash(file_path)}"
        
        # Cargar el módulo desde el archivo
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            print(f'>>> ERROR: No se pudo crear spec para {file_path}')
            return None
        
        module = importlib.util.module_from_spec(spec)
        
        # Agregar al sys.modules para que las importaciones funcionen
        sys.modules[module_name] = module
        
        # Ejecutar el módulo
        spec.loader.exec_module(module)
        
        # Obtener la clase
        if hasattr(module, class_name):
            print(f'>>> Clase {class_name} cargada exitosamente desde {file_path}')
            return getattr(module, class_name)
        else:
            print(f'>>> ERROR: Clase {class_name} no encontrada en {file_path}')
            return None
            
    # except Exception as e:
    #     print(f'>>> ERROR al cargar clase desde {file_path}: {str(e)}')
    #     import traceback
    #     traceback.print_exc()
    #     return None

def get_module_class(class_name):
    """
    Obtiene la clase Accesos con la siguiente prioridad:
    1. Módulo personalizado en CUSTOM_MODULE_PATHS (accesos_utils.py)
    2. Módulo personalizado en CUSTOM_MODULE_PATHS (app.py)
    3. Módulo local (.app)
    
    Returns:
        Clase Accesos cargada
    """
    print('>>>  Buscan do clase...', class_name)
    
    # 1. Intentar cargar desde rutas personalizadas
    custom_file, filename = find_module_file(CUSTOM_MODULE_PATHS, class_name)
    
    if custom_file:
        print(f'>>> Intentando cargar desde módulo personalizado: {custom_file}')
        ThisClass = load_class_from_file(custom_file, class_name)
        
        if ThisClass:
            print('>>> ✓ Usando clase Accesos personalizada')
            return ThisClass
        else:
            print('>>> ⚠ Fallo al cargar clase personalizada, usando módulo local')
    
    # 2. Fallback: cargar desde módulo local
    try:

        module_path = f"lkf_addons.{class_name.lower()}.app"
        module = importlib.import_module(module_path)

        ThisClass = getattr(module, class_name)


        print('>>> Intentando cargar desde módulo local (.app)')
        # from lkf_addons.accesos.app import Accesos
        print('>>> ✓ Usando clase Accesos del módulo local')
        return ThisClass
    except ImportError as e:
        print(f'>>> ERROR: No se pudo cargar clase Accesos desde módulo local: {str(e)}')
        raise ImportError('No se pudo cargar la clase Accesos desde ninguna ubicación')

