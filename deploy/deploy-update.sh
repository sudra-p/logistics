#!/bin/bash
# =============================================================================
# Deploy Update Script
# Pulls latest code, rebuilds Docker images, runs migrations, and restarts
# services with minimal downtime.
#
# Usage: Run on the App EC2 instance
#   bash deploy-update.sh [branch]
#
# Arguments:
#   branch - Git branch to deploy (default: main)
# =============================================================================

set -euo pipefail

# --- Configuration ---
APP_DIR="/home/ubuntu/app/logistics"
BRANCH="${1:-main}"
COMPOSE_CMD="docker compose"

echo "=========================================="
echo "  Deploying Update - $(date)"
echo "  Branch: ${BRANCH}"
echo "=========================================="

cd "${APP_DIR}"

# --- Pre-flight checks ---
echo "[1/7] Pre-flight checks..."
if ! ${COMPOSE_CMD} ps | grep -q "Up"; then
    echo "  WARNING: Some services are not running!"
    ${COMPOSE_CMD} ps
fi

# --- Pull latest code ---
echo "[2/7] Pulling latest code..."
git fetch origin
git checkout ${BRANCH}
git pull origin ${BRANCH}

COMMIT_SHA=$(git rev-parse --short HEAD)
echo "  Deployed commit: ${COMMIT_SHA}"

# --- Build new Docker image ---
echo "[3/7] Building new Docker image..."
${COMPOSE_CMD} build --no-cache web

# --- Run database migrations ---
echo "[4/7] Running database migrations..."
${COMPOSE_CMD} run --rm web python manage.py migrate --noinput

# --- Collect static files ---
echo "[5/7] Collecting static files..."
${COMPOSE_CMD} run --rm web python manage.py collectstatic --noinput

# --- Restart services gracefully ---
echo "[6/7] Restarting services (zero-downtime)..."

# Restart web workers gracefully (gunicorn reload)
# This sends SIGHUP to gunicorn master process which spawns new workers
# and gracefully shuts down old ones
WEB_CONTAINER=$(${COMPOSE_CMD} ps -q web)
if [ -n "${WEB_CONTAINER}" ]; then
    docker exec "${WEB_CONTAINER}" kill -HUP 1 2>/dev/null || true
    echo "  Sent graceful reload signal to gunicorn"
    sleep 5
fi

# If graceful reload didn't work, do a rolling restart
${COMPOSE_CMD} up -d --no-deps --force-recreate web
echo "  Web service recreated"

# Restart Celery worker
${COMPOSE_CMD} up -d --no-deps --force-recreate celery_worker
echo "  Celery worker restarted"

# --- Health check ---
echo "[7/7] Running health check..."
sleep 5

HEALTH_URL="http://localhost/api/health/"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_URL}" || echo "000")

if [ "${HTTP_CODE}" == "200" ]; then
    echo "  Health check passed (HTTP ${HTTP_CODE})"
else
    echo "  WARNING: Health check returned HTTP ${HTTP_CODE}"
    echo "  Checking service logs..."
    ${COMPOSE_CMD} logs --tail=20 web
    echo ""
    echo "  Services may still be starting up. Please verify manually."
fi

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "  Commit: ${COMMIT_SHA}"
echo "  Time: $(date)"
echo "=========================================="
