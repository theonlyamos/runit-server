from datetime import datetime
from bson.objectid import ObjectId
from odbms import DBMS, Model

from ..common.utils import Utils

class User(Model):
    '''A model class for user'''
    TABLE_NAME = 'users'

    def __init__(self, email: str, name: str, password: str, 
                 image: str = '', gat: str ='', 
                 grt: str ='', created_at=None, 
                 updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.email = email
        self.name = name
        self.password = password
        self.image = image
        self.gat = gat
        self.grt = grt
        

    def save(self):
        '''
        Instance Method for saving User instance to Database

        @params None
        @return None
        '''
        
        data = self.__dict__.copy()
        data['updated_at'] = (datetime.now()).strftime("%a %b %d %Y %H:%M:%S")
        
        if DBMS.Database.dbms != 'mongodb':
            del data["created_at"]
            del data["updated_at"]

        if isinstance(self.id, ObjectId):
            data['password'] = Utils.hash_password(self.password)
            return DBMS.Database.insert(User.TABLE_NAME, Model.normalise(data, 'params'))
        
        # Update the existing record in database
        del data['password']
        return DBMS.Database.update(self.TABLE_NAME, self.normalise({'id': self.id}, 'params'), self.normalise(data, 'params'))
        
        
    
    def reset_password(self, new_password: str):
        '''
        Instance Method for resetting user password

        @param new_password User's new password
        @return None
        '''
        
        new_password = Utils.hash_password(new_password)

        DBMS.Database.update(User.TABLE_NAME, User.normalise({'id': self.id}, 'params'), {'password': new_password})
    
    def projects(self):#-> List[Project]:
        '''
        Instance Method for retrieving Projects of User Instance

        @params None
        @return List of Project Instances
        '''

        return DBMS.Database.find('projects', {'user_id': self.id})
    
    def count_projects(self):
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
        
        data = super().json()
        data['projects'] = self.count_projects()

        return data

    @classmethod
    def get_by_email(cls, email: str):
        '''
        Class Method for retrieving user by email address

        @param email email address of the user 
        @return User instance
        '''
        user = DBMS.Database.find_one(User.TABLE_NAME, {"email": email})
        
        if isinstance(user, dict):
            return cls(**cls.normalise(user)) if len(user.keys()) else None
        elif isinstance(user, list) or isinstance(user, tuple):
            return cls(*user) if len(user) else None
