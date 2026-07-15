# Prep notes for next feature work

Last verified: 2026-07-14 (autonomous soundness pass).

## What is green today

| Layer | Status |
|-------|--------|
| Domain stages (NMC / 600 / 900 / Presidents) | Locked by `tests/unit/test_core_domain.py` |
| Multigun aggs 1800 (2×900), 1800 (3×600), 2700 (3×900) | Unit + API lifecycle |
| Null / not-shot totals | API lifecycle |
| Named sub-matches (`instance_name`, e.g. `22 EIC`) | API lifecycle |
| CSV shooter import, leagues, match roster seed | API lifecycle |
| Match report + Excel export | API lifecycle |
| Auth (admin seed + JWT login) | Fixed 2026-07-14 |

### How to re-run verification

```bash
# Offline (no Mongo)
source .venv/bin/activate
PYTHONPATH=. pytest

# Full API lifecycle (Mongo required)
brew services start mongodb/brew/mongodb-community@7.0   # if local
MONGO_URL=mongodb://localhost:27017 \
  SECRET_KEY=dev-secret-at-least-32-chars \
  PYTHONPATH=. \
  pytest tests/unit tests/integration/test_api_lifecycle.py -v
```

Create venv once:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

## Bugs fixed in this soundness pass

1. **Auth completely broken on modern bcrypt**  
   `passlib` + `bcrypt` 5.x fails (`__about__` missing / false “password > 72 bytes”).  
   Default admin never created → login impossible.  
   **Fix:** hash/verify with the `bcrypt` package directly in `backend/auth.py`.  
   `passlib` removed from `backend/requirements.txt`.

2. **Double startup admin hook**  
   `create_first_admin` was registered as its own `@app.on_event("startup")` *and* called from `startup_event`. Consolidated to a single startup path.

3. **docker-compose hardcoded LAN IP**  
   Frontend build URL and CORS origins pointed at `192.168.50.167`. Defaults are now `localhost` with a comment for LAN overrides. `SECRET_KEY` env placeholder added.

4. **README 900 stage list was wrong**  
   Documented six stages + computed SFNMC; code uses nine entered stages including SFNMC/TFNMC/RFNMC. README aligned with code + range-officer notes.

## Known tech debt (do not block scoring; clean when touching area)

| Item | Notes |
|------|--------|
| Pydantic `.dict()` | Deprecated; prefer `model_dump()` / `model_dump(mode="json")` before Pydantic v3 |
| `datetime.utcnow()` | Deprecated; use `datetime.now(timezone.utc)` |
| FastAPI `on_event` | Prefer lifespan context managers |
| Score lookup keys in UI | `MatchReport.js` tries many legacy key formats for calibers — normalize when rewriting reports |
| Summary aggregate column | UI can over-sum cells for 1800; backend `calculate_aggregates` is authoritative |
| Root `requirements.txt` | Looks like a generic platform dump, not this app — prefer `backend/requirements.txt` |
| Legacy integration scripts | `tests/integration/*_test.py` hit remote preview URLs; not wired to pytest |

## Recommended next feature order (from product notes)

**Done (2026-07-14):** NRA Results Bulletin engine + web view + Excel + print/PDF
(`backend/bulletin.py`, Match → **Results Bulletin** tab). See
`docs/NRA_BULLETIN_SPEC.md` and `docs/sample-reports/`.

Still open:

1. **CSV columns** for competitor # / division / special categories  
2. **Metallic / .22-only** separate classifications  
3. **Last-target tie-break** (highest last stage) when score+X tied  
4. **Score entry typeahead** (type last name → dropdown)  
5. **Print labels / optional scantron layout**  

## Architecture anchors (for future PRs)

- Domain truth: `backend/core.py` (`BasicMatchType`, stages, aggregates, calibers, ratings)  
- API + Excel: `backend/server.py`  
- Auth: `backend/auth.py`  
- UI: `frontend/src/App.js` (match create), `ScoreEntry.js`, `MatchReport.js`, `EditMatch.js`, `ShootersList.js`  
- Users ≠ shooters ≠ league roster ≠ match roster (keep separate)

## Environment notes from this machine

- Python 3.14.6 + local MongoDB 7 via Homebrew worked for API tests  
- Docker CLI was not available here; compose file still valid for environments that have it  
- Frontend `npm install` may still be needed on first UI work (`yarn` was not on PATH)
