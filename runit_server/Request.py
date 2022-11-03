import requests

class Request:
    def __init__(self):
        req = requests.get('http://localhost:9000/get_app_requests/', headers={'Accept': 'application/json'})
        self.parameters = req.json()

    def args(self):
        return self.parameters
    
    def get(self, name=None):
        if name == None:
            return self.parameters['GET']
        return self.parameters['GET'][name] \
            if name in self.parameters['GET'].keys() \
                else ''

    def post(self, name=None):
        if name == None:
            return self.parameters['POST']
        return self.parameters['POST'][name] \
            if name in self.parameters['POST'].keys() \
                else ''