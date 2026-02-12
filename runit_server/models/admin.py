from datetime import datetime
from typing import Optional
from bson import ObjectId
from odbms import DBMS, Model
from ..common.utils import Utils


class Admin(Model):
    '''A model class for admin'''
    TABLE_NAME = 'admins'
    
    # Define fields for Pydantic with default values
    email: Optional[str] = None
    name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None

    def __init__(self, email: Optional[str] = None, name: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None, role: Optional[str] = None, created_at=None, updated_at=None, id=None, **kwargs):
        # Build kwargs dynamically, only including non-None values for datetime fields
        init_kwargs = {}
        if email is not None:
            init_kwargs['email'] = email
        if name is not None:
            init_kwargs['name'] = name
        if username is not None:
            init_kwargs['username'] = username
        if password is not None:
            init_kwargs['password'] = password
        if role is not None:
            init_kwargs['role'] = role
        
        # Handle datetime fields - convert strings to datetime if needed
        if created_at is not None:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    created_at = datetime.strptime(created_at, "%a %b %d %Y %H:%M:%S")
            init_kwargs['created_at'] = created_at
        if updated_at is not None:
            if isinstance(updated_at, str):
                try:
                    updated_at = datetime.fromisoformat(updated_at)
                except ValueError:
                    updated_at = datetime.strptime(updated_at, "%a %b %d %Y %H:%M:%S")
            init_kwargs['updated_at'] = updated_at
        if id is not None:
            init_kwargs['id'] = id
        init_kwargs.update(kwargs)
        super().__init__(**init_kwargs)

    async def save(self):
        '''
        Instance Method for saving Admin instance to database

        @params None
        @return None
        '''

        data = self.__dict__.copy()
        data['updated_at'] = datetime.now()
        
        if DBMS.Database.dbms != 'mongodb':
            del data["created_at"]
            del data["updated_at"]

        # Check if this is a new record (id is None) or existing record
        if self.id is None:
            # New record - insert it
            if self.password is not None:
                data['password'] = Utils.hash_password(str(self.password))
            result = await DBMS.Database.insert_one(self.TABLE_NAME, self.normalise(data, 'params'))
            # Set the id on the instance after insert
            if result:
                self.id = result
            return result
        
        # Update the existing record in database
        if 'password' in data:
            del data['password']
        return await DBMS.Database.update_one(self.TABLE_NAME, self.normalise({'id': self.id}, 'params'), self.normalise(data, 'params'))
    
    async def reset_password(self, new_password: str):
        '''
        Instance Method for resetting admin password

        @param new_password Admin's new password
        @return None
        '''

        hashed = Utils.hash_password(new_password)
        await DBMS.Database.update_one(Admin.TABLE_NAME, Admin.normalise({'id': self.id}, 'params'), {'password': hashed})
    

    async def json(self) -> dict:
        '''
        Instance Method for converting Admin Instance to Dict

        @paramas None
        @return dict() format of Function instance
        '''
        
        data = super().json()
        data['id'] = str(self.id)
        role = await self.get_role()
        data['role'] = self.normalise(role) if role else None

        return data
    
    async def get_role(self):
        '''
        Instance Method for retrieving Admin Role

        @params None
        @return List[Role] of Admin Instance
        '''

        return await DBMS.Database.find_one('roles', Admin.normalise({'name': self.role}, 'params'))


    @classmethod
    async def get_by_username(cls, username: str):
        '''
        Class Method for retrieving admin by username 

        @param username username of the admin 
        @return Admin instance
        '''
        admin = await DBMS.Database.find_one(Admin.TABLE_NAME, Admin.normalise({"username": username}, 'params'))
        
        if isinstance(admin, dict) and len(admin.keys()):
            # Normalize the data from database to match our field names
            normalized = cls.normalise(admin)
            return cls(
                email=normalized.get('email', ''),
                name=normalized.get('name', ''),
                username=normalized.get('username', ''),
                password=normalized.get('password', ''),
                role=normalized.get('role', ''),
                created_at=normalized.get('created_at'),
                updated_at=normalized.get('updated_at'),
                id=normalized.get('id')
            )
        return None
    
    @classmethod
    async def get_by_role(cls, role: str):
        '''
        Class Method for retrieving admin by role 

        @param role Role of the admin 
        @return Admin instance
        '''
        admin = await DBMS.Database.find_one(Admin.TABLE_NAME, {"role": role})
        if isinstance(admin, dict) and len(admin.keys()):
            # Normalize the data from database to match our field names
            normalized = cls.normalise(admin)
            return cls(
                email=normalized.get('email', ''),
                name=normalized.get('name', ''),
                username=normalized.get('username', ''),
                password=normalized.get('password', ''),
                role=normalized.get('role', ''),
                created_at=normalized.get('created_at'),
                updated_at=normalized.get('updated_at'),
                id=normalized.get('id')
            )
        return None
