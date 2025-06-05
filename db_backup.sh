#!/bin/bash

# Set your database file path
DB_FILE="secret_snakes.db"

# Set backup directory
BACKUP_DIR="/home/ec2-user/backups"

# S3 bucket name
S3_BUCKET="secret-snakes"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Get current date in YYYY-MM-DD format
DATE=$(date +%Y-%m-%d)

# Backup database to a file with date in name
BACKUP_FILE="$BACKUP_DIR/backup-$DATE.db"
sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"

# Optional: Compress the backup (recommended)
gzip "$BACKUP_FILE"

# Upload compressed backup to S3
aws s3 cp "$BACKUP_FILE.gz" "s3://$S3_BUCKET/database-backup/backup-$DATE.db.gz"
