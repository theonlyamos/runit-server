import os
from enum import Enum
from typing import Literal
from dotenv import find_dotenv, load_dotenv
from pathlib import Path

VERSION = "0.4.2"
CURRENT_PROJECT = ""
NOT_FOUND_FILE = '404.html'
DOT_RUNIT_IGNORE = '.runitignore'
CONFIG_FILE = 'runit.json'
STARTER_CONFIG_FILE = 'runit.json'
IS_RUNNING = False
CURRENT_PROJECT_DIR = os.path.realpath(os.curdir)
SESSION_SECRET_KEY = 'dsafidsalkjdsaofwpdsncdsfdsafdsafjhdkjsfndsfkjsldfdsfjaskljdf'
JWT_SECRET_KEY = '972a444fb071aa8ee83bf128808d255ec72e3a6b464a836b7d06254529c6'
JWT_ALGORITHM = 'HS256'
API_VERSION = 'v1'
SUBSCRIPTION_EVENTS = Literal['all', 'create', 'update', 'delete']

RUNIT_WORKDIR = Path(os.path.expanduser('~')).joinpath('RUNIT_WORKDIR')

RUNIT_HOMEDIR = Path(__file__).resolve().parent

if not RUNIT_WORKDIR.exists():
    RUNIT_WORKDIR.mkdir()

DOTENV_FILE = RUNIT_WORKDIR.joinpath('.env')

if not DOTENV_FILE.exists():
    with open(DOTENV_FILE, 'w') as file:
        pass 

load_dotenv(find_dotenv(str(DOTENV_FILE)))

GITHUB_APP_CLIENT_ID = os.getenv('GITHUB_APP_CLIENT_ID','')
GITHUB_APP_CLIENT_SECRET = os.getenv('GITHUB_APP_CLIENT_SECRET','')

PROJECTS_DIR = os.path.join(RUNIT_WORKDIR, 'projects')
TEMPLATES_PATH = os.path.join(RUNIT_HOMEDIR, 'templates')
DOCKER_TEMPLATES = os.path.join(TEMPLATES_PATH, 'docker')

STARTER_FILES = {'python': 'application.py', 
                 'php': 'index.php',
                 'javascript': 'main.js',
                 'multi': 'application.py'}
EXTENSIONS = {'python': '.py',  'php': '.php', 'javascript': '.js'}
EXT_TO_LANG = {'.py': 'python', '.php': 'php', 
               '.js': 'javascript', '.jsx': 'javascript', 
               '.ts': 'javascript', '.tsx': 'javascript'}
LANGUAGE_TO_ICONS = {
    'python': 'fab fa-python', 
    'php': 'fab fa-php',
    'javascript': 'fab fa-node-js',
    'multi': 'fas fa-project-diagram'
}
LANGUAGE_TO_RUNTIME = {'python': os.getenv('RUNTIME_PYTHON', 'python'), 
                       'php': os.getenv('RUNTIME_PHP', 'php'),
                       'javascript': os.getenv('RUNTIME_JAVASCRIPT', 'node'), 
                       'multi': 'multi'}
EXT_TO_RUNTIME = {'.py': LANGUAGE_TO_RUNTIME['python'], 
                  '.php': LANGUAGE_TO_RUNTIME['php'], 
                  '.js': LANGUAGE_TO_RUNTIME['javascript'],
                  '.ts': LANGUAGE_TO_RUNTIME['javascript']}
BASE_HEADERS = {
    'Content-Type': 'application/json'
}

class Language(Enum):
    php = 'php'
    multi = 'multi'
    python = 'python'
    javascript = 'javascript'
