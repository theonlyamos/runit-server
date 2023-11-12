from fastapi import FastAPI, Depends, Request, HTTPException
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from typing import Annotated

app = FastAPI()

# Setup session middleware
app.add_middleware(
    SessionMiddleware, 
    secret_key="secret-session-key",
    max_age=3600,
    https_only=True
)

async def get_session(request: Request):
    return await request.session()

async def get_current_user(session: dict = Depends(get_session)):
    user_id = session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    return user_id

@app.get("/login")
async def login(session: Annotated[dict, Depends(get_session)]):
    session["user_id"] = "user123"
    return RedirectResponse(url="/")

@app.get("/protected")
async def protected(current_user: str = Depends(get_current_user)):
   return f"Hello {current_user}"


from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt

# Create the app
app = FastAPI()

# Setup session handling
SECRET_KEY = "your-secret-key"
app.add_middleware(
    WSGIMiddleware, 
    secret_key=SECRET_KEY,
    session_cookie="mysession"
)

# OAuth2 setup for login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Fake user DB
USER_DB = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "fakehashedsecret",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True,
    },
}

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Provide a method to create access tokens. The create_access_token()
# function is used to actually generate the token
def authenticate_user(username: str, password: str):
    user = USER_DB.get(username, None)
    if not user:
        return False 
    if not verify_password(password, user['hashed_password']):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

# Login endpoint
@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user['username']}, expires_delta=access_token_expires
    )
    session_token = sha256(access_token.encode()).hexdigest()
    response = JSONResponse({"access_token": access_token, "token_type": "bearer"})

    response.set_cookie(
        "session_token",
        value=session_token,
        httponly=True, 
        expires=1800,
        max_age=1800,
    )

    return response

# Provide a method to get current user
async def get_current_user(session: Session = Depends(get_session)):
    user_token = session.get("user")
    if not user_token:
        raise HTTPException(status_code=400, detail="Not logged in")
    return user_token

# Secure endpoint  
@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user