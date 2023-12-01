
import json
import logging
import os
import shutil
from time import sleep
from pathlib import Path
from datetime import datetime
from typing import Annotated, Optional, Dict
import aiofiles

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request, \
    Depends, status, UploadFile
from dotenv import load_dotenv, dotenv_values, set_key

from ..core import flash, templates
from ..common import get_session, get_session_user
from ..models import Database
from ..models import Project
from ..models import User

from runit import RunIt
from ..constants import (
    RUNIT_HOMEDIR,
    PROJECTS_DIR,
    LANGUAGE_TO_ICONS,
    LANGUAGE_TO_RUNTIME
)

PROJECT_INDEX_URL_NAME = 'list_user_projects'
PROJECT_404_ERROR = 'Project does not exist'

load_dotenv()

project = APIRouter(
    prefix="/projects",
    tags=["projects"],
    dependencies=[Depends(get_session)]
)

@project.get('/')
async def list_user_projects(request: Request, view: Optional[str] = None):
    user_id = request.session['user_id']
    
    if view:
        request.session['view'] = view
    elif 'view' not in request.session.keys():
        request.session['view'] = 'grid'
        
    projects = Project.get_by_user(user_id)
    
    return templates.TemplateResponse('projects/index.html', context={
        'request': request, 'page': 'projects', 'projects': projects, 
        'icons': LANGUAGE_TO_ICONS})

@project.post('/')
async def create_user_project(
    request: Request, name: Annotated[str, Form()], 
    language: Annotated[str, Form()], 
    description: Annotated[Optional[str], Form()] = None,
    database: Annotated[Optional[str], Form()] = None):
    
    user_id = request.session['user_id']
    user = User.get(user_id)
    
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
        project_id = project.save().inserted_id
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

@project.get('/{project_id}')
@project.get('/{project_id}/')
async def user_project_details(request: Request, project_id: str):
    old_curdir = os.curdir
    
    if not Path(PROJECTS_DIR).joinpath(project_id).resolve().exists():
        flash(request, PROJECT_404_ERROR, 'danger')
        return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))
    
    os.chdir(Path(PROJECTS_DIR).joinpath(project_id).resolve())
    if not Path('.env').is_file():
        async with aiofiles.open('.env', 'w') as file:
            await file.close()

    environs = dotenv_values('.env')
    
    runit = RunIt(**RunIt.load_config())

    funcs = []
    for func in runit.get_functions():
        funcs.append({'name': func})
    
    os.chdir(old_curdir)
    project = Project.get(project_id)
    project = project.json()
    del project['author']
    project['functions'] = len(funcs)
    if project:
        return templates.TemplateResponse('projects/details.html', context={
            'request': request, 'page': 'projects','project': project, 
            'environs': environs, 'funcs': funcs})
    else:
        flash(request, PROJECT_404_ERROR, 'danger')
        return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))

@project.get('/reinstall/{project_id}')
@project.get('/reinstall/{project_id}/')
async def reinstall_project_dependencies(request: Request, project_id: str, background_task: BackgroundTasks):
    try:
        old_curdir = os.curdir
        
        if not Path(PROJECTS_DIR).joinpath(project_id).resolve().exists():
            flash(request, PROJECT_404_ERROR, 'danger')
            return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))

        os.chdir(Path(PROJECTS_DIR, project_id).resolve())
        runit = RunIt(**RunIt.load_config())
        background_task.add_task(runit.install_dependency_packages)
        
        os.chdir(old_curdir)
        flash(request, "Dependencies installation has started", "success")
    except Exception as e:
        logging.error(str(e))
        flash(request, "Error installing dependencies", "danger")
    finally:
        return RedirectResponse(request.url_for('user_project_details', project_id=project_id))

@project.get('/delete/{project_id}')
@project.get('/delete/{project_id}/')
async def delete_user_project(request: Request, project_id, background_task: BackgroundTasks):
    try:
        user_id = request.session['user_id']
        project = Project.get(project_id)
        
        if project:
            Project.remove({'_id': project_id, 'user_id': user_id})
            background_task.add_task(shutil.rmtree, Path(PROJECTS_DIR, project_id))
            flash(request, 'Project deleted successfully', category='success')
        else:
            flash(request, 'Project was not found. Operation not successful.', category='danger')
        return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))
    except Exception:
        flash(request, 'Project deleted successfully', category='success')
        return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))

@project.post('environ/{project_id}/')
async def user_project_environ(request: Request, project_id):
    env_file = Path(PROJECTS_DIR, project_id, '.env').resolve()
    async with aiofiles.open(env_file, 'w') as file:
        await file.close()
    
    for key, value in request.form.items():
        set_key(env_file, key, value)

    # project = Project.get(project_id)
    flash(request, 'Environment variables updated successfully', category='success')
    return RedirectResponse(request.url_for('user_project_details', project_id=project_id))

@project.patch('/')
async def update_user_project(request: Request):
    # user_id = request.session['user_id']
    return templates.TemplateResponse('projects/index.html', {
        'request': request, 'page':'projects', 'projects':[]})