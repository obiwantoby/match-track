"""
End-to-end API lifecycle smoke test against a real MongoDB.

Requires:
  MONGO_URL (default mongodb://localhost:27017)
  A running MongoDB instance

Uses an isolated DB name so it will not touch production data.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

# Isolate DB before importing the app
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ["DB_NAME"] = f"match_track_test_{uuid.uuid4().hex[:8]}"
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("ORIGINS", "http://localhost:3000")

from backend.server import app  # noqa: E402
from backend.database import client  # noqa: E402


@pytest.fixture(scope="module")
def api():
    with TestClient(app) as client_http:
        yield client_http
    # Teardown isolated DB (sync client — motor needs a running loop)
    try:
        from pymongo import MongoClient

        sync = MongoClient(os.environ["MONGO_URL"])
        sync.drop_database(os.environ["DB_NAME"])
        sync.close()
    except Exception:
        pass


@pytest.fixture(scope="module")
def auth_headers(api: TestClient):
    # Startup creates admin@example.com / admin123 when DB is empty
    resp = api.post(
        "/api/auth/token",
        data={"username": "admin@example.com", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_auth_and_me(api: TestClient, auth_headers):
    me = api.get("/api/auth/me", headers=auth_headers)
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "admin@example.com"
    assert body["role"] == "admin"


def test_match_types_and_calibers_available(api: TestClient, auth_headers):
    resp = api.get("/api/match-types", headers=auth_headers)
    assert resp.status_code == 200
    types = resp.json()
    # Endpoint shape may be dict or list depending on implementation
    if isinstance(types, dict):
        keys = set(types.keys())
    else:
        keys = {t if isinstance(t, str) else t.get("type") or t.get("name") for t in types}
    for expected in ("NMC", "600", "900", "Presidents"):
        assert any(expected in str(k) for k in keys), f"missing {expected} in {keys}"


def test_full_match_score_report_lifecycle(api: TestClient, auth_headers):
    # 1) Create shooter
    shooter_resp = api.post(
        "/api/shooters",
        headers=auth_headers,
        json={
            "name": "Lifecycle Shooter",
            "nra_number": "99990001",
            "cmp_number": "CMP-LIFE",
            "rating": "MA",
        },
    )
    assert shooter_resp.status_code == 200, shooter_resp.text
    shooter = shooter_resp.json()
    shooter_id = shooter["id"]
    assert shooter["rating"] == "MA"

    # 2) Create match with named sub-match and multi-type
    match_resp = api.post(
        "/api/matches",
        headers=auth_headers,
        json={
            "name": "Lifecycle Outdoor",
            "date": datetime(2026, 7, 4).isoformat(),
            "location": "Test Range",
            "match_types": [
                {
                    "type": "NMC",
                    "instance_name": "22 EIC",
                    "calibers": [".22"],
                },
                {
                    "type": "900",
                    "instance_name": "900_CF",
                    "calibers": ["CF", "Service Pistol"],
                },
                {
                    "type": "600",
                    "instance_name": "600_1",
                    "calibers": [".45"],
                },
                {
                    "type": "Presidents",
                    "instance_name": "Pres_1",
                    "calibers": ["DR"],
                },
            ],
            "aggregate_type": "None",
        },
    )
    assert match_resp.status_code == 200, match_resp.text
    match = match_resp.json()
    match_id = match["id"]
    assert match["match_types"][0]["instance_name"] == "22 EIC"

    # 3) Add shooter to roster
    roster_add = api.post(
        f"/api/matches/{match_id}/roster",
        headers=auth_headers,
        json={"shooter_ids": [shooter_id]},
    )
    assert roster_add.status_code == 200, roster_add.text

    # 4) Enter NMC score
    nmc_stages = [
        {"name": "SF", "score": 98, "x_count": 6},
        {"name": "TF", "score": 97, "x_count": 4},
        {"name": "RF", "score": 95, "x_count": 3},
    ]
    score_resp = api.post(
        "/api/scores",
        headers=auth_headers,
        json={
            "shooter_id": shooter_id,
            "match_id": match_id,
            "caliber": ".22",
            "match_type_instance": "22 EIC",
            "stages": nmc_stages,
        },
    )
    assert score_resp.status_code == 200, score_resp.text
    score = score_resp.json()
    assert score["total_score"] == 290
    assert score["total_x_count"] == 13
    assert score["not_shot"] is False
    score_id = score["id"]

    # 5) Enter 900 with mixed stages (including mid-NMC strings)
    nine_stages = [
        {"name": "SF1", "score": 90, "x_count": 2},
        {"name": "SF2", "score": 91, "x_count": 1},
        {"name": "SFNMC", "score": 92, "x_count": 3},
        {"name": "TFNMC", "score": 88, "x_count": 0},
        {"name": "RFNMC", "score": 89, "x_count": 1},
        {"name": "TF1", "score": 90, "x_count": 2},
        {"name": "TF2", "score": 85, "x_count": 0},
        {"name": "RF1", "score": 86, "x_count": 1},
        {"name": "RF2", "score": 87, "x_count": 0},
    ]
    nine_resp = api.post(
        "/api/scores",
        headers=auth_headers,
        json={
            "shooter_id": shooter_id,
            "match_id": match_id,
            "caliber": "CF",
            "match_type_instance": "900_CF",
            "stages": nine_stages,
        },
    )
    assert nine_resp.status_code == 200, nine_resp.text
    nine = nine_resp.json()
    assert nine["total_score"] == sum(s["score"] for s in nine_stages)
    assert nine["total_score"] == 798

    # 6) Not-shot path (all null stages)
    not_shot_resp = api.post(
        "/api/scores",
        headers=auth_headers,
        json={
            "shooter_id": shooter_id,
            "match_id": match_id,
            "caliber": "Service Pistol",
            "match_type_instance": "900_CF",
            "stages": [
                {"name": n, "score": None, "x_count": None}
                for n in [
                    "SF1",
                    "SF2",
                    "SFNMC",
                    "TFNMC",
                    "RFNMC",
                    "TF1",
                    "TF2",
                    "RF1",
                    "RF2",
                ]
            ],
        },
    )
    assert not_shot_resp.status_code == 200, not_shot_resp.text
    ns = not_shot_resp.json()
    assert ns["total_score"] is None
    assert ns["not_shot"] is True

    # 7) Match report
    report_resp = api.get(f"/api/match-report/{match_id}", headers=auth_headers)
    assert report_resp.status_code == 200, report_resp.text
    report = report_resp.json()
    assert shooter_id in report["shooters"]
    shooter_data = report["shooters"][shooter_id]
    assert shooter_data["shooter"]["name"] == "Lifecycle Shooter"
    # At least one scored entry present
    assert len(shooter_data["scores"]) >= 2

    # 8) Excel export
    excel_resp = api.get(
        f"/api/match-report/{match_id}/excel", headers=auth_headers
    )
    assert excel_resp.status_code == 200, excel_resp.text
    assert (
        "spreadsheet"
        in excel_resp.headers.get("content-type", "").lower()
        or excel_resp.headers.get("content-type", "").endswith(
            "openxmlformats-officedocument.spreadsheetml.sheet"
        )
        or excel_resp.content[:2] == b"PK"  # zip/xlsx magic
    )
    assert len(excel_resp.content) > 1000

    # 9) Edit score
    edit_resp = api.put(
        f"/api/scores/{score_id}",
        headers=auth_headers,
        json={
            "shooter_id": shooter_id,
            "match_id": match_id,
            "caliber": ".22",
            "match_type_instance": "22 EIC",
            "stages": [
                {"name": "SF", "score": 99, "x_count": 8},
                {"name": "TF", "score": 97, "x_count": 4},
                {"name": "RF", "score": 95, "x_count": 3},
            ],
        },
    )
    assert edit_resp.status_code == 200, edit_resp.text
    assert edit_resp.json()["total_score"] == 291

    # 10) Edit match (rename sub-match, preserve scores if same instance name)
    edit_match = api.put(
        f"/api/matches/{match_id}",
        headers=auth_headers,
        json={
            "name": "Lifecycle Outdoor (Edited)",
            "date": datetime(2026, 7, 4).isoformat(),
            "location": "Test Range West",
            "match_types": match["match_types"],
            "aggregate_type": "None",
        },
    )
    assert edit_match.status_code == 200, edit_match.text
    assert edit_match.json()["name"] == "Lifecycle Outdoor (Edited)"
    assert edit_match.json()["location"] == "Test Range West"

    # 11) Shooter report + averages
    sh_report = api.get(f"/api/shooter-report/{shooter_id}", headers=auth_headers)
    assert sh_report.status_code == 200, sh_report.text
    avgs = api.get(f"/api/shooter-averages/{shooter_id}", headers=auth_headers)
    assert avgs.status_code == 200, avgs.text


def test_aggregate_1800_2x900(api: TestClient, auth_headers):
    shooter = api.post(
        "/api/shooters",
        headers=auth_headers,
        json={"name": "Agg Shooter", "rating": "EX"},
    ).json()
    match = api.post(
        "/api/matches",
        headers=auth_headers,
        json={
            "name": "Two Gun 1800",
            "date": datetime(2026, 7, 5).isoformat(),
            "location": "Agg Range",
            "match_types": [
                {
                    "type": "900",
                    "instance_name": "900_A",
                    "calibers": [".22"],
                },
                {
                    "type": "900",
                    "instance_name": "900_B",
                    "calibers": [".22"],
                },
            ],
            "aggregate_type": "1800 (2x900)",
        },
    ).json()

    stages_a = [
        {"name": n, "score": 90, "x_count": 1}
        for n in [
            "SF1",
            "SF2",
            "SFNMC",
            "TFNMC",
            "RFNMC",
            "TF1",
            "TF2",
            "RF1",
            "RF2",
        ]
    ]
    stages_b = [
        {"name": n, "score": 95, "x_count": 2}
        for n in [
            "SF1",
            "SF2",
            "SFNMC",
            "TFNMC",
            "RFNMC",
            "TF1",
            "TF2",
            "RF1",
            "RF2",
        ]
    ]

    r1 = api.post(
        "/api/scores",
        headers=auth_headers,
        json={
            "shooter_id": shooter["id"],
            "match_id": match["id"],
            "caliber": ".22",
            "match_type_instance": "900_A",
            "stages": stages_a,
        },
    )
    r2 = api.post(
        "/api/scores",
        headers=auth_headers,
        json={
            "shooter_id": shooter["id"],
            "match_id": match["id"],
            "caliber": ".22",
            "match_type_instance": "900_B",
            "stages": stages_b,
        },
    )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["total_score"] == 810
    assert r2.json()["total_score"] == 855

    report = api.get(
        f"/api/match-report/{match['id']}", headers=auth_headers
    ).json()
    shooter_data = report["shooters"][shooter["id"]]
    aggs = shooter_data.get("aggregates") or {}
    # Key format: 1800_.22
    matching = [v for k, v in aggs.items() if "1800" in k and (".22" in k or "22" in k)]
    assert matching, f"expected 1800 aggregate, got {aggs}"
    assert matching[0]["score"] == 810 + 855


def test_csv_shooter_import(api: TestClient, auth_headers):
    csv_body = (
        "name,nra_number,cmp_number,rating\n"
        "CSV Alpha,1001,C1,HM\n"
        "CSV Beta,1002,,SS\n"
        "Lifecycle Shooter,99990001,DUP,MA\n"  # may skip as duplicate name/nra
    )
    files = {"file": ("shooters.csv", csv_body, "text/csv")}
    resp = api.post(
        "/api/shooters/bulk-csv",
        headers=auth_headers,
        files=files,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["created"] >= 2
    # List shooters includes imports
    listing = api.get("/api/shooters", headers=auth_headers)
    assert listing.status_code == 200
    names = {s["name"] for s in listing.json()}
    assert "CSV Alpha" in names
    assert "CSV Beta" in names


def test_league_seed_roster(api: TestClient, auth_headers):
    s1 = api.post(
        "/api/shooters",
        headers=auth_headers,
        json={"name": "League Member One"},
    ).json()
    s2 = api.post(
        "/api/shooters",
        headers=auth_headers,
        json={"name": "League Member Two"},
    ).json()

    league = api.post(
        "/api/leagues",
        headers=auth_headers,
        json={"name": "Test League", "season": "2026 Outdoor"},
    ).json()

    add = api.post(
        f"/api/leagues/{league['id']}/roster",
        headers=auth_headers,
        json={"shooter_ids": [s1["id"], s2["id"]]},
    )
    assert add.status_code == 200, add.text

    match = api.post(
        "/api/matches",
        headers=auth_headers,
        json={
            "name": "League Seeded Match",
            "date": datetime(2026, 7, 6).isoformat(),
            "location": "Club",
            "match_types": [
                {
                    "type": "NMC",
                    "instance_name": "NMC1",
                    "calibers": [".22"],
                }
            ],
            "aggregate_type": "None",
            "league_id": league["id"],
        },
    )
    assert match.status_code == 200, match.text
    roster = api.get(
        f"/api/matches/{match.json()['id']}/roster", headers=auth_headers
    )
    assert roster.status_code == 200
    body = roster.json()
    members = body.get("members") or body.get("roster") or []
    member_ids = set()
    for m in members:
        # MatchRosterMember: { shooter: { id, name, ... }, score_count, ... }
        if isinstance(m, dict) and "shooter" in m and isinstance(m["shooter"], dict):
            member_ids.add(m["shooter"]["id"])
        elif isinstance(m, dict) and "id" in m:
            member_ids.add(m["id"])
    if not member_ids:
        mdoc = api.get(
            f"/api/matches/{match.json()['id']}", headers=auth_headers
        ).json()
        member_ids = set(mdoc.get("roster_shooter_ids") or [])
    assert s1["id"] in member_ids
    assert s2["id"] in member_ids
