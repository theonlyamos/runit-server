from datetime import datetime

from bson.objectid import ObjectId

from odbms import DBMS, Model
from ..common.utils import Utils


class Role(Model):
    '''A model class for role'''
    TABLE_NAME = 'roles'

    def __init__(self, name: str, permission_ids: list, created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.name = name
        #self.permission_ids =  permission_ids.split('::') if type(permission_ids) == str \
        #                        else permission_ids
        self.permission_ids = permission_ids
        

    def save(self):
        '''
        Instance Method for saving Role instance to database

        @params None
        @return None
        '''

        data = self.__dict__.copy()

        if DBMS.Database.dbms != 'mongodb':
            del data["created_at"]
            del data["updated_at"]

        return DBMS.Database.insert(Role.TABLE_NAME, Role.normalise(data, 'params'))
    
    def json(self)-> dict:
        '''
        Instance Method for converting Role Instance to Dict

        @paramas None
        @return dict() format of Function instance
        '''
        
        data = super().json()
        data['id'] = str(self.id)
        data['permissions'] = self.permissions()

        return data
    
    @classmethod
    def get_by_name(cls, name: str):
        '''
        Class Method for retrieving role by name 

        @param name Name of the role 
        @return Role instance
        '''
        role = DBMS.Database.find_one(Role.TABLE_NAME, {"name": name})
        
        if isinstance(role, dict):
            return cls(**cls.normalise(role)) if len(role.keys()) else None
        elif isinstance(role, list) or isinstance(role, tuple):
            return cls(*role) if len(role) else None

    def permissions(self):
        '''
        Class Method for retrieving role by username 

        @param username username of the role 
        @return Role instance
        '''
        permissions = []
        for perm_id in self.permission_ids:
            permissions.append(DBMS.Database.find_one('permissions', {'id': perm_id}))
        
        return permissions
