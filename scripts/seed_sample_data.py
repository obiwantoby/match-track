#!/usr/bin/env python3
"""
Clean, reloadable sample dataset for Match Track (beta / demo).

By default CLEANS previous sample data first (safe: only records tagged as sample),
then loads a large consistent set for Results Bulletin, leagues, and multi-gun.

Usage:
  # Full clean reload (recommended)
  BASE_URL=http://127.0.0.1:8001/api python3 scripts/seed_sample_data.py

  # Append without deleting prior sample rows
  CLEAN=0 BASE_URL=... python3 scripts/seed_sample_data.py

All sample shooters use NRA numbers SEED00001… so they never collide with real data.
All sample matches/leagues are named with prefix "[SAMPLE] ".

Default login: admin@example.com / admin123
"""

from __future__ import annotations

import os
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080/api").rstrip("/")
EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
# Clean previous sample data before load (default ON)
CLEAN = os.environ.get("CLEAN", "1").strip().lower() not in ("0", "false", "no")

RNG = random.Random(42)
SAMPLE_PREFIX = "[SAMPLE] "
SEED_NRA_PREFIX = "SEED"
LEAGUE_NAME = f"{SAMPLE_PREFIX}River City Pistol League"

# ---------------------------------------------------------------------------
# Large clean shooter roster (Last, First) — unique SEED NRA + competitor #
# ---------------------------------------------------------------------------

def _build_shooters() -> List[Dict[str, Any]]:
    """36 shooters spanning classes, divisions, and special categories."""
    # (last, first, rating, division, specials)
    people: List[Tuple[str, str, str, str, List[str]]] = [
        # High Master
        ("Jorgenson", "Travis", "HM", "Civilian", ["Veteran"]),
        ("Sanderson", "Keith", "HM", "Civilian", ["Veteran"]),
        ("Shue", "Jon", "HM", "Civilian", ["Veteran"]),
        ("Markowski", "Greg", "HM", "Police", []),
        ("Emmert-Traciak", "Lisa", "HM", "Service", ["Women"]),
        ("Zurek", "John", "HM", "Civilian", ["Veteran"]),
        # Master
        ("Liming", "Christopher", "MA", "Police", []),
        ("Standard", "Mate", "MA", "Service", []),
        ("Dean", "Roy", "MA", "Civilian", ["Grand Senior"]),
        ("Toler", "Alan", "MA", "Civilian", ["Senior"]),
        ("Innes", "Seth", "MA", "Civilian", ["Veteran", "Senior"]),  # senior+vet → seed allows; UI exclusivity softer for sample
        ("Hitt", "Odie", "MA", "Police", []),
        # Expert
        ("Heinauer", "Anthony", "EX", "Police", []),
        ("Farrell", "Robert", "EX", "Service", []),
        ("Melton", "David", "EX", "Civilian", ["Veteran"]),
        ("Hinkle", "Isaac", "EX", "Civilian", []),
        ("Carter", "Sue", "EX", "Civilian", ["Women"]),
        ("Bennett", "Dennis", "EX", "Civilian", ["Grand Senior", "Veteran"]),
        ("Tanner", "Sheri", "EX", "Civilian", ["Women"]),
        ("Leidy", "Roy", "EX", "Civilian", ["Veteran"]),
        # Sharpshooter
        ("Shoaf", "Larry", "SS", "Civilian", []),
        ("Zaminer", "Scott", "SS", "Police", []),
        ("Goodman", "Mark", "SS", "Civilian", []),
        ("Young", "Timothy", "SS", "Service", []),
        ("Lowery", "Melinda", "SS", "Civilian", ["Women"]),
        ("Isikbay", "Serkis", "SS", "Civilian", []),
        # Marksman
        ("Drehle", "Ed", "MK", "Civilian", ["Grand Senior"]),
        ("Haynes", "Thomas", "MK", "Civilian", ["Veteran"]),
        ("Gschiel", "Thomas", "MK", "Civilian", ["Grand Senior"]),
        ("Brygider", "Michael", "MK", "Police", []),
        ("Newcomer", "Linda", "MK", "Civilian", ["Women", "Grand Senior"]),
        ("Swing", "Scott", "MK", "Civilian", ["Grand Senior"]),
        # Extra depth for density
        ("Rivera", "Alex", "HM", "Civilian", ["Veteran"]),
        ("Chen", "Blake", "MA", "Police", []),
        ("Morgan", "Casey", "EX", "Civilian", ["Senior"]),
        ("Whitfield", "Logan", "EX", "Service", []),
    ]

    # Soften exclusive specials for seed: Innes keep Senior only for cleaner awards
    people[10] = ("Innes", "Seth", "MA", "Civilian", ["Senior"])

    shooters: List[Dict[str, Any]] = []
    for i, (last, first, rating, division, cats) in enumerate(people, start=1):
        shooters.append(
            {
                "name": f"{last}, {first}",
                "competitor_number": 100 + i,  # 101…
                "nra_number": f"{SEED_NRA_PREFIX}{i:05d}",
                "cmp_number": f"CMP-S{i:03d}",
                "rating": rating,
                "division": division,
                "special_categories": cats,
            }
        )
    return shooters


SHOOTERS = _build_shooters()

MATCH_NAMES = [
    f"{SAMPLE_PREFIX}River City June Outdoor",
    f"{SAMPLE_PREFIX}Two-Gun 1800 Challenge",
    f"{SAMPLE_PREFIX}July 2700 Classic",
    f"{SAMPLE_PREFIX}Service & Revolver 1800",
    f"{SAMPLE_PREFIX}Weeknight NMC Series",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def login() -> str:
    r = requests.post(
        f"{BASE_URL}/auth/token",
        data={"username": EMAIL, "password": PASSWORD},
        timeout=60,
    )
    r.raise_for_status()
    print(f"✓ Logged in as {EMAIL} @ {BASE_URL}")
    return r.json()["access_token"]


def api(session: requests.Session, method: str, path: str, **kwargs) -> Any:
    url = f"{BASE_URL}{path}"
    r = session.request(method, url, timeout=120, **kwargs)
    if r.status_code >= 400:
        raise RuntimeError(f"{method} {path} → {r.status_code}: {r.text[:600]}")
    if r.status_code == 204 or not r.content:
        return None
    return r.json()


def clean_sample_data(session: requests.Session) -> None:
    """Remove only previous sample-tagged matches, league, and SEED* shooters."""
    print("… Cleaning previous [SAMPLE] data")

    matches = api(session, "GET", "/matches") or []
    for m in matches:
        name = m.get("name") or ""
        if name.startswith(SAMPLE_PREFIX) or name in MATCH_NAMES:
            mid = m["id"]
            api(session, "DELETE", f"/matches/{mid}")
            print(f"  - deleted match: {name}")

    leagues = api(session, "GET", "/leagues") or []
    for L in leagues:
        name = L.get("name") or ""
        if name.startswith(SAMPLE_PREFIX) or name == LEAGUE_NAME:
            api(session, "DELETE", f"/leagues/{L['id']}")
            print(f"  - deleted league: {name}")

    shooters = api(session, "GET", "/shooters") or []
    for sh in shooters:
        nra = str(sh.get("nra_number") or "")
        name = sh.get("name") or ""
        is_seed = nra.startswith(SEED_NRA_PREFIX) or name.startswith(SAMPLE_PREFIX)
        # Also clean known legacy seed NRAs that caused Alex Rivera / Rivera, Alex dupes
        legacy_nra = nra in {f"14280{i:03d}{i}" for i in range(1, 13)} or nra.startswith(
            "14280"
        )
        # Be conservative with 14280* — only if name looks like our old seed set
        old_seed_names = {
            "Alex Rivera",
            "Blake Chen",
            "Casey Morgan",
            "Dana Okonkwo",
            "Ellis Park",
            "Frankie Santos",
            "Gray Nakamura",
            "Harper Quinn",
            "Indigo Brooks",
            "Jordan Lee",
            "Kai Mendoza",
            "Logan Whitfield",
            "Rivera, Alex",
            "Chen, Blake",
            "Morgan, Casey",
            "Okonkwo, Dana",
            "Park, Ellis",
            "Santos, Frankie",
            "Nakamura, Gray",
            "Quinn, Harper",
            "Brooks, Indigo",
            "Lee, Jordan",
            "Mendoza, Kai",
            "Whitfield, Logan",
        }
        if is_seed or (nra.startswith("14280") and name in old_seed_names):
            try:
                api(session, "DELETE", f"/shooters/{sh['id']}?force=true")
                print(f"  - deleted shooter: {name} ({nra})")
            except Exception as e:
                print(f"  ! could not delete {name}: {e}")

    print("✓ Clean complete")


def stage_list(match_type: str) -> List[str]:
    if match_type == "NMC":
        return ["SF", "TF", "RF"]
    if match_type == "600":
        return ["SF1", "SF2", "TF1", "TF2", "RF1", "RF2"]
    if match_type == "900":
        return ["SF1", "SF2", "SFNMC", "TFNMC", "RFNMC", "TF1", "TF2", "RF1", "RF2"]
    if match_type == "Presidents":
        return ["SF1", "SF2", "TF", "RF"]
    raise ValueError(match_type)


def make_stages(
    match_type: str,
    skill: float,
    *,
    not_shot: bool = False,
    partial: bool = False,
) -> List[Dict[str, Any]]:
    names = stage_list(match_type)
    stages = []
    for i, name in enumerate(names):
        if not_shot:
            stages.append({"name": name, "score": None, "x_count": None})
            continue
        if partial and i >= len(names) - 2 and RNG.random() < 0.6:
            stages.append({"name": name, "score": None, "x_count": None})
            continue
        base = 72 + int(skill * 26)
        score = max(0, min(100, base + RNG.randint(-5, 5)))
        if RNG.random() < 0.02:
            score = max(0, score - 30)
        x_count = 0
        if score >= 96:
            x_count = RNG.randint(4, 9)
        elif score >= 92:
            x_count = RNG.randint(2, 5)
        elif score >= 88:
            x_count = RNG.randint(0, 3)
        elif score >= 84:
            x_count = RNG.randint(0, 1)
        stages.append({"name": name, "score": score, "x_count": x_count})
    return stages


def skill_for_rating(rating: Optional[str]) -> float:
    return {
        "HM": 0.94,
        "MA": 0.84,
        "EX": 0.72,
        "SS": 0.58,
        "MK": 0.44,
        "UNC": 0.50,
    }.get(rating or "UNC", 0.5)


def match_meta(name: str, date: datetime, location: str, **extra: Any) -> Dict[str, Any]:
    body = {
        "name": name,
        "date": date.isoformat(),
        "location": location,
        "is_nra_registered": True,
        "tournament_name": f"NRA REGISTERED MATCH -- {date.strftime('%B %d, %Y')}",
    }
    body.update(extra)
    return body


def post_score(
    session: requests.Session,
    *,
    shooter_id: str,
    match_id: str,
    caliber: str,
    instance: str,
    stages: List[Dict[str, Any]],
) -> None:
    api(
        session,
        "POST",
        "/scores",
        json={
            "shooter_id": shooter_id,
            "match_id": match_id,
            "caliber": caliber,
            "match_type_instance": instance,
            "stages": stages,
        },
    )


def main() -> int:
    token = login()
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"

    if CLEAN:
        clean_sample_data(s)
    else:
        print("… CLEAN=0 — leaving existing data (may skip duplicates)")

    # --- Shooters ---
    shooter_ids: Dict[str, str] = {}
    for payload in SHOOTERS:
        body = {
            "name": payload["name"],
            "nra_number": payload["nra_number"],
            "cmp_number": payload.get("cmp_number"),
            "rating": payload.get("rating"),
            "competitor_number": payload.get("competitor_number"),
            "division": payload.get("division") or "Civilian",
            "special_categories": list(payload.get("special_categories") or []),
        }
        created = api(s, "POST", "/shooters", json=body)
        shooter_ids[payload["name"]] = created["id"]
    print(f"✓ Created {len(shooter_ids)} sample shooters (SEED* NRA, #101+)")

    names = [p["name"] for p in SHOOTERS]
    league_members = names[:28]  # most of roster on league
    guests = names[28:]  # last few match-day only

    # --- League ---
    league = api(
        s,
        "POST",
        "/leagues",
        json={
            "name": LEAGUE_NAME,
            "season": "2026 Outdoor",
            "description": "Sample league — safe to delete (name starts with [SAMPLE])",
        },
    )
    league_id = league["id"]
    # batch roster adds
    api(
        s,
        "POST",
        f"/leagues/{league_id}/roster",
        json={"shooter_ids": [shooter_ids[n] for n in league_members]},
    )
    print(f"✓ League: {LEAGUE_NAME} ({len(league_members)} members, {len(guests)} guests)")

    # =====================================================================
    # Match 1 — multi-type outdoor (bulletin: SF / TF / RF / NMC / 900)
    # =====================================================================
    m1 = api(
        s,
        "POST",
        "/matches",
        json=match_meta(
            MATCH_NAMES[0],
            _now() - timedelta(days=18),
            "River City Rifle & Pistol Club, Marengo OH",
            match_types=[
                {"type": "NMC", "instance_name": "22 EIC", "calibers": [".22"]},
                {"type": "NMC", "instance_name": "CF NMC", "calibers": ["CF"]},
                {
                    "type": "900",
                    "instance_name": "900 Open",
                    "calibers": [".22", "CF", ".45"],
                },
                {
                    "type": "Presidents",
                    "instance_name": "Presidents",
                    "calibers": ["Service Pistol"],
                },
            ],
            aggregate_type="None",
            league_id=league_id,
        ),
    )
    m1_id = m1["id"]
    if guests:
        api(
            s,
            "POST",
            f"/matches/{m1_id}/roster",
            json={"shooter_ids": [shooter_ids[n] for n in guests]},
        )

    score_count = 0
    for idx, name in enumerate(names):
        sid = shooter_ids[name]
        rating = next(p["rating"] for p in SHOOTERS if p["name"] == name)
        skill = skill_for_rating(rating)
        # .22 NMC — all but one DNS
        not_shot = idx == len(names) - 1
        post_score(
            s,
            shooter_id=sid,
            match_id=m1_id,
            caliber=".22",
            instance="22 EIC",
            stages=make_stages("NMC", skill, not_shot=not_shot, partial=(idx % 11 == 0)),
        )
        score_count += 1
        # CF NMC — most
        if idx % 5 != 4:
            post_score(
                s,
                shooter_id=sid,
                match_id=m1_id,
                caliber="CF",
                instance="CF NMC",
                stages=make_stages("NMC", skill * 0.97),
            )
            score_count += 1
        # 900 multi-caliber — top 2/3 of field
        if idx < 24:
            for cal in [".22", "CF", ".45"][: 1 + (idx % 3)]:
                post_score(
                    s,
                    shooter_id=sid,
                    match_id=m1_id,
                    caliber=cal,
                    instance="900 Open",
                    stages=make_stages("900", skill - (0.04 if cal != ".22" else 0)),
                )
                score_count += 1
        if idx % 2 == 0:
            post_score(
                s,
                shooter_id=sid,
                match_id=m1_id,
                caliber="Service Pistol",
                instance="Presidents",
                stages=make_stages("Presidents", skill * 0.9),
            )
            score_count += 1
    print(f"✓ {MATCH_NAMES[0]}  ({score_count} score rows)")

    # =====================================================================
    # Match 2 — 1800 (2×900)
    # =====================================================================
    m2 = api(
        s,
        "POST",
        "/matches",
        json=match_meta(
            MATCH_NAMES[1],
            _now() - timedelta(days=10),
            "Prairie View Range",
            match_types=[
                {
                    "type": "900",
                    "instance_name": "900 Day 1",
                    "calibers": [".22", "CF"],
                },
                {
                    "type": "900",
                    "instance_name": "900 Day 2",
                    "calibers": [".22", "CF"],
                },
            ],
            aggregate_type="1800 (2x900)",
            league_id=league_id,
        ),
    )
    m2_id = m2["id"]
    c2 = 0
    for name in league_members:
        sid = shooter_ids[name]
        skill = skill_for_rating(
            next(p["rating"] for p in SHOOTERS if p["name"] == name)
        )
        for instance in ("900 Day 1", "900 Day 2"):
            for cal in (".22", "CF"):
                ns = name.endswith("Casey") and instance == "900 Day 2" and cal == "CF"
                post_score(
                    s,
                    shooter_id=sid,
                    match_id=m2_id,
                    caliber=cal,
                    instance=instance,
                    stages=make_stages(
                        "900",
                        skill + (0 if "Day 1" in instance else -0.03),
                        not_shot=ns,
                    ),
                )
                c2 += 1
    print(f"✓ {MATCH_NAMES[1]}  ({c2} score rows)")

    # =====================================================================
    # Match 3 — 2700 (3×900) grand aggregate material
    # =====================================================================
    m3 = api(
        s,
        "POST",
        "/matches",
        json=match_meta(
            MATCH_NAMES[2],
            _now() - timedelta(days=2),
            "State Fairgrounds Range / Cardinal Center",
            match_types=[
                {
                    "type": "900",
                    "instance_name": "900_A",
                    "calibers": [".22", "CF", ".45"],
                },
                {
                    "type": "900",
                    "instance_name": "900_B",
                    "calibers": [".22", "CF", ".45"],
                },
                {
                    "type": "900",
                    "instance_name": "900_C",
                    "calibers": [".22", "CF", ".45"],
                },
            ],
            aggregate_type="2700 (3x900)",
            league_id=league_id,
        ),
    )
    m3_id = m3["id"]
    c3 = 0
    full = league_members[:20]
    partial = league_members[20:28]
    for name in full:
        sid = shooter_ids[name]
        skill = skill_for_rating(
            next(p["rating"] for p in SHOOTERS if p["name"] == name)
        )
        for instance in ("900_A", "900_B", "900_C"):
            for cal in (".22", "CF", ".45"):
                post_score(
                    s,
                    shooter_id=sid,
                    match_id=m3_id,
                    caliber=cal,
                    instance=instance,
                    stages=make_stages("900", skill - (0.02 if cal != ".22" else 0)),
                )
                c3 += 1
    for name in partial:
        sid = shooter_ids[name]
        skill = skill_for_rating(
            next(p["rating"] for p in SHOOTERS if p["name"] == name)
        )
        for instance in ("900_A", "900_B"):
            post_score(
                s,
                shooter_id=sid,
                match_id=m3_id,
                caliber=".22",
                instance=instance,
                stages=make_stages("900", skill),
            )
            c3 += 1
    print(f"✓ {MATCH_NAMES[2]}  ({c3} score rows)")

    # =====================================================================
    # Match 4 — 1800 (3×600) service
    # =====================================================================
    m4 = api(
        s,
        "POST",
        "/matches",
        json=match_meta(
            MATCH_NAMES[3],
            _now() - timedelta(days=5),
            "Municipal Police Range",
            match_types=[
                {
                    "type": "600",
                    "instance_name": f"600_{i}",
                    "calibers": ["Service Pistol", "Service Revolver", "DR"],
                }
                for i in (1, 2, 3)
            ],
            aggregate_type="1800 (3x600)",
        ),
    )
    m4_id = m4["id"]
    service_names = names[:20]
    api(
        s,
        "POST",
        f"/matches/{m4_id}/roster",
        json={"shooter_ids": [shooter_ids[n] for n in service_names]},
    )
    c4 = 0
    for name in service_names:
        sid = shooter_ids[name]
        skill = skill_for_rating(
            next(p["rating"] for p in SHOOTERS if p["name"] == name)
        )
        for instance in ("600_1", "600_2", "600_3"):
            post_score(
                s,
                shooter_id=sid,
                match_id=m4_id,
                caliber="Service Pistol",
                instance=instance,
                stages=make_stages("600", skill * 0.88),
            )
            c4 += 1
            if names.index(name) < 10:
                post_score(
                    s,
                    shooter_id=sid,
                    match_id=m4_id,
                    caliber="Service Revolver",
                    instance=instance,
                    stages=make_stages("600", skill * 0.8),
                )
                c4 += 1
            if names.index(name) < 5:
                post_score(
                    s,
                    shooter_id=sid,
                    match_id=m4_id,
                    caliber="DR",
                    instance=instance,
                    stages=make_stages("600", skill * 0.75),
                )
                c4 += 1
    print(f"✓ {MATCH_NAMES[3]}  ({c4} score rows)")

    # =====================================================================
    # Match 5 — simple weeknight NMC series (dense single-type board)
    # =====================================================================
    m5 = api(
        s,
        "POST",
        "/matches",
        json=match_meta(
            MATCH_NAMES[4],
            _now(),
            "River City Indoor",
            match_types=[
                {
                    "type": "NMC",
                    "instance_name": "NMC Week 1",
                    "calibers": [".22", "CF", ".45"],
                },
                {
                    "type": "NMC",
                    "instance_name": "NMC Week 2",
                    "calibers": [".22", "CF", ".45"],
                },
            ],
            aggregate_type="None",
            league_id=league_id,
        ),
    )
    m5_id = m5["id"]
    c5 = 0
    for name in league_members:
        sid = shooter_ids[name]
        skill = skill_for_rating(
            next(p["rating"] for p in SHOOTERS if p["name"] == name)
        )
        for instance in ("NMC Week 1", "NMC Week 2"):
            for cal in (".22", "CF", ".45"):
                if RNG.random() < 0.08:
                    continue  # some missing cards
                post_score(
                    s,
                    shooter_id=sid,
                    match_id=m5_id,
                    caliber=cal,
                    instance=instance,
                    stages=make_stages("NMC", skill + RNG.uniform(-0.05, 0.02)),
                )
                c5 += 1
    print(f"✓ {MATCH_NAMES[4]}  ({c5} score rows)")

    total_scores = score_count + c2 + c3 + c4 + c5
    print(
        f"""
╔══════════════════════════════════════════════════════════════════╗
║              SAMPLE DATA LOADED (clean reload)                   ║
╠══════════════════════════════════════════════════════════════════╣
║  Login:    admin@example.com / admin123                          ║
║  Shooters: {len(SHOOTERS):3d}  (NRA SEED00001…, competitor #101+)              ║
║  League:   {LEAGUE_NAME[:42]:42s} ║
║  Matches:  5  (all names start with [SAMPLE])                    ║
║  Scores:   ~{total_scores} rows                                               ║
╠══════════════════════════════════════════════════════════════════╣
║  Try: Matches → [SAMPLE] July 2700 Classic → Results Bulletin    ║
║       Slow Fire / NMC / Grand Aggregate → Export Excel / Print   ║
║                                                                  ║
║  Re-run anytime: CLEAN=1 (default) wipes only [SAMPLE]/SEED*   ║
╚══════════════════════════════════════════════════════════════════╝
"""
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
