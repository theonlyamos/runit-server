import os
from pathlib import Path
import time
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status, APIRouter
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import timedelta

from runit import RunIt

from ...models.project import Project
from ...models.secret import Secret
from ...core import jsonify
from ...common.security import authenticate, create_access_token, Token
from ...models import User
from ...models import Admin
from ...common import Utils
from ...constants import (
    RUNIT_HOMEDIR,
    PROJECTS_DIR,
    API_VERSION
)

from dotenv import load_dotenv


load_dotenv()

REGISTER_HTML_TEMPLATE = 'register.html'
HOME_PAGE = 'index'

public_api = APIRouter(
    tags=["public_api api"]
)

class LoginData(BaseModel):
    email: EmailStr
    password: str
    
class UserData(BaseModel):
    name: str
    email: EmailStr
    password: str
    cpassword: str



# Login endpoint
@public_api.post("/login", response_model=Token)
async def api_login(form_data: LoginData):
    user = authenticate(form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"email": user.email}, expires_delta=access_token_expires
    )

    return JSONResponse({"access_token": access_token, "token_type": "bearer"})

@public_api.post('/register', response_model=Token)
async def api_register(
    data: UserData
):
    if data.password != data.cpassword:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Passwords do not match",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = User.get_by_email(data.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User already exists",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    User(data.email, data.name, data.password).save()
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"email": data.email}, expires_delta=access_token_expires
    )

    return JSONResponse({"access_token": access_token, "token_type": "bearer"})

@public_api.get('/{project_id}')
@public_api.get('/{project_id}/{function}')
async def run_project_api(request: Request, project_id: str, function: Optional[str] = None):
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
            result = RunIt.start(project_id, function, PROJECTS_DIR, request.query_params._dict)
            os.chdir(RUNIT_HOMEDIR)
            response = await jsonify(result)
            t1 = time.perf_counter() # Record the stop time
            elapsed_time = t1 - t0 # Calculate elapsed time
            print(f'Time taken: {elapsed_time:.8f} seconds')
            return JSONResponse(response) if type(response) is dict else response
    except Exception as e:
        logging.exception(e)
        return JSONResponse(RunIt.notfound(), status.HTTP_404_NOT_FOUND)
