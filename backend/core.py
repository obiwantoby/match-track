import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

# --- Enumerations ---
class BasicMatchType(str, Enum):
    NMC = "NMC"
    SIXHUNDRED = "600"
    NINEHUNDRED = "900"
    PRESIDENTS = "Presidents"

class AggregateType(str, Enum):
    NONE = "None"
    EIGHTEEN_HUNDRED_2X900 = "1800 (2x900)"
    EIGHTEEN_HUNDRED_3X600 = "1800 (3x600)"
    TWENTY_SEVEN_HUNDRED = "2700 (3x900)"

class CaliberType(str, Enum):
    TWENTYTWO = ".22"
    CENTERFIRE = "CF"
    FORTYFIVE = ".45"
    SERVICEPISTOL = "Service Pistol"
    SERVICEREVOLVER = "Service Revolver"
    DR = "DR"

class Rating(str, Enum):
    HM = "HM"    # High Master
    MA = "MA"    # Master
    EX = "EX"    # Expert
    SS = "SS"    # Sharpshooter
    MK = "MK"    # Marksman
    UNC = "UNC"  # Unclassified

# --- Constants ---
STANDARD_CALIBER_ORDER_MAP = {
    CaliberType.TWENTYTWO: 1,
    CaliberType.CENTERFIRE: 2,
    CaliberType.FORTYFIVE: 3,
    CaliberType.SERVICEPISTOL: 4,
    CaliberType.SERVICEREVOLVER: 5,
    CaliberType.DR: 6,
}

# --- Pydantic Models ---
class ShooterBase(BaseModel):
    name: str
    nra_number: Optional[str] = None
    cmp_number: Optional[str] = None
    rating: Optional[Rating] = None

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

class ScoreStage(BaseModel):
    name: str  # e.g., "SF", "TF1", "RF2"
    score: Optional[int] = None
    x_count: Optional[int] = None

class ScoreBase(BaseModel):
    shooter_id: str
    match_id: str
    caliber: CaliberType
    match_type_instance: str  # e.g., "NMC1", "600_1"
    stages: List[ScoreStage]
    total_score: Optional[int] = None
    total_x_count: Optional[int] = None
    not_shot: bool = False

class Score(ScoreBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)