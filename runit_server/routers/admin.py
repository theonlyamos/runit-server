import logging
import os
import shutil
import time
from pathlib import Path
from typing import Annotated, Optional, Dict
import aiofiles

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request, Depends,\
    status, UploadFile
    
from dotenv import dotenv_values

from odbms import DBMS

from ..core import flash, templates
from ..common import get_admin_session
from ..common import Utils
from ..models import User
from ..models import Project
from ..models import Admin
from ..models import Role
from ..models import Function
from ..models import Database
from ..models import Collection
from ..models import Schedule
from ..models import ScheduleLog

from ..constants import (
    PROJECTS_DIR,
    EXTENSIONS,
    LANGUAGE_TO_ICONS,
    LANGUAGE_TO_RUNTIME
)

ADMIN_LOGIN_PAGE = 'admin_login_page'
ADMIN_DATABASE_INDEX = 'admin_list_databases'
ADMIN_PROJECTS_INDEX = 'admin_list_projects'
ADMIN_ADMINISTRATORS_INDEX = 'admin_list_administrators'

from runit import RunIt

admin = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin_session)]
)

@admin.get('/')
async def admin_dashboard(request: Request):
    admin = await Admin.get(request.session['admin_id'])
    return templates.TemplateResponse('admin/index.html', context={
        'request': request, 'page': 'home', 'admin': admin,
        'admin_name': admin.name if admin else ''})

@admin.get('/users/')
async def admin_list_users(request: Request, view: Optional[str] = None):
    users = await User.all()

    users_data = []
    for user in users:
        projects = await user.count_projects()
        user_data = user.json()
        user_data['projects'] = projects
        users_data.append(user_data)

    if view:
        request.session['view'] = view
    elif 'view' not in request.session.keys():
        request.session['view'] = 'grid'

    return templates.TemplateResponse('admin/users/index.html', context={
        'request': request, 'page': 'users', 'users': users_data,
        'icons': LANGUAGE_TO_ICONS})

@admin.get('/users/{user_id}')
@admin.get('/users/{user_id}/')
async def admin_get_user(request: Request, user_id: str):
    try:
        user = await User.get(user_id)  # type: ignore
        if not user:
            raise Exception('User not found')
        
        projects = await Project.get_by_user(str(user.id))
        databases = await Database.get_by_user(str(user.id))
        admin_record = await Admin.find_one({'email': user.email})
        
        user_data = user.json()
        user_data['projects'] = len(projects)
        user_data['databases'] = len(databases)
        user_data['is_admin'] = admin_record is not None
        
        return templates.TemplateResponse('admin/users/details.html', context={
            'request': request, 'page': 'users', 'user': user_data,
            'projects': projects, 'icons': LANGUAGE_TO_ICONS})
    except Exception as e:
        flash(request, str(e), 'danger')
        return RedirectResponse(request.url_for('admin_list_users'))
    
@admin.put('/users/{user_id}')
@admin.put('/users/{user_id}/')
@admin.post('/users/{user_id}')
@admin.post('/users/{user_id}/')
async def admin_update_user(
    request: Request,
    user_id: str,
    name: Annotated[str, Form()] = '',
    email: Annotated[str, Form()] = '',
    is_admin: Annotated[Optional[str], Form()] = None
):
    try:
        user = await User.get(user_id)  # type: ignore
        if not user:
            return JSONResponse(
                {'success': False, 'message': 'User not found'},
                status_code=status.HTTP_404_NOT_FOUND
            )

        if not name or not email:
            return JSONResponse(
                {'success': False, 'message': 'Name and email are required'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        old_email = user.email

        existing_user = await User.get_by_email(email)
        if existing_user and str(existing_user.id) != str(user_id):
            return JSONResponse(
                {'success': False, 'message': 'Email is already in use by another user'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        await user.update({'name': name, 'email': email})

        return JSONResponse({'success': True, 'message': 'User updated successfully'})
    except Exception as e:
        logging.exception('Error updating user')
        return JSONResponse(
            {'success': False, 'message': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@admin.post('/users/{user_id}/reset-password')
@admin.post('/users/{user_id}/reset-password/')
async def admin_reset_user_password(
    request: Request,
    user_id: str,
    new_password: Annotated[str, Form()] = '',
    confirm_password: Annotated[str, Form()] = ''
):
    try:
        user = await User.get(user_id)  # type: ignore
        if not user:
            return JSONResponse(
                {'success': False, 'message': 'User not found'},
                status_code=status.HTTP_404_NOT_FOUND
            )

        if not new_password:
            return JSONResponse(
                {'success': False, 'message': 'Password is required'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return JSONResponse(
                {'success': False, 'message': 'Passwords do not match'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return JSONResponse(
                {'success': False, 'message': 'Password must be at least 6 characters'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        await user.reset_password(new_password)
        return JSONResponse({'success': True, 'message': 'Password reset successfully'})
    except Exception as e:
        logging.exception('Error resetting user password')
        return JSONResponse(
            {'success': False, 'message': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@admin.post('/users/{user_id}/delete')
@admin.post('/users/{user_id}/delete/')
async def admin_delete_user(request: Request, user_id: str, background_task: BackgroundTasks):
    try:
        user = await User.get(user_id)  # type: ignore
        if not user:
            return JSONResponse(
                {'success': False, 'message': 'User not found'},
                status_code=status.HTTP_404_NOT_FOUND
            )

        projects = await Project.get_by_user(str(user.id))

        for project in projects:
            project_path = Path(PROJECTS_DIR, str(project.id))
            if project_path.exists():
                background_task.add_task(shutil.rmtree, project_path)
            await Project.delete_many({'id': str(project.id), 'user_id': str(user.id)})

        await Database.delete_many({'user_id': str(user.id)})
        await Admin.delete_many({'email': user.email})
        await User.delete_many({'id': str(user.id)})

        return JSONResponse({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        logging.exception('Error deleting user')
        return JSONResponse(
            {'success': False, 'message': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# --- Administrators ---
@admin.get('/administrators/')
async def admin_list_administrators(request: Request, view: Optional[str] = None):
    admins = await Admin.all()
    admins_data = []
    for a in admins:
        admins_data.append(await a.json())

    if view:
        request.session['administrators_view'] = view
    elif 'administrators_view' not in request.session.keys():
        request.session['administrators_view'] = 'grid'

    raw_roles = await DBMS.Database.find(Role.TABLE_NAME, {})
    roles = [{'name': r.get('name', '')} for r in raw_roles if r.get('name')]

    return templates.TemplateResponse('admin/administrators/index.html', context={
        'request': request, 'page': 'administrators', 'admins': admins_data,
        'roles': roles, 'icons': LANGUAGE_TO_ICONS})


@admin.get('/administrators/{admin_id}')
@admin.get('/administrators/{admin_id}/')
async def admin_get_administrator(request: Request, admin_id: str):
    try:
        admin_record = await Admin.get(admin_id)  # type: ignore
        if not admin_record:
            raise Exception('Administrator not found')

        admin_data = await admin_record.json()
        raw_roles = await DBMS.Database.find(Role.TABLE_NAME, {})
        roles = [{'name': r.get('name', '')} for r in raw_roles if r.get('name')]
        is_self = str(request.session.get('admin_id', '')) == str(admin_id)

        return templates.TemplateResponse('admin/administrators/details.html', context={
            'request': request, 'page': 'administrators', 'admin': admin_data,
            'roles': roles, 'is_self': is_self, 'icons': LANGUAGE_TO_ICONS})
    except Exception as e:
        flash(request, str(e), 'danger')
        return RedirectResponse(request.url_for(ADMIN_ADMINISTRATORS_INDEX))


@admin.post('/administrators')
@admin.post('/administrators/')
async def admin_create_administrator(
    request: Request,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    role: Annotated[str, Form()] = 'subadmin'
):
    try:
        existing = await Admin.get_by_username(username)
        if existing:
            flash(request, 'Username already exists', 'danger')
            return RedirectResponse(request.url_for(ADMIN_ADMINISTRATORS_INDEX), status_code=status.HTTP_303_SEE_OTHER)

        new_admin = Admin(email=email, name=name, username=username, password=password, role=role)
        await new_admin.save()
        flash(request, 'Administrator created successfully', 'success')
    except Exception as e:
        flash(request, str(e), 'danger')
    return RedirectResponse(request.url_for(ADMIN_ADMINISTRATORS_INDEX), status_code=status.HTTP_303_SEE_OTHER)


@admin.put('/administrators/{admin_id}')
@admin.put('/administrators/{admin_id}/')
@admin.post('/administrators/{admin_id}')
@admin.post('/administrators/{admin_id}/')
async def admin_update_administrator(
    request: Request,
    admin_id: str,
    name: Annotated[str, Form()] = '',
    email: Annotated[str, Form()] = '',
    username: Annotated[str, Form()] = '',
    role: Annotated[str, Form()] = 'subadmin'
):
    try:
        admin_record = await Admin.get(admin_id)  # type: ignore
        if not admin_record:
            return JSONResponse(
                {'success': False, 'message': 'Administrator not found'},
                status_code=status.HTTP_404_NOT_FOUND
            )

        if not name or not email or not username:
            return JSONResponse(
                {'success': False, 'message': 'Name, email and username are required'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        existing = await Admin.get_by_username(username)
        if existing and str(existing.id) != str(admin_id):
            return JSONResponse(
                {'success': False, 'message': 'Username already in use'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        await admin_record.update({'name': name, 'email': email, 'username': username, 'role': role})
        return JSONResponse({'success': True, 'message': 'Administrator updated successfully'})
    except Exception as e:
        logging.exception('Error updating administrator')
        return JSONResponse(
            {'success': False, 'message': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@admin.post('/administrators/{admin_id}/reset-password')
@admin.post('/administrators/{admin_id}/reset-password/')
async def admin_reset_administrator_password(
    request: Request,
    admin_id: str,
    new_password: Annotated[str, Form()] = '',
    confirm_password: Annotated[str, Form()] = ''
):
    try:
        admin_record = await Admin.get(admin_id)  # type: ignore
        if not admin_record:
            return JSONResponse(
                {'success': False, 'message': 'Administrator not found'},
                status_code=status.HTTP_404_NOT_FOUND
            )

        if not new_password:
            return JSONResponse(
                {'success': False, 'message': 'Password is required'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return JSONResponse(
                {'success': False, 'message': 'Passwords do not match'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return JSONResponse(
                {'success': False, 'message': 'Password must be at least 6 characters'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        await admin_record.reset_password(new_password)
        return JSONResponse({'success': True, 'message': 'Password reset successfully'})
    except Exception as e:
        logging.exception('Error resetting administrator password')
        return JSONResponse(
            {'success': False, 'message': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@admin.post('/administrators/{admin_id}/delete')
@admin.post('/administrators/{admin_id}/delete/')
async def admin_delete_administrator(request: Request, admin_id: str):
    try:
        current_admin_id = request.session.get('admin_id')
        if str(current_admin_id) == str(admin_id):
            return JSONResponse(
                {'success': False, 'message': 'You cannot delete your own account'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        admin_record = await Admin.get(admin_id)  # type: ignore
        if not admin_record:
            return JSONResponse(
                {'success': False, 'message': 'Administrator not found'},
                status_code=status.HTTP_404_NOT_FOUND
            )

        await Admin.delete_many({'id': str(admin_id)})
        return JSONResponse({'success': True, 'message': 'Administrator deleted successfully'})
    except Exception as e:
        logging.exception('Error deleting administrator')
        return JSONResponse(
            {'success': False, 'message': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@admin.get('/projects')
@admin.get('/projects/')
async def admin_list_projects(request: Request, view: Optional[str] = None):
    projects = await Project.all()
    
    if view:
        request.session['view'] = view
    elif 'view' not in request.session.keys():
        request.session['view'] = 'grid'
        
    return templates.TemplateResponse('admin/projects/index.html', context={
            'request': request, 'page': 'projects', 'projects': projects,
            'user': {}, 'icons': LANGUAGE_TO_ICONS})

@admin.get('/projects/{project_id}')
@admin.get('/projects/{project_id}/')
async def admin_get_project(request: Request, project_id):
    old_curdir = os.curdir
    
    project = await Project.get(project_id)
    if not project:
        flash(request, 'Project does not exist', 'danger')
        return RedirectResponse(request.url_for('admin_list_projects'))
    
    os.chdir(Path(PROJECTS_DIR, str(project.id)))
    if not os.path.isfile('.env'):
        open('.env', 'w').close()

    environs = dotenv_values('.env')

    runit = RunIt(**RunIt.load_config())

    funcs = []
    for func in runit.get_functions():
        funcs.append({'name': func, 'link': f"/{project_id}/{func}/"})
    
    os.chdir(old_curdir)

    if project:
        project_data = project.json()
        return templates.TemplateResponse('admin/projects/details.html', context={
            'request': request, 'page': 'projects', 'project': project_data,
            'environs': environs, 'funcs': funcs, 'icons': LANGUAGE_TO_ICONS})
    else:
        flash(request, 'Project does not exist', 'danger')
        return RedirectResponse(request.url_for('admin_list_projects'))

@admin.post('/projects')
@admin.post('/projects/')
async def admin_create_project(
    request: Request, name: Annotated[str, Form()], 
    user_id: Annotated[str, Form()], 
    language: Annotated[str, Form()], 
    description: Annotated[Optional[str], Form()] = None,
    database: Annotated[Optional[str], Form()] = None):
    
    user_id = request.session['user_id']
    user = await User.get(user_id)  # type: ignore
    
    if name and language and user:
        config = {}
        config['name'] = name
        config['language'] = language
        config['runtime'] = LANGUAGE_TO_RUNTIME[language]
        config['description'] = description
        config['author'] = {}
        config['author']['name'] = user.name
        config['author']['email'] = user.email
        
        project = Project(user_id, **config)
        await project.save()
        project_id = str(project.id)
        
        homepage = f"{request.base_url}{project_id}/"
        await project.update({'homepage': homepage})

        config['_id'] = project_id
        config['homepage'] = homepage
        
        os.chdir(PROJECTS_DIR)
        
        config['name'] = project_id
        new_runit = RunIt(**config)
        
        new_runit._id = project_id
        new_runit.name = name
        
        os.chdir(Path(PROJECTS_DIR, project_id))
        new_runit.update_config()
        
        if (database):
            collection_name = f"{name}_db_{user_id}_{project_id}"
            new_db = Database(name+'_db', collection_name, user_id, project_id)
            await new_db.save()
        
        flash(request, 'Project Created Successfully.', category='success')
    else:
        flash(request, 'Missing required fields.', category='danger')
    
    user_id = request.session['user_id']
    projects = await Project.get_by_user(user_id)
    
    return templates.TemplateResponse('projects/index.html', context={
        'request': request, 'page': 'projects', 'projects': projects, 
        'icons': LANGUAGE_TO_ICONS})

@admin.get('/projects/delete/{project_id}')
@admin.get('/projects/delete/{project_id}/')
async def admin_delete_project(request: Request, project_id, background_task: BackgroundTasks):
    try:
        user_id = request.session['user_id']
        project = await Project.get(project_id)
        
        if project:
            await Project.delete_many({'id': project_id, 'user_id': user_id})
            background_task.add_task(shutil.rmtree, Path(PROJECTS_DIR, str(project.id)))
            flash(request, 'Project deleted successfully', category='success')
        else:
            flash(request, 'Project was not found. Operation not successful.', category='danger')
        return RedirectResponse(request.url_for(ADMIN_PROJECTS_INDEX))
    except Exception:
        flash(request, 'Project deleted successfully', category='success')
        return RedirectResponse(request.url_for(ADMIN_PROJECTS_INDEX))


@admin.get('/databases')
@admin.get('/databases/')
async def admin_list_databases(request: Request, view: Optional[str] = None):
    global EXTENSIONS
    global LANGUAGE_TO_ICONS

    view = view if view else 'grid'
    databases = await Database.all()
    for db in databases:
        Collection.TABLE_NAME = db.collection_name
        count = await DBMS.Database.count(Collection.TABLE_NAME, {})
        if count and DBMS.Database.dbms == 'mongodb':
            stats = await DBMS.Database.db.command('collstats', db.collection_name)  # type: ignore
            if stats:
                db.stats = {'size': int(stats['storageSize'])/1024, 'count': stats['count']}
        
    projects = await Project.all()
    
    return templates.TemplateResponse('admin/databases/index.html', context={
            'request': request, 'page': 'databases', 'databases': databases,
            'projects': projects, 'icons': LANGUAGE_TO_ICONS})

@admin.get('/databases/{database_id}')
@admin.get('/databases/{database_id}/')
async def admin_get_database(request: Request, database_id: str):
    database = await Database.get(database_id)
    
    if database:
        Collection.TABLE_NAME = database.collection_name            # type: ignore
        collections = await Collection.find({})
        
        result = []
        for col in collections:
            result.append(col.json())
        
        schema_names_to_input_types = {
            'str': 'text',
            'text': 'textarea',
            'int': 'number',
            'float': 'number',
            'bool': 'checkbox'
        }
        
        return templates.TemplateResponse('admin/databases/details.html', context={
                'request': request, 'page':'databases',
                'database': database.json(), 'collections': result,
                'inputTypes': schema_names_to_input_types})
    else:
        flash(request, 'Database does not exist', 'danger')
        return RedirectResponse(request.url_for(ADMIN_DATABASE_INDEX))
    
@admin.post('/databases')
async def admin_create_database(
    request: Request,
    name: Annotated[str, Form()],
    project_id: Annotated[str, Form()]
):

    project = await Project.get(project_id)
    
    if name and project_id and project:
        collection_name = f"{name}_{project.user_id}_{project_id}"  # type: ignore
        data = {'name': name, 'collection_name': collection_name,
                'project_id': project_id, 'user_id': project.user_id}  # type: ignore

        new_db = Database(**data)
        await new_db.save()
                
        flash(request, 'Database Created Successfully.', category='success')
    else:
        flash(request, 'Missing required fields.', category='danger')
    return RedirectResponse(request.url_for(ADMIN_DATABASE_INDEX), status_code=status.HTTP_303_SEE_OTHER)

@admin.post('/schema/{database_id}/')
async def admin_database_schema(request: Request, database_id: str):
    try:
        data = await request.form()
        await Database.update_one({'id': database_id}, {'schema': dict(data)})
        
        flash(request, 'Schema updated successfully', category='success')
    except Exception as e:
        logging.error(str(e))
        flash(request, 'Error updating database schema', category='danger')
    return RedirectResponse(request.url_for('admin_get_database', database_id=database_id), status_code=status.HTTP_303_SEE_OTHER)

@admin.patch('/databases/{database_id}')
@admin.patch('/databases/{database_id}/')
async def admin_update_database(request: Request, database_id: str):
    return templates.TemplateResponse('admin/databases/index.html', {
        'request': request, 'page': 'databases', 'databases': []
    })

@admin.get('/databases/delete/{database_id}/')
async def admin_delete_database(request: Request, database_id: str):
    db = await Database.get(database_id)
    if db:
        result = await Database.delete_many({'id': database_id})
        flash(request, 'Database deleted successfully', category='success')
    else:
        flash(request, 'Database was not found. Operation not successful.', category='danger')
    return RedirectResponse(request.url_for(ADMIN_DATABASE_INDEX), status_code=status.HTTP_303_SEE_OTHER)

@admin.get('/profile/')
async def admin_profile(request: Request):
    user_id = request.session['admin_id']
    user = await Admin.get(user_id)
    
    if not user:
        flash(request, "User does not exist", "danger")
        return RedirectResponse(request.url_for('admin_dashboard'), status_code=status.HTTP_303_SEE_OTHER)
    
    user_json = await user.json()
    return templates.TemplateResponse('admin/profile.html', context={
        'request': request, 'page': 'profile', 'user': user_json})


@admin.post('/profile/')
async def admin_update_profile(
    request: Request,
    name: Annotated[str, Form()] = '',
    username: Annotated[str, Form()] = '',
    email: Annotated[str, Form()] = ''
):
    try:
        admin_id = request.session.get('admin_id')
        if not admin_id:
            return JSONResponse(
                {'success': False, 'message': 'Not authenticated'},
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        admin_record = await Admin.get(admin_id)  # type: ignore
        if not admin_record:
            return JSONResponse(
                {'success': False, 'message': 'Administrator not found'},
                status_code=status.HTTP_404_NOT_FOUND
            )

        if not name or not username or not email:
            return JSONResponse(
                {'success': False, 'message': 'Name, username and email are required'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        existing = await Admin.get_by_username(username)
        if existing and str(existing.id) != str(admin_id):
            return JSONResponse(
                {'success': False, 'message': 'Username already in use'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        await admin_record.update({'name': name, 'username': username, 'email': email})
        return JSONResponse({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        logging.exception('Error updating profile')
        return JSONResponse(
            {'success': False, 'message': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@admin.post('/profile/change-password')
@admin.post('/profile/change-password/')
async def admin_change_password(
    request: Request,
    current_password: Annotated[str, Form()] = '',
    new_password: Annotated[str, Form()] = '',
    confirm_password: Annotated[str, Form()] = ''
):
    try:
        admin_id = request.session.get('admin_id')
        if not admin_id:
            return JSONResponse(
                {'success': False, 'message': 'Not authenticated'},
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        admin_record = await Admin.get(admin_id)  # type: ignore
        if not admin_record:
            return JSONResponse(
                {'success': False, 'message': 'Administrator not found'},
                status_code=status.HTTP_404_NOT_FOUND
            )

        if not Utils.check_hashed_password(current_password, admin_record.password):
            return JSONResponse(
                {'success': False, 'message': 'Current password is incorrect'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if not new_password:
            return JSONResponse(
                {'success': False, 'message': 'New password is required'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return JSONResponse(
                {'success': False, 'message': 'Passwords do not match'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return JSONResponse(
                {'success': False, 'message': 'Password must be at least 6 characters'},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        await admin_record.reset_password(new_password)
        return JSONResponse({'success': True, 'message': 'Password changed successfully'})
    except Exception as e:
        logging.exception('Error changing password')
        return JSONResponse(
            {'success': False, 'message': str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@admin.get('/logout/')
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(request.url_for(ADMIN_LOGIN_PAGE), status_code=status.HTTP_303_SEE_OTHER)


# --- Schedules ---
ADMIN_SCHEDULES_INDEX = 'admin_list_schedules'

@admin.get('/schedules/')
async def admin_list_schedules(request: Request, view: Optional[str] = None):
    schedules = await Schedule.all()
    schedules_data = []
    
    for sched in schedules:
        sched_data = sched.json()
        project = await Project.get(sched.project_id)
        user = await User.get(sched.user_id)
        sched_data['project'] = project.json() if project else None
        sched_data['user'] = user.json() if user else None
        schedules_data.append(sched_data)
    
    if view:
        request.session['schedules_view'] = view
    elif 'schedules_view' not in request.session.keys():
        request.session['schedules_view'] = 'grid'
    
    projects = await Project.all()
    projects_data = [p.json() for p in projects]
    
    return templates.TemplateResponse('admin/schedules/index.html', context={
        'request': request, 'page': 'schedules', 'schedules': schedules_data,
        'projects': projects_data, 'icons': LANGUAGE_TO_ICONS})


@admin.get('/schedules/{schedule_id}')
@admin.get('/schedules/{schedule_id}/')
async def admin_get_schedule(request: Request, schedule_id: str):
    sched = await Schedule.get(schedule_id)
    if not sched:
        flash(request, 'Schedule not found', 'danger')
        return RedirectResponse(request.url_for(ADMIN_SCHEDULES_INDEX))
    
    sched_data = sched.json()
    project = await Project.get(sched.project_id)
    user = await User.get(sched.user_id)
    sched_data['project'] = project.json() if project else None
    sched_data['user'] = user.json() if user else None
    
    logs = await ScheduleLog.get_by_schedule(schedule_id, limit=50)
    logs_data = [log.json() for log in logs]
    
    projects = await Project.all()
    projects_data = [p.json() for p in projects]
    
    return templates.TemplateResponse('admin/schedules/details.html', context={
        'request': request, 'page': 'schedules', 'schedule': sched_data,
        'projects': projects_data, 'logs': logs_data, 'icons': LANGUAGE_TO_ICONS})


@admin.post('/schedules/{schedule_id}')
@admin.post('/schedules/{schedule_id}/')
async def admin_update_schedule(
    request: Request,
    schedule_id: str,
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
        await schedule_service.remove_job(schedule_id)
    
    return JSONResponse({'success': True, 'message': 'Schedule updated successfully'})


@admin.post('/schedules/{schedule_id}/toggle')
@admin.post('/schedules/{schedule_id}/toggle/')
async def admin_toggle_schedule(request: Request, schedule_id: str):
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


@admin.post('/schedules/{schedule_id}/delete')
@admin.post('/schedules/{schedule_id}/delete/')
async def admin_delete_schedule(request: Request, schedule_id: str):
    sched = await Schedule.get(schedule_id)
    if not sched:
        return JSONResponse(
            {'success': False, 'message': 'Schedule not found'},
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    from ..services.scheduler import schedule_service
    await schedule_service.remove_job(schedule_id)
    await Schedule.delete_many({'id': schedule_id})
    
    return JSONResponse({'success': True, 'message': 'Schedule deleted successfully'})

