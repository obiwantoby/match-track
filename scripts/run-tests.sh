#!/usr/bin/env bash
# Run match-track verification suite.
# Usage:
#   ./scripts/run-tests.sh          # unit only (no Mongo)
#   ./scripts/run-tests.sh all      # unit + API lifecycle (needs Mongo)

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"
export MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}"
export SECRET_KEY="${SECRET_KEY:-dev-secret-at-least-32-chars-long}"

mode="${1:-unit}"

case "$mode" in
  unit)
    echo "==> Unit tests (offline)"
    pytest tests/unit -v
    ;;
  all|integration|api)
    echo "==> Unit + API lifecycle (Mongo required at $MONGO_URL)"
    pytest tests/unit tests/integration/test_api_lifecycle.py -v
    ;;
  *)
    echo "Usage: $0 [unit|all]"
    exit 2
    ;;
esac
