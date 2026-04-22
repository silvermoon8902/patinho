#!/usr/bin/env bash
# Weekly restore verification: pipe the latest dump into a throwaway
# Postgres container and sanity-check key tables exist + have rows.
#
# Cron (server): 0 5 * * 0 /opt/patinho/ops/pg_restore_verify.sh
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/patinho/backups}"

latest="$(ls -1t "$BACKUP_DIR"/patinho-*.sql.gz 2>/dev/null | head -n 1 || true)"
if [[ -z "$latest" ]]; then
  echo "[$(date -Iseconds)] No backup found in $BACKUP_DIR"
  exit 1
fi

echo "[$(date -Iseconds)] Verifying $latest"

container="patinho-restore-verify-$RANDOM"
docker run --rm -d --name "$container" \
  -e POSTGRES_USER=patinho \
  -e POSTGRES_PASSWORD=patinho \
  -e POSTGRES_DB=patinho \
  postgres:16-alpine > /dev/null

cleanup() { docker rm -f "$container" >/dev/null 2>&1 || true; }
trap cleanup EXIT

# Wait for readiness
for _ in {1..30}; do
  if docker exec "$container" pg_isready -U patinho >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

gunzip -c "$latest" | docker exec -i "$container" psql -U patinho -d patinho > /dev/null

for table in users bets wallets participations bet_templates; do
  count=$(docker exec "$container" psql -U patinho -d patinho -tAc "SELECT COUNT(*) FROM $table;")
  echo "  $table: $count rows"
done

echo "[$(date -Iseconds)] Verification OK"
