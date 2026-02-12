import signal
import asyncio
import logging
from typing import Optional
from pathlib import Path
from sys import platform
from datetime import timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from .core import lifespan, templates, on_startup, on_shutdown, get_uptime, ws_manager
from .exceptions import UnauthorizedException, UnauthorizedAdminException
from .constants import RUNIT_WORKDIR, SESSION_SECRET_KEY, DOTENV_FILE, VERSION

from dotenv import load_dotenv

from .routers import account
from .routers import project
from .routers import database
from .routers import github_router
from .routers import admin
from .routers import public
from .routers import setup

from .routers.api import api_router

load_dotenv(DOTENV_FILE)

shutdown_event = asyncio.Event()

@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Application lifespan context manager."""
    await on_startup()
    
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(graceful_shutdown()))
        except NotImplementedError:
            pass
    
    yield
    
    await on_shutdown()


async def graceful_shutdown():
    """Handle graceful shutdown."""
    logging.info("Received shutdown signal, initiating graceful shutdown...")
    shutdown_event.set()
    
    await asyncio.sleep(0.5)
    
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task():
            task.cancel()


app = FastAPI(
    title="Runit Server",
    description="Serverless function execution backend",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=app_lifespan,
    dependencies=[Depends(lifespan)]
)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    max_age=3600,
    https_only=False
)


@app.get('/health')
@app.get('/healthz')
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return JSONResponse({
        "status": "healthy",
        "version": VERSION,
        "uptime_seconds": get_uptime()
    })


@app.get('/ready')
@app.get('/readyz')
async def readiness_check():
    """Readiness check endpoint for Kubernetes."""
    return JSONResponse({
        "status": "ready",
        "websocket_connections": ws_manager.get_stats()
    })


@app.get('/metrics')
async def metrics():
    """Basic metrics endpoint."""
    return JSONResponse({
        "uptime_seconds": get_uptime(),
        "version": VERSION,
        "websocket": ws_manager.get_stats()
    })

static = Path(__file__).resolve().parent / "static"
uploads = Path(RUNIT_WORKDIR, 'accounts')
app.mount('/static', StaticFiles(directory=static, html=True),  name='static')
    
if not uploads.resolve().exists():
    uploads.resolve().mkdir()
    

app.mount('/uploads', StaticFiles(directory=uploads, html=True),  name='uploads')

app.include_router(api_router)
app.include_router(admin)
app.include_router(account)
app.include_router(project)
app.include_router(database)
app.include_router(github_router)
app.include_router(public)
app.include_router(setup)

@app.exception_handler(UnauthorizedException)
async def redirect_to_login(request: Request,  exception: Optional[str]):
    return RedirectResponse(request.url_for('index'))

@app.exception_handler(UnauthorizedAdminException)
async def redirect_to_admin_login(request: Request, exception: Optional[str]):
    return RedirectResponse(request.url_for('admin_login_page'))

@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_page(request: Request, exception: Optional[str]):
    return templates.TemplateResponse('404.html', {'request': request})
