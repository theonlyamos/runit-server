
import logging
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Annotated, Optional
import aiofiles

from fastapi.responses import JSONResponse
from fastapi import APIRouter, BackgroundTasks,  Request, \
    Depends, status
from dotenv import load_dotenv, dotenv_values
from pydantic import BaseModel

from ...common import get_current_user
from ...models import Database
from ...models import Project
from ...models import User

from runit import RunIt
from ...constants import (
    PROJECTS_DIR,
    LANGUAGE_TO_RUNTIME,
    Language
)

PROJECT_404_ERROR = 'Project does not exist'
    
class ProjectData(BaseModel):
    name: str
    language: Language
    description: Optional[str] = None
    database: Optional[str] = None

load_dotenv()

projects_api = APIRouter(
    prefix="/projects",
    tags=["projects api"],
    dependencies=[Depends(get_current_user)],
)

@projects_api.get('/')
async def api_list_user_projects(user: Annotated[User, Depends(get_current_user)]):
    
    projects = Project.get_by_user(user.id) # type: ignore
    json_projects = []
    for project in projects:
        json_projects.append(project.json())
    
    return JSONResponse(json_projects)

@projects_api.post('/')
async def api_create_user_project(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    project_data: ProjectData
):
    
    user = User.get(user.id) # type: ignore
    
    response = {
        'status': 'success', 
        'message': 'Project created successfully'
    }
    
    try:
        # name = RunIt.set_project_name(args.name)
        # if RunIt.exists(name):
        # flash(request, f'{name} project already Exists', category='danger')
        
        config = {}
        config['name'] = project_data.name
        config['language'] = project_data.language.value
        config['runtime'] = LANGUAGE_TO_RUNTIME[project_data.language.value]
        config['description'] = project_data.description
        config['author'] = {}
        config['author']['name'] = user.name
        config['author']['email'] = user.email
        
        project = Project(user.id, **config)
        project_id = project.save().inserted_id # type: ignore
        project_id = str(project_id)
        project.id = project_id
        
        homepage = f"{request.base_url}{project_id}/"
        Project.update({'id': project_id}, {'homepage': homepage})

        config['_id'] = project_id
        config['homepage'] = homepage
        
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
            Database(
                project_data.name+'_db',
                user.id,
                project_id
            ).save()
        response['project'] = Project.get(project_id).json() # type: ignore
    except Exception as e:
        logging.info(str(e))
        response['status'] = 'error'
        response['message'] = 'Error creating project'
    
    return JSONResponse(
        response,
        status_code=status.HTTP_201_CREATED if response['status'] == 'success' else status.HTTP_204_NO_CONTENT
    )

@projects_api.get('/{project_id}')
async def api_get_project_details(
    user: Annotated[User, Depends(get_current_user)],
    project_id: str
):
    old_curdir = os.curdir
    
    response = {}
    if not Path(PROJECTS_DIR).joinpath(project_id).resolve().exists():
        return JSONResponse(response)
    
    os.chdir(Path(PROJECTS_DIR, project_id).resolve())
    if not Path('.env').is_file():
        async with aiofiles.open('.env', 'w') as file:
            await file.close()

    environs = dotenv_values('.env')
    
    runit = RunIt(**RunIt.load_config())

    funcs = []
    for func in runit.get_functions():
        funcs.append(func)
    
    os.chdir(old_curdir)
    project = Project.find({
        'id': project_id,
        'user_id': user.id
    })

    if len(project):
        project = project[0].json()
        del project['author']
        project['functions'] = len(funcs)
        project['endpoints'] = []
        for func in funcs:
            project['endpoints'].append(f"{project['homepage']}{func}")
        response = project
    
    return JSONResponse(response)

@projects_api.get('/delete/{project_id}')
async def api_delete_user_project(
    user: Annotated[User, Depends(get_current_user)],
    project_id, 
    background_task: BackgroundTasks):
    response = {
            'status': 'success',
            'message': 'Project deleted successfully'
        }
    try:
        user_id = user.id
        project = Project.find({
            'id': project_id,
            'user_id': user_id
        })
        
        if len(project):
            project = project[0]
            Project.remove({'_id': project_id, 'user_id': user_id})
            background_task.add_task(shutil.rmtree, Path(PROJECTS_DIR, project_id).resolve())
            
        else:
            response['status'] = 'error'
            response['message'] = 'Project was not found. Operation not successful'

    except Exception:
        response['status'] = 'error'
        response['message'] = 'Error during operation'
    finally:
        return JSONResponse(response)

@projects_api.patch('/')
async def api_update_user_project(request: Request):
    # user_id = request.session['user_id']
    return JSONResponse({})