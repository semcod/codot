#!/usr/bin/env bash
set -euo pipefail

echo "=== Testing Godot LiteLLM + ACL stack ==="
echo ""

set -a
source .env
set +a

LLM_BASE_URL="http://localhost:${LLM_PORT:-18094}"
MOCK_BASE_URL="http://localhost:${MOCK_API_PORT:-18095}"

wait_for_http() {
    local url="$1"
    local attempts="${2:-30}"
    local sleep_seconds="${3:-2}"
    local i
    for ((i=1; i<=attempts; i++)); do
        if curl -fsS "$url" >/dev/null 2>&1; then
            return 0
        fi
        sleep "$sleep_seconds"
    done
    return 1
}

if ! docker-compose ps | grep -q "godot-llm"; then
    echo "❌ LLM service is not running. Please run 'make start' first."
    exit 1
fi

echo "✓ LLM service is running"
echo ""

echo "Test 1: Waiting for mock API and LLM health endpoints..."
if wait_for_http "$MOCK_BASE_URL/health" 45 2; then
    echo "✓ Mock API healthy at $MOCK_BASE_URL/health"
else
    echo "❌ Mock API did not become ready"
    exit 1
fi
if wait_for_http "$LLM_BASE_URL/health" 45 2; then
    echo "✓ LLM API healthy at $LLM_BASE_URL/health"
else
    echo "❌ LLM API did not become ready"
    exit 1
fi

echo ""

echo "Test 2: Fetch allowed endpoint via ACL..."
ALLOWED_FETCH=$(curl -fsS -X POST "$LLM_BASE_URL/fetch" \
  -H "Content-Type: application/json" \
  -d '{"uri":"http://mock-api:8001/api/v1/devices"}')
python3 - "$ALLOWED_FETCH" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
assert payload["json"]["items"][0]["name"] == "temperature-sensor", payload
print("allowed fetch items:", len(payload["json"]["items"]))
PY

echo "✓ Allowed endpoint data is visible"
echo ""

echo "Test 3: Fetch multiple endpoints through /context..."
CONTEXT_RESPONSE=$(curl -fsS -X POST "$LLM_BASE_URL/context" \
  -H "Content-Type: application/json" \
  -d '{"uris":["http://mock-api:8001/api/v1/devices","http://mock-api:8001/api/v1/protocols/123"]}')
python3 - "$CONTEXT_RESPONSE" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
assert payload["count"] == 2, payload
assert payload["items"][0]["ok"] is True, payload
assert payload["items"][1]["ok"] is True, payload
print("context items:", payload["count"])
PY
echo "✓ /context returned data from multiple endpoints"
echo ""

echo "Test 4: Fetch denied endpoint via ACL..."
DENIED_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$LLM_BASE_URL/fetch" \
  -H "Content-Type: application/json" \
  -d '{"uri":"http://localhost:5433"}')
if [ "$DENIED_STATUS" = "403" ]; then
    echo "✓ Local/private endpoint correctly denied"
else
    echo "❌ Expected 403 for blocked endpoint, got $DENIED_STATUS"
    exit 1
fi

echo ""

echo "Test 5: NLP prompt -> service bundle"
SERVICE_RESPONSE=$(curl -fsS -X POST "$LLM_BASE_URL/generate/bundle" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"Stwórz bundle usługi dla urządzeń z endpointem mock-api i wyjściem python fastapi.",
    "bundle_name":"llm-devices-service",
    "source_uris":["http://mock-api:8001/api/v1/devices"],
    "write_file":true,
    "include_context":true
  }')
python3 - "$SERVICE_RESPONSE" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
bundle = payload["bundle"]
assert bundle["kind"] == "SERVICE_BUNDLE", bundle
assert bundle["runner"] in {"go_temporal", "python_fastapi"}, bundle
assert len(payload["context"]) == 1, payload
print("bundle file:", payload["file_path"])
PY
if [ -f "bundles/generated/llm-devices-service.json" ]; then
    echo "✓ Generated service bundle file exists"
else
    echo "❌ Generated service bundle file missing"
    exit 1
fi

echo ""

echo "Test 6: NLP prompt -> view bundle"
VIEW_RESPONSE=$(curl -fsS -X POST "$LLM_BASE_URL/generate/bundle" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"Zbuduj live dashboard view bundle dla mock API z web pwa targets.",
    "bundle_name":"llm-device-dashboard",
    "source_uris":["http://mock-api:8001/api/v1/protocols/123"],
    "targets":["web","pwa"],
    "write_file":true,
    "include_context":true
  }')
python3 - "$VIEW_RESPONSE" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
bundle = payload["bundle"]
assert bundle["kind"] == "VIEW_BUNDLE", bundle
assert "web" in bundle.get("targets", []), bundle
assert "pwa" in bundle.get("targets", []), bundle
print("bundle file:", payload["file_path"])
PY
if [ -f "bundles/generated/llm-device-dashboard.json" ]; then
    echo "✓ Generated view bundle file exists"
else
    echo "❌ Generated view bundle file missing"
    exit 1
fi

echo ""

echo "Test 7: NLP prompt -> application bundle"
APP_RESPONSE=$(curl -fsS -X POST "$LLM_BASE_URL/generate/bundle" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt":"Wygeneruj application bundle dla desktop, mobile, web i pwa klienta danych.",
    "bundle_name":"llm-multi-platform-app",
    "targets":["desktop","mobile","web","pwa"],
    "write_file":true
  }')
python3 - "$APP_RESPONSE" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
bundle = payload["bundle"]
assert bundle["kind"] == "APPLICATION_BUNDLE", bundle
assert bundle["runner"] == "go_temporal", bundle
assert set(["desktop", "mobile", "web", "pwa"]).issubset(set(bundle.get("targets", []))), bundle
print("bundle file:", payload["file_path"])
PY
if [ -f "bundles/generated/llm-multi-platform-app.json" ]; then
    echo "✓ Generated application bundle file exists"
else
    echo "❌ Generated application bundle file missing"
    exit 1
fi

echo ""

echo "Test 8: Generated bundles visible under endpoint"
BUNDLES_RESPONSE=$(curl -fsS "$LLM_BASE_URL/bundles")
python3 - "$BUNDLES_RESPONSE" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
files = payload.get("files", [])
assert any("llm-devices-service.json" in f for f in files), files
assert any("llm-device-dashboard.json" in f for f in files), files
assert any("llm-multi-platform-app.json" in f for f in files), files
print("visible files:", files)
PY

echo ""
echo "=== LLM tests passed ==="
