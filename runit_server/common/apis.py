from odbms import DBMS, normalise
from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, get_jwt

from werkzeug.utils import secure_filename

from ..models import Function
from ..models import Project
from ..models import User
from .security import authenticate

import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

from runit import RunIt

load_dotenv()
PROJECTS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'projects')

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
        try:
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
            runit._id = project_id
            runit.update_config()

            funcs = []
            for func in runit.get_functions():
                funcs.append(f"{os.getenv('RUNIT_PROTOCOL')}{os.getenv('RUNIT_SERVERNAME')}/{project_id}/{func}/")
            result['functions'] = funcs
            result['homepage'] = f"{os.getenv('RUNIT_PROTOCOL')}{os.getenv('RUNIT_SERVERNAME')}/{project_id}/{func}/"
            return result
        except Exception as e:
            return {'status': 'error', 'msg': str(e)}

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

    # @jwt_required()
    def post(self, project_id, collection):
        '''
        Api for retrieving documents

        @param project_id Project ID
        @param collection Collection Name
        @return Documents Documents from collection
        '''
        try:
            data = request.get_json()
            if 'filter' in data.keys() and not 'columns' in data.keys():
                results = DBMS.Database.find(collection, data['filter'])
            elif 'columns' in data.keys() and not 'filter' in data.keys():
                results = DBMS.Database.find(collection, projection=data['columns'])
            elif 'filter' in data.keys() and 'columns' in data.keys():
                results = DBMS.Database.find(collection, data['filter'], data['columns'])
            else:
                results = DBMS.Database.find(collection)
                
            return [normalise(result) for result in results]
        except Exception as e:
            print(str(e))
            return {'status': 'error', 'msg': str(e)}
   
