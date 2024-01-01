
import logging
from typing import Annotated, Optional

from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import APIRouter, BackgroundTasks, Request, Depends, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

from ...core import WSConnectionManager
from ...common import get_current_user
from ...models import User
from ...models import Database
from ...models import Collection
from ...constants import SUBSCRIPTION_EVENTS

from runit import RunIt

PROJECT_404_ERROR = 'Project does not exist'

load_dotenv()

database_api = APIRouter(
    prefix="/documents",
    tags=["database api"],
    dependencies=[Depends(get_current_user)],
)

wsmanager = WSConnectionManager()

async def get_collection(project_id: str, collection: str, document_id: list|str, _filter: dict):
    db = Database.find_one({
        'project_id': project_id,
        'name': collection
    })
    
    Collection.TABLE_NAME = db.collection_name
    if isinstance(document_id, list):
        results = []
        for _id in document_id:
            _filter['id'] = _id
            document = Collection.find_one(_filter)
            results.append(document.json())
        return results
    elif document_id:
        _filter['id'] = document_id

    document = Collection.find_one(_filter)

    if document:
        return document.json()
    return {}

@database_api.websocket('/subscribe/{event}/{client_id}/{project_id}/{collection}')
@database_api.websocket('/subscribe/{event}/{client_id}/{project_id}/{collection}/')
@database_api.websocket('/subscribe/{event}/{client_id}/{project_id}/{collection}/{document_id}')
@database_api.websocket('/subscribe/{event}/{client_id}/{project_id}/{collection}/{document_id}/')
async def subscription_endpoint(
    websocket: WebSocket, 
    event: SUBSCRIPTION_EVENTS,
    client_id: str,
    project_id: str,
    collection: str,
    document_id: Optional[str] = None
    ):

    await wsmanager.subscribe(websocket, event, client_id, project_id, collection, document_id)
    try:
        while True:
            data = await websocket.receive_json()
            
            # if data['type'] == 'browser':
            #     wsmanager.receivers[client_id] = data['client']
            # elif data['type'] == 'response':
            #     for key, value in wsmanager.receivers.items():
            #         if client_id == value:
            #             client_ws = wsmanager.clients[key]
            #             await wsmanager.send(data['data'], client_ws)
            # await wsmanager.send(json.dumps({'message': 'Hello, client'}), websocket)
    except WebSocketDisconnect:
        wsmanager.disconnect(client_id)
    except Exception as e:
        logging.error(str(e)) 

@database_api.get('/')
@database_api.get('/{project_id}')
@database_api.get('/{project_id}/')
@database_api.get('/{project_id}/{collection}')
@database_api.get('/{project_id}/{collection}/')
@database_api.get('/{project_id}/{collection}/{document_id}')
@database_api.get('/{project_id}/{collection}/{document_id}/')
async def api_list_user_documents(
    request: Request, 
    user: Annotated[User, Depends(get_current_user)],
    project_id: str,
    collection: str,
    document_id: Optional[str] = None
    ) -> JSONResponse:
    
    response = {
        'status': 'success',
    }
    
    try:
        data = request.query_params._dict

        user_id = user.id
        params = {'user_id': user_id}
        params['name'] = collection
        params['project_id'] = project_id
            
        db = Database.find_one(params)
        
        if not db:
            raise NameError("Collection wasn't found")

        Collection.TABLE_NAME = db.collection_name
        
        _filter = data['filter'] if 'filter' in data.keys() else {}
        projection = data['columns'] if 'columns' in data.keys() else []
        
        if not document_id:
            results = Collection.find(_filter, projection)
            documents = [result.json() for result in results]
            response['data'] = documents
        else:
            document = Collection.find_one(_filter, projection)
            response['data'] = document.json()
            
    except Exception as e:
        logging.exception(e)
        response['status'] = 'error'
        response['message'] = 'Error fetching document(s)'
    
    return JSONResponse(response)

@database_api.post('/{project_id}')
@database_api.post('/{project_id}/')
async def api_create_user_database(
    request: Request, 
    user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[str] = None
):
    response = {
        'status': 'success',
    }
    try:
        form_data = await request.json()
        name = str(form_data['name'])
        
        if name and project_id:
            
            collection_name = f"{name}_{user.id}_{project_id}"
            data = {'name': name, 'collection_name': collection_name,
                    'project_id': project_id,'user_id': user.id}
            
            new_db = Database(**data)
            database_id = new_db.save().inserted_id     # type: ignore
            
            response['message'] = 'Successfully created database'
            response['data'] = { # type: ignore
                'id': str(database_id), 
                'collection_name': collection_name,
                'user_id': user.id,
                'project_id': project_id
            }
    except Exception as e:
        logging.exception(e)
        response['status'] = 'error'
        response['message'] = 'Error creating database'
    
    return JSONResponse(response)

@database_api.post('/{project_id}/{collection}')
@database_api.post('/{project_id}/{collection}/')
async def api_create_user_document(
    request: Request, 
    user: Annotated[User, Depends(get_current_user)],
    project_id: str,
    collection: str,
    background_task: BackgroundTasks
):
    response = {
        'status': 'success',
    }
    try:
        form_data = await request.json()
        documents = form_data['documents']
        
        db = Database.find_one({
            'project_id': project_id,
            'name': collection
        })
        
        if not db:
            raise NameError("Database was not found")
        
        Collection.TABLE_NAME = db.collection_name
        
        if isinstance(documents, list):
            results = Collection.insert_many(documents).inserted_ids
            response['data'] = [str(_id) for _id in results] # type: ignore
        else:
            document_id = Collection(**documents).save().inserted_id
            response['data'] = str(document_id)
            
        data = await get_collection(project_id, collection, response['data'], {})
        background_task.add_task(wsmanager.has_subscription, 'create', project_id, collection, response['data'], data)
        
    except NameError:
        response['status'] = 'error'
        response['message'] = f'Collection with name {collection} was not found'
        
    except Exception as e:
        logging.exception(e)
        response['status'] = 'error'
        response['message'] = 'Error creating database'
    
    return JSONResponse(response)

@database_api.put('/{project_id}/{collection}')
@database_api.put('/{project_id}/{collection}/')
@database_api.put('/{project_id}/{collection}/{document_id}')
@database_api.put('/{project_id}/{collection}/{document_id}/')
async def api_update_user_document(
    request: Request, 
    user: Annotated[User, Depends(get_current_user)],
    project_id: str,
    collection: str,
    background_task: BackgroundTasks,
    document_id: Optional[str] = None,
):
    response = {
        'status': 'success',
    }
    try:
        form_data = await request.json()
        document = form_data['document']
        
        db = Database.find_one({
            'user_id': user.id,
            'project_id': project_id,
            'name': collection
        })
        
        if not db:
            raise NameError("Document was not found")
        
        Collection.TABLE_NAME = db.collection_name
        _filter = form_data['filter'] if 'filter' in form_data.keys() else {}
        if document_id:
            _filter['id'] = document_id
        params = _filter.copy()
        Collection.update(_filter, document)        # type: ignore
        
        response['message'] = 'Document updated successfully'

        data = await get_collection(project_id, collection, document_id, params)
        if data:
            background_task.add_task(wsmanager.has_subscription, 'update', project_id, collection, data['id'], data)
        
    except NameError:
        response['status'] = 'error'
        response['message'] = f'Collection was not found'
        
    except Exception as e:
        logging.exception(e)
        response['status'] = 'error'
        response['message'] = 'Error creating database'
    
    return JSONResponse(response)

@database_api.delete('/{project_id}/{collection}')
@database_api.delete('/{project_id}/{collection}/')
async def api_delete_user_document(
    request: Request, 
    user: Annotated[User, Depends(get_current_user)],
    project_id: str,
    collection: str,
    background_task: BackgroundTasks,
    document_id: Optional[str] = None,
):
    response = {
        'status': 'success',
    }
    try:
        params = request.query_params._dict
        
        db = Database.find_one({
            'user_id': user.id,
            'project_id': project_id,
            'name': collection
        })
        
        if not db:
            raise NameError("Document was not found")
        
        Collection.TABLE_NAME = db.collection_name

        result = Collection.remove(params)
        response['message'] = 'Document deleted successfully'
        
        background_task.add_task(wsmanager.has_subscription, 'delete', project_id, collection, document_id, response)
        
    except NameError:
        response['status'] = 'error'
        response['message'] = f'Collection was not found'
        
    except Exception as e:
        logging.exception(e)
        response['status'] = 'error'
        response['message'] = 'Error creating database'
    
    return JSONResponse(response)
