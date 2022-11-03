#from packages import request

def index():
    return 'Yay, Python works'

def counter():
    return ' '.join([i for i in range(0, 9)])

def printout(string):
    return string

def time():
    from datetime import datetime
    return (datetime.utcnow()).strftime("%a %b %d %Y %H:%M:%S")

def html():
    with open('index.html', 'rt') as file:
        content = file.read()
        return content
