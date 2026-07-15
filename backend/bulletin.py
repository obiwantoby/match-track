"""
NRA Tournament Results Bulletin standings engine.

Pure functions — no DB I/O. See docs/NRA_BULLETIN_SPEC.md and
docs/sample-reports/*.pdf for the format this matches.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple


class Division(str, Enum):
    CIVILIAN = "Civilian"
    POLICE = "Police"
    SERVICE = "Service"


class SpecialCategory(str, Enum):
    GRAND_SENIOR = "Grand Senior"
    SENIOR = "Senior"
    WOMEN = "Women"
    VETERAN = "Veteran"


# Class label for section titles
CLASS_TITLE = {
    "HM": "HIGH MASTER",
    "MA": "MASTER",
    "EX": "EXPERT",
    "SS": "SHARPSHOOTER",
    "MK": "MARKSMAN",
}

CLASS_AWARD_NAME = {
    "HM": "High Master",
    "MA": "Master",
    "EX": "Expert",
    "SSMK": "Sharpshooter/Marksman",
}


@dataclass
class CompetitorResult:
    shooter_id: str
    name: str
    competitor_number: Optional[int]
    rating: Optional[str]  # HM, MA, EX, SS, MK, UNC
    division: Optional[str]  # Civilian, Police, Service
    special_categories: List[str] = field(default_factory=list)
    score: int = 0
    x_count: int = 0
    # optional last-target chain for future tie-break (highest last stage first)
    stage_scores_reverse: List[Optional[int]] = field(default_factory=list)

    def name_with_suffixes(self) -> str:
        suffixes: List[str] = []
        cats = set(self.special_categories or [])
        if SpecialCategory.GRAND_SENIOR.value in cats or "Grand Senior" in cats:
            suffixes.append("GS")
        if SpecialCategory.VETERAN.value in cats or "Veteran" in cats:
            suffixes.append("VET")
        if not suffixes:
            return self.name
        return f"{self.name} {' '.join(suffixes)}"


def format_score_x(score: int, x_count: int) -> str:
    """Match sample display: 194.8 x  /  298.21 x  /  2659  156  x for large X."""
    if x_count is None:
        x_count = 0
    if x_count >= 100:
        return f"{score}  {x_count}  x"
    return f"{score}.{x_count}  x"


def sort_key(c: CompetitorResult) -> Tuple:
    """Higher score, then higher X, then lower competitor number."""
    num = c.competitor_number if c.competitor_number is not None else 10**9
    return (-c.score, -c.x_count, num)


def rank_competitors(results: Sequence[CompetitorResult]) -> List[CompetitorResult]:
    return sorted(results, key=sort_key)


def _is_police_or_service(division: Optional[str]) -> bool:
    return division in (Division.POLICE.value, Division.SERVICE.value, "Police", "Service")


def _is_civilian(division: Optional[str]) -> bool:
    return division in (Division.CIVILIAN.value, "Civilian", None, "")


def _has_cat(c: CompetitorResult, cat: str) -> bool:
    return cat in (c.special_categories or [])


def place_label_open(place: int) -> Optional[str]:
    return {1: "Match Winner", 2: "Second Place", 3: "Third Place"}.get(place)


def place_label_class(place: int, class_key: str, division_label: str) -> Optional[str]:
    """class_key: HM|MA|EX|SSMK; division_label: Police/Service|Civilian|All Categories"""
    award = CLASS_AWARD_NAME.get(class_key, class_key)
    ordinals = {
        1: "First",
        2: "Second",
        3: "Third",
        4: "Fourth",
    }
    if place not in ordinals:
        return None
    # SS/MK and most classes: only top 3; Expert Civilian samples label Fourth
    if class_key == "SSMK" and place > 3:
        return None
    if class_key != "EX" and place > 3:
        return None
    if class_key == "EX" and place > 4:
        return None
    return f"{ordinals[place]} {award} - {division_label}"


def build_open_place_awards(
    ranked: Sequence[CompetitorResult], top_n: int = 3
) -> List[Dict[str, Any]]:
    rows = []
    for i, c in enumerate(ranked[:top_n], start=1):
        rows.append(_row(c, i, place_label_open(i)))
    return rows


def build_special_category_awards(
    ranked: Sequence[CompetitorResult],
) -> List[Dict[str, Any]]:
    """
    One winner per special award (first in ranked order who qualifies).
    Order matches sample bulletins.
    """
    specs = [
        ("High Senior", lambda c: _has_cat(c, "Senior")),
        ("High Woman", lambda c: _has_cat(c, "Women")),
        ("High Civilian", lambda c: _is_civilian(c.division)),
        ("High Police", lambda c: c.division == Division.POLICE.value or c.division == "Police"),
        ("High Service", lambda c: c.division == Division.SERVICE.value or c.division == "Service"),
        ("High Grand Senior", lambda c: _has_cat(c, "Grand Senior")),
        ("High Veteran", lambda c: _has_cat(c, "Veteran")),
    ]
    out: List[Dict[str, Any]] = []
    for title, pred in specs:
        for c in ranked:
            if pred(c):
                row = _row(c, None, title)
                out.append(row)
                break
    return out


def build_class_section(
    ranked: Sequence[CompetitorResult],
    *,
    ratings: Sequence[str],
    division_mode: str,
    class_key: str,
    division_label: str,
    section_title: str,
) -> Dict[str, Any]:
    """
    division_mode: 'civilian' | 'police_service' | 'all'
    """
    filtered: List[CompetitorResult] = []
    for c in ranked:
        r = (c.rating or "").upper()
        if r not in ratings:
            continue
        if division_mode == "civilian" and not _is_civilian(c.division):
            continue
        if division_mode == "police_service" and not _is_police_or_service(c.division):
            continue
        # 'all' — no division filter
        filtered.append(c)

    rows = []
    for i, c in enumerate(filtered, start=1):
        rows.append(_row(c, i, place_label_class(i, class_key, division_label)))

    return {
        "title": section_title,
        "competitor_count": len(filtered),
        "rows": rows,
    }


def build_all_class_sections(ranked: Sequence[CompetitorResult]) -> List[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    plan = [
        (["HM"], "police_service", "HM", "Police/Service", "HIGH MASTER -- POLICE/SERVICE"),
        (["HM"], "civilian", "HM", "Civilian", "HIGH MASTER -- CIVILIAN"),
        (["MA"], "police_service", "MA", "Police/Service", "MASTER -- POLICE/SERVICE"),
        (["MA"], "civilian", "MA", "Civilian", "MASTER -- CIVILIAN"),
        (["EX"], "police_service", "EX", "Police/Service", "EXPERT -- POLICE/SERVICE"),
        (["EX"], "civilian", "EX", "Civilian", "EXPERT -- CIVILIAN"),
        (["SS", "MK"], "all", "SSMK", "All Categories", "SHARPSHOOTER/MARKSMAN -- ALL CATEGORIES"),
    ]
    for ratings, mode, ckey, dlabel, title in plan:
        sec = build_class_section(
            ranked,
            ratings=ratings,
            division_mode=mode,
            class_key=ckey,
            division_label=dlabel,
            section_title=title,
        )
        # Always include section even if empty? Samples only show non-empty.
        if sec["competitor_count"] > 0:
            sections.append(sec)
    return sections


def _row(
    c: CompetitorResult, place: Optional[int], award_label: Optional[str]
) -> Dict[str, Any]:
    return {
        "place": place,
        "competitor_number": c.competitor_number,
        "shooter_id": c.shooter_id,
        "name": c.name,
        "name_display": c.name_with_suffixes(),
        "score": c.score,
        "x_count": c.x_count,
        "score_display": format_score_x(c.score, c.x_count),
        "award_label": award_label,
        "rating": c.rating,
        "division": c.division,
    }


def build_bulletin(
    *,
    tournament_title: str,
    date_line: str,
    location: str,
    match_no: int,
    event_title: str,
    results: Sequence[CompetitorResult],
    open_label: str = "OPEN",
) -> Dict[str, Any]:
    """
    Full bulletin payload for web / Excel / print.

    event_title example: ".22 SLOW FIRE MATCH" or ".22 NMC MATCH"
    """
    ranked = rank_competitors([r for r in results if r.score is not None])
    open_awards = build_open_place_awards(ranked)
    specials = build_special_category_awards(ranked)
    class_sections = build_all_class_sections(ranked)

    return {
        "header": {
            "bulletin_title": "TOURNAMENT RESULTS BULLETIN",
            "tournament_title": tournament_title,
            "date_line": date_line,
            "location": location,
            "match_no": match_no,
            "event_title": event_title,
            "open_label": open_label,
        },
        "competitor_count": len(ranked),
        "open_place_awards": open_awards,
        "special_category_awards": specials,
        "class_sections": class_sections,
        "full_ranking": [_row(c, i, None) for i, c in enumerate(ranked, start=1)],
    }


# --- Score extraction helpers (stage / aggregate) ---
# NMC mid-block (SFNMC/TFNMC/RFNMC) is NEVER included in SF/TF/RF — separate event.

SLOW_STAGES = {"SF", "SF1", "SF2"}
TIMED_STAGES = {"TF", "TF1", "TF2"}
RAPID_STAGES = {"RF", "RF1", "RF2"}
NMC_BLOCK_STAGES = {"SFNMC", "TFNMC", "RFNMC"}  # 900 course mid-block only


def sum_stages(
    stages: Sequence[Dict[str, Any]], allowed_names: set
) -> Tuple[Optional[int], Optional[int]]:
    """Sum score/x for stages whose names are in allowed_names. None if no valid stages."""
    total_s = 0
    total_x = 0
    any_valid = False
    for st in stages:
        name = st.get("name") or ""
        if name not in allowed_names:
            continue
        sc = st.get("score")
        if sc is None:
            continue
        any_valid = True
        total_s += int(sc)
        xc = st.get("x_count")
        total_x += int(xc) if xc is not None else 0
    if not any_valid:
        return None, None
    return total_s, total_x


def event_score_from_score_doc(
    score_doc: Dict[str, Any], event_scope: str
) -> Tuple[Optional[int], Optional[int]]:
    """
    event_scope:
      total | slow | timed | rapid | nmc
      (nmc = SFNMC+TFNMC+RFNMC block on a 900; total = full scorecard)
    """
    if score_doc.get("not_shot"):
        return None, None
    stages = score_doc.get("stages") or []
    if event_scope == "total":
        ts = score_doc.get("total_score")
        if ts is None:
            return None, None
        return int(ts), int(score_doc.get("total_x_count") or 0)
    if event_scope == "slow":
        return sum_stages(stages, SLOW_STAGES)
    if event_scope == "timed":
        return sum_stages(stages, TIMED_STAGES)
    if event_scope == "rapid":
        return sum_stages(stages, RAPID_STAGES)
    if event_scope == "nmc":
        # Prefer mid-block on 900; if this is an NMC scorecard, use full total
        block = sum_stages(stages, NMC_BLOCK_STAGES)
        if block[0] is not None:
            return block
        ts = score_doc.get("total_score")
        if ts is None:
            return None, None
        return int(ts), int(score_doc.get("total_x_count") or 0)
    raise ValueError(f"Unknown event_scope: {event_scope}")


def event_title_for(caliber: str, event_scope: str, aggregate: bool = False) -> str:
    cal = caliber or ""
    if aggregate and event_scope == "grand":
        return "GRAND AGGREGATE MATCH"
    if aggregate and event_scope == "caliber":
        return f"{cal} AGGREGATE MATCH"
    names = {
        "slow": f"{cal} SLOW FIRE MATCH",
        "timed": f"{cal} TIMED FIRE MATCH",
        "rapid": f"{cal} RAPID FIRE MATCH",
        "nmc": f"{cal} NMC MATCH",
        "total": f"{cal} MATCH",
    }
    return names.get(event_scope, f"{cal} MATCH")
