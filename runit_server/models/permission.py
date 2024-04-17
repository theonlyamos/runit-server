from odbms import DBMS, Model


class Permission(Model):
    '''A model class for permission'''
    TABLE_NAME = 'permissions'

    def __init__(self, name: str, description: str, created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.name = name
        self.description = description