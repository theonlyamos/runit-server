
import json
import logging
import os
import shutil
from time import sleep
from pathlib import Path
from datetime import datetime
from typing import Annotated, Optional, Dict

import aiofiles
from github import Github, Auth

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request, \
    Depends, status, UploadFile
from dotenv import load_dotenv, dotenv_values, set_key

from ..core import flash, templates
from ..common import get_session
from ..models import Database
from ..models import Project
from ..models import User
from ..models import ProjectData

from runit import RunIt
from ..constants import (
    RUNIT_HOMEDIR,
    PROJECTS_DIR,
    LANGUAGE_TO_ICONS,
    LANGUAGE_TO_RUNTIME,
    GITHUB_APP_CLIENT_ID
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
    user = User.get(user_id)
    user = user.json() if user else None
    
    if view:
        request.session['view'] = view
    elif 'view' not in request.session.keys():
        request.session['view'] = 'grid'
        
    projects = Project.get_by_user(user_id)
    
    return templates.TemplateResponse('projects/index.html', context={
        'request': request, 'page': 'projects', 'projects': projects, 
        'user': user, 'git_client_id': GITHUB_APP_CLIENT_ID, 
        'repos': {}, 'icons': LANGUAGE_TO_ICONS})

@project.post('/')
async def create_user_project(
    request: Request, 
    project_data: ProjectData,
    background_task: BackgroundTasks):
    response = {
        'status': 'success',
        'message': 'Project created successfully'
    }

    user_id = request.session['user_id']
    user = User.get(user_id)
    
    if not user:
        response['status'] = 'error'
        response['message'] = 'User does not exist'
        logging.error(f'User {user_id} does not exist')
        return JSONResponse(response)
    
    if project_data.name and project_data.language:
        # name = RunIt.set_project_name(args.name)
        # if RunIt.exists(name):
        # flash(request, f'{name} project already Exists', category='danger')
        
        config = {}
        config['name'] = project_data.name
        config['language'] = project_data.language
        config['runtime'] = LANGUAGE_TO_RUNTIME[project_data.language.value]
        config['description'] = project_data.description
        config['author'] = {}
        config['author']['name'] = user.name            # type: ignore
        config['author']['email'] = user.email          # type: ignore
        if project_data.github_repo and project_data.github_repo_branch:
            config['github_repo'] = project_data.github_repo
            config['github_repo_branch'] = project_data.github_repo_branch
        
        project = Project(user_id, **config)
        project_id = project.save().inserted_id     # type: ignore
        project_id = str(project_id)
        project.id = project_id
        
        homepage = f"{request.base_url}{project_id}/"
        project.update({'homepage': homepage})

        config['_id'] = project_id
        config['homepage'] = homepage
        
        if project_data.github_repo and project_data.github_repo_branch:
            Path(PROJECTS_DIR, project_id).resolve().mkdir()
            os.chdir(Path(PROJECTS_DIR, project_id).resolve())
            
            EVENTS = ["push"]
            HOOK_URL = "https://smee.io/gYpSAHqmso0R6aZ"
            HAS_HOOK = False
            config = {
                # "url": f"{request.base_url}/github/webhook",
                "url": HOOK_URL,
                "content_type": "json"
            }
            auth = Auth.Token(user.gat) # type: ignore
            g = Github(auth=auth)
            repo = g.get_user().get_repo(f"{project_data.github_repo}")
            
            for hook in repo.get_hooks():
                if hook.raw_data['config']['url'] == HOOK_URL:
                    HAS_HOOK = True
                    break
                
            if not HAS_HOOK:
                repo.create_hook("web", config, EVENTS, active=True)
            
            contents = repo.get_contents("")
            while contents:
                file_content = contents.pop(0)      # type: ignore
                
                if file_content.type == "dir":
                    Path(PROJECTS_DIR, project_id, file_content.path).resolve().mkdir()
                else:
                    async with aiofiles.open(Path(PROJECTS_DIR, project_id, file_content.path).resolve(), 'wb') as file:
                        await file.write(file_content.decoded_content)
            
            
            runit = RunIt(**RunIt.load_config())
            background_task.add_task(runit.install_dependency_packages)
        else:
            os.chdir(PROJECTS_DIR)
            config['name'] = project_id
            new_runit = RunIt(**config)
            
            new_runit._id = project_id
            new_runit.name = project_data.name
        
            os.chdir(Path(PROJECTS_DIR, project_id))
            new_runit.update_config()
        
        # os.chdir(RUNIT_HOMEDIR)
        
        if (project_data.database):
            # Create database for project
            Database(project_data.name+'_db', user_id, project_id).save()
        
        response['project_id'] = project_id
    else:
        response['status'] = 'error'
        response['message'] = 'Error creating project'
        logging.error(f'Emsg=rror creating project by User {user_id}')
    
    return JSONResponse(response)

@project.get('/{project_id}')
@project.get('/{project_id}/')
async def user_project_details(request: Request, project_id: str):
    old_curdir = os.curdir
    
    project = Project.get(project_id)
    if not project:
        flash(request, PROJECT_404_ERROR, 'danger')
        return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))
    
    elif not Path(PROJECTS_DIR, project.id).resolve().exists():
        flash(request, PROJECT_404_ERROR, 'danger')
        return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))
    
    os.chdir(Path(PROJECTS_DIR, project.id).resolve())
    if not Path('.env').is_file():
        async with aiofiles.open('.env', 'w') as file:
            await file.close()

    environs = dotenv_values('.env')
    
    runit = RunIt(**RunIt.load_config())

    funcs = []
    for func in runit.get_functions():
        funcs.append({'name': func})
    
    os.chdir(old_curdir)

    project = project.json()        # type: ignore
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
        
        project = Project.get(project_id)
        if not project:
            flash(request, PROJECT_404_ERROR, 'danger')
            return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))
        
        if not Path(PROJECTS_DIR, project.id).resolve().exists():
            flash(request, PROJECT_404_ERROR, 'danger')
            return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))

        os.chdir(Path(PROJECTS_DIR, project.id).resolve())
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
            background_task.add_task(shutil.rmtree, Path(PROJECTS_DIR, project.id))
            flash(request, 'Project deleted successfully', category='success')
        else:
            flash(request, 'Project was not found. Operation not successful.', category='danger')
        return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))
    except Exception:
        flash(request, 'Project deleted successfully', category='success')
        return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))

@project.post('environ/{project_id}/')
async def user_project_environ(request: Request, project_id):
    project = Project.get(project_id)
    if not project:
        flash(request, PROJECT_404_ERROR, 'danger')
        return RedirectResponse(request.url_for(PROJECT_INDEX_URL_NAME))
    
    env_file = Path(PROJECTS_DIR, project.id, '.env').resolve()
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