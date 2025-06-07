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

# --- More Helper Functions ---

def _get_aggregate_components(aggregate_type: AggregateType) -> tuple[Optional[BasicMatchType], list[str]]:
    if aggregate_type == AggregateType.TWENTY_SEVEN_HUNDRED:
        return BasicMatchType.NINEHUNDRED, ["SF", "NMC", "TF", "RF", "900"]
    elif aggregate_type == AggregateType.EIGHTEEN_HUNDRED_2X900:
        return BasicMatchType.NINEHUNDRED, ["SF", "NMC", "TF", "RF", "900"]
    elif aggregate_type == AggregateType.EIGHTEEN_HUNDRED_3X600:
        return BasicMatchType.SIXHUNDRED, ["SF", "TF", "RF", "600"] # No NMC for 600
    return None, []

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

def calculate_aggregates(scores: Dict[str, Any], match: Match) -> Dict[str, Any]:
    """Calculate aggregate scores based on match configuration"""
    aggregates = {}

    # 1800 (2x900) Aggregate
    if match.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_2X900:
        by_caliber: Dict[CaliberType, List[Dict[str, Any]]] = {}
        for key, score_data in scores.items():
            # Ensure score_data["score"] exists and has "total_score"
            if not score_data.get("score") or score_data["score"].get("total_score") is None:
                continue

            # Check if the match type instance corresponds to a 900-point match type
            is_900_type = False
            for mt in match.match_types:
                if mt.instance_name in key and mt.type == BasicMatchType.NINEHUNDRED:
                    is_900_type = True
                    break
            
            if is_900_type:
                caliber_str = score_data["score"]["caliber"]
                # Convert caliber_str to CaliberType enum if necessary, or ensure consistency
                # Assuming caliber_str is a value that can be mapped to CaliberType
                try:
                    caliber = CaliberType(caliber_str)
                    if caliber not in by_caliber:
                        by_caliber[caliber] = []
                    by_caliber[caliber].append(score_data["score"])
                except ValueError:
                    # Handle cases where caliber_str is not a valid CaliberType
                    pass # Or log a warning

        for caliber, cal_scores in by_caliber.items():
            if len(cal_scores) >= 2:
                cal_scores.sort(key=lambda s: s["total_score"], reverse=True)
                top_two = cal_scores[:2]
                total = sum(s["total_score"] for s in top_two)
                x_count = sum(s.get("total_x_count", 0) or 0 for s in top_two) # Handle None for x_count
                aggregates[f"1800_{caliber.value}"] = {
                    "score": total,
                    "x_count": x_count,
                    "components": [s["match_type_instance"] for s in top_two],
                }

    # 1800 (3x600) Aggregate
    elif match.aggregate_type == AggregateType.EIGHTEEN_HUNDRED_3X600:
        by_caliber: Dict[CaliberType, List[Dict[str, Any]]] = {}
        for key, score_data in scores.items():
            if not score_data.get("score") or score_data["score"].get("total_score") is None:
                continue

            is_600_type = False
            for mt in match.match_types:
                if mt.instance_name in key and mt.type == BasicMatchType.SIXHUNDRED:
                    is_600_type = True
                    break

            if is_600_type:
                caliber_str = score_data["score"]["caliber"]
                try:
                    caliber = CaliberType(caliber_str)
                    if caliber not in by_caliber:
                        by_caliber[caliber] = []
                    by_caliber[caliber].append(score_data["score"])
                except ValueError:
                    pass

        for caliber, cal_scores in by_caliber.items():
            if len(cal_scores) >= 3:
                cal_scores.sort(key=lambda s: s["total_score"], reverse=True)
                top_three = cal_scores[:3]
                total = sum(s["total_score"] for s in top_three)
                x_count = sum(s.get("total_x_count", 0) or 0 for s in top_three)
                aggregates[f"1800_{caliber.value}"] = {
                    "score": total,
                    "x_count": x_count,
                    "components": [s["match_type_instance"] for s in top_three],
                }

    # 2700 Aggregate
    elif match.aggregate_type == AggregateType.TWENTY_SEVEN_HUNDRED:
        by_caliber: Dict[CaliberType, List[Dict[str, Any]]] = {}
        for key, score_data in scores.items():
            if not score_data.get("score") or score_data["score"].get("total_score") is None:
                continue
            
            is_900_type = False
            for mt in match.match_types:
                if mt.instance_name in key and mt.type == BasicMatchType.NINEHUNDRED:
                    is_900_type = True
                    break

            if is_900_type:
                caliber_str = score_data["score"]["caliber"]
                try:
                    caliber = CaliberType(caliber_str)
                    if caliber not in by_caliber:
                        by_caliber[caliber] = []
                    by_caliber[caliber].append(score_data["score"])
                except ValueError:
                    pass
        
        for caliber, cal_scores in by_caliber.items():
            if len(cal_scores) >= 3:
                cal_scores.sort(key=lambda s: s["total_score"], reverse=True)
                top_three = cal_scores[:3]
                total = sum(s["total_score"] for s in top_three)
                x_count = sum(s.get("total_x_count", 0) or 0 for s in top_three)
                aggregates[f"2700_{caliber.value}"] = {
                    "score": total,
                    "x_count": x_count,
                    "components": [s["match_type_instance"] for s in top_three],
                }

    return aggregates

def calculate_shooter_averages_by_caliber(scores: List[Score]) -> Dict[str, Any]:
    """Calculate shooter's average performance by caliber from a list of scores"""
    by_caliber = {}
    
    for score_obj in scores:
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
        by_caliber[caliber]["total_x_count_sum"] += score_obj.total_x_count or 0

        # Process stages
        for stage in score_obj.stages:
            if stage.score is None:
                continue
                
            if "SF" in stage.name:
                by_caliber[caliber]["sf_score_sum"] += stage.score
                by_caliber[caliber]["sf_valid_count"] += 1
                by_caliber[caliber]["sf_x_count_sum"] += stage.x_count or 0
            elif "TF" in stage.name:
                by_caliber[caliber]["tf_score_sum"] += stage.score
                by_caliber[caliber]["tf_valid_count"] += 1
                by_caliber[caliber]["tf_x_count_sum"] += stage.x_count or 0
            elif "RF" in stage.name:
                by_caliber[caliber]["rf_score_sum"] += stage.score
                by_caliber[caliber]["rf_valid_count"] += 1
                by_caliber[caliber]["rf_x_count_sum"] += stage.x_count or 0

        # Calculate NMC scores (typically SF + TF + RF for a single match)
        if "NMC" in score_obj.match_type_instance and score_obj.total_score is not None:
            by_caliber[caliber]["nmc_score_sum"] += score_obj.total_score
            by_caliber[caliber]["nmc_valid_count"] += 1
            by_caliber[caliber]["nmc_x_count_sum"] += score_obj.total_x_count or 0

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

    return averages

def calculate_score_subtotals(score_obj: Score, stages_config: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate subtotals for a score based on stage configuration"""
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
    
    return subtotals

# --- API Endpoint Function ---
async def get_shooter_report_data(shooter_id: str, db) -> Dict[str, Any]:
    """Get comprehensive shooter report including matches and detailed scores with averages"""
    
    shooter = await db.shooters.find_one({"id": shooter_id})
    if not shooter:
        return None

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