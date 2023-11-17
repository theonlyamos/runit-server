import os
import json
import logging
from typing import Optional

from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Depends, status

from ..core import WSConnectionManager, flash, templates
from ..common.security import authenticate, create_access_token, get_session_user
from ..models import User
from ..models import Admin
from ..common import Utils

from runit import RunIt

from dotenv import load_dotenv, find_dotenv, dotenv_values

from ..constants import (
    RUNIT_HOMEDIR,
    PROJECTS_DIR
)

load_dotenv()

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
async def expose(request: Request, client_id: str, func: str):
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
@public.get('/login/')
async def index(request: Request):
    settings = dotenv_values(find_dotenv())

    if settings is None or settings['SETUP'] != 'completed':
        return RedirectResponse(request.url_for('setup.index'))
    if 'user_id' in request.session.keys():
        return RedirectResponse(request.url_for('user_home'))
    return templates.TemplateResponse('login.html', context={'request': request})

@public.get('/register')
@public.get('/register/')
async def registration_page(request: Request):
    return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context={'request': request})

@public.post('/register')
@public.post('/register/')
async def register(request: Request):
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        c_password = request.form.get('cpassword')
        if password != c_password:
            flash(request, 'Passwords do not match!', 'danger')
            return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context={'request': request})
        user = User.get_by_email(email)
        if user:
            flash(request, 'User is already Registered!', 'danger')
            return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context={'request': request})
        
        User(email, name, password).save()
        #print(user.inserted_id)
        flash(request, 'Registration Successful!', 'success')
        return RedirectResponse(request.url_for(HOME_PAGE), status_code=status.HTTP_201_CREATED)

    except Exception:
        flash(request, 'Error during registration', 'danger')
        return RedirectResponse(request.url_for('registration_page'), status_code=status.HTTP_304_NOT_MODIFIED)

@public.post('/login')
@public.post('/login/')
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

@public.get('/login/admin')
@public.get('/login/admin/')
def admin_login_page(request: Request):
    if 'admin_id' in request.session and request.session['admin_id']:
        return RedirectResponse(request.url_for('admin_dashboard'))
    return templates.TemplateResponse('admin/login.html', context={'request': request, 'title':'Admin Login'})

@public.post('/login/admin')
@public.post('/login/admin/')
def admin_login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    admin = Admin.get_by_username(form_data.username)
    if admin and Utils.check_hashed_password(form_data.password, admin.password):
            
            access_token = create_access_token(admin.json())
            request.session['admin_id'] = admin.id
            request.session['admin_name'] = admin.name
            request.session['admin_username'] = admin.username
            request.session['access_token'] = access_token

            return RedirectResponse(request.url_for('admin_dashboard'), status_code=status.HTTP_303_SEE_OTHER)
    flash(request, 'Invalid Login Credentials', 'danger')
    return RedirectResponse(request.url_for('admin_login_page'))

@public.get('/{project_id}')
@public.get('/{project_id}/')
def project(project_id: str):
    current_project_dir = os.path.join(PROJECTS_DIR, project_id)
    if os.path.isdir(current_project_dir):
        if not RunIt.is_private(project_id, current_project_dir):
            result = RunIt.start(project_id, 'index', current_project_dir)
            os.chdir(RUNIT_HOMEDIR)
            
            return result

    return RunIt.notfound()

@public.get('/{project_id}/{function}')
@public.get('/{project_id}/{function}/')
def run_project(request: Request, project_id, function: Optional[str] = None):
    current_project_dir = os.path.join(PROJECTS_DIR, project_id)
    if os.path.isdir(current_project_dir):
        if not RunIt.is_private(project_id, current_project_dir):
            result = RunIt.start(project_id, function, current_project_dir, request.query_params)
            os.chdir(RUNIT_HOMEDIR)
            return result

    return RunIt.notfound()