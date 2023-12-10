import os
import logging
from time import sleep
from pathlib import Path
from datetime import datetime
from typing import Annotated, Optional, Dict

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request, \
    Depends, status, UploadFile
from dotenv import load_dotenv, dotenv_values, set_key

from ..core import flash, templates
from ..common import get_session, get_session_user
from ..models import Database
from ..models import Collection
from ..models import Project
from ..models import User

from odbms import DBMS

from ..constants import (
    RUNIT_HOMEDIR,
    LANGUAGE_TO_ICONS
)

load_dotenv()

DATABASE_INDEX = 'list_user_databases'

database = APIRouter(
    prefix="/databases",
    tags=["databases"],
    dependencies=[Depends(get_session)]
)

@database.get('/')
async def list_user_databases(request: Request, view: Optional[str] = None):
    user_id = request.session['user_id']
    
    if view:
        request.session['view'] = view
    elif 'view' not in request.session.keys():
        request.session['view'] = 'grid'
    
    databases = Database.get_by_user(user_id)
    for db in databases:
        Collection.TABLE_NAME = db.collection_name
        if Collection.count():
            stats = DBMS.Database.db.command('collstats', db.collection_name)   # type: ignore
            if stats:
                db.stats = {'size': int(stats['storageSize'])/1024, 'count': stats['count']}
        
    projects = Project.get_by_user(user_id)
    
    return templates.TemplateResponse('databases/index.html', context={
        'request': request, 'page': 'databases', 'databases': databases, 
        'projects': projects, 'icons': LANGUAGE_TO_ICONS})
    
@database.post('/')
async def create_user_database(
    request: Request,
    name: Annotated[str, Form()],
    project_id: Annotated[str, Form()]):
    
    user_id = request.session['user_id']
    
    if name and project_id:
        collection_name = f"{name}_{user_id}_{project_id}"
        data = {'name': name, 'collection_name': collection_name,
                'project_id': project_id,'user_id': user_id}
        
        new_db = Database(**data)
        results = new_db.save().inserted_id     # type: ignore
                
        flash(request, 'Database Created Successfully.', category='success')
    else:
        flash(request, 'Missing required fields.', category='danger')
    return RedirectResponse(request.url_for(DATABASE_INDEX), status_code=status.HTTP_303_SEE_OTHER)

@database.get('/{database_id}/')
async def user_database_details(request: Request, database_id):
    database = Database.get(database_id)
    
    if database:
        Collection.TABLE_NAME = database.collection_name
        collections = Collection.find({})
        
        result = []
        for col in collections:
            result.append(col.json())
        
        schema_names_to_input_types = {
            'str': 'text',
            'text': 'textarea',
            'int': 'number',
            'float': 'number',
            'bool': 'checkbox'
        }
        
        return templates.TemplateResponse('databases/details.html', context={
                'request': request, 'page':'databases',
                'database': database.json(), 'collections': result,
                'inputTypes': schema_names_to_input_types})
    else:
        flash(request, 'Database does not exist', 'danger')
        return RedirectResponse(request.url_for(DATABASE_INDEX))

@database.post('/schema/{database_id}/')
async def user_database_schema(request: Request, database_id: str):
    try:
        data = await request.form()
        Database.update({'id': database_id}, {'schema': data})
        
        flash(request, 'Schema updated successfully', category='success')
    except Exception as e:
        logging.error(str(e))
        flash(request, 'Error updating database schema', category='danger')
    return RedirectResponse(request.url_for('user_database_details', database_id=database_id))

@database.patch('/')
async def update_user_database(request: Request):
    user_id = request.session['user_id']
    return templates.TemplateResponse('databases/index.html', context={
        'request': request, 'page': 'databases', 'databases': []})

@database.get('/delete/{database_id}/')
async def delete_user_database(request: Request, database_id):
    user_id = request.session['user_id']
    db = Database.get(database_id)
    if db:
        result = Database.remove({'_id': database_id, 'user_id': user_id})
        flash(request, 'Database deleted successfully', category='success')
    else:
        flash(request, 'Database was not found. Operation not successful.', category='danger')
    return RedirectResponse(request.url_for(DATABASE_INDEX))
