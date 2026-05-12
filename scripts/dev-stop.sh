#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[dev-stop]${NC} $1"; }
warn() { echo -e "${RED}[dev-stop]${NC} $1"; }

# Stop backend
if [[ -f "$PROJECT_ROOT/.dev-backend.pid" ]]; then
  PID=$(cat "$PROJECT_ROOT/.dev-backend.pid")
  if kill "$PID" 2>/dev/null; then
    log "Stopped backend (PID: $PID)"
  else
    warn "Backend PID $PID not found, may already be stopped."
  fi
  rm -f "$PROJECT_ROOT/.dev-backend.pid"
else
  warn "Backend PID file not found."
fi

# Stop MySQL (Docker only, don't stop brew services to avoid interfering)
if docker ps --format '{{.Names}}' | grep -q "^care-assist-mysql$"; then
  docker stop care-assist-mysql >/dev/null 2>&1
  log "Stopped MySQL container."
fi

# Stop Redis (Docker only)
if docker ps --format '{{.Names}}' | grep -q "^care-assist-redis$"; then
  docker stop care-assist-redis >/dev/null 2>&1
  log "Stopped Redis container."
fi

log "Development environment stopped."
