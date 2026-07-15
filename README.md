# Match Track

Web app for running conventional pistol matches: rosters, stage scores, multi-gun aggregates, and **NRA-style Results Bulletins** (place awards, special categories, class × division).

**Stack:** React + FastAPI + MongoDB (Docker Compose).  
**Repo:** [github.com/obiwantoby/match-track](https://github.com/obiwantoby/match-track)

## Table of contents

- [Install (Linux / WSL / Ubuntu)](#install-linux--wsl--ubuntu)
- [Quick start](#quick-start)
- [Features](#features)
- [Match types & scoring](#match-types--scoring)
- [Sample data](#sample-data)
- [Usage overview](#usage-overview)
- [Results Bulletin](#results-bulletin)
- [Development (manual)](#development-manual)
- [API summary](#api-summary)
- [Project structure](#project-structure)
- [Further docs](#further-docs)
- [Default login](#default-login)
- [Troubleshooting](#troubleshooting)

---

## Install (Linux / WSL / Ubuntu)

Yes — use **`run.sh`**. It is written for **stock Ubuntu/Debian**, including **WSL2 with Ubuntu**.

### What it does

1. Installs **Docker Engine + Compose** if missing (via official apt repo)  
2. Detects your LAN IP (or use `--host`)  
3. Writes a local `.env` (SECRET_KEY, API URL for the frontend build)  
4. Runs `docker compose up -d --build`  
5. Optionally loads sample data (`--seed`)  
6. Prints the **URL** and **admin login**

### Requirements

- Ubuntu 22.04+ / Debian (or WSL2 Ubuntu)  
- `sudo` if Docker is not installed yet  
- Internet for first image pulls  
- ~2 GB free disk recommended for images  

**WSL tips**

- Use a real distro (e.g. Ubuntu), not “WSL1 only”  
- Docker can be: Docker Engine inside WSL (what `run.sh` installs), **or** Docker Desktop with WSL integration  
- Open the printed URL from Windows browser (`http://localhost:8080` or the LAN IP)

### Install steps

```bash
git clone https://github.com/obiwantoby/match-track.git
cd match-track
chmod +x run.sh

# Start (install Docker if needed)
./run.sh

# Or start + load sample shooters/matches/bulletins data
./run.sh --seed

# Optional overrides
./run.sh --host 192.168.50.29 --port 8080 --seed
```

Useful options:

| Flag | Meaning |
|------|---------|
| `--seed` | After start, load clean sample dataset |
| `--port N` | Host port (default `8080`) |
| `--host HOST` | Public IP/hostname baked into the frontend API URL |
| `--skip-docker-install` | Fail if Docker missing instead of installing |
| `--no-build` | `compose up` without rebuild |

Environment (optional): `APP_PORT`, `PUBLIC_HOST`, `SECRET_KEY`, `DB_NAME`.

### After install

```text
Open:   http://<your-ip>:8080
Login:  admin@example.com
Pass:   admin123
```

Change the admin password on shared machines.

### Day-2 commands

```bash
cd match-track
docker compose ps
docker compose logs -f app
docker compose down          # stop (data volume kept)
docker compose up -d --build # start / rebuild
```

For reverse proxy / Caddy / production notes, see **[DEPLOY.md](DEPLOY.md)**.

---

## Quick start

Same as install if you already have Docker:

```bash
git clone https://github.com/obiwantoby/match-track.git
cd match-track
chmod +x run.sh && ./run.sh --seed
```

Or:

```bash
docker compose up -d --build
```

Compose uses:

- **MongoDB 7.0** (pinned — Mongo 8.x has crashed on small LXCs)  
- App on host port **8080** (nginx + API)  
- Mongo bound to **127.0.0.1:27017** only  

Frontend API URL is set at **image build** time via `FRONTEND_ENV` / `.env` (handled by `run.sh`).

---

## Features

- **Staff users** — Admin / Reporter (JWT auth; passwords via **bcrypt**)  
- **Shooters** — Global directory (no login): name, NRA/CMP, class, **competitor #**, **division**, **special categories**  
- **Leagues** — Season rosters that grow over time  
- **Match roster** — Per-day snapshot (league seed + guests)  
- **Match types** — NMC, 600, 900, Presidents; multi-caliber instances; named sub-matches (e.g. `22 EIC`)  
- **Aggregates** — 1800 (2×900 or 3×600), 2700 (3×900)  
- **Score entry / edit** — Stage scores, X counts, not-shot / null handling  
- **Reports**
  - Match summary + detailed stages  
  - Excel match workbook (summary + per-shooter sheets)  
  - **Results Bulletin** (NRA-style): place awards, special categories, class × civilian / police-service  
  - Bulletin Excel + print-to-PDF (print CSS)  
- **CSV import** — Users and shooters (optional specials/division columns)  
- **Sample seed** — Clean reloadable demo data (`[SAMPLE]` / `SEED*`)  

---

## Match types & scoring

| Type | Stages | Max |
|------|--------|-----|
| **NMC** | SF, TF, RF | 300 |
| **600** | SF1–2, TF1–2, RF1–2 | 600 |
| **900** | SF1, SF2, **SFNMC, TFNMC, RFNMC**, TF1, TF2, RF1, RF2 | 900 |
| **Presidents** | SF1, SF2, TF, RF | 400 |

**900 subtotals** (NMC mid-block is separate):

- **SF** = SF1 + SF2  
- **NMC** = SFNMC + TFNMC + RFNMC  
- **TF** = TF1 + TF2  
- **RF** = RF1 + RF2  

**Multi-gun aggregates:**

- `1800 (2x900)` · `1800 (3x600)` · `2700 (3x900)`

**Calibers:** `.22`, `CF`, `.45`, `Service Pistol`, `Service Revolver`, `DR`

---

## Sample data

Safe demo load (does **not** wipe real shooters unless they use `SEED*` NRA or old seed names):

```bash
# Via run.sh
./run.sh --seed

# Or into a running stack
docker compose cp scripts/seed_sample_data.py app:/tmp/seed_sample_data.py
docker compose exec -T \
  -e BASE_URL=http://127.0.0.1:8001/api \
  -e CLEAN=1 \
  app python3 /tmp/seed_sample_data.py
```

- **`CLEAN=1` (default):** deletes prior `[SAMPLE]` matches/league and `SEED*` shooters, then reloads  
- **~36 shooters** with class, division, special categories, competitor #  
- **5 matches**, hundreds of scores  
- Open a `[SAMPLE]` match → **Results Bulletin**  

Script: `scripts/seed_sample_data.py`

---

## Usage overview

| Layer | Purpose |
|-------|---------|
| **Users** | Staff logins (admin / reporter) |
| **Shooters** | Competitors (no login) |
| **Leagues** | Evolving club roster |
| **Match roster** | Who shoots *that day* |

**Shooter fields for awards:** competitor #, class (HM/MA/EX/SS/MK), division (Civilian / Police / Service), special categories (**Grand Senior**, **Senior**, **Women**, **Veteran**). Women may combine with one other special.

**Typical day:** League roster → create match (optional league seed) → roster guests → enter scores → Match report / Results Bulletin → Excel or Print/PDF.

---

## Results Bulletin

On a match page → **Results Bulletin**:

1. Pick event (Slow Fire, Timed, Rapid, **NMC** separate from SF/TF/RF, full total, caliber agg, grand agg)  
2. View web bulletin (place awards, specials, class boards)  
3. **Export Excel** or **Print / PDF** (browser “Save as PDF”)  

Rules: [`docs/NRA_BULLETIN_SPEC.md`](docs/NRA_BULLETIN_SPEC.md)

---

## Development (manual)

For local work without `run.sh`:

**Prerequisites:** Node 20+, Python 3.11+, MongoDB 7, Yarn or npm  

```bash
# Backend
cd backend
pip install -r requirements.txt
export MONGO_URL=mongodb://localhost:27017
export DB_NAME=shooting_matches_db
export SECRET_KEY=dev-secret-at-least-32-chars
uvicorn backend.server:app --reload --host 0.0.0.0 --port 8001

# Frontend (other terminal)
cd frontend
cp .env.example .env   # REACT_APP_BACKEND_URL=http://localhost:8001
yarn install && yarn start
```

**Tests (offline unit + optional API):**

```bash
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
PYTHONPATH=. pytest tests/unit -q
# API lifecycle needs Mongo:
MONGO_URL=mongodb://localhost:27017 SECRET_KEY=dev-secret-at-least-32-chars \
  PYTHONPATH=. pytest tests/unit tests/integration/test_api_lifecycle.py -q
```

Or: `./scripts/run-tests.sh` / `./scripts/run-tests.sh all`

---

## API summary

Base path: `/api`

| Area | Examples |
|------|----------|
| Auth | `POST /auth/token`, `GET /auth/me`, change-password |
| Shooters | CRUD, `POST /shooters/bulk-csv` |
| Leagues / rosters | `/leagues…`, `/matches/{id}/roster…` |
| Matches / scores | CRUD, match-types, match-config |
| Reports | `/match-report/{id}`, `/match-report/{id}/excel` |
| Bulletins | `/match-report/{id}/bulletin`, `/bulletin/events`, `/bulletin/excel` |
| Admin | users, bulk users CSV, `POST /reset-database` |

---

## Project structure

```
match-track/
├── run.sh                 # Linux / WSL / Ubuntu one-shot install + start
├── docker-compose.yml     # app + mongo:7.0
├── Dockerfile
├── DEPLOY.md              # Production / Caddy / seed ops
├── backend/
│   ├── server.py          # FastAPI routes + Excel
│   ├── core.py            # Models, stages, aggregates
│   ├── bulletin.py        # NRA bulletin standings engine
│   ├── excel_style.py     # Shared Excel formatting
│   ├── auth.py            # JWT + bcrypt
│   └── database.py
├── frontend/
│   ├── .env.example       # REACT_APP_BACKEND_URL=…
│   └── src/components/
│   ├── MatchReport.js / MatchBulletin.js / MatchRoster.js
│   ├── ScoreEntry.js / EditScore.js / EditMatch.js
│   ├── ShootersList.js / ShooterDetail.js / LeagueList.js
│   └── UserManagement.js
├── scripts/
│   ├── seed_sample_data.py
│   └── run-tests.sh
├── tests/unit/            # Domain + bulletin tests (no Mongo)
└── docs/
    ├── NRA_BULLETIN_SPEC.md
    └── PREP_NEXT.md
```

---

## Further docs

| Doc | Contents |
|-----|----------|
| [DEPLOY.md](DEPLOY.md) | Deploy, Caddy, seed on a server |
| [docs/NRA_BULLETIN_SPEC.md](docs/NRA_BULLETIN_SPEC.md) | Bulletin format & ranking rules |
| [docs/PREP_NEXT.md](docs/PREP_NEXT.md) | Backlog / known debt |
| [docs/DEPLOYED_PROD.md](docs/DEPLOYED_PROD.md) | Lab topology notes (optional) |

---

## Default login

| | |
|--|--|
| Email | `admin@example.com` |
| Password | `admin123` |

Created automatically when the users collection is empty.

---

## Troubleshooting

| Issue | What to try |
|-------|-------------|
| Can’t log in | Check `docker compose logs app` for admin seed; bcrypt is required (passlib removed). Reset volumes only if you accept data loss: `docker compose down -v && ./run.sh` |
| Blank / old UI | Hard refresh; rebuild: `docker compose up -d --build` |
| Mongo crash in LXC | Use compose pin **`mongo:7.0`** (already default), not `mongo:latest` / 8.x |
| Frontend calls wrong API | Rebuild with correct `FRONTEND_ENV` / `./run.sh --host …` (API URL is build-time) |
| CORS | Set `ORIGINS` to your real browser origin(s) |
| Bulletin awards empty | Set class, division, special categories, competitor # on shooters |
| WSL Docker permission | Log out/in after install, or script uses `sudo docker` when needed |
| Seed duplicates | Use `CLEAN=1` (default) on seed script; only removes sample-tagged data |

```bash
docker compose logs -f app
docker compose logs -f mongodb
docker compose ps
```
