#!/bin/bash
set -e

# Configuration
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MYSQL_DATA_DIR="${MYSQL_DATA_DIR:-${PROJECT_ROOT}/.mysql_data}"
MYSQL_PORT="${MYSQL_PORT:-3308}"
MYSQL_SOCKET="/tmp/mysql_3308.sock"
UVICORN_PORT="${UVICORN_PORT:-8000}"
DATABASE_URL="mysql+aiomysql://root@localhost:${MYSQL_PORT}/care_assist"
BACKEND_DIR="${PROJECT_ROOT}/backend"

echo "=== Family Health Assistant Backend Starter ==="

# 1. Start MySQL if not running
if ! mysqladmin -uroot -P${MYSQL_PORT} -h127.0.0.1 ping >/dev/null 2>&1; then
    echo "[1/5] Starting MySQL on port ${MYSQL_PORT}..."
    if [ ! -d "$MYSQL_DATA_DIR/mysql" ]; then
        echo "      Initializing MySQL data directory..."
        mkdir -p "$MYSQL_DATA_DIR"
        mysqld --initialize-insecure --datadir="$MYSQL_DATA_DIR"
    fi
    mysqld --datadir="$MYSQL_DATA_DIR" --port=${MYSQL_PORT} --socket="$MYSQL_SOCKET" &
    MYSQL_PID=$!

    # Wait for MySQL to be ready
    for i in {1..30}; do
        if mysqladmin -uroot -P${MYSQL_PORT} -h127.0.0.1 ping >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done

    if ! mysqladmin -uroot -P${MYSQL_PORT} -h127.0.0.1 ping >/dev/null 2>&1; then
        echo "ERROR: MySQL failed to start"
        exit 1
    fi
    echo "      MySQL ready (pid: $MYSQL_PID)"
else
    echo "[1/5] MySQL already running on port ${MYSQL_PORT}"
fi

# 2. Create database if not exists
echo "[2/5] Ensuring database exists..."
mysql -uroot -P${MYSQL_PORT} -h127.0.0.1 -e "CREATE DATABASE IF NOT EXISTS care_assist CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || true

# 3. Run Alembic migrations
echo "[3/5] Running Alembic migrations..."
cd "$BACKEND_DIR"
export DATABASE_URL
if [ -f ".venv/bin/alembic" ]; then
    .venv/bin/alembic upgrade head
else
    echo "ERROR: .venv/bin/alembic not found. Please run: cd backend && python -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

# 4. Kill existing process on port 8000
echo "[4/5] Checking for existing process on port ${UVICORN_PORT}..."
OLD_PID=$(lsof -ti tcp:${UVICORN_PORT} 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
    echo "      Killing existing process (pid: $OLD_PID)..."
    kill -9 $OLD_PID 2>/dev/null || true
    sleep 1
fi

# 5. Start Uvicorn
echo "[5/5] Starting Uvicorn on http://localhost:${UVICORN_PORT} ..."
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${UVICORN_PORT} --reload
