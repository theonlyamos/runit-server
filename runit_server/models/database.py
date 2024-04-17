from odbms import DBMS, Model

class Database(Model):
    TABLE_NAME = 'databases'

    def __init__(self, name: str, collection_name: str, user_id: str, project_id: str = '', schema: str = '{}', created_at=None, updated_at=None, id=None, **kwargs):
        super().__init__(created_at, updated_at, id)
        self.name = name
        self.collection_name = collection_name
        self.user_id = user_id
        self.project_id = project_id
        self.schema = schema

        for key, value in kwargs.items():
            self.__setattr__(key, value)

    def user(self):
        '''
        Instance Method for retrieving User of Database instance
        
        @params None
        @return User Instance
        '''

        return Model.normalise(DBMS.Database.find_one('users', Model.normalise({'id': self.user_id}, 'params'))) # type: ignore

    @classmethod
    def get_by_name(cls, collection_name: str)-> list:
        '''
        Class Method for retrieving collection by a name

        @param collectinon_name:str name of the collection
        @return List of Database instances
        '''
        
        databases = DBMS.Database.find(Database.TABLE_NAME, Model.normalise({'name': collection_name}, 'params'))
        
        return [cls(**Model.normalise(elem)) for elem in databases]
    
    @classmethod
    def get_by_user(cls, user_id: str)-> list:
        '''
        Class Method for retrieving databases by a user

        @param user_id:str _id of the user
        @return List of Database instances
        '''
        
        databases = DBMS.Database.find(Database.TABLE_NAME, Model.normalise({'user_id': user_id}, 'params'))
        
        return [cls(**Model.normalise(elem)) for elem in databases]

    def json(self)-> dict:
        '''
        Instance Method for converting instance to Dict

        @paramas None
        @return Dict() format of Database instance
        '''
        
        return self.__dict__
