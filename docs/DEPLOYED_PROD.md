# Production deployment (clinger lab)

Captured from the live CT deploy. Keep **docs.clinger.dev** separate.

## Topology

| Piece | Detail |
|-------|--------|
| Public URL | **https://match.clinger.dev** |
| Caddy | CT **102** (`192.168.50.14`) reverse_proxy → `192.168.50.29:8080` |
| App CT | `192.168.50.29` (Match Track compose) |
| docs.clinger.dev | **Left alone** — labdocs stays LAN-only on `.26` (not in Caddy) |

```
Browser → https://match.clinger.dev
       → Caddy CT 102 (192.168.50.14)
       → 192.168.50.29:8080  (app + nginx)
```

## Frontend build

```text
REACT_APP_BACKEND_URL=https://match.clinger.dev/api
```

(via compose `FRONTEND_ENV` / `.env` at **build** time)

## Live checks (last known good)

- `https://match.clinger.dev` → 200  
- Public login → ok  
- LAN `http://192.168.50.29:8080` → 200  

## Sample data (seeded on prod CT)

- 12 shooters  
- 1 league: River City Pistol League  
- 4 matches with scores (June Outdoor, Two-Gun 1800, July 2700, Service & Revolver 1800)  

## Login (change on shared systems)

- `admin@example.com` / `admin123`

## Ops notes that matter for the next install

1. **Mongo pin:** `mongo:latest` (8.x) segfaulted (**exit 139**) in this LXC. Use **`mongo:7.0`** with a smaller WiredTiger cache (`--wiredTigerCacheSizeGB 0.25`) and `restart: unless-stopped`. Already reflected in `docker-compose.yml`.
2. **Dockerfile:** `rm /app/.env` → **`rm -f`** so a missing `.env` does not break the frontend build stage.
3. Deploy notes on the CT: `/opt/match-track/DEPLOYED.txt`

## Handy commands on the app CT

```bash
cd /opt/match-track
docker compose ps
docker compose logs -f app
docker compose logs -f mongodb
docker compose restart
docker compose down
docker compose up -d --build
```

## Caddy snippet (CT 102)

```caddy
match.clinger.dev {
	encode gzip
	reverse_proxy 192.168.50.29:8080
}
```
