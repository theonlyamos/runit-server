from flask import Blueprint, redirect, render_template, \
     request, session, url_for, flash, jsonify

from ..common.security import authenticate
from ..models import User

import os
from dotenv import load_dotenv, dotenv_values, set_key, find_dotenv

from runit import RunIt

load_dotenv()

PROJECTS_DIR = os.path.realpath(os.path.join(os.getenv('RUNIT_HOMEDIR'), 'projects'))

setup = Blueprint('setup', __name__, url_prefix='/setup', static_folder=os.path.join('..','static'))

'''
@setup.before_request
def initial():
    os.chdir(os.getenv('RUNIT_HOMEDIR'))
''' 

@setup.get('/')
def index():
    return render_template('setup/index.html')

@setup.post('/')
def initsetup():
    env_file = find_dotenv()
    settings = dotenv_values(env_file)

    settings.update(request.form)

    for key, value in settings.items():
         set_key(env_file, key, value)
    set_key(env_file, 'setup', 'completed')
    
    flash('Setup completed', category='success')
    return redirect(url_for('complete_setup'))

@setup.get('/<string:project_id>/')
def project(project_id):
    if os.path.isdir(os.path.join(PROJECTS_DIR, project_id)):
        result = RunIt.start(project_id, 'index')
        os.chdir(os.getenv('RUNIT_HOMEDIR'))
        return jsonify(result)

    return RunIt.notfound()

@setup.get('/<string:project_id>/<string:function>/')
def run(project_id, function):
    if os.path.isdir(os.path.join(PROJECTS_DIR, project_id)):
        result = RunIt.start(project_id, function)
        os.chdir(os.getenv('RUNIT_HOMEDIR'))
        return jsonify(result)

    return RunIt.notfound()

@setup.route('/register/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        c_password = request.form.get('cpassword')
        if password != c_password:
            flash('Passwords do not match!', 'danger')
            return render_template('register.html')
        user = User.get_by_email(email)
        if user:
            flash('User is already Registered!', 'danger')
            return render_template('register.html')
        
        user = User(email, name, password).save()
        print(user.inserted_id)
        flash('Registration Successful!', 'success')
        return redirect(url_for('setup.index'))

    return render_template('register.html')

@setup.post('/login/')
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    user = authenticate(email, password)
    if user:
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        return redirect(url_for('setup.index'))
    else:
        flash('Invalid Login Credentials', 'danger')
    return redirect(url_for('setup.index'))
