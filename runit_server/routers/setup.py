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
    prefix="/setup",
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
async def setup_index(request: Request):
    env_file = find_dotenv()
    
    if env_file:
        settings = dotenv_values(env_file)
        if settings['SETUP'] == 'completed':
            return RedirectResponse(request.url_for('index'))
        
    return templates.TemplateResponse('setup/index.html', {
        'request': request
    })

@setup.post('/')
async def initsetup(request: Request):
    env_file = find_dotenv()
    settings = dotenv_values(env_file)
    data = await request.form()
    
    settings.update(data._dict)

    for key, value in settings.items():
         set_key(env_file, key, value) # type: ignore
    set_key(env_file, 'SETUP', 'completed')
    
    flash(request,'Setup completed', category='success')
    return RedirectResponse(request.url_for('complete_setup'))

@setup.get('/complete')
async def complete_setup():
    settings = dotenv_values(find_dotenv())

    if 'SETUP' in settings.keys() and settings['SETUP'] == 'completed':
        DBMS.initialize(settings['DBMS'], settings['DATABASE_HOST'], settings['DATABASE_PORT'], # type: ignore
                    settings['DATABASE_USERNAME'], settings['DATABASE_PASSWORD'],  # type: ignore
                    settings['DATABASE_NAME']) # type: ignore

    return RedirectResponse(request.url_for('index'))
