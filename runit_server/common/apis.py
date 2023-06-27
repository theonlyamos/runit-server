from odbms import DBMS, normalise
from flask import request, jsonify, send_from_directory
from flask_restful import Resource
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, get_jwt

from werkzeug.utils import secure_filename
from werkzeug.security import safe_join

from ..models import Function
from ..models import Project
from ..models import User
from ..models import Database
from ..models import Collection
from .security import authenticate

import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from threading import Thread

from runit import RunIt

load_dotenv()

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
WORKDIR =  os.path.join(os.getenv('USERPROFILE', os.getenv('HOME')), 'RUNIT_WORKDIR')
PROJECTS_DIR = os.path.join(WORKDIR, 'projects')

def stringifyObjectIds(model: object, properties: list)-> object:
    for property in properties:
        property._id = str(property._id)

class Login(Resource):
    '''
    Login Api
    '''

    def post(self):
        data = request.get_json()

        user = authenticate(data['email'], data['password'])
        if user:
            access_token = create_access_token(user.id)
            return {'status': 'success', 'access_token': access_token}
        return {'status': 'error', 'message': 'Invalid login credentials'}

class Account(Resource):
    '''
    Account Api
    '''

    @jwt_required()
    def get(self):
        user = User.get(get_jwt_identity())

        return user.json() if user else {'msg': 'Not Logged In!'}

class ProjectRS(Resource):
    '''
    Projects Api
    '''

    @jwt_required()
    def get(self):
        results = Project.get_by_user(get_jwt_identity())
        projects = [result.json() for result in results]

        return projects
    
    @jwt_required()
    def post(self)->dict:
        '''
        Api for publishing project

        @param project_id Project _id
        @param function Function Name
        @return Projects: dict Get all projects
        '''

        data = dict(request.form)
        file = request.files['file']
        
        result = {'status': 'success'}
        user = User.get(get_jwt_identity())

        
        if not '_id' in data.keys() or not len(data['_id']):
            del data['_id']
            project = Project(user.id, **data)
            project_id = project.save().inserted_id
            project_id = str(project_id)
            project.id = project_id
            homepage = f"{os.getenv('RUNIT_PROTOCOL')}{os.getenv('RUNIT_SERVERNAME')}/{project_id}/"
            project.update({'homepage': homepage})
            result['project_id'] = project_id
        else:
            project_id = data['_id']
            project = Project.get(data['_id'])
            del data['_id']
            project.update(data, {'id': project.id})

        if not os.path.exists(os.path.join(PROJECTS_DIR, project_id)):
            os.mkdir(os.path.join(PROJECTS_DIR, project_id))
            
        filepath = os.path.join(PROJECTS_DIR, project_id, secure_filename(file.filename))
        file.save(filepath)

        RunIt.extract_project(filepath)
        os.chdir(os.path.join(PROJECTS_DIR, project_id))
        #os.unlink(secure_filename(file.filename))
        runit = RunIt(**RunIt.load_config())
        Thread(target=runit.install_dependency_packages, args=()).start()
        
        runit._id = project_id
        runit.update_config()
        
        funcs = []
        for func in runit.get_functions():
            funcs.append(f"{request.scheme}://{os.getenv('RUNIT_SERVERNAME')}/{project_id}/{func}/")
        
        result['functions'] = funcs
        result['homepage'] = funcs[0]
        return result

class ProjectCloneRS(Resource):
    '''
    Projects Api
    '''

    @jwt_required()
    def get(self, project):
        '''
        Clone project from terminal
        
        @param project_id str ID of the project to clone
        @return Compressed file of files in project directory
        '''
        global PROJECTS_DIR
        
        try:
            project = Project.find_one({'name': project, 'user_id': get_jwt_identity()})
            
            if project:
                if not os.path.exists(os.path.join(PROJECTS_DIR, project.id)):
                    raise Exception('Project not found!')
                    
                os.chdir(os.path.join(PROJECTS_DIR, project.id))
                config = RunIt.load_config()
                
                if not config:
                    raise FileNotFoundError
                
                project = RunIt(**config)
                filename = project.compress()
                # os.chdir(WORKDIR)
                
                return send_from_directory(safe_join(PROJECTS_DIR, project._id), filename, as_attachment=True)
            else:
                return jsonify({'status': 'error', 'msg': 'Project does not exist'})
        except Exception as e:
            return jsonify({'status': 'error', 'msg': str(e)})

class ProjectById(Resource):
    '''
    Project Api
    '''

    @jwt_required()
    def get(self, project_id):
        project = Project.get(project_id)
    
        return project.json() if project else None
    
    @jwt_required()
    def post(self, project_id):
        data = dict(request.get_json())
        
        project = Project.get(project_id)
        if project:
            result =  Project.update(data)
            return {'status': 'success', 'message': 'Operation Successful!'}

        return {'status': 'error', 'message': 'Operation unsuccessful'}
    
    @jwt_required()
    def delete(self, project_id):
        project = Project.get(project_id)
    
        return project
    
class FunctionRS(Resource):
    '''
    Functions Api
    '''

    @jwt_required()
    def get(self):
        results = Function.get_by_user(get_jwt_identity())
        functions = [result.json() for result in results]

        return functions

class FunctionById(Resource):
    '''
    Functions Api
    '''

    @jwt_required()
    def get(self, function_id):
        function = Function.get(function_id)

        if function:
            function = function.json()
            project = Project.get(function['project_id'])
            function['project'] = project.json() if project else project
        return function

class RunFunction(Resource):
    '''
    Functions Api
    '''

    @jwt_required()
    def get(self, project_id, function)-> dict:
        '''Get Function Details
        
        @param project_id _Id of project
        @param function Name of the function
        @return Function Details
        '''
        function = Function.get(function)

        if function:
            function = function.json()
            project = Project.get(function['project_id'])
            function['project'] = project.json() if project else project
        return function

class Document(Resource):
    '''
    Api for manipulating documents (crud)
    '''

    @jwt_required()
    def post(self, project_id, collection):
        '''
        Endpoint for CRUD actions on documents

        @param project_id Project ID
        @param collection Collection Name
        @return Documents Documents from collection
        '''

        try:
            data = request.get_json()

            user_id = get_jwt_identity()
            db = Database.find_one({'user_id': user_id, 'name': collection})
            
            if not db:
                raise NameError("Collection wasn't found")

            Collection.TABLE_NAME = db.collection_name
            
            if not 'function' in data.keys():
                raise SyntaxError('No database function to run')
            
            function = data['function']

            if function == 'all' or function == 'find' or function == 'find_many':
                projection = {}
                for item in data['projection']:
                    projection[item] = 1
                results = Collection.find(data['_filter'], projection)

            elif function == 'find_one':
                projection = {}
                for item in data['projection']:
                    projection[item] = 1
                
                results = Collection.find_one(data['_filter'], projection)

            elif function == 'insert':
                results = Collection(**data['document']).save()
            
            elif function == 'insert_many':
                results = Collection.insert_many(data['documents'])

            elif function == 'update':
                results = Collection.update(data['_filter'], data['update'])
            
            elif function == 'count':
                results = Collection.count(data['_filter'])
            
            if function == 'find_many' or function == 'find' or function == 'all':
                return jsonify([result.json() for result in results])
            elif function == 'find_one':
                return jsonify(results.json())
            elif function == 'insert':
                return jsonify({'status': 'success', 'msg': str(results.inserted_id)})
            elif function == 'count':
                return jsonify({'count': results})
            else:
                return jsonify({'status': 'success', 'msg': 'Operation successful'})

        except Exception as e:
            return jsonify({'status': 'error', 'msg': str(e)})
   
