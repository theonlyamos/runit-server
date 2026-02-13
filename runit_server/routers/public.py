import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import json
import logging
from pathlib import Path
import time
from typing import Annotated, Optional, Dict, Any
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

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


def _is_safe_next_path(next_path: Optional[str]) -> bool:
    if not next_path:
        return False
    parsed = urlparse(next_path)
    return bool(next_path.startswith("/")) and not parsed.scheme and not parsed.netloc


def _url_with_next(base_url: str, next_path: Optional[str]) -> str:
    if not _is_safe_next_path(next_path):
        return base_url
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode({'next': next_path})}"


def _login_template_context(request: Request, next_path: Optional[str]) -> dict:
    return {
        "request": request,
        "next": next_path if _is_safe_next_path(next_path) else "",
        "login_action": _url_with_next(str(request.url_for("login")), next_path),
        "register_page_url": _url_with_next(str(request.url_for("registration_page")), next_path),
    }


def _register_template_context(request: Request, next_path: Optional[str]) -> dict:
    return {
        "request": request,
        "next": next_path if _is_safe_next_path(next_path) else "",
        "register_action": _url_with_next(str(request.url_for("register")), next_path),
        "signin_page_url": _url_with_next(str(request.url_for("index")), next_path),
    }


def _append_access_token(redirect_uri: str, access_token: str) -> str:
    parsed = urlparse(redirect_uri)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["access_token"] = access_token
    new_query = urlencode(params)
    return urlunparse(parsed._replace(query=new_query))


def _is_valid_cli_redirect_uri(redirect_uri: Optional[str]) -> bool:
    if not redirect_uri:
        return False
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "http":
        return False
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        return False
    if not parsed.port:
        return False
    return bool(parsed.path and parsed.path.startswith("/"))

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
    next_path = request.query_params.get("next")
    
    if setup != 'completed':
        return RedirectResponse(request.url_for('setup_index'))
    if 'user_id' in request.session.keys():
        if _is_safe_next_path(next_path):
            return RedirectResponse(str(next_path), status_code=status.HTTP_303_SEE_OTHER)
        return RedirectResponse(request.url_for('user_home'))
    return templates.TemplateResponse('login.html', context=_login_template_context(request, next_path))

@public.get('/register')
async def registration_page(request: Request):
    next_path = request.query_params.get("next")
    return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context=_register_template_context(request, next_path))

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
    next_path = request.query_params.get("next")
    client_ip = get_client_ip(request)
    allowed, retry_after = rate_limiter.is_allowed(f"register:{client_ip}", max_requests=5, window_seconds=300)
    
    if not allowed:
        flash(request, f'Too many registration attempts. Try again in {retry_after} seconds.', 'danger')
        return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context=_register_template_context(request, next_path))
    
    try:
        if password != cpassword:
            flash(request, 'Passwords do not match!', 'danger')
            return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context=_register_template_context(request, next_path))
        
        is_strong, strength_msg = Utils.is_strong_password(password)
        if not is_strong:
            flash(request, strength_msg, 'danger')
            return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context=_register_template_context(request, next_path))
        
        user = await User.get_by_email(email)
 
        if user:
            flash(request, 'User already exists!', 'danger')
            return templates.TemplateResponse(REGISTER_HTML_TEMPLATE, context=_register_template_context(request, next_path))
        
        user = await User(email, name, password).save()

        flash(request, 'Registration Successful!', 'success')
        if _is_safe_next_path(next_path):
            return RedirectResponse(str(next_path), status_code=status.HTTP_303_SEE_OTHER)
        return RedirectResponse(request.url_for(HOME_PAGE), status_code=status.HTTP_303_SEE_OTHER)

    except Exception as e:
        logging.exception(e)
        flash(request, 'Error during registration', 'danger')
        return RedirectResponse(
            _url_with_next(str(request.url_for('registration_page')), next_path),
            status_code=status.HTTP_303_SEE_OTHER
        )

@public.post('/login')
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    next_path = request.query_params.get("next")
    client_ip = get_client_ip(request)
    allowed, retry_after = rate_limiter.is_allowed(f"login:{client_ip}", max_requests=10, window_seconds=60)
    
    if not allowed:
        flash(request, f'Too many login attempts. Try again in {retry_after} seconds.', 'danger')
        return templates.TemplateResponse('login.html', context=_login_template_context(request, next_path))
    
    csrf_token = form_data.scopes[0] if form_data.scopes else None
    if not await csrf.validate_token(request, csrf_token):
        flash(request, 'Invalid security token. Please try again.', 'danger')
        return templates.TemplateResponse('login.html', context=_login_template_context(request, next_path))
    
    user = await authenticate(form_data.username, form_data.password)
    
    if not user:
        flash(request, 'Invalid Login Credentials', 'danger')
        return templates.TemplateResponse('login.html', context=_login_template_context(request, next_path))

    access_token = create_access_token(user.json())
    request.session['user_id'] = user.id
    request.session['user_name'] = user.name
    request.session['user_email'] = user.email
    request.session['access_token'] = access_token
    
    rate_limiter.clear(f"login:{client_ip}")
    csrf.rotate_token(request)

    if _is_safe_next_path(next_path):
        return RedirectResponse(str(next_path), status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(request.url_for('user_home'), status_code=status.HTTP_303_SEE_OTHER)


@public.get('/auth/cli')
async def cli_auth(request: Request, redirect_uri: Optional[str] = None):
    if not _is_valid_cli_redirect_uri(redirect_uri):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid redirect_uri')
    redirect_uri_str = str(redirect_uri)

    next_path = f"/auth/cli?{urlencode({'redirect_uri': redirect_uri_str})}"
    if 'user_id' not in request.session:
        return RedirectResponse(
            _url_with_next(str(request.url_for('index')), next_path),
            status_code=status.HTTP_303_SEE_OTHER
        )

    access_token = request.session.get('access_token')
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    return RedirectResponse(
        _append_access_token(redirect_uri_str, str(access_token)),
        status_code=status.HTTP_303_SEE_OTHER
    )


@public.get('/auth/cli/register')
async def cli_auth_register(request: Request, redirect_uri: Optional[str] = None):
    if not _is_valid_cli_redirect_uri(redirect_uri):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid redirect_uri')
    redirect_uri_str = str(redirect_uri)

    next_path = f"/auth/cli?{urlencode({'redirect_uri': redirect_uri_str})}"
    if 'user_id' not in request.session:
        return RedirectResponse(
            _url_with_next(str(request.url_for('registration_page')), next_path),
            status_code=status.HTTP_303_SEE_OTHER
        )

    access_token = request.session.get('access_token')
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    return RedirectResponse(
        _append_access_token(redirect_uri_str, str(access_token)),
        status_code=status.HTTP_303_SEE_OTHER
    )

@public.get('/admin/login')
def admin_login_page(request: Request):
    if 'admin_id' in request.session and request.session['admin_id']:
        return RedirectResponse(request.url_for('admin_dashboard'))
    return templates.TemplateResponse('admin/login.html', context={'request': request, 'title':'Admin Login'})

@public.post('/admin/login')
async def admin_login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    admin = await Admin.get_by_username(form_data.username)

    if admin and admin.password and Utils.check_hashed_password(form_data.password, admin.password):
        admin_json = await admin.json()
        access_token = create_access_token(admin_json)
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
        project = await Project.get(project_id)

        if not project:
            logging.warning('Project not found')
            return JSONResponse(RunIt.notfound(), status.HTTP_404_NOT_FOUND)
        
        secret = await Secret.find_one({'project_id': project_id})
        env_vars = {}
        if secret and secret.variables:
            env_vars = secret.variables.copy()
        
        current_project_dir = Path(PROJECTS_DIR, str(project_id)).resolve()
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
            if isinstance(response, dict):
                return JSONResponse(response)
            if response is None:
                return JSONResponse(None)
            return JSONResponse(response)
    except Exception as e:
        logging.exception(e)
        return JSONResponse(RunIt.notfound(), status.HTTP_404_NOT_FOUND)