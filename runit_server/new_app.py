from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Dict
import logging
import json

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')

templates = Jinja2Templates('templates')

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

wsmanager = WSConnectionManager()

@app.websocket('/ws/{client_id}')
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await wsmanager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            if data['type'] == 'browser':
                wsmanager.receivers[client_id] = data['client']
            elif data['type'] == 'response':
                for key, value in wsmanager.receivers.items():
                    if client_id == value:
                        client_ws = wsmanager.clients[key]
                        await wsmanager.send(data['data'], client_ws)
            # await wsmanager.send(json.dumps({'message': 'Hello, client'}), websocket)
    except WebSocketDisconnect:
        wsmanager.disconnect(client_id)
    except Exception as e:
        logging.error(str(e)) 

@app.get('/e/{client_id}')
@app.get('/expose/{client_id}')
async def expose(request: Request, client_id: str):
    if client_id in list(wsmanager.clients.keys()):
        websocket = wsmanager.clients[client_id]
        parameters = dict(request.query_params)
        data = {'function': 'index', 'parameters': parameters}
        await wsmanager.send(json.dumps(data), websocket)
        return templates.TemplateResponse('exposed.html', context={'request': request})
    else:
        return templates.TemplateResponse('404.html', context={'request': request})

@app.get('/e/{client_id}/{func}')
@app.get('/expose/{client_id}/{func}')
async def expose(request: Request, client_id: str, func: str):
    if client_id in list(wsmanager.clients.keys()):
        websocket = wsmanager.clients[client_id]
        parameters = dict(request.query_params)
        print("Parameters", parameters)
        data = {'function': func, 'parameters': parameters}
        await wsmanager.send(json.dumps(data), websocket)
        return templates.TemplateResponse('exposed.html', context={'request': request})
    else:
        return templates.TemplateResponse('404.html', context={'request': request})