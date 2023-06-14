from datetime import datetime
import uuid

from bson.objectid import ObjectId

from odbms import DBMS, Model
from ..common.utils import Utils


class Admin(Model):
    '''A model class for admin'''
    TABLE_NAME = 'admins'

    def __init__(self, email, name, username, password, role, created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.email = email
        self.username = username
        self.name = name
        self.password = password
        self.role = role
        

    def save(self):
        '''
        Instance Method for saving Admin instance to database

        @params None
        @return None
        '''

        data = {
            "email": self.email,
            "name": self.name,
            "username": self.username,
            "role": self.role,
            "password": Utils.hash_password(self.password)
        }

        if DBMS.Database.dbms == 'mongodb':
            data["created_at"] = self.created_at
            data["updated_at"] = self.updated_at

        return DBMS.Database.insert(Admin.TABLE_NAME, data)
    
    def reset_password(self, new_password: str):
        '''
        Instance Method for resetting admin password

        @param new_password Admin's new password
        @return None
        '''

        DBMS.Database.update_one(Admin.TABLE_NAME, Admin.normalise({'id': self.id}, 'params'), {'password': new_password})
    

    def json(self)-> dict:
        '''
        Instance Method for converting Admin Instance to Dict

        @paramas None
        @return dict() format of Function instance
        '''

        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "role": self.get_role(),
            "username": self.username,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def get_role(self):
        '''
        Instance Method for retrieving Admin Role

        @params None
        @return List[Role] of Admin Instance
        '''

        return DBMS.Database.find_one('roles', Admin.normalise({'name': self.role}, 'params'))


    @classmethod
    def get_by_username(cls, username: str):
        '''
        Class Method for retrieving admin by username 

        @param username username of the admin 
        @return Admin instance
        '''
        admin = DBMS.Database.find_one(Admin.TABLE_NAME, {"username": username})
        return cls(**Model.normalise(admin)) if admin else None
    
    @classmethod
    def get_by_role(cls, role: str):
        '''
        Class Method for retrieving admin by role 

        @param role Role of the admin 
        @return Admin instance
        '''
        admin = DBMS.Database.find_one(Admin.TABLE_NAME, {"role": role})
        return cls(**Model.normalise(admin)) if admin else None
