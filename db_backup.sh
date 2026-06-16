#!/bin/bash
#
# Back up the Secret Snakes SQLite database and upload it to S3.
#
# Designed to run from cron on the EC2 host, e.g.:
#   0 3 * * * /home/ec2-user/secret-snakes/db_backup.sh >> /home/ec2-user/backups/backup.log 2>&1
#
# Unlike the original, this version FAILS LOUDLY: if any step (locate DB,
# snapshot, compress, upload) fails, the script exits non-zero and does NOT
# print a success message. That way a broken backup can't masquerade as a
# working one.

set -euo pipefail

# --- Configuration -----------------------------------------------------------

# Absolute path to the .env file. Hardcoded so the script behaves the same no
# matter what directory cron launches it from. Override by exporting ENV_FILE.
ENV_FILE="${ENV_FILE:-/home/ec2-user/secret-snakes/.env}"

# Where local snapshots are written before upload.
BACKUP_DIR="${BACKUP_DIR:-/home/ec2-user/backups}"

# S3 destination.
S3_BUCKET="${S3_BUCKET:-secret-snakes}"
S3_PREFIX="${S3_PREFIX:-database-backup}"

# Local snapshots are TRANSIENT. Each run stages the snapshot in BACKUP_DIR only
# long enough to compress and upload it, then deletes it (see the EXIT trap
# below). Nothing is retained on the host; backups live in S3. Set KEEP_LOCAL=1
# only when debugging a single run.
KEEP_LOCAL="${KEEP_LOCAL:-0}"

# --- Helpers -----------------------------------------------------------------

die() { echo "ERROR: $*" >&2; exit 1; }

# Report the line number if the script aborts unexpectedly under `set -e`.
trap 'die "backup aborted at line $LINENO"' ERR

# --- Preconditions -----------------------------------------------------------

command -v sqlite3 >/dev/null 2>&1 || die "sqlite3 is not installed or not on PATH"
command -v aws     >/dev/null 2>&1 || die "aws CLI is not installed or not on PATH"

[ -f "$ENV_FILE" ] || die ".env file not found at $ENV_FILE"

# Load environment variables from .env.
# shellcheck disable=SC1090
source "$ENV_FILE"

# The backup runs on the HOST, so it needs the host-side path to the database
# (SQLITE_DATABASE_FILEPATH_LOCAL), NOT the in-container path the app uses
# (SQLITE_DATABASE_FILEPATH, e.g. /app/data/...). They are intentionally
# different because the DB directory is bind-mounted into the container.
DB_FILE="${SQLITE_DATABASE_FILEPATH_LOCAL:-}"

[ -n "$DB_FILE" ] || die "SQLITE_DATABASE_FILEPATH_LOCAL is not set in $ENV_FILE"
[ -f "$DB_FILE" ] || die "Database file does not exist at: $DB_FILE"
[ -r "$DB_FILE" ] || die "Database file is not readable: $DB_FILE"

# --- Backup ------------------------------------------------------------------

mkdir -p "$BACKUP_DIR"

# Include the time, not just the date, so a second run in the same day does not
# silently overwrite the first.
TIMESTAMP="$(date +%Y-%m-%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/backup-$TIMESTAMP.db"
GZ_FILE="$BACKUP_FILE.gz"

# The staged snapshot is temporary. Remove it whenever the script exits, on
# success OR failure, so nothing accumulates on the host (backups live in S3).
# An aborted run that left a half-written .db/.db.gz behind is cleaned up too.
cleanup() {
    if [ "$KEEP_LOCAL" != "1" ]; then
        rm -f "$BACKUP_FILE" "$GZ_FILE" 2>/dev/null || true
    fi
}
trap 'cleanup' EXIT

# Use SQLite's online .backup (safe on a live database, unlike a raw file copy).
sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'" \
    || die "sqlite3 .backup failed for $DB_FILE"

# A backup of nothing is worse than no backup, because it looks like success.
[ -s "$BACKUP_FILE" ] || die "backup file is empty: $BACKUP_FILE"

gzip -f "$BACKUP_FILE" || die "gzip failed for $BACKUP_FILE"
[ -s "$GZ_FILE" ] || die "compressed backup is empty: $GZ_FILE"

# --- Upload ------------------------------------------------------------------

S3_URI="s3://$S3_BUCKET/$S3_PREFIX/$(basename "$GZ_FILE")"
aws s3 cp "$GZ_FILE" "$S3_URI" || die "upload to $S3_URI failed"

# --- Cleanup -----------------------------------------------------------------
# The staged local snapshot is deleted by the EXIT trap (cleanup) defined above,
# so no copies accumulate on the host. Only reached if every step succeeded.
echo "Database backup created and uploaded successfully: $S3_URI"
