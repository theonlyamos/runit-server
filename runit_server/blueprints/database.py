
import os
import sys
import json
from time import sleep
from datetime import datetime

from flask import Blueprint, flash, render_template, redirect, \
    url_for, request, session
from bson.objectid import ObjectId
from dotenv import load_dotenv, dotenv_values, set_key

from ..models import Database
from ..models import Collection
from ..models import Project
from ..models import User

from odbms import DBMS

from runit import RunIt

load_dotenv()

EXTENSIONS = {'python': '.py', 'php': '.php', 'javascript': '.js'}
LANGUAGE_ICONS = {'python': 'python', 'php': 'php',
                  'javascript': 'node-js', 'typescript': 'node-js'}

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
HOMEDIR = os.getenv('RUNIT_HOMEDIR', os.path.realpath(os.path.join(CURRENT_PATH, '..')))
PROJECTS_DIR = os.path.join(HOMEDIR, 'databases')

database = Blueprint('database', __name__, url_prefix='/databases', template_folder=os.path.join(HOMEDIR,'templates'), static_folder=os.path.join('..','static'))

@database.before_request
def authorize():
    if not 'user_id' in session:
        return redirect(url_for('public.index'))

@database.get('/')
def index():
    user_id = session['user_id']
    view = request.args.get('view')
    view = view if view else 'grid'
    databases = Database.get_by_user(user_id)
    for db in databases:
        Collection.TABLE_NAME = db.collection_name
        if Collection.count():
            stats = DBMS.Database.db.command('collstats', db.collection_name)
            if stats:
                db.stats = {'size': int(stats['storageSize'])/1024, 'count': stats['count']}
        
    projects = Project.get_by_user(user_id)
    
    return render_template('databases/index.html', page='databases',\
            databases=databases, projects=projects, view=view, icons=LANGUAGE_ICONS)

@database.post('/')
def create():
    user_id = session['user_id']
    
    name = request.form.get('name')
    project_id = request.form.get('project_id')
    
    if name and project_id:
        collection_name = f"{name}_{user_id}_{project_id}"
        data = {'name': name, 'collection_name': collection_name,
                'project_id': project_id,'user_id': user_id}
        
        new_db = Database(**data)
        results = new_db.save().inserted_id
                
        flash('Database Created Successfully.', category='success')
    else:
        flash('Missing required fields.', category='danger')
    return redirect(url_for('database.index'))

@database.get('/<database_id>/')
def details(database_id):
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
        
        return render_template('databases/details.html', 
                page='databases',\
                database=database.json(), 
                collections=result,
                inputTypes=schema_names_to_input_types)
    else:
        flash('Database does not exist', 'danger')
        return redirect(url_for('database.index'))

@database.post('/schema/<database_id>/')
def schema(database_id):
    try:
        data = request.form.to_dict()
        Database.update({'id': database_id}, {'schema': data})
        
        flash('Schema updated successfully', category='success')
    except Exception as e:
        flash(str(e), category='danger')
    return redirect(url_for('database.details', database_id=database_id))

@database.patch('/')
def update_database():
    user_id = session['user_id']
    return render_template('databases/index.html', page='databases', databases=[])

@database.post('/delete/<database_id>/')
def delete(database_id):
    user_id = session['user_id']
    db = Database.get(database_id)
    if db:
        result = Database.remove({'_id': database_id, 'user_id': user_id})
        flash('Database deleted successfully', category='success')
    else:
        flash('Database was not found. Operation not successful.', category='danger')
    return redirect(url_for('database.index'))
