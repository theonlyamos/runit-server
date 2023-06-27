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

        data = self.__dict__
        
        del data['id']

        if DBMS.Database.dbms == 'mongodb':
            data["created_at"]: self.created_at
            data["updated_at"]: self.updated_at

        return DBMS.Database.insert(self.TABLE_NAME, Model.normalise(data, 'params'))
    
    def user(self):
        '''
        Instance Method for retrieving User of Database instance
        
        @params None
        @return User Instance
        '''

        return Model.normalise(DBMS.Database.find_one('users', Model.normalise({'id': self.user_id}, 'params')))

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

    def json(self)-> dict:
        '''
        Instance Method for converting instance to Dict

        @paramas None
        @return Dict() format of Database instance
        '''
        
        return self.__dict__
    
    @staticmethod
    def stats(collection_name: str):
        '''
        Static method for getting collection stats
        
        @param collection_name:str Name of the collection
        @return Collection Stats
        '''
        
        return DBMS.Database.db.command('collstats', collection_name)
