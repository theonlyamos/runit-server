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

        data = self.__dict__.copy()

        if DBMS.Database.dbms != 'mongodb':
            del data["created_at"]
            del data["updated_at"]

        return DBMS.Database.insert(Permission.TABLE_NAME, data)