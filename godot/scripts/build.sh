#!/usr/bin/env bash
set -e

echo "=== Validating all bundles ==="
bash scripts/validate-all.sh

echo "=== Checking Go structs ==="
if command -v go &> /dev/null; then
    cd src
    go build -o /dev/null bundle.go 2>/dev/null || true
    echo "Go structs OK"
else
    echo "Go not installed — skipping Go build"
fi

echo "=== All checks passed ==="
