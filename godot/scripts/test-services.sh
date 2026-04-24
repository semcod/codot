#!/usr/bin/env bash
set -e

echo "=== Testing Godot Bundle System Services ==="
echo ""

set -a
source .env
set +a

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

wait_for_port() {
    local host="$1"
    local port="$2"
    local attempts="${3:-30}"
    local sleep_seconds="${4:-2}"
    local i
    for ((i=1; i<=attempts; i++)); do
        if python3 - "$host" "$port" <<'PY' >/dev/null 2>&1
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(1.0)
try:
    sock.connect((host, port))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
        then
            return 0
        fi
        sleep "$sleep_seconds"
    done
    return 1
}

# Check if docker-compose is running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Docker services are not running. Please run 'make docker-up' first."
    exit 1
fi

echo "✓ Docker services are running"
echo ""

# Test 1: Check schema server
echo "Test 1: Checking schema server..."
SCHEMA_URL="http://localhost:${SCHEMA_SERVER_PORT:-8084}/bundle.schema.json"
if wait_for_http "$SCHEMA_URL" 30 2; then
    echo "✓ Schema server is accessible at $SCHEMA_URL"
else
    echo "❌ Schema server is not accessible at $SCHEMA_URL"
    exit 1
fi
echo ""

# Test 2: Check Temporal server
echo "Test 2: Checking Temporal server..."
if wait_for_port localhost "${TEMPORAL_PORT:-7233}" 30 2; then
    echo "✓ Temporal gRPC frontend on port ${TEMPORAL_PORT:-7233}"
else
    echo "❌ Temporal gRPC frontend not accessible on port ${TEMPORAL_PORT:-7233}"
    exit 1
fi
if wait_for_http "http://localhost:${TEMPORAL_UI_PORT:-8233}" 30 2; then
    echo "✓ Temporal Web UI accessible at http://localhost:${TEMPORAL_UI_PORT:-8233}"
else
    echo "❌ Temporal Web UI not accessible at http://localhost:${TEMPORAL_UI_PORT:-8233}"
    exit 1
fi
echo ""

# Test 3: Check PostgreSQL
echo "Test 3: Checking PostgreSQL..."
if wait_for_port localhost "${POSTGRES_PORT:-5433}" 30 2; then
    echo "✓ PostgreSQL is accessible on port ${POSTGRES_PORT:-5433}"
else
    echo "❌ PostgreSQL is not accessible on port ${POSTGRES_PORT:-5433}"
    exit 1
fi
echo ""

# Test 4: Run bundle validation in Docker
echo "Test 4: Running bundle validation in Docker container..."
if docker exec godot-bundle-service bash scripts/validate-all.sh; then
    echo "✓ All bundles validated successfully in Docker"
else
    echo "❌ Bundle validation failed in Docker"
    exit 1
fi
echo ""

# Test 5: Check Go compilation
echo "Test 5: Checking Go compilation in Docker..."
if docker exec godot-bundle-service sh -c "cd src && GOFLAGS=-mod=mod go test bundle.go bundle_test.go"; then
    echo "✓ Go code compiles successfully"
else
    echo "❌ Go compilation failed"
    exit 1
fi
echo ""

# Test 6: Check schema URI configuration
echo "Test 6: Checking schema URI configuration..."
echo "✓ Schema URI from env: $(docker exec godot-bundle-service sh -c 'echo $BUNDLE_SCHEMA_URI')"
echo ""

# Test 7: Check bundle files exist
echo "Test 7: Checking bundle files..."
BUNDLE_COUNT=$(docker exec godot-bundle-service sh -c "find /app/bundles -type f -name '*.json' | wc -l")
echo "✓ Found $BUNDLE_COUNT bundle files in container"
echo ""

echo "=== Service Testing Complete ==="
echo ""
echo "Service URLs:"
echo "  Schema Server:  http://localhost:${SCHEMA_SERVER_PORT:-8084}/bundle.schema.json"
echo "  Temporal Web:   http://localhost:${TEMPORAL_UI_PORT:-8233}"
echo "  PostgreSQL:     localhost:${POSTGRES_PORT:-5433}"
echo ""
echo "Next steps:"
echo "  - Run 'make docker-test' to validate bundles"
echo "  - Run 'docker exec -it godot-bundle-service bash' to enter container"
echo "  - Run 'docker exec godot-bundle-service bash scripts/validate-all.sh' to validate bundles"
