#!/bin/bash
# =============================================================================
# DB EC2 Instance Setup Script
# Provisions a t3.medium EC2 instance with PostgreSQL 15 and configures it
# for remote access from the App instance.
#
# Usage: Run as root on a fresh Ubuntu 22.04 EC2 instance
#   sudo bash setup-db-instance.sh
#
# Prerequisites:
#   - Ubuntu 22.04 AMI
#   - EBS volume attached for data (recommended: gp3, 50GB+)
#   - Security group allows inbound 5432 from App instance SG only
# =============================================================================

set -euo pipefail

echo "=========================================="
echo "  Logistics DB Instance Setup"
echo "=========================================="

# --- Configuration ---
DB_NAME="${DB_NAME:-logistics}"
DB_USER="${DB_USER:-logistics_user}"
DB_PASSWORD="${DB_PASSWORD:-CHANGE_ME_SECURE_PASSWORD}"
APP_SUBNET="${APP_SUBNET:-10.0.1.0/24}"  # Private subnet of App instance

# --- Update system packages ---
echo "[1/6] Updating system packages..."
apt-get update -y
apt-get upgrade -y

# --- Install PostgreSQL 15 ---
echo "[2/6] Installing PostgreSQL 15..."
apt-get install -y wget gnupg2 lsb-release

# Add PostgreSQL APT repository
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
apt-get update -y
apt-get install -y postgresql-15 postgresql-client-15

# --- Configure EBS volume for data (if attached) ---
echo "[3/6] Configuring data directory..."
DATA_DIR="/var/lib/postgresql/15/main"

# Check if additional EBS volume is available at /dev/xvdf
if [ -b /dev/xvdf ]; then
    echo "  Found EBS volume at /dev/xvdf"
    # Only format if not already formatted
    if ! blkid /dev/xvdf; then
        mkfs.ext4 /dev/xvdf
    fi

    # Stop PostgreSQL to move data
    systemctl stop postgresql

    # Mount EBS volume
    mkdir -p /mnt/pgdata
    mount /dev/xvdf /mnt/pgdata

    # Add to fstab for persistence
    if ! grep -q "/mnt/pgdata" /etc/fstab; then
        echo "/dev/xvdf /mnt/pgdata ext4 defaults,nofail 0 2" >> /etc/fstab
    fi

    # Move PostgreSQL data to EBS
    if [ ! -d "/mnt/pgdata/postgresql" ]; then
        cp -a ${DATA_DIR} /mnt/pgdata/postgresql
    fi

    # Update PostgreSQL data directory
    sed -i "s|data_directory = '${DATA_DIR}'|data_directory = '/mnt/pgdata/postgresql'|" \
        /etc/postgresql/15/main/postgresql.conf
    DATA_DIR="/mnt/pgdata/postgresql"

    systemctl start postgresql
    echo "  Data directory moved to EBS volume"
else
    echo "  No additional EBS volume detected, using default data directory"
fi

# --- Configure PostgreSQL for remote access ---
echo "[4/6] Configuring PostgreSQL for remote access..."

PG_CONF="/etc/postgresql/15/main/postgresql.conf"
PG_HBA="/etc/postgresql/15/main/pg_hba.conf"

# Listen on all interfaces
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '0.0.0.0'/" ${PG_CONF}

# Performance tuning for t3.medium (4GB RAM)
cat >> ${PG_CONF} << 'PGCONF'

# --- Custom Performance Settings ---
shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
work_mem = 16MB
max_connections = 100
checkpoint_completion_target = 0.9
wal_buffers = 16MB
random_page_cost = 1.1
effective_io_concurrency = 200
min_wal_size = 1GB
max_wal_size = 4GB
PGCONF

# Allow connections from App instance subnet
echo "# Allow connections from App instance subnet" >> ${PG_HBA}
echo "host    ${DB_NAME}    ${DB_USER}    ${APP_SUBNET}    scram-sha-256" >> ${PG_HBA}

# --- Create database and user ---
echo "[5/6] Creating database and user..."
systemctl restart postgresql

sudo -u postgres psql << SQL
-- Create application user
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';

-- Create database
CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};

-- Connect to the database and set up schema permissions
\c ${DB_NAME}
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
SQL

echo "  Database '${DB_NAME}' created with user '${DB_USER}'"

# --- Install backup utilities ---
echo "[6/6] Installing backup utilities..."
apt-get install -y awscli

# Set up daily backup cron job
cat > /etc/cron.d/logistics-backup << 'CRON'
# Daily database backup at 2:00 AM UTC
0 2 * * * root /opt/logistics/backup-db.sh >> /var/log/logistics-backup.log 2>&1
CRON

# Copy backup script
mkdir -p /opt/logistics
# The backup script should be copied from deploy/backup-db.sh

echo ""
echo "=========================================="
echo "  DB Instance Setup Complete!"
echo "=========================================="
echo ""
echo "PostgreSQL 15 is running and configured."
echo ""
echo "Connection details:"
echo "  Host: $(hostname -I | awk '{print $1}')"
echo "  Port: 5432"
echo "  Database: ${DB_NAME}"
echo "  User: ${DB_USER}"
echo "  Password: (as configured)"
echo ""
echo "IMPORTANT: Update the App instance .env with this host IP!"
echo ""
echo "To test connection from App instance:"
echo "  psql -h $(hostname -I | awk '{print $1}') -U ${DB_USER} -d ${DB_NAME}"
echo ""
