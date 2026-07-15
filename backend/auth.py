import os
import uuid
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import bcrypt
import jwt
from jwt import PyJWTError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from .database import db

logger = logging.getLogger(__name__)

# Auth settings
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "CHANGE_THIS_TO_A_RANDOM_SECRET_IN_PRODUCTION"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

auth_router = APIRouter(prefix="/auth")


class UserRole(str, Enum):
    ADMIN = "admin"
    REPORTER = "reporter"


# --- Pydantic Models ---
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


# --- Password helpers ---
# Use bcrypt directly. passlib 1.7.x is unmaintained and breaks with bcrypt>=4.1
# (missing bcrypt.__about__) and can raise false "password too long" errors.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        password_bytes = plain_password.encode("utf-8")
        hash_bytes = (
            hashed_password.encode("utf-8")
            if isinstance(hashed_password, str)
            else hashed_password
        )
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except (ValueError, TypeError) as e:
        logger.warning(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    if password is None:
        raise ValueError("password is required")
    # bcrypt silently truncates past 72 bytes; fail clearly instead
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("password cannot be longer than 72 bytes")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


# --- User persistence helpers ---
async def get_user(email: str) -> Optional[UserInDB]:
    user = await db.users.find_one({"email": email})
    if user:
        return UserInDB(**user)
    return None


async def create_user_record(
    email: str,
    username: str,
    password: str,
    role: UserRole = UserRole.REPORTER,
) -> User:
    """
    Create a user in the database.

    Raises HTTPException 400 if email is already registered.
    """
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(password)

    user_obj = UserInDB(
        id=user_id,
        email=email,
        username=username,
        role=role,
        hashed_password=hashed_password,
        created_at=datetime.utcnow(),
        is_active=True,
    )

    user_dict = user_obj.dict()
    await db.users.insert_one(user_dict)
    logger.info(f"Created user {email} with ID {user_id} (role={role.value})")
    return User(**user_dict)


async def authenticate_user(email: str, password: str) -> Optional[UserInDB]:
    try:
        user = await get_user(email)
        if not user:
            logger.warning(f"Authentication failed: User with email {email} not found")
            return None

        if not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password for user {email}")
            return None

        logger.info(f"User {email} authenticated successfully")
        return user
    except Exception as e:
        logger.error(f"Authentication error for {email}: {str(e)}")
        return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        user_role: str = payload.get("role")
        if user_id is None or user_role is None:
            logger.warning("Token missing user_id or role")
            raise credentials_exception
        token_data = TokenData(user_id=user_id, role=user_role)
    except PyJWTError as e:
        logger.error(f"JWT decoding error: {e}")
        raise credentials_exception

    user_doc = await db.users.find_one({"id": token_data.user_id})
    if user_doc is None:
        logger.warning(
            f"User {token_data.user_id} not found in DB after token validation"
        )
        raise credentials_exception
    return User(**user_doc)


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
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
        data={"sub": user.id, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
    }


@auth_router.post("/register", response_model=User)
async def register_user(user_data: UserCreate):
    """Public registration always creates a reporter. Admins cannot self-promote."""
    try:
        return await create_user_record(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            role=UserRole.REPORTER,
        )
    except HTTPException:
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


@auth_router.post("/change-password")
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
