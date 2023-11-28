from datetime import datetime, timedelta
from typing import Optional, Annotated

from fastapi import FastAPI, Depends, HTTPException, Request, status, UploadFile
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.responses import RedirectResponse
from pydantic import BaseModel
from jose import JWTError, jwt

from ..models import User
from .utils import Utils
from ..exceptions import UnauthorizedException, UnauthorizedAdminException
from ..constants import JWT_SECRET_KEY, JWT_ALGORITHM, API_VERSION

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"api/{API_VERSION}/token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str

class UserData(BaseModel):
    email: str
    name: str
    password: str
    
def authenticate(email: str, password: str):
    '''
    Function for authenticating user

    @param email Email Address
    @param password Password
    @return User Instance or None
    '''
    user = User.get_by_email(email)
    if user and Utils.check_hashed_password(password, user.password):
        return user
    return None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_session(request: Request):
    if 'user_id' not in request.session.keys():
        raise UnauthorizedException
    return request.session

async def get_admin_session(request: Request):
    if 'admin_id' not in request.session.keys():
        raise UnauthorizedAdminException
    return request.session

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: Optional[str] = payload.get("email")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = User.get_by_email(token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_session_user(session: Annotated[dict, Depends(get_session)]):
    user_id = session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    return User.get(user_id)

def identity(payload):
    user_id = payload['identity']
    return User.get(user_id)
