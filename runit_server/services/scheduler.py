import os
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

from ..constants import PROJECTS_DIR

if TYPE_CHECKING:
    from ..models import Schedule, Project

logger = logging.getLogger(__name__)


class ScheduleService:
    _instance: Optional['ScheduleService'] = None
    scheduler: Optional[AsyncIOScheduler] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.scheduler = None
        return cls._instance
    
    def get_scheduler(self) -> AsyncIOScheduler:
        if self.scheduler is None:
            self.scheduler = AsyncIOScheduler()
        return self.scheduler
    
    async def start(self):
        from ..models import Schedule
        
        scheduler = self.get_scheduler()
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler started")
            await self.load_all_schedules()
    
    async def shutdown(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown")
    
    async def load_all_schedules(self):
        from odbms import DBMS
        from ..models import Schedule

        if DBMS.Database is None:
            logger.debug("Database not initialized, skipping schedule load")
            return

        try:
            schedules = await Schedule.get_enabled()
            for schedule in schedules:
                await self.add_job(schedule)
            logger.info(f"Loaded {len(schedules)} scheduled jobs")
        except Exception as e:
            logger.error(f"Error loading schedules: {e}")
    
    async def add_job(self, schedule: 'Schedule'):
        scheduler = self.get_scheduler()
        job_id = f"schedule_{schedule.id}"
        
        try:
            try:
                scheduler.remove_job(job_id)
            except JobLookupError:
                pass
            
            if not schedule.enabled:
                return
            
            trigger = CronTrigger.from_crontab(
                schedule.cron_expression,
                timezone=schedule.timezone
            )
            
            scheduler.add_job(
                self.execute_schedule,
                trigger=trigger,
                id=job_id,
                args=[str(schedule.id)],
                name=schedule.name,
                replace_existing=True
            )
            
            logger.info(f"Added job: {schedule.name} ({schedule.cron_expression})")
        except Exception as e:
            logger.error(f"Error adding job {schedule.name}: {e}")
    
    async def remove_job(self, schedule_id: str):
        scheduler = self.get_scheduler()
        job_id = f"schedule_{schedule_id}"
        
        try:
            scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
        except JobLookupError:
            pass
    
    async def execute_schedule(self, schedule_id: str):
        from ..models import Schedule, Project
        
        try:
            schedule = await Schedule.get(schedule_id)
            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return
            
            project = await Project.get(schedule.project_id)
            if not project:
                logger.error(f"Project {schedule.project_id} not found for schedule {schedule_id}")
                return
            
            logger.info(f"Executing schedule: {schedule.name} - Function: {schedule.function}")
            
            result = await self.run_function(project, schedule.function)
            
            run_count = (schedule.run_count or 0) + 1
            await schedule.update({
                'last_run': datetime.now(),
                'run_count': run_count
            })
            
            await self.log_execution(schedule, project, result, success=True)
            
            logger.info(f"Schedule {schedule.name} executed successfully. Run count: {run_count}")
            
        except Exception as e:
            logger.error(f"Error executing schedule {schedule_id}: {e}")
            try:
                schedule = await Schedule.get(schedule_id)
                if schedule:
                    await self.log_execution(schedule, None, str(e), success=False)
            except Exception:
                pass
    
    async def run_function(self, project: 'Project', function_name: str) -> dict:
        project_path = Path(PROJECTS_DIR, str(project.id))
        
        if not project_path.exists():
            raise Exception(f"Project path not found: {project_path}")
        
        from runit import RunIt
        
        try:
            result = await RunIt.start(str(project.id), function_name, PROJECTS_DIR)
            return {
                'function': function_name,
                'project_id': str(project.id),
                'result': result,
                'executed_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error running function {function_name}: {e}")
            raise
    
    async def log_execution(self, schedule: 'Schedule', project: Optional['Project'], 
                           result: any, success: bool):
        try:
            from ..models import ScheduleLog
            
            log = ScheduleLog(
                schedule_id=str(schedule.id),
                project_id=str(schedule.project_id),
                user_id=str(schedule.user_id),
                function=schedule.function or '',
                success=success,
                result=str(result) if result else None,
                error_message=str(result) if not success else None
            )
            await log.save()
        except Exception as e:
            logger.error(f"Error logging execution: {e}")
    
    async def get_next_run_time(self, schedule_id: str) -> Optional[datetime]:
        scheduler = self.get_scheduler()
        job_id = f"schedule_{schedule_id}"
        
        try:
            job = scheduler.get_job(job_id)
            if job and job.next_run_time:
                return job.next_run_time
        except Exception:
            pass
        return None


schedule_service = ScheduleService()
