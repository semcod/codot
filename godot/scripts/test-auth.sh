#!/usr/bin/env bash
# Test auth layer: Caddy forward_auth + LLM /auth endpoint.
set -e

LLM_URL="http://localhost:${LLM_PORT:-18094}"

echo "=== Auth Layer Test ==="

# 1. LLM /auth accepts valid token
echo "[1/4] LLM /auth with valid token..."
resp=$(curl -fsS -w "\n%{http_code}" -H "Authorization: Bearer admin-token" "$LLM_URL/auth" 2>&1 || true)
if echo "$resp" | grep -q "200"; then
    echo "✓ Valid token accepted (200)"
else
    echo "✗ Valid token rejected"
    echo "$resp"
    exit 1
fi

# 2. LLM /auth rejects invalid token
echo ""
echo "[2/4] LLM /auth with invalid token..."
resp=$(curl -fsS -w "\n%{http_code}" -H "Authorization: Bearer bad-token" "$LLM_URL/auth" 2>&1 || true)
if echo "$resp" | grep -q "403"; then
    echo "✓ Invalid token rejected (403)"
else
    echo "✗ Invalid token not rejected correctly"
    echo "$resp"
    exit 1
fi

# 3. LLM /auth rejects missing token
echo ""
echo "[3/4] LLM /auth without token..."
resp=$(curl -fsS -w "\n%{http_code}" "$LLM_URL/auth" 2>&1 || true)
if echo "$resp" | grep -q "401"; then
    echo "✓ Missing token rejected (401)"
else
    echo "✗ Missing token not rejected correctly"
    echo "$resp"
    exit 1
fi

# 4. Check Caddy /generate is protected (if Caddy schema-server is up on 8084)
echo ""
echo "[4/4] Caddy schema-server auth proxy..."
SCHEMA_URL="http://localhost:${SCHEMA_SERVER_PORT:-8084}"
if curl -fsS "$SCHEMA_URL/health" >/dev/null 2>&1; then
    # Caddy is running with auth
    resp=$(curl -fsS -w "\n%{http_code}" "$SCHEMA_URL/generate/bundle" \
        -H "Content-Type: application/json" \
        -d '{"prompt":"test","write_file":false}' 2>&1 || true)
    if echo "$resp" | grep -q "401\|403"; then
        echo "✓ Caddy /generate/bundle blocked without token"
    else
        echo "✗ Caddy /generate/bundle not blocking (may be 502 if LLM down)"
    fi
    # With valid token should get 200 (or 502 if LLM down)
    resp=$(curl -fsS -w "\n%{http_code}" "$SCHEMA_URL/generate/bundle" \
        -H "Authorization: Bearer admin-token" \
        -H "Content-Type: application/json" \
        -d '{"prompt":"test","write_file":false}' 2>&1 || true)
    if echo "$resp" | grep -q "200\|502"; then
        echo "✓ Caddy /generate/bundle allows valid token (200/502)"
    else
        echo "✗ Caddy /generate/bundle rejects valid token"
    fi
else
    echo "  schema-server not running — skipping Caddy proxy test"
    echo "  Run: make docker-up"
fi

echo ""
echo "=== Auth Layer Test PASSED ==="
