from datetime import datetime
from bson.objectid import ObjectId
from typing import Optional
from odbms import DBMS, Model

from ..common.utils import Utils
from ..common.cache import cached, cache


class User(Model):
    '''A model class for user'''
    TABLE_NAME = 'users'
    email: Optional[str] = None
    name: Optional[str] = None
    password: Optional[str] = None
    image: Optional[str] = ''
    gat: Optional[str] = ''
    grt: Optional[str] = ''

    @staticmethod
    def _parse_datetime(value):
        if not isinstance(value, str):
            return value
        for parser in (datetime.fromisoformat,):
            try:
                return parser(value)
            except ValueError:
                pass
        for fmt in ("%a %b %d %Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                pass
        return None

    def __init__(self, email: str, name: str, password: str, 
                 image: str = '', gat: str ='', 
                 grt: str ='', created_at=None, 
                 updated_at=None, id=None):
        created_at = User._parse_datetime(created_at)
        updated_at = User._parse_datetime(updated_at)

        init_kwargs = {
            'email': email,
            'name': name,
            'password': password,
            'image': image,
            'gat': gat,
            'grt': grt
        }
        if created_at is not None:
            init_kwargs['created_at'] = created_at
        if updated_at is not None:
            init_kwargs['updated_at'] = updated_at
        if id is not None:
            init_kwargs['id'] = id

        super().__init__(**init_kwargs)
        self.email = email
        self.name = name
        self.password = password
        self.image = image
        self.gat = gat
        self.grt = grt
        

    async def save(self):
        '''
        Instance Method for saving User instance to Database

        @params None
        @return None
        '''
        
        data = self.model_dump()
        data['updated_at'] = datetime.now()
        
        if DBMS.Database.dbms != 'mongodb':
            del data["created_at"]
            del data["updated_at"]

        if isinstance(self.id, ObjectId) or self.id is None:
            data['password'] = Utils.hash_password(self.password)
            cache.delete(f"user:email:{self.email}")
            result = await DBMS.Database.insert_one(User.TABLE_NAME, Model.normalise(data, 'params'))
            if result:
                self.id = str(result) if isinstance(result, ObjectId) else result
            return result
        
        cache.delete(f"user:id:{self.id}")
        cache.delete(f"user:email:{self.email}")
        del data['password']
        return await DBMS.Database.update_one(User.TABLE_NAME, self.normalise({'id': self.id}, 'params'), self.normalise(data, 'params'))
        
        
    
    async def reset_password(self, new_password: str):
        '''
        Instance Method for resetting user password

        @param new_password User's new password
        @return None
        '''
        
        new_password = Utils.hash_password(new_password)
        
        cache.delete(f"user:id:{self.id}")
        cache.delete(f"user:email:{self.email}")

        await DBMS.Database.update_one(User.TABLE_NAME, User.normalise({'id': self.id}, 'params'), {'password': new_password})
    
    def projects(self):
        '''
        Instance Method for retrieving Projects of User Instance

        @params None
        @return List of Project Instances
        '''

        return DBMS.Database.find('projects', {'user_id': self.id})
    
    async def count_projects(self):
        '''
        Instance Method for counting User Projects

        @params None
        @return int Count of Projects
        '''

        return await DBMS.Database.count('projects', User.normalise({'user_id': self.id}, 'params'))
    
    def json(self)-> dict:
        '''
        Instance Method for converting User Instance to Dict

        @paramas None
        @return dict() format of Function instance
        '''
        
        data = super().json()
        return data

    @classmethod
    async def get_by_email(cls, email: str):
        '''
        Class Method for retrieving user by email address

        @param email email address of the user 
        @return User instance
        '''
        cache_key = f"user:email:{email}"
        cached = cache.get(cache_key)
        if cached:
            return cls(**cls.normalise(cached)) if cached else None
        
        user = await DBMS.Database.find_one(User.TABLE_NAME, {"email": email})
        
        if isinstance(user, dict):
            if len(user.keys()):
                cache.set(cache_key, user, ttl=60)
                return cls(**cls.normalise(user))
            return None
        elif isinstance(user, list) or isinstance(user, tuple):
            return cls(*user) if len(user) else None
    
    @classmethod
    async def get(cls, user_id: str):
        '''
        Class Method for retrieving user by ID

        @param user_id User ID
        @return User instance
        '''
        cache_key = f"user:id:{user_id}"
        cached = cache.get(cache_key)
        if cached:
            return cls(**cls.normalise(cached)) if cached else None
        
        user = await DBMS.Database.find_one(User.TABLE_NAME, Model.normalise({'id': user_id}, 'params'))
        
        if isinstance(user, dict):
            if len(user.keys()):
                cache.set(cache_key, user, ttl=60)
                return cls(**cls.normalise(user))
            return None
        elif isinstance(user, list) or isinstance(user, tuple):
            return cls(*user) if len(user) else None
