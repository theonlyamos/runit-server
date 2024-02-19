import os
import json
import logging
from typing import Dict, Literal, Optional
from pathlib import Path
from contextlib import asynccontextmanager

from odbms import DBMS
from dotenv import dotenv_values, find_dotenv
from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from .constants import RUNIT_WORKDIR, SUBSCRIPTION_EVENTS

app_initialized = False

def flash(request: Request, message: str, category: str = "primary") -> None:
   if "_messages" not in request.session:
       request.session["_messages"] = []
       request.session["_messages"].append((category, message))
       
def get_flashed_messages(request: Request):
   return request.session.pop("_messages") if "_messages" in request.session else []

templates_path = Path(__file__).resolve().parent / 'templates'
templates = Jinja2Templates(templates_path)
templates.env.globals['get_flashed_messages'] = get_flashed_messages

async def lifespan(request: Request):
    global app_initialized
    
    if not Path(RUNIT_WORKDIR).resolve().exists():
        Path(RUNIT_WORKDIR).resolve().mkdir()
    
    if not Path(RUNIT_WORKDIR, 'accounts').resolve().exists():
        Path(RUNIT_WORKDIR, 'account').resolve().mkdir()
        
    if not Path(RUNIT_WORKDIR, 'projects').resolve().exists():
        Path(RUNIT_WORKDIR, 'projects').resolve().mkdir()

    settings = dotenv_values(find_dotenv())
    setup = os.getenv('SETUP') or settings['SETUP']
    DB_DBMS = os.getenv('DBMS') or settings['DBMS']
    DB_HOST = os.getenv('DATABASE_HOST') or settings['DATABASE_HOST']
    DB_PORT = os.getenv('DATABASE_PORT') or settings['DATABASE_PORT']
    DB_USERNAME = os.getenv('DATABASE_USERNAME') or settings['DATABASE_USERNAME']
    DB_PASSWORD = os.getenv('DATABASE_PASSWORD') or settings['DATABASE_PASSWORD']
    DB_DATABASE = os.getenv('DATABASE_NAME') or settings['DATABASE_NAME']
    
    if not app_initialized and setup and setup == 'completed':
        DBMS.initialize(DB_DBMS, DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD,DB_DATABASE) # type: ignore
        app_initialized = True
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

    # Check for the existence of '{' and '}'
    if '{' not in data or '}' not in data:
        return data

    # Extract the dictionary part
    dictionary_str = data[data.find('{'): data.rfind('}')+1]

    # Replace single quotes with double quotes
    dictionary_str = dictionary_str.replace("'", '"')

    # Convert string to dictionary
    try:
        data = json.loads(dictionary_str)
    except Exception:
        logging.warning('Data is not a valid json string')
    finally:
        return data

class WSConnectionManager:
    
    def __init__(self) -> None:
        self.clients: Dict[str, WebSocket] = {}
        self.receivers: Dict[str, str] = {}
        self.subscribers: Dict[str, WebSocket] = {}
        self.subscriptions = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.clients[client_id] = websocket
        
    async def subscribe(
        self, websocket: WebSocket, 
        event: SUBSCRIPTION_EVENTS,
        client_id: str, 
        project_id: str,
        collection: str,
        document_id: Optional[str]=None):
        await websocket.accept()
        self.subscribers[client_id] = websocket
        
        sub_info = {
            "event": event,
            "client_id": client_id,
            "collection": collection,
            "document_id": document_id
        }
        
        if not project_id in self.subscriptions.keys():
            self.subscriptions[project_id] = [sub_info]
        else:
            self.subscriptions[project_id].append(sub_info)
    
    def disconnect(self, client_id: str):
        if client_id in list(self.clients.keys()):
            del self.clients[client_id]
        if client_id in list(self.receivers.keys()):
            del self.receivers[client_id]
        if client_id in list(self.subscribers.keys()):
            del self.subscribers[client_id]
        
    async def send(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def json(self, data: dict, websocket: WebSocket):
        await websocket.send_json(data)
    
    async def has_subscription(
        self, event: SUBSCRIPTION_EVENTS, project_id: str, 
        collection: str, document_id: str|list,
        data
        ):
        response = {'event': event, 'data': data}
        
        if project_id in self.subscriptions.keys():
            for subber in self.subscriptions[project_id]:
                sub_client = subber['client_id']
                if subber['collection'] == collection \
                    and (subber['document_id'] == document_id or subber['document_id'] is None) \
                    and (event == subber['event'] or subber['event'] == 'all'):
                    await self.send(json.dumps(response), self.subscribers[sub_client])