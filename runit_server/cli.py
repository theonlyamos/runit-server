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
        DBMS.initialize(settings['DBMS'], settings['DATABASE_HOST'], settings['DATABASE_PORT'], # type: ignore
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
    if not Role.count():
        print('[#] Populating Roles')
        Role('developer', []).save()
        Role('superadmin', []).save()
        Role('subadmin', []).save()
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

def create_default_admin(args_is_true: bool = False):
    '''
    Create the default administrator account
    
    @params None
    @return None
    '''
    if args_is_true:
        setup_database()
        
    create_account = True

    if Admin.count():
        create_account = False
        
        result = Admin.find({})
        if len(result):
            admin = result[0]
            print(f'[!] Default Administrator account already exists [{admin.username}]')
            
            answer = input('[?] Would you like to reset the account? [yes|no]: ')
            if answer.lower() == 'yes':
                Admin.remove({'username': admin.username})
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
            Admin(adminemail, adminname, adminusername, adminpassword, adminrole).save()
            print('[!] Administrator account created successfully.')
        

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
