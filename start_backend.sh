#!/bin/bash
set -e

# Configuration
MYSQL_DATA_DIR="${MYSQL_DATA_DIR:-$(dirname "$0")/.mysql_data}"
MYSQL_PORT="${MYSQL_PORT:-3308}"
MYSQL_SOCKET="/tmp/mysql_3308.sock"
DATABASE_URL="mysql+aiomysql://root@localhost:${MYSQL_PORT}/care_assist"
BACKEND_DIR="$(dirname "$0")/backend"

echo "=== Family Health Assistant Backend Starter ==="

# 1. Start MySQL if not running
if ! mysqladmin -uroot -P${MYSQL_PORT} -h127.0.0.1 ping >/dev/null 2>&1; then
    echo "[1/4] Starting MySQL on port ${MYSQL_PORT}..."
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
    echo "[1/4] MySQL already running on port ${MYSQL_PORT}"
fi

# 2. Create database if not exists
echo "[2/4] Ensuring database exists..."
mysql -uroot -P${MYSQL_PORT} -h127.0.0.1 -e "CREATE DATABASE IF NOT EXISTS care_assist CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>/dev/null || true

# 3. Run Alembic migrations
echo "[3/4] Running Alembic migrations..."
cd "$BACKEND_DIR"
export DATABASE_URL
if [ -f ".venv/bin/alembic" ]; then
    .venv/bin/alembic upgrade head
else
    echo "ERROR: .venv/bin/alembic not found. Please run: cd backend && python -m venv .venv && pip install -r requirements.txt"
    exit 1
fi

# 4. Start Uvicorn
echo "[4/4] Starting Uvicorn on http://localhost:8000 ..."
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
