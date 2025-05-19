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

@api_router.get("/match-types")
async def get_match_types(current_user: User = Depends(get_current_active_user)):
    """Get all available match types with their stage definitions"""
    result = {}
    for match_type in BasicMatchType:
        result[match_type] = {
            "stages": get_stages_for_match_type(match_type),
            "max_score": get_match_type_max_score(match_type)
        }
    return result

@api_router.get("/match-config/{match_id}")
async def get_match_config(
    match_id: str,
    current_user: User = Depends(get_current_active_user)
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
        "match_types": []
    }
    
    for match_type_instance in match_obj.match_types:
        stages = get_stages_for_match_type(match_type_instance.type)
        config["match_types"].append({
            "type": match_type_instance.type,
            "instance_name": match_type_instance.instance_name,
            "calibers": match_type_instance.calibers,
            "stages": stages,
            "max_score": get_match_type_max_score(match_type_instance.type)
        })
    
    return config

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
    
    # Calculate total score and X count
    total_score = sum(stage.score for stage in score.stages)
    total_x_count = sum(stage.x_count for stage in score.stages)
    
    score_dict = score.dict()
    score_dict.update({
        "total_score": total_score,
        "total_x_count": total_x_count
    })
    
    score_obj = Score(**score_dict)
    await db.scores.insert_one(score_obj.dict())
    return score_obj

@api_router.put("/scores/{score_id}", response_model=Score)
async def update_score(
    score_id: str,
    score_update: ScoreCreate,
    current_user: User = Depends(get_current_active_user)
):
    # Only admins can update scores
    if current_user.role == UserRole.REPORTER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Check if score exists
    existing_score = await db.scores.find_one({"id": score_id})
    if not existing_score:
        raise HTTPException(status_code=404, detail="Score not found")
    
    # Calculate total score and X count
    total_score = sum(stage.score for stage in score_update.stages)
    total_x_count = sum(stage.x_count for stage in score_update.stages)
    
    score_dict = score_update.dict()
    score_dict.update({
        "total_score": total_score,
        "total_x_count": total_x_count
    })
    
    # Update score
    await db.scores.update_one(
        {"id": score_id},
        {"$set": score_dict}
    )
    
    # Get updated score
    updated_score = await db.scores.find_one({"id": score_id})
    return Score(**updated_score)

@api_router.get("/scores", response_model=List[Score])
async def get_scores(
    match_id: Optional[str] = None,
    shooter_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
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
    score_id: str,
    current_user: User = Depends(get_current_active_user)
):
    score = await db.scores.find_one({"id": score_id})
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    return Score(**score)

# Special Reports
@api_router.get("/match-report/{match_id}", response_model=Dict[str, Any])
async def get_match_report(
    match_id: str,
    current_user: User = Depends(get_current_active_user)
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
            shooter_data["scores"][key] = score_obj
    
    # Calculate aggregate scores if applicable
    if match_obj.aggregate_type != AggregateType.NONE:
        for shooter_data in result["shooters"].values():
            aggregates = calculate_aggregates(shooter_data["scores"], match_obj)
            shooter_data["aggregates"] = aggregates
    
    return result

def calculate_aggregates(scores, match):
    """Calculate aggregate scores based on match configuration"""
    aggregates = {}
    
    # 1800 (2x900) Aggregate
    if match.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_2X900:
        # Find all 900 match instances and group by caliber
        by_caliber = {}
        for key, score in scores.items():
            if any(mt.type == BasicMatchType.NINEHUNDRED and mt.instance_name in key for mt in match.match_types):
                caliber = score.caliber
                if caliber not in by_caliber:
                    by_caliber[caliber] = []
                by_caliber[caliber].append(score)
        
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
                    "components": [s.match_type_instance for s in top_two]
                }
    
    # 1800 (3x600) Aggregate
    elif match.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_3X600:
        # Find all 600 match instances and group by caliber
        by_caliber = {}
        for key, score in scores.items():
            if any(mt.type == BasicMatchType.SIXHUNDRED and mt.instance_name in key for mt in match.match_types):
                caliber = score.caliber
                if caliber not in by_caliber:
                    by_caliber[caliber] = []
                by_caliber[caliber].append(score)
        
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
                    "components": [s.match_type_instance for s in top_three]
                }
    
    # 2700 Aggregate
    elif match.aggregate_type == AggregateType.TWENTY_SEVEN_HUNDRED:
        # Find all 900 match instances and group by caliber
        by_caliber = {}
        for key, score in scores.items():
            if any(mt.type == BasicMatchType.NINEHUNDRED and mt.instance_name in key for mt in match.match_types):
                caliber = score.caliber
                if caliber not in by_caliber:
                    by_caliber[caliber] = []
                by_caliber[caliber].append(score)
        
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
                    "components": [s.match_type_instance for s in top_three]
                }
    
    return aggregates

@api_router.get("/shooter-report/{shooter_id}")
async def get_shooter_report(
    shooter_id: str,
    current_user: User = Depends(get_current_active_user)
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
        "averages": {
            "by_match_type": {},
            "by_caliber": {}
        }
    }
    
    # Group scores by match
    for score in score_objs:
        match_id = score.match_id
        if match_id in matches:
            match = matches[match_id]
            if match_id not in report["matches"]:
                report["matches"][match_id] = {
                    "match": match,
                    "scores": []
                }
            
            # Add score details
            report["matches"][match_id]["scores"].append({
                "score": score,
                "match_type": next((mt for mt in match.match_types if mt.instance_name == score.match_type_instance), None)
            })
    
    # Calculate averages by match type and caliber
    averages_by_type = {}
    averages_by_caliber = {}
    
    for score in score_objs:
        match_id = score.match_id
        if match_id in matches:
            match = matches[match_id]
            match_type = next((mt.type for mt in match.match_types if mt.instance_name == score.match_type_instance), None)
            
            if match_type:
                # By match type and caliber
                key = f"{match_type}_{score.caliber}"
                if key not in averages_by_type:
                    averages_by_type[key] = {
                        "count": 0,
                        "total_score": 0,
                        "total_x_count": 0,
                        "stages": {}
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
                            "x_count_sum": 0
                        }
                    
                    avg_data["stages"][stage.name]["score_sum"] += stage.score
                    avg_data["stages"][stage.name]["x_count_sum"] += stage.x_count
                
                # By caliber only
                if score.caliber not in averages_by_caliber:
                    averages_by_caliber[score.caliber] = {
                        "count": 0,
                        "total_score_sum": 0,
                        "total_x_count_sum": 0,
                        "match_types": {}
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
                        "x_count_sum": 0
                    }
                
                cal_data["match_types"][match_type]["count"] += 1
                cal_data["match_types"][match_type]["score_sum"] += score.total_score
                cal_data["match_types"][match_type]["x_count_sum"] += score.total_x_count
    
    # Calculate final averages
    for key, data in averages_by_type.items():
        if data["count"] > 0:
            data["avg_score"] = round(data["total_score"] / data["count"], 2)
            data["avg_x_count"] = round(data["total_x_count"] / data["count"], 2)
            
            for stage_name, stage_data in data["stages"].items():
                stage_data["avg_score"] = round(stage_data["score_sum"] / data["count"], 2)
                stage_data["avg_x_count"] = round(stage_data["x_count_sum"] / data["count"], 2)
    
    for caliber, data in averages_by_caliber.items():
        if data["count"] > 0:
            data["avg_score"] = round(data["total_score_sum"] / data["count"], 2)
            data["avg_x_count"] = round(data["total_x_count_sum"] / data["count"], 2)
            
            for match_type, mt_data in data["match_types"].items():
                if mt_data["count"] > 0:
                    mt_data["avg_score"] = round(mt_data["score_sum"] / mt_data["count"], 2)
                    mt_data["avg_x_count"] = round(mt_data["x_count_sum"] / mt_data["count"], 2)
    
    report["averages"]["by_match_type"] = averages_by_type
    report["averages"]["by_caliber"] = averages_by_caliber
    
    return report

# Root API endpoint
@api_router.get("/")
async def root():
    return {"message": "Enhanced Shooting Match Score Management API"}

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
