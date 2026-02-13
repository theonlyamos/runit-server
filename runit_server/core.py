import os
import json
import logging
import asyncio
import signal
from typing import Dict, Literal, Optional, Set
from pathlib import Path
from contextlib import asynccontextmanager
from threading import Lock

from odbms import DBMS
from dotenv import dotenv_values, find_dotenv
from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from .constants import DOTENV_FILE, RUNIT_WORKDIR, SUBSCRIPTION_EVENTS

app_initialized = False
startup_time = None

def flash(request: Request, message: str, category: str = "primary") -> None:
   if "_messages" not in request.session:
       request.session["_messages"] = []
       request.session["_messages"].append((category, message))
       
def get_flashed_messages(request: Request):
   return request.session.pop("_messages") if "_messages" in request.session else []

templates_path = Path(__file__).resolve().parent / 'templates'
templates = Jinja2Templates(templates_path)
templates.env.globals['get_flashed_messages'] = get_flashed_messages

def escape_attr(value):
    """Escape a value for safe use in HTML data attributes."""
    if value is None:
        return ''
    return str(value).replace('&', '&amp;').replace('"', '&quot;').replace("'", '&#39;').replace('<', '&lt;').replace('>', '&gt;')

templates.env.filters['escape_attr'] = escape_attr
templates.env.globals['escape_attr'] = escape_attr

def get_csrf_token(request: Request) -> str:
    """Get CSRF token for the current session."""
    from .common.utils import csrf
    return csrf.get_token(request)

templates.env.globals['get_csrf_token'] = get_csrf_token

async def lifespan(request: Request):
    global app_initialized, startup_time
    
    if not RUNIT_WORKDIR.resolve().exists():
        RUNIT_WORKDIR.resolve().mkdir()
    
    if not RUNIT_WORKDIR.joinpath('accounts').resolve().exists():
        RUNIT_WORKDIR.joinpath('account').resolve().mkdir()
        
    if not RUNIT_WORKDIR.joinpath('projects').resolve().exists():
        RUNIT_WORKDIR.joinpath('projects').resolve().mkdir()

    settings = dotenv_values(find_dotenv(str(DOTENV_FILE)))
    setup = os.getenv('SETUP') or settings.get('SETUP')
    
    DB_DBMS = os.getenv('DBMS') or settings.get('DBMS')
    DB_HOST = os.getenv('DATABASE_HOST') or settings.get('DATABASE_HOST')
    DB_PORT = os.getenv('DATABASE_PORT') or settings.get('DATABASE_PORT')
    DB_USERNAME = os.getenv('DATABASE_USERNAME') or settings.get('DATABASE_USERNAME')
    DB_PASSWORD = os.getenv('DATABASE_PASSWORD') or settings.get('DATABASE_PASSWORD')
    DB_DATABASE = os.getenv('DATABASE_NAME') or settings.get('DATABASE_NAME')
    
    if not app_initialized and setup and setup == 'completed':
        await DBMS.initialize_async(DB_DBMS, DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_DATABASE)
        app_initialized = True
        startup_time = asyncio.get_event_loop().time()
    else:
        return RedirectResponse(request.url_for('setup_index'))
    return True

async def jsonify(data):
    """
    Converts a string containing a dictionary to a Python dictionary.

    Args:
        data: The string containing a dictionary.

    Returns:
        A Python dictionary or the original string if no dictionary is found.
    """

    if not isinstance(data, str):
        return data

    if '{' not in data or '}' not in data:
        return data

    dictionary_str = data[data.find('{'): data.rfind('}')+1]
    dictionary_str = dictionary_str.replace("'", '"')

    try:
        import ast
        data = ast.literal_eval(dictionary_str)
    except Exception:
        try:
            data = json.loads(dictionary_str)
        except Exception:
            logging.warning('Data is not a valid json string')
    finally:
        return data


class WSConnectionManager:
    """Thread-safe WebSocket connection manager."""
    
    def __init__(self) -> None:
        self._lock = Lock()
        self._clients: Dict[str, WebSocket] = {}
        self._receivers: Dict[str, str] = {}
        self._subscribers: Dict[str, WebSocket] = {}
        self._subscriptions: Dict[str, list] = {}
        
    @property
    def clients(self) -> Dict[str, WebSocket]:
        with self._lock:
            return self._clients.copy()
    
    @property
    def receivers(self) -> Dict[str, str]:
        with self._lock:
            return self._receivers.copy()
    
    @property
    def subscribers(self) -> Dict[str, WebSocket]:
        with self._lock:
            return self._subscribers.copy()
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        with self._lock:
            self._clients[client_id] = websocket
        
    async def subscribe(
        self, websocket: WebSocket, 
        event: SUBSCRIPTION_EVENTS,
        client_id: str, 
        project_id: str,
        collection: str,
        document_id: Optional[str]=None):
        await websocket.accept()
        with self._lock:
            self._subscribers[client_id] = websocket
        
            sub_info = {
                "event": event,
                "client_id": client_id,
                "collection": collection,
                "document_id": document_id
            }
            
            if project_id not in self._subscriptions:
                self._subscriptions[project_id] = [sub_info]
            else:
                self._subscriptions[project_id].append(sub_info)
    
    def disconnect(self, client_id: str):
        with self._lock:
            self._clients.pop(client_id, None)
            self._receivers.pop(client_id, None)
            self._subscribers.pop(client_id, None)
        
    async def send(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def json(self, data: dict, websocket: WebSocket):
        await websocket.send_json(data)
    
    async def has_subscription(
        self, event: SUBSCRIPTION_EVENTS, project_id: str, 
        collection: str, document_id: str,
        data
        ):
        response = {'event': event, 'data': data}
        
        with self._lock:
            if project_id in self._subscriptions:
                for subber in self._subscriptions[project_id]:
                    sub_client = subber['client_id']
                    if subber['collection'] == collection \
                        and (subber['document_id'] == document_id or subber['document_id'] is None) \
                        and (event == subber['event'] or subber['event'] == 'all'):
                        if sub_client in self._subscribers:
                            await self.send(json.dumps(response), self._subscribers[sub_client])

    def get_stats(self) -> dict:
        """Get connection statistics."""
        with self._lock:
            return {
                "connected_clients": len(self._clients),
                "subscribers": len(self._subscribers),
                "active_subscriptions": sum(len(subs) for subs in self._subscriptions.values())
            }


ws_manager = WSConnectionManager()


async def on_startup():
    """Initialize server on startup."""
    global app_initialized, startup_time
    startup_time = asyncio.get_event_loop().time()
    logging.info("Runit server starting up...")

    # Initialize database before scheduler starts (when setup is completed)
    settings = dotenv_values(find_dotenv(str(DOTENV_FILE)))
    setup = os.getenv('SETUP') or settings.get('SETUP')
    if setup and setup == 'completed':
        DB_DBMS = os.getenv('DBMS') or settings.get('DBMS')
        DB_HOST = os.getenv('DATABASE_HOST') or settings.get('DATABASE_HOST')
        DB_PORT = os.getenv('DATABASE_PORT') or settings.get('DATABASE_PORT')
        DB_USERNAME = os.getenv('DATABASE_USERNAME') or settings.get('DATABASE_USERNAME')
        DB_PASSWORD = os.getenv('DATABASE_PASSWORD') or settings.get('DATABASE_PASSWORD')
        DB_DATABASE = os.getenv('DATABASE_NAME') or settings.get('DATABASE_NAME')
        await DBMS.initialize_async(DB_DBMS, DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_DATABASE)
        app_initialized = True


async def on_shutdown():
    """Cleanup on shutdown."""
    logging.info("Runit server shutting down...")


def get_uptime() -> float:
    """Get server uptime in seconds."""
    if startup_time is None:
        return 0
    return asyncio.get_event_loop().time() - startup_time