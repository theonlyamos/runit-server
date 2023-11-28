import os
import json
import logging
from hashlib import sha256
from typing import Annotated, Optional

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
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

from ...routers.api.project import projects_api

from dotenv import load_dotenv, find_dotenv, dotenv_values


load_dotenv()

REGISTER_HTML_TEMPLATE = 'register.html'
HOME_PAGE = 'index'

public_api = APIRouter(
    tags=["public api"]
)



# Login endpoint
@public_api.post("/token", response_model=Token)
async def api_login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate(form_data.username, form_data.password)
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