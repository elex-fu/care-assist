#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[dev-start]${NC} $1"; }
warn() { echo -e "${YELLOW}[dev-start]${NC} $1"; }
err() { echo -e "${RED}[dev-start]${NC} $1"; }

# --- Check dependencies ---

check_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "$1 is required but not installed."
    exit 1
  fi
}

check_cmd python3
check_cmd curl

# --- Check ports ---

check_port() {
  local port=$1
  if lsof -i ":$port" >/dev/null 2>&1; then
    warn "Port $port is already in use."
    return 1
  fi
  return 0
}

# --- MySQL ---

start_mysql() {
  log "Checking MySQL..."
  if mysqladmin ping -h 127.0.0.1 -P 3306 --silent 2>/dev/null; then
    log "MySQL is already running."
    return 0
  fi

  if command -v brew >/dev/null 2>&1 && brew services list 2>/dev/null | grep -q "mysql"; then
    log "Starting MySQL via brew services..."
    brew services start mysql
    sleep 3
  elif command -v docker >/dev/null 2>&1; then
    log "Starting MySQL via Docker..."
    docker run -d --name care-assist-mysql \
      -e MYSQL_ROOT_PASSWORD=rootpass \
      -e MYSQL_DATABASE=care_assist \
      -e MYSQL_USER=care \
      -e MYSQL_PASSWORD=carepass \
      -p 3306:3306 \
      mysql:8.0 \
      2>/dev/null || docker start care-assist-mysql 2>/dev/null || true
    sleep 5
  else
    err "MySQL is not running and no supported method found to start it."
    err "Install with: brew install mysql@8.0"
    exit 1
  fi

  # Wait for MySQL to be ready
  local retries=30
  while ! mysqladmin ping -h 127.0.0.1 -P 3306 --silent 2>/dev/null && [[ $retries -gt 0 ]]; do
    sleep 1
    ((retries--))
  done

  if mysqladmin ping -h 127.0.0.1 -P 3306 --silent 2>/dev/null; then
    log "MySQL is ready."
  else
    err "MySQL failed to start."
    exit 1
  fi
}

# --- Redis ---

start_redis() {
  log "Checking Redis..."
  if redis-cli ping >/dev/null 2>&1; then
    log "Redis is already running."
    return 0
  fi

  if command -v brew >/dev/null 2>&1 && brew services list 2>/dev/null | grep -q "redis"; then
    log "Starting Redis via brew services..."
    brew services start redis
    sleep 2
  elif command -v docker >/dev/null 2>&1; then
    log "Starting Redis via Docker..."
    docker run -d --name care-assist-redis \
      -p 6379:6379 \
      redis:7-alpine \
      2>/dev/null || docker start care-assist-redis 2>/dev/null || true
    sleep 2
  else
    warn "Redis is not running and no supported method found to start it."
    warn "Install with: brew install redis"
    warn "Backend will start without Redis (some features may not work)."
    return 0
  fi

  local retries=10
  while ! redis-cli ping >/dev/null 2>&1 && [[ $retries -gt 0 ]]; do
    sleep 1
    ((retries--))
  done

  if redis-cli ping >/dev/null 2>&1; then
    log "Redis is ready."
  else
    warn "Redis failed to start. Backend will start without it."
  fi
}

# --- Backend ---

start_backend() {
  log "Checking backend..."

  if ! check_port 8000; then
    err "Port 8000 is occupied. Is another uvicorn running?"
    exit 1
  fi

  cd "$BACKEND_DIR"

  if [[ ! -d ".venv" ]]; then
    log "Creating Python virtual environment..."
    python3 -m venv .venv
  fi

  source .venv/bin/activate

  log "Installing dependencies..."
  if command -v uv >/dev/null 2>&1; then
    uv pip install -q -r requirements.txt
  else
    pip install -q -r requirements.txt
  fi

  log "Starting FastAPI backend on http://localhost:8000 ..."
  nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
  BACKEND_PID=$!

  # Wait for health check
  local retries=20
  while ! curl -s --connect-timeout 1 http://localhost:8000/health >/dev/null 2>&1 && [[ $retries -gt 0 ]]; do
    sleep 1
    ((retries--))
  done

  if curl -s --connect-timeout 1 http://localhost:8000/health >/dev/null 2>&1; then
    log "Backend is ready. PID: $BACKEND_PID"
    echo "$BACKEND_PID" > "$PROJECT_ROOT/.dev-backend.pid"
  else
    err "Backend failed to start. Check logs/backend.log"
    exit 1
  fi
}

# --- Main ---

mkdir -p "$PROJECT_ROOT/logs"

log "Starting care-assist development environment..."

start_mysql
start_redis
start_backend

log ""
log "========================================"
log "  Development environment is running"
log "========================================"
log "  API Docs:    http://localhost:8000/docs"
log "  Health:      http://localhost:8000/health"
log "  MySQL:       localhost:3306"
log "  Redis:       localhost:6379"
log ""
log "  Logs:        logs/backend.log"
log "  Stop:        scripts/dev-stop.sh"
log "  Status:      scripts/dev-status.sh"
log "========================================"
