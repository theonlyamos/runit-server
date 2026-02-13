from datetime import datetime
from typing import Optional
from bson import ObjectId
from odbms import DBMS, Model


class Schedule(Model):
    TABLE_NAME = 'schedules'
    
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    name: Optional[str] = None
    function: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = 'UTC'
    enabled: Optional[bool] = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: Optional[int] = 0
    description: Optional[str] = None

    def __init__(self, user_id: str, project_id: str, name: str, function: str, 
                 cron_expression: str, timezone: str = 'UTC', enabled: bool = True,
                 description: str = '', last_run=None, next_run=None, run_count: int = 0,
                 created_at=None, updated_at=None, id=None):
        
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = datetime.strptime(created_at, "%a %b %d %Y %H:%M:%S")
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at)
            except ValueError:
                updated_at = datetime.strptime(updated_at, "%a %b %d %Y %H:%M:%S")
        if isinstance(last_run, str):
            try:
                last_run = datetime.fromisoformat(last_run)
            except ValueError:
                last_run = datetime.strptime(last_run, "%a %b %d %Y %H:%M:%S")
        if isinstance(next_run, str):
            try:
                next_run = datetime.fromisoformat(next_run)
            except ValueError:
                next_run = datetime.strptime(next_run, "%a %b %d %Y %H:%M:%S")

        init_kwargs = {
            "user_id": user_id,
            "project_id": project_id,
            "name": name,
            "function": function,
            "cron_expression": cron_expression,
            "timezone": timezone,
            "enabled": enabled,
            "description": description,
            "run_count": run_count,
        }
        if last_run is not None:
            init_kwargs["last_run"] = last_run
        if next_run is not None:
            init_kwargs["next_run"] = next_run
        if created_at is not None:
            init_kwargs["created_at"] = created_at
        if updated_at is not None:
            init_kwargs["updated_at"] = updated_at
        if id is not None:
            init_kwargs["id"] = id

        super().__init__(**init_kwargs)
        self.user_id = user_id
        self.project_id = project_id
        self.name = name
        self.function = function
        self.cron_expression = cron_expression
        self.timezone = timezone
        self.enabled = enabled
        self.description = description
        self.last_run = last_run
        self.next_run = next_run
        self.run_count = run_count

    async def save(self):
        db = self._db()
        data = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        data['updated_at'] = datetime.now()
        
        if db.dbms != 'mongodb':
            del data["created_at"]
            del data["updated_at"]

        if self.id is None:
            result = await db.insert_one(self.TABLE_NAME, self.normalise(data, 'params'))
            if result:
                self.id = result
            return result
        
        if 'id' in data:
            del data['id']
        return await db.update_one(self.TABLE_NAME, self.normalise({'id': self.id}, 'params'), self.normalise(data, 'params'))

    async def update(self, data: dict):
        db = self._db()
        data['updated_at'] = datetime.now()
        return await db.update_one(self.TABLE_NAME, self.normalise({'id': self.id}, 'params'), self.normalise(data, 'params'))

    def json(self) -> dict:
        data = super().json()
        data['id'] = str(self.id)
        data['user_id'] = str(self.user_id)
        data['project_id'] = str(self.project_id)
        data['enabled'] = self.enabled
        data['run_count'] = self.run_count or 0
        return data

    @classmethod
    def _db(cls):
        """Return the database connection, raising if not initialized."""
        if DBMS.Database is None:
            raise RuntimeError("Database not initialized")
        return DBMS.Database

    @classmethod
    async def get_by_user(cls, user_id: str):
        db = cls._db()
        schedules = await db.find(cls.TABLE_NAME, cls.normalise({'user_id': user_id}, 'params'))
        return [cls(**cls.normalise(elem)) for elem in schedules]

    @classmethod
    async def get_by_project(cls, project_id: str):
        db = cls._db()
        schedules = await db.find(cls.TABLE_NAME, cls.normalise({'project_id': project_id}, 'params'))
        return [cls(**cls.normalise(elem)) for elem in schedules]

    @classmethod
    async def get_enabled(cls):
        db = cls._db()
        schedules = await db.find(cls.TABLE_NAME, cls.normalise({'enabled': True}, 'params'))
        return [cls(**cls.normalise(elem)) for elem in schedules]

    @classmethod
    async def delete_by_project(cls, project_id: str):
        db = cls._db()
        return await db.delete_many(cls.TABLE_NAME, cls.normalise({'project_id': project_id}, 'params'))
