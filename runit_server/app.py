#! python
import os
import logging
import asyncio
from sys import platform
from datetime import timedelta

from flask import (
    Flask, jsonify, redirect, render_template,
    url_for, session, request
)
from flask_jwt_extended import JWTManager
from flask_restful import Api
import socketio
from dotenv import load_dotenv, dotenv_values, find_dotenv, set_key

from odbms import DBMS
from .common import  Login, Account, ProjectById, ProjectRS, ProjectCloneRS, Document

from .models import Admin
from .models import Role
from .constants import RUNIT_WORKDIR

load_dotenv()
app = Flask(__name__)
app.secret_key =  "dsafidsalkjdsaofwpdsncdsfdsafdsafjhdkjsfndsfkjsldfdsfjaskljdf"
app.config['SERVER_NAME'] = os.getenv('RUNIT_SERVERNAME')
app.config["JWT_SECRET_KEY"] = "972a444fb071aa8ee83bf128808d255ec72e3a6b464a836b7d06254529c6"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
api = Api(app, prefix='/api')
jwt = JWTManager(app)
sio = socketio.Server(async_mode='threading')
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

REQUESTS = []

#api.add_resource(RunFunction, '/<string:project_id>/<string:function>/')
api.add_resource(Login, '/login/')
api.add_resource(Account, '/account/')
api.add_resource(ProjectRS, '/projects/')
api.add_resource(ProjectById, '/projects/<string:project_id>/')
api.add_resource(ProjectCloneRS, '/projects/clone/<string:project>/')
api.add_resource(Document, '/document/<string:project_id>/<string:collection>/')
#api.add_resource(RunFunction, '/<string:project_id>/<string:function>/')
#api.add_resource(FunctionRS, '/functions/')
#api.add_resource(FunctionById, '/functions/<string:function_id>/')


from .blueprints import public, account, functions, project, database, admin, setup

app.register_blueprint(setup)
app.register_blueprint(public)
app.register_blueprint(functions)
app.register_blueprint(account)
app.register_blueprint(project)
app.register_blueprint(database)
app.register_blueprint(admin)

WS_CONNECTIONS = {}
WS_DATA = {}
WS_IGNORED_PATHS = ['elementSelector.css.map']

def get_request_parameters():
        parameters = request.args.to_dict()
        if 'content-type' in request.headers.keys() and request.headers['content-type'] == "application/json":
            data = request.get_json()
            parameters = {**parameters, **data}
        parameters.pop('output_format', None)
        return list(parameters.values())

@sio.event
def connect(sid, environ):
    WS_CONNECTIONS[sid] = {}
    sio.emit('handshake', sid, room=sid)
    print('Connected to socketio ', sid)
    
@sio.event
def disconnect(sid):
    del WS_CONNECTIONS[sid]
    print('Disconnected from socketio ', sid)

@sio.event
def message(sid, data):
    print(data)

@sio.event
def handshake(sid, data):
    WS_CONNECTIONS[sid] = data
    
@sio.on('expose')
def expose(sid, payload):
    for key, value in WS_CONNECTIONS.items():
        if 'client' in value.keys() and value['client'] == sid:
            sio.emit('forward', payload, room=key)

@app.route('/e/<string:sid>')
@app.route('/e/<string:sid>/')
def expose(sid):
    parameters = get_request_parameters()
    response = {'function': 'index', 'parameters': parameters}
    sio.emit('exposed', response, room=sid)
    path = request.host
    return render_template('exposed.html', path=path)

@app.route('/e/<string:sid>/<string:func>')
@app.route('/e/<string:sid>/<string:func>/')
def expose_function(sid,func):
    if func not in WS_IGNORED_PATHS:
        parameters = get_request_parameters()
        response = {'function': func, 'parameters': parameters}
        sio.emit('exposed', response, room=sid)
    path = request.host
    return render_template('exposed.html', path=path)

@app.route('/complete_setup/')
def complete_setup():
    global app
    settings = dotenv_values(find_dotenv())
    
    print('--Setting up database')
    DBMS.initialize(settings['DBMS'], settings['DATABASE_HOST'], settings['DATABASE_PORT'],
                    settings['DATABASE_USERNAME'], settings['DATABASE_PASSWORD'], 
                    settings['DATABASE_NAME'])

    if 'SETUP' in settings.keys() and settings['SETUP'] == 'completed':
        if settings['DBMS'] == 'mysql':
            DBMS.Database.setup()
    
    print('[--] Database setup complete')
    if not Role.count():
        print('[#] Populating Roles')
        Role('developer', []).save()
        Role('superadmin', []).save()
        Role('subadmin', []).save()
    if not Admin.count():
        print('[#] Creating default administrator')
        Admin('Administrator', settings['adminusername'], settings['adminpassword'], 1).save()
    
    del settings['adminusername']
    del settings['adminpassword']

    env_file = find_dotenv()
    file = open(find_dotenv(), 'w')
    file.close()

    for key, value in settings.items():
        set_key(env_file, key, value)

    return redirect(url_for('public.index'))

@app.route('/get_app_requests/')
def get_parameters():
    global REQUESTS
    if len(REQUESTS) > 0:
        return jsonify(REQUESTS.pop())
    return jsonify({'GET': {}, 'POST': {}})

with app.app_context():
    if not os.path.exists(RUNIT_WORKDIR):
        os.mkdir(RUNIT_WORKDIR)
    
    if not (os.path.exists(os.path.join(RUNIT_WORKDIR, 'accounts'))):
        os.mkdir(os.path.join(RUNIT_WORKDIR, 'accounts'))
        
    if not (os.path.exists(os.path.join(RUNIT_WORKDIR, 'projects'))):
        os.mkdir(os.path.join(RUNIT_WORKDIR, 'projects'))

    settings = dotenv_values(find_dotenv())

    if 'SETUP' in settings.keys() and settings['SETUP'] == 'completed':
        DBMS.initialize(settings['DBMS'], settings['DATABASE_HOST'], settings['DATABASE_PORT'],
                    settings['DATABASE_USERNAME'], settings['DATABASE_PASSWORD'], 
                    settings['DATABASE_NAME'])
    
@app.before_request
def startup():
    # if not os.path.exists('.env'):
    #     with open('.env', 'wt') as file:
    #         file.close()
    #     return redirect(url_for('setup.index'))
    global REQUESTS
    if request.path != '/get_app_requests/':
        REQUESTS.insert(0, 
                        {'GET': request.args.to_dict(),
                        'POST': request.form.to_dict()})

if __name__ != '__main__':
   uvicorn_logger = logging.getLogger('uvicorn.error')
   app.logger.handlers = uvicorn_logger.handlers
   app.logger.setLevel(uvicorn_logger.level)