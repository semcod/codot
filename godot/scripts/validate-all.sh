#!/usr/bin/env bash
set -e

echo "=== Validating all bundle JSONs ==="

FAILED=0
for bundle in bundles/*.json; do
    echo ""
    echo "Validating: $bundle"
    if bash scripts/validate-bundle.sh "$bundle"; then
        echo "✓ $bundle valid"
    else
        echo "✗ $bundle failed"
        FAILED=1
    fi
done

echo ""
if [ $FAILED -eq 0 ]; then
    echo "=== All bundles validated successfully ==="
else
    echo "=== Some bundles failed validation ==="
    exit 1
fi
