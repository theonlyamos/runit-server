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
from ..models import Function
from ..models import Database
from ..models import Collection

from ..constants import (
    PROJECTS_DIR,
    EXTENSIONS,
    LANGUAGE_TO_ICONS,
    LANGUAGE_TO_RUNTIME
)

ADMIN_LOGIN_PAGE = 'admin_login_page'
ADMIN_DATABASE_INDEX = 'admin_list_databases'
ADMIN_PROJECTS_INDEX = 'admin_list_projects'

from runit import RunIt

admin = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin_session)]
)

@admin.get('/')
async def admin_dashboard(request: Request):
    admin = Admin.get(request.session['admin_id'])
    return templates.TemplateResponse('admin/index.html', context={
        'request': request, 'page': 'home', 'admin': admin})

@admin.get('/users/')
async def admin_list_users(request: Request, view: Optional[str] = None):
    users = User.all()
    
    if view:
        request.session['view'] = view
    elif 'view' not in request.session.keys():
        request.session['view'] = 'grid'

    return templates.TemplateResponse('admin/users/index.html', context={
        'request': request, 'page': 'users', 'users': users, 
        'icons': LANGUAGE_TO_ICONS})

@admin.get('/users/{user_id}')
@admin.get('/users/{user_id}/')
async def admin_get_user(request: Request, user_id: str):
    try:
        user: User = User.get(user_id) # type: ignore
        if not User:
            raise Exception('User not found')
        
        projects = Project.get_by_user(user.id)
        
        return templates.TemplateResponse('admin/users/details.html', context={
            'request': request, 'page': 'users', 'user': user.json(),
            'projects': projects, 'icons': LANGUAGE_TO_ICONS})
    except Exception as e:
        flash(request, str(e), 'danger')
        return RedirectResponse(request.url_for('admin_list_users'))

@admin.get('/projects')
@admin.get('/projects/')
def admin_list_projects(request: Request, view: Optional[str] = None):
    projects = Project.all()
    
    if view:
        request.session['view'] = view
    elif 'view' not in request.session.keys():
        request.session['view'] = 'grid'
        
    return templates.TemplateResponse('admin/projects/index.html', context={
            'request': request, 'page': 'projects', 'projects': projects,
            'icons': LANGUAGE_TO_ICONS})

@admin.get('/projects/{project_id}')
@admin.get('/projects/{project_id}/')
async def admin_get_project(request: Request, project_id):
    old_curdir = os.curdir
    
    project = Project.get(project_id)
    if not project:
        flash(request, 'Project does not exist', 'danger')
        return RedirectResponse(request.url_for('admin_list_projects'))
    
    os.chdir(Path(PROJECTS_DIR, project.id))
    if not os.path.isfile('.env'):
        open('.env', 'w').close()

    environs = dotenv_values('.env')

    runit = RunIt(**RunIt.load_config())

    funcs = []
    for func in runit.get_functions():
        funcs.append({'name': func, 'link': f"/{project_id}/{func}/"})
    
    os.chdir(old_curdir)

    if project:
        return templates.TemplateResponse('admin/projects/details.html', context={
            'request': request, 'page': 'projects', 'project': project.json(),
            'environs': environs, 'funcs': funcs})
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
    user: User= User.get(user_id) # type: ignore
    
    if name and language:
        # name = RunIt.set_project_name(args.name)
        # if RunIt.exists(name):
        # flash(request, f'{name} project already Exists', category='danger')
        
        config = {}
        config['name'] = name
        config['language'] = language
        config['runtime'] = LANGUAGE_TO_RUNTIME[language]
        config['description'] = description
        config['author'] = {}
        config['author']['name'] = user.name
        config['author']['email'] = user.email
        
        project = Project(user_id, **config)
        project_id = project.save().inserted_id # type: ignore
        project_id = str(project_id)
        project.id = project_id
        
        homepage = f"{request.base_url}{project_id}/"
        project.update({'homepage': homepage})

        config['_id'] = project_id
        config['homepage'] = homepage
        
        os.chdir(PROJECTS_DIR)
        
        config['name'] = project_id
        new_runit = RunIt(**config)
        
        new_runit._id = project_id
        new_runit.name = name
        
        os.chdir(Path(PROJECTS_DIR, project_id))
        new_runit.update_config()
        
        # os.chdir(RUNIT_HOMEDIR)
        
        if (database):
            # Create database for project
            Database(name+'_db', user_id, project_id).save()
        
        flash(request, 'Project Created Successfully.', category='success')
    else:
        flash(request, 'Missing required fields.', category='danger')
    
    user_id = request.session['user_id']
    projects = Project.get_by_user(user_id)
    
    return templates.TemplateResponse('projects/index.html', context={
        'request': request, 'page': 'projects', 'projects': projects, 
        'icons': LANGUAGE_TO_ICONS})

@admin.get('/projects/delete/{project_id}')
@admin.get('/projects/delete/{project_id}/')
async def admin_delete_project(request: Request, project_id, background_task: BackgroundTasks):
    try:
        user_id = request.session['user_id']
        project = Project.get(project_id)
        
        if project:
            Project.remove({'_id': project_id, 'user_id': user_id})
            background_task.add_task(shutil.rmtree, Path(PROJECTS_DIR, project.id))
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
    databases = Database.all()
    for db in databases:
        Collection.TABLE_NAME = db.collection_name
        if Collection.count():
            stats = DBMS.Database.db.command('collstats', db.collection_name) # type: ignore
            if stats:
                db.stats = {'size': int(stats['storageSize'])/1024, 'count': stats['count']}
        
    projects = Project.all()
    
    return templates.TemplateResponse('admin/databases/index.html', context={
            'request': request, 'page': 'databases', 'databases': databases,
            'projects': projects, 'icons': LANGUAGE_TO_ICONS})

@admin.get('/databases/{database_id}')
@admin.get('/databases/{database_id}/')
async def admin_get_database(request: Request, database_id: str):
    database = Database.get(database_id)
    
    if database:
        Collection.TABLE_NAME = database.collection_name
        collections = Collection.find({})
        
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

    project = Project.get(project_id)
    
    if name and project_id:
        collection_name = f"{name}_{project.user_id}_{project_id}" # type: ignore
        data = {'name': name, 'collection_name': collection_name,
                'project_id': project_id,'user_id': project.user_id} # type: ignore

        new_db = Database(**data)
        results = new_db.save().inserted_id # type: ignore
                
        flash(request, 'Database Created Successfully.', category='success')
    else:
        flash(request, 'Missing required fields.', category='danger')
    return RedirectResponse(request.url_for(ADMIN_DATABASE_INDEX), status_code=status.HTTP_303_SEE_OTHER)

@admin.post('/schema/{database_id}/')
async def admin_database_schema(request: Request, database_id: str):
    try:
        data = await request.form()
        Database.update({'id': database_id}, {'schema': data})
        
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
    db = Database.get(database_id)
    if db:
        result = Database.remove({'_id': database_id})
        flash(request, 'Database deleted successfully', category='success')
    else:
        flash(request, 'Database was not found. Operation not successful.', category='danger')
    return RedirectResponse(request.url_for(ADMIN_DATABASE_INDEX), status_code=status.HTTP_303_SEE_OTHER)

@admin.get('/profile/')
async def admin_profile(request: Request):
    return templates.TemplateResponse('admin/profile.html', context={
        'request': request, 'page': 'profile'})

@admin.get('/logout/')
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse(request.url_for(ADMIN_LOGIN_PAGE), status_code=status.HTTP_303_SEE_OTHER)

