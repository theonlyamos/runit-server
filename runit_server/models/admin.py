from datetime import datetime
from odbms import DBMS, Model
from ..common.utils import Utils


class Admin(Model):
    '''A model class for admin'''
    TABLE_NAME = 'admins'

    def __init__(self, email: str, name: str, username: str, password: str, role: str, created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.email = email
        self.username = username
        self.name = name
        self.password = password
        self.role = role
        

    def save(self):
        '''
        Instance Method for saving Admin instance to database

        @params None
        @return None
        '''

        data = self.__dict__.copy()
        data['updated_at'] = (datetime.now()).strftime("%a %b %d %Y %H:%M:%S")
        data['password'] =  Utils.hash_password(self.password)

        if DBMS.Database.dbms != 'mongodb':
            del data["created_at"]
            del data["updated_at"]

        return DBMS.Database.insert(Admin.TABLE_NAME, data)
    
    def reset_password(self, new_password: str):
        '''
        Instance Method for resetting admin password

        @param new_password Admin's new password
        @return None
        '''

        DBMS.Database.update(Admin.TABLE_NAME, Admin.normalise({'id': self.id}, 'params'), {'password': new_password})
    

    def json(self)-> dict:
        '''
        Instance Method for converting Admin Instance to Dict

        @paramas None
        @return dict() format of Function instance
        '''
        
        data = super().json()
        data['id'] = str(self.id)
        data['role'] = self.normalise(self.get_role()) # type: ignore

        return data
    
    def get_role(self):
        '''
        Instance Method for retrieving Admin Role

        @params None
        @return List[Role] of Admin Instance
        '''

        return DBMS.Database.find_one('roles', Admin.normalise({'name': self.role}, 'params'))


    @classmethod
    def get_by_username(cls, username: str):
        '''
        Class Method for retrieving admin by username 

        @param username username of the admin 
        @return Admin instance
        '''
        admin = DBMS.Database.find_one(Admin.TABLE_NAME, Admin.normalise({"username": username}, 'params'))
        
        if isinstance(admin, dict):
            return cls(**cls.normalise(admin)) if len(admin.keys()) else None
        elif isinstance(admin, list) or isinstance(admin, tuple):
            return cls(*admin) if len(admin) else None
    
    @classmethod
    def get_by_role(cls, role: str):
        '''
        Class Method for retrieving admin by role 

        @param role Role of the admin 
        @return Admin instance
        '''
        admin = DBMS.Database.find_one(Admin.TABLE_NAME, {"role": role})
        if isinstance(admin, dict):
            return cls(**cls.normalise(admin)) if len(admin.keys()) else None
        elif isinstance(admin, list) or isinstance(admin, tuple):
            return cls(*admin) if len(admin) else None
