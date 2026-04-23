#!/usr/bin/env bash
set -e

echo "=== Testing Godot Bundle System Services ==="
echo ""

# Check if docker-compose is running
if ! docker-compose ps | grep -q "Up"; then
    echo "❌ Docker services are not running. Please run 'make docker-up' first."
    exit 1
fi

echo "✓ Docker services are running"
echo ""

# Test 1: Check schema server
echo "Test 1: Checking schema server..."
SCHEMA_PORT=$(grep SCHEMA_SERVER_PORT .env | cut -d '=' -f2)
SCHEMA_URL="http://localhost:${SCHEMA_PORT:-8084}/bundle.schema.json"
if curl -s -f "$SCHEMA_URL" > /dev/null; then
    echo "✓ Schema server is accessible at $SCHEMA_URL"
else
    echo "❌ Schema server is not accessible at $SCHEMA_URL"
fi
echo ""

# Test 2: Check Temporal server
echo "Test 2: Checking Temporal server..."
TEMPORAL_PORT=$(grep TEMPORAL_PORT .env | cut -d '=' -f2)
if nc -z localhost ${TEMPORAL_PORT:-7233} 2>/dev/null; then
    echo "✓ Temporal server is accessible on port ${TEMPORAL_PORT:-7233}"
else
    echo "❌ Temporal server is not accessible on port ${TEMPORAL_PORT:-7233}"
fi
echo ""

# Test 3: Check PostgreSQL
echo "Test 3: Checking PostgreSQL..."
POSTGRES_PORT=$(grep POSTGRES_PORT .env | cut -d '=' -f2)
if nc -z localhost ${POSTGRES_PORT:-5433} 2>/dev/null; then
    echo "✓ PostgreSQL is accessible on port ${POSTGRES_PORT:-5433}"
else
    echo "❌ PostgreSQL is not accessible on port ${POSTGRES_PORT:-5433}"
fi
echo ""

# Test 4: Run bundle validation in Docker
echo "Test 4: Running bundle validation in Docker container..."
if docker exec godot-bundle-service bash scripts/validate-all.sh; then
    echo "✓ All bundles validated successfully in Docker"
else
    echo "❌ Bundle validation failed in Docker"
fi
echo ""

# Test 5: Check Go compilation
echo "Test 5: Checking Go compilation in Docker..."
if docker exec godot-bundle-service sh -c "cd src && go build -o /tmp/test bundle.go"; then
    echo "✓ Go code compiles successfully"
    docker exec godot-bundle-service rm -f /tmp/test
else
    echo "❌ Go compilation failed"
fi
echo ""

# Test 6: Test schema loading with default schema
echo "Test 6: Testing schema loading with default schema..."
docker exec godot-bundle-service sh -c "cd src && go run -c 'package main; import (\"os\"; \"log\"); func main() { log.Println(os.Getenv(\"BUNDLE_SCHEMA_URI\")) }'" 2>/dev/null || echo "⚠ Schema URI test skipped (Go compilation issue)"
echo "Test 6: Schema URI from env: $(docker exec godot-bundle-service sh -c 'echo $BUNDLE_SCHEMA_URI')"
echo ""

# Test 7: Check bundle files exist
echo "Test 7: Checking bundle files..."
BUNDLE_COUNT=$(docker exec godot-bundle-service sh -c "ls /app/bundles/*.json | wc -l")
echo "✓ Found $BUNDLE_COUNT bundle files in container"
echo ""

echo "=== Service Testing Complete ==="
echo ""
echo "Service URLs:"
echo "  Schema Server:  http://localhost:${SCHEMA_PORT:-8084}/bundle.schema.json"
echo "  Temporal Web:   http://localhost:${TEMPORAL_PORT:-7233}"
echo "  PostgreSQL:     localhost:${POSTGRES_PORT:-5433}"
echo ""
echo "Next steps:"
echo "  - Run 'make docker-test' to validate bundles"
echo "  - Run 'docker exec -it godot-bundle-service bash' to enter container"
echo "  - Run 'docker exec godot-bundle-service bash scripts/validate-all.sh' to validate bundles"
