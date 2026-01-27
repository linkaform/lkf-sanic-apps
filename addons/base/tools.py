# -*- coding: utf-8 -*-
### Linkaform Modules / Archivo de Módulo ###

# Importaciones necesarias
from functools import wraps

def reload_user(func):
    """Decorador que recarga usuario desde headers"""
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        print('Reloading user...')
        # Obtener headers de kwargs
        headers = kwargs.get('headers', {})
        # Aquí SÍ tienes acceso a self porque wrapped recibe self como primer argumento
        if headers:
            # Actualizar self.user desde JWT
            auth_header = headers.get('Authorization', headers.get('authorization', ''))
            if auth_header:
                jwt_token = auth_header.replace('Bearer ', '')
                self.config['JWT_KEY'] = jwt_token
                user_data = self.decode_jwt()
                user_data['id'] = user_data.get('user_id')
                self.config['USERNAME'] = user_data.get('username')
                self.record_user_id = user_data.get('user_id')
                self.user_id = user_data.get('user_id')
                self.parent_id = user_data.get('parent_id')
                self.timezone = user_data.get('timezone')
                self.user.update(user_data)
                # Decodificar y actualizar
            
        result = func(self, *args, **kwargs)
        return result
    return wrapped