from fastapi.responses import RedirectResponse
from fastapi import APIRouter, Request, status
from odbms import DBMS
    
from ..models import Admin, User, Role, Permission, Project, Database, Secret
from ..core import flash, templates
from ..constants import  DOTENV_FILE, RUNIT_HOMEDIR, RUNIT_WORKDIR

import os
from dotenv import load_dotenv, dotenv_values, set_key, find_dotenv

from runit import RunIt

load_dotenv()

setup = APIRouter(
    prefix="/setup",
    tags=["projects"]
)

'''
Page for setting up runit-server
configurations.


@setup.before_request
def initial():
    os.chdir(os.getenv('RUNIT_HOMEDIR'))
''' 

@setup.get('/')
async def setup_index(request: Request):
    env_file = find_dotenv(str(DOTENV_FILE))
    
    if env_file:
        settings = dotenv_values(env_file)
        if settings.get('SETUP') == 'completed':
            return RedirectResponse(request.url_for('index'))
        
    return templates.TemplateResponse('setup/index.html', {
        'request': request
    })

@setup.post('/')
async def initsetup(request: Request):
    env_file = find_dotenv(str(DOTENV_FILE))
    settings = dotenv_values(env_file)
    data = await request.form()
    data_json = data._dict
    
    admin_email = str(data_json.get('adminemail'))
    admin_username = str(data_json.get('adminusername'))
    admin_password = str(data_json.get('adminpassword'))
    del data_json['adminemail']
    del data_json['adminusername']
    del data_json['adminpassword']
    
    settings.update(data._dict)                             # type: ignore
    
    for key, value in settings.items():
         set_key(env_file, key, value) # type: ignore
    set_key(env_file, 'SETUP', 'completed')
    
    settings = dotenv_values(find_dotenv(str(DOTENV_FILE)))
    
    if 'SETUP' in settings.keys() and settings['SETUP'] == 'completed':
        os.chdir(RUNIT_HOMEDIR)
        if settings['DBMS'] == 'sqlite':
            settings['DATABASE_NAME'] = str(settings.get('DATABASE_NAME', 'runit'))+'.db'
        db_port = int(settings['DATABASE_PORT']) if settings.get('DATABASE_PORT') else None
        await DBMS.initialize_async(settings['DBMS'], settings['DATABASE_HOST'], db_port, # type: ignore
                    settings['DATABASE_USERNAME'], settings['DATABASE_PASSWORD'],  # type: ignore
                    settings['DATABASE_NAME']) # type: ignore

        # Create tables if they do not exist in relational datatabases
        # [sqlite, mysql, postgresql]
        Admin.create_table()
        User.create_table()
        Permission.create_table()
        Role.create_table()   
        Project.create_table()   
        Database.create_table()
        Secret.create_table()
        
        Role('developer', []).save()
        Role('superadmin', []).save()
        Role('subadmin', []).save()
        
        Admin(admin_email, 'Administrator', admin_username, admin_password, 'superadmin').save()
    
    flash(request,'Setup completed', category='success')
    return RedirectResponse(request.url_for('index'), status_code=status.HTTP_303_SEE_OTHER)