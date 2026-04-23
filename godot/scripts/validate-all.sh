#!/usr/bin/env bash
set -e

echo "=== Validating all bundle JSONs ==="

FAILED=0
FOUND=0
while IFS= read -r bundle; do
    FOUND=1
    echo ""
    echo "Validating: $bundle"
    if bash scripts/validate-bundle.sh "$bundle"; then
        echo "✓ $bundle valid"
    else
        echo "✗ $bundle failed"
        FAILED=1
    fi
done < <(find bundles -type f -name '*.json' | sort)

if [ "$FOUND" -eq 0 ]; then
    echo "No bundle JSON files found under bundles/"
    exit 1
fi

echo ""
if [ $FAILED -eq 0 ]; then
    echo "=== All bundles validated successfully ==="
else
    echo "=== Some bundles failed validation ==="
    exit 1
fi
