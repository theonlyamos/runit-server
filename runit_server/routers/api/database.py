import ast
import json
import logging
from typing import Annotated, Dict, List, Optional, Union
from urllib.parse import parse_qs, unquote

from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import APIRouter, BackgroundTasks, Request, Depends, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv

from ...core import WSConnectionManager
from ...common import get_current_user
from ...models import User
from ...models import Database
from ...models import Collection
from ...constants import SUBSCRIPTION_EVENTS
from odbms import DBMS
from odbms.model import Model

from runit import RunIt

PROJECT_404_ERROR = 'Project does not exist'

load_dotenv()

database_api = APIRouter(
    prefix="/documents",
    tags=["database api"],
    dependencies=[Depends(get_current_user)],
)

wsmanager = WSConnectionManager()

async def get_collection(project_id: str, collection: str, document_id: Union[list, str], _filter: dict):
    db = await Database.find_one({
        'project_id': project_id,
        'name': collection
    })
    if not db:
        return {}

    Collection.TABLE_NAME = db.collection_name  # type: ignore[assignment]
    if isinstance(document_id, list):
        results = []
        for _id in document_id:
            flt = {**_filter, 'id': _id}
            document = await Collection.find_one(flt)
            results.append(document.json() if document else {})
        return results
    elif document_id:
        _filter['id'] = document_id

    document = await Collection.find_one(_filter)

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
    
    response: dict = {
        'status': 'success',
    }

    try:
        data = request.query_params._dict
        user_id = user.id
        params = {'user_id': user_id}
        params['name'] = collection
        params['project_id'] = project_id

        db = await Database.find_one(params)

        if not db:
            raise NameError("Collection wasn't found")

        Collection.TABLE_NAME = db.collection_name  # type: ignore[assignment]

        # Parse filter: support both 'filter' and '_filter' params, URL-encoded or plain
        raw_filter = data.get('filter') or data.get('_filter')
        if raw_filter:
            decoded = unquote(raw_filter) if '%' in str(raw_filter) else raw_filter
            try:
                _filter = json.loads(decoded)
            except json.JSONDecodeError:
                _filter = ast.literal_eval(decoded)
        else:
            _filter = {}
        raw_projection = json.loads(data['projection']) if 'projection' in data.keys() else []
        projection_keys: List = list(raw_projection.keys()) if isinstance(raw_projection, dict) else raw_projection

        if not document_id:
            results = await Collection.find(_filter)
            documents = [result.json() for result in results]
            response['data'] = documents
        else:
            document = await Collection.find_one({'id': document_id})
            json_document = document.json() if document else {}
            if projection_keys:
                json_document = {k: json_document[k] for k in projection_keys if k in json_document}

            response['data'] = json_document
            
    except Exception as e:
        logging.exception(e)
        response['status'] = 'error'
        response['message'] = 'Error fetching documents'
    finally:
        return JSONResponse(response)

@database_api.post('/{project_id}')
@database_api.post('/{project_id}/')
async def api_create_user_database(
    request: Request, 
    user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[str] = None
):
    response: dict = {
        'status': 'success',
    }
    try:
        form_data = await request.json()
        name = str(form_data['name'])
        
        if name and project_id:

            collection_name = f"{name}_{user.id}_{project_id}"
            data = {'name': name, 'collection_name': collection_name,
                    'project_id': project_id, 'user_id': user.id}

            new_db = Database(**data)
            await new_db.save()
            database_id = new_db.id

            Collection.TABLE_NAME = collection_name  # type: ignore[assignment]
            Collection.create_table()  # type: ignore[misc]

            response['message'] = 'Successfully created database'
            response['data'] = {
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
    response: dict = {
        'status': 'success',
    }
    try:
        form_data = await request.json()
        documents = form_data['documents']

        db = await Database.find_one({
            'project_id': project_id,
            'name': collection
        })

        if not db:
            raise NameError("Database was not found")

        Collection.TABLE_NAME = db.collection_name  # type: ignore[assignment]

        if isinstance(documents, list):
            normalised = [Model.normalise(doc, 'params') for doc in documents]
            db_conn = DBMS.Database
            if db_conn is not None:
                results = await db_conn.insert_many(Collection.table_name(), normalised)  # type: ignore[union-attr]
                response['data'] = [str(oid) for oid in (results if isinstance(results, (list, tuple)) else [results])]
            else:
                raise RuntimeError("Database not initialized")
        else:
            doc = Collection(**documents)
            await doc.save()
            response['data'] = str(doc.id)

        doc_ids = response['data']
        data = await get_collection(project_id, collection, doc_ids if isinstance(doc_ids, (list, str)) else str(doc_ids), {})
        background_task.add_task(wsmanager.has_subscription, 'create', project_id, collection, doc_ids, data)  # type: ignore[arg-type]
        
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
    response: dict = {
        'status': 'success',
    }
    try:
        form_data = await request.json()
        document = form_data['document']

        db = await Database.find_one({
            'user_id': user.id,
            'project_id': project_id,
            'name': collection
        })

        if not db:
            raise NameError("Document was not found")

        Collection.TABLE_NAME = db.collection_name  # type: ignore[assignment]
        _filter = form_data['filter'] if 'filter' in form_data.keys() else {}
        if document_id:
            _filter['id'] = document_id
        params = _filter.copy()
        await Collection.update_one(_filter, document)        # type: ignore
        
        response['message'] = 'Document updated successfully'

        data = await get_collection(project_id, collection, document_id or '', params)
        if isinstance(data, dict) and data:
            background_task.add_task(wsmanager.has_subscription, 'update', project_id, collection, data.get('id', document_id or ''), data)
        
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
    response: dict = {
        'status': 'success',
    }
    try:
        params = request.query_params._dict

        db = await Database.find_one({
            'user_id': user.id,
            'project_id': project_id,
            'name': collection
        })

        if not db:
            raise NameError("Document was not found")

        Collection.TABLE_NAME = db.collection_name  # type: ignore[assignment]

        if DBMS.Database:
            params_normalised = Model.normalise(params, 'params')
            result = await DBMS.Database.delete_one(Collection.table_name(), params_normalised)
        else:
            raise RuntimeError("Database not initialized")
        response['message'] = 'Document deleted successfully'

        background_task.add_task(wsmanager.has_subscription, 'delete', project_id, collection, document_id or '', response)
        
    except NameError:
        response['status'] = 'error'
        response['message'] = f'Collection was not found'
        
    except Exception as e:
        logging.exception(e)
        response['status'] = 'error'
        response['message'] = 'Error creating database'
    
    return JSONResponse(response)
