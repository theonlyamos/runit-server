import os
import json
import logging
from pathlib import Path
import time
from typing import Annotated, Optional

from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Form, Request, WebSocket, WebSocketDisconnect, Depends, status

from ..core import WSConnectionManager, flash, templates, jsonify
from ..common.security import authenticate, create_access_token, get_session_user
from ..models import User
from ..models import Admin
from ..models import Project
from ..models import Secret
from ..common import Utils

from runit import RunIt

from dotenv import find_dotenv, dotenv_values

from ..constants import (
    DOTENV_FILE,
    RUNIT_HOMEDIR,
    PROJECTS_DIR
)

REGISTER_HTML_TEMPLATE = 'register.html'
HOME_PAGE = 'index'

wsmanager = WSConnectionManager()

public = APIRouter(
    tags=["public"]
)

@public.websocket('/ws/{client_id}')
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await wsmanager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data['type'] == 'browser':
                wsmanager.receivers[client_id] = data['client']
            elif data['type'] == 'response':
                for key, value in wsmanager.receivers.items():
                    if client_id == value:
                        client_ws = wsmanager.clients[key]
                        await wsmanager.send(data['data'], client_ws)
            # await wsmanager.send(json.dumps({'message': 'Hello, client'}), websocket)
    except WebSocketDisconnect:
        wsmanager.disconnect(client_id)
    except Exception as e:
        logging.error(str(e)) 

@public.get('/e/{client_id}')
@public.get('/expose/{client_id}')
async def expose(request: Request, client_id: str):
    if client_id in list(wsmanager.clients.keys()):
        websocket = wsmanager.clients[client_id]
        parameters = dict(request.query_params)
        data = {'function': 'index', 'parameters': parameters}
        await wsmanager.send(json.dumps(data), websocket)
        return templates.TemplateResponse('exposed.html', context={'request': request})
    else:
        return templates.TemplateResponse('404.html', context={'request': request})

@public.get('/e/{client_id}/{func}')
@public.get('/expose/{client_id}/{func}')
async def expose_with_func(request: Request, client_id: str, func: str):
    if client_id in list(wsmanager.clients.keys()):
        websocket = wsmanager.clients[client_id]
        parameters = dict(request.query_params)
        data = {'function': func, 'parameters': parameters}
        await wsmanager.send(json.dumps(data), websocket)
        return templates.TemplateResponse('exposed.html', context={'request': request})
    else:
        return templates.TemplateResponse('404.html', context={'request': request})

@public.get('/')
@public.get('/login')
async def index(request: Request):
    settings = dotenv_values(find_dotenv(str(DOTENV_FILE)))
    setup = os.getenv('SETUP') or settings.get('SETUP')
    
    if setup != 'completed':
        return RedirectResponse(request.url_for('setup_index'))
    if 'user_id' in request.session.keys():
        return RedirectResponse(request.url_for('user_home'))
    return templates.TemplateResponse('login.html', context={'request': request})

@public.get('/register')
async def registration_page(request: Request):
    return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context={'request': request})

@public.post('/register')
async def register(
    request: Request,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    cpassword: Annotated[str, Form()],
):
    try:
        if password != cpassword:
            flash(request, 'Passwords do not match!', 'danger')
            return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context={'request': request})
        
        user = User.get_by_email(email)
 
        if user:
            flash(request, 'User already exists!', 'danger')
            return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context={'request': request})
        
        user = User(email, name, password).save()

        #print(user.inserted_id)
        flash(request, 'Registration Successful!', 'success')
        return RedirectResponse(request.url_for(HOME_PAGE), status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        logging.exception(e)
        flash(request, 'Error during registration', 'danger')
        return RedirectResponse(request.url_for('registration_page'), status_code=status.HTTP_303_SEE_OTHER)

@public.post('/login')
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate(form_data.username, form_data.password)
    
    if not user:
        flash(request, 'Invalid Login Credentials', 'danger')
        return templates.TemplateResponse('login.html', context={'request': request})

    access_token = create_access_token(user.json())
    request.session['user_id'] = user.id
    request.session['user_name'] = user.name
    request.session['user_email'] = user.email
    request.session['access_token'] = access_token

    return RedirectResponse(request.url_for('user_home'), status_code=status.HTTP_303_SEE_OTHER)

@public.get('/admin/login')
def admin_login_page(request: Request):
    if 'admin_id' in request.session and request.session['admin_id']:
        return RedirectResponse(request.url_for('admin_dashboard'))
    return templates.TemplateResponse('admin/login.html', context={'request': request, 'title':'Admin Login'})

@public.post('/admin/login')
def admin_login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    admin = Admin.get_by_username(form_data.username)

    if admin and Utils.check_hashed_password(form_data.password, admin.password):
        access_token = create_access_token(admin.json())
        request.session['admin_id'] = admin.id
        request.session['admin_name'] = admin.name
        request.session['admin_username'] = admin.email
        request.session['access_token'] = access_token

        return RedirectResponse(request.url_for('admin_dashboard'), status_code=status.HTTP_303_SEE_OTHER)
    flash(request, 'Invalid Login Credentials', 'danger')
    return RedirectResponse(request.url_for('admin_login_page'), status_code=status.HTTP_303_SEE_OTHER)

@public.get('/{project_id}')
@public.get('/{project_id}/{function}')
async def run_project(request: Request, project_id: str, function: Optional[str] = None):
    try:
        t0 = time.perf_counter()
        excluded = ['favicon.ico']
        if project_id in excluded:
            return None
        project = Project.get(project_id)
        if not project:
            logging.warning('Project not found')
            return JSONResponse(RunIt.notfound(), status.HTTP_404_NOT_FOUND)
        # elif project.private and request.session.get('user_id') != project.user_id:
        #     logging.warning('Project is private')
        #     return JSONResponse(RunIt.notfound(), status.HTTP_404_NOT_FOUND)
        
        secret = Secret.find_one({'project_id': project_id})
        if secret and secret.variables:
            environs = secret.variables
            for key, value in environs.items():
                os.environ[key] = value
        
        current_project_dir = Path(PROJECTS_DIR, str(project.id)).resolve()
        function = function if function else 'index'
        if current_project_dir.is_dir():
            result = await RunIt.start(project_id, function, PROJECTS_DIR, request.query_params._dict)
            os.chdir(RUNIT_HOMEDIR)
            response = await jsonify(result)
            t1 = time.perf_counter() # Record the stop time
            elapsed_time = t1 - t0 # Calculate elapsed time
            print(f'Time taken: {elapsed_time:.8f} seconds')
            return JSONResponse(response) if type(response) is dict else response
    except Exception as e:
        logging.exception(e)
        return JSONResponse(RunIt.notfound(), status.HTTP_404_NOT_FOUND)