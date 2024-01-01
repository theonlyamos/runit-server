from odbms import DBMS, Model

class Collection(Model):
    TABLE_NAME = ''

    def __init__(self, created_at=None, updated_at=None, id=None, **kwargs):
        super().__init__(created_at, updated_at, id)

        for key, value in kwargs.items():
            self.__setattr__(key, value)

    def save(self):
        '''
        Instance Method for saving Database instance to database

        @params None
        @return None
        '''

        data = self.__dict__.copy()
        
        del data['id']

        if DBMS.Database.dbms != 'mongodb':
            del data["created_at"]
            del data["updated_at"]

        return DBMS.Database.insert(self.TABLE_NAME, Model.normalise(data, 'params'))

    @classmethod
    def get_by_user(cls, user_id: str)-> list:
        '''
        Class Method for retrieving databases by a user

        @param user_id:str _id of the user
        @return List of Database instances
        '''
        
        databases = DBMS.Database.find(cls.TABLE_NAME, Model.normalise({'user_id': user_id}, 'params'))
        
        return [cls(**Model.normalise(elem)) for elem in databases]
    
    @classmethod
    def get_by_project(cls, project_id: str)-> list:
        '''
        Class Method for retrieving databases by a project

        @param project_id:str _id of the user
        @return List of Database instances
        '''
        
        databases = DBMS.Database.find(cls.TABLE_NAME, Model.normalise({'project_id': project_id}, 'params'))
        
        return [cls(**Model.normalise(elem)) for elem in databases]
    
    @staticmethod
    def stats(collection_name: str):
        '''
        Static method for getting collection stats
        
        @param collection_name:str Name of the collection
        @return Collection Stats
        '''
        
        if DBMS.Database.dbms == 'mongodb':
            return DBMS.Database.db.command('collstats', collection_name)
        
        return {}
