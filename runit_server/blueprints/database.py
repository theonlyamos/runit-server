
import os
import sys
from time import sleep
from datetime import datetime

from flask import Blueprint, flash, render_template, redirect, \
    url_for, request, session
from bson.objectid import ObjectId
from dotenv import load_dotenv, dotenv_values, set_key

from ..models import Database
from ..models import Project
from ..models import User


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
    projects = Project.get_by_user(user_id)
    
    return render_template('databases/index.html', page='databases',\
            databases=databases, projects=projects, view=view, icons=LANGUAGE_ICONS)

@database.post('/')
def create():
    user_id = session['user_id']
    
    name = request.form.get('name')
    project_id = request.form.get('project_id')
    
    if name and project_id:
        data = {'name': name, 'user_id': user_id, 'project_id': project_id}
        
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
        return render_template('databases/details.html', page='databases',\
            database=database.json())
    else:
        flash('Database does not exist', 'danger')
        return redirect(url_for('database.index'))

@database.post('/<database_id>/')
def environ(database_id):
    env_file = os.path.realpath(os.path.join(PROJECTS_DIR, database_id, '.env'))
    file = open(env_file, 'w')
    file.close()
    
    for key, value in request.form.items():
        set_key(env_file, key, value)

    database = Database.get(database_id)
    flash('Environment variables updated successfully', category='success')
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
