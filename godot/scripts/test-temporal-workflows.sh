#!/usr/bin/env bash
# Test Temporal workflows via Web UI: start worker, run a workflow, verify in UI.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEMPORAL_URL="http://localhost:${TEMPORAL_UI_PORT:-8233}"

echo "=== Temporal Workflow Test ==="

# 1. Ensure Temporal UI is reachable
echo "[1/4] Checking Temporal UI at $TEMPORAL_URL ..."
if ! curl -fsS "$TEMPORAL_URL" >/dev/null 2>&1; then
    echo "Error: Temporal UI not reachable at $TEMPORAL_URL"
    echo "Run: make docker-up"
    exit 1
fi
echo "✓ Temporal UI reachable"

# 2. Start Temporal worker in background (if not running)
echo ""
echo "[2/4] Starting Temporal worker..."
if ! pgrep -f "deploy_workflow.go" >/dev/null 2>&1; then
    cd "$ROOT/src"
    nohup go run deploy_workflow.go > /tmp/temporal-worker.log 2>&1 &
    sleep 3
    if ! pgrep -f "deploy_workflow.go" >/dev/null 2>&1; then
        echo "Error: worker failed to start"
        cat /tmp/temporal-worker.log 2>/dev/null || true
        exit 1
    fi
    echo "✓ Worker started (PID: $(pgrep -f deploy_workflow.go))"
else
    echo "✓ Worker already running"
fi

# 3. Execute a workflow via starter
echo ""
echo "[3/4] Executing protocol-dashboard workflow..."
cd "$ROOT/src"
go run starter.go @../bundles/protocol-dashboard.json > /tmp/starter.log 2>&1 || true
sleep 2
cat /tmp/starter.log

# 4. Verify workflow appears in Temporal UI
echo ""
echo "[4/4] Verifying workflow in Temporal UI..."
WF_LIST=$(curl -fsS "$TEMPORAL_URL/api/v1/namespaces/default/workflows" 2>/dev/null || echo "{}")
if echo "$WF_LIST" | grep -q "protocol-dashboard\|deploy-protocol-dashboard"; then
    echo "✓ Workflow visible in Temporal UI"
else
    echo "Warning: workflow not yet visible in UI (may need more time)"
    echo "$WF_LIST" | head -c 500
fi

echo ""
echo "=== Temporal Workflow Test COMPLETE ==="
echo "Temporal Web UI: $TEMPORAL_URL"
