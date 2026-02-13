import os
import logging
from pathlib import Path
from typing import Annotated, Optional
from datetime import datetime

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import APIRouter, Form, Request, Depends, status

from ..core import flash, templates
from ..common import get_session
from ..models import User, Project, Schedule, ScheduleLog

from runit import RunIt
from ..constants import (
    PROJECTS_DIR,
    LANGUAGE_TO_ICONS
)

SCHEDULE_INDEX_URL = 'list_user_schedules'

schedule = APIRouter(
    prefix="/schedules",
    tags=["schedules"],
    dependencies=[Depends(get_session)]
)

CRON_PRESETS = [
    {'label': 'Every minute', 'expression': '* * * * *'},
    {'label': 'Every 5 minutes', 'expression': '*/5 * * * *'},
    {'label': 'Every 15 minutes', 'expression': '*/15 * * * *'},
    {'label': 'Every 30 minutes', 'expression': '*/30 * * * *'},
    {'label': 'Every hour', 'expression': '0 * * * *'},
    {'label': 'Every 2 hours', 'expression': '0 */2 * * *'},
    {'label': 'Every day at midnight', 'expression': '0 0 * * *'},
    {'label': 'Every day at 6 AM', 'expression': '0 6 * * *'},
    {'label': 'Every day at noon', 'expression': '0 12 * * *'},
    {'label': 'Every day at 6 PM', 'expression': '0 18 * * *'},
    {'label': 'Every week (Sunday midnight)', 'expression': '0 0 * * 0'},
    {'label': 'Every month (1st midnight)', 'expression': '0 0 1 * *'},
]

TIMEZONES = [
    'UTC', 'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
    'America/Sao_Paulo', 'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Moscow',
    'Asia/Dubai', 'Asia/Kolkata', 'Asia/Bangkok', 'Asia/Singapore', 'Asia/Tokyo',
    'Asia/Shanghai', 'Australia/Sydney', 'Pacific/Auckland'
]


@schedule.get('')
@schedule.get('/')
async def list_user_schedules(request: Request, view: Optional[str] = None):
    user_id = request.session['user_id']
    user = await User.get(user_id)
    user = user.json() if user else None
    
    if view:
        request.session['schedules_view'] = view
    elif 'schedules_view' not in request.session.keys():
        request.session['schedules_view'] = 'grid'
    
    schedules = await Schedule.get_by_user(user_id)
    schedules_data = []
    
    for sched in schedules:
        sched_data = sched.json()
        project = await Project.get(sched.project_id)
        sched_data['project'] = project.json() if project else None
        schedules_data.append(sched_data)
    
    projects = await Project.get_by_user(user_id)
    projects_data = [p.json() for p in projects]
    
    return templates.TemplateResponse('schedules/index.html', context={
        'request': request, 'page': 'schedules', 'schedules': schedules_data,
        'projects': projects_data, 'user': user, 'icons': LANGUAGE_TO_ICONS,
        'cron_presets': CRON_PRESETS, 'timezones': TIMEZONES})


@schedule.get('/project/{project_id}')
@schedule.get('/project/{project_id}/')
async def list_project_schedules(request: Request, project_id: str):
    user_id = request.session['user_id']
    user = await User.get(user_id)
    user = user.json() if user else None
    
    project = await Project.get(project_id)
    if not project:
        flash(request, 'Project not found', 'danger')
        return RedirectResponse(request.url_for('list_user_schedules'))
    
    schedules = await Schedule.get_by_project(project_id)
    schedules_data = [s.json() for s in schedules]
    
    old_curdir = os.curdir
    os.chdir(Path(PROJECTS_DIR, str(project.id)))
    
    functions = []
    try:
        runit = RunIt(**RunIt.load_config())
        for func in runit.get_functions():
            functions.append({'name': func})
    except Exception:
        pass
    
    os.chdir(old_curdir)
    
    project_data = project.json()
    project_data['functions'] = functions
    
    return templates.TemplateResponse('schedules/index.html', context={
        'request': request, 'page': 'schedules', 'schedules': schedules_data,
        'project': project_data, 'user': user, 'icons': LANGUAGE_TO_ICONS,
        'cron_presets': CRON_PRESETS, 'timezones': TIMEZONES})


@schedule.get('/{schedule_id}')
@schedule.get('/{schedule_id}/')
async def get_schedule_details(request: Request, schedule_id: str):
    user_id = request.session['user_id']
    user = await User.get(user_id)
    user = user.json() if user else None
    
    sched = await Schedule.get(schedule_id)
    if not sched:
        flash(request, 'Schedule not found', 'danger')
        return RedirectResponse(request.url_for(SCHEDULE_INDEX_URL))
    
    sched_data = sched.json()
    project = await Project.get(sched.project_id)
    sched_data['project'] = project.json() if project else None
    
    logs = await ScheduleLog.get_by_schedule(schedule_id, limit=50)
    logs_data = [log.json() for log in logs]
    
    projects = await Project.get_by_user(user_id)
    projects_data = [p.json() for p in projects]
    
    return templates.TemplateResponse('schedules/details.html', context={
        'request': request, 'page': 'schedules', 'schedule': sched_data,
        'projects': projects_data, 'logs': logs_data, 'user': user, 'icons': LANGUAGE_TO_ICONS,
        'cron_presets': CRON_PRESETS, 'timezones': TIMEZONES})


@schedule.post('')
@schedule.post('/')
async def create_schedule(
    request: Request,
    project_id: Annotated[str, Form()],
    name: Annotated[str, Form()],
    function: Annotated[str, Form()],
    cron_expression: Annotated[str, Form()],
    timezone: Annotated[str, Form()] = 'UTC',
    enabled: Annotated[Optional[str], Form()] = None,
    description: Annotated[Optional[str], Form()] = ''
):
    user_id = request.session['user_id']
    
    project = await Project.get(project_id)
    if not project:
        return JSONResponse(
            {'success': False, 'message': 'Project not found'},
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    existing = await Schedule.find_one({'user_id': user_id, 'name': name, 'project_id': project_id})
    if existing:
        return JSONResponse(
            {'success': False, 'message': 'A schedule with this name already exists for this project'},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    new_schedule = Schedule(
        user_id=user_id,
        project_id=project_id,
        name=name,
        function=function,
        cron_expression=cron_expression,
        timezone=timezone,
        enabled=enabled == 'on',
        description=description or ''
    )
    
    await new_schedule.save()
    
    if new_schedule.enabled:
        from ..services.scheduler import schedule_service
        await schedule_service.add_job(new_schedule)
    
    return JSONResponse({'success': True, 'message': 'Schedule created successfully', 'schedule_id': str(new_schedule.id)})


@schedule.post('/{schedule_id}')
@schedule.post('/{schedule_id}/')
async def update_schedule(
    request: Request,
    schedule_id: str,
    project_id: Annotated[str, Form()] = '',
    name: Annotated[str, Form()] = '',
    function: Annotated[str, Form()] = '',
    cron_expression: Annotated[str, Form()] = '',
    timezone: Annotated[str, Form()] = 'UTC',
    enabled: Annotated[Optional[str], Form()] = None,
    description: Annotated[Optional[str], Form()] = ''
):
    sched = await Schedule.get(schedule_id)
    if not sched:
        return JSONResponse(
            {'success': False, 'message': 'Schedule not found'},
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    update_data = {}
    
    if name:
        update_data['name'] = name
    if function:
        update_data['function'] = function
    if cron_expression:
        update_data['cron_expression'] = cron_expression
    if timezone:
        update_data['timezone'] = timezone
    update_data['enabled'] = enabled == 'on'
    if description is not None:
        update_data['description'] = description
    
    await sched.update(update_data)
    
    from ..services.scheduler import schedule_service
    if sched.enabled:
        await schedule_service.add_job(sched)
    else:
        await schedule_service.remove_job(str(sched.id))
    
    return JSONResponse({'success': True, 'message': 'Schedule updated successfully'})


@schedule.post('/{schedule_id}/toggle')
@schedule.post('/{schedule_id}/toggle/')
async def toggle_schedule(request: Request, schedule_id: str):
    sched = await Schedule.get(schedule_id)
    if not sched:
        return JSONResponse(
            {'success': False, 'message': 'Schedule not found'},
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    new_status = not sched.enabled
    await sched.update({'enabled': new_status})
    
    from ..services.scheduler import schedule_service
    if new_status:
        await schedule_service.add_job(sched)
    else:
        await schedule_service.remove_job(schedule_id)
    
    return JSONResponse({
        'success': True, 
        'message': f'Schedule {"enabled" if new_status else "disabled"} successfully',
        'enabled': new_status
    })


@schedule.post('/{schedule_id}/delete')
@schedule.post('/{schedule_id}/delete/')
async def delete_schedule(request: Request, schedule_id: str):
    user_id = request.session['user_id']
    
    sched = await Schedule.get(schedule_id)
    if not sched:
        return JSONResponse(
            {'success': False, 'message': 'Schedule not found'},
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    if str(sched.user_id) != str(user_id):
        return JSONResponse(
            {'success': False, 'message': 'Unauthorized'},
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    from ..services.scheduler import schedule_service
    await schedule_service.remove_job(schedule_id)
    await Schedule.delete_many({'id': schedule_id})
    
    return JSONResponse({'success': True, 'message': 'Schedule deleted successfully'})


@schedule.get('/functions/{project_id}')
@schedule.get('/functions/{project_id}/')
async def get_project_functions(request: Request, project_id: str):
    project = await Project.get(project_id)
    if not project:
        return JSONResponse({'success': False, 'functions': []})
    
    old_curdir = os.curdir
    os.chdir(Path(PROJECTS_DIR, str(project.id)))
    
    functions = []
    try:
        runit = RunIt(**RunIt.load_config())
        for func in runit.get_functions():
            functions.append(func)
    except Exception as e:
        logging.error(f"Error getting functions: {e}")
    
    os.chdir(old_curdir)
    
    return JSONResponse({'success': True, 'functions': functions})
