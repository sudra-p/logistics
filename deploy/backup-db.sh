#!/bin/bash
# =============================================================================
# PostgreSQL Backup Script
# Dumps the logistics database and uploads to S3.
# Intended to run via cron on the DB instance.
#
# Usage:
#   bash backup-db.sh
#
# Prerequisites:
#   - AWS CLI configured with S3 write permissions (IAM role recommended)
#   - PostgreSQL client tools installed
#
# Cron example (daily at 2 AM UTC):
#   0 2 * * * /opt/logistics/backup-db.sh >> /var/log/logistics-backup.log 2>&1
# =============================================================================

set -euo pipefail

# --- Configuration ---
DB_NAME="${DB_NAME:-logistics}"
DB_USER="${DB_USER:-logistics_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
S3_BUCKET="${S3_BUCKET:-logistics-backups}"
S3_PREFIX="${S3_PREFIX:-db-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# --- Derived variables ---
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/${DB_NAME}_backup_${TIMESTAMP}.sql.gz"
S3_KEY="s3://${S3_BUCKET}/${S3_PREFIX}/${DB_NAME}_backup_${TIMESTAMP}.sql.gz"

echo "=========================================="
echo "  Database Backup - ${TIMESTAMP}"
echo "=========================================="

# --- Create backup ---
echo "[1/4] Creating database dump..."
pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --no-password \
    --format=plain \
    --no-owner \
    --no-privileges \
    | gzip > "${BACKUP_FILE}"

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "  Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# --- Upload to S3 ---
echo "[2/4] Uploading to S3..."
aws s3 cp "${BACKUP_FILE}" "${S3_KEY}" \
    --storage-class STANDARD_IA \
    --quiet

echo "  Uploaded to: ${S3_KEY}"

# --- Verify upload ---
echo "[3/4] Verifying upload..."
if aws s3 ls "${S3_KEY}" > /dev/null 2>&1; then
    echo "  Verification successful"
else
    echo "  ERROR: Upload verification failed!"
    exit 1
fi

# --- Clean up ---
echo "[4/4] Cleaning up..."
rm -f "${BACKUP_FILE}"

# Remove old backups from S3 (older than RETENTION_DAYS)
echo "  Removing backups older than ${RETENTION_DAYS} days..."
CUTOFF_DATE=$(date -d "-${RETENTION_DAYS} days" +%Y-%m-%d 2>/dev/null || date -v-${RETENTION_DAYS}d +%Y-%m-%d)
aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" | while read -r line; do
    FILE_DATE=$(echo "$line" | awk '{print $1}')
    FILE_NAME=$(echo "$line" | awk '{print $4}')
    if [[ "${FILE_DATE}" < "${CUTOFF_DATE}" ]] && [[ -n "${FILE_NAME}" ]]; then
        aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}/${FILE_NAME}" --quiet
        echo "    Removed old backup: ${FILE_NAME}"
    fi
done

echo ""
echo "Backup completed successfully at $(date)"
echo "=========================================="
