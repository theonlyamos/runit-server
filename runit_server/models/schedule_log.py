from datetime import datetime
from typing import Optional
from odbms import DBMS, Model


class ScheduleLog(Model):
    TABLE_NAME = 'schedule_logs'
    
    schedule_id: Optional[str] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    function: Optional[str] = None
    success: Optional[bool] = True
    result: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None

    def __init__(self, schedule_id: str, project_id: str, user_id: str,
                 function: str, success: bool = True, result: str = None,
                 error_message: str = None, duration_ms: int = None,
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

        init_kwargs = {
            "schedule_id": schedule_id,
            "project_id": project_id,
            "user_id": user_id,
            "function": function,
            "success": success,
            "result": result,
            "error_message": error_message,
            "duration_ms": duration_ms,
        }
        if created_at is not None:
            init_kwargs["created_at"] = created_at
        if updated_at is not None:
            init_kwargs["updated_at"] = updated_at
        if id is not None:
            init_kwargs["id"] = id

        super().__init__(**init_kwargs)
        self.schedule_id = schedule_id
        self.project_id = project_id
        self.user_id = user_id
        self.function = function
        self.success = success
        self.result = result
        self.error_message = error_message
        self.duration_ms = duration_ms

    async def save(self):
        data = {
            'schedule_id': self.schedule_id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'function': self.function,
            'success': self.success,
            'result': self.result,
            'error_message': self.error_message,
            'duration_ms': self.duration_ms,
            'created_at': datetime.now()
        }
        
        if self.id is None:
            result = await DBMS.Database.insert_one(self.TABLE_NAME, self.normalise(data, 'params'))
            if result:
                self.id = result
            return result
        
        if 'id' in data:
            del data['id']
        return await DBMS.Database.update_one(self.TABLE_NAME, self.normalise({'id': self.id}, 'params'), self.normalise(data, 'params'))

    def json(self) -> dict:
        data = super().json()
        data['id'] = str(self.id)
        data['schedule_id'] = str(self.schedule_id)
        data['project_id'] = str(self.project_id)
        data['user_id'] = str(self.user_id)
        data['success'] = self.success
        return data

    @classmethod
    async def get_by_schedule(cls, schedule_id: str, limit: int = 50):
        logs = await DBMS.Database.find(
            cls.TABLE_NAME, 
            cls.normalise({'schedule_id': schedule_id}, 'params'),
            limit=limit,
            sort=[('created_at', -1)]
        )
        return [cls(**cls.normalise(elem)) for elem in logs]

    @classmethod
    async def get_by_user(cls, user_id: str, limit: int = 50):
        logs = await DBMS.Database.find(
            cls.TABLE_NAME,
            cls.normalise({'user_id': user_id}, 'params'),
            limit=limit,
            sort=[('created_at', -1)]
        )
        return [cls(**cls.normalise(elem)) for elem in logs]

    @classmethod
    async def get_by_project(cls, project_id: str, limit: int = 50):
        logs = await DBMS.Database.find(
            cls.TABLE_NAME,
            cls.normalise({'project_id': project_id}, 'params'),
            limit=limit,
            sort=[('created_at', -1)]
        )
        return [cls(**cls.normalise(elem)) for elem in logs]

    @classmethod
    async def delete_by_schedule(cls, schedule_id: str):
        return await DBMS.Database.delete_many(cls.TABLE_NAME, cls.normalise({'schedule_id': schedule_id}, 'params'))
