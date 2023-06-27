
import os
import sys
from time import sleep
from datetime import datetime

from flask import Blueprint, flash, render_template, redirect, \
    url_for, request, session, jsonify
from bson.objectid import ObjectId
from dotenv import load_dotenv, dotenv_values, set_key

from ..models import Database
from ..models import Project
from ..models import User

from runit import RunIt, TEMPLATES_FOLDER

load_dotenv()

EXTENSIONS = {'python': '.py', 'php': '.php', 'javascript': '.js'}

LANGUAGE_ICONS = {'python': 'fab fa-python', 
                  'php': 'fab fa-php',
                  'javascript': 'fab fa-node-js',
                  'multi': 'fas fa-project-diagram'}
LANGUAGE_TO_RUNTIME = {'python': 'python', 'php': 'php',
                  'javascript': 'node'}

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
HOMEDIR =  os.path.join(os.getenv('USERPROFILE', os.getenv('HOME')), 'RUNIT_WORKDIR')
PROJECTS_DIR = os.path.join(HOMEDIR, 'projects')

project = Blueprint('project', __name__, url_prefix='/projects', template_folder=os.path.join('..','..','templates'), static_folder=os.path.join('..','static'))

@project.before_request
def authorize():
    if not 'user_id' in session:
        return redirect(url_for('public.index'))

@project.get('/')
def index():
    user_id = session['user_id']
    view = request.args.get('view')
    view = view if view else 'grid'
    projects = Project.get_by_user(user_id)
    
    return render_template('projects/index.html', page='projects',\
            projects=projects, view=view, icons=LANGUAGE_ICONS)

@project.post('/')
def create():
    user_id = session['user_id']
    user = User.get(user_id)
    
    name = request.form.get('name')
    language = request.form.get('language')
    description = request.form.get('description')
    
    if name and language:
        # name = RunIt.set_project_name(args.name)
        # if RunIt.exists(name):
        #    print(f'{name} project already Exists')
        #    sys.exit(1)
        
        config = {}
        config['name'] = name
        config['language'] = language
        config['runtime'] = LANGUAGE_TO_RUNTIME[language]
        config['description'] = description
        config['author'] = {}
        config['author']['name'] = user.name
        config['author']['email'] = user.email
        
        project = Project(user_id, **config)
        project_id = project.save().inserted_id
        project_id = str(project_id)
        project.id = project_id
        
        homepage = f"{request.base_url}/{project_id}/"
        project.update({'homepage': homepage})

        config['_id'] = project_id
        config['homepage'] = homepage
        
        os.chdir(PROJECTS_DIR)
        
        config['name'] = project_id
        new_runit = RunIt(**config)
        
        new_runit._id = project_id
        new_runit.name = name
        
        os.chdir(os.path.join(PROJECTS_DIR, project_id))
        new_runit.update_config()
        
        os.chdir(HOMEDIR)
        
        if (request.form.get('database')):
            # Create database for project
            new_db = Database(name+'_db', user_id, project_id).save()
        
        flash('Project Created Successfully.', category='success')
    else:
        flash('Missing required fields.', category='danger')
    return redirect(url_for('project.index'))

@project.get('/<project_id>/')
def details(project_id):
    old_curdir = os.curdir
    user_id = session['user_id']
    
    os.chdir(os.path.realpath(os.path.join(PROJECTS_DIR, project_id)))
    if not os.path.isfile('.env'):
        file = open('.env', 'w')
        file.close()

    environs = dotenv_values('.env')

    runit = RunIt(**RunIt.load_config())

    funcs = []
    for func in runit.get_functions():
        funcs.append({'name': func})
    
    os.chdir(old_curdir)
    project = Project.get(project_id)
    project = project.json()
    del project['author']
    project['functions'] = len(funcs)
    if project:
        return render_template('projects/details.html', page='projects',\
            project=project, environs=environs, funcs=funcs)
    else:
        flash('Project does not exist', 'danger')
        return redirect(url_for('project.index'))

@project.post('/<project_id>/')
def environ(project_id):
    env_file = os.path.realpath(os.path.join(PROJECTS_DIR, project_id, '.env'))
    file = open(env_file, 'w')
    file.close()
    
    for key, value in request.form.items():
        set_key(env_file, key, value)

    project = Project.get(project_id)
    flash('Environment variables updated successfully', category='success')
    return redirect(url_for('project.details', project_id=project_id))

@project.patch('/')
def update_project():
    user_id = session['user_id']
    return render_template('projects/index.html', page='projects', projects=[])

@project.post('/delete/<project_id>/')
def delete(project_id):
    try:
        user_id = session['user_id']
        project = Project.get(project_id)
        if project:
            result = Project.remove({'_id': project_id, 'user_id': user_id})
            os.chdir(PROJECTS_DIR)
            os.remove(project_id)
            os.chdir(HOMEDIR)
            flash('Project deleted successfully', category='success')
        else:
            flash('Project was not found. Operation not successful.', category='danger')
    except:
        flash('Error deleting project. Try again later.', category='danger')
        return redirect(url_for('project.index'))

@project.get('/files/<project_id>/')
def files(project_id):
    old_curdir = os.curdir
    user_id = session['user_id']
    
    os.chdir(os.path.realpath(os.path.join(PROJECTS_DIR, project_id)))
    files = []
    for file in os.listdir(os.curdir):
        if file != '404.html':
            filepath = os.path.join(os.curdir, file)
            files.append({'name': file, 'isfile': True if os.path.isfile(filepath) else False})
    
    os.chdir(old_curdir)
    project = Project.get(project_id)
    project = project.json()
    if not project:
        return jsonify({'status': 'error', 'message': 'Project does not exist'})
    
    return jsonify({'status': 'success', 'files': files, 'project': project})

@project.get('/editor/<project_id>/')
def get_file(project_id):
    old_curdir = os.curdir
    user_id = session['user_id']
    filename = request.args.get('file')
    os.chdir(os.path.realpath(os.path.join(PROJECTS_DIR, project_id)))
    filepath = os.path.join(os.curdir, filename)
    
    if not filename or not os.path.exists(filepath):
        os.chdir(old_curdir)
        return jsonify({'status': 'error', 'message': 'Invalid File Path'})
    
    content = ''
    with open(filepath, 'rt') as fd:
        content = fd.read()
    
    os.chdir(old_curdir)

    return jsonify({'status': 'success', 'content': content})

@project.put('/editor/<project_id>/')
def update_file(project_id):
    old_curdir = os.curdir
    user_id = session['user_id']
    filename = request.args.get('file')
    data = request.get_json()

    os.chdir(os.path.realpath(os.path.join(PROJECTS_DIR, project_id)))
    filepath = os.path.join(os.curdir, filename)
    
    if not filename or not os.path.exists(filepath):
        os.chdir(old_curdir)
        return jsonify({'status': 'error', 'message': 'Invalid File Path'})
    
    content = data['data']
    with open(filepath, 'wt') as fd:
        fd.write(content)
    
    os.chdir(old_curdir)

    return jsonify({'status': 'success', 'message': 'File Saved'})
