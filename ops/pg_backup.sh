#!/usr/bin/env bash
# Daily PostgreSQL backup with 14-day rotation.
#
# Cron (server): 0 3 * * * /opt/patinho/ops/pg_backup.sh >> /var/log/patinho-backup.log 2>&1
#
# Dumps are stored locally at /opt/patinho/backups/ until an off-site
# destination is provisioned by the client.
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/patinho}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
COMPOSE_FILES=(-f "$PROJECT_DIR/docker-compose.yml" -f "$PROJECT_DIR/docker-compose.prod.yml")

mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
target="$BACKUP_DIR/patinho-$timestamp.sql.gz"

echo "[$(date -Iseconds)] Starting backup -> $target"

docker compose "${COMPOSE_FILES[@]}" exec -T db \
  pg_dump -U patinho -d patinho --clean --if-exists --no-owner \
  | gzip -9 > "$target.partial"

mv "$target.partial" "$target"
size=$(du -h "$target" | cut -f1)
echo "[$(date -Iseconds)] Backup completed: $target ($size)"

# Rotation: keep the N most recent daily dumps.
find "$BACKUP_DIR" -maxdepth 1 -name 'patinho-*.sql.gz' -mtime "+$RETENTION_DAYS" -print -delete

# Emit a small summary for log tailing.
count=$(find "$BACKUP_DIR" -maxdepth 1 -name 'patinho-*.sql.gz' | wc -l)
echo "[$(date -Iseconds)] Retained $count backup(s) in $BACKUP_DIR"
