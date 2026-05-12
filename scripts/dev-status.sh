#!/usr/bin/env bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok() { echo -e "${GREEN}●${NC} $1"; }
fail() { echo -e "${RED}●${NC} $1"; }
warn() { echo -e "${YELLOW}●${NC} $1"; }

echo "Care Assist Development Environment Status"
echo "=========================================="
echo ""

# MySQL
if mysqladmin ping -h 127.0.0.1 -P 3306 --silent 2>/dev/null; then
  ok "MySQL      running on localhost:3306"
else
  fail "MySQL      not running"
fi

# Redis
if redis-cli ping >/dev/null 2>&1; then
  ok "Redis      running on localhost:6379"
else
  fail "Redis      not running"
fi

# Backend
if curl -s --connect-timeout 1 http://localhost:8000/health >/dev/null 2>&1; then
  ok "Backend    running on http://localhost:8000"
  curl -s http://localhost:8000/health | sed 's/^/           /'
else
  fail "Backend    not running on http://localhost:8000"
fi

echo ""
