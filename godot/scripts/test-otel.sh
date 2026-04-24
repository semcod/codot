#!/usr/bin/env bash
# Test OpenTelemetry/Jaeger trace collection is reachable.
set -e

JAEGER_URL="http://localhost:${JAEGER_UI_PORT:-16686}"
OTEL_GRPC="localhost:${JAEGER_OTLP_GRPC_PORT:-4317}"

echo "=== OpenTelemetry / Jaeger Test ==="

# 1. Check Jaeger UI reachable
echo "[1/3] Checking Jaeger UI at $JAEGER_URL ..."
if curl -fsS "$JAEGER_URL" >/dev/null 2>&1; then
    echo "✓ Jaeger UI reachable"
else
    echo "  Jaeger UI not reachable (run: make docker-up)"
fi

# 2. Check OTLP gRPC port
echo ""
echo "[2/3] Checking OTLP gRPC port $OTEL_GRPC ..."
if nc -z localhost "${JAEGER_OTLP_GRPC_PORT:-4317}" 2>/dev/null; then
    echo "✓ OTLP gRPC port open"
else
    echo "  OTLP gRPC port not responding"
fi

# 3. Check Jaeger API for services
echo ""
echo "[3/3] Checking Jaeger API for services..."
SVCS=$(curl -fsS "$JAEGER_URL/api/services" 2>/dev/null || echo "{}")
if echo "$SVCS" | grep -q '"data"'; then
    echo "✓ Jaeger API returns services list"
else
    echo "  Jaeger API no services yet (traces will appear after first bundle execution)"
fi

echo ""
echo "=== OpenTelemetry Test DONE ==="
echo "Export OTEL_EXPORTER=1 to enable stdout traces in bundle execution."
