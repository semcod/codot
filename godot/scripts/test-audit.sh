#!/usr/bin/env bash
# Test audit log: generate a bundle via LLM and verify Postgres audit_log entry.
set -e

set -a
source .env
set +a

LLM_URL="http://localhost:${LLM_PORT:-18094}"
POSTGRES_CONTAINER="temporal-postgres"
LLM_CONTAINER="godot-llm"

echo "=== Audit Log Test ==="

# Ensure LLM is reachable
if ! curl -fsS "$LLM_URL/generate/bundle" \
    -X POST -H "Content-Type: application/json" \
    -d '{"prompt":"Build a weather dashboard for Berlin","write_file":false}' \
    >/dev/null 2>&1; then
    echo "Error: LLM service not reachable at $LLM_URL"
    echo "Run: make start"
    exit 1
fi
echo "✓ Generated bundle via LLM"

# Ensure audit table exists (idempotent via audit.py ensure_table)
if docker ps --format '{{.Names}}' | grep -q "^${LLM_CONTAINER}$"; then
    docker exec "$LLM_CONTAINER" python -c "import audit; audit.ensure_table()" 2>/dev/null || true
else
    echo "Warning: LLM container not running — table may not exist yet"
fi

# Query audit_log count
if docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER}$"; then
    count=$(docker exec -i "$POSTGRES_CONTAINER" \
        psql -U temporal -d temporal -t -c \
        "SELECT COUNT(*) FROM audit_log WHERE endpoint='/generate/bundle';")
    count=$(echo "$count" | xargs)
    echo "audit_log entries for /generate/bundle: $count"
    if [ "$count" -gt 0 ]; then
        echo "✓ Audit log written successfully"
    else
        echo "✗ No audit log entries found"
        exit 1
    fi
else
    echo "Error: Postgres container not running"
    exit 1
fi

echo ""
echo "=== Audit Log Test PASSED ==="
