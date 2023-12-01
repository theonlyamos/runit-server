from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request, \
    Depends, status, UploadFile
    
from ..core import flash, templates
from ..common.security import authenticate
from ..models import User

import os
from dotenv import load_dotenv, dotenv_values, set_key, find_dotenv

from runit import RunIt

load_dotenv()

setup = APIRouter(
    prefix="/projects",
    tags=["projects"]
)

'''
Page for setting up runit-server
configurations.


@setup.before_request
def initial():
    os.chdir(os.getenv('RUNIT_HOMEDIR'))
''' 

@setup.get('/')
def index(request: Request):
    env_file = find_dotenv()
    
    if env_file:
        settings = dotenv_values(env_file)
        if settings['SETUP'] == 'completed':
            return RedirectResponse(request.url_for('public.index'))
        
    return templates.TemplateResponse('setup/index.html', {
        'request': request
    })

@setup.post('/')
def initsetup(request: Request):
    env_file = find_dotenv()
    settings = dotenv_values(env_file)

    settings.update(request.form().__dict__)

    for key, value in settings.items():
         set_key(env_file, key, value) # type: ignore
    set_key(env_file, 'SETUP', 'completed')
    
    flash(request,'Setup completed', category='success')
    return RedirectResponse(request.url_for('complete_setup'))
