from odbms import DBMS, Model


class Secret(Model):
    '''A model class for permission'''
    TABLE_NAME = 'secrets'

    def __init__(self, user_id: str, project_id: str, variables: dict = {}, created_at=None, updated_at=None, id=None):
        super().__init__(created_at, updated_at, id)
        self.user_id = user_id
        self.project_id = project_id
        self.variables = variables
        

