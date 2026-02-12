from datetime import datetime
from typing import Optional
from odbms import DBMS, Model

class Project(Model):
    TABLE_NAME = 'projects'
    user_id: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = "0.0.1"
    description: Optional[str] = ""
    homepage: Optional[str] = ""
    language: Optional[str] = ""
    runtime: Optional[str] = ""
    start_file: Optional[str] = ""
    private: Optional[bool] = False
    author: Optional[str] = ""
    github_repo: Optional[str] = ""
    github_repo_branch: Optional[str] = ""

    def __init__(self, user_id: str, name: str, version: str = "0.0.1", description: str = "", homepage: str = "",
        language: str = "", runtime: str = "", start_file: str = "", private: bool = False, author: str = '', 
        github_repo: str = '', github_repo_branch: str = '', created_at=None, updated_at=None, id=None):
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = datetime.strptime(created_at, "%a %b %d %Y %H:%M:%S")
        if isinstance(updated_at, str):
            try:
                updated_at = datetime.fromisoformat(updated_at)
            except ValueError:
                updated_at = datetime.strptime(updated_at, "%a %b %d %Y %H:%M:%S")

        init_kwargs = {
            "user_id": user_id,
            "name": name,
            "version": version,
            "description": description,
            "homepage": homepage,
            "language": language,
            "runtime": runtime,
            "start_file": start_file,
            "private": private,
            "author": author,
            "github_repo": github_repo,
            "github_repo_branch": github_repo_branch,
        }
        if created_at is not None:
            init_kwargs["created_at"] = created_at
        if updated_at is not None:
            init_kwargs["updated_at"] = updated_at
        if id is not None:
            init_kwargs["id"] = id

        super().__init__(**init_kwargs)
        self.name = name
        self.user_id = user_id
        self.version = version
        self.description = description
        self.homepage = homepage
        self.language = language
        self.runtime = runtime
        self.private = private
        self.start_file = start_file
        self.author = author
        self.github_repo = github_repo
        self.github_repo_branch = github_repo_branch

    
    def user(self):#-> User:
        '''
        Instance Method for retrieving User of Project instance
        
        @params None
        @return User Instance
        '''

        return Model.normalise(DBMS.Database.find_one('users', Model.normalise({'id': self.user_id}, 'params'))) # type: ignore
    
    async def functions(self):
        '''
        Instance Method for retrieving Functions of Project Instance

        @params None
        @return List of Function Instances
        '''

        return await DBMS.Database.find('functions', Model.normalise({'project_id': self.id}, 'params'))
    

    @classmethod
    async def get_by_user(cls, user_id: str)-> list:
        '''
        Class Method for retrieving projects by a user

        @param user_id:str _id of the user
        @return List of Project instances
        '''
        data = []
        projects = await DBMS.Database.find(Project.TABLE_NAME, Model.normalise({'user_id': user_id}, 'params'))

        for elem in projects:
            if isinstance(elem, dict):
                data.append(cls(**cls.normalise(elem)))
            else:
                data.append(cls(*elem))

        return data

