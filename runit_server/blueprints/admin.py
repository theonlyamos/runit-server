from datetime import datetime
import os

from flask import Blueprint, flash, render_template, redirect, \
    url_for, request, session
    
from bson.objectid import ObjectId
from dotenv import load_dotenv, dotenv_values, set_key, find_dotenv

from odbms import DBMS
from ..models import User
from ..models import Project
from ..models import Admin
from ..models import Function
from ..common import Utils


from runit import RunIt

EXTENSIONS = {'python': '.py', 'python3': '.py', 'php': '.php', 'javascript': '.js'}
LANGUAGE_ICONS = {'python': 'python', 'php': 'php',
                  'javascript': 'node-js', 'typescript': 'node-js'}

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
HOMEDIR = os.path.join(os.getenv('USERPROFILE', os.getenv('HOME')), 'RUNIT_WORKDIR')
PROJECTS_DIR = os.path.join(HOMEDIR, 'projects')

admin = Blueprint('admin', __name__, subdomain='admin', static_folder=os.path.join('..','static'))

@admin.before_request
def authorize():
    pass
    #if not 'admin_id' in session:
    #     return redirect(url_for('admin.loginpage'))

@admin.get('/login/')
def loginpage():
    return render_template('admin/login.html', title='Login')

@admin.route('/')
def index():
    if not 'admin_id' in session:
        return redirect(url_for('admin.loginpage'))
    
    admin = Admin.get(session['admin_id'])
    return render_template('admin/index.html', page='home', admin=admin)

@admin.post('/login/')
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    admin = Admin.get_by_username(username)
    #print(admin)
    if admin:
        if (Utils.check_hashed_password(password, admin.password)):
            session['admin_id'] = admin.id
            session['admin_name'] = admin.name
            session['admin_username'] = admin.username
            return redirect(url_for('admin.index'))
    flash('Invalid Login Credentials', 'danger')
    return redirect(url_for('admin.loginpage'))

@admin.get('/users/')
def users():
    users = User.all()
    view = request.args.get('view')
    view = view if view else 'grid'

    return render_template('admin/users/index.html', page='users',\
            users=users, view=view, icons=LANGUAGE_ICONS)

@admin.get('/users/<string:user_id>')
@admin.get('/users/<string:user_id>/')
def user(user_id):
    try:
        user = User.get(user_id)
        projects = Project.get_by_user(user.id)
        
        view = request.args.get('view')
        view = view if view else 'grid'
        
        return render_template('admin/users/details.html', page='users',\
            user=user.json(), projects=projects, view=view, icons=LANGUAGE_ICONS)
    except Exception as e:
        flash(str(e), 'danger')
        return redirect(url_for('admin.users'))

@admin.get('/projects')
@admin.get('/projects/')
def projects():
    projects = Project.all()
    return render_template('admin/projects/index.html', page='projects',\
            projects=projects, icons=LANGUAGE_ICONS)

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

@admin.get('/functions')
@admin.get('/functions/')
def functions():
    global EXTENSIONS
    global LANGUAGE_ICONS
    
    functions = Function.get_by_admin(session['admin_id'])
    projects = Project.get_by_admin(session['admin_id'])
    
    return render_template('functions/index.html', page='functions',\
            functions=functions, projects=projects,\
            languages=EXTENSIONS, icons=LANGUAGE_ICONS)

@admin.get('/databases')
@admin.get('/databases/')
def databases():
    global EXTENSIONS
    global LANGUAGE_ICONS
    
    functions = Function.get_by_admin(session['admin_id'])
    projects = Project.get_by_admin(session['admin_id'])
    
    return render_template('functions/index.html', page='functions',\
            functions=functions, projects=projects,\
            languages=EXTENSIONS, icons=LANGUAGE_ICONS)
        
@admin.route('/profile/')
def profile():
    return render_template('admin/profile.html', page='profile')

@admin.route('/logout/')
def logout():
    del session['admin_id']
    return redirect(url_for('admin.loginpage'))

@admin.route('/<page>')
def main(page):
    if (os.path.isdir(os.path.join('admins', page))):
        os.chdir(os.path.join('admins', page))
        result = RunIt.start()
        #os.chdir(os.path.join('..', '..'))
        return result
    else:
        return RunIt.notfound()
