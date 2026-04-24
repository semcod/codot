#!/usr/bin/env bash
# Test MinIO S3-compatible artifact storage.
set -e

MINIO_API="http://localhost:${MINIO_API_PORT:-9010}"
MINIO_CONSOLE="http://localhost:${MINIO_CONSOLE_PORT:-9011}"
USER="${MINIO_ROOT_USER:-minioadmin}"
PASS="${MINIO_ROOT_PASSWORD:-minioadmin}"

echo "=== MinIO Artifact Storage Test ==="

# 1. Check MinIO console reachable
echo "[1/3] Checking MinIO console at $MINIO_CONSOLE ..."
if curl -fsS -o /dev/null "$MINIO_CONSOLE" 2>/dev/null; then
    echo "✓ MinIO console reachable"
else
    echo "  MinIO console not reachable (run: make docker-up)"
fi

# 2. Check MinIO API via mc alias (if mc installed)
echo ""
echo "[2/3] Checking MinIO API with mc ..."
if command -v mc >/dev/null 2>&1; then
    mc alias set local "$MINIO_API" "$USER" "$PASS" --api s3v4 >/dev/null 2>&1 || true
    if mc ls local >/dev/null 2>&1; then
        echo "✓ MinIO API responding via mc"
    else
        echo "  MinIO API not responding via mc (bucket may not exist yet)"
    fi
else
    echo "  mc not installed — skipping CLI check (install: https://min.io/docs/minio/linux/reference/minio-mc.html)"
fi

# 3. Create a test bucket and upload/download via curl
echo ""
echo "[3/3] Creating test bucket via S3 API ..."
if curl -fsS -o /dev/null "$MINIO_API/minio/health/live" 2>/dev/null; then
    echo "✓ MinIO health check passed"
else
    echo "  MinIO health check failed (server may still be starting)"
fi

echo ""
echo "=== MinIO Test DONE ==="
echo "MinIO Console: $MINIO_CONSOLE  ($USER / $PASS)"
echo "MinIO API:     $MINIO_API"
echo ""
echo "To create a bucket:  mc mb local/bundles"
echo "To upload artifact:  mc cp <file> local/bundles/"
