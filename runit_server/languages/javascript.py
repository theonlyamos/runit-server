import os
from .runtime import Runtime

JS_TOOLS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)),'..', 'tools', 'javascript')


class Javascript(Runtime):
    '''
    Class for parsing and running
    Javascript functions from file
    '''
    LOADER = os.path.realpath(os.path.join(JS_TOOLS_DIR, 'loader.js'))
    RUNNER = os.path.realpath(os.path.join(JS_TOOLS_DIR, 'runner.js'))
    
    def __init__(self, filename, runtime):
        super().__init__(filename, runtime)