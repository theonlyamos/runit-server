from odbms import DBMS, Model

EXTENSIONS = {'python': '.py', 'python3': '.py', 'php': '.php', 'javascript': '.js'}

class Function(Model):
    TABLE_NAME = 'functions'

    def __init__(self, name, user_id, language, project_id=None, filename=None, description=None, created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.name = name
        self.filename = filename
        self.user_id = user_id
        self.project_id = project_id
        self.language = language
        self.description = description

    def save(self):
        '''
        Instance Method for saving Function instance to database

        @params None
        @return None
        '''
        data = {
            "name": self.name,
            "filename": self.filename,
            "user_id": self.user_id,
            "language": self.language,
            "description": self.description
        }

        if self.project_id:
            data.update({'project_id': self.project_id})
        
        if DBMS.Database.dbms == 'mongodb':
            data["created_at"]: self.created_at
            data["updated_at"]: self.updated_at

        return DBMS.Database.insert(Model.normalise(data, 'params'))
    
    def project(self):#-> Project:
        '''
        Instance Method for retrieving Project Instance of Function Instance

        @params None
        @return Project Instance
        '''

        #return Project.get(self.project_id)
        return DBMS.Database.find('projects', Model.normalise({'id': self.project_id}, 'params'))

    def user(self):
        '''
        Instance Method for retrieving User of Function instance
        
        @params None
        @return User instance
        '''

        return DBMS.Database.find_one('users', Model.normalise({'id': self.user_id}, 'params'))
    
    def json(self)-> dict:
        '''
        Instance Method for converting instance to dict()

        @paramas None
        @return dict() format of Function instance
        '''
        return {
            "id": str(self.id),
            "name": self.name,
            "filename": self.filename,
            "language": self.language[0],
            "description": self.description,
            #"user": self.user(),
            #"project": self.project() if self.project_id else {},
            "user_id": str(self.user_id),
            "project_id": str(self.project_id),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def get_by_project(cls, project_id: str):
        '''
        Class Method for retrieving functions by a project

        @param project_id:str _id of the of project
        @return List of Function instances
        '''
        functions = DBMS.Database.find(cls.TABLE_NAME, Model.normalise({'project_id': project_id}, 'params'))
        return [cls(**Model.normalise(elem)) for elem in functions]
    
    @classmethod
    def get_by_user(cls, user_id: str):
        '''
        Class Method for retrieving functions by a user

        @param user_id:str _id of the user
        @return List of Function instances
        '''
        functions = DBMS.Database.find(cls.TABLE_NAME, Model.normalise({'user_id': user_id}, 'params'))
        return [cls(**Model.normalise(elem)) for elem in functions]
