from odbms import DBMS, Model
from ..common.utils import Utils


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

        if DBMS.Database.dbms == 'mongodb':
            data["created_at"] = self.created_at
            data["updated_at"] = self.updated_at

        return DBMS.Database.insert(Permission.TABLE_NAME, data)
    
    def json(self)-> dict:
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
