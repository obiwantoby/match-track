import os
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# Replace jose with PyJWT
import jwt # For PyJWT
from jwt import PyJWTError # General PyJWT error, or use InvalidTokenError if preferred and available
# from jose import JWTError, jwt # REMOVE THIS LINE
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
import logging

# This will be initialized in server.py and imported here
# For now, to avoid circular imports or complex setup, we'll assume db is passed or configured
# A better approach might be a shared config module.
# For this step, we'll define it here and you can adjust server.py to provide it.
# Or, more simply, auth.py can import it from server.py if server.py defines it early.

# Assuming MONGO_URL and DB_NAME are in the environment
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get("DB_NAME", "shooting_matches_db")]

logger = logging.getLogger(__name__)

# Auth settings (consider moving to a config.py if they grow)
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "CHANGE_THIS_TO_A_RANDOM_SECRET_IN_PRODUCTION"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token") # Adjusted path

auth_router = APIRouter(prefix="/auth") # Removed /api prefix as it will be added by main app

# User role enumeration
class UserRole(str, Enum):
    ADMIN = "admin"
    REPORTER = "reporter"

# --- Pydantic Models for Authentication ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str


class TokenData(BaseModel):
    user_id: str
    role: str


class UserBase(BaseModel):
    email: EmailStr
    username: str
    role: UserRole = UserRole.REPORTER


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class UserInDB(User):
    hashed_password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

# --- Authentication Helper Functions ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


async def get_user(email: str) -> Optional[UserInDB]:
    user = await db.users.find_one({"email": email})
    if user:
        return UserInDB(**user)
    return None


async def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    try:
        user = await get_user(email)
        if not user:
            logger.warning(f"Authentication failed: User with email {email} not found")
            return None # Changed from False to None for consistency

        if not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password for user {email}")
            return None # Changed from False to None

        logger.info(f"User {email} authenticated successfully")
        return user
    except Exception as e:
        logger.error(f"Authentication error for {email}: {str(e)}")
        return None # Changed from False to None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Use PyJWT's encode method
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Use PyJWT's decode method
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        user_role: str = payload.get("role")
        if user_id is None or user_role is None: # Keep this check
            logger.warning("Token missing user_id or role")
            raise credentials_exception
        token_data = TokenData(user_id=user_id, role=user_role)
    except PyJWTError as e: # Catch PyJWT's specific errors (e.g., ExpiredSignatureError, InvalidTokenError)
        logger.error(f"JWT decoding error: {e}")
        raise credentials_exception
    
    user_doc = await db.users.find_one({"id": token_data.user_id}) # Renamed user to user_doc to avoid conflict
    if user_doc is None:
        logger.warning(f"User {token_data.user_id} not found in DB after token validation")
        raise credentials_exception
    return User(**user_doc)


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# This function is used by non-auth routes as well, but depends on get_current_active_user
# It's fine to keep it here if auth.py is the central place for user identity and permissions
async def get_admin_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user

# --- Authentication Routes ---
@auth_router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role.value}, expires_delta=access_token_expires # Ensure role is string
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value, # Ensure role is string
    }


@auth_router.post("/register", response_model=User)
async def register_user(user_data: UserCreate):
    try:
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(user_data.password)

        user_obj = UserInDB(
            id=user_id,
            email=user_data.email,
            username=user_data.username,
            role=user_data.role,
            hashed_password=hashed_password,
            created_at=datetime.utcnow(),
            is_active=True,
        )

        user_dict = user_obj.dict()
        logger.info(f"Registering new user: {user_data.email} with ID {user_id}")
        await db.users.insert_one(user_dict)
        logger.info(f"User registered with result: {user_dict['id']}") # Corrected logging

        return User(**user_dict)
    except HTTPException as he:
        logger.error(f"Registration HTTP error: {str(he)}")
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@auth_router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@auth_router.post("/change-password") # Removed response_model=Dict[str, bool] for simplicity, can be added back
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
):
    user_in_db = await db.users.find_one({"id": current_user.id})
    if not user_in_db:
        raise HTTPException(status_code=404, detail="User not found")

    user_obj = UserInDB(**user_in_db)
    if not verify_password(password_data.current_password, user_obj.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    hashed_password = get_password_hash(password_data.new_password)
    await db.users.update_one(
        {"id": current_user.id}, {"$set": {"hashed_password": hashed_password}}
    )
    return {"success": True}
