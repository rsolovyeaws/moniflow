import os
import jwt
import datetime
import logging
import hashlib
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from dotenv import load_dotenv
from database import users_collection, create_admin_user, store_refresh_token, revoke_refresh_token, get_refresh_token
from contextlib import asynccontextmanager


SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI startup."""
    await create_admin_user()  # Ensure admin user is created at startup
    yield

app = FastAPI(lifespan=lifespan)

# Pydantic models
class User(BaseModel):
    username: str
    role: str

class UserInDB(User):
    hashed_password: str
    
class UserRegister(BaseModel):
    username: str
    password: str
    email: EmailStr
    role: str = "user"

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

# Utility functions
def hash_email(email: str) -> str:
    """Hashes the email using SHA-256 for security."""
    return hashlib.sha256(email.encode()).hexdigest()

async def get_user(username: str):
    return await users_collection.find_one({"username": username})

async def create_user(username: str, password: str, email: str, role: str = "user"):
    hashed_password = pwd_context.hash(password)
    hashed_email = hash_email(email)
    user_data = {"username": username, "hashed_password": hashed_password, "email": hashed_email, "role": role}
    await users_collection.insert_one(user_data)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        user = await users_collection.find_one({"username": username}, {"_id": 0, "username": 1, "role": 1})
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return User(username=user["username"], role=user["role"])
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.post("/register")
async def register(user: UserRegister, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
      raise HTTPException(status_code=403, detail="Only admin can register new users")  
    
    try:
        existing_user = await get_user(user.username)
        existing_email = await users_collection.find_one({"email": hash_email(user.email)})
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        await create_user(user.username, user.password, user.email, user.role)
        return {"message": f"User {user.username} created with role {user.role}"}
    
    except HTTPException as e:
        logger.error(f"Error registering user: {e}")
        raise e

    except Exception as e:
        logger.error(f"Unexpected error registering user: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    hashed_email = hash_email(form_data.username)
    user = await users_collection.find_one({"$or": [{"username": form_data.username}, {"email": hashed_email}]})
    
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user["username"]})
    refresh_token = create_refresh_token(data={"sub": user["username"]})
    
    await store_refresh_token(user["username"], refresh_token)
    
    return {"access_token": access_token, "refresh_token": refresh_token,"token_type": "bearer"}

@app.post("/refresh")
async def refresh_token(refresh_token:str = Header(...)):
    payload = verify_token(refresh_token)
    username = payload.get("sub")
    
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    stored_token = await get_refresh_token(username)
    if stored_token != refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked token")
                       
    new_access_token = create_access_token(data={"sub": username})
    return {"access_token": new_access_token, "token_type": "bearer"}

@app.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    await revoke_refresh_token(current_user.username)
    return {"message": "Logged out successfully"}

@app.get("/users")
async def list_users(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
      raise HTTPException(status_code=403, detail="Only admin can list users")  
    
    users_cursor = users_collection.find({}, {"_id": 0, "username": 1, "role": 1})
    users = await users_cursor.to_list(length=100)
    
    return {"users": users} 
 
@app.get("/users/me", response_model=User)
async def get_current_user_data(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        user = await get_user(username)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        return User(username=user["username"], role=user["role"])
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@app.get("/users/{username}")
async def delete_user(username:str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
      raise HTTPException(status_code=403, detail="Only admin can delete users")  
    
    result = await users_collection.delete_one({"username": username})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User {username} deleted"}


@app.get("/slow-response")
async def slow_response():
    import asyncio
    await asyncio.sleep(10)  # Delay for 10 seconds
    return {"message": "This is a slow response"}