from datetime import datetime

from bson.objectid import ObjectId

from odbms import DBMS, Model
from ..common.utils import Utils


class Role(Model):
    '''A model class for role'''
    TABLE_NAME = 'roles'

    def __init__(self, name, permission_ids, created_at=None, updated_at=None, id=None):
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

        data = {
            "name": self.name,
            "permission_ids": self.permission_ids,
        }

        if DBMS.Database.dbms == 'mongodb':
            data["created_at"] = self.created_at
            data["updated_at"] = self.updated_at

        return DBMS.Database.db.insert(Role.TABLE_NAME, data)
    
    def json(self)-> dict:
        '''
        Instance Method for converting Role Instance to Dict

        @paramas None
        @return dict() format of Function instance
        '''

        return {
            "id": str(self.id),
            "name": self.name,
            "permissions": self.permissions(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def permissions(self):
        '''
        Class Method for retrieving role by username 

        @param username username of the role 
        @return Role instance
        '''
        permissions = []
        for perm_id in self.permission_ids:
            permissions.append(DBMS.Database.db.find_one('permissions', {'id': perm_id}))
        
        return permissions
