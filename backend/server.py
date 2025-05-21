from fastapi import FastAPI, APIRouter, HTTPException, Body, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import io
from typing import Dict, List, Optional, Any, Union
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from fastapi.responses import StreamingResponse
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# MongoDB connection
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get("DB_NAME", "shooting_matches_db")]

# Auth settings
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "CHANGE_THIS_TO_A_RANDOM_SECRET_IN_PRODUCTION"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/api/auth")


# User role enumeration
class UserRole(str, Enum):
    ADMIN = "admin"
    REPORTER = "reporter"


# Match Type enumeration
class BasicMatchType(str, Enum):
    NMC = "NMC"
    SIXHUNDRED = "600"
    NINEHUNDRED = "900"
    PRESIDENTS = "Presidents"


# Aggregate Type enumeration
class AggregateType(str, Enum):
    NONE = "None"
    EIGHTEEN_HUNDRED_2X900 = "1800 (2x900)"
    EIGHTEEN_HUNDRED_3X600 = "1800 (3x600)"
    TWENTY_SEVEN_HUNDRED = "2700 (3x900)"


# Caliber Type enumeration
class CaliberType(str, Enum):
    TWENTYTWO = ".22"
    CENTERFIRE = "CF"
    FORTYFIVE = ".45"
    SERVICEPISTOL = "Service Pistol"
    SERVICEREVOLVER = "Service Revolver"
    DR = "DR"


# Define Models
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


class ShooterBase(BaseModel):
    name: str
    nra_number: Optional[str] = None
    cmp_number: Optional[str] = None


class ShooterCreate(ShooterBase):
    pass


class Shooter(ShooterBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Match Type Configuration
class MatchTypeInstance(BaseModel):
    type: BasicMatchType
    instance_name: str  # e.g., "NMC1", "600_1"
    calibers: List[CaliberType]


# Match Definition
class MatchBase(BaseModel):
    name: str
    date: datetime
    location: str
    match_types: List[MatchTypeInstance]
    aggregate_type: AggregateType = AggregateType.NONE


class MatchCreate(MatchBase):
    pass


class Match(MatchBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Score Stage (individual component scores)
class ScoreStage(BaseModel):
    name: str  # e.g., "SF", "TF1", "RF2"
    score: Optional[int] = None
    x_count: int = 0


# Score Entry
class ScoreBase(BaseModel):
    shooter_id: str
    match_id: str
    caliber: CaliberType
    match_type_instance: str  # e.g., "NMC1", "600_1"
    stages: List[ScoreStage]
    total_score: Optional[int] = None
    total_x_count: Optional[int] = None


class ScoreCreate(ScoreBase):
    pass


class Score(ScoreBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScoreWithDetails(Score):
    shooter_name: str
    match_name: str
    match_date: datetime
    match_location: str


# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


# Helper functions for match configuration
def get_stages_for_match_type(match_type: BasicMatchType) -> Dict[str, Any]:
    """Return the stage names and subtotal structure for a given match type"""
    if match_type == BasicMatchType.NMC:
        return {
            "entry_stages": ["SF", "TF", "RF"],
            "subtotal_stages": [],
            "subtotal_mappings": {},
            "max_score": 300,
        }
    elif match_type == BasicMatchType.SIXHUNDRED:
        return {
            "entry_stages": ["SF1", "SF2", "TF1", "TF2", "RF1", "RF2"],
            "subtotal_stages": [],
            "subtotal_mappings": {},
            "max_score": 600,
        }
    elif match_type == BasicMatchType.NINEHUNDRED:
        # Modified to include SFNMC, TFNMC, RFNMC as entry stages
        # All values will be entered manually by users (SF1, SF2, TF1, TF2, RF1, RF2, SFNMC, TFNMC, RFNMC)
        # No automatic calculation of subtotals
        return {
            "entry_stages": ["SF1", "SF2", "TF1", "TF2", "RF1", "RF2", "SFNMC", "TFNMC", "RFNMC"],
            "subtotal_stages": [],
            "subtotal_mappings": {},
            "max_score": 900,
        }
    elif match_type == BasicMatchType.PRESIDENTS:
        return {
            "entry_stages": ["SF1", "SF2", "TF", "RF"],
            "subtotal_stages": [],
            "subtotal_mappings": {},
            "max_score": 400,
        }
    return {
        "entry_stages": [],
        "subtotal_stages": [],
        "subtotal_mappings": {},
        "max_score": 0,
    }


def get_match_type_max_score(match_type: BasicMatchType) -> int:
    """Return the maximum possible score for a match type"""
    return get_stages_for_match_type(match_type)["max_score"]


async def get_user(email: str):
    try:
        user_dict = await db.users.find_one({"email": email})
        if user_dict:
            return UserInDB(**user_dict)
        logger.warning(f"User with email {email} not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving user {email}: {str(e)}")
        return None


async def authenticate_user(email: str, password: str):
    try:
        user = await get_user(email)
        if not user:
            logger.warning(f"Authentication failed: User with email {email} not found")
            return False

        if not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password for user {email}")
            return False

        logger.info(f"User {email} authenticated successfully")
        return user
    except Exception as e:
        logger.error(f"Authentication error for {email}: {str(e)}")
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id, role=role)
    except JWTError:
        raise credentials_exception

    user = await db.users.find_one({"id": token_data.user_id})
    if user is None:
        raise credentials_exception

    return UserInDB(**user)


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_admin_user(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


# Authentication Routes
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
        data={"sub": user.id, "role": user.role}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role,
    }


@auth_router.post("/register", response_model=User)
async def register_user(user_data: UserCreate):
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create new user with explicitly set ID
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

        # Insert user into database
        result = await db.users.insert_one(user_dict)
        logger.info(f"User registered with result: {result.inserted_id}")

        # Return user without hashed password
        return User(**user_dict)
    except HTTPException as he:
        # Re-raise HTTP exceptions as-is
        logger.error(f"Registration HTTP error: {str(he)}")
        raise
    except Exception as e:
        # Log and convert other exceptions
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@auth_router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@auth_router.post("/change-password", response_model=Dict[str, bool])
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
):
    # Get the user from database with the hashed password
    user_in_db = await db.users.find_one({"id": current_user.id})
    if not user_in_db:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    user_obj = UserInDB(**user_in_db)
    if not verify_password(password_data.current_password, user_obj.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Hash new password
    hashed_password = get_password_hash(password_data.new_password)

    # Update password
    await db.users.update_one(
        {"id": current_user.id}, {"$set": {"hashed_password": hashed_password}}
    )

    return {"success": True}


# User management routes (admin only)
@api_router.get("/users", response_model=List[User])
async def get_users(current_user: User = Depends(get_admin_user)):
    users = await db.users.find().to_list(1000)
    return [User(**user) for user in users]


@api_router.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: str, user_data: UserBase, current_user: User = Depends(get_admin_user)
):
    # Check if user exists
    existing_user = await db.users.find_one({"id": user_id})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user
    await db.users.update_one({"id": user_id}, {"$set": user_data.dict()})

    # Get updated user
    updated_user = await db.users.find_one({"id": user_id})
    return User(**updated_user)


@api_router.delete("/users/{user_id}", response_model=Dict[str, bool])
async def delete_user(user_id: str, current_user: User = Depends(get_admin_user)):
    # Prevent deleting the current user
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    # Delete user
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"success": True}


# Database reset endpoint (admin only)
@api_router.post("/reset-database", response_model=Dict[str, bool])
async def reset_database(current_user: User = Depends(get_admin_user)):
    """Reset the database to a clean state, preserving only the current admin user"""
    # Get current admin user details
    admin_user = await db.users.find_one({"id": current_user.id})

    # Drop all collections
    for collection_name in await db.list_collection_names():
        if collection_name != "users":  # Don't drop users yet
            await db[collection_name].drop()

    # Remove all users except the current admin
    await db.users.delete_many({"id": {"$ne": current_user.id}})

    # Return success
    return {"success": True}


# Shooter Routes
@api_router.post("/shooters", response_model=Shooter)
async def create_shooter(
    shooter: ShooterCreate, current_user: User = Depends(get_current_active_user)
):
    # Only admins can create shooters
    if current_user.role == UserRole.REPORTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    shooter_obj = Shooter(**shooter.dict())
    result = await db.shooters.insert_one(shooter_obj.dict())
    return shooter_obj


@api_router.get("/shooters", response_model=List[Shooter])
async def get_shooters(current_user: User = Depends(get_current_active_user)):
    shooters = await db.shooters.find().to_list(1000)
    return [Shooter(**shooter) for shooter in shooters]


@api_router.get("/shooters/{shooter_id}", response_model=Shooter)
async def get_shooter(
    shooter_id: str, current_user: User = Depends(get_current_active_user)
):
    shooter = await db.shooters.find_one({"id": shooter_id})
    if not shooter:
        raise HTTPException(status_code=404, detail="Shooter not found")
    return Shooter(**shooter)


# Match Routes
@api_router.post("/matches", response_model=Match)
async def create_match(
    match: MatchCreate, current_user: User = Depends(get_current_active_user)
):
    # Only admins can create matches
    if current_user.role == UserRole.REPORTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    match_obj = Match(**match.dict())
    result = await db.matches.insert_one(match_obj.dict())
    return match_obj


@api_router.get("/matches", response_model=List[Match])
async def get_matches(current_user: User = Depends(get_current_active_user)):
    matches = await db.matches.find().sort("date", -1).to_list(1000)
    return [Match(**match) for match in matches]


@api_router.get("/matches/{match_id}", response_model=Match)
async def get_match(
    match_id: str, current_user: User = Depends(get_current_active_user)
):
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return Match(**match)


@api_router.put("/matches/{match_id}", response_model=Match)
async def update_match(
    match_id: str,
    match_update: MatchCreate,
    current_user: User = Depends(get_current_active_user)
):
    # Only admins can update matches
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    
    # Check if match exists
    existing_match = await db.matches.find_one({"id": match_id})
    if not existing_match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Update match
    match_obj = Match(id=match_id, **match_update.dict())
    
    # Update in database
    await db.matches.update_one(
        {"id": match_id}, 
        {"$set": match_obj.dict(exclude={"id"})}
    )
    
    # Get updated match
    updated_match = await db.matches.find_one({"id": match_id})
    if not updated_match:
        raise HTTPException(status_code=500, detail="Failed to update match")
    
    return Match(**updated_match)


@api_router.delete("/matches/{match_id}")
async def delete_match(
    match_id: str, current_user: User = Depends(get_current_active_user)
):
    # Only admins can delete matches
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete matches")
    
    # Find the match to ensure it exists
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Delete all scores associated with this match
    delete_scores_result = await db.scores.delete_many({"match_id": match_id})
    
    # Delete match configuration
    await db.match_configs.delete_many({"match_id": match_id})
    
    # Delete the match itself
    delete_match_result = await db.matches.delete_one({"id": match_id})
    
    if delete_match_result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete match")
    
    return {
        "success": True,
        "message": f"Match deleted successfully along with {delete_scores_result.deleted_count} related scores"
    }


@api_router.get("/match-types")
async def get_match_types(current_user: User = Depends(get_current_active_user)):
    """Get all available match types with their stage definitions"""
    result = {}
    for match_type in BasicMatchType:
        stages_info = get_stages_for_match_type(match_type)
        result[match_type] = {
            "entry_stages": stages_info["entry_stages"],
            "subtotal_stages": stages_info["subtotal_stages"],
            "subtotal_mappings": stages_info["subtotal_mappings"],
            "max_score": stages_info["max_score"],
        }
    return result


@api_router.get("/match-config/{match_id}")
async def get_match_config(
    match_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get the detailed configuration for a match, including all stages for each match type"""
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match_obj = Match(**match)

    # Build detailed configuration
    config = {
        "match_id": match_obj.id,
        "match_name": match_obj.name,
        "date": match_obj.date,
        "location": match_obj.location,
        "aggregate_type": match_obj.aggregate_type,
        "match_types": [],
    }

    for match_type_instance in match_obj.match_types:
        stages_info = get_stages_for_match_type(match_type_instance.type)
        config["match_types"].append(
            {
                "type": match_type_instance.type,
                "instance_name": match_type_instance.instance_name,
                "calibers": match_type_instance.calibers,
                "entry_stages": stages_info["entry_stages"],
                "subtotal_stages": stages_info["subtotal_stages"],
                "subtotal_mappings": stages_info["subtotal_mappings"],
                "max_score": stages_info["max_score"],
            }
        )

    return config


# Score Routes
@api_router.post("/scores", response_model=Score)
async def create_score(
    score: ScoreCreate, current_user: User = Depends(get_current_active_user)
):
    # Only admins can create scores
    if current_user.role == UserRole.REPORTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Get match configuration to determine if we need to add subtotals
    match = await db.matches.find_one({"id": score.match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match_obj = Match(**match)
    match_type_instance = next(
        (
            mt
            for mt in match_obj.match_types
            if mt.instance_name == score.match_type_instance
        ),
        None,
    )

    if not match_type_instance:
        raise HTTPException(status_code=400, detail="Invalid match type instance")

    # Get the match type configuration
    stages_info = get_stages_for_match_type(match_type_instance.type)

    # Calculate total score and X count from the entry stages, skipping null values
    total_score = sum(stage.score for stage in score.stages if stage.score is not None)
    total_x_count = sum(stage.x_count for stage in score.stages if stage.x_count is not None)

    # Create the score object with calculated totals
    score_dict = score.dict()
    score_dict.update({"total_score": total_score, "total_x_count": total_x_count})

    score_obj = Score(**score_dict)
    await db.scores.insert_one(score_obj.dict())
    return score_obj


@api_router.put("/scores/{score_id}", response_model=Score)
async def update_score(
    score_id: str,
    score_update: ScoreCreate,
    current_user: User = Depends(get_current_active_user),
):
    # Only admins can update scores
    if current_user.role == UserRole.REPORTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )

    # Check if score exists
    existing_score = await db.scores.find_one({"id": score_id})
    if not existing_score:
        raise HTTPException(status_code=404, detail="Score not found")

    # Get match configuration
    match = await db.matches.find_one({"id": score_update.match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    match_obj = Match(**match)
    match_type_instance = next(
        (
            mt
            for mt in match_obj.match_types
            if mt.instance_name == score_update.match_type_instance
        ),
        None,
    )

    if not match_type_instance:
        raise HTTPException(status_code=400, detail="Invalid match type instance")

    # Calculate total score and X count from the entry stages, skipping null values
    total_score = sum(stage.score for stage in score_update.stages if stage.score is not None)
    total_x_count = sum(stage.x_count for stage in score_update.stages if stage.x_count is not None)

    # Update the score object with calculated totals
    score_dict = score_update.dict()
    score_dict.update({"total_score": total_score, "total_x_count": total_x_count})

    # Update score
    await db.scores.update_one({"id": score_id}, {"$set": score_dict})

    # Get updated score
    updated_score = await db.scores.find_one({"id": score_id})
    return Score(**updated_score)


@api_router.get("/scores", response_model=List[Score])
async def get_scores(
    match_id: Optional[str] = None,
    shooter_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    # Build query
    query = {}
    if match_id:
        query["match_id"] = match_id
    if shooter_id:
        query["shooter_id"] = shooter_id

    scores = await db.scores.find(query).to_list(1000)
    return [Score(**score) for score in scores]


@api_router.get("/scores/{score_id}", response_model=Score)
async def get_score(
    score_id: str, current_user: User = Depends(get_current_active_user)
):
    score = await db.scores.find_one({"id": score_id})
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    return Score(**score)


# Special Reports
@api_router.get("/match-report/{match_id}", response_model=Dict[str, Any])
async def get_match_report(
    match_id: str, current_user: User = Depends(get_current_active_user)
):
    # Get match details
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    match_obj = Match(**match)
    
    # Get all scores for this match
    scores = await db.scores.find({"match_id": match_id}).to_list(1000)
    
    # Build shooter data map
    shooter_ids = set(score["shooter_id"] for score in scores)
    shooters = {}
    for shooter_id in shooter_ids:
        shooter = await db.shooters.find_one({"id": shooter_id})
        if shooter:
            shooters[shooter_id] = Shooter(**shooter)
    
    # Get match configuration for subtotal calculations
    match_config = await get_match_config(match_id, current_user)
    match_types_config = {mt["instance_name"]: mt for mt in match_config["match_types"]}
    
    # Organize scores by shooter, match type instance, and caliber
    result = {
        "match": match_obj,
        "shooters": {}
    }
    
    for score in scores:
        score_obj = Score(**score)
        shooter_id = score_obj.shooter_id
        if shooter_id not in result["shooters"] and shooter_id in shooters:
            result["shooters"][shooter_id] = {
                "shooter": shooters[shooter_id],
                "scores": {}
            }
        
        if shooter_id in result["shooters"]:
            shooter_data = result["shooters"][shooter_id]
            match_type_instance = score_obj.match_type_instance
            caliber = score_obj.caliber
            
            key = f"{match_type_instance}_{caliber}"
            
            # Add calculated subtotals if this match type has them
            if match_type_instance in match_types_config:
                mt_config = match_types_config[match_type_instance]
                match_type = mt_config["type"]
                stages_config = get_stages_for_match_type(match_type)
                
                subtotals = {}
                
                if stages_config["subtotal_mappings"]:
                    # Process subtotals based on match type
                    for subtotal_name, stage_names in stages_config["subtotal_mappings"].items():
                        subtotal_score = 0
                        subtotal_x_count = 0
                        
                        for stage in score_obj.stages:
                            if stage.name in stage_names:
                                subtotal_score += stage.score
                                subtotal_x_count += stage.x_count
                        
                        subtotals[subtotal_name] = {
                            "score": subtotal_score,
                            "x_count": subtotal_x_count
                        }
                
                shooter_data["scores"][key] = {
                    "score": {
                        "id": score_obj.id,  # Include the score ID
                        "match_type_instance": match_type_instance,
                        "caliber": caliber,
                        "total_score": score_obj.total_score,
                        "total_x_count": score_obj.total_x_count,
                        "stages": [
                            {
                                "name": stage.name,
                                "score": stage.score,
                                "x_count": stage.x_count
                            }
                            for stage in score_obj.stages
                        ]
                    },
                    "subtotals": subtotals
                }
    
    # Calculate and add aggregates if applicable
    if match_obj.aggregate_type != "None":
        for shooter_id, shooter_data in result["shooters"].items():
            shooter_data["aggregates"] = {}
    
    # Include match configuration in the result
    result["match_config"] = match_config
    
    return result

@api_router.get("/match-report/{match_id}/excel")
async def get_match_report_excel(
    match_id: str, current_user: User = Depends(get_current_active_user)
):
    # Get the match report data first (reuse existing function)
    report_data = await get_match_report(match_id, current_user)
    match_obj = report_data["match"]
    shooters_data = report_data["shooters"]
    
    # Create a new workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Match Report"
    
    # Define styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )
    
    # Add match details
    ws.append(["Match Report"])
    ws.merge_cells(f"A1:G1")
    cell = ws.cell(row=1, column=1)
    cell.font = Font(bold=True, size=16)
    cell.alignment = Alignment(horizontal="center")
    
    ws.append([])
    ws.append(["Match Name:", match_obj.name])
    ws.append(["Date:", match_obj.date.strftime("%Y-%m-%d")])
    ws.append(["Location:", match_obj.location])
    ws.append(["Aggregate Type:", match_obj.aggregate_type])
    ws.append([])
    
    # Add summary table header
    header_row = ["Shooter", "Average"]
    
    # Add headers for each match type and caliber
    for mt in match_obj.match_types:
        for caliber in mt.calibers:
            header_row.append(f"{mt.instance_name} ({caliber})")
    
    # Add Aggregate column if applicable
    if match_obj.aggregate_type != "None":
        header_row.append(match_obj.aggregate_type)
    
    ws.append(header_row)
    
    # Apply header styles
    for col in range(1, len(header_row) + 1):
        cell = ws.cell(row=8, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Auto-adjust column widths for headers
    for i, column_width in enumerate([20, 15] + [15] * (len(header_row) - 2), 1):
        ws.column_dimensions[get_column_letter(i)].width = column_width
    
    # Add data rows
    for shooter_id, shooter_data in shooters_data.items():
        shooter = shooter_data["shooter"]
        
        # Create a new row with the shooter name
        row = [shooter.name]
        
        # Will collect all valid scores for average calculation
        valid_scores = []
        score_rows = []
        
        # Add scores for each match type and caliber
        for mt in match_obj.match_types:
            for caliber in mt.calibers:
                # Try multiple key formats
                key_formats = [
                    f"{mt.instance_name}_{caliber}",
                    f"{mt.instance_name}_CaliberType.{caliber.replace('.', '').upper()}"
                ]
                
                # Try special case formats for known calibers
                if caliber == ".22":
                    key_formats.append(f"{mt.instance_name}_CaliberType.TWENTYTWO")
                elif caliber == "CF":
                    key_formats.append(f"{mt.instance_name}_CaliberType.CENTERFIRE")
                elif caliber == ".45":
                    key_formats.append(f"{mt.instance_name}_CaliberType.FORTYFIVE")
                elif caliber == "Service Pistol":
                    key_formats.append(f"{mt.instance_name}_CaliberType.SERVICEPISTOL")
                    key_formats.append(f"{mt.instance_name}_CaliberType.NINESERVICE")  # Legacy
                    key_formats.append(f"{mt.instance_name}_CaliberType.FORTYFIVESERVICE")  # Legacy
                elif caliber == "Service Revolver":
                    key_formats.append(f"{mt.instance_name}_CaliberType.SERVICEREVOLVER")
                elif caliber == "DR":
                    key_formats.append(f"{mt.instance_name}_CaliberType.DR")
                
                # Try to find a matching score
                score_data = None
                for key in key_formats:
                    if key in shooter_data["scores"]:
                        score_data = shooter_data["scores"][key]
                        break
                
                # Add the score to the row
                if score_data:
                    score_value = score_data["score"]["total_score"]
                    x_count = score_data["score"]["total_x_count"]
                    
                    # Check if this is a non-shot match (score is None/null)
                    if score_value is None:
                        # This is a non-shot match, display as "-" and don't include in average
                        score_rows.append("-")
                    else:
                        # This is a valid score (including 0 scores)
                        score_rows.append(f"{score_value} ({x_count}X)")
                        # Add to valid_scores (0 is a valid score, None is not)
                        valid_scores.append(score_value)
                else:
                    # No score found - display as - and don't include in average
                    score_rows.append("-")
        
        # Calculate average (if there are any valid scores)
        # Only include non-null scores in the average calculation
        non_null_scores = [score for score in valid_scores if score is not None]
        if non_null_scores:
            average_score = sum(non_null_scores) / len(non_null_scores)
            row.append(f"{average_score:.2f}")
        else:
            row.append("-")
            
        # Add all score rows
        row.extend(score_rows)
        
        # Add aggregate score if applicable
        if match_obj.aggregate_type != "None":
            if match_obj.aggregate_type == "1800 (3x600)" or match_obj.aggregate_type == "1800 (2x900)":
                # Calculate total across all calibers
                total_score = 0
                total_x_count = 0
                has_scores = False
                
                for key, score_data in shooter_data["scores"].items():
                    score_value = score_data["score"]["total_score"]
                    x_count = score_data["score"]["total_x_count"]
                    
                    # Skip non-shot matches (score is None)
                    if score_value is None:
                        continue
                        
                    total_score += score_value
                    total_x_count += x_count
                    has_scores = True
                
                if has_scores:
                    row.append(f"{total_score} ({total_x_count}X)")
                else:
                    row.append("-")
            elif "aggregates" in shooter_data and shooter_data["aggregates"]:
                agg_scores = []
                for agg_key, agg_data in shooter_data["aggregates"].items():
                    agg_scores.append(f"{agg_data['score']} ({agg_data['x_count']}X)")
                
                row.append(", ".join(agg_scores) if agg_scores else "-")
            else:
                row.append("-")
        
        ws.append(row)
    
    # Apply borders to data cells
    data_rows = len(shooters_data)
    for row in range(9, 9 + data_rows):
        for col in range(1, len(header_row) + 1):
            cell = ws.cell(row=row, column=col)
            cell.border = thin_border
            if col > 2:  # Align score columns to center
                cell.alignment = Alignment(horizontal="center")
            elif col == 2:  # Align average column to center
                cell.alignment = Alignment(horizontal="center")
    
    # Freeze panes to keep the shooter name and average columns visible when scrolling
    ws.freeze_panes = ws.cell(row=9, column=3)  # Freeze first two columns (A and B)
    
    # Add detailed score cards (one per shooter)
    for shooter_id, shooter_data in shooters_data.items():
        shooter = shooter_data["shooter"]
        ws_detail = wb.create_sheet(title=f"{shooter.name[:28]}")  # Limit sheet name length
        
        # Add shooter details
        ws_detail.append([f"Score Card - {shooter.name}"])
        ws_detail.merge_cells(f"A1:G1")
        cell = ws_detail.cell(row=1, column=1)
        cell.font = Font(bold=True, size=16)
        cell.alignment = Alignment(horizontal="center")
        
        ws_detail.append([])
        ws_detail.append(["Match:", match_obj.name])
        ws_detail.append(["Date:", match_obj.date.strftime("%Y-%m-%d")])
        ws_detail.append(["Location:", match_obj.location])
        
        if shooter.nra_number:
            ws_detail.append(["NRA Number:", shooter.nra_number])
        if shooter.cmp_number:
            ws_detail.append(["CMP Number:", shooter.cmp_number])
            
        ws_detail.append([])
        
        # For each match type and caliber, add detailed scores
        row_index = 9  # Starting row for score details
        
        for mt in match_obj.match_types:
            match_config = None
            for mt_config in report_data.get("match_config", {}).get("match_types", []):
                if mt_config["instance_name"] == mt.instance_name:
                    match_config = mt_config
                    break
            
            if not match_config:
                continue
                
            stages_config = get_stages_for_match_type(mt.type)
            
            for caliber in mt.calibers:
                # Try multiple key formats as in the summary
                key_formats = [
                    f"{mt.instance_name}_{caliber}",
                    f"{mt.instance_name}_CaliberType.{caliber.replace('.', '').upper()}"
                ]
                
                # Add special cases
                if caliber == ".22":
                    key_formats.append(f"{mt.instance_name}_CaliberType.TWENTYTWO")
                elif caliber == "CF":
                    key_formats.append(f"{mt.instance_name}_CaliberType.CENTERFIRE")
                elif caliber == ".45":
                    key_formats.append(f"{mt.instance_name}_CaliberType.FORTYFIVE")
                elif caliber == "Service Pistol":
                    key_formats.append(f"{mt.instance_name}_CaliberType.SERVICEPISTOL")
                    key_formats.append(f"{mt.instance_name}_CaliberType.NINESERVICE")
                    key_formats.append(f"{mt.instance_name}_CaliberType.FORTYFIVESERVICE")
                elif caliber == "Service Revolver":
                    key_formats.append(f"{mt.instance_name}_CaliberType.SERVICEREVOLVER")
                elif caliber == "DR":
                    key_formats.append(f"{mt.instance_name}_CaliberType.DR")
                
                # Try to find a matching score
                score_data = None
                for key in key_formats:
                    if key in shooter_data["scores"]:
                        score_data = shooter_data["scores"][key]
                        break
                
                if not score_data:
                    continue
                
                # Add header for this match type and caliber
                ws_detail.append([f"{mt.instance_name} - {caliber}"])
                ws_detail.merge_cells(f"A{row_index}:E{row_index}")
                cell = ws_detail.cell(row=row_index, column=1)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
                
                row_index += 1
                
                # Add stage headers
                header_row = ["Stage", "Score", "X Count"]
                ws_detail.append(header_row)
                
                # Apply header styles
                for col in range(1, len(header_row) + 1):
                    cell = ws_detail.cell(row=row_index, column=col)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                    cell.border = thin_border
                
                row_index += 1
                
                # Add stage scores
                stages = score_data["score"]["stages"]
                for stage in stages:
                    # Format the score and x_count correctly for display
                    score_display = "-" if stage["score"] is None else stage["score"]
                    x_count_display = "-" if stage["x_count"] is None else stage["x_count"]
                    
                    ws_detail.append([
                        stage["name"],
                        score_display,
                        x_count_display
                    ])
                    
                    # Apply borders to data cells
                    for col in range(1, len(header_row) + 1):
                        cell = ws_detail.cell(row=row_index, column=col)
                        cell.border = thin_border
                        if col > 1:  # Align score columns to center
                            cell.alignment = Alignment(horizontal="center")
                    
                    row_index += 1
                
                # Add total row
                ws_detail.append([
                    "Total",
                    score_data["score"]["total_score"],
                    score_data["score"]["total_x_count"]
                ])
                
                # Apply total row styling
                for col in range(1, len(header_row) + 1):
                    cell = ws_detail.cell(row=row_index, column=col)
                    cell.font = Font(bold=True)
                    cell.border = thin_border
                    if col > 1:  # Align score columns to center
                        cell.alignment = Alignment(horizontal="center")
                
                row_index += 2  # Space before next match type
        
        # Auto-adjust column widths
        for i, column_width in enumerate([15, 10, 10], 1):
            ws_detail.column_dimensions[get_column_letter(i)].width = column_width
    
    # Save to BytesIO object
    excel_file = io.BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)  # Rewind to beginning
    
    filename = f"match_report_{match_obj.name.replace(' ', '_')}_{match_obj.date.strftime('%Y-%m-%d')}.xlsx"
    
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Access-Control-Expose-Headers": "Content-Disposition"  # Important for CORS
    }
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )


def calculate_aggregates(scores, match):
    """Calculate aggregate scores based on match configuration"""
    aggregates = {}

    # 1800 (2x900) Aggregate
    if match.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_2X900:
        # Find all 900 match instances and group by caliber
        by_caliber = {}
        for key, score_data in scores.items():
            if any(
                mt.type == BasicMatchType.NINEHUNDRED and mt.instance_name in key
                for mt in match.match_types
            ):
                # Skip NULL scores
                if score_data["score"].total_score is None:
                    continue
                    
                caliber = score_data["score"].caliber
                if caliber not in by_caliber:
                    by_caliber[caliber] = []
                by_caliber[caliber].append(score_data["score"])

        # Calculate 1800 aggregate for each caliber with at least 2 scores
        for caliber, cal_scores in by_caliber.items():
            if len(cal_scores) >= 2:
                # Sort by score (highest first) and take top 2
                cal_scores.sort(key=lambda s: s.total_score, reverse=True)
                top_two = cal_scores[:2]
                total = sum(s.total_score for s in top_two)
                x_count = sum(s.total_x_count for s in top_two)
                aggregates[f"1800_{caliber}"] = {
                    "score": total,
                    "x_count": x_count,
                    "components": [s.match_type_instance for s in top_two],
                }

    # 1800 (3x600) Aggregate
    elif match.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_3X600:
        # Find all 600 match instances and group by caliber
        by_caliber = {}
        for key, score_data in scores.items():
            if any(
                mt.type == BasicMatchType.SIXHUNDRED and mt.instance_name in key
                for mt in match.match_types
            ):
                # Skip NULL scores
                if score_data["score"].total_score is None:
                    continue
                    
                caliber = score_data["score"].caliber
                if caliber not in by_caliber:
                    by_caliber[caliber] = []
                by_caliber[caliber].append(score_data["score"])

        # Calculate 1800 aggregate for each caliber with at least 3 scores
        for caliber, cal_scores in by_caliber.items():
            if len(cal_scores) >= 3:
                # Sort by score (highest first) and take top 3
                cal_scores.sort(key=lambda s: s.total_score, reverse=True)
                top_three = cal_scores[:3]
                total = sum(s.total_score for s in top_three)
                x_count = sum(s.total_x_count for s in top_three)
                aggregates[f"1800_{caliber}"] = {
                    "score": total,
                    "x_count": x_count,
                    "components": [s.match_type_instance for s in top_three],
                }

    # 2700 Aggregate
    elif match.aggregate_type == AggregateType.TWENTY_SEVEN_HUNDRED:
        # Find all 900 match instances and group by caliber
        by_caliber = {}
        for key, score_data in scores.items():
            if any(
                mt.type == BasicMatchType.NINEHUNDRED and mt.instance_name in key
                for mt in match.match_types
            ):
                caliber = score_data["score"].caliber
                if caliber not in by_caliber:
                    by_caliber[caliber] = []
                by_caliber[caliber].append(score_data["score"])

        # Calculate 2700 aggregate for each caliber with at least 3 scores
        for caliber, cal_scores in by_caliber.items():
            if len(cal_scores) >= 3:
                # Sort by score (highest first) and take top 3
                cal_scores.sort(key=lambda s: s.total_score, reverse=True)
                top_three = cal_scores[:3]
                total = sum(s.total_score for s in top_three)
                x_count = sum(s.total_x_count for s in top_three)
                aggregates[f"2700_{caliber}"] = {
                    "score": total,
                    "x_count": x_count,
                    "components": [s.match_type_instance for s in top_three],
                }

    return aggregates


@api_router.get("/shooter-report/{shooter_id}")
async def get_shooter_report(
    shooter_id: str, current_user: User = Depends(get_current_active_user)
):
    shooter = await db.shooters.find_one({"id": shooter_id})
    if not shooter:
        raise HTTPException(status_code=404, detail="Shooter not found")

    shooter_obj = Shooter(**shooter)

    # Get all scores for this shooter
    scores = await db.scores.find({"shooter_id": shooter_id}).to_list(1000)
    score_objs = [Score(**score) for score in scores]

    # Get all matches the shooter participated in
    match_ids = set(score.match_id for score in score_objs)
    matches = {}
    for match_id in match_ids:
        match = await db.matches.find_one({"id": match_id})
        if match:
            matches[match_id] = Match(**match)

    # Build detailed report
    report = {
        "shooter": shooter_obj,
        "matches": {},
        "averages": {"by_match_type": {}, "by_caliber": {}},
    }

    # Group scores by match
    for score in score_objs:
        match_id = score.match_id
        if match_id in matches:
            match = matches[match_id]
            if match_id not in report["matches"]:
                report["matches"][match_id] = {"match": match, "scores": []}

            # Add score details
            report["matches"][match_id]["scores"].append(
                {
                    "score": score,
                    "match_type": next(
                        (
                            mt
                            for mt in match.match_types
                            if mt.instance_name == score.match_type_instance
                        ),
                        None,
                    ),
                }
            )

    # Calculate averages by match type and caliber
    averages_by_type = {}
    averages_by_caliber = {}

    for score in score_objs:
        match_id = score.match_id
        if match_id in matches:
            match = matches[match_id]
            match_type = next(
                (
                    mt.type
                    for mt in match.match_types
                    if mt.instance_name == score.match_type_instance
                ),
                None,
            )

            if match_type:
                # By match type and caliber
                key = f"{match_type}_{score.caliber}"
                if key not in averages_by_type:
                    averages_by_type[key] = {
                        "count": 0,
                        "total_score": 0,
                        "total_x_count": 0,
                        "stages": {},
                    }

                avg_data = averages_by_type[key]
                avg_data["count"] += 1
                avg_data["total_score"] += score.total_score
                avg_data["total_x_count"] += score.total_x_count

                # Track stage scores
                for stage in score.stages:
                    if stage.name not in avg_data["stages"]:
                        avg_data["stages"][stage.name] = {
                            "score_sum": 0,
                            "x_count_sum": 0,
                        }

                    avg_data["stages"][stage.name]["score_sum"] += (stage.score if stage.score is not None else 0)
                    avg_data["stages"][stage.name]["count"] = avg_data["stages"][stage.name].get("count", 0) + (1 if stage.score is not None else 0)
                    avg_data["stages"][stage.name]["x_count_sum"] += (stage.x_count if stage.x_count is not None else 0)

                # By caliber only
                if score.caliber not in averages_by_caliber:
                    averages_by_caliber[score.caliber] = {
                        "count": 0,
                        "total_score_sum": 0,
                        "total_x_count_sum": 0,
                        "match_types": {},
                    }

                cal_data = averages_by_caliber[score.caliber]
                cal_data["count"] += 1
                cal_data["total_score_sum"] += score.total_score
                cal_data["total_x_count_sum"] += score.total_x_count

                # Track match type data
                if match_type not in cal_data["match_types"]:
                    cal_data["match_types"][match_type] = {
                        "count": 0,
                        "score_sum": 0,
                        "x_count_sum": 0,
                    }

                cal_data["match_types"][match_type]["count"] += 1
                cal_data["match_types"][match_type]["score_sum"] += score.total_score
                cal_data["match_types"][match_type][
                    "x_count_sum"
                ] += score.total_x_count

                # Calculate final averages
    for key, data in averages_by_type.items():
        if data["count"] > 0:
            valid_scores_count = sum(1 for stage_name, stage_data in data["stages"].items() if stage_data.get("count", 0) > 0)
            if valid_scores_count > 0:
                data["avg_score"] = round(data["total_score"] / data["count"], 2)
                data["avg_x_count"] = round(data["total_x_count"] / data["count"], 2)

                for stage_name, stage_data in data["stages"].items():
                    stage_count = stage_data.get("count", 0)
                    if stage_count > 0:
                        stage_data["avg_score"] = round(
                            stage_data["score_sum"] / stage_count, 2
                        )
                        stage_data["avg_x_count"] = round(
                            stage_data["x_count_sum"] / stage_count, 2
                        )

    for caliber, data in averages_by_caliber.items():
        if data["count"] > 0:
            data["avg_score"] = round(data["total_score_sum"] / data["count"], 2)
            data["avg_x_count"] = round(data["total_x_count_sum"] / data["count"], 2)

            for match_type, mt_data in data["match_types"].items():
                if mt_data["count"] > 0:
                    mt_data["avg_score"] = round(
                        mt_data["score_sum"] / mt_data["count"], 2
                    )
                    mt_data["avg_x_count"] = round(
                        mt_data["x_count_sum"] / mt_data["count"], 2
                    )

    report["averages"]["by_match_type"] = averages_by_type
    report["averages"]["by_caliber"] = averages_by_caliber

    return report


# Add shooter averages endpoint for ShooterDetail component
@api_router.get("/shooter-averages/{shooter_id}")
async def get_shooter_averages(
    shooter_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get shooter's average performance by caliber"""
    shooter = await db.shooters.find_one({"id": shooter_id})
    if not shooter:
        raise HTTPException(status_code=404, detail="Shooter not found")

    # Get all scores for this shooter
    scores = await db.scores.find({"shooter_id": shooter_id}).to_list(1000)

        # Group scores by caliber
    by_caliber = {}
    for score in scores:
        score_obj = Score(**score)
        caliber = score_obj.caliber
        
        # Skip scores with None (NULL) total_score
        if score_obj.total_score is None:
            continue
            
        if caliber not in by_caliber:
            by_caliber[caliber] = {
                "matches_count": 0,
                "valid_matches_count": 0,
                "sf_score_sum": 0,
                "sf_valid_count": 0,
                "sf_x_count_sum": 0,
                "tf_score_sum": 0,
                "tf_valid_count": 0,
                "tf_x_count_sum": 0,
                "rf_score_sum": 0,
                "rf_valid_count": 0,
                "rf_x_count_sum": 0,
                "nmc_score_sum": 0,
                "nmc_valid_count": 0,
                "nmc_x_count_sum": 0,
                "total_score_sum": 0,
                "total_x_count_sum": 0,
            }

        by_caliber[caliber]["matches_count"] += 1
        by_caliber[caliber]["valid_matches_count"] += 1
        by_caliber[caliber]["total_score_sum"] += score_obj.total_score
        by_caliber[caliber]["total_x_count_sum"] += score_obj.total_x_count

        # Process stages
        for stage in score_obj.stages:
            if stage.score is None:
                continue
                
            if "SF" in stage.name:
                by_caliber[caliber]["sf_score_sum"] += stage.score
                by_caliber[caliber]["sf_valid_count"] += 1
                by_caliber[caliber]["sf_x_count_sum"] += stage.x_count
            elif "TF" in stage.name:
                by_caliber[caliber]["tf_score_sum"] += stage.score
                by_caliber[caliber]["tf_valid_count"] += 1
                by_caliber[caliber]["tf_x_count_sum"] += stage.x_count
            elif "RF" in stage.name:
                by_caliber[caliber]["rf_score_sum"] += stage.score
                by_caliber[caliber]["rf_valid_count"] += 1
                by_caliber[caliber]["rf_x_count_sum"] += stage.x_count

        # Calculate NMC scores (typically SF + TF + RF for a single match)
        if "NMC" in score_obj.match_type_instance and score_obj.total_score is not None:
            by_caliber[caliber]["nmc_score_sum"] += score_obj.total_score
            by_caliber[caliber]["nmc_valid_count"] += 1
            by_caliber[caliber]["nmc_x_count_sum"] += score_obj.total_x_count

    # Calculate averages
    averages = {}
    for caliber, data in by_caliber.items():
        valid_matches_count = data["valid_matches_count"]
        
        if valid_matches_count > 0:
            averages[caliber] = {
                "matches_count": data["matches_count"],
                "valid_matches_count": valid_matches_count,
                "sf_score_avg": round(data["sf_score_sum"] / max(data["sf_valid_count"], 1), 2) if data["sf_valid_count"] > 0 else None,
                "sf_x_count_avg": round(data["sf_x_count_sum"] / max(data["sf_valid_count"], 1), 2) if data["sf_valid_count"] > 0 else None,
                "tf_score_avg": round(data["tf_score_sum"] / max(data["tf_valid_count"], 1), 2) if data["tf_valid_count"] > 0 else None,
                "tf_x_count_avg": round(data["tf_x_count_sum"] / max(data["tf_valid_count"], 1), 2) if data["tf_valid_count"] > 0 else None,
                "rf_score_avg": round(data["rf_score_sum"] / max(data["rf_valid_count"], 1), 2) if data["rf_valid_count"] > 0 else None,
                "rf_x_count_avg": round(data["rf_x_count_sum"] / max(data["rf_valid_count"], 1), 2) if data["rf_valid_count"] > 0 else None,
                "nmc_score_avg": round(data["nmc_score_sum"] / max(data["nmc_valid_count"], 1), 2) if data["nmc_valid_count"] > 0 else None,
                "nmc_x_count_avg": round(data["nmc_x_count_sum"] / max(data["nmc_valid_count"], 1), 2) if data["nmc_valid_count"] > 0 else None,
                "total_score_avg": round(data["total_score_sum"] / valid_matches_count, 2),
                "total_x_count_avg": round(data["total_x_count_sum"] / valid_matches_count, 2),
            }

    return {"caliber_averages": averages}


# Root API endpoint
@api_router.get("/")
async def root():
    return {"message": "Enhanced Shooting Match Score Management API"}


# Include the routers in the main app
app.include_router(api_router)
app.include_router(auth_router)

# Get allowed origins from environment variable or use defaults
origins_env = os.environ.get("ORIGINS", "")
default_origins = [
    "http://localhost:8080",  # Docker compose frontend
    "http://localhost:3000",  # Development frontend
    "https://localhost:8080",
    "https://localhost:3000",
    "http://192.168.50.167:8080",  # User's local environment
    "https://b78bc624-fd3d-457d-a921-b3684a7c6c0b.preview.emergentagent.com",  # Emergent preview URL
    "*",  # Allow all origins as fallback - consider removing in production
]

# Parse origins from environment variable if present
allowed_origins = default_origins
if origins_env:
    custom_origins = [origin.strip() for origin in origins_env.split(",")]
    allowed_origins.extend(custom_origins)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Create a first admin user if no users exist
@app.on_event("startup")
async def create_first_admin():
    try:
        # Check if users collection is empty
        users_count = await db.users.count_documents({})

        if users_count == 0:
            # Create default admin user
            default_email = "admin@example.com"
            default_password = "admin123"  # Change this in production!
            hashed_password = get_password_hash(default_password)

            user = UserInDB(
                id=str(uuid.uuid4()),  # Explicitly set ID
                email=default_email,
                username="admin",
                role=UserRole.ADMIN,
                hashed_password=hashed_password,
                created_at=datetime.utcnow(),
                is_active=True,
            )

            user_dict = user.dict()
            await db.users.insert_one(user_dict)
            logger.info(f"Created default admin user: {default_email}")
            logger.info(f"Admin user ID: {user_dict['id']}")
        else:
            logger.info(
                f"Database already has {users_count} users, skipping default admin creation"
            )
    except Exception as e:
        logger.error(f"Error creating default admin user: {str(e)}")
        # Don't fail startup, log the error and continue


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
