import logging
from typing import  Optional
import aiofiles

from fastapi.responses import JSONResponse
from fastapi import APIRouter, HTTPException, Request, Depends


from ..common import get_session
from ..models import User


from github import Github, Auth

from ..constants import (
    GITHUB_APP_CLIENT_ID,
    GITHUB_APP_CLIENT_SECRET
)

github_router = APIRouter(
    prefix="/github",
    tags=["github"],
    dependencies=[Depends(get_session)]
)

@github_router.get('/callback')
async def github_callback(request: Request):
    user = User.get(request.session['user_id'])
    response = {'status': 'success'}
    try:
        g = Github()
        app = g.get_oauth_application(GITHUB_APP_CLIENT_ID, GITHUB_APP_CLIENT_SECRET)
        code = request.query_params.get('code')
        token = app.get_access_token(str(code))
        if user:
            user.gat = token.token
            user.grt = str(token.refresh_token)
            user.save()
        response['data'] = token.token
    except Exception as e:
        logging.warn(str(e))
        response['status'] = 'error'
        response['message'] = 'Error connecting to Github'
    finally:
        return JSONResponse(response)

@github_router.get('/repos')
@github_router.get('/repos/{repo_name}')
async def get_repos(request: Request, repo_name: Optional[str] = None):
    user = User.get(request.session['user_id'])
    user = user.json() if user else None
    response: dict = {'status': 'success'}
    repos: list[dict] = []
    try:
        if not user or not user['gat']:
            raise Exception('User is not authenticated')

        auth = Auth.Token(user['gat'])
        g = Github(auth=auth)

        if not repo_name:
            git_repos = g.get_user().get_repos()
            for repo in git_repos:
                repos.append({
                    'id': str(repo.id), 
                    'name': repo.name,
                    'description': repo.description
                })
        else:
            git_repo = g.get_user().get_repo(f"{repo_name}")
            git_branches =  git_repo.get_branches()

            repos.append({
                'id': git_repo.id,
                'name': git_repo.name,
                'description': git_repo.description,
                'branches': [branch.name for branch in git_branches]
            })
        response['data'] = repos
    except Exception as e:
        logging.warn(str(e))
        response['status'] = 'error'
        response['message'] = 'Error getting repository'
    finally:
        return JSONResponse(response)

