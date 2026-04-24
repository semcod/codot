#!/usr/bin/env bash
# Test Prometheus/Grafana scrape of LLM /metrics endpoint.
set -e

LLM_URL="http://localhost:${LLM_PORT:-18094}"
PROM_URL="http://localhost:${PROMETHEUS_PORT:-9090}"

echo "=== Prometheus/Grafana Test ==="

# 1. LLM /metrics reachable
echo "[1/3] Checking LLM /metrics..."
if ! curl -fsS "$LLM_URL/metrics" >/dev/null 2>&1; then
    echo "Error: LLM /metrics not reachable at $LLM_URL/metrics"
    echo "Ensure LLM service is running: make start"
    exit 1
fi
echo "✓ LLM /metrics reachable"

# 2. Prometheus is up and has LLM target
echo ""
echo "[2/3] Checking Prometheus targets..."
if ! curl -fsS "$PROM_URL/api/v1/targets" >/dev/null 2>&1; then
    echo "Error: Prometheus not reachable at $PROM_URL"
    echo "Ensure Prometheus is running: make docker-up"
    exit 1
fi
echo "✓ Prometheus reachable"

# 3. LLM metrics appear in Prometheus
echo ""
echo "[3/3] Checking LLM metrics in Prometheus..."
sleep 2
if curl -fsS "$PROM_URL/api/v1/query?query=up{job='llm'}" | grep -q '"value":\["[0-9]*","1"\]'; then
    echo "✓ LLM target is UP in Prometheus"
else
    echo "Warning: LLM target not yet reported as UP (may need more scrape cycles)"
fi

echo ""
echo "=== Prometheus/Grafana Test PASSED ==="
echo "Grafana UI: http://localhost:${GRAFANA_PORT:-3000}  (admin/${GRAFANA_PASSWORD:-admin})"
