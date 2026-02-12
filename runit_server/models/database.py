from datetime import datetime
from typing import Optional

from pydantic import Field
from odbms import DBMS, Model


def _parse_datetime(value):
    if not isinstance(value, str):
        return value
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    for fmt in ("%a %b %d %Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


class Database(Model):
    TABLE_NAME = 'databases'
    name: Optional[str] = None
    collection_name: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = ''
    collection_schema: Optional[dict] = Field(default_factory=dict, alias="schema")

    def __init__(self, name: str, collection_name: str, user_id: str, project_id: str = '', schema: dict = None, created_at=None, updated_at=None, id=None, **kwargs):
        created_at = _parse_datetime(created_at)
        updated_at = _parse_datetime(updated_at)
        init_kwargs = {
            "name": name,
            "collection_name": collection_name,
            "user_id": user_id,
            "project_id": project_id,
            "schema": schema or {},
        }
        if created_at is not None:
            init_kwargs["created_at"] = created_at
        if updated_at is not None:
            init_kwargs["updated_at"] = updated_at
        if id is not None:
            init_kwargs["id"] = id
        init_kwargs.update(kwargs)
        super().__init__(**init_kwargs)

    def user(self):
        '''
        Instance Method for retrieving User of Database instance
        
        @params None
        @return User Instance
        '''

        return Model.normalise(DBMS.Database.find_one('users', Model.normalise({'id': self.user_id}, 'params'))) # type: ignore

    @classmethod
    def get_by_name(cls, collection_name: str)-> list:
        '''
        Class Method for retrieving collection by a name

        @param collectinon_name:str name of the collection
        @return List of Database instances
        '''
        
        databases = DBMS.Database.find(Database.TABLE_NAME, Model.normalise({'name': collection_name}, 'params'))
        
        return [cls(**Model.normalise(elem)) for elem in databases]
    
    @classmethod
    async def get_by_user(cls, user_id: str)-> list:
        '''
        Class Method for retrieving databases by a user

        @param user_id:str _id of the user
        @return List of Database instances
        '''
        
        databases = await DBMS.Database.find(Database.TABLE_NAME, Model.normalise({'user_id': user_id}, 'params'))
        
        return [cls(**Model.normalise(elem)) for elem in databases]
