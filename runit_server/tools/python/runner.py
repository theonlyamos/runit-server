import os
import sys
import inspect

args = sys.argv
functionArguments = None

try:
    if len(args) >= 3:
        filename = args[1]
        functionname = args[2]

        sys.path.append(os.path.abspath(os.curdir))
        module = __import__(inspect.getmodulename(filename))
        method = [f[1] for f in inspect.getmembers(module, inspect.isfunction) if f[0] == functionname][0]

        if len(args) > 3:
            functionArguments = args[3]

        if functionArguments is not None:
            method(functionArguments)
        else:
            method()
    
except Exception as e:
    print(str(e))