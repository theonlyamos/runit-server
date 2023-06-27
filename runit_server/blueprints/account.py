from datetime import datetime
import os
from sys import prefix

from flask import Blueprint, flash, render_template, redirect, \
    url_for, request, session
from bson.objectid import ObjectId
from dotenv import load_dotenv

from odbms import DBMS
from ..models import Project
from ..models import User
from ..models import Function

from runit import RunIt

load_dotenv()

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
HOMEDIR = os.getenv('RUNIT_HOMEDIR', os.path.realpath(os.path.join(CURRENT_PATH, '..')))
PROJECTS_DIR = os.path.join(HOMEDIR, 'projects')

EXTENSIONS = {'python': '.py', 'python3': '.py', 'php': '.php', 'javascript': '.js'}
LANGUAGE_ICONS = {'python': 'python', 'python3': 'python', 'php': 'php',
                  'javascript': 'node-js', 'typescript': 'node-js'}

account = Blueprint('account', __name__, url_prefix='/account', static_folder=os.path.join('..','static'))

@account.before_request
def authorize():
    if not 'user_id' in session:
        return redirect(url_for('public.index'))

@account.route('/')
def index():
    user = User.get(session['user_id'])
    return render_template('account/home.html', page='home', user=user)

@account.route('/projects/', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def projects():
    user_id = session['user_id']
    if request.method == 'GET':
        projects = [project for project in Project.get_by_user(user_id) if project in os.listdir(PROJECTS_DIR)]
        return render_template('projects/index.html', page='projects',\
             projects=projects)

    elif request.method == 'POST':
        name = request.form.get('name')
        date = (datetime.utcnow()).strftime("%a %b %d %Y %H:%M:%S")
        if name:
            Project(name, user_id).save()
            flash('Project created successfully', category='success')
        else:
            flash('Name of the project is required', category='danger')
        return redirect(url_for('account.projects'))
    
    elif request.method == 'PATCH':
        return render_template('projects/index.html', page='projects', projects=[])
    elif request.method == 'DELETE':
        return render_template('projects/index.html', page='projects', projects=[])

@account.get('/functions')
@account.get('/functions/')
def functions():
    global EXTENSIONS
    global LANGUAGE_ICONS

    functions = Function.get_by_user(session['user_id'])
    projects = Project.get_by_user(session['user_id'])
    
    return render_template('functions/index.html', page='functions',\
            functions=functions, projects=projects,\
            languages=EXTENSIONS, icons=LANGUAGE_ICONS)

@account.get('/databases')
@account.get('/databases/')
def databases():
    global EXTENSIONS
    global LANGUAGE_ICONS

    functions = Function.get_by_user(session['user_id'])
    projects = Project.get_by_user(session['user_id'])
    
    return render_template('functions/index.html', page='functions',\
            functions=functions, projects=projects,\
            languages=EXTENSIONS, icons=LANGUAGE_ICONS)
 
@account.get('/profile')
@account.get('/profile/')
def profile():
    try:
        user_id = session['user_id']
        user = User.get(user_id)
        
        view = request.args.get('view')
        view = view if view else 'grid'
        
        return render_template('account/profile.html', page='profile',\
            user=user.json())
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('account.index'))

@account.route('/logout/')
def logout():
    del session['user_id']
    return redirect(url_for('public.index'))

@account.route('/<page>')
def main(page):
    if (os.path.isdir(os.path.join('accounts', page))):
        os.chdir(os.path.join('accounts', page))
        result = RunIt.start()
        #os.chdir(os.path.join('..', '..'))
        return result
    else:
        return RunIt.notfound()
