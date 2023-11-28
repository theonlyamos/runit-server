import os
import json
import logging
from typing import Annotated, Optional

from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter, Form, Request, WebSocket, WebSocketDisconnect, Depends, status

from ...core import WSConnectionManager, flash, templates
from ...common.security import authenticate, create_access_token, get_session_user
from ...models import User
from ...models import Admin
from ...common import Utils

from runit import RunIt

from dotenv import load_dotenv, find_dotenv, dotenv_values

from ...constants import (
    RUNIT_HOMEDIR,
    PROJECTS_DIR
)

load_dotenv()

REGISTER_HTML_TEMPLATE = 'register.html'
HOME_PAGE = 'index'

wsmanager = WSConnectionManager()

public_api = APIRouter(
    tags=["public"]
)

@public_api.post('/token')
@public_api.post('/token/')
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
