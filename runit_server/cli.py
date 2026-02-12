import os
from pathlib import Path
import sys
import logging
import argparse
from getpass import getpass

from dotenv import load_dotenv, set_key, find_dotenv, dotenv_values

from .app import app

from odbms import DBMS
from .models import Role, Admin, User, Permission

from runit import RunIt

from .constants import RUNIT_WORKDIR, RUNIT_HOMEDIR, DOTENV_FILE, VERSION
import uvicorn

logging.getLogger('uvicorn').setLevel(logging.INFO)

load_dotenv(DOTENV_FILE)

RunIt.RUNTIME_ENV = 'server'

def setup_database():
    '''
    Connect to database using connection settings from .env
    
    @params None
    @return None
    '''
    settings = dotenv_values(find_dotenv(str(DOTENV_FILE)))
    if settings.get('DBMS') == 'sqlite':
        DBMS.initialize_with_defaults('sqlitle', settings.get('DATABASE_NAME'))
    
    else:
        db_port = int(settings['DATABASE_PORT']) if settings.get('DATABASE_PORT') else None
        DBMS.initialize(settings['DBMS'], settings['DATABASE_HOST'], db_port, # type: ignore
                    settings['DATABASE_USERNAME'], settings['DATABASE_PASSWORD'],  # type: ignore
                    settings['DATABASE_NAME']) # type: ignore
    
    # Create tables if they do not exist in relational datatabases
    # [sqlite, mysql, postgresql]
    Admin.create_table()
    User.create_table()
    Permission.create_table()
    Role.create_table()   
     
    # print('[--] Database setup complete')
    # Populate tables initially
    _run_async(_populate_roles_async())


def _run_async(coro):
    """Helper to run async code from sync context, handling nested event loops."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, create a task
        return loop.create_task(coro)
    except RuntimeError:
        # No event loop running, use asyncio.run
        return asyncio.run(coro)


async def _setup_database_async():
    """Async version: Connect to database using connection settings from .env"""
    settings = dotenv_values(find_dotenv(str(DOTENV_FILE)))
    if settings.get('DBMS') == 'sqlite':
        await DBMS.initialize_async('sqlite', database=settings.get('DATABASE_NAME'))
    else:
        db_port = int(settings['DATABASE_PORT']) if settings.get('DATABASE_PORT') else None
        await DBMS.initialize_async(
            settings['DBMS'], 
            settings['DATABASE_HOST'], 
            db_port,
            settings['DATABASE_USERNAME'], 
            settings['DATABASE_PASSWORD'],
            settings['DATABASE_NAME']
        )
    
    # Create tables if they do not exist in relational datatabases
    Admin.create_table()
    User.create_table()
    Permission.create_table()
    Role.create_table()
    
    # Populate tables initially
    await _populate_roles_async()


async def _populate_roles_async():
    """Async helper to populate roles."""
    # Use DBMS.Database.count() directly since Model doesn't have count() method
    count = await DBMS.Database.count(Role.TABLE_NAME, {})
    if not count:
        print('[#] Populating Roles')
        # Use keyword arguments for the new Pydantic-based Model class
        await Role(name='developer', permission_ids=[]).save()
        await Role(name='superadmin', permission_ids=[]).save()
        await Role(name='subadmin', permission_ids=[]).save()
        print('[--] Roles populated')


def create_folders():
    if not os.path.exists(RUNIT_WORKDIR):
        os.mkdir(RUNIT_WORKDIR)
    
    if not (os.path.exists(os.path.join(RUNIT_WORKDIR, 'accounts'))):
        os.mkdir(os.path.join(RUNIT_WORKDIR, 'accounts'))
        
    if not (os.path.exists(os.path.join(RUNIT_WORKDIR, 'projects'))):
        os.mkdir(os.path.join(RUNIT_WORKDIR, 'projects'))

def create_dot_env(settings: dict):
    '''
    Create .env file and populate with {settings}
    
    @param settings dict Dictionary of default settings
    @return None
    '''
    
    if not DOTENV_FILE.resolve().exists():
        open(DOTENV_FILE, 'wt').close()
        
    for key, value in settings.items():
        set_key(str(DOTENV_FILE), key, value)

async def _create_default_admin_async(args_is_true: bool = False):
    '''
    Async version: Create the default administrator account
    
    @params None
    @return None
    '''
    if args_is_true:
        await _setup_database_async()
        
    create_account = True

    # Use DBMS.Database.count() directly since Model doesn't have count() method
    count = await DBMS.Database.count(Admin.TABLE_NAME, {})
    if count:
        create_account = False
        
        result = await Admin.find({})
        if len(result):
            admin = result[0]
            print(f'[!] Default Administrator account already exists [{admin.username}]')
            
            answer = input('[?] Would you like to reset the account? [yes|no]: ')
            if answer.lower() == 'yes':
                # Use DBMS.Database.delete_many() directly
                await DBMS.Database.delete_many(Admin.TABLE_NAME, {'username': admin.username})
                create_account = True
            
    if create_account:
        print('[#] Create default administrator account')
        adminemail = input('Administrator Email Address: ')
        adminname = input('Administrator Full Name: ')
        adminusername = input('Administrator Username: ')
        adminpassword = getpass('Administrator Password: ')
        adminrole = input('Administrator role: [superadmin] ')
        adminrole = adminrole if adminrole else 'superadmin'
        
        if adminemail and adminusername and adminpassword and adminrole:
            admin = Admin(adminemail, adminname, adminusername, adminpassword, adminrole)
            await admin.save()
            print('[!] Administrator account created successfully.')

def create_default_admin(args_is_true: bool = False):
    '''
    Create the default administrator account
    
    @params None
    @return None
    '''
    _run_async(_create_default_admin_async(args_is_true))
        

def setup_runit(args):
    '''
    Setup Runit server side
    
    @params args
    @return None
    '''
    try:
        if args.admin:
            return create_default_admin(args.admin)
            
        domain = args.domain if hasattr(args, 'domain') else ''
        allowed = ['DBMS', 'DATABASE_HOST', 'DATABASE_PORT', 
                'DATABASE_USERNAME', 'DATABASE_PASSWORD', 
                'DATABASE_NAME', 'RUNTIME_PYTHON', 'RUNTIME_PHP',
                'RUNTIME_JAVASCRIPT', 'GITHUB_APP_CLIENT_ID',
                'GITHUB_APP_CLIENT_SECRET']
        
        default_settings = {
            'RUNIT_WORKDIR': str(RUNIT_WORKDIR),
            'RUNIT_HOMEDIR': str(RUNIT_HOMEDIR),
            'RUNIT_SERVERNAME': '',
            'DBMS': 'sqlite',
            'DATABASE_HOST': '127.0.0.1',
            'DATABASE_PORT': '',
            'DATABASE_USERNAME': '',
            'DATABASE_PASSWORD': '',
            'DATABASE_NAME': 'runit',
            'RUNTIME_PYTHON': 'python',
            'RUNTIME_PHP': 'php',
            'RUNTIME_JAVASCRIPT': 'node',
            'GITHUB_APP_CLIENT_ID': '',
            'GITHUB_APP_CLIENT_SECRET': '',
            'SETUP': ''
        }

        settings = dotenv_values(find_dotenv(str(DOTENV_FILE)))
        
        if settings is None or settings.keys() != default_settings.keys():
            create_dot_env(default_settings)

        settings = dotenv_values(find_dotenv(str(DOTENV_FILE)))
        
        print('')
        for key, value in settings.items():
            if key in allowed:
                settings[key] = input(f'{key} [{value}]: ')
                if key != 'DATABASE_USERNAME' and key != 'dbpassword':
                    settings[key] = settings[key] if settings[key] else value
        
        settings['RUNIT_HOMEDIR'] = RUNIT_HOMEDIR           # type: ignore
        
        if settings['DBMS'] and settings['DATABASE_HOST'] \
            and settings['DATABASE_PORT'] and settings['DATABASE_NAME']:
            settings['SETUP'] = 'completed'
        
        for key, value in settings.items():
            set_key(DOTENV_FILE, key, str(value))
        
        setup_database()
        create_default_admin()
    
    except Exception as e:
        print(str(e))
        sys.exit(1)

def run_server(args = {}):
    RunIt.DOCKER = args.docker
    RunIt.KUBERNETES = args.kubernetes

    uvicorn.run(app, host=args.host, port=args.port, log_level='info', proxy_headers=True, forwarded_allow_ips="*")

def get_arguments():
    global parser
    global VERSION
    
    subparsers = parser.add_subparsers()
    
    setup_parser = subparsers.add_parser('setup', help='Runit server-side configuration')
    setup_parser.add_argument('-d', '--domain', type=str, help="Runit server-side domain name")
    setup_parser.add_argument('--dbms', type=str, help="Runit Database System [mongodb|mysql]", choices=['mongodb', 'mysql'])
    setup_parser.add_argument('--dbhost', type=str, help="Database host ip address")
    setup_parser.add_argument('--dbport', type=str, help="Database host port")
    setup_parser.add_argument('--dbusername', type=str, help="Database user username")
    setup_parser.add_argument('--dbpassword', type=str, help="Database user password")
    setup_parser.add_argument('--dbname', type=str, help="Database name")
    setup_parser.add_argument('--admin', action='store_true', help="Manage administrator account")
    setup_parser.set_defaults(func=setup_runit)
    
    parser.add_argument('--docker', action='store_true', help="Run program in docker container")
    parser.add_argument('--kubernetes', action='store_true', help="Run program using kubernetes")
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host address to run server on')
    parser.add_argument('--port', type=int, default=9000, help='Host port to run server on')
    parser.add_argument('--debug', action='store_true', help="Enable debug mode")
    parser.add_argument('--production', action='store_true', help="Run in production mode")
    parser.add_argument('-v','--version', action='version', version=f'%(prog)s {VERSION}')
    parser.set_defaults(func=run_server)
    return parser.parse_args()

def main():
    global parser
    try:
        parser = argparse.ArgumentParser(description="A terminal client for runit-server")
        args = get_arguments()
        args.func(args)

    except Exception as e:
        print(str(e), '\n')
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
