# Match Track — deploy package notes

For the agent/human deploying this on **Proxmox / 192.168.50.5** with **Caddy**.

## Fastest path (Ubuntu / Debian)

From the project root on a stock Ubuntu box:

```bash
chmod +x run.sh
./run.sh              # install Docker if needed, build, start
./run.sh --seed       # same + sample shooters/matches
./run.sh --port 8080 --host 192.168.50.29
```

At the end it prints the **browser URL**, **admin email**, and **password**.

## Live lab topology (clinger)

See **`docs/DEPLOYED_PROD.md`** for the full map. Short version:

- **https://match.clinger.dev** → Caddy CT 102 (`192.168.50.14`) → app CT `192.168.50.29:8080`
- **docs.clinger.dev** left alone (labdocs LAN-only on `.26`, not in Caddy)
- Frontend build: `REACT_APP_BACKEND_URL=https://match.clinger.dev/api`
- **Mongo:** pin **`mongo:7.0`** (not `latest`/8.x — exit 139 in small LXC) + small WiredTiger cache

## What this is

Full-stack shooting match tracker:

- **Frontend:** React (built into nginx static files)
- **Backend:** FastAPI + MongoDB
- **Compose:** `docker-compose.yml` → services `app` + `mongodb`

Local defaults:

- App UI/API: port **8080** inside host (mapped `8080:8080`)
- Mongo: port **27017**
- Default admin: `admin@example.com` / `admin123` (change after first login)

## Recommended host layout

```text
/opt/match-track/          # extract archive here
  docker-compose.yml
  Dockerfile
  backend/
  frontend/
  ...
```

## Build-time env (important for public hostname)

When building behind **docs.clinger.dev** (or a dedicated subdomain), the frontend API URL is baked in at **image build** time via compose build arg `FRONTEND_ENV`.

Edit `docker-compose.yml` before build:

```yaml
services:
  app:
    build:
      context: .
      args:
        FRONTEND_ENV: "REACT_APP_BACKEND_URL=https://docs.clinger.dev/api"
        # If you use a dedicated host instead, e.g.:
        # FRONTEND_ENV: "REACT_APP_BACKEND_URL=https://match.clinger.dev/api"
    environment:
      - MONGO_URL=mongodb://mongodb:27017
      - DB_NAME=shooting_matches_db
      - SECRET_KEY=<long-random-secret>
      - ORIGINS=https://docs.clinger.dev,http://docs.clinger.dev
    ports:
      - "8080:8080"   # or bind only to localhost if Caddy is on same host: "127.0.0.1:8080:8080"
```

Then:

```bash
cd /opt/match-track
docker compose up -d --build
```

## Caddy — add reverse proxy for docs.clinger.dev

If **docs.clinger.dev already serves something else**, prefer a **path** or a **new subdomain** (e.g. `match.clinger.dev`) so docs and match-track do not fight for `/`.

### Option A — dedicated subdomain (recommended)

```caddy
match.clinger.dev {
	encode gzip
	reverse_proxy 127.0.0.1:8080
}
```

DNS: `match.clinger.dev` → host that runs Caddy (or internal VIP).

### Option B — same host as docs under a path (more fragile)

SPA + `/api` under a subpath needs nginx/app path-prefix work this package does **not** fully implement. Prefer Option A.

### Option C — reuse docs.clinger.dev only if nothing else is on it

```caddy
docs.clinger.dev {
	encode gzip
	reverse_proxy 127.0.0.1:8080
}
```

Reload Caddy after edit:

```bash
# common patterns — pick what this host uses
sudo systemctl reload caddy
# or
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Health checks

```bash
curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/
curl -sS -X POST http://127.0.0.1:8080/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123"
```

## Optional sample data (clean reload)

With stack running:

```bash
cd /opt/match-track
docker compose cp scripts/seed_sample_data.py app:/tmp/seed_sample_data.py
# CLEAN=1 (default): deletes prior [SAMPLE] matches/league and SEED* shooters, then reloads
docker compose exec -T \
  -e BASE_URL=http://127.0.0.1:8001/api \
  -e CLEAN=1 \
  app python3 /tmp/seed_sample_data.py
```

Loads **~36 shooters** (NRA `SEED00001…`, competitor #101+), **1 league**, **5 matches**,
hundreds of scores. Safe to re-run — only sample-tagged data is wiped.

Then: match → **Results Bulletin** → Slow Fire / NMC / Grand Agg → Excel or Print/PDF.

## Files to ignore on deploy

Do **not** require host-native Node/Python for runtime — Docker only.

Excluded from the zip (if packaging script was used):

- `.git/`, `.venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`
- local Colima / test DB junk

## Auth note

Password hashing uses **bcrypt** directly (not passlib). Default admin is created on empty DB at startup.

## Stack components in this archive

| Path | Role |
|------|------|
| `docker-compose.yml` | app + mongodb |
| `Dockerfile` | multi-stage frontend build + nginx + uvicorn |
| `entrypoint.sh` | wait for Mongo, start API + nginx |
| `nginx.conf` | serve SPA, proxy `/api` → `:8001` |
| `backend/` | FastAPI |
| `frontend/` | React source |
| `scripts/seed_sample_data.py` | demo data |
| `docs/PREP_NEXT.md` | product backlog / known debt |

## If build fails on frontend eslint

Dockerfile already sets `DISABLE_ESLINT_PLUGIN=true` for production build.
