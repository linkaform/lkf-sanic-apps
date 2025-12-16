# coding: utf-8
"""
Pool de conexiones MongoDB optimizado para reutilización
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

# POOL GLOBAL (se inicializa una sola vez)
_db_pool = None
_async_db_pool = None

def init_db(settings):
    """
    Inicializa el pool de conexiones MongoDB
    SE LLAMA UNA SOLA VEZ al arrancar la aplicación
    """
    global _db_pool
    
    if _db_pool is not None:
        logger.warning("DB Pool ya estaba inicializado")
        return _db_pool
    
    mongodb_uri = settings.config.get('MONGODB_URI')
    mongodb_host = settings.config.get('MONGODB_HOST')
    max_pool_size = settings.config.get('MONGODB_MAX_POOL_SIZE', 100)
    
    logger.info(f"Creando pool de conexiones MongoDB: {mongodb_host}")
    
    _db_pool = MongoClient(
        mongodb_uri or f"mongodb://{mongodb_host}/",
        maxPoolSize=max_pool_size,
        minPoolSize=10,
        maxIdleTimeMS=settings.config.get('MONGODB_MAX_IDLE_TIME', 12000),
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=20000
    )
    
    logger.info("Pool de conexiones MongoDB creado exitosamente")
    return _db_pool

async def init_async_db(settings):
    """
    Inicializa el pool de conexiones asíncronas (Motor)
    """
    global _async_db_pool
    
    if _async_db_pool is not None:
        return _async_db_pool
    
    mongodb_uri = settings.config.get('MONGODB_URI')
    max_pool_size = settings.config.get('MONGODB_MAX_POOL_SIZE', 100)
    
    _async_db_pool = AsyncIOMotorClient(
        mongodb_uri,
        maxPoolSize=max_pool_size,
        minPoolSize=10
    )
    
    return _async_db_pool

def get_db_pool():
    """
    Obtiene el pool de conexiones existente
    NO crea nuevas conexiones
    """
    if _db_pool is None:
        raise RuntimeError("DB Pool no ha sido inicializado")
    return _db_pool

def get_collection(collection_name='form_answer', db_name=None):
    """
    Obtiene una colección del pool existente
    Reutiliza conexiones del pool
    """
    pool = get_db_pool()
    db_name = db_name or pool.get_default_database().name
    return pool[db_name][collection_name]

class DatabaseManager:
    """
    Manager para facilitar acceso a colecciones
    """
    def __init__(self, settings):
        self.settings = settings
        self._pool = None
    
    @property
    def pool(self):
        if self._pool is None:
            self._pool = get_db_pool()
        return self._pool
    
    def get_collection(self, collection_name='form_answer'):
        """Obtiene colección del pool"""
        return get_collection(collection_name)
    
    def close(self):
        """Cierra el pool de conexiones"""
        global _db_pool
        if _db_pool:
            _db_pool.close()
            _db_pool = None
