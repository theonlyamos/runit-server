from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

from subprocess import check_output
from typing import Any

load_dotenv()

class Runtime(object):
    '''
    Class for parsing and running
    functions from file
    '''
    LOADER = ""
    RUNNER = ""
    
    def __init__(self, filename="", runtime="", is_file = False):
        self.filename = filename
        self.runtime = runtime
        self.is_file = is_file
        self.module = os.path.realpath(os.path.join(os.curdir, self.filename))
        self.functions = []
        self.load_functions_from_file()
    
    def load_functions_from_file(self):
        '''
        Class method for retrieving exported
        function names in .js file

        @param None
        @return None
        '''
        
        try:
            command = check_output(f'{self.runtime} {self.LOADER} {self.module}', shell=True)
            result = str(command)
            result = result.lstrip("b'").lstrip('"').replace('\\n', '\n').replace('\\r', '\r').rstrip("'").rstrip('"').strip()
            
            if self.runtime == 'php':
                self.functions = result.split(',')
            else:
                self.functions = eval(result)

            for key in self.functions:
                self.__setattr__(key, self.anon_function)
                
        except Exception as e:
            print(str(e))
            return str(e)

    def list_functions(self):
        '''
        List Class methods

        @param None
        @retun None
        '''
        return [func for func in self.functions]

    def anon_function(self, *args):
        args = ', '.join(args)
        try:
            if len(args):
                if self.is_file:
                    return os.system(f'{self.runtime} {self.filename} "{args}"')
                else:
                    command = check_output(f'{self.runtime} {self.RUNNER} {self.module} {self.current_func} "{args}"', shell=True)
            else:
                if self.is_file:
                    return os.system(f'{self.runtime} {self.filename}')
                else:
                    command = check_output(f'{self.runtime} {self.RUNNER} {self.module} {self.current_func}', shell=True)

            result = str(command)
            return result.lstrip("b'").replace('\\n', '\n').replace('\\r', '\r').rstrip("'").strip()
        except Exception as e:
            return str(e)