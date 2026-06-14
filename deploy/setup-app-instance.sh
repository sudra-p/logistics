#!/bin/bash
# =============================================================================
# App EC2 Instance Setup Script
# Provisions a t3.medium EC2 instance with Docker, Docker Compose, and
# deploys the Logistics application stack (Django + Celery + Redis + Nginx).
#
# Usage: Run as root on a fresh Ubuntu 22.04 EC2 instance
#   sudo bash setup-app-instance.sh
#
# Prerequisites:
#   - Ubuntu 22.04 AMI
#   - IAM role with S3, SES permissions attached
#   - Security group allows inbound 80, 443, 22
#   - DB instance already provisioned and accessible
# =============================================================================

set -euo pipefail

echo "=========================================="
echo "  Logistics App Instance Setup"
echo "=========================================="

# --- Configuration ---
APP_USER="ubuntu"
APP_DIR="/home/${APP_USER}/logistics"
REPO_URL="${REPO_URL:-https://github.com/your-org/logistics.git}"
BRANCH="${BRANCH:-main}"

# --- Update system packages ---
echo "[1/8] Updating system packages..."
apt-get update -y
apt-get upgrade -y

# --- Install Docker ---
echo "[2/8] Installing Docker..."
apt-get install -y ca-certificates curl gnupg lsb-release

mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add ubuntu user to docker group
usermod -aG docker ${APP_USER}

# --- Install Docker Compose (standalone) ---
echo "[3/8] Installing Docker Compose..."
COMPOSE_VERSION="v2.24.0"
curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# --- Install Git and utilities ---
echo "[4/8] Installing Git and utilities..."
apt-get install -y git awscli jq htop

# --- Clone application code ---
echo "[5/8] Cloning application code..."
if [ -d "${APP_DIR}" ]; then
    echo "  App directory exists, pulling latest..."
    cd "${APP_DIR}"
    sudo -u ${APP_USER} git pull origin ${BRANCH}
else
    sudo -u ${APP_USER} git clone -b ${BRANCH} "${REPO_URL}" "${APP_DIR}"
fi

cd "${APP_DIR}"

# --- Create .env file from template ---
echo "[6/8] Creating environment configuration..."
if [ ! -f "${APP_DIR}/.env" ]; then
    cat > "${APP_DIR}/.env" << 'ENVFILE'
# Django Settings
DJANGO_SECRET_KEY=CHANGE_ME_TO_A_RANDOM_SECRET_KEY
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,localhost

# Database (points to DB EC2 instance private IP)
DB_NAME=logistics
DB_USER=logistics_user
DB_PASSWORD=CHANGE_ME_DB_PASSWORD
DB_HOST=CHANGE_ME_DB_PRIVATE_IP
DB_PORT=5432

# Redis (local, via Docker)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# AWS Configuration
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET_NAME=logistics-documents
AWS_S3_REGION=ap-south-1

# AWS SES
AWS_SES_REGION=ap-south-1
AWS_SES_FROM_EMAIL=noreply@your-domain.com

# Distribution list (comma-separated)
DISTRIBUTION_LIST=admin@your-domain.com
ENVFILE
    chown ${APP_USER}:${APP_USER} "${APP_DIR}/.env"
    echo "  .env file created. Please edit with actual values!"
    echo "  >> nano ${APP_DIR}/.env"
fi

# --- Build and start Docker Compose services ---
echo "[7/8] Building and starting Docker services..."
cd "${APP_DIR}"
sudo -u ${APP_USER} docker-compose build
sudo -u ${APP_USER} docker-compose up -d

# --- Run Django migrations ---
echo "[8/8] Running Django migrations..."
sudo -u ${APP_USER} docker-compose exec -T web python manage.py migrate
sudo -u ${APP_USER} docker-compose exec -T web python manage.py collectstatic --noinput

# --- Install systemd service for auto-start ---
echo "Installing systemd service..."
cp "${APP_DIR}/deploy/logistics-docker.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable logistics-docker.service

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env file: nano ${APP_DIR}/.env"
echo "  2. Restart services: docker-compose restart"
echo "  3. Create superuser: docker-compose exec web python manage.py createsuperuser"
echo "  4. Verify health: curl http://localhost/api/health/"
echo ""
