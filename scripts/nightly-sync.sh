#!/bin/bash
# Nightly listing refresh for a local Mac setup: makes sure the database is
# up (Colima + docker compose), then syncs every authorized source and hides
# listings older than LISTING_MAX_AGE_DAYS. Scheduled by
# scripts/install-nightly-sync.sh; logs to ~/Library/Logs/weblora-nightly-sync.log.
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') nightly sync starting"
colima status >/dev/null 2>&1 || colima start
cd "$ROOT"
docker compose up -d db redis
for _ in $(seq 1 30); do
  docker compose exec -T db pg_isready -U realestate >/dev/null 2>&1 && break
  sleep 2
done

cd "$ROOT/backend"
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py sync_sources
echo "=== $(date '+%Y-%m-%d %H:%M:%S') nightly sync finished"
