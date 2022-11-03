from datetime import datetime
from typing import Dict, List
import uuid

from bson.objectid import ObjectId

from ..common.database import Database
from ..common.utils import Utils
from .model import Model


class Admin(Model):
    '''A model class for admin'''
    TABLE_NAME = 'admins'

    def __init__(self, name, username, password, role_id, created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.username = username
        self.name = name
        self.password = password
        self.role_id = role_id
        

    def save(self):
        '''
        Instance Method for saving Admin instance to database

        @params None
        @return None
        '''

        data = {
            "name": self.name,
            "username": self.username,
            "role_id": self.role_id,
            "password": Utils.hash_password(self.password)
        }

        if Database.dbms == 'mongodb':
            data["created_at"] = self.created_at
            data["updated_at"] = self.updated_at

        return Database.db.insert(Admin.TABLE_NAME, data)
    
    def reset_password(self, new_password: str):
        '''
        Instance Method for resetting admin password

        @param new_password Admin's new password
        @return None
        '''

        Database.db.update_one(Admin.TABLE_NAME, Admin.normalise({'id': self.id}, 'params'), {'password': new_password})
    

    def json(self)-> Dict:
        '''
        Instance Method for converting Admin Instance to Dict

        @paramas None
        @return dict() format of Function instance
        '''

        return {
            "id": str(self.id),
            "name": self.name,
            "role": self.role(),
            "username": self.username,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def role(self):
        '''
        Instance Method for retrieving Admin Role

        @params None
        @return List[Role] of Admin Instance
        '''

        return Database.db.find_one('roles', Admin.normalise({'id': self.role_id}, 'params'))


    @classmethod
    def get_by_username(cls, username: str):
        '''
        Class Method for retrieving admin by username 

        @param username username of the admin 
        @return Admin instance
        '''
        admin = Database.db.find_one(Admin.TABLE_NAME, {"username": username})
        return cls(**Model.normalise(admin)) if admin else None
