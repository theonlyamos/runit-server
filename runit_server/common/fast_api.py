from odbms import DBMS, normalise
from fastapi import APIRouter

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
from datetime import datetime

from runit import RunIt
from ..constants import (
    PROJECTS_DIR,
    DOCKER_TEMPLATES
)

load_dotenv()

router = APIRouter(prefix='/api')

@router.api_route('/login', methods=['POST'])
def login(request):
    """Login Api Endpoint

    Args:
        request (_type_): Request object exposed by fastapi
    """
    
    data = request.json()

    user = authenticate(data['email'], data['password'])
    if user:
        access_token = create_access_token(user.id)
        return {'status': 'success', 'access_token': access_token}
    return {'status': 'error', 'message': 'Invalid login credentials'}