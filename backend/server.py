from fastapi import FastAPI, APIRouter, HTTPException, Body
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'shooting_matches_db')]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class ShooterBase(BaseModel):
    name: str

class ShooterCreate(ShooterBase):
    pass

class Shooter(ShooterBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MatchBase(BaseModel):
    name: str
    date: datetime

class MatchCreate(MatchBase):
    pass

class Match(MatchBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ScoreBase(BaseModel):
    shooter_id: str
    match_id: str
    caliber: str
    sf_score: int
    sf_x_count: int
    tf_score: int
    tf_x_count: int
    rf_score: int
    rf_x_count: int
    nmc_score: Optional[int] = None
    nmc_x_count: Optional[int] = None
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

# Shooter Routes
@api_router.post("/shooters", response_model=Shooter)
async def create_shooter(shooter: ShooterCreate):
    shooter_obj = Shooter(**shooter.dict())
    result = await db.shooters.insert_one(shooter_obj.dict())
    return shooter_obj

@api_router.get("/shooters", response_model=List[Shooter])
async def get_shooters():
    shooters = await db.shooters.find().to_list(1000)
    return [Shooter(**shooter) for shooter in shooters]

@api_router.get("/shooters/{shooter_id}", response_model=Shooter)
async def get_shooter(shooter_id: str):
    shooter = await db.shooters.find_one({"id": shooter_id})
    if not shooter:
        raise HTTPException(status_code=404, detail="Shooter not found")
    return Shooter(**shooter)

# Match Routes
@api_router.post("/matches", response_model=Match)
async def create_match(match: MatchCreate):
    match_obj = Match(**match.dict())
    result = await db.matches.insert_one(match_obj.dict())
    return match_obj

@api_router.get("/matches", response_model=List[Match])
async def get_matches():
    matches = await db.matches.find().sort("date", -1).to_list(1000)
    return [Match(**match) for match in matches]

@api_router.get("/matches/{match_id}", response_model=Match)
async def get_match(match_id: str):
    match = await db.matches.find_one({"id": match_id})
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return Match(**match)

# Score Routes
@api_router.post("/scores", response_model=Score)
async def create_score(score: ScoreCreate):
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
async def get_scores():
    scores = await db.scores.find().to_list(1000)
    return [Score(**score) for score in scores]

@api_router.get("/scores/{score_id}", response_model=Score)
async def get_score(score_id: str):
    score = await db.scores.find_one({"id": score_id})
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    return Score(**score)

# Special Reports
@api_router.get("/match-report/{match_id}", response_model=List[ScoreWithDetails])
async def get_match_report(match_id: str):
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
async def get_shooter_report(shooter_id: str):
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
async def get_shooter_averages(shooter_id: str):
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

# Include the router in the main app
app.include_router(api_router)

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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
