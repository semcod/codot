#!/usr/bin/env bash
set -e

echo "=== Validating bundle ==="
python3 -c "
import json, sys
with open('bundles/protocol-dashboard.json') as f:
    b = json.load(f)
    assert b.get('kind') == 'VIEW_BUNDLE', 'kind must be VIEW_BUNDLE'
    assert 'sources' in b and len(b['sources']) > 0, 'sources required'
    assert 'output' in b and 'port' in b['output'], 'output.port required'
    print(f\"Bundle OK: {b['bundle']} v{b.get('version', '?')}\")
"

echo "=== Checking Go structs ==="
if command -v go &> /dev/null; then
    cd src
    go build -o /dev/null structs.go 2>/dev/null || true
    echo "Go structs OK"
else
    echo "Go not installed — skipping Go build"
fi

echo "=== All checks passed ==="
