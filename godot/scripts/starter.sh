#!/usr/bin/env bash
set -e

echo "=== Temporal Starter ==="
echo "Requires: go + temporal server running"
echo ""

BUNDLE_FILE="${1:-bundles/protocol-dashboard.json}"
if [ ! -f "$BUNDLE_FILE" ]; then
    echo "Usage: $0 <bundle.json>"
    exit 1
fi

cd src
BUNDLE=$(cat "../$BUNDLE_FILE")
GOFLAGS=-mod=mod go run starter.go "$BUNDLE"
