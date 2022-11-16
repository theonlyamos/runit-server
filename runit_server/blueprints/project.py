
import os
import sys
from time import sleep
from datetime import datetime

from flask import Blueprint, flash, render_template, redirect, \
    url_for, request, session
from bson.objectid import ObjectId
from dotenv import load_dotenv, dotenv_values, set_key

from ..models import Project
from ..models import User


from runit import RunIt

load_dotenv()
EXTENSIONS = {'python': '.py', 'php': '.php', 'javascript': '.js'}
LANGUAGE_ICONS = {'python': 'python', 'php': 'php',
                  'javascript': 'node-js', 'typescript': 'node-js'}
PROJECTS_DIR = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'projects'))

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
        funcs.append({'name': func, 'link': f"{os.getenv('RUNIT_PROTOCOL')}{os.getenv('RUNIT_SERVERNAME')}/{project_id}/{func}/"})
    
    os.chdir(old_curdir)
    project = Project.get(project_id)
    if project:
        return render_template('projects/details.html', page='projects',\
            project=project.json(), environs=environs, funcs=funcs)
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

@project.post('/')
def new_project():
    user_id = session['user_id']
    name = request.form.get('name')
    date = (datetime.utcnow()).strftime("%a %b %d %Y %H:%M:%S")
    project_id=None
    if name:
        project_id = Project(name, user_id).save()
        flash('Project created successfully', category='success')
    else:
        flash('Name of the project is required', category='danger')
    if project_id:
        return redirect(url_for('project.details', project_id=project_id))
    else:
        return redirect(url_for('project.new_project'))

@project.patch('/')
def update_project():
    user_id = session['user_id']
    return render_template('projects/index.html', page='projects', projects=[])

@project.delete('/')
def delete_project():
    user_id = session['user_id']
    return render_template('projects/index.html', page='projects', projects=[])
