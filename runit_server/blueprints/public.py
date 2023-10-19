from flask import Blueprint, redirect, render_template, \
     request, session, url_for, flash, jsonify
from flask_jwt_extended import create_access_token

from ..common.security import authenticate
from ..models import User
from ..models import Admin
from ..common import Utils

import os
from dotenv import load_dotenv, find_dotenv, dotenv_values

from runit import RunIt

from ..constants import (
    RUNIT_HOMEDIR,
    PROJECTS_DIR
)

load_dotenv()

REGISTER_HTML_TEMPLATE = 'register.html'

public = Blueprint('public', __name__)

'''
@public.before_request
def initial():
    os.chdir(os.getenv('RUNIT_HOMEDIR'))
''' 

@public.route('/')
@public.route('/login')
@public.route('/login/')
def index():
    settings = dotenv_values(find_dotenv())

    if settings is None or settings['SETUP'] != 'completed':
        return redirect(url_for('setup.index'))
    if 'user_id' in session:
        return redirect(url_for('account.index'))
    return render_template('login.html')

@public.get('/<string:project_id>')
@public.get('/<string:project_id>/')
def project(project_id):
    current_project_dir = os.path.join(PROJECTS_DIR, project_id)
    if os.path.isdir(current_project_dir):
        if not RunIt.is_private(project_id, current_project_dir):
            result = RunIt.start(project_id, 'index', current_project_dir)
            os.chdir(RUNIT_HOMEDIR)
            
            return result

    return RunIt.notfound()

@public.get('/<string:project_id>/<string:function>')
@public.get('/<string:project_id>/<string:function>/')
def run(project_id, function):
    current_project_dir = os.path.join(PROJECTS_DIR, project_id)
    if os.path.isdir(current_project_dir):
        if not RunIt.is_private(project_id, current_project_dir):
            result = RunIt.start(project_id, function, current_project_dir)
            os.chdir(RUNIT_HOMEDIR)
            return result

    return RunIt.notfound()

@public.route('/register/', methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            c_password = request.form.get('cpassword')
            if password != c_password:
                flash('Passwords do not match!', 'danger')
                return render_template(REGISTER_HTML_TEMPLATE)
            user = User.get_by_email(email)
            if user:
                flash('User is already Registered!', 'danger')
                return render_template(REGISTER_HTML_TEMPLATE)
            
            User(email, name, password).save()
            #print(user.inserted_id)
            flash('Registration Successful!', 'success')
            return redirect(url_for('public.index'))

        return render_template(REGISTER_HTML_TEMPLATE)
    except Exception as e:
        flash('Error during registration', 'danger')
        return render_template(REGISTER_HTML_TEMPLATE)

@public.post('/login/')
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    user = authenticate(email, password)
    if user:
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_email'] = user.email
        session['access_token'] = create_access_token(user.id)
        return redirect(url_for('account.index'))
    else:
        flash('Invalid Login Credentials', 'danger')
    return redirect(url_for('public.index'))

@public.get('/login/admin')
@public.get('/login/admin/')
def admin_loginpage():
    if 'admin_id' in session and session['admin_id']:
        return redirect(url_for('admin.index'))
    return render_template('admin/login.html', title='Admin Login')

@public.post('/login/admin')
@public.post('/login/admin/')
def admin_login():
    username = request.form.get('username')
    password = request.form.get('password')

    admin = Admin.get_by_username(username)
    if admin:
        if Utils.check_hashed_password(password, admin.password):
            session['admin_id'] = admin.id
            session['admin_name'] = admin.name
            session['admin_username'] = admin.username

            return redirect(url_for('admin.index'))
    flash('Invalid Login Credentials', 'danger')
    return redirect(url_for('public.admin_loginpage'))
