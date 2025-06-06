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

# --- Pydantic Models needed by helper functions (Moved Up) ---
class ShooterBase(BaseModel):
    name: str
    nra_number: Optional[str] = None
    cmp_number: Optional[str] = None

class Shooter(ShooterBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MatchTypeInstance(BaseModel):
    type: BasicMatchType
    instance_name: str  # e.g., "NMC1", "600_1"
    calibers: List[CaliberType]

class MatchBase(BaseModel):
    name: str
    date: datetime
    location: str
    match_types: List[MatchTypeInstance]
    aggregate_type: AggregateType = AggregateType.NONE

class Match(MatchBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- Helper for standard caliber ordering ---
STANDARD_CALIBER_ORDER_MAP = {
    CaliberType.TWENTYTWO: 1,
    CaliberType.CENTERFIRE: 2,
    CaliberType.FORTYFIVE: 3,
    CaliberType.SERVICEPISTOL: 4,
    CaliberType.SERVICEREVOLVER: 5,
    CaliberType.DR: 6,
}

# --- Helper function to get base match type and fields for aggregate ---
def _get_aggregate_components(aggregate_type: AggregateType):
    if aggregate_type == AggregateType.TWENTY_SEVEN_HUNDRED:
        return BasicMatchType.NINEHUNDRED, ["SF", "NMC", "TF", "RF", "900"]
    elif aggregate_type == AggregateType.EIGHTEEN_HUNDRED_2X900:
        return BasicMatchType.NINEHUNDRED, ["SF", "NMC", "TF", "RF", "900"]
    elif aggregate_type == AggregateType.EIGHTEEN_HUNDRED_3X600:
        return BasicMatchType.SIXHUNDRED, ["SF", "TF", "RF", "600"] # No NMC for 600
    return None, []

# --- Helper function to get ordered calibers for an aggregate match type ---
def _get_ordered_calibers_for_aggregate(match_obj: Match, base_match_type_for_agg: BasicMatchType) -> List[CaliberType]:
    present_calibers = set()
    if not base_match_type_for_agg: # Should not happen if called correctly
        return []
        
    for mt_instance in match_obj.match_types:
        if mt_instance.type == base_match_type_for_agg:
            for cal in mt_instance.calibers: # A MatchTypeInstance can have multiple calibers
                present_calibers.add(cal)
    
    sorted_calibers = sorted(list(present_calibers), key=lambda c: STANDARD_CALIBER_ORDER_MAP.get(c, 99))
    return sorted_calibers

# --- New dynamic header builder for aggregate matches ---
def _build_dynamic_aggregate_header_and_calibers(match_obj: Match):
    header_row1 = ["", ""]  # For Shooter, Aggregate Total
    header_row2 = ["Shooter", "Aggregate Total"]
    
    base_match_type_for_agg, agg_sub_fields = _get_aggregate_components(match_obj.aggregate_type)
    
    if not base_match_type_for_agg or not agg_sub_fields:
        # Fallback for unknown aggregate type or if no components defined
        return header_row1, header_row2, [], [], None 

    ordered_calibers_list = _get_ordered_calibers_for_aggregate(match_obj, base_match_type_for_agg)

    for caliber_enum in ordered_calibers_list:
        caliber_str = caliber_enum.value
        header_row1 += [caliber_str] + [""] * (len(agg_sub_fields) - 1)
        header_row2 += agg_sub_fields
        
    return header_row1, header_row2, ordered_calibers_list, agg_sub_fields, base_match_type_for_agg

# --- New dynamic header builder for non-aggregate matches ---
def _build_dynamic_non_aggregate_header(match_obj: Match) -> List[str]:
    header = ["Shooter", "Average"]
    # Sort match types by instance name for consistent column order
    sorted_match_types = sorted(match_obj.match_types, key=lambda mt: mt.instance_name)
    for mt in sorted_match_types:
        # Sort calibers within a match_type_instance for consistency
        sorted_calibers_for_mt = sorted(list(set(mt.calibers)), key=lambda c: STANDARD_CALIBER_ORDER_MAP.get(c, 99))
        for caliber_enum in sorted_calibers_for_mt:
            header.append(f"{mt.instance_name} ({caliber_enum.value})")
    return header

# --- Modified build_aggregate_row_grouped function ---
def build_aggregate_row_grouped(
    shooter: Shooter, 
    shooter_data: Dict[str, Any], 
    report_data: Dict[str, Any], 
    ordered_calibers: List[CaliberType], 
    agg_sub_fields: List[str],
    base_match_type_for_agg: BasicMatchType
):
    row = [shooter.name]
    
    overall_agg_total_score = 0
    overall_agg_total_x = 0
    
    match_config = report_data.get("match_config", {})
    match_types_configs_dict = {mtc["instance_name"]: mtc for mtc in match_config.get("match_types", [])}

    for score_key, score_item in shooter_data["scores"].items():
        score_details = score_item["score"]
        if score_details.get("not_shot", False) or score_details["total_score"] is None:
            continue

        instance_name = score_details["match_type_instance"]
        mt_config_for_score = match_types_configs_dict.get(instance_name)
        
        if mt_config_for_score and mt_config_for_score["type"] == base_match_type_for_agg:
            overall_agg_total_score += score_details["total_score"]
            overall_agg_total_x += (score_details["total_x_count"] or 0)
            
    row.append(f"{overall_agg_total_score} ({overall_agg_total_x}X)" if overall_agg_total_score > 0 or overall_agg_total_x > 0 else "-")

    for target_caliber_enum in ordered_calibers:
        target_caliber_str = target_caliber_enum.value
        
        col_data = {field: {"score": 0, "x": 0} for field in agg_sub_fields}
        col_total_score_direct_sum = 0 # Sum of total_score from individual matches for this caliber
        col_total_x_direct_sum = 0     # Sum of total_x_count from individual matches for this caliber
        has_data_for_caliber_column = False

        for score_key, score_item in shooter_data["scores"].items():
            score_details = score_item["score"]
            if score_details.get("not_shot", False) or score_details["caliber"] != target_caliber_str:
                continue

            instance_name = score_details["match_type_instance"]
            mt_config_for_score = match_types_configs_dict.get(instance_name)

            if mt_config_for_score and mt_config_for_score["type"] == base_match_type_for_agg:
                has_data_for_caliber_column = True
                
                if score_details["total_score"] is not None:
                    col_total_score_direct_sum += score_details["total_score"]
                if score_details["total_x_count"] is not None:
                    col_total_x_direct_sum += score_details["total_x_count"]

                for stage in score_details["stages"]:
                    val = stage["score"] if stage["score"] is not None else 0
                    xval = stage["x_count"] if stage["x_count"] is not None else 0
                    
                    stage_name_upper = stage["name"].upper() # Normalize stage name for matching

                    if stage_name_upper.startswith("SF") and "NMC" not in stage_name_upper:
                        col_data["SF"]["score"] += val
                        col_data["SF"]["x"] += xval
                    elif "NMC" in stage_name_upper and "NMC" in agg_sub_fields:
                         col_data["NMC"]["score"] += val
                         col_data["NMC"]["x"] += xval
                    elif stage_name_upper.startswith("TF") and "NMC" not in stage_name_upper:
                        col_data["TF"]["score"] += val
                        col_data["TF"]["x"] += xval
                    elif stage_name_upper.startswith("RF") and "NMC" not in stage_name_upper:
                        col_data["RF"]["score"] += val
                        col_data["RF"]["x"] += xval
        
        def fmt_cell(score_val, x_val):
            if not has_data_for_caliber_column: return "-"
            return f"{score_val} ({x_val}X)" if score_val > 0 or x_val > 0 else "0 (0X)"

        for field_name in agg_sub_fields:
            if field_name in ["SF", "TF", "RF"] or (field_name == "NMC" and "NMC" in col_data):
                row.append(fmt_cell(col_data[field_name]["score"], col_data[field_name]["x"]))
            elif field_name == "900" or field_name == "600": # This is the total for the caliber column
                row.append(fmt_cell(col_total_score_direct_sum, col_total_x_direct_sum))
            # else: # Should not happen with defined agg_sub_fields
            #     row.append("-") # Fallback for unexpected field
                
    return row

# --- New function to build a row for non-aggregate matches ---
def build_non_aggregate_row(
    shooter: Shooter, 
    shooter_data: Dict[str, Any], 
    match_obj: Match # Pass the full match_obj to access its structure
) -> List[Any]:
    row = [shooter.name]
    
    total_score_sum = 0
    num_scored_entries = 0
    
    # Pre-calculate overall average for this shooter in this non-aggregate match
    for score_key, score_item in shooter_data["scores"].items():
        score_details = score_item["score"]
        if not score_details.get("not_shot", False) and score_details["total_score"] is not None:
            total_score_sum += score_details["total_score"]
            num_scored_entries += 1
            
    if num_scored_entries > 0:
        average_score = round(total_score_sum / num_scored_entries, 2)
        row.append(average_score)
    else:
        row.append("-") # No scores to average

    # Sort match types by instance name for consistent column order, same as in header builder
    sorted_match_types = sorted(match_obj.match_types, key=lambda mt: mt.instance_name)
    
    for mt_instance in sorted_match_types:
        # Sort calibers within a match_type_instance for consistency, same as in header builder
        sorted_calibers_for_mt = sorted(list(set(mt_instance.calibers)), key=lambda c: STANDARD_CALIBER_ORDER_MAP.get(c, 99))
        for target_caliber_enum in sorted_calibers_for_mt:
            target_caliber_str = target_caliber_enum.value
            
            score_found = False
            # Iterate through the shooter's scores to find the matching entry
            for score_key, score_item in shooter_data["scores"].items():
                score_details = score_item["score"]
                # The key in shooter_data["scores"] is typically f"{match_type_instance}_{caliber}"
                # We need to match instance_name and caliber
                if score_details["match_type_instance"] == mt_instance.instance_name and \
                   score_details["caliber"] == target_caliber_str:
                    if not score_details.get("not_shot", False) and score_details["total_score"] is not None:
                        row.append(f"{score_details['total_score']} ({score_details.get('total_x_count', 0)}X)")
                    else:
                        row.append("-") # Not shot or no score
                    score_found = True
                    break
            
            if not score_found:
                row.append("-") # No score entry found for this specific match_type_instance and caliber
                
    return row

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


class ShooterCreate(ShooterBase):
    pass


# Match Type Configuration


# Match Definition


class MatchCreate(MatchBase):
    pass


# Score Stage (individual component scores)
class ScoreStage(BaseModel):
    name: str  # e.g., "SF", "TF1", "RF2"
    score: Optional[int] = None
    x_count: Optional[int] = None


# Score Entry
class ScoreBase(BaseModel):
    shooter_id: str
    match_id: str
    caliber: CaliberType
    match_type_instance: str  # e.g., "NMC1", "600_1"
    stages: List[ScoreStage]
    total_score: Optional[int] = None
    total_x_count: Optional[int] = None
    not_shot: bool = False  # New field to indicate if the match was not shot


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
    
    existing_match_obj = Match(**existing_match)
    
    # Find match types that have been removed or modified
    existing_match_types = {mt.instance_name: mt for mt in existing_match_obj.match_types}
    new_match_types = {mt.instance_name: mt for mt in match_update.match_types}
    
    # Delete scores for entirely removed match types
    removed_match_types = set(existing_match_types.keys()) - set(new_match_types.keys())
    if removed_match_types:
        for match_type in removed_match_types:
            await db.scores.delete_many({
                "match_id": match_id,
                "match_type_instance": match_type
            })
    
    # For match types that still exist, check for removed calibers
    for match_type_name in set(existing_match_types.keys()) & set(new_match_types.keys()):
        existing_calibers = set(existing_match_types[match_type_name].calibers)
        new_calibers = set(new_match_types[match_type_name].calibers)
        
        # Find calibers that have been removed
        removed_calibers = existing_calibers - new_calibers
        
        # Delete scores for removed calibers
        if removed_calibers:
            for caliber in removed_calibers:
                await db.scores.delete_many({
                    "match_id": match_id,
                    "match_type_instance": match_type_name,
                    "caliber": caliber
                })
    
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
    has_valid_score = any(stage.score is not None for stage in score.stages)
    has_valid_x = any(stage.x_count is not None for stage in score.stages)
    
    # If all stages are NULL, mark as not shot and set totals to NULL
    not_shot = not has_valid_score
    total_score = sum(stage.score for stage in score.stages if stage.score is not None) if has_valid_score else None
    total_x_count = sum(stage.x_count for stage in score.stages if stage.x_count is not None) if has_valid_x else None
    
    # Create the score object with calculated totals and not_shot flag
    score_dict = score.dict()
    score_dict.update({
        "total_score": total_score, 
        "total_x_count": total_x_count,
        "not_shot": not_shot
    })

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
    has_valid_score = any(stage.score is not None for stage in score_update.stages)
    has_valid_x = any(stage.x_count is not None for stage in score_update.stages)
    
    # If all stages are NULL, mark as not shot and set totals to NULL
    not_shot = not has_valid_score
    total_score = sum(stage.score for stage in score_update.stages if stage.score is not None) if has_valid_score else None
    total_x_count = sum(stage.x_count for stage in score_update.stages if stage.x_count is not None) if has_valid_x else None
    
    # Update the score object with calculated totals and not_shot flag
    score_dict = score_update.dict()
    score_dict.update({
        "total_score": total_score, 
        "total_x_count": total_x_count,
        "not_shot": not_shot
    })

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
                                # Handle NULL values in subtotal calculation
                                if stage.score is not None:
                                    subtotal_score += stage.score
                                if stage.x_count is not None:
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
            shooter_scores = shooter_data["scores"]
            shooter_data["aggregates"] = calculate_aggregates(shooter_scores, match_obj)

            # --- Add fallback aggregate total if not present ---
            agg_label = None
            agg_count = 0
            if match_obj.aggregate_type == AggregateType.TWENTY_SEVEN_HUNDRED:
                agg_label = "2700"
                agg_count = 3
            elif match_obj.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_2X900:
                agg_label = "1800"
                agg_count = 2
            elif match_obj.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_3X600:
                agg_label = "1800"
                agg_count = 3

            if agg_label:
                # Find all 900 or 600 scores for this shooter
                scores_list = []
                x_counts = []
                for key, score_data in shooter_scores.items():
                    score = score_data["score"]
                    if score["total_score"] is not None:
                        scores_list.append(score["total_score"])
                        x_counts.append(score["total_x_count"] or 0)
                if len(scores_list) >= agg_count:
                    total = sum(sorted(scores_list, reverse=True)[:agg_count])
                    x_total = sum(sorted(x_counts, reverse=True)[:agg_count])
                    shooter_data["aggregates"][agg_label] = {
                        "score": total,
                        "x_count": x_total,
                    }

    # Include match configuration in the result
    result["match_config"] = match_config
    
    return result

@api_router.get("/match-report/{match_id}/excel")
async def get_match_report_excel(
    match_id: str, current_user: User = Depends(get_current_active_user)
):
    # Get the match report data first (reuse existing function)
    report_data = await get_match_report(match_id, current_user)
    match_obj: Match = report_data["match"] # Added type hint
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
    ws.merge_cells(f"A1:G1") # Adjust merge range if needed, G1 seems fine for now
    cell = ws.cell(row=1, column=1)
    cell.font = Font(bold=True, size=16)
    cell.alignment = Alignment(horizontal="center")
    
    ws.append([])
    ws.append(["Match Name:", match_obj.name])
    ws.append(["Date:", match_obj.date.strftime("%Y-%m-%d")])
    ws.append(["Location:", match_obj.location])
    
    agg_type_map = {
        AggregateType.TWENTY_SEVEN_HUNDRED: "2700 (3x900)", # Clarified display
        AggregateType.EIGHTEEN_HUNDRED_2X900: "1800 (2x900)",
        AggregateType.EIGHTEEN_HUNDRED_3X600: "1800 (3x600)",
        AggregateType.NONE: "None"
    }
    agg_type_display = agg_type_map.get(match_obj.aggregate_type, str(match_obj.aggregate_type.value if isinstance(match_obj.aggregate_type, Enum) else match_obj.aggregate_type))
    
    ws.append(["Aggregate Type:", agg_type_display])
    ws.append([]) # Blank row
    
    is_aggregate = match_obj.aggregate_type != AggregateType.NONE
    
    # Variables for dynamic header content
    header_row1_content = []
    header_row2_content = []
    ordered_calibers_for_agg = []
    agg_sub_fields_for_agg = []
    base_match_type_for_agg_val = None # Store the BasicMatchType enum value

    # --- Build summary header ---
    if is_aggregate:
        header_row1_content, header_row2_content, ordered_calibers_for_agg, agg_sub_fields_for_agg, base_match_type_for_agg_val = \
            _build_dynamic_aggregate_header_and_calibers(match_obj)
        
        # Only append if headers are generated (i.e., valid aggregate type)
        if header_row1_content and header_row2_content:
            ws.append(header_row1_content)
            ws.append(header_row2_content)
        header_row_for_styling_and_cols = header_row2_content # Used for column counts and styling main header
        header_offset = 2 if header_row1_content and header_row2_content else 0
    else:
        header_row_for_styling_and_cols = _build_dynamic_non_aggregate_header(match_obj)
        ws.append(header_row_for_styling_and_cols)
        header_offset = 1

    current_header_start_row = 8 # Assuming match details take up to row 7

    # Add shooter rows
    for idx, (shooter_id, s_data) in enumerate(shooters_data.items()): # s_data to avoid conflict
        shooter_obj = s_data["shooter"]
        row_content_list: List[Any] # Type hint for clarity
        if is_aggregate:
            if base_match_type_for_agg_val and ordered_calibers_for_agg and agg_sub_fields_for_agg: # Ensure all parts are valid
                row_content_list = build_aggregate_row_grouped(
                    shooter_obj, s_data, report_data, 
                    ordered_calibers_for_agg, agg_sub_fields_for_agg, base_match_type_for_agg_val
                )
            else: # Should not happen if headers were generated
                row_content_list = [shooter_obj.name, "-"] 
        else:
            row_content_list = build_non_aggregate_row(shooter_obj, s_data, match_obj) # Pass match_obj
        
        for col_idx_excel, value in enumerate(row_content_list, 1):
            ws.cell(row=current_header_start_row + header_offset + idx, column=col_idx_excel, value=value)

    # Apply header styles (for both header rows if aggregate)
    if header_offset > 0: # Check if any header was actually added
        if is_aggregate and header_offset == 2:
            # Determine start columns for caliber names dynamically
            caliber_start_cols_excel = [3] # First caliber starts at column C (3)
            if ordered_calibers_for_agg and agg_sub_fields_for_agg:
                current_col_for_calc = 3 + len(agg_sub_fields_for_agg)
                for _ in range(1, len(ordered_calibers_for_agg)):
                    caliber_start_cols_excel.append(current_col_for_calc)
                    current_col_for_calc += len(agg_sub_fields_for_agg)

            for r_idx_offset in range(header_offset):
                actual_row_idx = current_header_start_row + r_idx_offset
                # Use length of header_row1_content for first header row, header_row2_content for second
                current_row_content = header_row1_content if r_idx_offset == 0 else header_row2_content
                for col_idx_excel in range(1, len(current_row_content) + 1):
                    cell = ws.cell(row=actual_row_idx, column=col_idx_excel)
                    if r_idx_offset == 0: # Caliber row (first header row)
                        if col_idx_excel in caliber_start_cols_excel:
                            cell.font = Font(bold=True)
                            cell.alignment = Alignment(horizontal="left") # Caliber names left-aligned
                            cell.border = thin_border
                        elif col_idx_excel <= 2 : # Shooter, Agg Total in first header row - no special style
                            cell.border = Border() # No border for these in the caliber row
                        else: # Blank cells under merged caliber name
                            cell.border = thin_border # Keep border for structure
                    else: # Fields row (second header row or the only header row for non-agg)
                        cell.font = header_font
                        cell.fill = header_fill
                        cell.alignment = header_alignment
                        cell.border = thin_border
        elif not is_aggregate and header_offset == 1: # Non-aggregate single header row
             for col_idx_excel in range(1, len(header_row_for_styling_and_cols) + 1):
                cell = ws.cell(row=current_header_start_row, column=col_idx_excel)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border

    # Merge cells for caliber groupings in the first header row (aggregate only)
    if is_aggregate and header_offset == 2 and ordered_calibers_for_agg and agg_sub_fields_for_agg:
        start_col_merge = 3 # Column C
        for i in range(len(ordered_calibers_for_agg)):
            if len(agg_sub_fields_for_agg) > 1: # Only merge if there's more than one sub-field
                ws.merge_cells(
                    start_row=current_header_start_row, start_column=start_col_merge,
                    end_row=current_header_start_row, end_column=start_col_merge + len(agg_sub_fields_for_agg) - 1
                )
            start_col_merge += len(agg_sub_fields_for_agg)

    # Auto-adjust column widths for headers (use the longest header row for column count)
    # This needs to be based on the actual content of header_row_for_styling_and_cols
    if header_row_for_styling_and_cols:
        ws.column_dimensions[get_column_letter(1)].width = 25 # Shooter name
        ws.column_dimensions[get_column_letter(2)].width = 18 # Aggregate Total / Average
        for i in range(3, len(header_row_for_styling_and_cols) + 1):
             ws.column_dimensions[get_column_letter(i)].width = 12 # Default for score columns

    # Determine columns to bold (e.g., "900" or "600" total columns for aggregates)
    total_col_indices_to_bold = []
    if is_aggregate and agg_sub_fields_for_agg:
        total_field_name = agg_sub_fields_for_agg[-1] # e.g., "900" or "600"
        # header_row_for_styling_and_cols is header_row2_content here
        for i, h_val in enumerate(header_row_for_styling_and_cols):
            if h_val == total_field_name:
                total_col_indices_to_bold.append(i + 1) # 1-indexed

    data_start_excel_row = current_header_start_row + header_offset
    for idx, (shooter_id, s_data) in enumerate(shooters_data.items()): # s_data to avoid conflict
        shooter_obj = s_data["shooter"]
        row_content_list: List[Any] # Type hint for clarity
        if is_aggregate:
            if base_match_type_for_agg_val and ordered_calibers_for_agg and agg_sub_fields_for_agg: # Ensure all parts are valid
                row_content_list = build_aggregate_row_grouped(
                    shooter_obj, s_data, report_data, 
                    ordered_calibers_for_agg, agg_sub_fields_for_agg, base_match_type_for_agg_val
                )
            else: # Should not happen if headers were generated
                row_content_list = [shooter_obj.name, "-"] 
        else:
            row_content_list = build_non_aggregate_row(shooter_obj, s_data, match_obj) # Pass match_obj
        
        for col_idx_excel, value in enumerate(row_content_list, 1):
            ws.cell(row=data_start_excel_row + idx, column=col_idx_excel, value=value)

    # Apply borders and alignment to all data cells
    for row in ws.iter_rows(min_row=data_start_excel_row, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            cell.border = thin_border
            if cell.col_idx > 1:  # Center-align score columns
                cell.alignment = Alignment(horizontal="center")

    # Apply bold font to total columns (e.g., "900" or "600" total columns for aggregates)
    for row in ws.iter_rows(min_row=data_start_excel_row, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
        for cell in row:
            if cell.col_idx in total_col_indices_to_bold:
                cell.font = Font(bold=True)

    # Freeze panes for both aggregate and non-aggregate matches
    if is_aggregate:
        # For aggregate matches, freeze after "Aggregate Total" column (column B)
        ws.freeze_panes = f"C{data_start_excel_row}"
    else:
        # For non-aggregate matches, freeze after "Average" column (column B)
        ws.freeze_panes = f"C{data_start_excel_row}"

    # Create detailed sheets for each shooter
    for shooter_id, shooter_data in shooters_data.items():
        shooter = shooter_data["shooter"]
        ws_detail = wb.create_sheet(title=f"{shooter.name[:28]}")  # Limit sheet name length
        
        # Add shooter details
        ws_detail.append(["Shooter Report"])
        ws_detail.merge_cells(f"A1:C1")
        cell = ws_detail.cell(row=1, column=1)
        cell.font = Font(bold=True, size=16)
        cell.alignment = Alignment(horizontal="center")
        
        ws_detail.append([])
        ws_detail.append(["Shooter Name:", shooter.name])
        ws_detail.append(["Match Name:", match_obj.name])
        ws_detail.append(["Date:", match_obj.date.strftime("%Y-%m-%d")])
        ws_detail.append(["Location:", match_obj.location])
        ws_detail.append(["NRA Number:", shooter.nra_number or "-"])
        ws_detail.append(["CMP Number:", shooter.cmp_number or "-"])
        ws_detail.append([])
        
        if is_aggregate:
            total_possible_display_value = ""
            agg_main_label_for_lookup = ""
            
            if match_obj.aggregate_type == AggregateType.TWENTY_SEVEN_HUNDRED:
                total_possible_display_value = "2700"
                agg_main_label_for_lookup = "2700"
            elif match_obj.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_2X900:
                total_possible_display_value = "1800"
                agg_main_label_for_lookup = "1800"
            elif match_obj.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_3X600:
                total_possible_display_value = "1800"
                agg_main_label_for_lookup = "1800"

            # Display the main aggregate total for the shooter
            # Try to get this from the pre-calculated aggregates in shooter_data
            main_agg_score_display = "-"
            if agg_main_label_for_lookup and \
               shooter_data.get("aggregates") and \
               shooter_data["aggregates"].get(agg_main_label_for_lookup):
                agg_info = shooter_data["aggregates"][agg_main_label_for_lookup]
                main_agg_score_val = agg_info.get("score", 0)
                main_agg_x_val = agg_info.get("x_count", 0)
                if main_agg_score_val > 0 or main_agg_x_val > 0:
                    main_agg_score_display = f"{main_agg_score_val} ({main_agg_x_val}X)"
            
            ws_detail.append([f"Aggregate Total ({total_possible_display_value}):", main_agg_score_display])

            # Per-caliber breakdown for the aggregate's components
            base_match_type_for_agg_detail, agg_sub_fields_detail = _get_aggregate_components(match_obj.aggregate_type)
            ordered_calibers_for_agg_detail = []
            if base_match_type_for_agg_detail:
                 ordered_calibers_for_agg_detail = _get_ordered_calibers_for_aggregate(match_obj, base_match_type_for_agg_detail)

            if ordered_calibers_for_agg_detail and base_match_type_for_agg_detail:
                # Determine if the sub-total is per 900 or 600 points
                sub_total_points_label = ""
                if base_match_type_for_agg_detail == BasicMatchType.NINEHUNDRED:
                    sub_total_points_label = "900"
                elif base_match_type_for_agg_detail == BasicMatchType.SIXHUNDRED:
                    sub_total_points_label = "600"
                
                if sub_total_points_label: # Only proceed if we have a valid label (900 or 600)
                    for caliber_enum_detail in ordered_calibers_for_agg_detail:
                        caliber_str_detail = caliber_enum_detail.value
                        caliber_component_total_score = 0
                        caliber_component_total_x = 0
                        has_data_for_caliber_component = False

                        # Sum scores for this caliber that are of the aggregate's base match type
                        for score_key, score_item_detail in shooter_data["scores"].items():
                            score_details_item = score_item_detail["score"]
                            if score_details_item["caliber"] == caliber_str_detail:
                                # Check if this score's match_type_instance is of the base_match_type_for_agg_detail
                                is_part_of_aggregate_base_type = False
                                for mt_cfg in match_obj.match_types:
                                    if mt_cfg.instance_name == score_details_item["match_type_instance"] and \
                                       mt_cfg.type == base_match_type_for_agg_detail:
                                        is_part_of_aggregate_base_type = True
                                        break
                                
                                if is_part_of_aggregate_base_type:
                                    if not score_details_item.get("not_shot", False):
                                        if score_details_item["total_score"] is not None:
                                            caliber_component_total_score += score_details_item["total_score"]
                                            has_data_for_caliber_component = True
                                        if score_details_item["total_x_count"] is not None:
                                            caliber_component_total_x += score_details_item["total_x_count"]
                        
                        display_val = f"{caliber_component_total_score} ({caliber_component_total_x}X)" if has_data_for_caliber_component else "-"
                        ws_detail.append([f"{caliber_str_detail} {sub_total_points_label}", display_val])
            
            ws_detail.append([])  # Blank row before detailed stage breakdown
        
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
                current_row = ws_detail.max_row  # Get the actual row that was just appended
                ws_detail.merge_cells(f"A{current_row}:C{current_row}")
                
                # Apply filled background to header row
                for col in range(1, 4):
                    cell = ws_detail.cell(row=current_row, column=col)
                    cell.fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
                
                # Apply bold font to the first cell which has the header text
                cell = ws_detail.cell(row=current_row, column=1)
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal="center")
                
                row_index += 1
                
                # Add stage headers
                header_row = ["Stage", "Score", "X Count"]
                ws_detail.append(header_row)
                current_row = ws_detail.max_row  # Get the actual row for the header
                
                # Apply header styles
                for col in range(1, len(header_row) + 1):
                    cell = ws_detail.cell(row=current_row, column=col)
                    cell.font = header_font
                    cell.fill = header_fill
                    cell.alignment = header_alignment
                    cell.border = thin_border
                
                row_index += 1
                
                # Check if this is a not_shot match
                not_shot = score_data["score"].get("not_shot", False)
                if not_shot:
                    # Add "Not Shot" indicator with special formatting
                    ws_detail.append(["Not Shot"])
                    current_row = ws_detail.max_row
                    not_shot_cell = ws_detail.cell(row=current_row, column=1)
                    not_shot_cell.font = Font(bold=True, color="FF0000")  # Red text
                    ws_detail.merge_cells(f"A{current_row}:C{current_row}")
                    row_index += 1
                    
                    # Add total row with dashes
                    ws_detail.append([
                        "Total",
                        "-",
                        "-"
                    ])
                    current_row = ws_detail.max_row
                    
                    # Apply total row formatting
                    for col in range(1, 4):
                        cell = ws_detail.cell(row=current_row, column=col)
                        cell.font = Font(bold=True)
                        cell.border = thin_border
                        if col > 1:  # Center-align score columns
                            cell.alignment = Alignment(horizontal="center")
                            
                    row_index += 1
                    
                else:
                    # Add stage scores
                    stages = score_data["score"]["stages"]
                    for stage in stages:
                        stage_name = stage["name"]
                        score_value = stage["score"]
                        x_count = stage["x_count"]
                        
                        # Format the score and x_count correctly for display
                        score_display = "-" if score_value is None else score_value
                        x_count_display = "-" if x_count is None else x_count
                        
                        ws_detail.append([
                            stage_name,
                            score_display,
                            x_count_display
                        ])
                        current_row = ws_detail.max_row
                        
                        # Apply borders to data cells
                        for col in range(1, len(header_row) + 1):
                            cell = ws_detail.cell(row=current_row, column=col)
                            cell.border = thin_border
                            if col > 1:  # Align score columns to center
                                cell.alignment = Alignment(horizontal="center")
                        
                        row_index += 1
                    
                    # Add total row
                    total_score = score_data["score"]["total_score"]
                    total_x_count = score_data["score"]["total_x_count"]
                    
                    # Format the total score and x_count correctly for display
                    total_score_display = "-" if total_score is None else total_score
                    total_x_count_display = "-" if total_x_count is None else total_x_count
                    
                    ws_detail.append([
                        "Total",
                        total_score_display,
                        total_x_count_display
                    ])
                    current_row = ws_detail.max_row
                
                    # Apply total row styling
                    for col in range(1, len(header_row) + 1):
                        cell = ws_detail.cell(row=current_row, column=col)
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
        by_caliber = {}
        for key, score_data in scores.items():
            if any(
                mt.type == BasicMatchType.NINEHUNDRED and mt.instance_name in key
                for mt in match.match_types
            ):
                if score_data["score"]["total_score"] is None:
                    continue
                caliber = score_data["score"]["caliber"]
                if caliber not in by_caliber:
                    by_caliber[caliber] = []
                by_caliber[caliber].append(score_data["score"])

        for caliber, cal_scores in by_caliber.items():
            if len(cal_scores) >= 2:
                cal_scores.sort(key=lambda s: s["total_score"], reverse=True)
                top_two = cal_scores[:2]
                total = sum(s["total_score"] for s in top_two)
                x_count = sum(s["total_x_count"] for s in top_two)
                aggregates[f"1800_{caliber}"] = {
                    "score": total,
                    "x_count": x_count,
                    "components": [s["match_type_instance"] for s in top_two],
                }

    # 1800 (3x600) Aggregate
    elif match.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_3X600:
        by_caliber = {}
        for key, score_data in scores.items():
            if any(
                mt.type == BasicMatchType.SIXHUNDRED and mt.instance_name in key
                for mt in match.match_types
            ):
                if score_data["score"]["total_score"] is None:
                    continue
                caliber = score_data["score"]["caliber"]
                if caliber not in by_caliber:
                    by_caliber[caliber] = []
                by_caliber[caliber].append(score_data["score"])

        for caliber, cal_scores in by_caliber.items():
            if len(cal_scores) >= 3:
                cal_scores.sort(key=lambda s: s["total_score"], reverse=True)
                top_three = cal_scores[:3]
                total = sum(s["total_score"] for s in top_three)
                x_count = sum(s["total_x_count"] for s in top_three)
                aggregates[f"1800_{caliber}"] = {
                    "score": total,
                    "x_count": x_count,
                    "components": [s["match_type_instance"] for s in top_three],
                }

    # 2700 Aggregate
    elif match.aggregate_type == AggregateType.TWENTY_SEVEN_HUNDRED:
        by_caliber = {}
        for key, score_data in scores.items():
            if any(
                mt.type == BasicMatchType.NINEHUNDRED and mt.instance_name in key
                for mt in match.match_types
            ):
                if score_data["score"]["total_score"] is None:
                    continue
                caliber = score_data["score"]["caliber"]
                if caliber not in by_caliber:
                    by_caliber[caliber] = []
                by_caliber[caliber].append(score_data["score"])

        for caliber, cal_scores in by_caliber.items():
            if len(cal_scores) >= 3:
                cal_scores.sort(key=lambda s: s["total_score"], reverse=True)
                top_three = cal_scores[:3]
                total = sum(s["total_score"] for s in top_three)
                x_count = sum(s["total_x_count"] for s in top_three)
                aggregates[f"2700_{caliber}"] = {
                    "score": total,
                    "x_count": x_count,
                    "components": [s["match_type_instance"] for s in top_three],
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

                # Skip NULL scores and scores marked as not_shot
                if score.total_score is None or getattr(score, "not_shot", False):
                    continue
                    
                avg_data = averages_by_type[key]
                avg_data["count"] += 1
                avg_data["total_score"] += score.total_score
                avg_data["total_x_count"] += (score.total_x_count or 0)  # Handle NULL x_count

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
                cal_data["total_x_count_sum"] += (score.total_x_count or 0)  # Handle NULL x_count

                # Track match type data
                if match_type not in cal_data["match_types"]:
                    cal_data["match_types"][match_type] = {
                        "count": 0,
                        "score_sum": 0,
                        "x_count_sum": 0,
                    }

                cal_data["match_types"][match_type]["count"] += 1
                cal_data["match_types"][match_type]["score_sum"] += score.total_score
                cal_data["match_types"][match_type]["x_count_sum"] += (score.total_x_count or 0)  # Handle NULL x_count

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
    "https://54bdef35-ae60-4161-ae24-d2c0da9aaead.preview.emergentagent.com",  # Emergent preview URL
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
