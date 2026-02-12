
import logging
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Annotated, Optional
import aiofiles

from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import APIRouter, BackgroundTasks,  Request, \
    Depends, status, UploadFile
from dotenv import load_dotenv, dotenv_values
from pydantic import BaseModel

from odbms import DBMS

from ...common import get_current_user
from ...models import Database
from ...models import Project
from ...models import User
from ...models import ProjectData
from ...models import Collection

from ...core import flash

from runit import RunIt
from ...constants import (
    DOCKER_TEMPLATES,
    PROJECTS_DIR,
    LANGUAGE_TO_RUNTIME
)

PROJECT_404_ERROR = 'Project does not exist'

load_dotenv()

projects_api = APIRouter(
    prefix="/projects",
    tags=["projects api"],
    dependencies=[Depends(get_current_user)],
)

@projects_api.get('/')
async def api_list_user_projects(user: Annotated[User, Depends(get_current_user)]):
    
    projects = await Project.find_many({'user_id': user.id}) # type: ignore
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
        
        project = Project(str(user.id), **config)
        saved_project = project.save()
        project_id = saved_project
        
        if not project_id:
            response['status'] = 'error'
            response['message'] = 'Error creating project'
        else:
            project_id = str(project_id)
            project.id = project_id
            
            homepage = f"{request.base_url}{project_id}"
            await Project.update_one({'id': project_id}, {'homepage': homepage})

            config['_id'] = project_id
            config['homepage'] = homepage
            
            os.chdir(PROJECTS_DIR)
            
            config['name'] = project_id
            new_runit = RunIt(**config)
            
            new_runit._id = project_id
            new_runit.name = project_data.name
            
            project_folder = Path(PROJECTS_DIR, project_id).resolve()
            # if not project_folder.exists():
            #     project_folder.mkdir()
                
            os.chdir(str(project_folder))
            new_runit.update_config()
            
            # os.chdir(RUNIT_HOMEDIR)
            
            if (project_data.database):
                # Create database for project
                collection_name = f"{project_data.name}_{str(user.id)}_{project_id}"
                database = Database(
                    project_data.name+'_db',
                    collection_name,
                    str(user.id),
                    project_id
                )
                await database.save()
                Collection.TABLE_NAME = collection_name # type: ignore
                Collection.create_table()
            flash(request, 'Project created successfully', category='success')
            response['project'] = Project.get(project_id).json() # type: ignore
    except Exception as e:
        logging.exception(e)
        response['status'] = 'error'
        response['message'] = 'Error creating project'
    finally:
        return JSONResponse(
            response,
            status_code=status.HTTP_201_CREATED if response['status'] == 'success' else status.HTTP_200_OK
        )

@projects_api.post('/publish')
async def api_publish_user_project(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    background_task: BackgroundTasks
):
    '''
    Api for publishing project

    @param project_id Project _id
    @param function Function Name
    @return Projects: dict Get all projects
    '''

    try:
        form_data = await request.form()
        data = dict(form_data)
        file = data.pop('file', None)
        if file is None:
            return JSONResponse({'status': 'error', 'message': 'No project file provided.'}, status_code=400)

        result = {'status': 'success'}
        raw_project_id = str(data.get('_id', '')).strip().lower()

        if 'private' in data and isinstance(data['private'], str):
            data['private'] = data['private'].strip().lower() in ('1', 'true', 'yes', 'on')

        if raw_project_id in ('', 'none', 'null', 'undefined'):
            data.pop('_id', None)
            project = Project(user_id=user.id, **data)      # type: ignore

            saved_project = await project.save()
            if not saved_project.id:
                return JSONResponse({'status': 'error', 'message': 'Unable to create project record.'}, status_code=500)
            project_id = str(saved_project.id)
            project.id = project_id
            homepage = f"{request.base_url}{project_id}"
            await Project.update_one({'id': project_id}, {'homepage': homepage})
            result['project_id'] = project_id
        else:
            project_id = str(data['_id']).strip()
            project = await Project.get(str(data['_id']))
            if project:
                del data['_id']
                await Project.update_one({'id': project_id}, data)

        PROJECT_PATH = Path(PROJECTS_DIR, project_id).resolve()
        if not PROJECT_PATH.exists():
            os.mkdir(PROJECT_PATH)
            
        filepath = Path(PROJECT_PATH, file.filename)                                 # type: ignore
        contents = await file.read()                                                 # type: ignore
        async with aiofiles.open(filepath, 'wb') as f:
            await f.write(contents)
        await file.close()                                                           # type: ignore

        RunIt.extract_project(filepath)
        os.chdir(PROJECT_PATH)

        runit = RunIt(**RunIt.load_config())
        
        if RunIt.DOCKER:
            docker_file = f"{runit.runtime}.dockerfile"
            full_docker_filepath = f"{os.path.join(DOCKER_TEMPLATES, docker_file)}"
            print(f'[~] {full_docker_filepath}')
            project_docker_file = os.path.join(PROJECT_PATH, 'Dockerfile')
            
            if not os.path.exists(project_docker_file):
                with open(full_docker_filepath, 'rt') as nf:
                    with open(project_docker_file, 'wt') as pf:
                        content = nf.read()
                        pf.write(content)

            background_task.add_task(RunIt.dockerize, str(PROJECT_PATH))   # type: ignore
        else:
            runit.install_dependency_packages()
        
        runit._id = project_id
        runit.update_config()
        
        funcs = []
        for func in runit.get_functions():
            funcs.append(f"{request.base_url}{project_id}/{func}")
        
        result['functions'] = funcs                                                         # type: ignore
        result['homepage'] = funcs[0] if len(funcs) else ''
        return result
    
    except Exception as e:
        logging.exception(e)
        return JSONResponse({'status': 'error', 'message': "Error publishing project."})
    

@projects_api.get('/clone/{project_name}')
async def api_clone_user_project(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    project_name: str
):
    '''
    Clone project from terminal
    
    @param project_id str ID of the project to clone
    @return Compressed file of files in project directory
    '''
    global PROJECTS_DIR
    
    try:
        project = await Project.find_one({'name': project_name, 'user_id': user.id})
        
        if project:
            project_path = Path(PROJECTS_DIR, str(project.id)).resolve()
            if not project_path.exists():
                raise FileNotFoundError('Project not found!')
                
            os.chdir(project_path)
            config = RunIt.load_config()
            
            if not config:
                raise FileNotFoundError('Project not found!')
            
            runit_project = RunIt(**config)
            filename = runit_project.compress()
            # os.chdir(WORKDIR)
            file_path = Path(project_path, filename)
            
            def iterfile():
                with open(file_path, mode="rb") as file:  
                    yield from file
            
            return StreamingResponse(iterfile(), media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={filename}"})

        else:
            return JSONResponse({'status': 'error', 'message': 'Project does not exist'})
    except Exception as e:
        logging.error(str(e))
        return JSONResponse({'status': 'error', 'message': "Couldn't clone project"})


@projects_api.get('/{project_id}')
async def api_get_project_details(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    project_id: str
):
    old_curdir = os.curdir
    response = {}
    
    project = await Project.get(project_id)
    
    if not project:
        logging.error(f'Project {project_id} does not exist')
        return JSONResponse(response)
    
    if not Path(PROJECTS_DIR, str(project.id)).resolve().exists():
        logging.error(f'Project Path {str(Path(PROJECTS_DIR, str(project.id)))} does not exist')
        return JSONResponse(response)
    
    os.chdir(Path(PROJECTS_DIR, str(project.id)).resolve())
    if not Path('.env').is_file():
        async with aiofiles.open('.env', 'w') as file:
            await file.close()

    environs = dotenv_values('.env')
    
    runit = RunIt(**RunIt.load_config())

    funcs = []
    for func in runit.get_functions():
        funcs.append(func)
    
    os.chdir(old_curdir)
    project = await Project.find_one({
        'id': project_id,
        'user_id': user.id
    })

    if project:
        project = project.json()
        del project['author']
        project['functions'] = funcs
        project['endpoints'] = []
        for func in funcs:
            project['endpoints'].append(f"{request.base_url}{project_id}{func}")
        response = project
        
    return JSONResponse(response)

@projects_api.delete('/{project_ids}')
@projects_api.delete('/{project_ids}/')
async def api_delete_user_project(
    user: Annotated[User, Depends(get_current_user)],
    project_ids, 
    background_task: BackgroundTasks):
    project_ids = project_ids.split(',')
    
    response = {
            'status': 'success',
            'message': f"Project{'' if len(project_ids) == 1 else 's'} deleted successfully"
    }
    try:
        user_id = user.id
        
        for project_id in project_ids:
            project = await Project.find_one({
                'id': project_id,
                'user_id': user_id
            })
            
            if project:
                await project.delete()
                background_task.add_task(shutil.rmtree, Path(PROJECTS_DIR, str(project.id)).resolve())

    except Exception:
        response['status'] = 'error'
        response['message'] = 'Error during operation'
    finally:
        return JSONResponse(response)

@projects_api.patch('/')
async def api_update_user_project(request: Request):
    # user_id = request.session['user_id']
    return JSONResponse({})