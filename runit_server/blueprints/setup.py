from flask import Blueprint, redirect, render_template, \
     request, session, url_for, flash, jsonify

from ..common.security import authenticate
from ..models import User

import os
from dotenv import load_dotenv, dotenv_values, set_key, find_dotenv

from runit import RunIt

load_dotenv()

setup = Blueprint('setup', __name__, url_prefix='/setup', static_folder=os.path.join('..','static'))

'''
Page for setting up runit-server
configurations.


@setup.before_request
def initial():
    os.chdir(os.getenv('RUNIT_HOMEDIR'))
''' 

@setup.get('/')
def index():
    env_file = find_dotenv()
    
    if env_file:
        settings = dotenv_values(env_file)
        if settings['SETUP'] == 'completed':
            return redirect(url_for('public.index'))
        
    return render_template('setup/index.html')

@setup.post('/')
def initsetup():
    env_file = find_dotenv()
    settings = dotenv_values(env_file)

    settings.update(request.form)

    for key, value in settings.items():
         set_key(env_file, key, value)
    set_key(env_file, 'SETUP', 'completed')
    
    flash('Setup completed', category='success')
    return redirect(url_for('complete_setup'))
