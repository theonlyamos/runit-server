from flask import Blueprint, redirect, render_template, \
     request, session, url_for, flash, jsonify

from ..common.security import authenticate
from ..models import User

import os
from dotenv import load_dotenv

from runit import RunIt

load_dotenv()

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
HOMEDIR = os.path.realpath(os.path.join(CURRENT_PATH, '..'))
PROJECTS_DIR = os.path.realpath(os.path.join(CURRENT_PATH, '..', 'projects'))

public = Blueprint('public', __name__)

'''
@public.before_request
def initial():
    os.chdir(os.getenv('RUNIT_HOMEDIR'))
''' 

@public.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('account.index'))
    return render_template('login.html')

@public.get('/<string:project_id>/')
def project(project_id):
    if os.path.isdir(os.path.join(PROJECTS_DIR, project_id)):
        result = RunIt.start(project_id, 'index', os.path.join(PROJECTS_DIR, project_id))
        os.chdir(HOMEDIR)
        return result

    return RunIt.notfound()

@public.get('/<string:project_id>/<string:function>/')
def run(project_id, function):
    if os.path.isdir(os.path.join(PROJECTS_DIR, project_id)):
        result = RunIt.start(project_id, function, os.path.join(PROJECTS_DIR, project_id))
        os.chdir(HOMEDIR)
        return result

    return RunIt.notfound()

@public.route('/register/', methods=['GET', 'POST'])
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
        #print(user.inserted_id)
        flash('Registration Successful!', 'success')
        return redirect(url_for('public.index'))

    return render_template('register.html')

@public.post('/login/')
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    user = authenticate(email, password)
    if user:
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        return redirect(url_for('account.index'))
    else:
        flash('Invalid Login Credentials', 'danger')
    return redirect(url_for('public.index'))

