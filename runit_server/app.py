import os
import json
import logging
from typing import Optional
from pathlib import Path
from sys import platform
from datetime import timedelta


from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from dotenv import load_dotenv

from .common import  (
    Login, Account, ProjectById, ProjectRS, 
    ProjectCloneRS, Document
)

from .models import Admin
from .models import Role
from .core import lifespan, templates
from .exceptions import UnauthorizedException, UnauthorizedAdminException
from .constants import RUNIT_WORKDIR, SESSION_SECRET_KEY


from .routers import account
from .routers import project
from .routers import database
from .routers import admin
from .routers import public

load_dotenv()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    max_age=3600,
    https_only=True
)
static = Path(__file__).resolve().parent / "static"
uploads = Path(RUNIT_WORKDIR, 'accounts')
app.mount('/static', StaticFiles(directory=static, html=True),  name='static')
app.mount('/uploads', StaticFiles(directory=uploads, html=True),  name='uploads')
app.include_router(admin)
app.include_router(account)
app.include_router(project)
app.include_router(database)
app.include_router(public)

@app.exception_handler(UnauthorizedException)
async def redirect_to_login(request: Request,  exception: Optional[str]):
    return RedirectResponse(request.url_for('index'))

@app.exception_handler(UnauthorizedAdminException)
async def redirect_to_admin_login(request: Request, exception: Optional[str]):
    return RedirectResponse(request.url_for('admin_login_page'))

@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_page(request: Request, exception: Optional[str]):
    return templates.TemplateResponse('404.html', {'request': request})