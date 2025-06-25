#!/bin/bash 

# Define the path to your .env file
# Assuming your .env file is in the same directory as this script.
# Adjust this path if your .env file is located elsewhere.
ENV_FILE="./.env"

# Check if the .env file exists
if [ -f "$ENV_FILE" ]; then
    # Source the .env file to load environment variables
    # This reads key=value pairs and sets them as environment variables
    source "$ENV_FILE"
else
    echo "Error: .env file not found at $ENV_FILE"
    echo "Please ensure your SQLITE_DATABASE_FILEPATH is correctly set in a .env file."
    exit 1
fi

# Now reference SQLITE_DATABASE_FILEPATH from the environment
# It will be automatically set by the 'source' command if it's in your .env
# Make sure SQLITE_DATABASE_FILEPATH is defined in your .env like:
# SQLITE_DATABASE_FILEPATH=/path/to/your/secret_snakes.db
DB_FILE="$SQLITE_DATABASE_FILEPATH_LOCAL"

# Check if DB_FILE is set
if [ -z "$DB_FILE" ]; then
    echo "Error: SQLITE_DATABASE_FILEPATH is not set in $ENV_FILE"
    exit 1
fi

# Set backup directory
BACKUP_DIR="/home/ec2-user/backups"

# S3 bucket name
S3_BUCKET="secret-snakes" # You might want to get this from .env too, e.g., S3_BUCKET="$S3_BUCKET_NAME"

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

echo "Database backup created and uploaded successfully: s3://$S3_BUCKET/database-backup/backup-$DATE.db.gz"