from odbms import DBMS, Model

class Project(Model):
    TABLE_NAME = 'projects'

    def __init__(self, user_id: str, name: str, version: str = "0.0.1", description: str = "", homepage: str = "",
        language: str = "", runtime: str = "", start_file: str = "", private: bool = False, author: str = '', 
        github_repo: str = '', github_repo_branch: str = '', created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.name = name
        self.user_id = user_id
        self.version = version
        self.description = description
        self.homepage = homepage
        self.language = language
        self.runtime = runtime
        self.private = private
        self.start_file = start_file
        self.author = author
        self.github_repo = github_repo
        self.github_repo_branch = github_repo_branch

    
    def user(self):#-> User:
        '''
        Instance Method for retrieving User of Project instance
        
        @params None
        @return User Instance
        '''

        return Model.normalise(DBMS.Database.find_one('users', Model.normalise({'id': self.user_id}, 'params'))) # type: ignore
    
    def functions(self):
        '''
        Instance Method for retrieving Functions of Project Instance

        @params None
        @return List of Function Instances
        '''

        return DBMS.Database.find('functions', Model.normalise({'project_id': self.id}, 'params'))
    
    def json(self)-> dict:
        '''
        Instance Method for converting instance to Dict

        @paramas None
        @return Dict() format of Project instance
        '''
        data = super().json()
        data['id'] = str(data['id'])
        data['user_id'] = str(data['user_id'])
        
        return data

    @classmethod
    def get_by_user(cls, user_id: str)-> list:
        '''
        Class Method for retrieving projects by a user

        @param user_id:str _id of the user
        @return List of Project instances
        '''
        
        
        
        data = []
        projects = DBMS.Database.find(Project.TABLE_NAME, Model.normalise({'user_id': user_id}, 'params'))

        for elem in projects:
            if isinstance(elem, dict):
                data.append(cls(**cls.normalise(elem)))
            else:
                data.append(cls(*elem))

        return data

