from datetime import datetime
from bson.objectid import ObjectId
from odbms import DBMS, Model

from ..common.utils import Utils
from ..common.cache import cached, cache


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
            cache.delete(f"user:email:{self.email}")
            return DBMS.Database.insert(User.TABLE_NAME, Model.normalise(data, 'params'))
        
        cache.delete(f"user:id:{self.id}")
        cache.delete(f"user:email:{self.email}")
        del data['password']
        return DBMS.Database.update(self.TABLE_NAME, self.normalise({'id': self.id}, 'params'), self.normalise(data, 'params'))
        
        
    
    def reset_password(self, new_password: str):
        '''
        Instance Method for resetting user password

        @param new_password User's new password
        @return None
        '''
        
        new_password = Utils.hash_password(new_password)
        
        cache.delete(f"user:id:{self.id}")
        cache.delete(f"user:email:{self.email}")

        DBMS.Database.update(User.TABLE_NAME, User.normalise({'id': self.id}, 'params'), {'password': new_password})
    
    def projects(self):
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
        cache_key = f"user:email:{email}"
        cached = cache.get(cache_key)
        if cached:
            return cls(**cls.normalise(cached)) if cached else None
        
        user = DBMS.Database.find_one(User.TABLE_NAME, {"email": email})
        
        if isinstance(user, dict):
            if len(user.keys()):
                cache.set(cache_key, user, ttl=60)
                return cls(**cls.normalise(user))
            return None
        elif isinstance(user, list) or isinstance(user, tuple):
            return cls(*user) if len(user) else None
    
    @classmethod
    def get(cls, user_id: str):
        '''
        Class Method for retrieving user by ID

        @param user_id User ID
        @return User instance
        '''
        cache_key = f"user:id:{user_id}"
        cached = cache.get(cache_key)
        if cached:
            return cls(**cls.normalise(cached)) if cached else None
        
        user = DBMS.Database.find_one(User.TABLE_NAME, Model.normalise({'id': user_id}, 'params'))
        
        if isinstance(user, dict):
            if len(user.keys()):
                cache.set(cache_key, user, ttl=60)
                return cls(**cls.normalise(user))
            return None
        elif isinstance(user, list) or isinstance(user, tuple):
            return cls(*user) if len(user) else None
