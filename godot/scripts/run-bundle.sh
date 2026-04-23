#!/usr/bin/env bash
set -e

BUNDLE_FILE="${1:-bundles/protocol-dashboard.json}"
if [ ! -f "$BUNDLE_FILE" ]; then
    echo "Error: Bundle file not found: $BUNDLE_FILE"
    exit 1
fi

echo "=== Running bundle: $BUNDLE_FILE ==="

# Validate first
bash scripts/validate-bundle.sh "$BUNDLE_FILE"

# Extract runner
RUNNER=$(python3 -c "import json; print(json.load(open('$BUNDLE_FILE'))['runner'])")
echo "Runner: $RUNNER"

case "$RUNNER" in
    go_temporal)
        echo "Starting Temporal runner..."
        cd src
        BUNDLE=$(cat "../$BUNDLE_FILE")
        GOFLAGS=-mod=mod go run starter.go "$BUNDLE"
        ;;
    python_fastapi)
        echo "Python FastAPI runner not yet implemented"
        exit 1
        ;;
    *)
        echo "Unknown runner: $RUNNER"
        exit 1
        ;;
esac
