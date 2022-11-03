import os
import sys
import shelve
import getpass
import argparse
from typing import Type

from flask import Flask, request
from dotenv import load_dotenv, set_key, find_dotenv, dotenv_values

from .languages import LanguageParser
from .modules import Account
from .runit import RunIt

load_dotenv()

VERSION = "0.0.5"
CURRENT_PROJECT = ""
CURRENT_PROJECT_DIR = os.path.realpath(os.curdir)
EXT_TO_RUNTIME = {'.py': 'python', '.php': 'php', '.js': 'node'}

def StartWebserver(project: Type[RunIt], host: str = '127.0.0.1', port: int = 5000):
    app = Flask(__name__)
    app.secret = os.getenv('RUNIT_SECRET_KEY')
    try:
        app.add_url_rule('/', view_func=project.serve)
        app.add_url_rule('/<func>', view_func=project.serve)
        app.add_url_rule('/<func>/', view_func=project.serve)
        app.run(host, port, True)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(e)

def create_new_project(args):
    global CONFIG_FILE
    global CURRENT_PROJECT
    '''
    Method for creating new project or
    function from command line arguments

    @param args Arguments from argparse
    @return None
    '''
    
    if args.name:
        name = RunIt.set_project_name(args.name)
        if RunIt.exists(name):
            print(f'{name} project already Exists')
            sys.exit(1)
        
        CONFIG_FILE = 'runit.json'
        config = {}
        config['name'] = args.name
        config['language'] = args.language
        config['runtime'] = args.runtime
        config['author'] = {}
        config['author']['name'] = getpass.getuser()
        config['author']['email'] = "name@example.com"
        
        user = Account.user()
        os.chdir(CURRENT_PROJECT_DIR)
        if user is not None:
            config['author']['name'] = user['name']
            config['author']['email'] = user['email']
        
        CURRENT_PROJECT = RunIt(**config)
        print(CURRENT_PROJECT)
    else:
        print('Project name not specified')

def run_project(args):
    global CONFIG_FILE
    CONFIG_FILE = args.config
    
    if not CONFIG_FILE and not args.file:
        raise FileNotFoundError
    else:
        if not RunIt.has_config_file() and not args.file:
            raise FileNotFoundError
        elif args.file:
            filename = args.file
            runtime = EXT_TO_RUNTIME[os.path.splitext(filename)[1]]
            LanguageParser.run_file(filename, runtime)
        else:
            project = RunIt(**RunIt.load_config())

            if args.shell:
                print(project.serve(args.function, args.arguments, args.file))
            else:
                StartWebserver(project, args.host, args.port)
            
def publish(args):
    global CONFIG_FILE
    CONFIG_FILE = args.config

    global BASE_HEADERS
    # token = load_token()

    # headers = {}
    # headers['Authorization'] = f"Bearer {token}"

    Account.isauthenticated({})
    user = Account.user()

    os.chdir(CURRENT_PROJECT_DIR)

    config = RunIt.load_config()
    if not config:
        raise FileNotFoundError
    
    project = RunIt(**config)
    if user:
        project.author['name'] = user['name']
        project.author['email'] = user['email']

    project.update_config()
    print('[-] Preparing project for upload...')
    filename = project.compress()
    print('[#] Project files compressed')
    #print(project.config)

    print('[-] Uploading file....', end='\r')
    file = open(filename, 'rb')
    files = {'file': file}
    result = Account.publish_project(files, project.config)
    file.close()
    os.chdir(CURRENT_PROJECT_DIR)
    os.unlink(filename)

    if 'msg' in result.keys():
        print(result['msg'])
        exit(1)
    elif 'message' in result.keys():
        print(result['message'])
        exit(1)
    
    print('[#] Files Uploaded!!!')
    if 'project_id' in result.keys():
        project._id = result['project_id']
        project.homepage = result['homepage']
        project.update_config()
        print('[*] Project config updated')

    print('[*] Project published successfully')
    print('[!] Access your functions with the urls below:')

    print(f"[-] {result['homepage']}")
    for func_url in result['functions']:
        print(f"[-] {func_url}")

def setup_runit(args):
    '''
    Setup Runit server side
    
    @params args
    @return None
    '''
    global parser
    domain = args.domain
    allowed = ['dbms', 'dbhost', 'dbport', 
               'dbusername', 'dbpassword', 'dbname']
    
    settings = dotenv_values(find_dotenv())
    if not domain:
        default = os.environ['RUNIT_SERVERNAME']
        domain = input(f'Server Address [{default}]: ')
        domain = domain if domain else default
    
    for key, value in settings.items():
        if key in allowed:
            if getattr(args, key):
                settings[key] = getattr(args, key)
            else:
                settings[key] = input(f'{key} [{value}]: ')
                if key != 'dbusername' and key != 'dbpassword':
                    settings[key] = settings[key] if settings[key] else value
    
    settings['RUNIT_SERVERNAME'] = domain
    settings['RUNIT_HOMEDIR'] = os.path.join('..', os.path.realpath(os.path.split(__file__)[0]))
    
    if settings['RUNIT_SERVERNAME'] and settings['dbms'] and \
        settings['dbhost'] and settings['dbport'] and settings['dbname']:
        settings['setup'] = 'completed'
    
    for key, value in settings.items():
        set_key(find_dotenv(), key, value)

def load_token(access_token = None):
    with shelve.open('account') as account:
        if access_token is None and 'access_token' in account.keys():
            return account['access_token']
        if access_token:
            account['access_token'] = access_token
        else:
            account['access_token'] = ''
        return None

def is_file(string):
    if (os.path.isfile(os.path.join(os.curdir, string))):
        return open(string, 'rt')
    return False

def get_functions(args):
    config = RunIt.load_config()
    if not config:
        raise FileNotFoundError
    
    project = RunIt(**config)
    print(project.get_functions())

def print_help(args):
    global parser
    parser.print_help()

def get_arguments():
    global parser
    global VERSION
    
    subparsers = parser.add_subparsers()
    new_parser = subparsers.add_parser('new', help='Create new project or function')
    new_parser.add_argument("name", type=str, nargs="?", 
                        help="Name of the new project")          
    new_parser.add_argument('-l', '--language', type=str, choices=['python', 'php', 'javascript'],
                        help="Language of the new project")
    new_parser.add_argument('-r','--runtime', type=str,
                        help="Runtime of the project language. E.g: python3.10, node")
    new_parser.set_defaults(func=create_new_project)
    
    # run_parser = subparsers.add_parser('run', help='Run current|specified project|function')
    # run_parser.add_argument('function', default='index', type=str, nargs='?', help='Name of function to run')
    # run_parser.add_argument('--file', type=str, nargs='?', help='Name of file to run')
    # run_parser.add_argument('--shell', action='store_true', help='Run function only in shell')
    # run_parser.add_argument('-x', '--arguments', action='append', default=[], help='Comma separated function arguments')
    # run_parser.set_defaults(func=run_project)

    login_parser = subparsers.add_parser('login', help="User account login")
    login_parser.add_argument('--email', type=str, help="Account email address")
    login_parser.add_argument('--password', type=str, help="Account password")
    login_parser.set_defaults(func=Account.login)

    register_parser = subparsers.add_parser('register', help="Register new account")
    register_parser.add_argument('--name', type=str, help="Account user's name")
    register_parser.add_argument('--email', type=str, help="Account email address")
    register_parser.add_argument('--password', type=str, help="Account password")
    register_parser.set_defaults(func=Account.register)

    account_parser = subparsers.add_parser('account', help='Get Current logged in user info')
    account_parser.add_argument('-i', '--info', action='store_true', help="Print out current account info")
    account_parser.set_defaults(func=Account.info)
    
    projects_parser = subparsers.add_parser('projects', help='Manage projects')
    projects_parser.add_argument('-l', '--list', action='store_true', help="List account projects")
    projects_parser.add_argument('--id', type=str, help="Project ID")
    projects_parser.set_defaults(func=Account.projects)

    projects_subparser = projects_parser.add_subparsers()

    new_project_parser = projects_subparser.add_parser('new', help="Create new Project")
    new_project_parser.add_argument('name', type=str, help="Name of project")
    new_project_parser.set_defaults(func=create_new_project)

    update_project_parser = projects_subparser.add_parser('update', help="Update Project by Id")
    update_project_parser.add_argument('--id', required=True, help="Id of the project to be updated")
    update_project_parser.add_argument('-d', '--data', required=True, type=str, action='append', help='A dictionary or string. E.g: name="new name" or {"name": "new name"}')
    update_project_parser.set_defaults(func=Account.update_project)

    delete_project_parser = projects_subparser.add_parser('rm', help="Delete Project")
    delete_project_parser.add_argument('--id', required=True, help="Id of the project to be deleted")
    delete_project_parser.set_defaults(func=Account.delete_project)

    functions_parser = subparsers.add_parser('functions', help='Manage functions')
    functions_parser.add_argument('-l', '--list', action='store_true', help="List project functions")
    functions_parser.add_argument('--id', type=str, help="Function ID")
    functions_parser.add_argument('-p', '--project', type=str, help="Project ID")
    functions_parser.set_defaults(func=get_functions)
    
    setup_parser = subparsers.add_parser('setup', help='Runit server-side configuration')
    setup_parser.add_argument('-d', '--domain', type=str, help="Runit server-side domain name")
    setup_parser.add_argument('--dbms', type=str, help="Runit Database System [mongodb|mysql]", choices=['mongodb', 'mysql'])
    setup_parser.add_argument('--dbhost', type=str, help="Database host ip address")
    setup_parser.add_argument('--dbport', type=str, help="Database host port")
    setup_parser.add_argument('--dbusername', type=str, help="Database user username")
    setup_parser.add_argument('--dbpassword', type=str, help="Database user password")
    setup_parser.add_argument('--dbname', type=str, help="Database name")
    setup_parser.set_defaults(func=setup_runit)

    publish_parser = subparsers.add_parser('publish', help='Publish current project')
    publish_parser.set_defaults(func=publish)
    
    parser.add_argument('-f', '--function', default='index', type=str, nargs='?', help='Name of function to run')
    parser.add_argument('--file', type=str, nargs='?', help='Name of file to run')
    parser.add_argument('--shell', action='store_true', help='Run function only in shell')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host address to run project on')
    parser.add_argument('--port', type=int, default=5000, help='Host port to run project on')
    parser.add_argument('-x', '--arguments', action='append', default=[], help='Comma separated function arguments')
    parser.add_argument('-c','--config', type=is_file, default='runit.json', 
                        help="Configuration File, defaults to 'runit.json'") 
    parser.add_argument('-v','--version', action='version', version=f'%(prog)s {VERSION}')
    parser.set_defaults(func=run_project)
    return parser.parse_args()

def main():
    global parser
    try:
        parser = argparse.ArgumentParser(description="A terminal client for runit")
        args = get_arguments()
        args.func(args)

    except FileNotFoundError:
        print('No runit project or file to run\n')
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()