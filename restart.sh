#!/bin/bash
# PeerForge — full restart script
# Run this whenever the app stops working or the DB gets an I/O error:
#   chmod +x restart.sh && ./restart.sh

set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
API_DIR="$REPO/arinar-v2/apps/api"
WEB_DIR="$REPO/arinar-v2/apps/web"

echo "=== PeerForge Restart ==="

# ── 1. Kill old processes ────────────────────────────────────────────────────
echo "→ Stopping old processes..."
pkill -f "uvicorn src.main" 2>/dev/null || true
pkill -f "celery.*worker"   2>/dev/null || true
pkill -f "next dev"         2>/dev/null || true
sleep 1

# ── 2. Restart Colima (fixes Docker I/O errors) ─────────────────────────────
echo "→ Restarting Colima VM..."
colima stop --force 2>/dev/null || true
colima start --cpu 2 --memory 4 --disk 20
echo "→ Waiting for Docker to stabilise..."
sleep 8

# ── 3. Restart containers ───────────────────────────────────────────────────
echo "→ Restarting Docker containers..."
docker restart peerforge-db peerforge-redis peerforge-minio 2>/dev/null || \
  (cd "$REPO/arinar-v2/infra/docker" && docker compose -f docker-compose.dev.yml up -d)
echo "→ Waiting for DB to accept connections..."
for i in $(seq 1 15); do
  if nc -z localhost 5433 2>/dev/null; then
    echo "   DB port open after ${i}s"
    break
  fi
  sleep 1
done
sleep 3  # extra settle time for Postgres to finish recovery

# ── 4. Verify DB ─────────────────────────────────────────────────────────────
echo "→ Verifying database..."
cd "$API_DIR"
source .venv/bin/activate
python3 -c "
import psycopg2, sys
try:
    conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5433/peerforge_local')
    cur = conn.cursor()
    cur.execute('SELECT count(*) FROM debates')
    count = cur.fetchone()[0]
    conn.close()
    print(f'   ✅ DB healthy — {count} debates found')
except Exception as e:
    print(f'   ❌ DB error: {e}')
    sys.exit(1)
"

# ── 5. Start API ─────────────────────────────────────────────────────────────
echo "→ Starting FastAPI..."
nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/peerforge-api.log 2>&1 &
API_PID=$!
echo "   API PID: $API_PID  (logs: /tmp/peerforge-api.log)"

# ── 6. Start Celery ──────────────────────────────────────────────────────────
echo "→ Starting Celery worker..."
nohup celery -A src.celery_app worker --loglevel=info \
  --queues=celery,materials,preflight > /tmp/peerforge-celery.log 2>&1 &
CELERY_PID=$!
echo "   Celery PID: $CELERY_PID  (logs: /tmp/peerforge-celery.log)"

# ── 7. Start frontend ────────────────────────────────────────────────────────
echo "→ Starting Next.js frontend..."
cd "$WEB_DIR"
nohup npm run dev > /tmp/peerforge-web.log 2>&1 &
WEB_PID=$!
echo "   Frontend PID: $WEB_PID  (logs: /tmp/peerforge-web.log)"

# ── 8. Final check ───────────────────────────────────────────────────────────
echo "→ Waiting for API to be ready..."
sleep 10
HTTP=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer dev-bypass-token" \
  "http://localhost:8000/debates?workspace_id=00000000-0000-0000-0000-000000000101")

if [ "$HTTP" = "200" ]; then
  echo ""
  echo "✅  All services running!"
  echo "   Frontend : http://localhost:3000"
  echo "   API      : http://localhost:8000"
  echo "   API docs : http://localhost:8000/docs"
else
  echo "⚠️  API returned HTTP $HTTP — check /tmp/peerforge-api.log"
fi
