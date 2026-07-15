#!/usr/bin/env bash
# =============================================================================
# Match Track — one-shot installer / launcher
#
# Designed for stock Ubuntu/Debian — servers, VMs, LXC, and WSL2 Ubuntu:
#   git clone … && cd match-track
#   chmod +x run.sh && ./run.sh
#   Optional sample data:
#     ./run.sh --seed
#
# When finished, prints URL + default admin login.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

APP_PORT="${APP_PORT:-8080}"
DB_NAME="${DB_NAME:-shooting_matches_db}"
SEED=0
SKIP_DOCKER_INSTALL=0
NO_BUILD=0
PUBLIC_HOST="${PUBLIC_HOST:-}"   # optional override, e.g. match.example.com or 192.168.1.50

usage() {
  cat <<EOF
Usage: ./run.sh [options]

  --seed              Load sample shooters / matches after start
  --port N            Host port for the UI (default: ${APP_PORT})
  --host HOST         Public hostname or IP for the frontend API URL
                      (default: auto-detect primary LAN IP)
  --skip-docker-install
                      Do not attempt to install Docker if missing
  --no-build          docker compose up without --build
  -h, --help          Show this help

Environment (optional):
  APP_PORT, PUBLIC_HOST, SECRET_KEY, DB_NAME
EOF
}

log()  { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m✓\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed) SEED=1; shift ;;
    --port) APP_PORT="${2:?}"; shift 2 ;;
    --host) PUBLIC_HOST="${2:?}"; shift 2 ;;
    --skip-docker-install) SKIP_DOCKER_INSTALL=1; shift ;;
    --no-build) NO_BUILD=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown option: $1 (try --help)" ;;
  esac
done

need_cmd() { command -v "$1" >/dev/null 2>&1; }

# ---------------------------------------------------------------------------
# Detect public host / IP for the browser
# ---------------------------------------------------------------------------
detect_host() {
  if [[ -n "$PUBLIC_HOST" ]]; then
    echo "$PUBLIC_HOST"
    return
  fi
  # Prefer the IP used for the default route (works on most Ubuntu cloud/LAN boxes)
  local ip=""
  if need_cmd ip; then
    ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}' || true)"
  fi
  if [[ -z "$ip" ]] && need_cmd hostname; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
  fi
  if [[ -z "$ip" ]]; then
    ip="127.0.0.1"
    warn "Could not detect LAN IP; using 127.0.0.1 (override with --host)"
  fi
  echo "$ip"
}

# ---------------------------------------------------------------------------
# Docker install (Ubuntu / Debian)
# ---------------------------------------------------------------------------
install_docker_if_needed() {
  if need_cmd docker && docker compose version >/dev/null 2>&1; then
    ok "Docker and Compose already available"
    return
  fi

  if [[ "$SKIP_DOCKER_INSTALL" -eq 1 ]]; then
    die "Docker/Compose not found and --skip-docker-install was set"
  fi

  if [[ "$(id -u)" -ne 0 ]] && ! need_cmd sudo; then
    die "Need root or sudo to install Docker"
  fi
  SUDO=""
  if [[ "$(id -u)" -ne 0 ]]; then
    SUDO="sudo"
  fi

  log "Installing Docker Engine + Compose plugin (Ubuntu/Debian)..."

  # Minimal deps
  $SUDO apt-get update -y
  $SUDO apt-get install -y ca-certificates curl gnupg

  # Official Docker apt repo (works on Ubuntu 22.04/24.04 and Debian bookworm-ish)
  $SUDO install -m 0755 -d /etc/apt/keyrings
  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    $SUDO chmod a+r /etc/apt/keyrings/docker.gpg
  fi

  # Detect distro id for the apt source line
  local id codename
  # shellcheck source=/dev/null
  . /etc/os-release
  id="${ID:-ubuntu}"
  codename="${VERSION_CODENAME:-jammy}"
  # Docker publishes ubuntu + debian repos; map derivatives loosely
  if [[ "$id" != "ubuntu" && "$id" != "debian" ]]; then
    id="ubuntu"
    codename="jammy"
    warn "Non Ubuntu/Debian ID ($ID); using ubuntu/jammy Docker repo"
  fi

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${id} ${codename} stable" \
    | $SUDO tee /etc/apt/sources.list.d/docker.list >/dev/null

  $SUDO apt-get update -y
  $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  $SUDO systemctl enable --now docker || true

  # Allow non-root use in this session when possible
  if [[ "$(id -u)" -ne 0 ]]; then
    $SUDO usermod -aG docker "$USER" || true
    warn "Added $USER to docker group (may need re-login). Using sudo for this run if needed."
  fi

  if ! need_cmd docker; then
    die "Docker install finished but 'docker' is not on PATH"
  fi
  ok "Docker installed"
}

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
  elif need_cmd sudo && sudo docker info >/dev/null 2>&1; then
    sudo docker "$@"
  else
    die "Cannot talk to Docker daemon (is it running?)"
  fi
}

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  elif need_cmd sudo && sudo docker compose version >/dev/null 2>&1; then
    sudo docker compose "$@"
  else
    die "docker compose plugin not available"
  fi
}

# ---------------------------------------------------------------------------
# Secrets / env for compose
# ---------------------------------------------------------------------------
ensure_env() {
  local host="$1"
  local public_url="http://${host}:${APP_PORT}"
  local api_url="${public_url}/api"

  if [[ ! -f .env ]]; then
    log "Creating .env (SECRET_KEY, ports, public URL)..."
    local secret
    secret="$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p -c 32)"
    cat > .env <<EOF
# Generated by run.sh — safe to keep local; do not commit
SECRET_KEY=${secret}
APP_PORT=${APP_PORT}
PUBLIC_HOST=${host}
PUBLIC_URL=${public_url}
REACT_APP_BACKEND_URL=${api_url}
FRONTEND_ENV=REACT_APP_BACKEND_URL=${api_url}
ORIGINS=${public_url},http://localhost:${APP_PORT},http://127.0.0.1:${APP_PORT}
DB_NAME=${DB_NAME}
EOF
    ok "Wrote .env"
  else
    ok "Using existing .env"
    # Refresh host-facing URLs if missing or host/port changed
    if ! grep -q '^FRONTEND_ENV=' .env 2>/dev/null; then
      echo "FRONTEND_ENV=REACT_APP_BACKEND_URL=${api_url}" >> .env
    fi
  fi

  # Export for this compose invocation (compose reads .env automatically for ${VAR})
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a

  # Ensure critical exports even if .env is partial
  export APP_PORT="${APP_PORT}"
  export SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32 2>/dev/null || echo changeme-please-set-secret)}"
  export FRONTEND_ENV="${FRONTEND_ENV:-REACT_APP_BACKEND_URL=${api_url}}"
  export ORIGINS="${ORIGINS:-${public_url},http://localhost:${APP_PORT},http://127.0.0.1:${APP_PORT}}"
  export DB_NAME="${DB_NAME}"
  export PUBLIC_URL="${PUBLIC_URL:-$public_url}"
}

# ---------------------------------------------------------------------------
# Start stack
# ---------------------------------------------------------------------------
start_stack() {
  log "Building and starting Match Track (this can take several minutes on first run)..."
  if [[ "$NO_BUILD" -eq 1 ]]; then
    compose up -d
  else
    compose up -d --build
  fi
  ok "Containers started"
}

wait_for_app() {
  local host="$1"
  local url="http://127.0.0.1:${APP_PORT}/"
  log "Waiting for app to respond on port ${APP_PORT}..."
  local i
  for i in $(seq 1 60); do
    if curl -fsS -o /dev/null "$url" 2>/dev/null; then
      ok "App is up"
      return 0
    fi
    sleep 2
  done
  warn "App did not answer HTTP yet — check: docker compose logs -f app"
  return 0
}

seed_data() {
  log "Loading sample data..."
  # API listens on 8001 inside the app container; nginx is 8080
  if [[ -f scripts/seed_sample_data.py ]]; then
    compose cp scripts/seed_sample_data.py app:/tmp/seed_sample_data.py
    compose exec -T \
      -e BASE_URL=http://127.0.0.1:8001/api \
      -e ADMIN_EMAIL=admin@example.com \
      -e ADMIN_PASSWORD=admin123 \
      -e CLEAN=1 \
      app python3 /tmp/seed_sample_data.py \
      || warn "Sample data seed failed (app may still be fine)"
  else
    warn "scripts/seed_sample_data.py not found — skip seed"
  fi
}

print_banner() {
  local host="$1"
  local url="${PUBLIC_URL:-http://${host}:${APP_PORT}}"

  cat <<EOF

╔══════════════════════════════════════════════════════════════════╗
║                     MATCH TRACK IS READY                         ║
╠══════════════════════════════════════════════════════════════════╣
║  Open in browser:                                                ║
║                                                                  ║
║      ${url}
║                                                                  ║
║  Login:                                                          ║
║      Email:     admin@example.com                                ║
║      Password:  admin123                                         ║
║                                                                  ║
║  Change that password after first login on shared machines.      ║
╠══════════════════════════════════════════════════════════════════╣
║  Useful commands (from this directory):                          ║
║      docker compose ps                                           ║
║      docker compose logs -f app                                  ║
║      docker compose down                                         ║
║      ./run.sh --seed          # add sample shooters/matches      ║
╚══════════════════════════════════════════════════════════════════╝

EOF
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
  log "Match Track installer"
  echo "  Project: $ROOT"

  if [[ ! -f docker-compose.yml ]] || [[ ! -f Dockerfile ]]; then
    die "Run this from the match-track project root (docker-compose.yml missing)"
  fi

  if ! need_cmd curl; then
    if need_cmd apt-get; then
      log "Installing curl..."
      if [[ "$(id -u)" -eq 0 ]]; then apt-get update -y && apt-get install -y curl
      else sudo apt-get update -y && sudo apt-get install -y curl
      fi
    else
      die "curl is required"
    fi
  fi

  install_docker_if_needed

  local host
  host="$(detect_host)"
  ok "Public host/IP: $host"
  ok "Port: $APP_PORT"

  ensure_env "$host"
  start_stack
  wait_for_app "$host"

  if [[ "$SEED" -eq 1 ]]; then
    seed_data
  fi

  print_banner "$host"
}

main "$@"
