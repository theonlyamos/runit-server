from odbms import DBMS, Model

from ..common.utils import Utils

class User(Model):
    '''A model class for user'''
    TABLE_NAME = 'users'

    def __init__(self, email, name, password, created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.email = email
        self.name = name
        self.password = password
        

    def save(self):
        '''
        Instance Method for saving User instance to Database

        @params None
        @return None
        '''

        data = {
            "name": self.name,
            "email": self.email,
            "password": Utils.hash_password(self.password)
        }

        if DBMS.Database.dbms == 'mongodb':
            data["created_at"] = self.created_at
            data["updated_at"] = self.updated_at

        return DBMS.Database.insert(User.TABLE_NAME, data)
    
    def reset_password(self, new_password: str):
        '''
        Instance Method for resetting user password

        @param new_password User's new password
        @return None
        '''

        DBMS.Database.update_one(User.TABLE_NAME, User.normalise({'id': self.id}, 'params'), {'password': new_password})
    
    def projects(self):#-> List[Project]:
        '''
        Instance Method for retrieving Projects of User Instance

        @params None
        @return List of Project Instances
        '''

        return DBMS.Database.find('projects', {'user_id': self.id}, 'params')
    
    def count_projects(self)-> int:
        '''
        Instance Method for counting User Projects

        @params None
        @return int Count of Projects
        '''

        return DBMS.Database.count('projects', User.normalise({'user_id': self.id}, 'params'))
    
    def json(self)-> dict:
        '''
        Instance Method for converting User Instance to Dict

        @paramas None
        @return dict() format of Function instance
        '''

        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "projects": self.count_projects(),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def get_by_email(cls, email: str):
        '''
        Class Method for retrieving user by email address

        @param email email address of the user 
        @return User instance
        '''
        user = DBMS.Database.find_one(User.TABLE_NAME, {"email": email})
        return cls(**Model.normalise(user)) if user else None
