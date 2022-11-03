#! python

import os
import sys
import json
from zipfile import ZipFile

from flask import request
from io import TextIOWrapper

from .languages import LanguageParser


VERSION = "0.0.5"
CURRENT_PROJECT = ""
TEMPLATES_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
STARTER_FILES = {'python': 'application.py', 'php': 'index.php','javascript': 'main.js'}
EXTENSIONS = {'python': '.py',  'php': '.php', 'javascript': '.js'}
EXT_TO_LANG = {'.py': 'python', '.php': 'php', '.js': 'javascript'}
EXT_TO_RUNTIME = {'.py': 'python', '.php': 'php', '.js': 'node'}
NOT_FOUND_FILE = '404.html'
CONFIG_FILE = 'runit.json'
STARTER_CONFIG_FILE = 'runit.json'
IS_RUNNING = False
PROJECTS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'projects')
CURRENT_PROJECT_DIR = os.path.realpath(os.curdir)
BASE_HEADERS = {
    'Content-Type': 'application/json'
}

class RunIt:
    def __init__(self, name, _id="", version="0.0.1", description="", homepage="",
    language="", runtime="", start_file="", author={}, is_file: bool = False):
        global STARTER_FILES

        self._id = _id
        self.name = name
        self.version = version
        self.description = description
        self.homepage = homepage
        self.language = language
        self.runtime = runtime
        self.author = author
        self.config = {}
        self.start_file = start_file if start_file else STARTER_FILES[self.language]
        self.create_config()
        
        if not RunIt.has_config_file() and not is_file:
            self.create_folder()
            self.dump_config()
            self.create_starter_files()
    
    def __repr__(self):
        return json.dumps(self.config, indent=4)

    @staticmethod
    def exists(name):
        return os.path.exists(os.path.join(os.curdir, name))

    @staticmethod
    def has_config_file():
        global CONFIG_FILE

        if isinstance(CONFIG_FILE, str):
            return os.path.exists(os.path.join(os.curdir, CONFIG_FILE))
        elif isinstance(CONFIG_FILE, bool):
            return False
        return True

    @staticmethod
    def load_config()-> dict:
        '''
        Load Configuration file from
        current directory: runit.json
        
        @params None
        @return Dictionary
        '''
        global CONFIG_FILE
        
        if isinstance(CONFIG_FILE, str):
            if os.path.exists(os.path.join(os.curdir, CONFIG_FILE)):
                with open(CONFIG_FILE, 'rt') as file:
                    return json.load(file)
        elif isinstance(CONFIG_FILE, TextIOWrapper):
            return json.load(CONFIG_FILE)
        return {}

    @staticmethod
    def set_project_name(name: str =None)-> str:
        '''
        Set Project name from argument
        or terminal input
        
        @param  name
        @return name
        '''
        global IS_RUNNING
        try:
            if not IS_RUNNING:
                IS_RUNNING = True
            else:
                name = str(input('Enter RunIt Name: '))
            while not name:
                name = str(input('Enter RunIt Name: '))
            return name
        except KeyboardInterrupt:
            sys.exit(1)


    @classmethod
    def start(cls, project_id: str, func='index'):
        global NOT_FOUND_FILE
        global PROJECTS_DIR

        os.chdir(os.path.join(PROJECTS_DIR, project_id))
        
        if not RunIt.has_config_file():
            return RunIt.notfound()
        
        project = cls(**RunIt.load_config())

        args = request.args
        
        args_list = []
        for key, value in args.items():
            args_list.append(value)
        
        start_file = project.start_file

        lang_parser = LanguageParser.detect_language(start_file, project.runtime)
        lang_parser.current_func = func
        try:
            return getattr(lang_parser, func)(*args_list)
        except AttributeError as e:
            return f"Function with name '{func}' not defined!"
        except TypeError as e:
            try:
                return getattr(lang_parser, func)()
            except TypeError as e:
                return str(e)
    
    @staticmethod
    def notfound():
        global TEMPLATES_FOLDER
        global NOT_FOUND_FILE

        with open(os.path.join(os.curdir, TEMPLATES_FOLDER, NOT_FOUND_FILE),'rt') as file:
            return file.read()
    
    @staticmethod
    def extract_project(filepath):
        directory, filename = os.path.split(filepath)
    
        with ZipFile(filepath, 'r') as file:
            file.extractall(directory)
        os.unlink(filepath)
    
    def get_functions(self)->list:
        lang_parser = LanguageParser.detect_language(self.start_file, self.runtime)
        return lang_parser.list_functions()
    
    def serve(self, func: str = 'index', args: dict|list=None, filename: str = ''):
        global NOT_FOUND_FILE
        global request

        lang_parser = LanguageParser.detect_language(self.start_file, self.runtime)
        lang_parser.current_func = func
        
        if not args and request:
            args = dict(request.args)

        args_list = args if type(args) == list else []
        
        if type(args) == dict:
            for key, value in args.items():
                args_list.append(value)

        try:
            return getattr(lang_parser, func)(*args_list)
        except AttributeError as e:
            return RunIt.notfound()
            # return f"Function with name '{func}' not defined!"
        except TypeError as e:
            try:
                return getattr(lang_parser, func)()
            except TypeError as e:
                return str(e)
    
    def create_folder(self):
        os.mkdir(os.path.join(os.curdir, self.name))

    def dump_config(self):
        global CONFIG_FILE

        if isinstance(CONFIG_FILE, str):
            config_file = open(os.path.join(os.curdir, self.name,
            CONFIG_FILE),'wt')
        else:
            config_file = CONFIG_FILE

        json.dump(self.config, config_file, indent=4)
        config_file.close()

    def update_config(self):
        global CONFIG_FILE
        global STARTER_CONFIG_FILE

        if isinstance(CONFIG_FILE, TextIOWrapper):
            CONFIG_FILE.close()
            CONFIG_FILE = STARTER_CONFIG_FILE
        
        config_file = open(CONFIG_FILE,'wt')
        self.config['_id'] = self._id
        self.config['name'] = self.name
        self.config['version'] = self.version
        self.config['description'] = self.description
        self.config['homepage'] = self.homepage
        self.config['language'] = self.language
        self.config['runtime'] = self.runtime
        self.config['start_file'] = self.start_file
        self.config['author'] = self.author
        json.dump(self.config, config_file, indent=4)
        config_file.close()
    
    def compress(self):
        os.chdir(CURRENT_PROJECT_DIR)

        zipname = f'{self.name}.zip'
        exclude_list = [zipname, 'account.db']
        with ZipFile(zipname, 'w') as zipobj:
            print('[!] Compressing Project Files...')
            for folderName, subfolders, filenames in os.walk(os.curdir):
                for filename in filenames:
                    filepath = os.path.join(folderName,  filename)
                    #print(filepath)
                    print(os.path.basename(filepath), zipname, os.path.basename(filepath) != zipname)
                    if not os.path.basename(filepath) in exclude_list:
                        zipobj.write(filepath, filepath)
                        print(f'[{filepath}] Compressed!')
            print(f'[!] Filename: {zipname}')
        return zipname

    def create_config(self):
        self.config['_id'] = self._id
        self.config['name'] = self.name
        self.config['version'] = self.version
        self.config['description'] = self.description
        self.config['homepage'] = 'https://example.com/project_id/'
        self.config['language'] = self.language
        self.config['runtime'] = self.runtime
        self.config['start_file'] = self.start_file
        self.config['author'] = self.author
    
    def create_starter_files(self):
        global TEMPLATES_FOLDER
        global NOT_FOUND_FILE
        
        with open(os.path.join(os.curdir, TEMPLATES_FOLDER, self.language,
            self.start_file),'rt') as file:
            with open(os.path.join(os.curdir, self.name, self.start_file), 'wt') as starter:
                starter.write(file.read())
        
        with open(os.path.join(os.curdir, TEMPLATES_FOLDER, NOT_FOUND_FILE),'rt') as file:
            with open(os.path.join(os.curdir, self.name, NOT_FOUND_FILE), 'wt') as error:
                error.write(file.read())
        
        '''
        with open(os.path.join(os.curdir, 'runit-cli.py'),'rt') as file:
            with open(os.path.join(os.curdir, self.name, 'runit-cli.py'), 'wt') as client:
                client.write(file.read())
        '''

        if self.language.startswith('python'):
            PACKAGES_FOLDER = 'packages'
            os.mkdir(os.path.join(os.curdir, self.name, PACKAGES_FOLDER))
            for filename in os.listdir(os.path.abspath(os.path.join(os.curdir, TEMPLATES_FOLDER, self.language, PACKAGES_FOLDER))):
                if os.path.isfile(os.path.join(os.curdir, TEMPLATES_FOLDER, self.language,
                    PACKAGES_FOLDER, filename)):
                    with open(os.path.join(os.curdir, TEMPLATES_FOLDER, self.language,
                        PACKAGES_FOLDER, filename),'rt') as file:
                        with open(os.path.join(os.curdir, self.name, PACKAGES_FOLDER, filename), 'wt') as package:
                            package.write(file.read())




