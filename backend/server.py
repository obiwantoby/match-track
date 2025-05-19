from fastapi import FastAPI, APIRouter, HTTPException, Body, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Union, Dict, Any
import uuid
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'shooting_matches_db')]

# Auth settings
SECRET_KEY = os.environ.get("SECRET_KEY", "CHANGE_THIS_TO_A_RANDOM_SECRET_IN_PRODUCTION")
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
    name: str  # e.g., "SF", "TF1", "RFNMC"
    score: int
    x_count: int

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
def get_stages_for_match_type(match_type: BasicMatchType) -> List[str]:
    """Return the stage names for a given match type"""
    if match_type == BasicMatchType.NMC:
        return ["SF", "TF", "RF"]
    elif match_type == BasicMatchType.SIXHUNDRED:
        return ["SF1", "SF2", "TF1", "TF2", "RF1", "RF2"]
    elif match_type == BasicMatchType.NINEHUNDRED:
        return ["SF1", "SF2", "SFNMC", "TFNMC", "RFNMC", "TF1", "TF2", "RF1", "RF2"]
    elif match_type == BasicMatchType.PRESIDENTS:
        return ["SF1", "SF2", "TF", "RF"]
    return []

def get_match_type_max_score(match_type: BasicMatchType) -> int:
    """Return the maximum possible score for a match type"""
    if match_type == BasicMatchType.NMC:
        return 300
    elif match_type == BasicMatchType.SIXHUNDRED:
        return 600
    elif match_type == BasicMatchType.NINEHUNDRED:
        return 900
    elif match_type == BasicMatchType.PRESIDENTS:
        return 400
    return 0

async def get_user(email: str):
    user_dict = await db.users.find_one({"email": email})
    if user_dict:
        return UserInDB(**user_dict)
    return None

async def authenticate_user(email: str, password: str):
    user = await get_user(email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

# Auth Routes
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
        "role": user.role
    }

@auth_router.post("/register", response_model=User)
async def register_user(user: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    user_obj = UserInDB(**user.dict(), hashed_password=hashed_password)
    
    # Save to database
    await db.users.insert_one(user_obj.dict())
    
    # Return user without password
    return User(**user_obj.dict())

@auth_router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# User management (Admin only)
@auth_router.get("/users", response_model=List[User])
async def get_users(current_user: User = Depends(get_admin_user)):
    users = await db.users.find().to_list(1000)
    return [User(**user) for user in users]

@auth_router.post("/users", response_model=User)
async def create_user(user: UserCreate, current_user: User = Depends(get_admin_user)):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    user_obj = UserInDB(**user.dict(), hashed_password=hashed_password)
    
    # Save to database
    await db.users.insert_one(user_obj.dict())
    
    # Return user without password
    return User(**user_obj.dict())

@auth_router.put("/users/{user_id}/role", response_model=User)
async def update_user_role(
    user_id: str, 
    role: UserRole, 
    current_user: User = Depends(get_admin_user)
):
    # Prevent users from changing their own role
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    # Update user role
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"role": role}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Return updated user
    user = await db.users.find_one({"id": user_id})
    return User(**user)

# Shooter Routes
@api_router.post("/shooters", response_model=Shooter)
async def create_shooter(
    shooter: ShooterCreate,
    current_user: User = Depends(get_current_active_user)
):
    # Only admins can create shooters
    if current_user.role == UserRole.REPORTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
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
    shooter_id: str,
    current_user: User = Depends(get_current_active_user)
):
    shooter = await db.shooters.find_one({"id": shooter_id})
    if not shooter:
        raise HTTPException(status_code=404, detail="Shooter not found")
    return Shooter(**shooter)

# Match Routes
@api_router.post("/matches", response_model=Match)
async def create_match(
    match: MatchCreate,
    current_user: User = Depends(get_current_active_user)
):
    # Only admins can create matches
    if current_user.role == UserRole.REPORTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
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
    match_id: str,
    current_user: User = Depends(get_current_active_user)
):
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return Match(**match)

# Score Routes
@api_router.post("/scores", response_model=Score)
async def create_score(
    score: ScoreCreate,
    current_user: User = Depends(get_current_active_user)
):
    # Only admins can create scores
    if current_user.role == UserRole.REPORTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Calculate NMC (National Match Course) as SF + TF + RF
    nmc_score = score.sf_score + score.tf_score + score.rf_score
    nmc_x_count = score.sf_x_count + score.tf_x_count + score.rf_x_count
    
    # Total score is the same as NMC for now
    total_score = nmc_score
    total_x_count = nmc_x_count
    
    score_dict = score.dict()
    score_dict.update({
        "nmc_score": nmc_score,
        "nmc_x_count": nmc_x_count,
        "total_score": total_score,
        "total_x_count": total_x_count
    })
    
    score_obj = Score(**score_dict)
    await db.scores.insert_one(score_obj.dict())
    return score_obj

@api_router.get("/scores", response_model=List[Score])
async def get_scores(current_user: User = Depends(get_current_active_user)):
    scores = await db.scores.find().to_list(1000)
    return [Score(**score) for score in scores]

@api_router.get("/scores/{score_id}", response_model=Score)
async def get_score(
    score_id: str,
    current_user: User = Depends(get_current_active_user)
):
    score = await db.scores.find_one({"id": score_id})
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    return Score(**score)

# Special Reports
@api_router.get("/match-report/{match_id}", response_model=List[ScoreWithDetails])
async def get_match_report(
    match_id: str,
    current_user: User = Depends(get_current_active_user)
):
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Get all scores for this match
    scores = await db.scores.find({"match_id": match_id}).to_list(1000)
    
    # For each score, get the shooter details
    result = []
    for score in scores:
        shooter = await db.shooters.find_one({"id": score["shooter_id"]})
        if shooter:
            # Combine score with shooter and match details
            score_with_details = {
                **score,
                "shooter_name": shooter["name"],
                "match_name": match["name"],
                "match_date": match["date"]
            }
            result.append(ScoreWithDetails(**score_with_details))
    
    return result

@api_router.get("/shooter-report/{shooter_id}", response_model=List[ScoreWithDetails])
async def get_shooter_report(
    shooter_id: str,
    current_user: User = Depends(get_current_active_user)
):
    shooter = await db.shooters.find_one({"id": shooter_id})
    if not shooter:
        raise HTTPException(status_code=404, detail="Shooter not found")
    
    # Get all scores for this shooter
    scores = await db.scores.find({"shooter_id": shooter_id}).to_list(1000)
    
    # For each score, get the match details
    result = []
    for score in scores:
        match = await db.matches.find_one({"id": score["match_id"]})
        if match:
            # Combine score with shooter and match details
            score_with_details = {
                **score,
                "shooter_name": shooter["name"],
                "match_name": match["name"],
                "match_date": match["date"]
            }
            result.append(ScoreWithDetails(**score_with_details))
    
    # Sort by match date
    result.sort(key=lambda x: x.match_date, reverse=True)
    
    return result

@api_router.get("/shooter-averages/{shooter_id}")
async def get_shooter_averages(
    shooter_id: str,
    current_user: User = Depends(get_current_active_user)
):
    shooter = await db.shooters.find_one({"id": shooter_id})
    if not shooter:
        raise HTTPException(status_code=404, detail="Shooter not found")
    
    # Get all scores for this shooter
    scores = await db.scores.find({"shooter_id": shooter_id}).to_list(1000)
    
    # Calculate averages by caliber
    caliber_averages = {}
    
    for score in scores:
        caliber = score["caliber"]
        if caliber not in caliber_averages:
            caliber_averages[caliber] = {
                "sf_score_sum": 0, "sf_x_count_sum": 0,
                "tf_score_sum": 0, "tf_x_count_sum": 0,
                "rf_score_sum": 0, "rf_x_count_sum": 0,
                "nmc_score_sum": 0, "nmc_x_count_sum": 0,
                "total_score_sum": 0, "total_x_count_sum": 0,
                "count": 0
            }
        
        # Add to sums
        caliber_averages[caliber]["sf_score_sum"] += score["sf_score"]
        caliber_averages[caliber]["sf_x_count_sum"] += score["sf_x_count"]
        caliber_averages[caliber]["tf_score_sum"] += score["tf_score"]
        caliber_averages[caliber]["tf_x_count_sum"] += score["tf_x_count"]
        caliber_averages[caliber]["rf_score_sum"] += score["rf_score"]
        caliber_averages[caliber]["rf_x_count_sum"] += score["rf_x_count"]
        caliber_averages[caliber]["nmc_score_sum"] += score["nmc_score"]
        caliber_averages[caliber]["nmc_x_count_sum"] += score["nmc_x_count"]
        caliber_averages[caliber]["total_score_sum"] += score["total_score"]
        caliber_averages[caliber]["total_x_count_sum"] += score["total_x_count"]
        caliber_averages[caliber]["count"] += 1
    
    # Calculate averages
    result = {}
    for caliber, data in caliber_averages.items():
        count = data["count"]
        result[caliber] = {
            "sf_score_avg": round(data["sf_score_sum"] / count, 2),
            "sf_x_count_avg": round(data["sf_x_count_sum"] / count, 2),
            "tf_score_avg": round(data["tf_score_sum"] / count, 2),
            "tf_x_count_avg": round(data["tf_x_count_sum"] / count, 2),
            "rf_score_avg": round(data["rf_score_sum"] / count, 2),
            "rf_x_count_avg": round(data["rf_x_count_sum"] / count, 2),
            "nmc_score_avg": round(data["nmc_score_sum"] / count, 2),
            "nmc_x_count_avg": round(data["nmc_x_count_sum"] / count, 2),
            "total_score_avg": round(data["total_score_sum"] / count, 2),
            "total_x_count_avg": round(data["total_x_count_sum"] / count, 2),
            "matches_count": count
        }
    
    return {
        "shooter_name": shooter["name"],
        "caliber_averages": result
    }

# Root API endpoint
@api_router.get("/")
async def root():
    return {"message": "Shooting Match Score Management API"}

# Include the routers in the main app
app.include_router(api_router)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create a first admin user if no users exist
@app.on_event("startup")
async def create_first_admin():
    # Check if users collection is empty
    users_count = await db.users.count_documents({})
    if users_count == 0:
        # Create default admin user
        default_email = "admin@example.com"
        default_password = "admin123"  # Change this in production!
        hashed_password = get_password_hash(default_password)
        
        user = UserInDB(
            email=default_email,
            username="admin",
            role=UserRole.ADMIN,
            hashed_password=hashed_password
        )
        
        await db.users.insert_one(user.dict())
        logger.info(f"Created default admin user: {default_email}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
