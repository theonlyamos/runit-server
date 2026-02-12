import base64
from pathlib import Path
from typing import Annotated, Optional
import aiofiles

from fastapi.responses import JSONResponse
from fastapi import APIRouter, Form, HTTPException, Request, Depends,\
    status, UploadFile
from pydantic import BaseModel, EmailStr

from ...common import get_current_user
from ...common import Utils
from ...models import Project
from ...models import User
from ...models import Function

from ...constants import RUNIT_WORKDIR

account_api = APIRouter(
    prefix="/account",
    tags=["account api"],
    dependencies=[Depends(get_current_user)],
)

class AccountData(BaseModel):
    email: EmailStr
    name: str
    password: str

class PasswordData(BaseModel):
    password: str
    new_password: str
    confirm_password: str

@account_api.get('/')
async def api_user_account(user: Annotated[User, Depends(get_current_user)]):
    return JSONResponse(user.json())

@account_api.get('/projects')
async def api_list_user_projects(user: Annotated[User, Depends(get_current_user)]):
    projects = await Project.get_by_user(user.id) # type: ignore
    json_projects = []
    for project in projects:
        json_projects.append(project.json())
    
    return JSONResponse(json_projects)

 
@account_api.get('/profile')
async def api_user_profile(user: Annotated[User, Depends(get_current_user)]):
    user_json = user.json()
    del user_json['password']
    del user_json['gat']
    del user_json['grt']
    
    print('---Account Info', user_json)
    
    return JSONResponse(user_json)

@account_api.post('/profile')
async def api_update_user_profile(
    user: Annotated[User, Depends(get_current_user)],
    account: AccountData
):
    response = {
        'status': 'success', 
        'message': 'Profile updated successfully'
    }

    if not user or not user.password:
        response['status'] = 'error'
        response['message'] = 'User not found'
    elif Utils.check_hashed_password(account.password, user.password):
        user.email = account.email
        user.name = account.name
        await user.save()
        response['user'] = user.json() # type: ignore
    else:
        response['status'] = 'error'
        response['message'] = 'Unauthorized Action'
        
    return JSONResponse(response)

@account_api.post('/password')
async def api_update_user_password(
    user: Annotated[User, Depends(get_current_user)],
    data: PasswordData
):
    response = {
        'status': 'success', 
        'message': 'Password changed successfully'
    }

    if not user or not user.password:
        response['status'] = 'error'
        response['message'] = 'User not found'
    elif not Utils.check_hashed_password(data.password, user.password):
        response['status'] = 'error'
        response['message'] = 'Unauthorized Action'
    elif data.new_password != data.confirm_password:
        response['status'] = 'error'
        response['message'] = 'Passwords do not watch'
    else:
        await user.reset_password(data.new_password)
        
    return JSONResponse(response)
    
@account_api.post('/image')
async def api_update_user_image(
    request: Request,
    user: Annotated[User, Depends(get_current_user)], 
    file: UploadFile
):
    if not user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user session")

    user_id = str(user.id)
    encoded_filename = base64.urlsafe_b64encode(str(file.filename).encode('utf-8'))
    encoded_filename = encoded_filename.decode('utf-8').replace('=','').replace('.', '')
    filename = f"{user_id}_{encoded_filename}_{Path(str(file.filename)).suffix}"
    upload_dir = Path(RUNIT_WORKDIR, 'accounts', user_id)
    
    try:
        if not upload_dir.exists():
            upload_dir.mkdir()
            
        upload_path = upload_dir.joinpath(filename)

        contents = await file.read()
        async with aiofiles.open(str(upload_path), 'wb') as f:
            await f.write(contents)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading image",
        )
    finally:
        await file.close()
    
    user.image = filename
    await user.save()  
    
    return JSONResponse({'status': 'success', 'filepath': str(request.url_for('uploads', path=str(user.id)+'/'+user.image))})
