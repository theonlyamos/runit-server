import os
import sys
import argparse

from waitress import serve
from dotenv import load_dotenv, set_key, find_dotenv, dotenv_values

from .app import app

load_dotenv()

VERSION = "0.1.2"

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

def run_server(args = None):
    app.run(host=args.host, port=args.port, debug=args.debug)
    # serve(app, listen=f"*:{args.port}")

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
    setup_parser.set_defaults(func=setup_runit)
    
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Host address to run server on')
    parser.add_argument('--port', type=int, default=9000, help='Host port to run server on')
    parser.add_argument('--debug', type=bool, choices=[True, False], default=True, help="Enable debug mode")
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
