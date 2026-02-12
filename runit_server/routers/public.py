import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import json
import logging
from pathlib import Path
import time
from typing import Annotated, Optional, Dict, Any

from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Form, Request, WebSocket, WebSocketDisconnect, Depends, status, HTTPException

from ..core import WSConnectionManager, flash, templates, jsonify
from ..common.security import authenticate, create_access_token, get_session_user
from ..models import User
from ..models import Admin
from ..models import Project
from ..models import Secret
from ..common.utils import Utils, rate_limiter, csrf

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

def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@public.post('/register')
async def register(
    request: Request,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    cpassword: Annotated[str, Form()],
):
    client_ip = get_client_ip(request)
    allowed, retry_after = rate_limiter.is_allowed(f"register:{client_ip}", max_requests=5, window_seconds=300)
    
    if not allowed:
        flash(request, f'Too many registration attempts. Try again in {retry_after} seconds.', 'danger')
        return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context={'request': request})
    
    try:
        if password != cpassword:
            flash(request, 'Passwords do not match!', 'danger')
            return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context={'request': request})
        
        is_strong, strength_msg = Utils.is_strong_password(password)
        if not is_strong:
            flash(request, strength_msg, 'danger')
            return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context={'request': request})
        
        user = User.get_by_email(email)
 
        if user:
            flash(request, 'User already exists!', 'danger')
            return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context={'request': request})
        
        user = User(email, name, password).save()

        flash(request, 'Registration Successful!', 'success')
        return RedirectResponse(request.url_for(HOME_PAGE), status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        logging.exception(e)
        flash(request, 'Error during registration', 'danger')
        return RedirectResponse(request.url_for('registration_page'), status_code=status.HTTP_303_SEE_OTHER)

@public.post('/login')
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    client_ip = get_client_ip(request)
    allowed, retry_after = rate_limiter.is_allowed(f"login:{client_ip}", max_requests=10, window_seconds=60)
    
    if not allowed:
        flash(request, f'Too many login attempts. Try again in {retry_after} seconds.', 'danger')
        return templates.TemplateResponse('login.html', context={'request': request})
    
    csrf_token = form_data.scopes[0] if form_data.scopes else None
    if not csrf.validate_token(request, csrf_token):
        flash(request, 'Invalid security token. Please try again.', 'danger')
        return templates.TemplateResponse('login.html', context={'request': request})
    
    user = authenticate(form_data.username, form_data.password)
    
    if not user:
        flash(request, 'Invalid Login Credentials', 'danger')
        return templates.TemplateResponse('login.html', context={'request': request})

    access_token = create_access_token(user.json())
    request.session['user_id'] = user.id
    request.session['user_name'] = user.name
    request.session['user_email'] = user.email
    request.session['access_token'] = access_token
    
    rate_limiter.clear(f"login:{client_ip}")
    csrf.rotate_token(request)

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

_project_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="project_runner")


async def run_project_async(
    project_id: str, 
    function: str, 
    projects_dir: str, 
    params: Dict[str, Any]
) -> Any:
    """Run project in thread pool to avoid blocking event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _project_executor,
        lambda: asyncio.run(RunIt.start(project_id, function, projects_dir, params))
    )


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
        
        secret = Secret.find_one({'project_id': project_id})
        env_vars = {}
        if secret and secret.variables:
            env_vars = secret.variables.copy()
        
        current_project_dir = Path(PROJECTS_DIR, str(project.id)).resolve()
        function = function if function else 'index'
        if current_project_dir.is_dir():
            original_env = dict(os.environ)
            try:
                for key, value in env_vars.items():
                    os.environ[key] = str(value)
                
                result = await run_project_async(
                    project_id, 
                    function, 
                    PROJECTS_DIR, 
                    dict(request.query_params)
                )
            finally:
                for key in env_vars.keys():
                    if key in original_env:
                        os.environ[key] = original_env[key]
                    else:
                        os.environ.pop(key, None)
            
            response = await jsonify(result)
            t1 = time.perf_counter()
            elapsed_time = t1 - t0
            logging.info(f'Project {project_id} executed in {elapsed_time:.4f}s')
            return JSONResponse(response) if isinstance(response, dict) else response
    except Exception as e:
        logging.exception(e)
        return JSONResponse(RunIt.notfound(), status.HTTP_404_NOT_FOUND)