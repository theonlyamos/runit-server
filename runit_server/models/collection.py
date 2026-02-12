from odbms import DBMS, Model

class Collection(Model):
    TABLE_NAME = ''

    def __init__(self, created_at=None, updated_at=None, id=None, **kwargs):
        init_kwargs = {**kwargs}
        if created_at is not None:
            init_kwargs['created_at'] = created_at
        if updated_at is not None:
            init_kwargs['updated_at'] = updated_at
        if id is not None:
            init_kwargs['id'] = id
        super().__init__(**init_kwargs)

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
