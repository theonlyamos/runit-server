import os
import time
from pathlib import Path
from typing import Annotated, Optional, Dict
import aiofiles

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import APIRouter, Form, HTTPException, Request, Depends,\
    status, UploadFile

from ..core import flash, templates
from ..common import get_session
from ..common import Utils
from ..models import Project
from ..models import User
from ..models import Function

from runit import RunIt

from dotenv import load_dotenv

from ..constants import (
    EXTENSIONS,
    LANGUAGE_TO_ICONS,
    RUNIT_WORKDIR
)

PROJECTS_INDEX_TEMPLATE = 'projects/index.html'

load_dotenv()

account = APIRouter(
    prefix="/account",
    tags=["account"],
    dependencies=[Depends(get_session)]
)

@account.get('/')
async def user_home(request: Request):
    user = User.get(request.session['user_id'])
    return templates.TemplateResponse('account/home.html', context={
        'request': request, 'page':'home', 'user':user
    })

@account.get('/functions')
@account.get('/functions/')
async def list_user_functions(request: Request):
    functions = Function.get_by_user(request.session['user_id'])
    projects = Project.get_by_user(request.session['user_id'])
    
    return templates.TemplateResponse('functions/index.html', context={
        'request': request, 'page':'functions', 'functions': functions, 
        'projects': projects, 'languages': EXTENSIONS, 'icons': LANGUAGE_TO_ICONS})

 
@account.get('/profile')
@account.get('/profile/')
async def user_profile(request: Request):
    user_id = request.session['user_id']
    user = User.get(user_id)
    
    view = request.get('view')
    view = view if view else 'grid'
    
    return templates.TemplateResponse('account/profile.html', context={
        'request': request, 'page': 'profile', 'user':user.json()})

@account.post('/profile')
@account.post('/profile/')
async def update_user_profile(request: Request, email: Annotated[str, Form()], name: Annotated[str, Form()], password: Annotated[str, Form()]):
    user_id = request.session['user_id']
    user = User.get(user_id)

    if Utils.check_hashed_password(password, user.password):
        user.email = email
        user.name = name
        user.save()

        flash(request, "Profile updated successfully", "success")
    else:
        flash(request, "Unauthorized Action", "warning")
        
    return templates.TemplateResponse('account/profile.html', context={
        'request': request, 'page': 'profile', 'user':user.json()})

@account.post('/password')
@account.post('/password/')
async def update_user_password(request: Request, password: Annotated[str, Form()], new_password: Annotated[str, Form()], confirm_password: Annotated[str, Form()]):
    user_id = request.session['user_id']
    user = User.get(user_id)


    if not Utils.check_hashed_password(password, user.password):
        flash(request, "Unauthorized Action", "danger")
    elif new_password != confirm_password:
        flash(request, "Passwords do not watch", "danger")
    else:
        user.reset_password(new_password)
        request.session.clear()
        flash(request, "Password changed successfully. Log in", "success")
        return RedirectResponse(request.url_for('index'), status_code=status.HTTP_303_SEE_OTHER)
    
    return RedirectResponse(request.url_for('user_profile'), status_code=status.HTTP_303_SEE_OTHER)
        
@account.post('/image')
@account.post('/image/')
async def update_user_image(request: Request,  file: UploadFile):
    user_id = request.session['user_id']
    filename = f"{user_id}_{int(time.time())}{Path(file.filename).suffix}"
    upload_dir = Path(RUNIT_WORKDIR).joinpath('accounts', user_id)
    
    try:
        if not upload_dir.exists():
            upload_dir.mkdir()
            
        upload_path = upload_dir.joinpath(filename)

        contents = await file.read()
        async with aiofiles.open(str(upload_path), 'wb') as f:
            await f.write(contents)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading image",
        )
    finally:
        await file.close()
    
    user = User.get(user_id)  
    user.image = filename
    user.save()  
    return JSONResponse({'status': 'success', 'filepath': str(upload_path)})
    # return RedirectResponse(request.url_for('user_profile'), status_code=status.HTTP_303_SEE_OTHER)

@account.route('/logout/')
async def user_logout(request: Request):
    request.session.clear()
    return RedirectResponse(request.url_for('index'))

# @account.route('/{page}')
# async def main(page):
#     if (os.path.isdir(os.path.join('accounts', page))):
#         os.chdir(os.path.join('accounts', page))
#         result = RunIt.start()
#         #os.chdir(os.path.join('..', '..'))
#         return result
#     else:
#         return RunIt.notfound()
