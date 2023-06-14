from flask import Blueprint, jsonify, request

from ..models import Project
from runit import RunIt

import os
from dotenv import load_dotenv

load_dotenv()

CURRENT_PATH = os.path.dirname(os.path.realpath(__file__))
HOMEDIR = os.getenv('RUNIT_HOMEDIR', os.path.realpath(os.path.join(CURRENT_PATH, '..')))
PROJECTS_DIR = os.path.join(HOMEDIR, 'projects')

functions = Blueprint('functions', __name__)

@functions.get('/<string:project_id>/<string:function>/')
def run(project_id, function):
    if (os.path.isdir(os.path.join(PROJECTS_DIR, project_id))):
        #os.chdir(project.path)
        result = RunIt.start(project_id, function)
        os.chdir(os.getenv('RUNIT_HOMEDIR'))
        return jsonify(result)

    return RunIt.notfound()
