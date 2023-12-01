import os
import json
import logging
from hashlib import sha256
from typing import Annotated, Optional

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt

from runit import RunIt

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
    tags=["public api"]
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
async def register(
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
