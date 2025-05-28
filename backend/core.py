import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any  # Add Dict, Any

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

# --- Helper functions for match configuration ---
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
        # Modified order: SF1, SF2, SFNMC, TFNMC, RFNMC, TF1, TF2, RF1, RF2
        return {
            "entry_stages": ["SF1", "SF2", "SFNMC", "TFNMC", "RFNMC", "TF1", "TF2", "RF1", "RF2"],
            "subtotal_stages": ["SF", "TF", "RF"],
            "subtotal_mappings": {
                "SF": ["SF1", "SF2", "SFNMC"],
                "TF": ["TF1", "TF2", "TFNMC"],
                "RF": ["RF1", "RF2", "RFNMC"],
            },
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