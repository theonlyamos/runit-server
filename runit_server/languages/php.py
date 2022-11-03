import os
from .runtime import Runtime

PHP_TOOLS_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..','tools', 'php')

class PHP(Runtime):
    '''
    Class for parsing and running php
    functions from file
    '''
    LOADER = os.path.realpath(os.path.join(PHP_TOOLS_DIR, 'loader.php'))
    RUNNER = os.path.realpath(os.path.join(PHP_TOOLS_DIR, 'runner.php'))
    
    def __init__(self, filename, runtime):
        super().__init__(filename, runtime)
