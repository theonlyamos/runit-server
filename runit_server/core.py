import os
from typing import Dict
from pathlib import Path
from contextlib import asynccontextmanager

from odbms import DBMS
from dotenv import dotenv_values, find_dotenv
from fastapi import FastAPI, WebSocket, Request
from fastapi.templating import Jinja2Templates


from .constants import RUNIT_WORKDIR

def flash(request: Request, message: str, category: str = "primary") -> None:
   if "_messages" not in request.session:
       request.session["_messages"] = []
       request.session["_messages"].append((category, message))
def get_flashed_messages(request: Request):
   return request.session.pop("_messages") if "_messages" in request.session else []

templates_path = Path(__file__).resolve().parent / 'templates'
templates = Jinja2Templates(templates_path)
templates.env.globals['get_flashed_messages'] = get_flashed_messages

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(RUNIT_WORKDIR):
        os.mkdir(RUNIT_WORKDIR)
    
    if not (os.path.exists(os.path.join(RUNIT_WORKDIR, 'accounts'))):
        os.mkdir(os.path.join(RUNIT_WORKDIR, 'accounts'))
        
    if not (os.path.exists(os.path.join(RUNIT_WORKDIR, 'projects'))):
        os.mkdir(os.path.join(RUNIT_WORKDIR, 'projects'))

    settings = dotenv_values(find_dotenv())

    if 'SETUP' in settings.keys() and settings['SETUP'] == 'completed':
        DBMS.initialize(settings['DBMS'], settings['DATABASE_HOST'], settings['DATABASE_PORT'],
                    settings['DATABASE_USERNAME'], settings['DATABASE_PASSWORD'], 
                    settings['DATABASE_NAME'])
    yield

class WSConnectionManager:
    def __init__(self) -> None:
        self.clients: Dict[str, WebSocket] = {}
        self.receivers: Dict[str, str] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.clients[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in list(self.clients.keys()):
            del self.clients[client_id]
        if client_id in list(self.receivers.keys()):
            del self.receivers[client_id]
        
    async def send(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def json(self, data: dict, websocket: WebSocket):
        await websocket.send_json(data)
