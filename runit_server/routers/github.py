import logging
from typing import  Any, Optional
import aiofiles
import requests

from fastapi.responses import JSONResponse, RedirectResponse
from fastapi import APIRouter, HTTPException, Request, Depends, status

from ..core import flash
from ..common import get_session
from ..models import User


from github import Github, Auth, GithubException

from ..constants import (
    GITHUB_APP_CLIENT_ID,
    GITHUB_APP_CLIENT_SECRET
)

github_router = APIRouter(
    prefix="/github",
    tags=["github"]
)

async def get_access_token(user: User, code: str):
    g = Github()
    app = g.get_oauth_application(GITHUB_APP_CLIENT_ID, GITHUB_APP_CLIENT_SECRET)
    token = app.get_access_token(code)
    auth = Auth.Token(token.token)
    g = Github(auth=auth)
    
    user.gat = token.token
    user.grt = str(token.refresh_token)
    user.save()
    
    return g

async def user_access_token(access_token):
    auth = Auth.Token(access_token)
    g = Github(auth=auth)
    
    return g

async def refresh_access_token(user: User):
    logging.info(f"Old Token: {user.gat}")
    g = Github()
    app = g.get_oauth_application(GITHUB_APP_CLIENT_ID, GITHUB_APP_CLIENT_SECRET)
    token = app.refresh_access_token(user.grt)
    auth = app.get_app_user_auth(token)
    g = Github(auth=auth)
    
    user.gat = token.token
    user.grt = str(token.refresh_token)
    user.save()
    logging.info(f"New Token: {token.token}")
    return g

async def fetch_repositories(g: Github, repo_name: Optional[str] = None)-> list[dict]:
    logging.info("Fetching repos...")
    repos: list[dict] = []
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
    return repos

@github_router.post('/webhook')
async def github_webhook(request: Request):
    data = await request.form()
    print(data._dict)
    return JSONResponse({'status': True, 'message': 'Webhook Received'})
    
@github_router.get('/callback', dependencies=[Depends(get_session)])
async def github_callback(request: Request):
    user = User.get(request.session['user_id'])
    response = {'status': 'success'}
    try:
        code = request.query_params.get('code')
        action = request.query_params.get('setup_action')
        
        g = await get_access_token(user, code) # type: ignore
        if not action:
            return RedirectResponse(f"https://github.com/apps/runit-app/installations/new/permissions?target_id={g.get_user().id}", status_code=status.HTTP_303_SEE_OTHER)
        
        flash(request, 'Successfully connected to Github', 'success')
        return RedirectResponse(request.url_for('list_user_projects'), status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        # logging.exception(e)
        logging.warn(str(e))
        flash(request, 'Error connecting to Github', 'danger')
        return RedirectResponse(request.url_for('list_user_projects'), status_code=status.HTTP_303_SEE_OTHER)


@github_router.get('/repos', dependencies=[Depends(get_session)])
@github_router.get('/repos/{repo_name}', dependencies=[Depends(get_session)])
async def get_repos(request: Request, repo_name: Optional[str] = None):
    user = User.get(request.session['user_id'])  
    error_count = 0
    response: dict = {'status': 'success'}
    repos: list[dict] = []
    
    try:
        if not user or not user.gat:
            raise Exception('User is not authenticated')

        g = await user_access_token(user.gat) # type: ignore
        repos = await fetch_repositories(g, repo_name)
        response['data'] = repos
    except GithubException:
        error_count += 1
        
        if error_count >= 2:
            raise Exception('Too many exceptions')
        g = await refresh_access_token(user) # type: ignore
        response['data'] = await fetch_repositories(g)
    except requests.ConnectionError:
        logging.error('Connection error')
        response['status'] = 'error'
        response['message'] = 'Error connecting to github'
    except Exception as e:
        logging.exception(e)
        response['status'] = 'error'
        response['message'] = 'Expired access tokens'
    finally:
        return JSONResponse(response)

