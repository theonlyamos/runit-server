from datetime import datetime
import os

from flask import Blueprint, flash, render_template, redirect, \
    url_for, request, session
    
from bson.objectid import ObjectId
from dotenv import dotenv_values

from odbms import DBMS
from ..models import User
from ..models import Project
from ..models import Admin
from ..models import Function
from ..models import Database
from ..models import Collection

from ..constants import (
    PROJECTS_DIR,
    EXTENSIONS,
    LANGUAGE_TO_ICONS
)

ADMIN_LOGIN_PAGE = 'public.admin_loginpage'
ADMIN_DATABASE_INDEX = 'admin.databases'

from runit import RunIt

admin = Blueprint('admin', __name__, url_prefix='/admin', static_folder=os.path.join('..','static'))

@admin.before_request
def authorize():
    if not 'admin_id' in session:
        return redirect(url_for(ADMIN_LOGIN_PAGE))

@admin.route('/')
def index():
    admin = Admin.get(session['admin_id'])
    return render_template('admin/index.html', page='home', admin=admin)

@admin.get('/users/')
def users():
    users = User.all()
    view = request.args.get('view')
    view = view if view else 'grid'

    return render_template('admin/users/index.html', page='users',\
            users=users, view=view, icons=LANGUAGE_TO_ICONS)

@admin.get('/users/<string:user_id>')
@admin.get('/users/<string:user_id>/')
def user(user_id):
    try:
        user = User.get(user_id)
        projects = Project.get_by_user(user.id)
        
        view = request.args.get('view')
        view = view if view else 'grid'
        
        return render_template('admin/users/details.html', page='users',\
            user=user.json(), projects=projects, view=view, icons=LANGUAGE_TO_ICONS)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.users'))

@admin.get('/projects')
@admin.get('/projects/')
def projects():
    projects = Project.all()
    return render_template('admin/projects/index.html', page='projects',\
            projects=projects, icons=LANGUAGE_TO_ICONS)

@admin.get('/projects/<project_id>')
@admin.get('/projects/<project_id>/')
def project(project_id):
    old_curdir = os.curdir
    
    os.chdir(os.path.realpath(os.path.join(PROJECTS_DIR, project_id)))
    if not os.path.isfile('.env'):
        file = open('.env', 'w')
        file.close()

    environs = dotenv_values('.env')

    runit = RunIt(**RunIt.load_config())

    funcs = []
    for func in runit.get_functions():
        funcs.append({'name': func, 'link': f"/{project_id}/{func}/"})
    
    os.chdir(old_curdir)
    project = Project.get(project_id)
    if project:
        return render_template('admin/projects/details.html', page='projects',\
            project=project.json(), environs=environs, funcs=funcs)
    else:
        flash('Project does not exist', 'danger')
        return redirect(url_for('project.index'))

@admin.get('/databases')
@admin.get('/databases/')
def databases():
    global EXTENSIONS
    global LANGUAGE_TO_ICONS

    view = request.args.get('view')
    view = view if view else 'grid'
    databases = Database.all()
    for db in databases:
        Collection.TABLE_NAME = db.collection_name
        if Collection.count():
            stats = DBMS.Database.db.command('collstats', db.collection_name)
            if stats:
                db.stats = {'size': int(stats['storageSize'])/1024, 'count': stats['count']}
        
    projects = Project.all()
    
    return render_template('admin/databases/index.html', page='databases',\
            databases=databases, projects=projects, view=view, icons=LANGUAGE_TO_ICONS)

@admin.get('/databases/<database_id>')
@admin.get('/databases/<database_id>/')
def database(database_id):
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
        return redirect(url_for(ADMIN_DATABASE_INDEX))
    
@admin.post('/databases')
@admin.post('/databases/')
def create_database():
    name = request.form.get('name')
    project_id = request.form.get('project_id')
    project = Project.get(project_id)
    
    if name and project_id:
        collection_name = f"{name}_{project.user_id}_{project_id}"
        data = {'name': name, 'collection_name': collection_name,
                'project_id': project_id,'user_id': project.user_id}
        print(data)
        new_db = Database(**data)
        results = new_db.save().inserted_id
                
        flash('Database Created Successfully.', category='success')
    else:
        flash('Missing required fields.', category='danger')
    return redirect(url_for(ADMIN_DATABASE_INDEX))

@admin.post('/schema/<database_id>/')
def database_schema(database_id):
    try:
        data = request.form.to_dict()
        Database.update({'id': database_id}, {'schema': data})
        
        flash('Schema updated successfully', category='success')
    except Exception as e:
        flash(str(e), category='danger')
    return redirect(url_for('admin.database', database_id=database_id))

@admin.patch('/databases')
@admin.patch('/databases/')
def update_database():
    return render_template('admin/databases/index.html', page='databases', databases=[])

@admin.post('/delete/<database_id>/')
def delete_database(database_id):
    db = Database.get(database_id)
    if db:
        result = Database.remove({'_id': database_id})
        flash('Database deleted successfully', category='success')
    else:
        flash('Database was not found. Operation not successful.', category='danger')
    return redirect(url_for(ADMIN_DATABASE_INDEX))

@admin.route('/profile/')
def profile():
    return render_template('admin/profile.html', page='profile')

@admin.route('/logout/')
def logout():
    del session['admin_id']
    return redirect(url_for(ADMIN_LOGIN_PAGE))

@admin.route('/<page>')
def main(page):
    if (os.path.isdir(os.path.join('admins', page))):
        os.chdir(os.path.join('admins', page))
        result = RunIt.start()
        #os.chdir(os.path.join('..', '..'))
        return result
    else:
        return RunIt.notfound()
