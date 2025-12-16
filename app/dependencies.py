# coding: utf-8
"""
Gestor de dependencias globales
Inicializa ONCE y reutiliza en todos los requests
"""

from linkaform_api import base
# from lkf_addons.accesos.app import Accesos

import logging

logger = logging.getLogger(__name__)

# INSTANCIAS GLOBALES (inicializadas una sola vez)
_lkf_api = None
_module_cache = {}

class DependenciesManager:
    """
    Gestor centralizado de dependencias
    Se inicializa UNA VEZ al arrancar la app
    """
    
    def __init__(self, settings):
        self.settings = settings
        self._lkf_api = None
        self._module_instances = {}
    
    @property
    def lkf_api(self):
        """LKF API Client - singleton"""
        if self._lkf_api is None:
            logger.info("Inicializando LKF API Client...")
            self._lkf_api = base.LKF_Base(
                self.settings,
                use_api=True
            )
        return self._lkf_api
    
    def get_module_instance(self, module_name, module_class=None, **kwargs):
        """
        Obtiene o crea instancia de módulo (con caché)
        
        Args:
            module_name: Nombre del módulo (ej: 'Accesos')
            module_class: Clase del módulo
            **kwargs: Parámetros adicionales
        
        Returns:
            Instancia del módulo (cacheada)
        """
        cache_key = f"{module_name}_{hash(str(kwargs))}"
        
        if cache_key not in self._module_instances:
            logger.info(f"Creando instancia de módulo: {module_name}")
            
            # Importar dinámicamente el módulo
            if not module_class:
                module_class = module_name
            
            # Importar la clase
            import importlib
            module = importlib.import_module(f'lkf_addons.{module_name.lower()}.app')
            ModuleClass = getattr(module, module_class)
            
            # Crear instancia
            self._module_instances[cache_key] = ModuleClass(
                self.settings,
                use_api=True,
                **kwargs
            )
        return self._module_instances[cache_key]
    
    def clear_cache(self):
        """Limpia el caché de módulos (útil para testing)"""
        self._module_instances.clear()


async def init_dependencies(settings):
    """
    Inicializa las dependencias globales
    Se llama UNA VEZ al arrancar
    """
    logger.info("Inicializando dependencias globales...")
    
    deps = DependenciesManager(settings)
    
    # Pre-calentar el LKF API client
    _ = deps.lkf_api
    
    logger.info("Dependencias inicializadas correctamente")
    return deps


def get_dependencies(request):
    """
    Helper para obtener dependencias del contexto de Sanic
    
    Usage en routes:
        deps = get_dependencies(request)
        accesos = deps.get_module_instance('Accesos')
    """
    print('get_dependencies....')
    return request.app.ctx.dependencies
