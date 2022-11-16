from odbms import DBMS, Model

class Project(Model):
    TABLE_NAME = 'projects'

    def __init__(self, user_id, name, version="0.0.1", description="", homepage="",
    language="", runtime="", start_file="", author={}, created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.name = name
        self.user_id = user_id
        self.version = version
        self.description = description
        self.homepage = homepage
        self.language = language
        self.runtime = runtime
        self.start_file = start_file
        self.author = author

    def save(self):
        '''
        Instance Method for saving Project instance to database

        @params None
        @return None
        '''

        data = {
            "name": self.name,
            "user_id": self.user_id,
            "version": self.version,
            "description": self.description,
            "homepage": self.homepage,
            "language": self.language,
            "runtime": self.runtime,
            "start_file": self.start_file,
            "author": self.author
        }

        if DBMS.Database.dbms == 'mongodb':
            data["created_at"]: self.created_at
            data["updated_at"]: self.updated_at

        return DBMS.Database.insert(Project.TABLE_NAME, Model.normalise(data, 'params'))
    
    def user(self):#-> User:
        '''
        Instance Method for retrieving User of Project instance
        
        @params None
        @return User Instance
        '''

        return Model.normalise(DBMS.Database.find_one('users', Model.normalise({'id': self.user_id}, 'params')))
    
    def functions(self)-> list:
        '''
        Instance Method for retrieving Functions of Project Instance

        @params None
        @return List of Function Instances
        '''

        return DBMS.Database.find('functions', Model.normalise({'project_id': self.id}, 'params'))
    
    def count_functions(self)-> int:
        '''
        Instance Method for counting function in Project

        @params None
        @return Count of functions
        '''

        return DBMS.Database.count('functions', Model.normalise({'project_id': self.id}, 'params'))
    
    def json(self)-> dict:
        '''
        Instance Method for converting instance to Dict

        @paramas None
        @return Dict() format of Project instance
        '''
        return {
            "id": str(self.id),
            "name": self.name,
            "user_id": str(self.user_id),
            "version": self.version,
            "description": self.description,
            "homepage": self.homepage,
            "language": self.language,
            "runtime": self.runtime,
            "start_file": self.start_file,
            "author": self.author,
            "functions": self.count_functions(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def get_by_user(cls, user_id: str)-> list:
        '''
        Class Method for retrieving projects by a user

        @param user_id:str _id of the user
        @return List of Project instances
        '''
        
        projects = DBMS.Database.find(Project.TABLE_NAME, Model.normalise({'user_id': user_id}, 'params'))
        
        return [cls(**Model.normalise(elem)) for elem in projects]

