from datetime import datetime
from typing import Dict, List
import uuid

from bson.objectid import ObjectId

from ..common.database import Database
from ..common.utils import Utils
from .model import Model


class Permission(Model):
    '''A model class for permission'''
    TABLE_NAME = 'permissions'

    def __init__(self, name, description, created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.name = name
        self.description = description
        

    def save(self):
        '''
        Instance Method for saving Permission instance to database

        @params None
        @return None
        '''

        data = {
            "name": self.name,
            "description": self.description
        }

        if Database.dbms == 'mongodb':
            data["created_at"] = self.created_at
            data["updated_at"] = self.updated_at

        return Database.db.insert(Permission.TABLE_NAME, data)
    
    def json(self)-> Dict:
        '''
        Instance Method for converting Permission Instance to Dict

        @paramas None
        @return dict() format of Function instance
        '''

        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
