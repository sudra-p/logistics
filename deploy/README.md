# Logistics Platform - EC2 Deployment Guide

## Architecture Overview

The application runs on two EC2 instances in the same VPC:

```
┌─────────────────────────────────────────────────────────┐
│  VPC (10.0.0.0/16)                                      │
│                                                          │
│  ┌─────────────────────────┐   ┌──────────────────────┐│
│  │  App Instance (t3.medium)│   │  DB Instance (t3.med) ││
│  │                          │   │                       ││
│  │  ┌───────┐  ┌────────┐  │   │  ┌────────────────┐  ││
│  │  │ Nginx │──│ Django  │──│───│──│ PostgreSQL 15  │  ││
│  │  └───────┘  │(Gunicorn)│ │   │  └────────────────┘  ││
│  │             └────────┘  │   │                       ││
│  │  ┌───────┐  ┌────────┐  │   │  EBS Volume (gp3)    ││
│  │  │ Redis │  │ Celery  │  │   │  /mnt/pgdata         ││
│  │  └───────┘  └────────┘  │   └──────────────────────┘│
│  └─────────────────────────┘                             │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

- **AWS Account** with the following services:
  - EC2 (2x t3.medium instances)
  - S3 (document storage + backups)
  - SES (email notifications, verified domain/addresses)
  - IAM (roles for EC2 instances)
- **Domain name** with DNS pointing to App instance Elastic IP
- **SSH key pair** for EC2 access

## EC2 Instance Setup

### 1. Create Security Groups

#### App Instance Security Group (`logistics-app-sg`)

| Type    | Port  | Source              | Description          |
|---------|-------|---------------------|----------------------|
| SSH     | 22    | Your IP             | Admin access         |
| HTTP    | 80    | 0.0.0.0/0           | Web traffic          |
| HTTPS   | 443   | 0.0.0.0/0           | Web traffic (SSL)    |

#### DB Instance Security Group (`logistics-db-sg`)

| Type       | Port | Source              | Description          |
|------------|------|---------------------|----------------------|
| SSH        | 22   | Your IP             | Admin access         |
| PostgreSQL | 5432 | logistics-app-sg    | App → DB connection  |

### 2. Create IAM Roles

#### App Instance IAM Role (`logistics-app-role`)
Attach policies:
- `AmazonS3FullAccess` (or scoped to your bucket)
- `AmazonSESFullAccess` (or scoped to your domain)

#### DB Instance IAM Role (`logistics-db-role`)
Attach policies:
- `AmazonS3FullAccess` (for backup uploads)

### 3. Launch EC2 Instances

Both instances:
- **AMI:** Ubuntu 22.04 LTS
- **Type:** t3.medium (2 vCPU, 4GB RAM)
- **Storage:** 20GB gp3 (root volume)

DB instance additional:
- **EBS Volume:** 50GB gp3 (data volume, attach as `/dev/xvdf`)

### 4. Create S3 Buckets

```bash
# Document storage
aws s3 mb s3://logistics-documents --region ap-south-1

# Database backups
aws s3 mb s3://logistics-backups --region ap-south-1
```

## Deployment Steps

### Step 1: Setup DB Instance

SSH into the DB instance and run:

```bash
# Set environment variables
export DB_NAME=logistics
export DB_USER=logistics_user
export DB_PASSWORD="your-secure-password-here"
export APP_SUBNET="10.0.1.0/24"  # App instance private subnet

# Run setup script
sudo -E bash setup-db-instance.sh
```

Note the private IP of the DB instance — you'll need it for the App instance.

### Step 2: Setup App Instance

SSH into the App instance and run:

```bash
# Set environment variables
export REPO_URL="https://github.com/your-org/logistics.git"
export BRANCH="main"

# Run setup script
sudo -E bash setup-app-instance.sh
```

### Step 3: Configure Environment

Edit the `.env` file on the App instance:

```bash
nano /home/ubuntu/logistics/.env
```

Update these values:
- `DJANGO_SECRET_KEY` — generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- `DB_HOST` — Private IP of DB instance
- `DB_PASSWORD` — same as set during DB setup
- `DJANGO_ALLOWED_HOSTS` — your domain name
- `AWS_*` — your AWS credentials (or leave empty if using IAM roles)

### Step 4: Restart and Verify

```bash
cd /home/ubuntu/logistics
docker-compose restart

# Verify health
curl http://localhost/api/health/
```

### Step 5: Setup SSL (Let's Encrypt)

```bash
# Install certbot
sudo apt-get install -y certbot

# Get certificate (stop nginx first or use webroot)
sudo certbot certonly --standalone -d your-domain.com

# Update nginx.conf with certificate paths
# Restart nginx
docker-compose restart nginx
```

### Step 6: Create Admin User

```bash
docker-compose exec web python manage.py createsuperuser
```

### Step 7: Setup Backup Cron

On the DB instance:

```bash
sudo cp /path/to/backup-db.sh /opt/logistics/backup-db.sh
sudo chmod +x /opt/logistics/backup-db.sh

# Configure environment for backup script
echo 'DB_NAME=logistics' | sudo tee /etc/environment.d/logistics.conf
echo 'DB_USER=logistics_user' | sudo tee -a /etc/environment.d/logistics.conf
echo 'S3_BUCKET=logistics-backups' | sudo tee -a /etc/environment.d/logistics.conf
```

## Deploying Updates

From the App instance:

```bash
cd /home/ubuntu/logistics
bash deploy/deploy-update.sh main
```

This will:
1. Pull the latest code
2. Rebuild Docker images
3. Run database migrations
4. Restart services gracefully

## Monitoring

### Health Check

```bash
curl http://your-domain.com/api/health/
# Response: {"status": "ok", "version": "1.0.0"}
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery_worker
docker-compose logs -f nginx
```

### Check Service Status

```bash
docker-compose ps
systemctl status logistics-docker
```

## Troubleshooting

### Services won't start

```bash
# Check Docker status
sudo systemctl status docker

# Check compose logs
docker-compose logs --tail=50

# Verify .env file exists and has correct values
cat /home/ubuntu/logistics/.env
```

### Database connection refused

```bash
# From App instance, test DB connectivity
nc -zv <DB_PRIVATE_IP> 5432

# On DB instance, check PostgreSQL status
sudo systemctl status postgresql

# Check pg_hba.conf allows App instance subnet
sudo cat /etc/postgresql/15/main/pg_hba.conf
```

### Celery tasks not processing

```bash
# Check Redis
docker-compose exec redis redis-cli ping

# Check Celery worker logs
docker-compose logs celery_worker

# Restart Celery
docker-compose restart celery_worker
```

### Out of disk space

```bash
# Check disk usage
df -h

# Clean Docker images
docker system prune -a

# Check PostgreSQL data size (on DB instance)
sudo du -sh /mnt/pgdata/
```

### SSL certificate renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Force renewal
sudo certbot renew --force-renewal
```

## Backup and Recovery

### Manual Backup

```bash
# On DB instance
sudo bash /opt/logistics/backup-db.sh
```

### Restore from Backup

```bash
# Download backup from S3
aws s3 cp s3://logistics-backups/db-backups/logistics_backup_YYYYMMDD_HHMMSS.sql.gz /tmp/

# Decompress
gunzip /tmp/logistics_backup_*.sql.gz

# Restore
sudo -u postgres psql logistics < /tmp/logistics_backup_*.sql
```

## Security Checklist

- [ ] Change all default passwords
- [ ] Restrict SSH access to known IPs
- [ ] Enable AWS CloudTrail for audit logging
- [ ] Set up CloudWatch alarms for CPU/memory
- [ ] Enable PostgreSQL audit logging
- [ ] Configure UFW firewall on both instances
- [ ] Use IAM roles instead of access keys where possible
- [ ] Enable S3 bucket versioning
- [ ] Rotate Django SECRET_KEY periodically
- [ ] Keep system packages updated (`apt-get upgrade`)
