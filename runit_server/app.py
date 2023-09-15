#! python
import os
import logging
from sys import platform
from datetime import timedelta

from flask import Flask, jsonify, redirect, url_for, session, request
from flask_jwt_extended import JWTManager
from flask_restful import Api
from dotenv import load_dotenv, dotenv_values, find_dotenv, set_key

from odbms import DBMS
from .common import  Login, Account, ProjectById, ProjectRS, ProjectCloneRS, Document

from .models import Admin
from .models import Role
from .constants import RUNIT_WORKDIR

app = Flask(__name__)
api = Api(app, prefix='/api')

load_dotenv()

app.secret_key =  "dsafidsalkjdsaofwpdsncdsfdsafdsafjhdkjsfndsfkjsldfdsfjaskljdf"
app.config['SERVER_NAME'] = os.getenv('RUNIT_SERVERNAME')
app.config["JWT_SECRET_KEY"] = "972a444fb071aa8ee83bf128808d255ec72e3a6b464a836b7d06254529c6"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)

jwt = JWTManager(app)

if __name__ != '__main__':
   uvicorn_logger = logging.getLogger('uvicorn.error')
   app.logger.handlers = uvicorn_logger.handlers
   app.logger.setLevel(uvicorn_logger.level)

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
app.register_blueprint(admin, subdomain='admin')

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
